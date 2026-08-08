/* 銘印鑽石｜訂單狀態中文對照（會員專區、查詢進度、後台共用） */
(function (global) {
  'use strict';
  var labels = {
    received: '已收到申請',
    order_confirming: '訂單已確認',
    dna_lab: 'DNA 萃取鑑定中',
    deposit_confirmed: '訂金已確認',
    in_production: '製作中',
    quality_check: '品管檢驗中',
    shipped: '已出貨',
    completed: '已完成',
    cancelled: '已取消'
  };
  global.ImprintOrderStatus = {
    labels: labels,
    /* 刻意不用 this.labels：這個函式常被單獨取出當 callback 傳遞(例如 statusLabel = window.ImprintOrderStatus.label)，
       若依賴 this 綁定，脫離原物件呼叫時 this 會是 undefined 而噴錯。 */
    label: function (status, fulfillmentMethod) {
      var code = status || '';
      if (code === 'shipped') {
        var method = (fulfillmentMethod || '').toString().toLowerCase();
        if (method === 'pickup') return '可取貨';
        return '已出貨';
      }
      return labels[code] || code || '-';
    },
    /* Admin <select> option text — one control covers both fulfillment labels. */
    optionLabel: function (status) {
      if (status === 'shipped') return '已出貨/可取貨';
      return labels[status] || status || '-';
    }
  };
})(window);
