/* 銘印鑽石｜後端 API 連線設定
   取代 supabase-client.js。後端是獨立部署的 Node/Vercel 專案(見 /backend)，
   資料庫用 Neon Postgres，取代原本 Supabase 的 Postgres + Auth + PostgREST。

   所有方法回傳 Promise，resolve 成 { ok, error, ...資料 } 這種形狀(呼叫端看
   result.error 有沒有值來判斷成功/失敗)，只有真的連不上網路才會 reject。
   登入狀態靠後端設定的 httpOnly cookie 維持，所以每個 fetch 都要帶
   credentials:'include'，跨網域才吃得到 cookie。
*/
(function (global) {
  'use strict';

  var API_BASE = (typeof global.IMPRINT_API_BASE === 'string' && global.IMPRINT_API_BASE)
    || ''; // 部署時在頁面設 window.IMPRINT_API_BASE 指向 /backend 網址

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
          if (!res.ok && !data.error) data.error = 'HTTP ' + res.status;
          return data;
        });
      })
      .catch(function (err) {
        return { error: '系統連線異常，請稍後再試。', networkError: err };
      });
  }

  global.imprintAPI = {
    // ---- auth ----
    signup: function (fields) { return request('/api/auth/signup', { method: 'POST', body: fields }); },
    login: function (email, password) { return request('/api/auth/login', { method: 'POST', body: { email: email, password: password } }); },
    logout: function () { return request('/api/auth/logout', { method: 'POST' }); },
    getSession: function () { return request('/api/auth/session'); },
    requestPasswordReset: function (email) { return request('/api/auth/request-password-reset', { method: 'POST', body: { email: email } }); },
    resetPassword: function (token, newPassword) { return request('/api/auth/reset-password', { method: 'POST', body: { token: token, newPassword: newPassword } }); },

    // ---- customer ----
    getMyOrders: function () { return request('/api/orders'); },
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
      getDashboardStats: function () { return request('/api/admin/dashboard'); },
      getLeads: function () { return request('/api/admin/leads'); },
      markLeadDone: function (type, id) { return request('/api/admin/leads', { method: 'POST', body: { type: type, id: id } }); },
      getOrders: function () { return request('/api/admin/orders'); },
      createOrder: function (fields) { return request('/api/admin/orders', { method: 'POST', body: fields }); },
      updateOrderStatus: function (id, status, statusNote) { return request('/api/admin/order-update', { method: 'POST', body: { id: id, status: status, statusNote: statusNote } }); },
    },
  };
})(window);
