# Project Context: MarketingAI SaaS

## Project Overview
A SaaS platform where users can chat with an AI agent that creates marketing
automation. Users have free and paid plans.

## Design system (Tailwind CDN, `base.html`)
Токени в `tailwind.config.theme.extend`:
| Токен | Клас (приклад) | HEX |
|--------|----------------|-----|
| ACTION-PRIMARY | `bg-action-primary` | #f9cd1d |
| BRAND-DEEP | `text-brand-deep` | #0f4482 |
| BRAND-MUTED | `bg-brand-muted` | #5873a1 |
| INTERACTIVE | `ring-interactive`, `text-interactive` | #739bd1 |
| SURFACE-MAIN | `bg-surface-main` | #e6eaef |
| SURFACE-CARD | `bg-surface-card` | #aec4e4 |
| NEUTRAL-TEXT | `text-neutral-text` | #78797a |
| BORDER-SOFT | `border-line-soft` | #cbd5e1 |

Тіні: `shadow-soft`, `shadow-floating`, `shadow-card-soft` (картки чату: `0 10px 25px -5px rgba(0,0,0,0.05)`). **Бульбашки чату** (`base.html`): користувач — фон `rgb(15 68 130 / 0.9)`, текст білий; AI/агент (`.chat-bubble-secondary`) — текст `rgb(15 68 130 / 0.9)` на білому. CTA: клас `.ds-btn-cta` (ACTION-PRIMARY + текст BRAND-DEEP; hover — трохи темніший жовтий `#e6b919`, без тіні). «Вихід» у шапці: `hover:!bg-slate-100` замість суцільного `surface-main`. Кнопки DaisyUI `.btn` — без `box-shadow` на hover/active (глобально в `base.html`). Ряди степера в чаті: при hover лише світліший фон, без додаткової тіні; дашборд-картки — `hover:bg-base-200/30` замість `hover:shadow-md`.

