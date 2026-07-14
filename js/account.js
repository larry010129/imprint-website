/* 銘印鑽石｜會員專區 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var nameEl = document.getElementById('accName');
    var phoneEl = document.getElementById('accPhone');
    var emailEl = document.getElementById('accEmail');
    var ordersList = document.getElementById('ordersList');
    var logoutBtn = document.getElementById('logoutBtn');
    if (!ordersList || !window.imprintAPI) return;

    var api = window.imprintAPI;
    var statusLabel = window.ImprintOrderStatus ? window.ImprintOrderStatus.label : function (s) { return s; };

    api.getSession().then(function (res) {
      if (!res || !res.user) {
        window.location.href = 'login.html?next=account.html';
        return;
      }

      if (emailEl) emailEl.textContent = res.user.email || '-';
      if (res.profile) {
        if (nameEl) nameEl.textContent = res.profile.full_name || '-';
        if (phoneEl) phoneEl.textContent = res.profile.phone || '-';
      }

      api.getMyOrders().then(function (oRes) {
        if (oRes.error) {
          ordersList.innerHTML = '<p style="color:var(--ink-faint);font-size:13px;">載入訂單失敗，請稍後重新整理頁面。</p>';
          return;
        }
        var orders = oRes.orders || [];
        if (!orders.length) {
          ordersList.innerHTML = '<p style="color:var(--ink-faint);font-size:13px;">目前沒有訂單紀錄。若您已下單，會由顧問為您建立訂單，建立後即可在此查詢進度。</p>';
          return;
        }
        ordersList.innerHTML = orders.map(function (o) {
          return (
            '<div class="order-row">' +
              '<div class="num">' + o.order_number + '</div>' +
              '<div class="status">目前狀態：' + statusLabel(o.status) + '</div>' +
              (o.product_type ? '<div style="font-size:13px;color:var(--ink-soft);margin-top:6px;">' + (o.series ? o.series + '・' : '') + o.product_type + '</div>' : '') +
              (o.status_note ? '<div style="font-size:12.5px;color:var(--ink-faint);margin-top:6px;">' + o.status_note + '</div>' : '') +
            '</div>'
          );
        }).join('');
      });
    });

    if (logoutBtn) {
      logoutBtn.addEventListener('click', function () {
        api.logout().then(function () {
          window.location.href = 'index.html';
        });
      });
    }
  });
})();
