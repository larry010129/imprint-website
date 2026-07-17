(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.Notifications = {
    load: function () {
      return fetch(M.apiBase() + '/api/notifications/recent', { credentials: 'include' }).then(function (r) { return r.json(); });
    },
    remove: function (id) {
      return fetch((global.IMPRINT_API_BASE || '') + '/api/notifications/delete', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id }),
      }).then(function (r) { return r.json(); });
    },
  };
})(window);
