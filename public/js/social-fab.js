(function () {
  'use strict';

  var root = document.querySelector('[data-social-fab]');
  if (!root) return;

  var menu = document.getElementById('imprintContactFabMenu');
  var toggle = document.getElementById('imprintContactFabToggle');
  if (!menu || !toggle) return;

  var BP_HIDE_STYLE_ID = 'imprint-hide-botpress-fab';
  var HOVER_CLOSE_MS = 280;
  var hoverCapable = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  var closeTimer = null;

  if (hoverCapable) root.classList.add('is-hover-mode');

  function setOpen(open) {
    root.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    toggle.setAttribute('aria-label', open ? '聯絡選單已展開' : '開啟聯絡選單');
    menu.hidden = !open;
    menu.setAttribute('aria-hidden', open ? 'false' : 'true');
  }

  function cancelScheduledClose() {
    if (closeTimer) {
      window.clearTimeout(closeTimer);
      closeTimer = null;
    }
  }

  function openMenu() {
    cancelScheduledClose();
    setOpen(true);
  }

  function close() {
    cancelScheduledClose();
    setOpen(false);
  }

  function scheduleClose() {
    if (!hoverCapable) return;
    cancelScheduledClose();
    closeTimer = window.setTimeout(function () {
      closeTimer = null;
      setOpen(false);
    }, HOVER_CLOSE_MS);
  }

  function openBotpressChat() {
    if (window.botpress && typeof window.botpress.open === 'function') {
      window.botpress.open();
      return true;
    }
    if (window.botpress && typeof window.botpress.toggle === 'function') {
      window.botpress.toggle();
      return true;
    }
    return false;
  }

  function hideBotpressFab() {
    var shadowRoot = document.querySelector('.bpChatContainer > #fab-root')?.shadowRoot;
    if (!shadowRoot || !shadowRoot.querySelector('.bpFabWrapper')) return false;
    if (shadowRoot.getElementById(BP_HIDE_STYLE_ID)) return true;

    var style = document.createElement('style');
    style.id = BP_HIDE_STYLE_ID;
    style.textContent = [
      '.bpFabWrapper { display: none !important; visibility: hidden !important; pointer-events: none !important; }',
      '@media (max-width: 900px) {',
      '  #message-preview-root {',
      '    bottom: calc(var(--shop-mobile-buy-bar-height, 0px) + 104px) !important;',
      '    visibility: var(--shop-mobile-chat-visibility, visible) !important;',
      '  }',
      '}',
    ].join('\n');
    shadowRoot.appendChild(style);
    return true;
  }

  if (hoverCapable) {
    root.addEventListener('mouseenter', openMenu);
    root.addEventListener('mouseleave', scheduleClose);
    root.addEventListener('focusin', openMenu);
    root.addEventListener('focusout', function (event) {
      if (!root.contains(event.relatedTarget)) scheduleClose();
    });
  } else {
    toggle.addEventListener('click', function () {
      setOpen(!root.classList.contains('is-open'));
    });

    document.addEventListener('click', function (event) {
      if (!root.classList.contains('is-open')) return;
      if (root.contains(event.target)) return;
      close();
    });
  }

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') close();
  });

  menu.querySelectorAll('[data-social-fab-link]').forEach(function (link) {
    link.addEventListener('click', close);
  });

  var chatBtn = menu.querySelector('[data-social-fab-chat]');
  if (chatBtn) {
    chatBtn.addEventListener('click', function () {
      close();
      if (!openBotpressChat()) {
        var tries = 0;
        var poll = window.setInterval(function () {
          tries += 1;
          if (openBotpressChat() || tries > 40) window.clearInterval(poll);
        }, 250);
      }
    });
  }

  hideBotpressFab();
  var hidePoll = window.setInterval(function () {
    if (hideBotpressFab()) window.clearInterval(hidePoll);
  }, 250);
  window.setTimeout(function () {
    hideBotpressFab();
    window.clearInterval(hidePoll);
  }, 15000);

  if (window.botpress && typeof window.botpress.on === 'function') {
    window.botpress.on('webchat:initialized', hideBotpressFab);
  }
})();
