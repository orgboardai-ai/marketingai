"""
API синхронізації розкладу з Google Calendar.
"""
import json
import secrets
import datetime
import logging
from urllib.parse import urlparse, urlunparse

from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request as DRFRequest

from django.http import HttpResponseNotFound
from django.core.cache import cache

from .models import GoogleCalendarCredential, ScheduleSlot
from . import services

logger = logging.getLogger(__name__)
User = get_user_model()

# Резерв, якщо сесія зникне після редіректу з Google (ngrok, кілька вкладок).
_OAUTH_COOKIE = 'mkt_cal_oauth'
_OAUTH_COOKIE_SALT = 'mkt_cal_oauth_v1'
_OAUTH_COOKIE_MAX_AGE = 900
_OAUTH_CACHE_PREFIX = 'mkt_cal_oauth_state:'
_OAUTH_CACHE_TTL = 900  # секунд; узгоджено з cookie


def _oauth_cache_key(state: str) -> str:
    """Ключ у cache для зв’язку state OAuth → user_id (без сесії/cookie після Google)."""
    return f'{_OAUTH_CACHE_PREFIX}{state}'


def _redirect_uri(request) -> str:
    """
    redirect_uri для OAuth Flow — збігається з Authorized redirect URI у Google Cloud.
    Якщо задано GOOGLE_REDIRECT_URI — нормалізуємо через urlparse (без зайвих query),
    щоб той самий рядок використовувався в authorization_url і fetch_token.
    """
    p = (getattr(request, 'path', '') or '').rstrip('/')
    if p.endswith('/api/google-calendar/schedule'):
        return request.build_absolute_uri('/api/google-calendar/schedule/')
    configured = (getattr(settings, 'GOOGLE_REDIRECT_URI', '') or '').strip()
    if configured:
        pr = urlparse(configured)
        return urlunparse((pr.scheme, pr.netloc, pr.path, '', '', ''))
    return request.build_absolute_uri(reverse('calendar_sync:oauth_callback'))


