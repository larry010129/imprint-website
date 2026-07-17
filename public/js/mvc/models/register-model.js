(function (global) {
  'use strict';
  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.Register = {
    signup: function (payload) {
      return global.imprintAPI.signup(payload);
    },
  };
})(window);
