/**
 * Логіка полінгу чату: кожні 2 секунди запит GET /api/chat/messages/?conversation_id=&after=
 * Використовується також inline у chat.html; цей файл можна підключити для спільних хелперів.
 */
(function () {
  window.ChatPolling = {
    intervalMs: 2000,
    poll: function (conversationId, afterId, onMessages) {
      if (!conversationId || typeof onMessages !== 'function') return;
      var url = '/api/chat/messages/?conversation_id=' + conversationId;
      if (afterId) url += '&after=' + afterId;
      fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(onMessages)
        .catch(function () {});
    },
  };
})();
