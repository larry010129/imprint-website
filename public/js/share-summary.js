(function () {
  'use strict';

  /* New links are a short code (/s/K7M29QXA) that the server turns back into the
     saved configuration. Old links carry the whole configuration (long base64) and
     keep working: anything longer than a code is decoded in the browser as before. */
  var SHORT_CODE_MAX = 16;

  function showError(root, message) {
    root.innerHTML = '<div class="share-page"><p class="share-error">' + message + '</p>'
      + '<p class="share-error-actions"><a class="share-btn share-btn--primary" href="/shop/calculator/">返回試算</a></p></div>';
  }

  document.addEventListener('DOMContentLoaded', function () {
    var root = document.getElementById('share-summary-root');
    if (!root || !window.ShopConfigToken || !window.ShopQuoteRender) return;

    var parts = window.location.pathname.split('/').filter(Boolean);
    var token = parts[0] === 's' ? parts[1] : '';

    if (token && token.length <= SHORT_CODE_MAX) {
      fetch('/api/share/' + encodeURIComponent(token), { credentials: 'same-origin' })
        .then(function (res) {
          if (res.ok) return res.json();
          var err = new Error('share ' + res.status);
          err.status = res.status;
          throw err;
        })
        .then(function (data) {
          window.ShopQuoteRender.mount(root, data && data.config, 'share');
        })
        .catch(function (err) {
          showError(root, err && err.status === 404
            ? '這個分享連結不存在或已失效，請回到計算機重新分享。'
            : '暫時無法載入分享內容，請稍後再試。');
        });
      return;
    }

    var config = window.ShopConfigToken.fromPath()
      || window.ShopConfigToken.fromQuery('config')
      || window.ShopConfigToken.fromQuery('token');
    window.ShopQuoteRender.mount(root, config, 'share');
  });
})();
