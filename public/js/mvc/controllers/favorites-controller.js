(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.Favorites;
  var View = global.ImprintViews.Favorites;

  M.createController({
    run: function () {
      if (!M.isPage('favorites')) return;
      M.requireSession('favorites.html').then(function (s) {
        if (!s) return;
        return Model.load();
      }).then(function (res) {
        if (!res) return;
        View.render(res.favorites || []);
        document.getElementById('favorites-grid')?.addEventListener('click', function (ev) {
          var btn = ev.target.closest('.favorite-remove');
          if (!btn) return;
          if (!confirm('確定移除此收藏？')) return;
          Model.remove(btn.dataset.id).then(function () {
            btn.closest('.member-favorite-card')?.remove();
          });
        });
      });
    },
  });
})(window);
