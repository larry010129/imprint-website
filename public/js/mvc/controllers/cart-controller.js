(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.Cart;
  var View = global.ImprintViews.Cart;
  var detailRequestToken = 0;

  M.createController({
    run: function () {
      if (!M.isPage('cart')) return;
      // Live /cart is HTMX-owned (#htmx-cart); skip MVC list so steppers stay wired.
      if (document.getElementById('htmx-cart')) return;
      View.setState('loading');

      M.requireSession('/cart').then(function (session) {
        if (!session) return;
        return Model.load();
      }).then(function (res) {
        if (!res) return;
        if (res.error) { View.setState('empty'); return; }
        var rows = res.items || res.cart_rows || [];
        if (!rows.length) { View.setState('empty'); return; }
        View.renderRows(rows);
        View.setState('list');
        View.updateSelection();
        bindEvents();
      }).catch(function () { View.setState('empty'); });
    },
  });

  function bindEvents() {
    var e = View.els();
    if (e.selectAll) {
      e.selectAll.addEventListener('change', function () {
        var checked = e.selectAll.checked;
        [].slice.call(e.list.querySelectorAll('.cart-item-checkbox')).forEach(function (cb) {
          cb.checked = checked;
        });
        View.updateSelection();
      });
    }
    if (e.list) {
      e.list.addEventListener('change', function (ev) {
        if (ev.target.classList.contains('cart-item-checkbox')) View.updateSelection();
      });
      e.list.addEventListener('click', function (ev) {
        var remove = ev.target.closest('.cart-item-remove');
        if (remove) {
          if (!confirm('確定要移除此品項嗎？')) return;
          Model.remove(remove.dataset.id).then(function (data) {
            if (data.success || !data.error) {
              document.getElementById('cart-item-' + remove.dataset.id)?.remove();
              if (!e.list.querySelector('.member-cart-item')) View.setState('empty');
              else View.updateSelection();
            }
          });
          return;
        }
        var dec = ev.target.closest('.cart-qty-dec');
        if (dec) {
          var rowDec = dec.closest('.member-cart-item');
          var inputDec = rowDec && rowDec.querySelector('.cart-qty-input');
          var curDec = Number(inputDec && inputDec.value || 1) || 1;
          changeQty(dec.dataset.id, curDec - 1);
          return;
        }
        var inc = ev.target.closest('.cart-qty-inc');
        if (inc) {
          var rowInc = inc.closest('.member-cart-item');
          var inputInc = rowInc && rowInc.querySelector('.cart-qty-input');
          var curInc = Number(inputInc && inputInc.value || 1) || 1;
          changeQty(inc.dataset.id, curInc + 1);
          return;
        }
        var detail = ev.target.closest('.cart-detail-btn');
        if (detail) openDetail(detail.dataset.id);
      });
      e.list.addEventListener('change', function (ev) {
        if (ev.target.classList.contains('cart-qty-input')) {
          changeQty(ev.target.dataset.id, ev.target.value);
        }
      });
    }
    if (e.checkoutBtn) {
      e.checkoutBtn.addEventListener('click', function () {
        var ids = View.updateSelection();
        if (!ids.length) return;
        global.location.href = '/checkout?items=' + ids.map(encodeURIComponent).join(',');
      });
    }
    if (e.dialogClose && e.dialog) e.dialogClose.addEventListener('click', function () { e.dialog.close(); });
  }

  function reloadCart() {
    return Model.load().then(function (res) {
      if (!res || res.error) { View.setState('empty'); return; }
      var rows = res.items || res.cart_rows || [];
      if (!rows.length) { View.setState('empty'); return; }
      View.renderRows(rows);
      View.setState('list');
      View.updateSelection();
    });
  }

  function changeQty(id, quantity) {
    var next = Number(quantity);
    if (!id || Number.isNaN(next)) return;
    if (next <= 0 && !confirm('數量為 0 將移除此品項，確定嗎？')) {
      reloadCart();
      return;
    }
    Model.setQuantity(id, next).then(function (data) {
      if (data && data.error) {
        reloadCart();
        return;
      }
      return reloadCart();
    }).catch(function () { reloadCart(); });
  }

  function openDetail(id) {
    var e = View.els();
    if (!e.dialog) return;
    var requestToken = ++detailRequestToken;
    e.dialogBody.innerHTML = window.SkeletonUI
      ? '<div class="skel-panel" aria-busy="true">' + window.SkeletonUI.line('long') + window.SkeletonUI.line('medium') + '</div>'
      : '<p class="member-state">載入中…</p>';
    e.dialog.showModal();
    Model.detail(id).then(function (data) {
      if (requestToken !== detailRequestToken || !e.dialog.open) return;
      if (data.item) View.renderDetail(data.item, data.breakdown);
      else e.dialogBody.innerHTML = '<p class="member-state">無法載入明細</p>';
    }).catch(function () {
      if (requestToken !== detailRequestToken || !e.dialog.open) return;
      e.dialogBody.innerHTML = '<p class="member-state">無法載入明細，請稍後再試。</p>';
    });
  }
})(window);
