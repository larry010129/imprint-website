(function () {
  'use strict';

  function esc(text) {
    var el = document.createElement('span');
    el.textContent = text == null ? '' : String(text);
    return el.innerHTML;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var root = document.getElementById('share-summary-root');
    if (!root) return;
    var token = (window.location.pathname.split('/').pop() || '').replace(/\.html$/, '');
    var qToken = new URLSearchParams(window.location.search).get('token');
    var id = qToken || token;
    if (!id || id === 'summary') {
      root.innerHTML = '<p>無效的分享連結。</p>';
      return;
    }
    fetch('/api/share/' + encodeURIComponent(id), { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) {
          root.innerHTML = '<p>' + esc(data.error) + '</p>';
          return;
        }
        root.innerHTML =
          '<header class="quote-sheet-header"><h1>試算分享</h1></header>' +
          '<section class="share-product">' +
            (data.image_url ? '<img src="' + esc(data.image_url) + '" alt="">' : '') +
            '<div><h2>' + esc(data.summary || '訂製品項') + '</h2></div>' +
          '</section>' +
          '<p class="quote-total"><strong>NT$ ' + esc(String(data.total || '—')) + '</strong></p>' +
          '<p><button type="button" id="share-copy-link">複製連結</button></p>';
        document.getElementById('share-copy-link')?.addEventListener('click', function () {
          navigator.clipboard.writeText(window.location.href);
        });
      })
      .catch(function () {
        root.innerHTML = '<p>無法載入分享內容。</p>';
      });
  });
})();
