"""
Налаштування проєкту MarketingAI.
Усі секрети беруться з змінних середовища.
"""


import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

DEBUG = os.environ.get('DEBUG', '1') == '1'

# Кнопка «Нова розмова» на /chat/ (новий Conversation — порожня історія для n8n). У проді: CHAT_ALLOW_NEW_CONVERSATION=0
CHAT_ALLOW_NEW_CONVERSATION = os.environ.get(
    'CHAT_ALLOW_NEW_CONVERSATION',
    '1' if DEBUG else '0',
) == '1'


def _normalize_host_header_value(val):
    """З env часто кладуть https://host/ — для ALLOWED_HOSTS потрібен лише host."""
    val = (val or '').strip()
    for prefix in ('https://', 'http://'):
        if val.lower().startswith(prefix):
            val = val[len(prefix) :]
    val = val.split('/')[0].split('?')[0].strip()
    return val


def _allowed_hosts_list():
    """localhost + ALLOWED_HOSTS з env + опційно NGROK_HOST або рядок у .ngrok-host."""
    raw = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1')
    hosts = [h.strip() for h in raw.split(',') if h.strip()]
    ngrok = _normalize_host_header_value(os.environ.get('NGROK_HOST', ''))
    if ngrok and ngrok not in hosts:
        hosts.append(ngrok)
    ngrok_file = BASE_DIR / '.ngrok-host'
    if ngrok_file.is_file():
        try:
            line = _normalize_host_header_value(ngrok_file.read_text(encoding='utf-8').splitlines()[0])
            if line and not line.startswith('#') and line not in hosts:
                hosts.append(line)
        except OSError:
            pass
    return hosts


def _csrf_trusted_origins():
    """
    Origins для CSRF при POST через HTTPS (ngrok тощо).
    Беремо GOOGLE_REDIRECT_URI, ALLOWED_HOSTS і опційно CSRF_TRUSTED_ORIGINS з env.
    """
    out = ['http://localhost:8000', 'http://127.0.0.1:8000']
    for env_key in ('GOOGLE_REDIRECT_URI', 'GOOGLE_SIGNIN_REDIRECT_URI'):
        redirect = (os.environ.get(env_key, '') or '').strip()
        if redirect:
            p = urlparse(redirect)
            if p.scheme and p.netloc:
                origin = f'{p.scheme}://{p.netloc}'
                if origin not in out:
                    out.append(origin)
    extra = (os.environ.get('CSRF_TRUSTED_ORIGINS', '') or '').strip()
    if extra:
        for part in extra.split(','):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    for host in _allowed_hosts_list():
        if host in ('localhost', '127.0.0.1'):
            continue
        for scheme in ('https', 'http'):
            origin = f'{scheme}://{host}'
            if origin not in out:
                out.append(origin)
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


ALLOWED_HOSTS = _allowed_hosts_list()

CSRF_TRUSTED_ORIGINS = _csrf_trusted_origins()

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'apps.accounts',
    'apps.chat',
    'apps.billing',
    'apps.calendar_sync',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'marketingai.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'marketingai.wsgi.application'

# PostgreSQL з DATABASE_URL (формат Railway: postgres://...)
_db_url = os.environ.get('DATABASE_URL')
if _db_url:
    import re
    _db_url = re.sub(r'^postgres://', 'postgresql://', _db_url)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'OPTIONS': {'options': '-c search_path=public'},
        }
    }
    try:
        import dj_database_url
        DATABASES['default'] = dj_database_url.parse(_db_url)
    except ImportError:
        from urllib.parse import urlparse
        u = urlparse(_db_url)
        DATABASES['default'].update({
            'NAME': u.path[1:] if u.path else 'marketingai',
            'USER': u.username or '',
            'PASSWORD': u.password or '',
            'HOST': u.hostname or 'localhost',
            'PORT': u.port or '5432',
        })
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uk'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# Не вимагати автентифікацію для публічних ендпоінтів — перевизначається у views
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Інтеграції (з env)
N8N_WEBHOOK_URL = os.environ.get('N8N_WEBHOOK_URL', '')
CHATWOOT_API_TOKEN = os.environ.get('CHATWOOT_API_TOKEN', '')
CHATWOOT_BASE_URL = os.environ.get('CHATWOOT_BASE_URL', '').rstrip('/')
CHATWOOT_ACCOUNT_ID = os.environ.get('CHATWOOT_ACCOUNT_ID', '')
CHATWOOT_INBOX_ID = os.environ.get('CHATWOOT_INBOX_ID', '')

# WayForPay
WAYFORPAY_MERCHANT_ACCOUNT = os.environ.get('WAYFORPAY_MERCHANT_ACCOUNT', '')
WAYFORPAY_MERCHANT_SECRET = os.environ.get('WAYFORPAY_MERCHANT_SECRET', '')
WAYFORPAY_CURRENCY = os.environ.get('WAYFORPAY_CURRENCY', 'EUR')

# Google OAuth2 (Calendar) — основні ключі з .env
GOOGLE_CLIENT_ID = (os.environ.get('GOOGLE_CLIENT_ID', '') or os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')).strip()
GOOGLE_CLIENT_SECRET = (os.environ.get('GOOGLE_CLIENT_SECRET', '') or os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')).strip()
GOOGLE_REDIRECT_URI = os.environ.get(
    'GOOGLE_REDIRECT_URI',
    'http://localhost:8000/api/calendar/oauth/callback/',
)
GOOGLE_SIGNIN_REDIRECT_URI = os.environ.get(
    'GOOGLE_SIGNIN_REDIRECT_URI',
    'http://localhost:8000/accounts/google/callback/',
)
GOOGLE_CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']
# Один consent: профіль + календар (реєстрація/вхід без другого OAuth для слотів).
GOOGLE_FULL_OAUTH_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/calendar',
]

# Ngrok / reverse proxy: коректний https у request.build_absolute_uri() (OAuth redirect_uri).
_trust_proxy = (
    os.environ.get('TRUST_X_FORWARDED_SSL', '').strip().lower() in ('1', 'true', 'yes')
    or bool(_normalize_host_header_value(os.environ.get('NGROK_HOST', '')))
)
_https_oauth = GOOGLE_REDIRECT_URI.lower().startswith('https://') or (
    (GOOGLE_SIGNIN_REDIRECT_URI or '').lower().startswith('https://')
)
if _trust_proxy or _https_oauth:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
# Secure cookies лише за явного тунелю — інакше зламається вхід на http://localhost при https у .env.
if _trust_proxy:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Аліаси для коду, що ще читає старі імена
GOOGLE_OAUTH_CLIENT_ID = GOOGLE_CLIENT_ID
GOOGLE_OAUTH_CLIENT_SECRET = GOOGLE_CLIENT_SECRET
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
