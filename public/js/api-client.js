/* 銘印鑽石｜後端 API 連線設定
   取代 supabase-client.js。正式環境為同站 FastAPI（Render 或本機 uvicorn），
   路徑前綴 /api；資料庫為 Postgres（Supabase 或本機）。

   所有方法回傳 Promise，resolve 成 { ok, error, ...資料 } 這種形狀(呼叫端看
   result.error 有沒有值來判斷成功/失敗)，只有真的連不上網路才會 reject。
   登入狀態靠後端設定的 httpOnly cookie 維持，所以每個 fetch 都要帶
   credentials:'include'。
*/
(function (global) {
  'use strict';

  var API_BASE = (typeof global.IMPRINT_API_BASE === 'string' && global.IMPRINT_API_BASE)
    || ''; // 同站部署留空；僅在 API 與靜態站不同網域時才設 window.IMPRINT_API_BASE

  function request(path, options) {
    options = options || {};
    return fetch(API_BASE + path, {
      method: options.method || 'GET',
      credentials: 'include',
      headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
      body: options.body ? JSON.stringify(options.body) : undefined,
    })
      .then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (data) {
          if (!res.ok && !data.error) {
            if (typeof data.detail === 'string') data.error = data.detail;
            else if (Array.isArray(data.detail)) {
              data.error = data.detail.map(function (d) {
                return (d && d.msg) ? d.msg : String(d);
              }).join('；');
            }
            else data.error = 'HTTP ' + res.status;
          }
          data._httpStatus = res.status;
          return data;
        });
      })
      .catch(function (err) {
        return { error: '系統連線異常，請稍後再試。', networkError: err };
      });
  }

  function apiErrorMessage(data) {
    if (!data) return '未知錯誤';
    if (typeof data.error === 'string') return data.error;
    if (data.error && data.error.message) return data.error.message;
    if (typeof data.detail === 'string') return data.detail;
    return '未知錯誤';
  }

  global.imprintAPI = {
    apiErrorMessage: apiErrorMessage,
    // ---- auth ----
    signup: function (fields) { return request('/api/auth/signup', { method: 'POST', body: fields }); },
    login: function (email, password) { return request('/api/auth/login', { method: 'POST', body: { email: email, password: password } }); },
    logout: function () { return request('/api/auth/logout', { method: 'POST' }); },
    getSession: function () { return request('/api/auth/session'); },
    requestPasswordReset: function (email) { return request('/api/auth/request-password-reset', { method: 'POST', body: { email: email } }); },
    resetPassword: function (token, newPassword) { return request('/api/auth/reset-password', { method: 'POST', body: { token: token, newPassword: newPassword } }); },

    // ---- customer ----
    getMyOrders: function () { return request('/api/orders'); },
    getMyOrder: function (orderNumber) {
      return request('/api/order?orderNumber=' + encodeURIComponent(orderNumber));
    },
    updateMyOrder: function (fields) { return request('/api/order', { method: 'PUT', body: fields }); },
    trackOrder: function (orderNumber, phone) { return request('/api/track-order', { method: 'POST', body: { orderNumber: orderNumber, phone: phone } }); },
    submitContact: function (fields) { return request('/api/contact', { method: 'POST', body: fields }); },
    submitQuoteRequest: function (fields) { return request('/api/quote-request', { method: 'POST', body: fields }); },

    // ---- pricing / gold price (public reads, admin-only writes) ----
    getPricingOverrides: function () { return request('/api/pricing'); },
    savePricingOverrides: function (overrides) { return request('/api/pricing', { method: 'POST', body: { overrides: overrides } }); },
    resetPricingOverrides: function () { return request('/api/pricing', { method: 'POST', body: { reset: true } }); },
    getLiveGoldPrice: function () { return request('/api/gold-price'); },
    refreshGoldPrice: function () { return request('/api/gold-refresh', { method: 'POST' }); },

    // ---- shop (dynamic catalog calculator) ----
    getCatalog: function (opts) {
      var q = opts && opts.preview ? '?preview=1' : '';
      return request('/api/catalog' + q);
    },
    getShopPrices: function () { return request('/api/prices'); },
    getShopQuote: function (config, opts) {
      var q = opts && opts.preview ? '?preview=1' : '';
      return request('/api/quote' + q, { method: 'POST', body: config });
    },
    getCart: function () { return request('/api/cart'); },
    addToCart: function (config) { return request('/api/cart', { method: 'POST', body: config }); },
    updateCartItem: function (id, config) {
      return request('/api/cart-item?id=' + encodeURIComponent(id), { method: 'PUT', body: Object.assign({ id: id }, config) });
    },
    checkoutCart: function (itemIds) {
      return request('/api/cart-checkout', { method: 'POST', body: itemIds ? { itemIds: itemIds } : {} });
    },
    getFavorites: function () { return request('/api/favorites'); },
    addFavorite: function (config) { return request('/api/favorites', { method: 'POST', body: config }); },

    getBase: function () { return API_BASE; },

    // ---- admin ----
    admin: {
      getDashboardStats: function (params) {
        var qs = '';
        if (params) {
          var parts = [];
          Object.keys(params).forEach(function (key) {
            if (params[key] != null && params[key] !== '') {
              parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(params[key]));
            }
          });
          if (parts.length) qs = '?' + parts.join('&');
        }
        return request('/api/admin/dashboard' + qs);
      },
      dashboardExportUrl: function (params) {
        var qs = '';
        if (params) {
          var parts = [];
          Object.keys(params).forEach(function (key) {
            if (params[key] != null && params[key] !== '') {
              parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(params[key]));
            }
          });
          if (parts.length) qs = '?' + parts.join('&');
        }
        return (API_BASE || '') + '/api/admin/dashboard/export' + qs;
      },
      getLeads: function () { return request('/api/admin/leads'); },
      markLeadDone: function (type, id) { return request('/api/admin/leads', { method: 'POST', body: { type: type, id: id } }); },
      getOrders: function () { return request('/api/admin/orders'); },
      createOrder: function (fields) { return request('/api/admin/orders', { method: 'POST', body: fields }); },
      updateOrderStatus: function (id, status, statusNote) { return request('/api/admin/order-update', { method: 'POST', body: { id: id, status: status, statusNote: statusNote } }); },
      cancelOrder: function (id, reason) { return request('/api/admin/order-cancel', { method: 'POST', body: { id: id, reason: reason } }); },
      bulkUpdateOrders: function (ids, status, cancelReason) {
        return request('/api/admin/orders-bulk-update', { method: 'POST', body: { ids: ids, status: status, cancelReason: cancelReason || null } });
      },
      deleteOrder: function (id, reason) { return request('/api/admin/order-cancel', { method: 'POST', body: { id: id, reason: reason || '管理員取消' } }); },
      getProducts: function () { return request('/api/admin/products'); },
      saveProduct: function (fields) { return request('/api/admin/products', { method: 'POST', body: fields }); },
      updateProduct: function (fields) { return request('/api/admin/product-update', { method: 'POST', body: fields }); },
      productAction: function (id, action) { return request('/api/admin/product-action', { method: 'POST', body: { id: id, action: action } }); },
      reorderProducts: function (order) { return request('/api/admin/products-reorder', { method: 'POST', body: { order: order } }); },
      getInvites: function () { return request('/api/admin/invites'); },
      createInvite: function (fields) { return request('/api/admin/invites', { method: 'POST', body: fields }); },
      inviteAction: function (id, action) { return request('/api/admin/invite-action', { method: 'POST', body: { id: id, action: action } }); },
      getAccounts: function () { return request('/api/admin/accounts'); },
      accountAction: function (id, action, extra) {
        var body = { id: id, action: action };
        if (extra) Object.keys(extra).forEach(function (k) { body[k] = extra[k]; });
        return request('/api/admin/account-action', { method: 'POST', body: body });
      },
    },
  };
})(window);
