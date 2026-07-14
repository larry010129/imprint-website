/* 銘印鑽石｜訪客查詢訂製進度（不需登入，透過訂單編號＋電話比對） */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('trackForm');
    if (!form) return;

    var btn = document.getElementById('trackSubmitBtn');
    var msg = document.getElementById('trackFormMsg');
    var result = document.getElementById('orderResult');
    var statusLabel = window.ImprintOrderStatus ? window.ImprintOrderStatus.label : function (s) { return s; };

    function formatDate(iso) {
      if (!iso) return '-';
      var d = new Date(iso);
      return d.getFullYear() + '/' + (d.getMonth() + 1) + '/' + d.getDate();
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      msg.textContent = '';
      msg.className = 'form-msg';
      result.innerHTML = '';

      if (!window.imprintAPI) {
        msg.textContent = '系統連線異常，請稍後再試。';
        msg.className = 'form-msg is-err';
        return;
      }

      var orderNumber = form.orderNumber.value.trim();
      var phone = form.phone.value.trim();

      if (!orderNumber || !phone) {
        msg.textContent = '請輸入訂單編號與電話。';
        msg.className = 'form-msg is-err';
        return;
      }

      btn.disabled = true;
      btn.textContent = '查詢中…';

      window.imprintAPI.trackOrder(orderNumber, phone).then(function (res) {
        btn.disabled = false;
        btn.textContent = '查詢進度';

        if (res.error) {
          console.error('[track-order]', res.error);
          msg.textContent = '查詢失敗，請稍後再試。';
          msg.className = 'form-msg is-err';
          return;
        }

        var rows = res.rows || [];
        if (!rows.length) {
          msg.textContent = '查無此訂單，請確認訂單編號與電話是否正確，或透過官方 LINE 聯繫顧問。';
          msg.className = 'form-msg is-err';
          return;
        }

        var o = rows[0];
        result.innerHTML =
          '<div class="order-result-card">' +
            '<span class="status-badge">' + statusLabel(o.status) + '</span>' +
            '<div class="row"><span class="k">訂單編號</span><span class="v">' + o.order_number + '</span></div>' +
            (o.series ? '<div class="row"><span class="k">系列</span><span class="v">' + o.series + '</span></div>' : '') +
            (o.product_type ? '<div class="row"><span class="k">品項</span><span class="v">' + o.product_type + '</span></div>' : '') +
            (o.status_note ? '<div class="row"><span class="k">備註</span><span class="v">' + o.status_note + '</span></div>' : '') +
            '<div class="row"><span class="k">最後更新</span><span class="v">' + formatDate(o.updated_at) + '</span></div>' +
          '</div>';
      });
    });
  });
})();
