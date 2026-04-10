/**
 * Спливаючі сповіщення (toast) у правому верхньому куті.
 * Виклик: window.marketingaiToast({ message: 'Текст', type: 'success'|'error'|'warning'|'info' })
 */
(function () {
  'use strict';

  var DEFAULT_MS = 5200;
  var HOST_ID = 'marketingai-toast-host';

  function ensureHost() {
    var el = document.getElementById(HOST_ID);
    if (el) return el;
    el = document.createElement('div');
    el.id = HOST_ID;
    el.className =
      'fixed top-4 right-4 z-[200] flex flex-col gap-2 w-[min(380px,calc(100vw-2rem))] pointer-events-none';
    el.setAttribute('aria-live', 'polite');
    document.body.appendChild(el);
    return el;
  }

  var TYPE_STYLES = {
    success: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    error: 'border-red-200 bg-red-50 text-red-900',
    warning: 'border-amber-200 bg-amber-50 text-amber-950',
    info: 'border-sky-200 bg-sky-50 text-sky-950',
  };

  function marketingaiToast(options) {
    var opts = options || {};
    var message = String(opts.message != null ? opts.message : '').trim();
    if (!message) return;

    var type = TYPE_STYLES[opts.type] ? opts.type : 'info';
    var ms = opts.durationMs != null ? Number(opts.durationMs) : DEFAULT_MS;
    if (ms < 1500) ms = 1500;

    var host = ensureHost();
    var toast = document.createElement('div');
    toast.className =
      'marketingai-toast-animate pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-lg ' +
      (TYPE_STYLES[type] || TYPE_STYLES.info);
    toast.setAttribute('role', 'status');

    var text = document.createElement('p');
    text.className = 'flex-1 leading-snug break-words';
    text.textContent = message;

    var closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className =
      'shrink-0 rounded-lg p-1 text-current opacity-60 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-blue-400';
    closeBtn.setAttribute('aria-label', 'Закрити');
    closeBtn.innerHTML =
      '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>';

    function removeToast() {
      if (!toast.parentNode) return;
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(12px)';
      toast.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
      setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 220);
    }

    toast.appendChild(text);
    toast.appendChild(closeBtn);
    host.appendChild(toast);

    var t = setTimeout(removeToast, ms);
    closeBtn.addEventListener('click', function () {
      clearTimeout(t);
      removeToast();
    });
  }

  window.marketingaiToast = marketingaiToast;
})();
