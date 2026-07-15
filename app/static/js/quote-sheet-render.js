(function () {
  'use strict';

  function esc(text) {
    var el = document.createElement('span');
    el.textContent = text == null ? '' : String(text);
    return el.innerHTML;
  }

  function fmt(n) {
    return Number(n || 0).toLocaleString('zh-TW', { maximumFractionDigits: 0 });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var root = document.getElementById('quote-sheet-root');
    if (!root || !window.imprintAPI) return;

    var params = new URLSearchParams(window.location.search);
    var configRaw = params.get('config');
    if (!configRaw) {
      root.innerHTML = '<p>缺少 config 參數。</p>';
      return;
    }

    var config;
    try {
      config = JSON.parse(decodeURIComponent(configRaw));
    } catch (_) {
      root.innerHTML = '<p>config 格式錯誤。</p>';
      return;
    }

    window.imprintAPI.getShopQuote(config).then(function (res) {
      if (res.error || !res.quote) {
        root.innerHTML = '<p>無法取得報價。</p>';
        return;
      }
      var q = res.quote;
      var product = res.product || {};
      var now = new Date();
      root.innerHTML =
        '<header class="quote-sheet-header">' +
          '<div><h1>珠寶訂製報價單</h1></div>' +
          '<div class="quote-sheet-meta"><time>' + esc(now.toISOString().slice(0, 16).replace('T', ' ')) + '</time></div>' +
        '</header>' +
        '<section class="share-product">' +
          (product.image_url ? '<img src="' + esc(product.image_url) + '" alt="">' : '') +
          '<div><p>' + esc(product.category || config.category || '') + '</p>' +
          '<h2>' + esc(product.name_zh || product.name || '訂製品項') + '</h2></div>' +
        '</section>' +
        '<section class="quote-breakdown">' +
          (q.diamondPrice != null ? '<p><span>鑽石價格</span><strong>NT$ ' + fmt(q.diamondPrice) + '</strong></p>' : '') +
          (q.taijinPrice != null ? '<p><span>台金價格</span><strong>NT$ ' + fmt(q.taijinPrice) + '</strong></p>' : '') +
          (q.laborPrice != null ? '<p><span>金工費</span><strong>NT$ ' + fmt(q.laborPrice) + '</strong></p>' : '') +
          '<p class="quote-total"><span>含稅預估總價</span><strong>NT$ ' + fmt(q.total) + '</strong></p>' +
        '</section>' +
        '<p class="quote-disclaimer">本報價為當下金價之預估結果；實際金額可能因市場價格與最終規格調整。</p>' +
        '<footer><button type="button" id="quote-print-btn">列印 / 儲存 PDF</button></footer>';
    });
  });
})();
