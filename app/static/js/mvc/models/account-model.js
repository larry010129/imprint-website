(function (global) {
  'use strict';
  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.Account = {
    getSession: function () {
      return global.imprintAPI.getSession();
    },
    getOrders: function () {
      return global.imprintAPI.getMyOrders();
    },
    logout: function () {
      return global.imprintAPI.logout();
    },
  };
})(window);
