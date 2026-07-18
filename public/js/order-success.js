(function () {
  'use strict';

  var params = new URLSearchParams(window.location.search);
  var updated = params.get('updated') === '1';
  var order = (params.get('order') || '').trim();
  var ordersRaw = (params.get('orders') || '').trim();
  var orderList = order
    ? [order]
    : ordersRaw.split(',').map(function (s) { return s.trim(); }).filter(Boolean);

  var title = document.getElementById('success-title');
  var lead = document.getElementById('success-lead');
  var orderEl = document.getElementById('success-order-no');

  if (updated) {
    if (title) title.textContent = '訂單已更新';
    if (lead) lead.textContent = '您的訂單規格已重新儲存，我們會依更新內容為您處理。';
  }

  if (orderEl && orderList.length) {
    orderEl.hidden = false;
    orderEl.textContent = orderList.length === 1
      ? '訂單編號：' + orderList[0]
      : '訂單編號：' + orderList.join('、');
  }
})();
