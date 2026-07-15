/**
 * Imprint MVC core — Model-View-Controller helpers for static pages.
 * Views:  partials/views/{member,content}/*.html
 * Models: js/mvc/models/*.js
 * Controllers: js/mvc/controllers/*.js
 */
(function (global) {
  'use strict';

  function escapeHtml(text) {
    var el = document.createElement('span');
    el.textContent = text == null ? '' : String(text);
    return el.innerHTML;
  }

  function formatPrice(n) {
    if (n == null || n === '') return '—';
    return 'NT$ ' + Number(n).toLocaleString('zh-TW', { maximumFractionDigits: 0 });
  }

  function api() {
    return global.imprintAPI;
  }

  function apiBase() {
    return (api() && api().getBase()) || '';
  }

  function t(key, fallback, args) {
    if (global.t) {
      var out = global.t(key, args);
      if (out) return out;
    }
    if (args && fallback && fallback.indexOf('{count}') >= 0) {
      return fallback.replace('{count}', args.count != null ? args.count : '');
    }
    return fallback || key;
  }

  function pageId() {
    return document.body && document.body.getAttribute('data-mvc');
  }

  function isPage(id) {
    return pageId() === id;
  }

  function requireSession(nextPath) {
    var a = api();
    if (!a) return Promise.resolve(null);
    return a.getSession().then(function (res) {
      if (!res || !res.user) {
        global.location.href = 'login.html?next=' + encodeURIComponent(nextPath || global.location.pathname.split('/').pop());
        return null;
      }
      return res;
    });
  }

  function show(el, visible) {
    if (!el) return;
    el.classList.toggle('hidden', !visible);
  }

  function createController(spec) {
    var ctrl = {
      init: function () {
        if (document.readyState === 'loading') {
          document.addEventListener('DOMContentLoaded', spec.run);
        } else {
          spec.run();
        }
      },
    };
    ctrl.init();
    return ctrl;
  }

  global.ImprintMVC = {
    escapeHtml: escapeHtml,
    formatPrice: formatPrice,
    api: api,
    apiBase: apiBase,
    t: t,
    pageId: pageId,
    isPage: isPage,
    requireSession: requireSession,
    show: show,
    createController: createController,
  };
})(window);
