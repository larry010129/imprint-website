(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.Notifications = {
    load: function () {
      return fetch(M.apiBase() + '/api/notifications/recent', { credentials: 'include' }).then(function (r) { return r.json(); });
    },
    remove: function (id) {
      return fetch('/notifications/delete/' + id, { method: 'POST', credentials: 'include' }).then(function (r) { return r.json(); });
    },
  };
})(window);
