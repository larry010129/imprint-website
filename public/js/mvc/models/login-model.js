(function (global) {
  'use strict';
  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.Login = {
    login: function (email, password, remember) {
      return global.imprintAPI.login(email, password, remember);
    },
    getSession: function () {
      return global.imprintAPI.getSession();
    },
    requestReset: function (email) {
      return global.imprintAPI.requestPasswordReset(email);
    },
  };
})(window);
