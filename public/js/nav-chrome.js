/* SSR nav chrome — mobile drawer + account menu (HTMX loads account HTML). */
(function () {
  'use strict';

  function setupNav(root) {
    var burger = root.querySelector('[data-nav-burger]');
    var mobile = root.querySelector('[data-mobile-nav]');
    if (burger && mobile) {
      var setMobileOpen = function (open) {
        root.classList.toggle('is-mobile-menu-open', open);
        mobile.classList.toggle('is-open', open);
        burger.classList.toggle('is-open', open);
        burger.setAttribute('aria-expanded', open ? 'true' : 'false');
        burger.setAttribute('aria-label', open ? '關閉選單' : '開啟選單');
        mobile.setAttribute('aria-hidden', open ? 'false' : 'true');
        document.body.style.overflow = open ? 'hidden' : '';
      };
      burger.addEventListener('click', function () {
        setMobileOpen(!root.classList.contains('is-mobile-menu-open'));
      });
      mobile.addEventListener('click', function (e) {
        if (e.target.closest('a') || e.target.closest('button.account-menu-item')) {
          setMobileOpen(false);
        }
      });
      var mq = window.matchMedia('(min-width: 901px)');
      mq.addEventListener('change', function () {
        if (mq.matches) setMobileOpen(false);
      });
    }

    var isHome = document.body.classList.contains('page-home');
    if (isHome) {
      /* Prefer [data-site-nav-root] (site-chrome); fallback parent for older markup */
      var heroRoot = root.closest('[data-site-nav-root]') || root.parentElement;
      if (heroRoot) heroRoot.classList.add('is-nav-hero');
      var onScroll = function () {
        document.body.classList.toggle('is-nav-scrolled', window.scrollY > 16);
      };
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
    } else {
      var onScroll2 = function () {
        root.classList.toggle('is-scrolled', window.scrollY > 10);
      };
      window.addEventListener('scroll', onScroll2, { passive: true });
      onScroll2();
    }
  }

  function setupAccountMenus(scope) {
    (scope || document).querySelectorAll('[data-account-menu]').forEach(function (menu) {
      if (menu.dataset.bound) return;
      menu.dataset.bound = '1';
      var toggle = menu.querySelector('[data-account-toggle]');
      var panel = menu.querySelector('[data-account-panel]');
      if (!toggle || !panel) return;
      toggle.addEventListener('click', function () {
        var open = panel.hasAttribute('hidden');
        if (open) panel.removeAttribute('hidden');
        else panel.setAttribute('hidden', '');
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
      document.addEventListener('mousedown', function (e) {
        if (!menu.contains(e.target)) {
          panel.setAttribute('hidden', '');
          toggle.setAttribute('aria-expanded', 'false');
        }
      });
    });
  }

  document.querySelectorAll('[data-site-nav]').forEach(setupNav);
  setupAccountMenus(document);
  document.body.addEventListener('htmx:afterSwap', function (e) {
    setupAccountMenus(e.target);
  });
})();
