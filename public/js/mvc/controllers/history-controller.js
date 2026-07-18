(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.History;
  var View = global.ImprintViews.History;

  M.createController({
    run: function () {
      if (!M.isPage('history')) return;
      View.bindTabs();
      View.bindSearch();
      View.bindEdit();
      M.requireSession('history.html').then(function (s) {
        if (!s) return;
        return Model.load();
      }).then(function (res) {
        if (!res) return;
        if (res.error) {
          View.renderError(res.error);
          return;
        }
        var statusLabel = global.ImprintOrderStatus ? global.ImprintOrderStatus.label : function (st) { return st; };
        View.render(res.orders || [], statusLabel);
      });
    },
  });
})(window);
