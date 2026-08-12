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

  function pagingQuery(opts) {
    opts = opts || {};
    var parts = [];
    if (opts.page != null && opts.page !== '') {
      parts.push('page=' + encodeURIComponent(opts.page));
    }
    var size = opts.pageSize != null ? opts.pageSize : opts.page_size;
    if (size != null && size !== '') {
      parts.push('page_size=' + encodeURIComponent(size));
    }
    if (opts.q) parts.push('q=' + encodeURIComponent(opts.q));
    if (opts.category) parts.push('category=' + encodeURIComponent(opts.category));
    if (opts.page_key || opts.pageKey) {
      parts.push('page_key=' + encodeURIComponent(opts.page_key || opts.pageKey));
    }
    return parts.length ? ('?' + parts.join('&')) : '';
  }

  /**
   * One page when opts.page set; otherwise walk pages (page_size 100) until total covered.
   * Keeps legacy admin panels working after server-side LIMIT.
   */
  function requestPagedList(path, itemsKey, opts) {
    opts = opts || {};
    if (opts.page != null && opts.page !== '') {
      return request(path + pagingQuery(opts));
    }
    var pageSize = opts.pageSize || opts.page_size || 100;
    var page = 1;
    var all = [];
    var meta = {};
    function step() {
      return request(
        path + pagingQuery(Object.assign({}, opts, { page: page, page_size: pageSize }))
      ).then(function (res) {
        if (res && res.error) return res;
        meta = res || {};
        var chunk = (res && res[itemsKey]) || [];
        all = all.concat(chunk);
        var total = typeof res.total === 'number' ? res.total : all.length;
        if (all.length < total && chunk.length > 0) {
          page += 1;
          return step();
        }
        var out = Object.assign({}, meta);
        out[itemsKey] = all;
        out.total = total;
        return out;
      });
    }
    return step();
  }

  function apiErrorMessage(data) {
    if (!data) return '未知錯誤';
    if (typeof data.error === 'string' && data.error) return data.error;
    if (data.error && data.error.message) return data.error.message;
    if (typeof data.detail === 'string' && data.detail) return data.detail;
    if (Array.isArray(data.detail) && data.detail.length) {
      return data.detail.map(function (d) {
        return (d && d.msg) ? d.msg : String(d);
      }).join('；');
    }
    if (typeof data.message === 'string' && data.message) return data.message;
    return '未知錯誤';
  }

  /** Prompt admin password (+ optional TOTP) for step-up protected mutations. */
  function collectStepUp(label) {
    var pwd = global.prompt(
      '請輸入您的管理員密碼以確認' + (label ? '「' + label + '」' : '') + '：'
    );
    if (pwd == null || !String(pwd).trim()) {
      return { error: '已取消（需管理員密碼）', _cancelled: true };
    }
    var totp = global.prompt('若已啟用 Authenticator，請輸入驗證碼；否則留空後確定：') || '';
    return {
      password: String(pwd),
      totpCode: String(totp).trim() || undefined,
    };
  }

  function withStepUp(label, body) {
    var step = collectStepUp(label);
    if (step.error) return step;
    var out = Object.assign({}, body || {});
    out.password = step.password;
    if (step.totpCode) out.totpCode = step.totpCode;
    return out;
  }

  global.imprintAPI = {
    apiErrorMessage: apiErrorMessage,
    collectStepUp: collectStepUp,
    // ---- auth ----
    signup: function (fields) { return request('/api/auth/signup', { method: 'POST', body: fields }); },
    login: function (email, password, remember) {
      return request('/api/auth/login', {
        method: 'POST',
        body: { email: email, password: password, remember: remember !== false },
      });
    },
    logout: function () { return request('/api/auth/logout', { method: 'POST' }); },
    getSession: function () { return request('/api/auth/session'); },
    updateProfile: function (fields) {
      return request('/api/auth/profile', { method: 'PATCH', body: fields });
    },
    changePassword: function (fields) {
      return request('/api/auth/change-password', { method: 'POST', body: fields || {} });
    },
    googleEnrichProfile: function (accessToken) {
      return request('/api/auth/google-enrich', {
        method: 'POST',
        body: { access_token: accessToken },
      });
    },
    requestPasswordReset: function (email) { return request('/api/auth/request-password-reset', { method: 'POST', body: { email: email } }); },
    resetPassword: function (token, newPassword) { return request('/api/auth/reset-password', { method: 'POST', body: { token: token, newPassword: newPassword } }); },
    verifyPasswordResetTotp: function (email, code) {
      return request('/api/auth/forgot-password-verify', {
        method: 'POST',
        body: { email: email, code: code },
      });
    },
    resetPasswordWithTotp: function (email, code, newPassword) {
      // Two-step: Authenticator verify sets imprint_pwreset cookie, then set password.
      return request('/api/auth/forgot-password-verify', {
        method: 'POST',
        body: { email: email, code: code },
      }).then(function (res) {
        if (res && res.error) return res;
        return request('/api/auth/reset-password-totp', {
          method: 'POST',
          body: { newPassword: newPassword },
        });
      });
    },

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
    savePricingOverrides: function (overrides) {
      var body = withStepUp('儲存定價覆寫', { overrides: overrides });
      if (body.error) return Promise.resolve(body);
      return request('/api/pricing', { method: 'POST', body: body });
    },
    resetPricingOverrides: function () {
      var body = withStepUp('重設定價覆寫', { reset: true });
      if (body.error) return Promise.resolve(body);
      return request('/api/pricing', { method: 'POST', body: body });
    },
    getMembershipConfig: function () { return request('/api/membership-config'); },
    getAdminMembershipConfig: function () { return request('/api/admin/membership-config'); },
    saveAdminMembershipConfig: function (config) {
      var body = withStepUp('儲存會員階梯設定', { config: config });
      if (body.error) return Promise.resolve(body);
      return request('/api/admin/membership-config', { method: 'POST', body: body });
    },
    resetAdminMembershipConfig: function () {
      var body = withStepUp('重設會員階梯設定', { reset: true });
      if (body.error) return Promise.resolve(body);
      return request('/api/admin/membership-config', { method: 'POST', body: body });
    },
    getLiveGoldPrice: function () { return request('/api/gold-price'); },
    refreshGoldPrice: function () { return request('/api/gold-refresh', { method: 'POST' }); },

    // ---- shop (dynamic catalog calculator) ----
    getCatalog: function (opts) {
      var parts = [];
      if (opts && opts.preview) parts.push('preview=1');
      if (opts && opts.category) parts.push('category=' + encodeURIComponent(opts.category));
      if (opts && opts.detail) parts.push('detail=' + encodeURIComponent(opts.detail));
      var q = parts.length ? '?' + parts.join('&') : '';
      return request('/api/catalog' + q);
    },
    getCatalogProduct: function (productId, opts) {
      var q = opts && opts.preview ? '?preview=1' : '';
      return request('/api/catalog/product/' + encodeURIComponent(productId) + q);
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
      getOrders: function (opts) {
        return request('/api/admin/orders' + pagingQuery(opts));
      },
      createOrder: function (fields) { return request('/api/admin/orders', { method: 'POST', body: fields }); },
      updateOrderStatus: function (id, status, statusNote) { return request('/api/admin/order-update', { method: 'POST', body: { id: id, status: status, statusNote: statusNote } }); },
      cancelOrder: function (id, reason) {
        // Cancel: reason only — no admin password / step-up.
        return request('/api/admin/order-cancel', {
          method: 'POST',
          body: { id: id, reason: reason },
        });
      },
      bulkUpdateOrders: function (ids, status, cancelReason) {
        var body = {
          ids: ids,
          status: status,
          cancelReason: cancelReason || null,
        };
        // Cancel uses reason only; other bulk status changes still step-up.
        if (status !== 'cancelled') {
          body = withStepUp('批次更新訂單', body);
          if (body.error) return Promise.resolve(body);
        }
        return request('/api/admin/orders-bulk-update', { method: 'POST', body: body });
      },
      deleteOrder: function (id, reason) {
        return this.cancelOrder(id, reason || '管理員取消');
      },
      getProducts: function (opts) {
        return request('/api/admin/products' + pagingQuery(opts));
      },
      createProductCategory: function (fields) { return request('/api/admin/product-category', { method: 'POST', body: fields }); },
      createDiamondShape: function (fields) { return request('/api/admin/diamond-shape', { method: 'POST', body: fields }); },
      deleteProductCategory: function (slug) { return request('/api/admin/product-category/' + encodeURIComponent(slug), { method: 'DELETE' }); },
      updateProductCategory: function (slug, fields) {
        return request('/api/admin/product-category/' + encodeURIComponent(slug), { method: 'PATCH', body: fields });
      },
      forceProductCategoryAddon: function (slug, fields) {
        return request(
          '/api/admin/product-category/' + encodeURIComponent(slug) + '/force-addon',
          { method: 'POST', body: fields }
        );
      },
      uploadProductCategoryThumb: function (slug, file) {
        var fd = new FormData();
        fd.append('file', file);
        return fetch(API_BASE + '/api/admin/product-category-upload?slug=' + encodeURIComponent(slug), {
          method: 'POST',
          credentials: 'include',
          body: fd,
        }).then(function (res) {
          return res.json().catch(function () { return {}; }).then(function (data) {
            if (!res.ok) {
              var msg = apiErrorMessage(data);
              if (!data.error || data.error === '未知錯誤') {
                data.error = (msg && msg !== '未知錯誤') ? msg : ('HTTP ' + res.status);
              }
            }
            data._httpStatus = res.status;
            return data;
          });
        }).catch(function () {
          return { error: '系統連線異常，請稍後再試。' };
        });
      },
      saveProduct: function (fields) { return request('/api/admin/products', { method: 'POST', body: fields }); },
      updateProduct: function (fields) { return request('/api/admin/product-update', { method: 'POST', body: fields }); },
      productAction: function (id, action) { return request('/api/admin/product-action', { method: 'POST', body: { id: id, action: action } }); },
      productImageAction: function (imageId, action) {
        return request('/api/admin/product-image-action', {
          method: 'POST',
          body: { image_id: imageId, action: action },
        });
      },
      reorderProducts: function (order) { return request('/api/admin/products-reorder', { method: 'POST', body: { order: order } }); },
      getInvites: function (opts) {
        return requestPagedList('/api/admin/invites', 'invites', opts);
      },
      createInvite: function (fields) {
        var body = Object.assign({}, fields || {});
        if (!body.password && !body.adminPassword) {
          var step = collectStepUp('建立邀請碼');
          if (step.error) return Promise.resolve(step);
          body.adminPassword = step.password;
          if (step.totpCode) body.totpCode = step.totpCode;
        }
        return request('/api/admin/invites', { method: 'POST', body: body });
      },
      inviteAction: function (id, action) { return request('/api/admin/invite-action', { method: 'POST', body: { id: id, action: action } }); },
      getCoupons: function (opts) {
        return requestPagedList('/api/admin/coupons', 'coupons', opts);
      },
      createCoupon: function (fields) {
        var body = withStepUp('建立優惠碼', fields || {});
        if (body.error) return Promise.resolve(body);
        return request('/api/admin/coupons', { method: 'POST', body: body });
      },
      updateCoupon: function (fields) {
        var body = withStepUp('更新優惠碼', fields || {});
        if (body.error) return Promise.resolve(body);
        return request('/api/admin/coupon-update', { method: 'POST', body: body });
      },
      couponAction: function (id, action) {
        var body = withStepUp('優惠碼操作', { id: id, action: action });
        if (body.error) return Promise.resolve(body);
        return request('/api/admin/coupon-action', { method: 'POST', body: body });
      },
      getTestimonials: function (opts) {
        return requestPagedList('/api/admin/testimonials', 'testimonials', opts);
      },
      createTestimonial: function (fields) { return request('/api/admin/testimonials', { method: 'POST', body: fields }); },
      updateTestimonial: function (fields) { return request('/api/admin/testimonial-update', { method: 'POST', body: fields }); },
      reorderTestimonial: function (id, direction) {
        return request('/api/admin/testimonial-reorder', { method: 'POST', body: { id: id, direction: direction } });
      },
      testimonialAction: function (id, action) { return request('/api/admin/testimonial-action', { method: 'POST', body: { id: id, action: action } }); },
      getJournalPosts: function (opts) {
        return requestPagedList('/api/admin/journal-posts', 'posts', opts);
      },
      createJournalPost: function (fields) { return request('/api/admin/journal-posts', { method: 'POST', body: fields }); },
      updateJournalPost: function (fields) { return request('/api/admin/journal-post-update', { method: 'POST', body: fields }); },
      journalPostAction: function (id, action) {
        return request('/api/admin/journal-post-action', { method: 'POST', body: { id: id, action: action } });
      },
      uploadTestimonial: function (file) {
        var fd = new FormData();
        fd.append('file', file);
        return fetch(API_BASE + '/api/admin/testimonial-upload', {
          method: 'POST',
          credentials: 'include',
          body: fd,
        }).then(function (res) {
          return res.json().catch(function () { return {}; }).then(function (data) {
            if (!res.ok && !data.error) {
              if (typeof data.detail === 'string') data.error = data.detail;
              else data.error = 'HTTP ' + res.status;
            }
            data._httpStatus = res.status;
            return data;
          });
        }).catch(function () {
          return { error: '系統連線異常，請稍後再試。' };
        });
      },
      getFaqItems: function (opts) {
        return requestPagedList('/api/admin/faq-items', 'items', opts);
      },
      getFaqCategories: function () { return request('/api/admin/faq-categories'); },
      createFaqItem: function (fields) { return request('/api/admin/faq-items', { method: 'POST', body: fields }); },
      updateFaqItem: function (fields) { return request('/api/admin/faq-update', { method: 'POST', body: fields }); },
      faqAction: function (id, action) {
        var body = withStepUp('FAQ 發布/刪除', { id: id, action: action });
        if (body.error) return Promise.resolve(body);
        return request('/api/admin/faq-action', { method: 'POST', body: body });
      },
      createFaqCategory: function (fields) { return request('/api/admin/faq-categories', { method: 'POST', body: fields }); },
      updateFaqCategory: function (fields) { return request('/api/admin/faq-category-update', { method: 'POST', body: fields }); },
      faqCategoryAction: function (id, action) {
        var body = withStepUp('刪除 FAQ 分類', { id: id, action: action });
        if (body.error) return Promise.resolve(body);
        return request('/api/admin/faq-category-action', { method: 'POST', body: body });
      },
      listCmsPages: function (opts) {
        return requestPagedList('/api/admin/cms-pages', 'pages', opts);
      },
      getCmsPage: function (id) { return request('/api/admin/cms-pages/' + encodeURIComponent(id)); },
      getCmsSitePage: function (route) {
        return request('/api/admin/cms-site-page?route=' + encodeURIComponent(route || ''));
      },
      updateCmsPage: function (fields) { return request('/api/admin/cms-page-update', { method: 'POST', body: fields }); },
      cmsPageAction: function (id, action) {
        var body = withStepUp('CMS 頁面操作', { id: id, action: action });
        if (body.error) return Promise.resolve(body);
        return request('/api/admin/cms-page-action', { method: 'POST', body: body });
      },
      createCmsSection: function (pageId, fields) {
        return request('/api/admin/cms-pages/' + encodeURIComponent(pageId) + '/sections', {
          method: 'POST',
          body: fields,
        });
      },
      updateCmsSection: function (fields) {
        return request('/api/admin/cms-section-update', { method: 'POST', body: fields });
      },
      getCmsSectionHtml: function (id) {
        return request('/api/admin/cms-sections/' + encodeURIComponent(id) + '/html');
      },
      cmsSectionAction: function (id, action) {
        var body = { id: id, action: action };
        if (action === 'delete') {
          body = withStepUp('刪除 CMS 區塊', body);
          if (body.error) return Promise.resolve(body);
        }
        return request('/api/admin/cms-section-action', { method: 'POST', body: body });
      },
      reorderCmsSections: function (pageId, sectionIds) {
        return request('/api/admin/cms-pages/' + encodeURIComponent(pageId) + '/sections/reorder', {
          method: 'PATCH',
          body: { sectionIds: sectionIds },
        });
      },
      syncCmsSectionPageImage: function (fields) {
        return request('/api/admin/cms-section-page-image', {
          method: 'POST',
          body: Object.assign({ action: 'upsert' }, fields || {}),
        });
      },
      removeCmsSectionPageImage: function (fields) {
        return request('/api/admin/cms-section-page-image', {
          method: 'POST',
          body: Object.assign({ action: 'delete' }, fields || {}),
        });
      },
      getPageCopySlots: function (pageKey) {
        var url = '/api/admin/page-copy-slots';
        if (pageKey) url += '?page_key=' + encodeURIComponent(pageKey);
        return request(url);
      },
      updatePageCopySlot: function (fields) {
        return request('/api/admin/page-copy-slot-update', { method: 'POST', body: fields });
      },
      getCmsMedia: function (opts) {
        return requestPagedList('/api/admin/cms-media', 'media', opts);
      },
      uploadCmsMedia: function (file) {
        var fd = new FormData();
        fd.append('file', file);
        return fetch(API_BASE + '/api/admin/cms-media-upload', {
          method: 'POST',
          credentials: 'include',
          body: fd,
        }).then(function (res) {
          return res.json().catch(function () { return {}; }).then(function (data) {
            if (!res.ok && !data.error) {
              if (typeof data.detail === 'string') data.error = data.detail;
              else data.error = 'HTTP ' + res.status;
            }
            data._httpStatus = res.status;
            return data;
          });
        }).catch(function () {
          return { error: '系統連線異常，請稍後再試。' };
        });
      },
      cmsMediaAction: function (id, action) {
        return request('/api/admin/cms-media-action', { method: 'POST', body: { id: id, action: action } });
      },
      /**
       * One roundtrip for admin Content panel: active tab page + pageImageKeys + site_pages.
       * Query: tab, page, page_size, optional page_key (page-images filter).
       */
      getContentBootstrap: function (opts) {
        opts = opts || {};
        var parts = ['tab=' + encodeURIComponent(opts.tab || 'banners')];
        var page = opts.page != null ? opts.page : 1;
        var size = opts.pageSize != null ? opts.pageSize : (opts.page_size != null ? opts.page_size : 10);
        parts.push('page=' + encodeURIComponent(page));
        parts.push('page_size=' + encodeURIComponent(size));
        if (opts.page_key || opts.pageKey) {
          parts.push('page_key=' + encodeURIComponent(opts.page_key || opts.pageKey));
        }
        return request('/api/admin/content-bootstrap?' + parts.join('&'));
      },
      getBanners: function (opts) {
        return requestPagedList('/api/admin/banners', 'banners', opts);
      },
      createBanner: function (fields) { return request('/api/admin/banners', { method: 'POST', body: fields }); },
      updateBanner: function (fields) { return request('/api/admin/banner-update', { method: 'POST', body: fields }); },
      bannerAction: function (id, action) { return request('/api/admin/banner-action', { method: 'POST', body: { id: id, action: action } }); },
      uploadBanner: function (file) {
        var fd = new FormData();
        fd.append('file', file);
        return fetch(API_BASE + '/api/admin/banner-upload', {
          method: 'POST',
          credentials: 'include',
          body: fd,
        }).then(function (res) {
          return res.json().catch(function () { return {}; }).then(function (data) {
            if (!res.ok && !data.error) {
              if (typeof data.detail === 'string') data.error = data.detail;
              else data.error = 'HTTP ' + res.status;
            }
            data._httpStatus = res.status;
            return data;
          });
        }).catch(function () {
          return { error: '系統連線異常，請稍後再試。' };
        });
      },
      getPageImages: function (opts) {
        return requestPagedList('/api/admin/page-images', 'pageImages', opts);
      },
      getPageImageCreateOptions: function () { return request('/api/admin/page-image-create-options'); },
      createPageImage: function (pageKey, slotKey) {
        return request('/api/admin/page-image-create', {
          method: 'POST',
          body: { pageKey: pageKey, slotKey: slotKey },
        });
      },
      updatePageImage: function (fields) { return request('/api/admin/page-image-update', { method: 'POST', body: fields }); },
      pageImageAction: function (pageKey, slotKey, action) {
        return request('/api/admin/page-image-action', {
          method: 'POST',
          body: { pageKey: pageKey, slotKey: slotKey, action: action },
        });
      },
      uploadPageImage: function (file, pageKey) {
        var fd = new FormData();
        fd.append('file', file);
        if (pageKey) fd.append('page_key', String(pageKey));
        return fetch(API_BASE + '/api/admin/page-image-upload', {
          method: 'POST',
          credentials: 'include',
          body: fd,
        }).then(function (res) {
          return res.json().catch(function () { return {}; }).then(function (data) {
            if (!res.ok && !data.error) {
              if (typeof data.detail === 'string') {
                data.error = data.detail;
              } else if (Array.isArray(data.detail) && data.detail.length) {
                data.error = data.detail.map(function (item) {
                  if (typeof item === 'string') return item;
                  return (item && (item.msg || item.message)) || '';
                }).filter(Boolean).join('；') || ('HTTP ' + res.status);
              } else {
                data.error = 'HTTP ' + res.status;
              }
            }
            data._httpStatus = res.status;
            return data;
          });
        }).catch(function () {
          return { error: '系統連線異常（伺服器可能正在重載），請稍後再試。' };
        });
      },
      getAccounts: function (qOrOpts, maybeOpts) {
        var opts = {};
        if (qOrOpts && typeof qOrOpts === 'object') {
          opts = qOrOpts;
        } else {
          opts = Object.assign({}, maybeOpts || {});
          if (qOrOpts) opts.q = qOrOpts;
        }
        return requestPagedList('/api/admin/accounts', 'accounts', opts);
      },
      getAccount: function (id) {
        return request('/api/admin/accounts/' + encodeURIComponent(id));
      },
      accountAction: function (id, action, extra) {
        var body = { id: id, action: action };
        if (extra) Object.keys(extra).forEach(function (k) { body[k] = extra[k]; });
        return request('/api/admin/account-action', { method: 'POST', body: body });
      },
      getPlugins: function () {
        return request('/api/admin/plugins');
      },
      updatePlugin: function (slug, fields) {
        var body = fields || {};
        if (slug) {
          return request('/api/admin/plugins/' + encodeURIComponent(slug), {
            method: 'PATCH',
            body: body,
          });
        }
        return request('/api/admin/plugins', { method: 'PATCH', body: body });
      },
      getFeaturedVideo: function () {
        return request('/api/admin/featured-video');
      },
      saveFeaturedVideo: function (body) {
        return request('/api/admin/featured-video', {
          method: 'PUT',
          body: body || {},
        });
      },
      syncFeaturedVideo: function () {
        return request('/api/admin/featured-video/sync', {
          method: 'POST',
          body: {},
        });
      },
      getEngagementRings: function () {
        return request('/api/admin/engagement-rings');
      },
      saveEngagementRings: function (body) {
        return request('/api/admin/engagement-rings', {
          method: 'PUT',
          body: body || {},
        });
      },
    },
  };
})(window);
