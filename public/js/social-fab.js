(function () {
  'use strict';

  var root = document.querySelector('[data-social-fab]');
  if (!root) return;

  function isCheckoutFlowPage() {
    var path = (window.location.pathname || '').toLowerCase();
    return (
      path.indexOf('checkout') !== -1 ||
      path.indexOf('success') !== -1 ||
      path.indexOf('cart') !== -1
    );
  }

  if (isCheckoutFlowPage()) {
    root.hidden = true;
    root.setAttribute('aria-hidden', 'true');
    root.style.display = 'none';
    return;
  }

  var menu = document.getElementById('imprintContactFabMenu');
  var toggle = document.getElementById('imprintContactFabToggle');
  if (!menu || !toggle) return;

  var HOVER_CLOSE_MS = 280;
  var hoverCapable = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  var closeTimer = null;

  if (hoverCapable) root.classList.add('is-hover-mode');

  function setOpen(open) {
    root.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    toggle.setAttribute('aria-label', open ? '關閉聯絡選單' : '開啟聯絡選單');
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
})();
