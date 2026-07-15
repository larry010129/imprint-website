(function (global) {
  'use strict';
  var M = global.ImprintMVC;

  function formatDate(iso) {
    if (!iso) return '-';
    var d = new Date(iso);
    return d.getFullYear() + '/' + (d.getMonth() + 1) + '/' + d.getDate();
  }

  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.TrackOrder = {
    els: function () {
      return {
        form: document.getElementById('trackForm'),
        btn: document.getElementById('trackSubmitBtn'),
        msg: document.getElementById('trackFormMsg'),
        result: document.getElementById('orderResult'),
      };
    },
    setMsg: function (text, type) {
      var e = this.els();
      if (!e.msg) return;
      e.msg.textContent = text || '';
      e.msg.className = 'form-msg' + (type ? ' is-' + type : '');
    },
    setLoading: function (loading) {
      var e = this.els();
      if (!e.btn) return;
      e.btn.disabled = loading;
      e.btn.textContent = loading ? '查詢中…' : '查詢進度';
    },
    clearResult: function () {
      var e = this.els();
      if (e.result) e.result.innerHTML = '';
    },
    renderResult: function (order, statusLabel) {
      var e = this.els();
      if (!e.result) return;
      e.result.innerHTML =
        '<div class="order-result-card">' +
          '<span class="status-badge">' + M.escapeHtml(statusLabel(order.status)) + '</span>' +
          '<div class="row"><span class="k">訂單編號</span><span class="v">' + M.escapeHtml(order.order_number) + '</span></div>' +
          (order.series ? '<div class="row"><span class="k">系列</span><span class="v">' + M.escapeHtml(order.series) + '</span></div>' : '') +
          (order.product_type ? '<div class="row"><span class="k">品項</span><span class="v">' + M.escapeHtml(order.product_type) + '</span></div>' : '') +
          (order.status_note ? '<div class="row"><span class="k">備註</span><span class="v">' + M.escapeHtml(order.status_note) + '</span></div>' : '') +
          '<div class="row"><span class="k">最後更新</span><span class="v">' + formatDate(order.updated_at) + '</span></div>' +
        '</div>';
    },
  };
})(window);
