(function (global) {
  'use strict';
  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.Login = {
    login: function (email, password) {
      return global.imprintAPI.login(email, password);
    },
    getSession: function () {
      return global.imprintAPI.getSession();
    },
    requestReset: function (email) {
      return global.imprintAPI.requestPasswordReset(email);
    },
  };
})(window);
