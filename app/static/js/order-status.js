/* 銘印鑽石｜訂單狀態中文對照（會員專區、查詢進度、後台共用） */
(function (global) {
  'use strict';
  var labels = {
    received: '已收到申請',
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
    label: function (status) {
      return labels[status] || status || '-';
    }
  };
})(window);
