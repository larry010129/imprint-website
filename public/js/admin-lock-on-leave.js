/* 銘印鑽石｜隱藏頁面：開著時保持解鎖，離開時立刻上鎖（每次進入都要通行碼）。 */
(function () {
  'use strict';

  var KEEPALIVE_MS = 60 * 1000;
  var KEEPALIVE_URL = '/api/admin/release-notes/keepalive';
  var LOCK_URL = '/api/admin/release-notes/lock';

  function keepalive() {
    fetch(KEEPALIVE_URL, { method: 'POST', credentials: 'include' })
      .then(function (res) {
        /* Unlock lapsed (laptop slept, long idle): back to the code prompt. */
        if (res.status === 403) window.location.reload();
      })
      .catch(function () { /* offline: the next tick tries again */ });
  }

  function lock() {
    var sent = false;
    try {
      sent = navigator.sendBeacon && navigator.sendBeacon(LOCK_URL, new Blob([], { type: 'text/plain' }));
    } catch (e) { sent = false; }
    if (!sent) {
      try { fetch(LOCK_URL, { method: 'POST', credentials: 'include', keepalive: true }); } catch (e) { /* ignore */ }
    }
  }

  setInterval(keepalive, KEEPALIVE_MS);

  /* Leaving, closing, reloading or switching away on mobile all fire pagehide. */
  window.addEventListener('pagehide', lock);

  /* Back/forward cache can restore this page after we locked: reload to get the prompt. */
  window.addEventListener('pageshow', function (event) {
    if (event.persisted) window.location.reload();
  });
})();
