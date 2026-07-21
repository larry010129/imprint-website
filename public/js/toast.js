/* 輕量 toast 通知 — loading -> success/error（後台管理共用） */
(function () {
  'use strict';

  var ICONS = {
    loading: '<svg class="ap-toast__spinner" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="42" stroke-dashoffset="14"/></svg>',
    success: '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="currentColor" opacity=".15"/><path d="M7 12.5l3 3 7-7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    error: '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="currentColor" opacity=".15"/><path d="M12 7v6M12 16h.01" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>',
    info: '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="currentColor" opacity=".15"/><path d="M12 8v4M12 16h.01" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>'
  };

  var region = null;
  function ensureRegion() {
    if (region) return region;
    region = document.createElement('div');
    region.className = 'ap-toast-region';
    region.setAttribute('role', 'status');
    region.setAttribute('aria-live', 'polite');
    document.body.appendChild(region);
    return region;
  }

  var toasts = {};
  var seq = 0;

  function esc(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function render(id) {
    var t = toasts[id];
    if (!t) return;
    t.el.className = 'ap-toast ap-toast--' + t.type;
    t.el.innerHTML =
      '<span class="ap-toast__icon">' + (ICONS[t.type] || ICONS.info) + '</span>' +
      '<span class="ap-toast__body">' +
        '<span class="ap-toast__title">' + esc(t.title) + '</span>' +
        (t.description ? '<span class="ap-toast__desc">' + esc(t.description) + '</span>' : '') +
      '</span>' +
      '<button type="button" class="ap-toast__close" aria-label="關閉通知">' +
        '<svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>' +
      '</button>';
    t.el.querySelector('.ap-toast__close').addEventListener('click', function () { dismiss(id); });
  }

  function scheduleAutoDismiss(id) {
    var t = toasts[id];
    if (!t) return;
    clearTimeout(t.timer);
    if (t.duration != null && t.duration !== Infinity) {
      t.timer = setTimeout(function () { dismiss(id); }, t.duration);
    }
  }

  function create(opts) {
    opts = opts || {};
    var id = 'toast-' + (++seq);
    var el = document.createElement('div');
    ensureRegion().appendChild(el);
    toasts[id] = {
      el: el,
      type: opts.type || 'loading',
      title: opts.title || '',
      description: opts.description || '',
      duration: opts.duration === undefined ? 4000 : opts.duration
    };
    render(id);
    requestAnimationFrame(function () { el.classList.add('ap-toast--in'); });
    scheduleAutoDismiss(id);
    return id;
  }

  function update(id, opts) {
    var t = toasts[id];
    if (!t) return;
    opts = opts || {};
    if (opts.type !== undefined) t.type = opts.type;
    if (opts.title !== undefined) t.title = opts.title;
    if (opts.description !== undefined) t.description = opts.description;
    if (opts.duration !== undefined) t.duration = opts.duration;
    render(id);
    scheduleAutoDismiss(id);
  }

  function dismiss(id) {
    var t = toasts[id];
    if (!t) return;
    clearTimeout(t.timer);
    t.el.classList.remove('ap-toast--in');
    t.el.classList.add('ap-toast--out');
    setTimeout(function () {
      t.el.remove();
      delete toasts[id];
    }, 250);
  }

  window.Toast = { create: create, update: update, dismiss: dismiss };

  /* (message, type) shim — matches the calls already present in shop.js */
  window.showToast = window.showToast || function (message, type) {
    return create({ title: message, type: type === 'error' ? 'error' : 'success', duration: 3500 });
  };
})();
