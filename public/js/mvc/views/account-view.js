(function (global) {
  'use strict';
  var M = global.ImprintMVC;

  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.Account = {
    els: function () {
      return {
        name: document.getElementById('accName'),
        phone: document.getElementById('accPhone'),
        email: document.getElementById('accEmail'),
        ordersList: document.getElementById('ordersList'),
        logoutBtn: document.getElementById('logoutBtn'),
      };
    },
    renderProfile: function (session) {
      var e = this.els();
      if (e.email) e.email.textContent = (session.user && session.user.email) || '-';
      if (session.profile) {
        if (e.name) e.name.textContent = session.profile.full_name || '-';
        if (e.phone) e.phone.textContent = session.profile.phone || '-';
      }
    },
    renderOrders: function (orders, statusLabel) {
      var e = this.els();
      if (!e.ordersList) return;
      if (!orders.length) {
        e.ordersList.innerHTML = '<p style="color:var(--ink-faint);font-size:13px;">目前沒有訂單紀錄。若您已下單，會由顧問為您建立訂單，建立後即可在此查詢進度。</p>';
        return;
      }
      e.ordersList.innerHTML = orders.map(function (o) {
        return (
          '<div class="order-row">' +
            '<div class="num">' + M.escapeHtml(o.order_number) + '</div>' +
            '<div class="status">目前狀態：' + M.escapeHtml(statusLabel(o.status)) + '</div>' +
            (o.product_type ? '<div style="font-size:13px;color:var(--ink-soft);margin-top:6px;">' + M.escapeHtml((o.series ? o.series + '・' : '') + o.product_type) + '</div>' : '') +
            (o.status_note ? '<div style="font-size:12.5px;color:var(--ink-faint);margin-top:6px;">' + M.escapeHtml(o.status_note) + '</div>' : '') +
          '</div>'
        );
      }).join('');
    },
    renderOrdersError: function () {
      var e = this.els();
      if (e.ordersList) {
        e.ordersList.innerHTML = '<p style="color:var(--ink-faint);font-size:13px;">載入訂單失敗，請稍後重新整理頁面。</p>';
      }
    },
  };
})(window);
