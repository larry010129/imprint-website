(function (global) {
  'use strict';
  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.Login = {
    login: function (email, password) {
      return global.imprintAPI.login(email, password);
    },
    requestReset: function (email) {
      return global.imprintAPI.requestPasswordReset(email);
    },
  };
})(window);
