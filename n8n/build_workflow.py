"""Генерує marketingai-chat-stages.json для імпорту в n8n."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
prep = (BASE / "prepare-scenario.js").read_text(encoding="utf-8")

after = r"""
const ctx = $('PrepareScenario').first().json.ctx;
const res = $input.first().json;
const text = res.choices && res.choices[0] && res.choices[0].message && res.choices[0].message.content
  ? res.choices[0].message.content
  : 'Не вдалося згенерувати відповідь.';
let nextQ = ctx.qIndex + 1;
let nextStage = ctx.stageIndex;
const len = ctx.meta.questions.length;
if (nextQ >= len) {
  nextQ = 0;
  nextStage = Math.min(ctx.stageIndex + 1, 8);
}
return [{
  json: {
    django_payload: {
      conversation_id: ctx.conversation_id,
      text: text,
      sender: 'ai',
      stage_index: nextStage,
      question_index: nextQ,
    },
  },
}];
""".strip()

workflow = {
    "name": "MarketingAI — етапи та питання",
    "nodes": [
        {
            "parameters": {
                "httpMethod": "POST",
                "path": "marketingai-chat",
                "responseMode": "onReceived",
                "options": {},
            },
            "id": "w1",
            "name": "Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [200, 300],
            "webhookId": "w1hook",
        },
        {
            "parameters": {"jsCode": prep},
            "id": "p1",
            "name": "PrepareScenario",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [440, 300],
        },
        {
            "parameters": {
                "conditions": {
                    "options": {
                        "version": 2,
                        "leftValue": "",
                        "caseSensitive": True,
                        "typeValidation": "loose",
                    },
                    "combinator": "and",
                    "conditions": [
                        {
                            "id": "c1",
                            "operator": {
                                "type": "boolean",
                                "operation": "true",
                                "singleValue": True,
                            },
                            "leftValue": "={{ $json.skip_llm }}",
                            "rightValue": "",
                        }
                    ],
                }
            },
            "id": "i1",
            "name": "IfSkipLLM",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [680, 300],
        },
        {
            "parameters": {
                "method": "POST",
                "url": "https://YOUR-DJANGO/api/chat/response/",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [{"name": "Content-Type", "value": "application/json"}]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify($json.django_payload) }}",
                "options": {},
            },
            "id": "d1",
            "name": "DjangoDirect",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [920, 180],
            "notesInFlow": True,
            "notes": "Підставте URL Django",
        },
        {
            "parameters": {
                "method": "POST",
                "url": "https://api.openai.com/v1/chat/completions",
                "authentication": "genericCredentialType",
                "genericAuthType": "httpHeaderAuth",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [{"name": "Content-Type", "value": "application/json"}]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify($json.openai_body) }}",
                "options": {},
            },
            "id": "o1",
            "name": "OpenAIChat",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [920, 420],
            "notesInFlow": True,
            "notes": "Header Auth: Authorization = Bearer sk-...",
        },
        {
            "parameters": {"jsCode": after},
            "id": "a1",
            "name": "AfterOpenAI",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1160, 420],
        },
        {
            "parameters": {
                "method": "POST",
                "url": "https://YOUR-DJANGO/api/chat/response/",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [{"name": "Content-Type", "value": "application/json"}]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify($json.django_payload) }}",
                "options": {},
            },
            "id": "d2",
            "name": "DjangoFromAI",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [1400, 420],
            "notesInFlow": True,
            "notes": "Той самий ендпоінт",
        },
    ],
    "connections": {
        "Webhook": {"main": [[{"node": "PrepareScenario", "type": "main", "index": 0}]]},
        "PrepareScenario": {"main": [[{"node": "IfSkipLLM", "type": "main", "index": 0}]]},
        "IfSkipLLM": {
            "main": [
                [{"node": "DjangoDirect", "type": "main", "index": 0}],
                [{"node": "OpenAIChat", "type": "main", "index": 0}],
            ]
        },
        "OpenAIChat": {"main": [[{"node": "AfterOpenAI", "type": "main", "index": 0}]]},
        "AfterOpenAI": {"main": [[{"node": "DjangoFromAI", "type": "main", "index": 0}]]},
    },
    "pinData": {},
    "meta": {"templateCredsSetupCompleted": False},
    "settings": {"executionOrder": "v1"},
    "staticData": None,
    "tags": [],
}

(BASE / "marketingai-chat-stages.json").write_text(
    json.dumps(workflow, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("Written marketingai-chat-stages.json")
