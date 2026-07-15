(function (global) {
  'use strict';
  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.TrackOrder = {
    track: function (orderNumber, phone) {
      return global.imprintAPI.trackOrder(orderNumber, phone);
    },
  };
})(window);
