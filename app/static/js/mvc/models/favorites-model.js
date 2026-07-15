(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.Favorites = {
    load: function () { return M.api().getFavorites(); },
    remove: function (id) {
      return fetch(M.apiBase() + '/api/favorites/' + encodeURIComponent(id), { method: 'DELETE', credentials: 'include' })
        .then(function (r) { return r.json(); });
    },
  };
})(window);
