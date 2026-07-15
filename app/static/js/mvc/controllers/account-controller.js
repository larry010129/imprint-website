(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.Account;
  var View = global.ImprintViews.Account;

  M.createController({
    run: function () {
      if (!M.isPage('account')) return;
      if (!View.els().ordersList || !M.api()) return;

      var statusLabel = global.ImprintOrderStatus ? global.ImprintOrderStatus.label : function (s) { return s; };

      M.requireSession('account.html').then(function (res) {
        if (!res) return;
        View.renderProfile(res);
        return Model.getOrders();
      }).then(function (oRes) {
        if (!oRes) return;
        if (oRes.error) {
          View.renderOrdersError();
          return;
        }
        View.renderOrders(oRes.orders || [], statusLabel);
      });

      var e = View.els();
      if (e.logoutBtn) {
        e.logoutBtn.addEventListener('click', function () {
          Model.logout().then(function () {
            global.location.href = '/';
          });
        });
      }
    },
  });
})(window);
