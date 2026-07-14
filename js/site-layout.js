/* Component layout — applies nav active state after baked-in partials.
   Partials are inlined by: node scripts/build-site-layout.mjs
   If data-site-include slots remain (dev), fetches partials over HTTP. */
(function () {
  'use strict';

  var PARTIALS = {
    topbar: 'partials/topbar.html',
    nav: 'partials/nav.html',
    footer: 'partials/footer.html',
    'head-common': 'partials/head-common.html',
    'home-main': 'partials/home-main.html',
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
    var order = ['head-common', 'topbar', 'nav', 'home-main', 'footer'];
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
