(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.Profile = {
    loadSession: function () { return M.api().getSession(); },
    loadOrders: function () { return M.api().getMyOrders(); },
  };
})(window);
