(function (global) {
  'use strict';
  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.ResetPassword = {
    reset: function (token, password) {
      return global.imprintAPI.resetPassword(token, password);
    },
    tokenFromUrl: function () {
      return new URLSearchParams(global.location.search).get('token');
    },
  };
})(window);
