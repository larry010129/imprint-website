/* Admin orders — checkboxes, bulk status, cancel with reason */
(function () {
  'use strict';

  var api = window.imprintAPI;
  if (!api || !api.admin) return;

  var tbody = document.getElementById('ordersTableBody');
  if (!tbody) return;

  var bulkBar = document.getElementById('ordersBulkBar');
  var bulkCount = document.getElementById('ordersBulkCount');
  var bulkStatus = document.getElementById('ordersBulkStatus');
  var bulkApply = document.getElementById('ordersBulkApply');
  var bulkClear = document.getElementById('ordersBulkClear');
  var selectAll = document.getElementById('ordersSelectAll');
  var cancelDialog = document.getElementById('orderCancelDialog');
  var cancelForm = document.getElementById('orderCancelForm');
  var cancelPreset = document.getElementById('orderCancelPreset');
  var cancelCustomWrap = document.getElementById('orderCancelCustomWrap');
  var cancelCustom = document.getElementById('orderCancelCustom');
  var cancelError = document.getElementById('orderCancelError');

  var STATUS_OPTIONS = [
    'received', 'dna_lab', 'deposit_confirmed', 'in_production',
    'quality_check', 'shipped', 'completed'
  ];
  var BULK_STATUS_OPTIONS = STATUS_OPTIONS.concat(['cancelled']);

  var CANCEL_REASONS = [
    { value: 'customer_request', label: '客戶要求取消' },
    { value: 'no_contact', label: '無法聯繫客戶' },
    { value: 'out_of_stock', label: '庫存／原料不足' },
    { value: 'payment_incomplete', label: '付款未完成' },
    { value: 'duplicate_order', label: '重複訂單' },
    { value: '__custom__', label: '其他（請說明）' },
  ];

  var STATUS_COLORS = {
    received: '#e0a458',
    dna_lab: '#6c9bd1',
    deposit_confirmed: '#5bc0de',
    in_production: '#9cefef',
    quality_check: '#5ecfcf',
    shipped: '#9b7fd4',
    completed: '#4caf7d',
    cancelled: '#8a817b'
  };

  var CATEGORY_LABELS = {
    pendant: '項墜', ring: '戒指', earring: '耳環', bracelet: '手鍊', chain: '鏈條'
  };
  var GOLD_LABELS = { '9k': '9K', '14k': '14K', '18k': '18K', pt950: 'PT950', s925: 'S925' };
  var COLOR_LABELS = { white: 'K白', yellow: 'K黃', rose: '玫瑰金' };

  var statusLabel = window.ImprintOrderStatus
    ? window.ImprintOrderStatus.label
    : function (s) { return s; };

  var cancelContext = { mode: 'single', ids: [] };
  var _loaded = false;

  function esc(s) {
    return window.AdminPanel && window.AdminPanel.escapeHtml
      ? window.AdminPanel.escapeHtml(s)
      : String(s == null ? '' : s);
  }

  function orderImageUrl(o) {
    if (window.AdminImageUrls && window.AdminImageUrls.orderPhoto) {
      return window.AdminImageUrls.orderPhoto(o.image_url, o.category, o.product_type, o.color);
    }
    return o.image_url || '';
  }

  function orderImageFallback(o) {
    if (window.ShopAssets) {
      var thumb = window.ShopAssets.categoryThumb(o.category);
      if (thumb) return thumb;
    }
    return window.AdminImageUrls ? window.AdminImageUrls.categoryFallback(o.category) : '';
  }

  function formatDateTime(iso) {
    if (!iso) return '-';
    var d = new Date(iso);
    var pad = function (n) { return n < 10 ? '0' + n : n; };
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' '
      + pad(d.getHours()) + ':' + pad(d.getMinutes());
  }

  function formatMoney(n) {
    if (n == null || n === '') return '-';
    return Number(n).toLocaleString('zh-TW', { maximumFractionDigits: 0 });
  }

  function isCancelled(o) {
    return o.status === 'cancelled' || o.status === 'canceled';
  }

  function checkboxHtml(id, checked, disabled) {
    return (
      '<label class="adx-check">' +
        '<input type="checkbox" class="adx-check-input order-row-check" data-order-id="' + esc(id) + '"' +
          (checked ? ' checked' : '') + (disabled ? ' disabled' : '') + ' aria-label="選取訂單">' +
        '<span class="adx-check-ui" aria-hidden="true"></span>' +
      '</label>'
    );
  }

  function statusIndex(status) {
    var i = STATUS_OPTIONS.indexOf(status);
    return i < 0 ? 0 : i;
  }

  function thumbHtml(url, alt, fallback) {
    if (!url) return '<span class="order-style-thumb--empty">—</span>';
    var fb = fallback ? ' data-fallback="' + esc(fallback) + '"' : '';
    return '<img class="order-style-thumb" src="' + esc(url) + '" alt="' + esc(alt || '') + '" loading="lazy"' + fb + '>';
  }

  function styleName(o) {
    if (o.product_type && o.series) return esc(o.series) + ' · ' + esc(o.product_type);
    if (o.product_type) return esc(o.product_type);
    if (o.series) return esc(o.series);
    return esc(o.category ? (CATEGORY_LABELS[o.category] || o.category) : '-');
  }

  function diamondLabel(o) {
    if (o.diamond_kind === 'fancy') return '彩鑽' + (o.fancy_color ? '（' + o.fancy_color + '）' : '');
    return '白鑽';
  }

  function subtotal(o) {
    if (o.total_price == null) return null;
    return Number(o.total_price) - Number(o.tax_amount_twd || 0);
  }

  function progressHtml(status) {
    if (isCancelled({ status: status })) {
      return '<div class="order-detail-status"><p class="order-detail-cancelled">此訂單已取消</p></div>';
    }
    var idx = statusIndex(status);
    var steps = STATUS_OPTIONS.map(function (s, i) {
      var state = i < idx ? 'complete' : (i === idx ? 'current' : 'incomplete');
      var color = STATUS_COLORS[s] || '#9cefef';
      var barStyle = state === 'incomplete' ? '' : ' style="--step-color:' + color + '"';
      return (
        '<div class="order-steps-item">' +
          '<div class="order-steps-bar order-steps-bar--' + state + '" data-step="' + s + '"' + barStyle + '></div>' +
          '<div class="order-steps-label order-steps-label--' + state + '">' + esc(statusLabel(s)) + '</div>' +
        '</div>'
      );
    }).join('');
    return '<div class="order-detail-status"><div class="order-steps" role="list">' + steps + '</div></div>';
  }

  function detailPanel(o) {
    var cat = CATEGORY_LABELS[o.category] || o.category || '-';
    var gold = GOLD_LABELS[o.gold_purity] || o.gold_purity || '-';
    var color = COLOR_LABELS[o.color] || o.color || '-';
    var img = orderImageUrl(o);
    var imgFb = orderImageFallback(o);
    var cancelNote = isCancelled(o) && o.cancel_reason
      ? '<p class="order-detail-cancel-reason">取消原因：' + esc(o.cancel_reason) + '</p>'
      : '';

    return (
      '<div class="order-detail-panel">' +
        '<div class="order-detail-layout">' +
          '<div class="order-detail-gallery">' +
            '<div class="order-detail-preview">' + thumbHtml(img, styleName(o), imgFb) + '</div>' +
            '<p class="order-detail-product-name">' + styleName(o) + '</p>' +
            '<p class="order-detail-product-meta">' + esc(cat) + ' · ' + esc(gold) + ' · ' + esc(color) + ' · ' + esc(diamondLabel(o)) + '</p>' +
            cancelNote +
          '</div>' +
          '<div class="order-detail-specs">' +
            '<div class="order-detail-grid">' +
              specItem('成色', gold) + specItem('顏色', color) + specItem('克拉', o.carat || '-') +
              specItem('鑽石顏色', diamondLabel(o)) + specItem('計價金價', formatMoney(o.gold_rate_per_gram)) +
              specItem('重量 (克)', o.weight_grams != null ? Number(o.weight_grams).toFixed(3) : '-') +
              specItem('戒圍', o.ring_size || '-') + specItem('戒圈刻字', o.engraving_band || '-') +
              specItem('腰圍刻字', o.engraving_girdle || '-') + specItem('總價 (NT$)', formatMoney(subtotal(o))) +
              specItem('稅金 5% (NT$)', formatMoney(o.tax_amount_twd)) +
              specItem('客戶', (o.customer_name || '-') + ' · ' + (o.customer_phone || '')) +
            '</div>' + progressHtml(o.status) +
          '</div></div></div>'
    );
  }

  function specItem(label, value) {
    return '<div class="order-detail-item"><span class="order-detail-label">' + esc(label) +
      '</span><span class="order-detail-value">' + esc(String(value)) + '</span></div>';
  }

  function statusSelect(o) {
    if (isCancelled(o)) {
      return '<span class="order-status-badge order-status-badge--cancelled">' + statusLabel('cancelled') + '</span>';
    }
    var opts = STATUS_OPTIONS.map(function (s) {
      return '<option value="' + s + '"' + (s === o.status ? ' selected' : '') + '>' + statusLabel(s) + '</option>';
    }).join('');
    return '<select class="status-select" data-status="' + esc(o.status) + '" data-order-id="' + esc(o.id) + '">' + opts + '</select>';
  }

  function selectedIds() {
    return Array.from(tbody.querySelectorAll('.order-row-check:checked')).map(function (cb) {
      return cb.dataset.orderId;
    });
  }

  function updateBulkBar() {
    var ids = selectedIds();
    var n = ids.length;
    if (bulkBar) bulkBar.hidden = n === 0;
    if (bulkCount) bulkCount.textContent = '已選 ' + n + ' 筆';
    if (selectAll) {
      var checks = tbody.querySelectorAll('.order-row-check:not(:disabled)');
      selectAll.checked = checks.length > 0 && ids.length === checks.length;
      selectAll.indeterminate = ids.length > 0 && ids.length < checks.length;
    }
  }

  function fillBulkStatusSelect() {
    if (!bulkStatus) return;
    bulkStatus.innerHTML = BULK_STATUS_OPTIONS.map(function (s) {
      return '<option value="' + s + '">' + statusLabel(s) + '</option>';
    }).join('');
  }

  function fillCancelPresetSelect() {
    if (!cancelPreset) return;
    cancelPreset.innerHTML = '<option value="" disabled selected>請選擇原因</option>' +
      CANCEL_REASONS.map(function (r) {
        return '<option value="' + r.value + '">' + esc(r.label) + '</option>';
      }).join('');
  }

  function resolveCancelReason() {
    if (!cancelPreset) return '';
    var preset = cancelPreset.value;
    if (!preset) return '';
    if (preset === '__custom__') {
      return String(cancelCustom && cancelCustom.value || '').trim();
    }
    var match = CANCEL_REASONS.find(function (r) { return r.value === preset; });
    return match ? match.label : preset;
  }

  function openCancelDialog(ids) {
    if (!cancelDialog || !ids.length) return;
    cancelContext = { mode: ids.length > 1 ? 'bulk' : 'single', ids: ids.slice() };
    if (cancelPreset) cancelPreset.selectedIndex = 0;
    if (cancelCustom) cancelCustom.value = '';
    if (cancelCustomWrap) cancelCustomWrap.hidden = true;
    if (cancelError) cancelError.hidden = true;
    cancelDialog.showModal();
  }

  function closeCancelDialog() {
    cancelDialog?.close();
    cancelContext = { mode: 'single', ids: [] };
  }

  function submitCancel() {
    var reason = resolveCancelReason();
    if (!reason) {
      if (cancelError) {
        cancelError.textContent = cancelPreset && cancelPreset.value === '__custom__'
          ? '請填寫其他原因說明'
          : '請選擇取消原因';
        cancelError.hidden = false;
      }
      return;
    }
    if (cancelError) cancelError.hidden = true;

    var btn = document.getElementById('orderCancelConfirm');
    if (btn) { btn.disabled = true; btn.textContent = '處理中…'; }

    var req;
    if (cancelContext.mode === 'bulk') {
      req = api.admin.bulkUpdateOrders(cancelContext.ids, 'cancelled', reason);
    } else {
      req = api.admin.cancelOrder(cancelContext.ids[0], reason);
    }

    req.then(function (res) {
      if (btn) { btn.disabled = false; btn.textContent = '確認取消'; }
      if (res.error) {
        if (cancelError) {
          cancelError.textContent = typeof res.error === 'string' ? res.error : (res.error.message || '取消失敗');
          cancelError.hidden = false;
        }
        return;
      }
      closeCancelDialog();
      load(null, true, true);
    });
  }

  function applyBulkStatus() {
    var ids = selectedIds();
    if (!ids.length || !bulkStatus) return;
    var status = bulkStatus.value;
    if (status === 'cancelled') {
      openCancelDialog(ids);
      return;
    }
    if (!confirm('確定將 ' + ids.length + ' 筆訂單狀態改為「' + statusLabel(status) + '」？')) return;
    bulkApply.disabled = true;
    api.admin.bulkUpdateOrders(ids, status).then(function (res) {
      bulkApply.disabled = false;
      if (res.error) {
        alert('批次更新失敗：' + (res.error.message || res.error));
        return;
      }
      load(null, true, true);
    });
  }

  function renderRows(orders) {
    if (!orders.length) {
      tbody.innerHTML = '<tr><td colspan="11" class="orders-empty">目前沒有訂單</td></tr>';
      updateBulkBar();
      return;
    }

    var html = '';
    orders.forEach(function (o) {
      var detailId = 'admin-detail-' + o.id;
      var img = orderImageUrl(o);
      var imgFb = orderImageFallback(o);
      var cat = CATEGORY_LABELS[o.category] || o.category || '-';
      var cancelled = isCancelled(o);

      html +=
        '<tr id="admin-row-' + esc(o.id) + '" class="order-row-main' + (cancelled ? ' is-cancelled' : '') + '" data-id="' + esc(o.id) + '" data-status="' + esc(o.status) + '"' +
          ' data-sort-number="' + esc(o.order_number || o.id) + '"' +
          ' data-sort-created="' + esc(o.created_at || '') + '"' +
          ' data-sort-customer="' + esc(o.customer_name || '') + '"' +
          ' data-sort-category="' + esc(cat) + '"' +
          ' data-sort-style="' + esc((o.series || '') + (o.product_type || '')) + '"' +
          ' data-sort-total="' + esc(String(o.total_price != null ? o.total_price : '')) + '"' +
          ' data-sort-status="' + esc(o.status || '') + '">' +
          '<td class="col-check">' + checkboxHtml(o.id, false, cancelled) + '</td>' +
          '<td>' + esc(o.order_number || o.id) + '</td>' +
          '<td>' + formatDateTime(o.created_at) + '</td>' +
          '<td><strong>' + esc(o.customer_name || '銘印') + '</strong></td>' +
          '<td>' + esc(cat) + '</td>' +
          '<td class="col-image">' + thumbHtml(img, o.order_number, imgFb) + '</td>' +
          '<td>' + styleName(o) + '</td>' +
          '<td class="col-price col-price--total">' + formatMoney(o.total_price) + '</td>' +
          '<td class="col-status"><span class="order-status-badge order-status-badge--' + esc(o.status) + '">' + statusLabel(o.status) + '</span></td>' +
          '<td class="col-actions admin-actions-cell"><div class="admin-actions-inner">' + statusSelect(o) +
            (cancelled ? '' : '<button type="button" class="admin-delete-btn" data-cancel-order="' + esc(o.id) + '" title="取消訂單" aria-label="取消訂單">✕</button>') +
          '</div></td>' +
          '<td class="col-detail"><button type="button" class="order-detail-btn" data-target="' + detailId + '" aria-expanded="false">查看詳情</button></td>' +
        '</tr>' +
        '<tr class="order-detail-row" id="' + detailId + '" hidden><td colspan="11">' + detailPanel(o) + '</td></tr>';
    });
    tbody.innerHTML = html;
    bindRowEvents();
    updateBulkBar();
    var table = tbody.closest('table');
    if (table && window.AdminTableSort) window.AdminTableSort.bind(table);
  }

  function bindRowEvents() {
    tbody.querySelectorAll('.order-row-check').forEach(function (cb) {
      cb.addEventListener('change', updateBulkBar);
    });

    tbody.querySelectorAll('.status-select').forEach(function (sel) {
      sel.addEventListener('change', function () {
        var id = sel.dataset.orderId;
        var status = sel.value;
        sel.dataset.status = status;
        sel.disabled = true;
        api.admin.updateOrderStatus(id, status, null).then(function (res) {
          sel.disabled = false;
          if (res.error) {
            alert('更新失敗：' + (res.error.message || res.error));
            load(null, true, true);
            return;
          }
          load(null, true, true);
        });
      });
    });

    tbody.querySelectorAll('[data-cancel-order]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        openCancelDialog([btn.dataset.cancelOrder]);
      });
    });
  }

  function load(query, silent, force) {
    if (!query && _loaded && !force) return;
    if (!silent) tbody.innerHTML = '<tr><td colspan="11" class="orders-empty">載入中…</td></tr>';
    var req = query
      ? fetch('/api/admin/orders?q=' + encodeURIComponent(query), { credentials: 'include' }).then(function (r) { return r.json(); })
      : api.admin.getOrders();
    req.then(function (res) {
      if (res.error) {
        tbody.innerHTML = '<tr><td colspan="11" class="orders-empty">載入失敗</td></tr>';
        return;
      }
      renderRows(res.orders || []);
      if (!query) _loaded = true;
    });
  }

  function ensureLoaded() {
    load(null, _loaded);
  }

  fillBulkStatusSelect();
  fillCancelPresetSelect();

  selectAll?.addEventListener('change', function () {
    var on = selectAll.checked;
    tbody.querySelectorAll('.order-row-check:not(:disabled)').forEach(function (cb) {
      cb.checked = on;
    });
    updateBulkBar();
  });

  bulkApply?.addEventListener('click', applyBulkStatus);
  bulkClear?.addEventListener('click', function () {
    tbody.querySelectorAll('.order-row-check').forEach(function (cb) { cb.checked = false; });
    if (selectAll) { selectAll.checked = false; selectAll.indeterminate = false; }
    updateBulkBar();
  });

  cancelPreset?.addEventListener('change', function () {
    if (cancelCustomWrap) cancelCustomWrap.hidden = cancelPreset.value !== '__custom__';
    if (cancelError) cancelError.hidden = true;
  });

  cancelForm?.addEventListener('submit', function (e) {
    e.preventDefault();
    submitCancel();
  });

  document.getElementById('orderCancelDismiss')?.addEventListener('click', closeCancelDialog);
  document.getElementById('orderCancelClose')?.addEventListener('click', closeCancelDialog);

  var searchInput = document.getElementById('ordersSearch');
  if (searchInput) {
    var timer;
    searchInput.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(function () { load(searchInput.value.trim()); }, 300);
    });
  }

  document.getElementById('btnNewOrder')?.addEventListener('click', function () {
    if (window.AdminPanel && window.AdminPanel.openNewOrderModal) {
      window.AdminPanel.openNewOrderModal(load);
    }
  });

  window.AdminOrdersPanel = { load: load, ensureLoaded: ensureLoaded };
})();
