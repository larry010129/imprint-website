(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.Profile;
  var View = global.ImprintViews.Profile;

  M.createController({
    run: function () {
      if (!M.isPage('profile')) return;
      M.requireSession('profile.html').then(function (session) {
        if (!session) return;
        return Model.loadOrders().then(function (res) {
          View.render(session, (res && res.orders) || []);
        });
      });
    },
  });
})(window);
