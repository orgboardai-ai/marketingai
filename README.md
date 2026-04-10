# MarketingAI

SaaS-платформа: чат з AI-агентом для маркетингової автоматизації, тарифи та оплата через WayForPay.

## Швидкий старт

```bash
# Віртуальне середовище та залежності
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt

# Змінні середовища: скопіюйте .env.example в .env та заповніть
copy .env.example .env

# Міграції та сервер
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Відкрийте [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

## Доступ з інтернету (ngrok)

1. Запустіть Django: `python manage.py runserver 0.0.0.0:8000`
2. У іншому терміналі: `ngrok http 8000`
3. У `.env` вкажіть хост з ngrok (**без** `https://`):

   ```env
   NGROK_HOST=ваш-піддомен.ngrok-free.dev
   ```

   Або створіть файл **`.ngrok-host`** у корені проєкту — один рядок з тим самим доменом (див. `.ngrok-host.example`).

4. Перезапустіть `runserver`, щоб підхопив `.env` / `.ngrok-host`.

У режимі `DEBUG` у `settings` уже дозволені домени `*.ngrok-free.*`, увімкнено `SECURE_PROXY_SSL_HEADER` для коректного CSRF за HTTPS.

## Документація проєкту

Усі деталі дизайну, API, інтеграцій та поточний статус — у **[CONTEXT.md](CONTEXT.md)**.

## Правила для AI

У корені проєкту є **.cursorrules** та **.cursor/rules/context.mdc** — перед змінами читайте CONTEXT.md.
