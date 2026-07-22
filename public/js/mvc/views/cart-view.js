(function (global) {
  'use strict';
  var M = global.ImprintMVC;

  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.Cart = {
    els: function () {
      return {
        loading: document.getElementById('cart-loading'),
        empty: document.getElementById('cart-empty'),
        wrap: document.getElementById('cart-list-wrap'),
        list: document.getElementById('cart-list'),
        selectedLabel: document.getElementById('cart-selected-label'),
        selectedTotal: document.getElementById('cart-selected-total'),
        checkoutBtn: document.getElementById('cart-checkout-btn'),
        selectAll: document.getElementById('cart-select-all'),
        dialog: document.getElementById('cart-detail-dialog'),
        dialogBody: document.getElementById('cart-detail-body'),
        dialogClose: document.getElementById('cart-detail-close'),
      };
    },
    setState: function (state) {
      var e = this.els();
      M.show(e.loading, state === 'loading');
      M.show(e.empty, state === 'empty');
      M.show(e.wrap, state === 'list');
    },
    renderRows: function (rows) {
      var e = this.els();
      if (!e.list) return;
      e.list.innerHTML = rows.map(function (row) {
        var item = row.item || row;
        var specs = row.specs || item.specs || {};
        var id = item.id;
        var price = item.total_price != null ? item.total_price : item.totalPrice;
        var img = row.image_url || item.image_url || '';
        var summary = item.summary_zh || item.summary || ('#' + id);
        var meta = [specs.category, specs.carat ? specs.carat + ' ct' : '', specs.gold, specs.color].filter(Boolean).join(' · ');
        return (
          '<li class="member-cart-item" id="cart-item-' + id + '" data-id="' + id + '" data-price="' + (price || 0) + '">' +
            '<label><input type="checkbox" class="cart-item-checkbox" value="' + id + '" checked></label>' +
            (img ? '<img class="member-cart-item__thumb" src="' + M.escapeHtml(img) + '" alt="" loading="lazy">' :
              '<span class="member-cart-item__thumb member-cart-item__thumb--empty">💎</span>') +
            '<div><div class="member-cart-item__title">' + M.escapeHtml(summary) + '</div>' +
            (meta ? '<div class="member-cart-item__meta">' + M.escapeHtml(meta) + '</div>' : '') + '</div>' +
            '<div class="member-cart-item__price">' + M.formatPrice(price) + '</div>' +
            '<div class="member-cart-item__actions">' +
              '<button type="button" class="btn-text cart-detail-btn" data-id="' + id + '">明細</button>' +
              '<a href="/shop/calculator/?cart_edit=' + encodeURIComponent(id) + '" class="btn-text">編輯</a>' +
              '<button type="button" class="btn-text cart-item-remove" data-id="' + id + '">移除</button>' +
            '</div></li>'
        );
      }).join('');
    },
    updateSelection: function () {
      var e = this.els();
      if (!e.list) return;
      var boxes = [].slice.call(e.list.querySelectorAll('.cart-item-checkbox'));
      var selected = boxes.filter(function (cb) { return cb.checked; });
      var total = 0;
      selected.forEach(function (cb) {
        var row = cb.closest('.member-cart-item');
        total += Number(row && row.dataset.price || 0);
      });
      if (e.selectedLabel) e.selectedLabel.textContent = '已選 ' + selected.length + ' 件';
      if (e.selectedTotal) e.selectedTotal.textContent = M.formatPrice(total);
      if (e.checkoutBtn) e.checkoutBtn.disabled = selected.length === 0;
      if (e.selectAll) {
        e.selectAll.checked = boxes.length > 0 && selected.length === boxes.length;
        e.selectAll.indeterminate = selected.length > 0 && selected.length < boxes.length;
      }
      return selected.map(function (cb) { return String(cb.value); });
    },
    renderDetail: function (item) {
      var e = this.els();
      if (!e.dialogBody) return;
      e.dialogBody.innerHTML = '<p class="member-state">' + M.escapeHtml(item.summary || '') + '</p><p><strong>' + M.formatPrice(item.total_price || item.totalPrice) + '</strong></p>';
    },
  };
})(window);