**Футер** (`base.html`): фон `bg-brand-deep` (#0f4482); заголовки колонок — білий uppercase; колонкові посилання — `.marketingai-footer-link` (білий 70%, `pb-1` + `border-b` білий при hover/focus/`aria-current`); опис бренду — `text-white/70`; нижня смуга — `border-white/25`, копірайт — `text-sm font-medium text-white` (як правові посилання), праворуч «Умови / Конфіденційність / Cookies» — `.marketingai-footer-legal` та декоративна зірка.

Сторінка **Контакти**: `GET/POST /contacts/`, шаблон `contacts.html` — еталон кабінетської сторінки: `max-w-6xl`, картки `rounded-2xl border-line-soft bg-white shadow-soft`, `h1`/`h2`/`text-brand-deep`/`text-neutral-text`; активна вкладка «Контакти» у навігації: `bg-interactive` / білий текст; графік у таблиці: Пн—Пт + вихідні; дві картки `items-stretch`; кнопка відправки — `.ds-btn-cta` + `bg-action-primary`.

Сторінка **Чат** (`chat.html`): **узгоджено з Контакти** — контейнер `max-w-6xl`, типографіка як у Контактів; картки `rounded-2xl border-line-soft bg-white shadow-soft`; **Нова розмова** (тимчасово для тесту ШІ): кнопка над повідомленнями, якщо `CHAT_ALLOW_NEW_CONVERSATION=1` (за замовчуванням увімкнено при `DEBUG=1`, у проді вимкнено без env); створює новий `Conversation` через `POST /api/chat/message/` без `conversation_id`, `event: chat_opened` — порожня історія для n8n; локально скидаються етап до 0, ціль та вкладка інструкції «Відео»; **етапи**: індекси `0–1` доступні, **`FIRST_LOCKED_STAGE_INDEX = 2`** (етапи 3–9) — замок лише в колі степера (без дубля біля номера), у списку зліва — без кліку; `clampStageIndex()` обмежує `currentStageIndex` до `1`; у списку зліва сітка **`items-start`**, сайдбар **`self-start`**, список **`max-h-[min(70vh,28rem)] overflow-y-auto`** — не розтягується на висоту правої колонки; **пройдений і поточний** етапи в списку та **поточне коло** у степері — **`bg-brand-deep/90`** (`rgb(15 68 130 / 0.9)`) + білий текст; підписи етапів у степері — `text-brand-deep`; **вкладки інструкції** (1–4): активна — `bg-surface-card/60 ring-1 ring-line-soft`; неактивна — `border border-line-soft bg-white shadow-sm`; вимкнена — пунктирна рамка. Контент кроків — **`.marketingai-instr-panels`** без додаткового сірого/білого «ложа»: панелі **`.instr-panel`** лишаються на тлі основної білої картки інструкції (`border-b` у заголовка кроку). Токен `shadow-card-soft` у `tailwind.config` за потреби для інших блоків.

**Навігація** (`base.html`): активний пункт — нижня лінія `border-brand-deep` (без кольорової плашки); ім’я користувача — без білої картки/тіні, `border-l border-line-soft`, `text-neutral-text font-normal`; «Вихід» — `btn btn-sm`, окремо від імені.

### Кабінет: шпаргалка оформлення (нові сторінки як Контакти / Чат)
- **Шаблон**: `{% extends 'base.html' %}`; **контент** — `mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16` (фон сторінки вже `body.bg-surface-main`).
- **Заголовок сторінки**: `h1` — `text-3xl font-bold tracking-tight text-brand-deep sm:text-4xl`; підзаголовок — `mt-3 max-w-2xl text-lg text-brand-deep/90`.
- **Секційні заголовки в картках**: `h2` — `text-xl font-bold text-brand-deep`; допоміжний текст — `text-sm text-neutral-text`.
- **Картка-блок** (основний патерн): `rounded-2xl border border-line-soft bg-white p-6 shadow-soft sm:p-8`. Уникати зайвого «білий–сірий–білий» без потреби (див. чат: `.marketingai-instr-panels`).
- **Рамки / розділювачі**: `border-line-soft`; легкий внутрішній акцент — `bg-surface-main/25` … `bg-surface-main/35` (не дублювати повну білу картку всередині білої).
- **Тіні**: картки сторінки — `shadow-soft`; дуже легка глибина для вкладених елементів — `shadow-sm` або `shadow-card-soft` точково.
- **Кнопка відправки / головний CTA у формі**: `btn` + `ds-btn-cta` + `bg-action-primary` + `text-brand-deep` (жовтий фон, темно-синій текст; hover задає `.ds-btn-cta` у `base.html`).
- **Кнопка вторинна / небезпечна**: як у чаті — `btn rounded-md border-0 bg-brand-deep text-white hover:brightness-110` або `text-red-500` для «очистити»; **не** покладатися на дефолтний сірий hover DaisyUI для жовтих CTA.
- **Поля вводу**: `input input-bordered` + `rounded-md` або `rounded-xl` + `border-line-soft bg-white text-brand-deep/90 placeholder:text-neutral-text/60` + `focus:border-brand-deep focus:outline-none focus:ring-2 focus:ring-interactive/40`.
- **Посилання в контенті кабінету**: `text-neutral-text hover:text-brand-deep` (або `transition-colors`).
- **Пігулки навігації в шапці** (еталон у `base.html`): неактивна — `text-sm text-neutral-text hover:text-brand-deep`; активна для більшості пунктів — `font-semibold text-brand-deep bg-surface-card/60 ring-1 ring-line-soft`; **виняток «Контакти»** — `font-semibold text-white bg-interactive ring-1 ring-interactive shadow-sm`.
- **Вкладки всередині сторінки** (як кроки інструкції в чаті): активна — `font-semibold text-brand-deep bg-surface-card/60 ring-1 ring-line-soft`; неактивна — `border border-line-soft bg-white shadow-sm` + hover на рамку/тінь; вимкнена — пунктир + `opacity-60` (логіка в `chat.html`, `_setTabButtonState`).
- **Футер**: не змішувати з кабінетом — окремі класи `.marketingai-footer-link` та правові посилання (див. `base.html`).

## Tech Stack
- Backend: Django 5.x + Django REST Framework
- Frontend: Django Templates + Tailwind CSS + DaisyUI
- Database: PostgreSQL
- Payments: WayForPay (Ukrainian payment system)
- Hosting: Railway
- Integrations: n8n (AI agent), Chatwoot (CRM/live chat monitoring)

## App Structure
```
marketingai/
├── marketingai/          # project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/         # registration, login, Google sign-in (профіль+calendar)
│   ├── chat/             # chat with AI agent, polling, webhooks
│   ├── billing/          # WayForPay plans and payments
├── templates/
│   ├── base.html         # navigation, footer, Tailwind + DaisyUI
│   ├── home.html         # landing page
│   ├── pricing.html
│   ├── dashboard.html
│   └── chat.html
├── static/
│   ├── css/
│   └── js/
│       └── chat.js       # polling logic
└── requirements.txt
```

## Database Models

### UserPlan
- user (OneToOne → User)
- plan: choices = [free, basic, pro]
- steps_used (int, default 0)
- steps_limit (int, default 3 for free)
- wayforpay_order_id (str)

### Conversation
- user (FK → User)
- chatwoot_conversation_id (int, nullable)
- created_at

### Message
- conversation (FK → Conversation)
- sender: choices = [user, ai, agent]
- text (TextField)
- created_at

## Pricing Plans (in euros)
- Free: розробка продукту, безкоштовно, 3 кроки
- Basic: 4 кроки, 300 євро одноразово
- Pro: 9 кроків, 990 євро одноразово

## Home Page Design (home.html)
Точно відтворити наступний дизайн:

### Кольори
- Фон hero секції: #F5F0E8 (світло-бежевий/кремовий)
- Кнопка "Спробувати безкоштовно": жовта (#F5C842), чорний текст, rounded-full
- Кнопка "Переглянути відео": біла з чорною рамкою, rounded-full
- Посилання "Як це працює →": простий текст без рамки
- Іконки карток: сині квадрати з rounded corners
- Фон можливостей: світло-блакитний (#EBF5FF)
- Фон відгуків: білий
- Фон цін: білий
- Фон footer: темно-синій (#1a2b4a)

### Навігація (base.html)
- Зліва: логотип (синя іконка робота + "MarketingAI" текст)
- По центру/праворуч: Можливості | Відгуки | Блог | Ціни
- Крайній правий: кнопка "Увійти" синя, rounded-full
- Фон навігації: білий, тонка тінь знизу

### Hero секція
- Фон: #F5F0E8 (кремовий), великий відступ зверху і знизу
- Заголовок: "Marketing AI System" жирний, великий (~4xl), по центру
- Підзаголовок: "Ваш персональний AI-асистент з маркетингу для стабільного та прогнозованого прибутку" — сірий текст, по центру
- Три кнопки в ряд по центру:
  1. "Спробувати безкоштовно" — жовта, rounded-full
  2. "Переглянути відео" — біла з рамкою, rounded-full
  3. "Як це працює →" — текст без рамки

### Секція карток (3 колонки)
- Фон: #F5F0E8 (той самий кремовий)
- Три картки з білим фоном, rounded-xl, легка тінь
- Кожна картка має:
  - Іконка: синій квадрат з rounded corners зверху зліва
  - Заголовок великими літерами: ДІАГНОСТИКА / ПЛАН ДІЙ / КОНСУЛЬТАЦІЯ
  - Опис сірим текстом
- ДІАГНОСТИКА: "Глибокий аналіз маркетингових воронок та виявлення прихованих точок росту за допомогою AI"
- ПЛАН ДІЙ: "Покрокова карта впровадження змін для масштабування вашого бізнесу на основі даних"
- КОНСУЛЬТАЦІЯ: "Супровід від експертів у налаштуванні системи для отримання стабільних результатів"

### Секція МОЖЛИВОСТІ
- Заголовок "МОЖЛИВОСТІ" по центру, жирний
- Світло-блакитний фон (#EBF5FF)
- 4 пункти у 2 колонки, кожен з синьою галочкою в колі зліва:
  - Автоматична генерація контент-плану
  - Аналіз конкурентів за 30 секунд
  - Створення текстів для реклами
  - Підбір каналів просування під вашу нішу

### Секція ВІДГУКИ
- Заголовок "ВІДГУКИ" по центру, жирний
- Білий фон
- 3 картки відгуків з тінню:
  - Картка 1: ★★★★★ "Ця система замінила мені SMM менеджера. Дуже зручно!" — Олена, власниця кав'ярні
  - Картка 2: ★★★★★ "Чіткий план дій, без води. Результат відчув за тиждень." — Ігор, автосервіс
  - Картка 3: ★★★★☆ "Зекономила 500 євро на консультаціях. Рекомендую." — Марія, онлайн-курси

### Секція ЦІНИ
- Заголовок "ЦІНИ" по центру, жирний
- 3 картки в ряд:
  - Безкоштовно: підзаголовок "РОЗРОБКА ПРОДУКТУ", текст "Безкоштовно"
  - 300 євро: підзаголовок "4 КРОКИ", текст "300 євро" — виділена синьою рамкою (активний план)
  - 990 євро: підзаголовок "9 КРОКІВ", текст "990 євро"

### Footer
- Фон: темно-синій (#1a2b4a), білий текст
- Зліва: логотип + "Інноваційні рішення для маркетингу на основі штучного інтелекту"
- 4 колонки посилань:
  - Продукт: Можливості, Ціни, Відгуки
  - Компанія: Блог, Про нас, Кар'єра
  - Підтримка: Довідка, Чат, Контакти
  - Правові: Умови використання, Конфіденційність
- Знизу: "© 2026 MarketingAI. Всі права захищені."

## Architecture: Chat Flow

### User sends message:
1. Browser → POST /api/chat/message/ (Django DRF)
2. Django saves message to DB (status: pending)
3. Django simultaneously sends to:
   a. Chatwoot API → creates incoming message (so human agents can monitor)
   b. n8n webhook → AI processes the message

### n8n workflow (імпорт)
- Готовий JSON: **`n8n/marketingai-chat-stages.json`** (9 етапів, питання в Code; збірка: `python n8n/build_workflow.py`).
- Інструкції: **`n8n/README.md`**.

### n8n responds:
1. n8n AI agent generates response
2. n8n simultaneously sends to:
   a. Chatwoot API → creates outgoing message
   b. POST /api/chat/response/ → Django saves to DB

### User sees response:
- Browser polls GET /api/chat/messages/?after={lastMessageId} every 2 seconds
- New messages appear in chat UI

### Human agent replies in Chatwoot:
- Chatwoot sends webhook → POST /api/chatwoot-webhook/
- Django saves message (sender='agent') to DB
- User sees it via polling

## Key API Endpoints (DRF)
- POST /api/chat/message/         ← user sends message або event `chat_opened` (без тексту в БД)
- GET  /api/chat/conversation/<id>/ ← стан етапу (GET) / синхронізація етапу (PATCH `stage_index`)
- POST /api/chat/response/        ← n8n sends AI response (+ опційно `stage_index`, `question_index`)
- GET  /api/chat/messages/        ← polling; без `after` — повна історія (відновлення після офлайну)
- POST /api/chatwoot-webhook/     ← Chatwoot webhook handler
- POST /api/billing/checkout/     ← create WayForPay payment
- POST /api/billing/webhook/      ← WayForPay webhook handler

### Google — вхід і календар одним кроком
- GET  /accounts/google/start/?next=/…   ← редірект на Google (openid + profile + email + calendar)
- GET  /accounts/google/callback/        ← створення/пошук User, `GoogleCalendarCredential`, `login()`, `UserPlan`
- У Google Cloud → OAuth client додати **другий** Authorized redirect URI: `…/accounts/google/callback/` (як у `GOOGLE_SIGNIN_REDIRECT_URI`)

### Google Calendar (`/api/calendar/`) — лише для користувачів без повного Google-входу
- GET  /api/calendar/oauth/start/     ← JSON `{ "auth_url": "..." }` (IsAuthenticated)
- GET  /api/calendar/oauth/callback/  ← OAuth redirect (AllowAny; user з сесії)
- POST /api/calendar/save-schedule/   ← зберегти 12,5 год слотів + події в Google Calendar
- GET  /api/calendar/schedule/          ← поточний розклад з БД
- DELETE /api/calendar/schedule/delete/ ← видалити розклад і події
- GET  /api/calendar/status/          ← підключено Google / кількість слотів

## Regular Django Views (HTML pages)
- / → home.html
- /pricing → pricing.html
- /dashboard → dashboard.html
- /chat → chat.html
- /login → login.html (кнопка «Продовжити з Google»)
- /register → register.html
- /accounts/google/start|callback → вхід/реєстрація через Google + календар
- /billing → billing.html

## WayForPay Integration
- Library: wayforpay (pip install wayforpay)
- Flow:
  1. User clicks "Купити план"
  2. Django creates WayForPay payment form with HMAC signature
  3. User redirected to WayForPay payment page
  4. After payment WayForPay sends webhook to /api/billing/webhook/
  5. Django verifies signature and updates UserPlan
- Required env vars: WAYFORPAY_MERCHANT_ACCOUNT, WAYFORPAY_MERCHANT_SECRET

## Environment Variables
```
SECRET_KEY=
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
# ngrok / CSRF (один з варіантів):
NGROK_HOST=xxxx.ngrok-free.dev
# або CSRF_TRUSTED_ORIGINS=https://xxxx.ngrok-free.dev
# або файл .ngrok-host (один рядок — домен)
# продакшен за reverse proxy:
# BEHIND_PROXY=1
DATABASE_URL=
N8N_WEBHOOK_URL=
CHATWOOT_API_TOKEN=
CHATWOOT_BASE_URL=
CHATWOOT_ACCOUNT_ID=
CHATWOOT_INBOX_ID=
WAYFORPAY_MERCHANT_ACCOUNT=
WAYFORPAY_MERCHANT_SECRET=
WAYFORPAY_CURRENCY=EUR
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/calendar/oauth/callback/
GOOGLE_SIGNIN_REDIRECT_URI=http://localhost:8000/accounts/google/callback/
```

## Important Decisions
- Polling every 2 seconds (not WebSocket) for simplicity
- Django is the central hub — Chatwoot and n8n are independent receivers
- n8n handles both AI response AND sending to Chatwoot (not Django)
- One-time payments (not subscriptions) via WayForPay
- Templates use base.html inheritance — navigation updated in one place
- All AI logic lives in n8n, Django only stores and serves data
- No Celery or Redis needed — architecture is synchronous

## Coding Standards
- Each Django app has: models.py, views.py, urls.py, serializers.py, admin.py
- Register all models in admin.py
- Use environment variables for all secrets (never hardcode)
- Write code comments in Ukrainian
- All API endpoints must return proper HTTP status codes
- Handle errors gracefully with try/except

## Current Status
- [ ] Project initialized
- [ ] Models created
- [x] Auth: логін/реєстрація + Google (профіль+calendar одним OAuth)
- [ ] home.html created with exact design
- [ ] Chat page and polling working
- [x] Крок 4: розклад 12,5 год, сітка h-8; виділення прямокутника слотів одним перетягуванням (pointer + elementFromPoint); шапка: блок «ПІБ + Вихід» зліва від розділювача
- [x] Google: sign-in (`GOOGLE_SIGNIN_REDIRECT_URI`) + `calendar_sync` / save-schedule; окремий OAuth календаря для користувачів з паролем; ngrok; аліас `/api/google-calendar/schedule/`; на головній — лише «Спробувати безкоштовно»; одна кнопка «Продовжити з Google» на логіні та реєстрації (include); у шапці для залогіненого — прізвище та ім’я з профілю (оновлення з Google при вході)
- [x] Google Calendar: суміжні 30-хв слоти на один день тижня об’єднуються в одну щотижневу подію перед insert (`merge_contiguous_slots`)
- [x] Дизайн-система в `base.html` (токени + тіні + `.ds-btn-cta`); сторінка Контакти `/contacts/`; навігація та футер на токенах; тости + Django messages; сторінка Чат узгоджена з Контакти; етапи 3–9 з замком, лише 1–2 інтерактивні; сайдбар етапів `items-start` + скрол списку; пройдений/поточний — `bg-brand-deep` у списку та степері; степер, інструкції, розклад, бульбашки; без агресивних тіней на hover у CTA та `.btn` DaisyUI; кнопка «Нова розмова» для тесту агента (`CHAT_ALLOW_NEW_CONVERSATION`, новий `Conversation`)
- [ ] n8n webhook connected
- [ ] Chatwoot connected
- [ ] WayForPay payments working
- [ ] Deployed to Railway
