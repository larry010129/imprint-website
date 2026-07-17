(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var root = document.getElementById('quote-sheet-root');
    if (!root || !window.ShopConfigToken || !window.ShopQuoteRender) return;
    var config = window.ShopConfigToken.fromQuery('config');
    window.ShopQuoteRender.mount(root, config, 'quote');
  });
})();
