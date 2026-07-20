/* Shop terms gate — show once until accepted (localStorage + cookie). */
(function () {
  'use strict';

  var STORAGE_KEY = 'imprint_shop_terms_v1';
  var COOKIE_NAME = 'imprint_shop_terms';

  function readAccepted() {
    try {
      if (localStorage.getItem(STORAGE_KEY) === '1') return true;
    } catch (_) {}
    return document.cookie.split(';').some(function (c) {
      return c.trim().indexOf(COOKIE_NAME + '=1') === 0;
    });
  }

  function markAccepted() {
    try { localStorage.setItem(STORAGE_KEY, '1'); } catch (_) {}
    document.cookie = COOKIE_NAME + '=1; path=/; max-age=31536000; SameSite=Lax';
  }

  function ensureShopTermsAccepted() {
    if (readAccepted()) return Promise.resolve(true);

    var dialog = document.getElementById('shop-terms-dialog');
    if (!dialog || typeof dialog.showModal !== 'function') return Promise.resolve(true);

    return new Promise(function (resolve) {
      var scroll = dialog.querySelector('.shop-terms-scroll');
      var agreeBtn = dialog.querySelector('#shop-terms-agree');
      var hint = dialog.querySelector('#shop-terms-scroll-hint');
      var readBottom = false;

      function setReadBottom(ok) {
        readBottom = ok;
        if (agreeBtn) agreeBtn.disabled = !ok;
        if (hint) hint.hidden = ok;
        dialog.querySelector('.shop-terms-footer')?.classList.toggle('shop-terms-footer--ready', ok);
      }

      function onScroll() {
        if (!scroll || readBottom) return;
        var max = scroll.scrollHeight - scroll.clientHeight;
        if (max <= 0 || scroll.scrollTop / max >= 0.99) setReadBottom(true);
      }

      function cleanup() {
        scroll?.removeEventListener('scroll', onScroll);
        dialog.removeEventListener('cancel', onCancel);
        document.body.classList.remove('shop-terms-blocked');
      }

      function onCancel(e) {
        e.preventDefault();
      }

      dialog.querySelector('#shop-terms-decline')?.addEventListener('click', function () {
        cleanup();
        dialog.close();
        resolve(false);
        window.location.href = '/';
      }, { once: true });

      dialog.querySelector('#shop-terms-agree')?.addEventListener('click', function () {
        if (!readBottom) return;
        markAccepted();
        cleanup();
        dialog.close();
        resolve(true);
      }, { once: true });

      scroll?.addEventListener('scroll', onScroll, { passive: true });
      dialog.addEventListener('cancel', onCancel);
      document.body.classList.add('shop-terms-blocked');
      setReadBottom(false);
      dialog.showModal();
      var focused = document.activeElement;
      if (focused && dialog.contains(focused)) focused.blur();
      requestAnimationFrame(onScroll);
    });
  }

  window.ensureShopTermsAccepted = ensureShopTermsAccepted;
})();
