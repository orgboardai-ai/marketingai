"""
Логіка Google Calendar API та збереження розкладу.
"""
from __future__ import annotations

import datetime
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import GoogleCalendarCredential, ScheduleSlot

logger = logging.getLogger(__name__)

User = get_user_model()

SCOPES = ['https://www.googleapis.com/auth/calendar']

RRULE_DAYS = {0: 'MO', 1: 'TU', 2: 'WE', 3: 'TH', 4: 'FR', 5: 'SA', 6: 'SU'}


def normalize_token_expiry_for_db(expiry: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    """
    Google OAuth повертає expiry як naive UTC. З USE_TZ=True зберігаємо як aware UTC.
    """
    if expiry is None:
        return None
    if timezone.is_naive(expiry):
        return timezone.make_aware(expiry, datetime.timezone.utc)
    return expiry


def _google_http_error_message(err: HttpError) -> str:
    """Текст помилки Google Calendar API для логів і UI."""
    try:
        raw = err.content.decode('utf-8') if err.content else ''
        data = json.loads(raw) if raw else {}
        err_obj = data.get('error') or {}
        msg = (err_obj.get('message') or '').strip()
        reasons = err_obj.get('errors') or []
        reason_codes = []
        for item in reasons:
            if isinstance(item, dict) and item.get('reason'):
                reason_codes.append(str(item['reason']))
        hint = ''
        blob = ' '.join([msg] + reason_codes).lower()
        if 'has not been used' in blob or 'disabled' in blob or 'accessnotconfigured' in blob.replace('_', ''):
            hint = (
                ' Увімкніть API: Google Cloud Console → APIs & Services → Library → «Google Calendar API» → Enable.'
            )
        if not msg:
            msg = str(err)
        return (msg + hint).strip()
    except Exception:
        return str(err)


def _client_id() -> str:
    return (getattr(settings, 'GOOGLE_CLIENT_ID', '') or getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '') or '').strip()


def _client_secret() -> str:
    return (getattr(settings, 'GOOGLE_CLIENT_SECRET', '') or getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', '') or '').strip()


def get_oauth_flow(
    *,
    redirect_uri: str,
    state: Optional[str] = None,
    scopes: Optional[List[str]] = None,
) -> Flow:
    """
    Повертає Flow для OAuth2 (веб-клієнт з client_secret).
    PKCE вимкнено: інакше після редіректу новий Flow без того самого code_verifier ламає fetch_token.
    """
    cid = _client_id()
    csec = _client_secret()
    if not cid or not csec:
        raise ValueError('Google OAuth не налаштовано (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET).')

    scope_list = list(scopes) if scopes is not None else list(getattr(settings, 'GOOGLE_CALENDAR_SCOPES', SCOPES))

    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': cid,
                'client_secret': csec,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
            }
        },
        scopes=scope_list,
        state=state,
        redirect_uri=redirect_uri,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = redirect_uri
    return flow


def persist_google_calendar_credential(user, creds) -> None:
    """Зберігає або оновлює токени Google (календар) для користувача."""
    scopes_str = ' '.join(creds.scopes) if creds.scopes else ' '.join(SCOPES)
    prev = GoogleCalendarCredential.objects.filter(user=user).first()
    prev_refresh = (prev.refresh_token or '') if prev else ''
    refresh = (creds.refresh_token or prev_refresh or '').strip()

    GoogleCalendarCredential.objects.update_or_create(
        user=user,
        defaults={
            'access_token': creds.token or '',
            'refresh_token': refresh,
            'token_uri': creds.token_uri or 'https://oauth2.googleapis.com/token',
            'token_expiry': normalize_token_expiry_for_db(getattr(creds, 'expiry', None)),
            'client_id': _client_id(),
            'client_secret': _client_secret(),
            'scopes': scopes_str,
        },
    )


def fetch_google_userinfo(access_token: str) -> Optional[Dict[str, Any]]:
    """Профіль з Google (email, sub) за access_token."""
    import requests

    if not (access_token or '').strip():
        return None
    try:
        r = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning('userinfo: %s', e)
        return None


