(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.History = {
    load: function () { return M.api().getMyOrders(); },
  };
})(window);
