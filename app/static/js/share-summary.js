(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var root = document.getElementById('share-summary-root');
    if (!root || !window.ShopConfigToken || !window.ShopQuoteRender) return;
    var config = window.ShopConfigToken.fromPath()
      || window.ShopConfigToken.fromQuery('config')
      || window.ShopConfigToken.fromQuery('token');
    window.ShopQuoteRender.mount(root, config, 'share');
  });
})();
