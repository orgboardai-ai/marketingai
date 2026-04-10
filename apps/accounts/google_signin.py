"""
Вхід і реєстрація одним кліком Google + одразу доступ до Calendar API (без другого OAuth).
"""
import logging
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.core.cache import cache
from django.db import IntegrityError
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_GET
from urllib.parse import urlparse, urlunparse

from apps.billing.models import UserPlan
from apps.calendar_sync import services as cal_services

logger = logging.getLogger(__name__)

SIGNIN_CACHE_PREFIX = 'mkt_gsign:'
SIGNIN_CACHE_TTL = 900


def _signin_cache_key(state: str) -> str:
    return f'{SIGNIN_CACHE_PREFIX}{state}'


def signin_redirect_uri(request) -> str:
    """Має збігатися з Authorized redirect URI для цього флоу в Google Cloud."""
    configured = (getattr(settings, 'GOOGLE_SIGNIN_REDIRECT_URI', '') or '').strip()
    if configured:
        pr = urlparse(configured)
        return urlunparse((pr.scheme, pr.netloc, pr.path, '', '', ''))
    return request.build_absolute_uri(reverse('google_signin_callback'))


def signin_authorization_response(request) -> str:
    configured = (getattr(settings, 'GOOGLE_SIGNIN_REDIRECT_URI', '') or '').strip()
    if configured:
        pr = urlparse(configured)
        qs = request.META.get('QUERY_STRING', '')
        return urlunparse((pr.scheme, pr.netloc, pr.path, '', qs, ''))
    return request.build_absolute_uri()


@require_GET
def google_signin_start(request):
    """Редірект на Google: профіль + календар одним consent."""
    cid = (getattr(settings, 'GOOGLE_CLIENT_ID', '') or '').strip()
    csec = (getattr(settings, 'GOOGLE_CLIENT_SECRET', '') or '').strip()
    if not cid or not csec:
        messages.error(request, 'Google OAuth не налаштовано (GOOGLE_CLIENT_ID / SECRET).')
        return redirect('login')

    next_path = request.GET.get('next')
    if next_path and isinstance(next_path, str) and next_path.startswith('/'):
        request.session['google_signin_next'] = next_path

    try:
        state = secrets.token_urlsafe(32)
        request.session['google_signin_state'] = state
        cache.set(_signin_cache_key(state), 1, SIGNIN_CACHE_TTL)
        ru = signin_redirect_uri(request)
        scopes = list(getattr(settings, 'GOOGLE_FULL_OAUTH_SCOPES', []))
        flow = cal_services.get_oauth_flow(redirect_uri=ru, state=state, scopes=scopes)
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
        )
        return redirect(auth_url)
    except Exception:
        logger.exception('google_signin_start')
        messages.error(request, 'Не вдалося почати вхід через Google.')
        return redirect('login')


@require_GET
def google_signin_callback(request):
    """Callback: користувач + токени календаря, session login."""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    if request.GET.get('error'):
        messages.warning(request, 'Вхід через Google скасовано.')
        return redirect('login')

    state = request.GET.get('state', '')
    code = request.GET.get('code', '')
    session_state = request.session.get('google_signin_state')
    cache_ok = bool(cache.get(_signin_cache_key(state)))
    state_ok = (session_state == state) or cache_ok

    if not code or not state or not state_ok:
        messages.error(request, 'Помилка сесії Google. Спробуйте ще раз.')
        return redirect('login')

    try:
        cache.delete(_signin_cache_key(state))
    except Exception:
        pass
    request.session.pop('google_signin_state', None)

    try:
        ru = signin_redirect_uri(request)
        flow = cal_services.get_oauth_flow(
            redirect_uri=ru,
            state=state,
            scopes=list(getattr(settings, 'GOOGLE_FULL_OAUTH_SCOPES', [])),
        )
        flow.fetch_token(authorization_response=signin_authorization_response(request))
    except Exception:
        logger.exception('google_signin_callback fetch_token')
        messages.error(
            request,
            'Google не підтвердив вхід. Додайте у Console той самий redirect URI, що й GOOGLE_SIGNIN_REDIRECT_URI у .env.',
        )
        return redirect('login')

    creds = flow.credentials
    access = creds.token or ''
    info = cal_services.fetch_google_userinfo(access)
    email = ((info or {}).get('email') or '').strip()
    if not email:
        messages.error(request, 'Google не надав email. Увімкніть доступ до email у вікні Google.')
        return redirect('login')

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        user = User.objects.filter(username__iexact=email).first()

    if user is None:
        uname = email[:150]
        try:
            user = User.objects.create_user(
                username=uname,
                email=email,
                first_name=((info or {}).get('given_name') or '')[:150],
                last_name=((info or {}).get('family_name') or '')[:150],
            )
            user.set_unusable_password()
            user.save()
        except IntegrityError:
            user = User.objects.filter(username__iexact=uname).first() or User.objects.filter(email__iexact=email).first()
            if user is None:
                messages.error(request, 'Не вдалося створити обліковий запис.')
                return redirect('login')
    else:
        # Оновлюємо email і ПІБ з Google при кожному вході (якщо Google їх надав).
        updates = []
        if not user.email:
            user.email = email
            updates.append('email')
        gn = (((info or {}).get('given_name') or '').strip())[:150]
        fn = (((info or {}).get('family_name') or '').strip())[:150]
        if gn and user.first_name != gn:
            user.first_name = gn
            updates.append('first_name')
        if fn and user.last_name != fn:
            user.last_name = fn
            updates.append('last_name')
        if updates:
            user.save(update_fields=updates)

    cal_services.persist_google_calendar_credential(user, creds)
    UserPlan.objects.get_or_create(user=user, defaults={'plan': 'free', 'steps_limit': 3})

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    next_url = request.session.pop('google_signin_next', None)
    if next_url and isinstance(next_url, str) and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('dashboard')