def get_credentials(user) -> Credentials:
    """
    Повертає актуальні Credentials для користувача.
    Якщо access_token прострочений — оновлює через refresh_token.
    """
    try:
        row = GoogleCalendarCredential.objects.get(user=user)
    except GoogleCalendarCredential.DoesNotExist as exc:
        raise PermissionError('Google Calendar не підключено.') from exc

    if not (row.refresh_token or row.access_token):
        raise PermissionError('Google Calendar не підключено.')

    scopes = row.scopes.split() if row.scopes else SCOPES
    creds = Credentials(
        token=row.access_token or None,
        refresh_token=row.refresh_token or None,
        token_uri=row.token_uri or 'https://oauth2.googleapis.com/token',
        client_id=_client_id() or row.client_id or None,
        client_secret=_client_secret() or row.client_secret or None,
        scopes=scopes,
    )
    if row.token_expiry:
        # google-auth порівнює expiry з naive UTC; з БД приходить aware UTC.
        exp = row.token_expiry
        if timezone.is_aware(exp):
            exp = timezone.make_naive(exp, datetime.timezone.utc)
        creds.expiry = exp

    if not creds.valid:
        if not creds.refresh_token:
            row.delete()
            raise PermissionError('Потрібна повторна авторизація Google.')
        try:
            creds.refresh(GoogleRequest())
        except Exception as e:
            logger.warning('RefreshError для user_id=%s: %s', user.pk, e)
            row.delete()
            raise PermissionError('Токен Google застарів. Увійдіть знову.') from e

        row.access_token = creds.token or ''
        try:
            row.token_expiry = normalize_token_expiry_for_db(creds.expiry)
        except Exception:
            row.token_expiry = None
        row.save(update_fields=['access_token', 'token_expiry', 'updated_at'])

    return creds


def get_calendar_service(user):
    """Повертає сервіс Calendar API."""
    creds = get_credentials(user)
    return build('calendar', 'v3', credentials=creds, cache_discovery=False)


def get_next_weekday(day_of_week: int) -> datetime.date:
    """
    Найближча дата з цим днем тижня (0=Пн), включно з сьогодні.
    """
    today = timezone.localdate()
    days_ahead = day_of_week - today.weekday()
    if days_ahead < 0:
        days_ahead += 7
    return today + datetime.timedelta(days=days_ahead)


def _combine_local(d: datetime.date, t: datetime.time) -> datetime.datetime:
    tz = timezone.get_current_timezone()
    return timezone.make_aware(datetime.datetime.combine(d, t), tz)


def _first_event_date(day_of_week: int, start_time: datetime.time) -> datetime.date:
    """Перший день події: якщо сьогодні цей день і час уже минув — наступний тиждень."""
    d = get_next_weekday(day_of_week)
    today = timezone.localdate()
    now_local = timezone.localtime()
    if d == today:
        start_dt = _combine_local(d, start_time)
        if start_dt <= now_local:
            d = d + datetime.timedelta(days=7)
    return d


def create_weekly_event(service, slot: ScheduleSlot, first_date: datetime.date, summary: str) -> str:
    """
    Створює щотижневу подію в Google Calendar.
    Повертає google_event_id.
    """
    tz_name = getattr(settings, 'TIME_ZONE', 'Europe/Kyiv')
    start_dt = _combine_local(first_date, slot.start_time)
    # Якщо end_time "раніше" за start (наприклад 23:30–00:00) — кінець наступного календарного дня
    if slot.end_time <= slot.start_time:
        end_date = first_date + datetime.timedelta(days=1)
        end_dt = _combine_local(end_date, slot.end_time)
    else:
        end_dt = _combine_local(first_date, slot.end_time)

    body: Dict[str, Any] = {
        'summary': summary,
        'description': 'Автоматично додано з MarketingAI.',
        'start': {'dateTime': start_dt.isoformat(), 'timeZone': tz_name},
        'end': {'dateTime': end_dt.isoformat(), 'timeZone': tz_name},
        'recurrence': [f"RRULE:FREQ=WEEKLY;BYDAY={RRULE_DAYS[slot.day_of_week]}"],
        'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 15}]},
    }
    created = service.events().insert(calendarId='primary', body=body).execute()
    eid = created.get('id', '') or ''
    logger.info('Google Calendar: створено подію id=%s summary=%s', eid, summary[:80])
    return eid


def delete_all_schedule_events(user) -> None:
    """Видаляє події в Google та рядки ScheduleSlot."""
    try:
        service = get_calendar_service(user)
    except PermissionError:
        ScheduleSlot.objects.filter(user=user).delete()
        return

    for slot in list(ScheduleSlot.objects.filter(user=user)):
        eid = (slot.google_event_id or '').strip()
        if not eid:
            continue
        try:
            service.events().delete(calendarId='primary', eventId=eid).execute()
        except HttpError as e:
            status_code = getattr(getattr(e, 'resp', None), 'status', None)
            if status_code == 404:
                continue
            logger.warning('HttpError при видаленні події %s: %s', eid, e)
        except Exception as ex:
            logger.warning('Помилка видалення події %s: %s', eid, ex)

    ScheduleSlot.objects.filter(user=user).delete()


