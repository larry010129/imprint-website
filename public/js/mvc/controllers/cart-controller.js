(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.Cart;
  var View = global.ImprintViews.Cart;

  M.createController({
    run: function () {
      if (!M.isPage('cart')) return;
      View.setState('loading');

      M.requireSession('cart.html').then(function (session) {
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
        var detail = ev.target.closest('.cart-detail-btn');
        if (detail) openDetail(detail.dataset.id);
      });
    }
    if (e.checkoutBtn) {
      e.checkoutBtn.addEventListener('click', function () {
        var ids = View.updateSelection();
        if (!ids.length) return;
        global.location.href = '/checkout.html?items=' + ids.map(encodeURIComponent).join(',');
      });
    }
    if (e.dialogClose && e.dialog) e.dialogClose.addEventListener('click', function () { e.dialog.close(); });
  }

  function openDetail(id) {
    var e = View.els();
    if (!e.dialog) return;
    e.dialogBody.innerHTML = window.SkeletonUI
      ? '<div class="skel-panel" aria-busy="true">' + window.SkeletonUI.line('long') + window.SkeletonUI.line('medium') + '</div>'
      : '<p class="member-state">載入中…</p>';
    e.dialog.showModal();
    Model.detail(id).then(function (data) {
      if (data.item) View.renderDetail(data.item);
      else e.dialogBody.innerHTML = '<p class="member-state">無法載入明細</p>';
    });
  }
})(window);
