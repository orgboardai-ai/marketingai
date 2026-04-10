# n8n — MarketingAI (етапи, питання, історія)

## Файли

| Файл | Призначення |
|------|-------------|
| **`marketingai-chat-stages.json`** | Імпорт workflow у n8n (основний). |
| **`prepare-scenario.js`** | Логіка етапів і питань (копія всередині JSON; редагуйте тут і перегенеруйте JSON). |
| **`build_workflow.py`** | `python n8n/build_workflow.py` — збирає `marketingai-chat-stages.json` з `prepare-scenario.js`. |

## Що робить workflow

1. **Webhook** `POST …/webhook/marketingai-chat` — приймає JSON від Django (див. нижче).
2. **PrepareScenario** (Code) — масив **9 етапів**, у кожного `intro` + **2 питання** (редагується в `prepare-scenario.js`).
   - `event: chat_opened` → привітання + перше питання **без LLM** (`skip_llm: true`).
   - `user_message` → тіло для **OpenAI** + контекст `history`.
3. **IfSkipLLM** — гілка без LLM → одразу **DjangoDirect**; інакше **OpenAI** → **AfterOpenAI** (оновлення `question_index` / перехід на наступний етап) → **DjangoFromAI**.
4. Обидві гілки викликають **`POST /api/chat/response/`** з полями `conversation_id`, `text`, `sender: ai`, опційно `stage_index`, `question_index`.

## Тіло вебхука (від Django)

```json
{
  "conversation_id": 1,
  "message_id": 12,
  "user_id": 1,
  "text": "…",
  "event": "chat_opened | user_message",
  "stage_index": 0,
  "question_index": 0,
  "bot_active": true,
  "history": [{ "sender": "user", "text": "…" }, { "sender": "ai", "text": "…" }]
}
```

Якщо `bot_active: false`, Django **не викликає** n8n (перехоплення оператором Chatwoot).

## Налаштування після імпорту

1. **OpenAIChat** — credential **Header Auth**: `Authorization` = `Bearer sk-…`.
2. **DjangoDirect** та **DjangoFromAI** — замінити `https://YOUR-DJANGO` на ваш домен (ngrok/Railway).
3. Активувати workflow, скопіювати production URL у `.env`:

   `N8N_WEBHOOK_URL=https://…/webhook/marketingai-chat`

4. У Django: `CSRF_TRUSTED_ORIGINS` / `NGROK_HOST` за потреби.

## Історія та офлайн

Усі повідомлення зберігаються в **Django**; при відкритті чату клієнт завантажує повну історію з `GET /api/chat/messages/?conversation_id=`. Після переривання мережі користувач бачить ту саму переписку.

## Зміна питань

1. Відредагуйте масив `STAGES` у **`prepare-scenario.js`**.
2. Виконайте: `python n8n/build_workflow.py`
3. Імпортуйте оновлений **`marketingai-chat-stages.json`** (або замініть вузол Code у n8n вручну).

## Chatwoot

- Вхідні з сайту й **вихідні від AI** (після відповіді n8n) можна дублювати в Chatwoot з боку Django (див. `views.py`: `_send_to_chatwoot` при `incoming_response`).
- Повідомлення оператора з Chatwoot → webhook → `sender: agent`, **`bot_active = false`** — бот зупиняється, n8n більше не викликається для цієї розмови.
