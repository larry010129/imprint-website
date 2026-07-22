(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.Favorites = {
    render: function (favorites) {
      var grid = document.getElementById('favorites-grid');
      var loading = document.getElementById('favorites-loading');
      if (loading) loading.classList.add('hidden');
      if (!grid) return;
      if (!favorites.length) {
        grid.classList.remove('hidden');
        grid.innerHTML = '<div class="member-state member-state--empty" style="grid-column:1/-1;"><p>尚未收藏任何款式。</p><a href="/shop/calculator/" class="btn btn-mint">前往選擇</a></div>';
        return;
      }
      grid.innerHTML = favorites.map(function (fav) {
        var url = fav.load_url || fav.loadUrl || ('/shop/calculator/?prefill=' + encodeURIComponent(fav.id || ''));
        return (
          '<article class="member-favorite-card" data-id="' + M.escapeHtml(fav.id) + '">' +
            (fav.image_url ? '<img src="' + M.escapeHtml(fav.image_url) + '" alt="" loading="lazy">' : '') +
            '<div class="member-favorite-card__body"><h2>' + M.escapeHtml(fav.summary || fav.name || '收藏款式') + '</h2>' +
            '<div class="member-favorite-card__actions"><a href="' + M.escapeHtml(url) + '">帶入試算</a>' +
            '<button type="button" class="favorite-remove" data-id="' + M.escapeHtml(fav.id) + '">移除</button></div></div></article>'
        );
      }).join('');
      grid.classList.remove('hidden');
    },
  };
})(window);
