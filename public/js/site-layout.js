/* Jinja pages bake nav/footer server-side; this only signals readiness for main.js. */
(function () {
  'use strict';

  function run() {
    document.documentElement.classList.add('site-layout-ready');
    document.dispatchEvent(new Event('site-layout:ready'));
  }

  window.__siteLayoutReady = (document.readyState === 'loading')
    ? new Promise(function (resolve) {
      document.addEventListener('DOMContentLoaded', function () {
        run();
        resolve();
      });
    })
    : Promise.resolve().then(run);
}());
