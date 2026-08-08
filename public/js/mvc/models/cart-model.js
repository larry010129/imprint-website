(function (global) {
  'use strict';
  var M = global.ImprintMVC;

  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.Cart = {
    load: function () { return M.api().getCart(); },
    remove: function (id) {
      return fetch(M.apiBase() + '/api/cart-item?id=' + encodeURIComponent(id), {
        method: 'DELETE',
        credentials: 'include',
      }).then(function (r) { return r.json(); });
    },
    detail: function (id) {
      return fetch(M.apiBase() + '/api/cart-item?id=' + encodeURIComponent(id), { credentials: 'include' })
        .then(function (r) { return r.json(); });
    },
    setQuantity: function (id, quantity) {
      return fetch(M.apiBase() + '/api/cart/quantity', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id, quantity: quantity }),
      }).then(function (r) { return r.json().then(function (data) {
        data._status = r.status;
        return data;
      }); });
    },
  };
})(window);
