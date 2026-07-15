(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.TrackOrder;
  var View = global.ImprintViews.TrackOrder;

  M.createController({
    run: function () {
      if (!M.isPage('track-order')) return;
      var e = View.els();
      if (!e.form) return;

      var statusLabel = global.ImprintOrderStatus ? global.ImprintOrderStatus.label : function (s) { return s; };

      e.form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        View.setMsg('');
        View.clearResult();

        if (!M.api()) {
          View.setMsg('系統連線異常，請稍後再試。', 'err');
          return;
        }

        var orderNumber = e.form.orderNumber.value.trim();
        var phone = e.form.phone.value.trim();
        if (!orderNumber || !phone) {
          View.setMsg('請輸入訂單編號與電話。', 'err');
          return;
        }

        View.setLoading(true);
        Model.track(orderNumber, phone).then(function (res) {
          View.setLoading(false);
          if (res.error) {
            View.setMsg('查詢失敗，請稍後再試。', 'err');
            return;
          }
          var rows = res.rows || [];
          if (!rows.length) {
            View.setMsg('查無此訂單，請確認訂單編號與電話是否正確，或透過官方 LINE 聯繫顧問。', 'err');
            return;
          }
          View.renderResult(rows[0], statusLabel);
        });
      });
    },
  });
})(window);