def _oauth_authorization_response(request) -> str:
    """
    Повний URL callback з code/state для flow.fetch_token().
    За ngrok request.build_absolute_uri() часто дає http/не той хост — Google відхиляє обмін.
    Тоді збираємо URL з GOOGLE_REDIRECT_URI + QUERY_STRING поточного запиту.
    """
    p = (getattr(request, 'path', '') or '').rstrip('/')
    if p.endswith('/api/google-calendar/schedule'):
        base = request.build_absolute_uri('/api/google-calendar/schedule/')
        qs = request.META.get('QUERY_STRING', '')
        return f'{base}?{qs}' if qs else base

    configured = (getattr(settings, 'GOOGLE_REDIRECT_URI', '') or '').strip()
    if configured:
        pr = urlparse(configured)
        qs = request.META.get('QUERY_STRING', '')
        return urlunparse((pr.scheme, pr.netloc, pr.path, '', qs, ''))

    return request.build_absolute_uri()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def google_oauth_start(request):
    """Початок OAuth: JSON з auth_url."""
    try:
        state = secrets.token_urlsafe(32)
        request.session['calendar_oauth_state'] = state
        request.session['calendar_oauth_user_id'] = request.user.pk
        flow = services.get_oauth_flow(redirect_uri=_redirect_uri(request), state=state)
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
        )
        try:
            cache.set(_oauth_cache_key(state), int(request.user.pk), _OAUTH_CACHE_TTL)
        except Exception as e:
            logger.warning('OAuth cache.set не вдався: %s', e)
        resp = Response({'auth_url': auth_url})
        # Підписаний cookie: state + user_id (якщо session не повернеться після accounts.google.com).
        try:
            payload = json.dumps({'s': state, 'u': request.user.pk})
            resp.set_signed_cookie(
                _OAUTH_COOKIE,
                payload,
                max_age=_OAUTH_COOKIE_MAX_AGE,
                samesite='Lax',
                httponly=True,
                path='/',
                salt=_OAUTH_COOKIE_SALT,
                secure=request.is_secure(),
            )
        except Exception as e:
            logger.warning('Не вдалося виставити OAuth cookie: %s', e)
        return resp
    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def google_oauth_callback(request):
    """Callback від Google: обмін code → токени, редірект на дашборд."""
    if request.GET.get('error'):
        logger.warning('OAuth Google error=%s desc=%s', request.GET.get('error'), request.GET.get('error_description', '')[:200])
        r = redirect(f'{reverse("chat")}?calendar=error&reason=google_denied')
        r.delete_cookie(_OAUTH_COOKIE, path='/')
        return r

    state = request.GET.get('state', '')
    code = request.GET.get('code', '')

    if not code or not state:
        r = redirect(f'{reverse("chat")}?calendar=error&reason=missing')
        r.delete_cookie(_OAUTH_COOKIE, path='/')
        return r

    session_state = request.session.get('calendar_oauth_state')
    session_uid = request.session.get('calendar_oauth_user_id')
    match_session = bool(session_state == state and session_uid)

    user_id = None
    if match_session:
        user_id = session_uid
    else:
        try:
            entry = cache.get(_oauth_cache_key(state))
            if entry is not None:
                user_id = int(entry) if not isinstance(entry, dict) else int(entry.get('uid'))
                cache.delete(_oauth_cache_key(state))
        except (TypeError, ValueError) as e:
            logger.warning('OAuth callback cache uid: %s', e)

    if user_id is None:
        try:
            raw = request.get_signed_cookie(_OAUTH_COOKIE, default=None, salt=_OAUTH_COOKIE_SALT)
            if raw:
                data = json.loads(raw)
                if data.get('s') == state:
                    user_id = data.get('u')
        except Exception as e:
            logger.warning('OAuth callback: cookie/state: %s', e)

    if user_id is None:
        logger.warning(
            'OAuth callback відхилено: session=%s cache/cookie без user для state',
            match_session,
        )
        r = redirect(f'{reverse("chat")}?calendar=error&reason=state')
        r.delete_cookie(_OAUTH_COOKIE, path='/')
        return r

    request.session.pop('calendar_oauth_state', None)
    request.session.pop('calendar_oauth_user_id', None)

    try:
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, TypeError, ValueError):
        r = redirect(f'{reverse("chat")}?calendar=error&reason=user')
        r.delete_cookie(_OAUTH_COOKIE, path='/')
        return r

    try:
        redirect_uri = _redirect_uri(request)
        flow = services.get_oauth_flow(redirect_uri=redirect_uri, state=state)
        auth_response = _oauth_authorization_response(request)
        flow.fetch_token(authorization_response=auth_response)
    except Exception as e:
        logger.exception('OAuth callback fetch_token')
        try:
            cache.delete(_oauth_cache_key(state))
        except Exception:
            pass
        r = redirect(f'{reverse("chat")}?calendar=error&reason=token')
        r.delete_cookie(_OAUTH_COOKIE, path='/')
        return r

    try:
        cache.delete(_oauth_cache_key(state))
    except Exception:
        pass

    creds = flow.credentials
    services.persist_google_calendar_credential(user, creds)

    # Повертаємо на чат, щоб фронтенд міг автоматично повторити POST save-schedule.
    ok = redirect(f'{reverse("chat")}?calendar=connected')
    ok.delete_cookie(_OAUTH_COOKIE, path='/')
    return ok


