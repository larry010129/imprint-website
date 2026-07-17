/* Decode base64url config tokens from the shop calculator (shop.js encodeConfigToken). */
(function (global) {
  'use strict';

  function decode(token) {
    if (!token) return null;
    try {
      var b64 = String(token).replace(/-/g, '+').replace(/_/g, '/');
      while (b64.length % 4) b64 += '=';
      var binary = atob(b64);
      var bytes = new Uint8Array(binary.length);
      for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      return JSON.parse(new TextDecoder().decode(bytes));
    } catch (_) {
      return null;
    }
  }

  function fromQuery(param) {
    var raw = new URLSearchParams(global.location.search).get(param || 'config');
    if (!raw) return null;
    return decode(raw) || (function () {
      try { return JSON.parse(decodeURIComponent(raw)); } catch (_) { return null; }
    })();
  }

  function fromPath() {
    var parts = global.location.pathname.split('/').filter(Boolean);
    if (parts[0] === 's' && parts[1]) return decode(parts[1]);
    var last = parts[parts.length - 1] || '';
    if (last && last !== 'summary' && last !== 'summary.html') return decode(last);
    return null;
  }

  global.ShopConfigToken = { decode: decode, fromQuery: fromQuery, fromPath: fromPath };
})(window);
