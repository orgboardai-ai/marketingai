/**
 * Вміст для вузла Code «Підготовка сценарію» (копія в workflow JSON).
 * Вхід: body вебхука від Django.
 */
const b = $input.first().json.body || $input.first().json;
const stageIndex = Math.min(Math.max(parseInt(b.stage_index, 10) || 0, 0), 8);
const qIndex = Math.max(parseInt(b.question_index, 10) || 0, 0);
const event = b.event || 'user_message';
const history = Array.isArray(b.history) ? b.history : [];

const STAGES = [
  { title: 'Інструкція', intro: 'Ми пройдемо 9 етапів маркетингової діагностики. На кожному етапі я поставлю кілька питань; відповідайте чесно — так зможу дати точніші рекомендації. Можна робити паузу: історія чату зберігається, після відновлення інтернету продовжите з того ж місця.', questions: ['Коротко опишіть ваш бізнес за 1–2 речення.', 'Яка головна ціль маркетингу на найближчі 3 місяці?'] },
  { title: 'Продукт', intro: '', questions: ['Що саме ви продаєте (продукт/послуга/підписка)?', 'У чому головна вигода для клієнта?'] },
  { title: 'УТП', intro: '', questions: ['Чим ви принципово відрізняєтесь від конкурентів?', 'Чи можете назвати цифру або факт, що це підтверджує?'] },
  { title: 'Цільова аудиторія', intro: '', questions: ['Хто ваш ідеальний клієнт (роль, розмір бізнесу, гео)?', 'Які болі або завдання він намагається закрити вашим продуктом?'] },
  { title: 'Лінії просування', intro: '', questions: ['Які канали зараз використовуєте (реклама, соцмережі, email, партнерки)?', 'Який канал дає найбільше заявок або продажів?'] },
  { title: 'Успішні дії', intro: '', questions: ['Що з маркетингу спрацювало найкраще за останній рік?', 'Що ви вже пробували і від чого відмовились?'] },
  { title: 'Воронки', intro: '', questions: ['Як виглядає шлях клієнта від першого контакту до оплати?', 'Де найбільше «просідання» конверсії?'] },
  { title: 'Стратегія та запуск', intro: '', questions: ['Який бюджет готові виділяти на маркетинг на місяць?', 'Які 2–3 пріоритетні гіпотези хочете перевірити першими?'] },
  { title: 'Аналіз', intro: '', questions: ['Які метрики відстежуєте зараз (CRM, аналітика)?', 'Що хотіли б бачити в щотижневому звіті по маркетингу?'] },
];

const meta = STAGES[stageIndex] || STAGES[0];

if (event === 'chat_opened') {
  const welcome = `Вітаю! ${meta.intro}\n\n**Етап ${stageIndex + 1}: ${meta.title}**\n\nПерше питання: ${meta.questions[0]}`;
  return [{
    json: {
      skip_llm: true,
      django_payload: {
        conversation_id: b.conversation_id,
        text: welcome,
        sender: 'ai',
        stage_index: stageIndex,
        question_index: 0,
      },
    },
  }];
}

const qi = Math.min(qIndex, meta.questions.length - 1);
const currentQ = meta.questions[qi];
const histText = history.slice(-16).map((h) => `${h.sender}: ${h.text}`).join('\n');
const system = `Ти маркетинговий AI-асистент MarketingAI. Етап: «${meta.title}». Поточне фокус-питання: «${currentQ}». Допоможи користувачу сформулювати відповідь або дай коротку рекомендацію. Українською, 2–6 речень, без води. Якщо відповідь повна — коротко підсумуй і запропонуй наступний крок.`;
const userContent = `Історія (останні повідомлення):\n${histText}\n\nОстаннє від користувача: ${b.text || ''}`;

return [{
  json: {
    skip_llm: false,
    openai_body: {
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: system },
        { role: 'user', content: userContent },
      ],
      temperature: 0.65,
    },
    ctx: {
      conversation_id: b.conversation_id,
      stageIndex,
      qIndex: qi,
      meta,
    },
  },
}];
