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
    updateProfile: function (fields) {
      return global.imprintAPI.updateProfile(fields);
    },
    logout: function () {
      return global.imprintAPI.logout();
    },
  };
})(window);