def merge_contiguous_slots(slots_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Прибирає дублікати та об'єднує на одному дні тижня послідовні інтервали,
    де кінець попереднього збігається з початком наступного (типові 30-хв слоти).

    Приклад: 06:00–06:30 + 06:30–07:00 + 07:00–07:30 + 07:30–08:00 → одна подія 06:00–08:00;
    розрив (наприклад 08:00 проти 09:00) → окремі події. Менше шуму в Google Calendar,
    зручніше переглядати розклад; загальна кількість годин не змінюється.
    """
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for raw in slots_data:
        key = (int(raw['day_of_week']), str(raw['start_time']), str(raw['end_time']))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(raw)

    buckets: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    for raw in uniq:
        dow = int(raw['day_of_week'])
        st = datetime.datetime.strptime(raw['start_time'], '%H:%M').time()
        et = datetime.datetime.strptime(raw['end_time'], '%H:%M').time()
        sm = st.hour * 60 + st.minute
        em = et.hour * 60 + et.minute
        if em <= sm:
            em += 24 * 60
        buckets[dow].append((sm, em))

    def minutes_to_time(m: int) -> datetime.time:
        m = m % (24 * 60)
        return datetime.time(hour=m // 60, minute=m % 60)

    out: List[Dict[str, Any]] = []
    for dow in sorted(buckets.keys()):
        ivs = sorted(buckets[dow], key=lambda x: x[0])
        cur_s, cur_e = ivs[0]
        for sm, em in ivs[1:]:
            if sm == cur_e:
                cur_e = em
            else:
                out.append(
                    {
                        'day_of_week': dow,
                        'start_time': minutes_to_time(cur_s).strftime('%H:%M'),
                        'end_time': minutes_to_time(cur_e).strftime('%H:%M'),
                    }
                )
                cur_s, cur_e = sm, em
        out.append(
            {
                'day_of_week': dow,
                'start_time': minutes_to_time(cur_s).strftime('%H:%M'),
                'end_time': minutes_to_time(cur_e).strftime('%H:%M'),
            }
        )
    return out


def save_schedule_to_calendar(user, slots_data: List[Dict[str, Any]], goal_title: str = '') -> Dict[str, Any]:
    """
    Видаляє старий розклад, створює нові щотижневі події та ScheduleSlot.
    slots_data: [{'day_of_week': int, 'start_time': 'HH:MM', 'end_time': 'HH:MM'}, ...]
    Суміжні слоти на одному дні об'єднуються в один інтервал перед записом у БД і Calendar.
    """
    errors: List[str] = []
    delete_all_schedule_events(user)

    try:
        service = get_calendar_service(user)
    except PermissionError as e:
        return {'created': 0, 'errors': [str(e)], 'expected': 0}

    merged = merge_contiguous_slots(slots_data)

    summary_base = 'Заняття з AI — MarketingAI'
    if goal_title:
        summary_base = f'Заняття з AI — {goal_title}'

    created = 0
    for raw in merged:
        try:
            dow = int(raw['day_of_week'])
            st = datetime.datetime.strptime(raw['start_time'], '%H:%M').time()
            et = datetime.datetime.strptime(raw['end_time'], '%H:%M').time()
        except (KeyError, ValueError, TypeError) as e:
            errors.append(str(e))
            continue

        slot = ScheduleSlot.objects.create(
            user=user,
            day_of_week=dow,
            start_time=st,
            end_time=et,
        )
        try:
            first = _first_event_date(dow, st)
            eid = create_weekly_event(service, slot, first, summary_base)
            slot.google_event_id = eid
            slot.save(update_fields=['google_event_id'])
            created += 1
        except HttpError as e:
            detail = _google_http_error_message(e)
            errors.append(detail)
            logger.warning('Google Calendar insert HttpError user_id=%s: %s', user.pk, detail)
            slot.delete()
        except Exception as e:
            logger.exception('create_weekly_event')
            errors.append(str(e))
            slot.delete()

    return {'created': created, 'errors': errors, 'expected': len(merged)}


def total_hours_from_slots_data(slots_data: List[Dict[str, Any]]) -> float:
    """Сума тривалості слотів у годинах."""
    total_minutes = 0
    for raw in slots_data:
        try:
            st = datetime.datetime.strptime(raw['start_time'], '%H:%M').time()
            et = datetime.datetime.strptime(raw['end_time'], '%H:%M').time()
        except (KeyError, ValueError, TypeError):
            continue
        sdt = datetime.datetime.combine(datetime.date.today(), st)
        edt = datetime.datetime.combine(datetime.date.today(), et)
        if et <= st:
            edt += datetime.timedelta(days=1)
        delta = edt - sdt
        total_minutes += int(delta.total_seconds() // 60)
    return total_minutes / 60.0
