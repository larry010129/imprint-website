/* Inject Imprint text-chat theme into Botpress shadow roots.
   Does NOT replace botpress.init — only styles after chat mounts. */
(function () {
  'use strict';

  var STYLE_ID = 'imprint-botpress-text-chat';
  var CSS_HREF = '/static/css/botpress-text-chat.css?v=4';
  var cssText = null;
  var cssPromise = null;
  var tries = 0;
  var maxTries = 80;
  var pollId = null;

  function loadCss() {
    if (cssText) return Promise.resolve(cssText);
    if (cssPromise) return cssPromise;
    cssPromise = fetch(CSS_HREF, { credentials: 'same-origin', cache: 'no-cache' })
      .then(function (res) {
        if (!res.ok) throw new Error('theme css ' + res.status);
        return res.text();
      })
      .then(function (text) {
        cssText = text;
        return cssText;
      })
      .catch(function () {
        cssPromise = null;
        return null;
      });
    return cssPromise;
  }

  function injectIntoShadow(shadowRoot, text) {
    if (!shadowRoot || !text) return false;
    var existing = shadowRoot.getElementById(STYLE_ID);
    if (existing) {
      if (existing.textContent !== text) existing.textContent = text;
      return true;
    }
    var style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = text;
    shadowRoot.appendChild(style);
    return true;
  }

  function findShadowRoots() {
    var roots = [];
    ['webchat-root', 'fab-root', 'message-preview-root'].forEach(function (id) {
      var host = document.getElementById(id);
      if (host && host.shadowRoot) roots.push(host.shadowRoot);
    });

    var container = document.querySelector('.bpChatContainer');
    if (container) {
      container.querySelectorAll('*').forEach(function (el) {
        if (el.shadowRoot) roots.push(el.shadowRoot);
      });
    }
    return roots;
  }

  function applyTheme() {
    return loadCss().then(function (text) {
      if (!text) return false;
      var applied = false;
      findShadowRoots().forEach(function (root) {
        if (injectIntoShadow(root, text)) applied = true;
      });
      return applied;
    });
  }

  function startPolling() {
    if (pollId) return;
    tries = 0;
    pollId = window.setInterval(function () {
      tries += 1;
      applyTheme().then(function (ok) {
        if (ok || tries >= maxTries) {
          window.clearInterval(pollId);
          pollId = null;
        }
      });
    }, 300);
  }

  function onReady() {
    applyTheme();
    startPolling();
  }

  function bindBotpress() {
    if (!(window.botpress && typeof window.botpress.on === 'function')) return false;
    window.botpress.on('webchat:initialized', onReady);
    window.botpress.on('webchat:opened', function () {
      applyTheme();
    });
    return true;
  }

  if (!bindBotpress()) {
    var waitBp = window.setInterval(function () {
      if (bindBotpress()) {
        window.clearInterval(waitBp);
        onReady();
      }
    }, 300);
    window.setTimeout(function () {
      window.clearInterval(waitBp);
    }, 20000);
  }

  // Light delayed attempts — do not use MutationObserver (can fight Botpress mount)
  window.setTimeout(onReady, 1500);
  window.setTimeout(onReady, 4000);
})();