def _validate_slots_payload(slots) -> tuple:
    """Повертає (ok: bool, errors: dict|None, normalized: list)."""
    if not isinstance(slots, list) or len(slots) == 0:
        return False, {'detail': 'slots має бути непорожнім списком'}, []

    normalized = []
    for i, item in enumerate(slots):
        if not isinstance(item, dict):
            return False, {'detail': f'slots[{i}] має бути об’єктом'}, []
        try:
            dow = int(item['day_of_week'])
            st_s = str(item['start_time'])
            et_s = str(item['end_time'])
        except (KeyError, TypeError, ValueError):
            return False, {'detail': f'Некоректний слот slots[{i}]'}, []

        if dow < 0 or dow > 6:
            return False, {'detail': f'day_of_week поза діапазоном: {dow}'}, []

        try:
            st = datetime.datetime.strptime(st_s, '%H:%M').time()
            et = datetime.datetime.strptime(et_s, '%H:%M').time()
        except ValueError:
            return False, {'detail': f'Некоректний час у slots[{i}]'}, []

        sdt = datetime.datetime.combine(datetime.date.today(), st)
        edt = datetime.datetime.combine(datetime.date.today(), et)
        if et <= st:
            edt += datetime.timedelta(days=1)
        if sdt >= edt:
            return False, {'detail': f'start_time має бути раніше end_time у slots[{i}]'}, []

        normalized.append(
            {
                'day_of_week': dow,
                'start_time': st.strftime('%H:%M'),
                'end_time': et.strftime('%H:%M'),
            }
        )

    total_h = services.total_hours_from_slots_data(normalized)
    if abs(total_h - 12.5) > 0.001:
        return False, {'detail': f'Сума слотів має бути 12.5 год (зараз {total_h:.2f}).'}, []

    return True, None, normalized


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_schedule(request):
    """Зберегти розклад і створити події в Google Calendar."""
    slots = request.data.get('slots')
    goal_title = (request.data.get('goal_title') or '').strip()

    ok, err, normalized = _validate_slots_payload(slots)
    if not ok:
        return Response(err, status=status.HTTP_400_BAD_REQUEST)

    if not GoogleCalendarCredential.objects.filter(user=request.user).exists():
        return Response(
            {'error': 'google_not_connected', 'auth_required': True},
            status=status.HTTP_200_OK,
        )

    try:
        result = services.save_schedule_to_calendar(request.user, normalized, goal_title=goal_title)
    except PermissionError:
        return Response(
            {'error': 'google_not_connected', 'auth_required': True},
            status=status.HTTP_200_OK,
        )

    expected = int(result.get('expected', len(normalized)))
    created = result['created']
    errs = list(result['errors'])

    # Не показуємо «успіх», якщо події реально не створені (раніше могло бути status=ok при created=0).
    if created < expected:
        if not errs:
            errs.append(
                'Події в календар не створені. Перевірте: 1) Google Cloud → увімкнено «Google Calendar API»; '
                '2) увійшли в той самий Google-акаунт, де дивитесь календар (primary).'
            )
        return Response(
            {
                'status': 'partial',
                'created': created,
                'errors': errs,
                'total_hours': 12.5,
            },
            status=status.HTTP_200_OK,
        )

    if errs:
        return Response(
            {
                'status': 'partial',
                'created': created,
                'errors': errs,
                'total_hours': 12.5,
            },
            status=status.HTTP_200_OK,
        )

    return Response(
        {
            'status': 'ok',
            'created': created,
            'total_hours': 12.5,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_schedule(request):
    """Поточний розклад користувача."""
    rows = ScheduleSlot.objects.filter(user=request.user).order_by('day_of_week', 'start_time')
    data = [
        {
            'day_of_week': r.day_of_week,
            'start_time': r.start_time.strftime('%H:%M'),
            'end_time': r.end_time.strftime('%H:%M'),
            'google_event_id': r.google_event_id,
        }
        for r in rows
    ]
    return Response({'slots': data})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_schedule(request):
    """Видалити весь розклад і події Google."""
    try:
        services.delete_all_schedule_events(request.user)
    except Exception as e:
        logger.exception('delete_schedule')
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendar_status(request):
    """Статус підключення Google та кількість слотів."""
    connected = GoogleCalendarCredential.objects.filter(user=request.user).exists()
    rows = ScheduleSlot.objects.filter(user=request.user)
    slots_count = rows.count()
    slots_data = [
        {
            'day_of_week': r.day_of_week,
            'start_time': r.start_time.strftime('%H:%M'),
            'end_time': r.end_time.strftime('%H:%M'),
        }
        for r in rows
    ]
    total_hours = services.total_hours_from_slots_data(slots_data)
    return Response(
        {
            'connected': connected,
            'slots_count': slots_count,
            'total_hours': round(total_hours, 2),
        }
    )


def legacy_google_calendar_schedule(request):
    """
    Сумісність зі старим redirect URI та старим фронтендом:
    GET ?code=… — OAuth callback (якщо в Google Console залишився /api/google-calendar/schedule/).
    POST — те саме, що /api/calendar/save-schedule/.
    """
    drf_request = DRFRequest(request)
    if request.method == 'GET' and request.GET.get('code'):
        return google_oauth_callback(drf_request)
    if request.method == 'POST':
        return save_schedule(drf_request)
    return HttpResponseNotFound(
        'Цей URL більше не використовується без OAuth. '
        'У Google Cloud Console вкажіть redirect: …/api/calendar/oauth/callback/ '
        'і в .env змінну GOOGLE_REDIRECT_URI на той самий URL. '
        'Кнопка «SAVE» має викликати POST /api/calendar/save-schedule/ (оновіть сторінку чату: Ctrl+F5).',
        content_type='text/plain; charset=utf-8',
    )
