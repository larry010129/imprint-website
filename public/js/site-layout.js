/* Component layout — applies nav active state after baked-in partials.
   Partials are inlined by: npm run build:layout
   If data-site-include slots remain (dev), fetches partials over HTTP. */
(function () {
  'use strict';

  var PARTIALS = {
    'layout-topbar': 'partials/layout/topbar.html',
    'layout-nav': 'partials/layout/nav.html',
    'layout-footer': 'partials/layout/footer.html',
    'layout-head': 'partials/layout/head-common.html',
    'view-home': 'partials/views/content/home-main.html',
    'view-price-ref': 'partials/views/content/price-reference.html',
    'view-gold-price': 'partials/views/content/gold-price.html',
    'view-cart': 'partials/views/member/cart.html',
    'view-favorites': 'partials/views/member/favorites.html',
    'view-notifications': 'partials/views/member/notifications.html',
    'view-history': 'partials/views/member/history.html',
    'view-success': 'partials/views/member/success.html',
    'view-profile': 'partials/views/member/profile.html',
    'view-login': 'partials/views/member/login.html',
    'view-register': 'partials/views/member/register.html',
    'view-account': 'partials/views/member/account.html',
    'view-track-order': 'partials/views/member/track-order.html',
    'view-reset-password': 'partials/views/member/reset-password.html',
    'view-contact-form': 'partials/views/member/contact-form.html',
    'view-404': 'partials/views/member/error-404.html',
    topbar: 'partials/layout/topbar.html',
    nav: 'partials/layout/nav.html',
    footer: 'partials/layout/footer.html',
    'head-common': 'partials/layout/head-common.html',
    'home-main': 'partials/views/content/home-main.html',
  };

  function siteRoot() {
    var body = document.body;
    if (body && body.dataset.siteRoot != null) return body.dataset.siteRoot;
    var script = document.currentScript;
    if (script && script.dataset.siteRoot != null) return script.dataset.siteRoot;
    return '';
  }

  function applyRoot(html, root) {
    return html.split('{{ROOT}}').join(root);
  }

  function inject(el, html) {
    if (el.tagName.toLowerCase() === 'head') {
      el.insertAdjacentHTML('beforeend', html);
      el.removeAttribute('data-site-include');
      return;
    }
    el.outerHTML = html;
  }

  function loadPartial(name) {
    return fetch(siteRoot() + PARTIALS[name], { credentials: 'same-origin' })
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to load partial: ' + name);
        return res.text();
      })
      .then(function (html) {
        return applyRoot(html, siteRoot());
      });
  }

  function applyNavActive() {
    var body = document.body;
    if (!body || !body.dataset.siteActive) return;
    var id = body.dataset.siteActive;
    var item = document.querySelector('.nav [data-nav-id="' + id + '"]');
    if (!item) return;
    item.classList.add('nav-item--active');
    var link = item.querySelector(':scope > a');
    if (link) link.setAttribute('aria-current', 'page');
  }

  function fetchSlots(slots) {
    document.documentElement.classList.add('site-layout-loading');
    var order = [
      'layout-head', 'head-common',
      'layout-topbar', 'topbar',
      'layout-nav', 'nav',
      'view-home', 'home-main',
      'layout-footer', 'footer',
    ];
    slots.sort(function (a, b) {
      var ai = order.indexOf(a.getAttribute('data-site-include'));
      var bi = order.indexOf(b.getAttribute('data-site-include'));
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    });

    return slots.reduce(function (chain, el) {
      return chain.then(function () {
        var name = el.getAttribute('data-site-include');
        if (!PARTIALS[name]) return;
        if (!document.body.contains(el) && el.tagName.toLowerCase() !== 'head') return;
        return loadPartial(name).then(function (html) {
          inject(el, html);
        });
      });
    }, Promise.resolve()).then(function () {
      document.documentElement.classList.remove('site-layout-loading');
      document.documentElement.classList.add('site-layout-ready');
    });
  }

  function run() {
    var slots = Array.prototype.slice.call(document.querySelectorAll('[data-site-include]'));
    var chain = slots.length ? fetchSlots(slots) : Promise.resolve();
    return chain.then(function () {
      if (!slots.length) {
        document.documentElement.classList.add('site-layout-ready');
      }
      applyNavActive();
      document.dispatchEvent(new Event('site-layout:ready'));
    }).catch(function (err) {
      document.documentElement.classList.remove('site-layout-loading');
      console.error('[site-layout]', err);
    });
  }

  window.__siteLayoutReady = (document.readyState === 'loading')
    ? new Promise(function (resolve) {
      document.addEventListener('DOMContentLoaded', function () {
        run().then(resolve);
      });
    })
    : run();
}());
