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
  var cancelDialog = document.getElementById('orderCancelDialog');
  var cancelForm = document.getElementById('orderCancelForm');
  var cancelChips = document.getElementById('orderCancelChips');
  var cancelReasonInput = document.getElementById('orderCancelReason');
  var cancelError = document.getElementById('orderCancelError');

  var STATUS_OPTIONS = [
    'received', 'order_confirming', 'deposit_confirmed', 'dna_lab',
    'in_production', 'quality_check', 'shipped', 'completed'
  ];
  var BULK_STATUS_OPTIONS = STATUS_OPTIONS.concat(['cancelled']);

  // Admin: chips fill the typing box (editable). Broader cancel than member.
  var CANCEL_REASON_CHIPS = [
    '客戶要求取消',
    '無法聯繫客戶',
    '庫存／原料不足',
    '付款未完成',
    '重複訂單',
    '其他',
  ];

  var _pageIndex = 0;
  var _pageSize = 20;
  var _total = 0;
  var _lastQuery = '';

  var STATUS_COLORS = {
    received: '#e0a458',
    order_confirming: '#e09a6a',
    dna_lab: '#6c9bd1',
    deposit_confirmed: '#5bc0de',
    in_production: '#9cefef',
    quality_check: '#5ecfcf',
    shipped: '#9b7fd4',
    completed: '#4caf7d',
    cancelled: '#8a817b'
  };

  var CATEGORY_LABELS = {
    diamond: '紀念鑽石', pendant: '項墜', ring: '戒指', earring: '耳環', bracelet: '手鍊', chain: '鏈條'
  };
  var GOLD_LABELS = { '9k': '9K', '14k': '14K', '18k': '18K', pt950: 'PT950', s925: 'S925' };
  var COLOR_LABELS = { white: 'K白', yellow: 'K黃', rose: '玫瑰金' };
  var FULFILLMENT_LABELS = { pickup: '門市自取', delivery: '宅配到府' };

  var statusLabel = window.ImprintOrderStatus
    ? window.ImprintOrderStatus.label
    : function (s) { return s; };
  var statusOptionLabel = window.ImprintOrderStatus && window.ImprintOrderStatus.optionLabel
    ? window.ImprintOrderStatus.optionLabel
    : statusLabel;

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

  function styleNamePlain(o) {
    if (o.product_type && o.series) return o.series + ' · ' + o.product_type;
    if (o.product_type) return o.product_type;
    if (o.series) return o.series;
    return o.category ? (CATEGORY_LABELS[o.category] || o.category) : '-';
  }

  function priceBreakdownLines(o) {
    var lines = '';
    if (o.diamond_price_twd != null && Number(o.diamond_price_twd) > 0) {
      lines += specItem('鑽石價格 (NT$)', formatMoney(o.diamond_price_twd));
    }
    var metalwork = Number(o.taijin_price_twd || 0) + Number(o.labor_price_twd || 0);
    if (metalwork > 0) {
      lines += specItem('金工價格 (NT$)', formatMoney(metalwork));
    }
    if (o.chain_total_twd != null && Number(o.chain_total_twd) > 0) {
      lines += specItem('搭配鏈條 (NT$)', formatMoney(o.chain_total_twd));
    }
    var discount = Number(o.discount_amount || 0);
    var subtotal = o.subtotal_before_discount != null ? Number(o.subtotal_before_discount) : null;
    if (discount > 0) {
      if (subtotal != null) {
        lines += specItem('小計 (NT$)', formatMoney(subtotal));
      }
      var couponLabel = o.coupon_code ? '優惠折抵 (' + o.coupon_code + ')' : '優惠折抵';
      lines += specItem(couponLabel + ' (NT$)', '−' + formatMoney(discount));
    }
    lines += specItem('總計 (NT$)', formatMoney(o.total_price));
    return lines;
  }

  function formatStatusDate(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleDateString('en-US', {
      timeZone: 'Asia/Taipei',
      month: 'numeric',
      day: 'numeric',
    });
  }

  function statusTimestamps(order) {
    var stamps = order && order.status_timestamps;
    if (!stamps) return {};
    if (typeof stamps === 'string') {
      try { return JSON.parse(stamps) || {}; } catch (e) { return {}; }
    }
    return stamps;
  }

  function progressHtml(order) {
    var status = typeof order === 'string' ? order : (order && order.status);
    if (isCancelled({ status: status })) {
      return '<div class="order-detail-status"><p class="order-detail-cancelled">此訂單已取消</p></div>';
    }
    var fulfillment = typeof order === 'object' && order ? order.fulfillment_method : null;
    var stamps = typeof order === 'object' && order ? statusTimestamps(order) : {};
    var serverSteps = typeof order === 'object' && order && Array.isArray(order.status_steps)
      ? order.status_steps
      : null;
    var idx = statusIndex(status);
    var steps = (serverSteps || STATUS_OPTIONS.map(function (s, i) {
      var state = i < idx ? 'complete' : (i === idx ? 'current' : 'incomplete');
      var date = state === 'incomplete' ? '' : formatStatusDate(stamps[s]);
      return {
        code: s,
        label: statusLabel(s, fulfillment),
        state: state,
        color: STATUS_COLORS[s] || '#9cefef',
        date: date,
      };
    })).map(function (step) {
      var state = step.state;
      var color = step.color || STATUS_COLORS[step.code] || '#9cefef';
      var barStyle = state === 'incomplete' ? '' : ' style="--step-color:' + color + '"';
      var date = step.date || '';
      var dateHtml = date
        ? '<span class="order-steps-date">' + esc(date) + '</span>'
        : '';
      var label = step.code === 'shipped'
        ? statusLabel('shipped', fulfillment)
        : (step.label || statusLabel(step.code, fulfillment));
      return (
        '<div class="order-steps-item">' +
          '<div class="order-steps-bar order-steps-bar--' + state + '" data-step="' + esc(step.code) + '"' + barStyle + '></div>' +
          '<div class="order-steps-label order-steps-label--' + state + '">' +
            esc(label) + dateHtml +
          '</div>' +
        '</div>'
      );
    }).join('');
    return '<div class="order-detail-status"><div class="order-steps" role="list">' + steps + '</div></div>';
  }

  function orderLengthCm(o) {
    var raw = o.chain_length_cm != null && o.chain_length_cm !== ''
      ? o.chain_length_cm
      : (o.lengthCm != null && o.lengthCm !== ''
        ? o.lengthCm
        : (o.chainLength != null && o.chainLength !== '' ? o.chainLength : null));
    return raw == null || raw === '' ? null : raw;
  }

  function sizeSpecRow(o) {
    var cat = String(o.category || '').toLowerCase();
    if (cat === 'ring') {
      return o.ring_size != null && o.ring_size !== ''
        ? specItem('戒圍', o.ring_size)
        : '';
    }
    if (cat === 'pendant' || cat === 'chain' || cat === 'bracelet') {
      var len = orderLengthCm(o);
      return len != null ? specItem('長度', String(len) + ' cm') : '';
    }
    return '';
  }

  function fulfillmentRows(o) {
    var method = o.fulfillment_method;
    var label = FULFILLMENT_LABELS[method] || method || '-';
    var rows = specItem('取貨方式', label);
    if (method === 'delivery') {
      var shipping = [o.shipping_city, o.shipping_postal, o.shipping_address]
        .filter(Boolean).join(' ');
      if (shipping) rows += specItem('收件地址', shipping);
    }
    var bottle = [o.collection_bottle_city, o.collection_bottle_postal, o.collection_bottle_address]
      .filter(Boolean).join(' ');
    if (bottle) rows += specItem('收集瓶寄送地址', bottle);
    if (method === 'pickup' && o.pickup_preferred_at) {
      var when = o.pickup_preferred_at;
      try {
        var d = new Date(when);
        if (!isNaN(d.getTime())) {
          var startParts = new Intl.DateTimeFormat('en-CA', {
            timeZone: 'Asia/Taipei',
            year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit', hour12: false
          }).formatToParts(d);
          var get = function (type) {
            var p = startParts.find(function (x) { return x.type === type; });
            return p ? p.value : '';
          };
          var end = new Date(d.getTime() + 60 * 60 * 1000);
          var endParts = new Intl.DateTimeFormat('en-CA', {
            timeZone: 'Asia/Taipei',
            hour: '2-digit', minute: '2-digit', hour12: false
          }).formatToParts(end);
          var endGet = function (type) {
            var p = endParts.find(function (x) { return x.type === type; });
            return p ? p.value : '';
          };
          when =
            get('year') + '/' + get('month') + '/' + get('day') + ' ' +
            get('hour') + ':' + get('minute') + '–' +
            endGet('hour') + ':' + endGet('minute');
        }
      } catch (e) { /* keep raw */ }
      rows += specItem('希望取貨時間', when);
    }
    return rows;
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
              sizeSpecRow(o) + specItem('戒圈刻字', o.engraving_band || '-') +
              specItem('金屬刻字', o.engraving_remark || '-') +
              (o.engraving_girdle
                ? specItemHtml('腰圍刻字', girdleDisplayHtml(o.engraving_girdle))
                : specItem('腰圍刻字', '-')) +
              priceBreakdownLines(o) +
              specItem('客戶', (o.customer_name || '-') + ' · ' + (o.customer_phone || '')) +
              fulfillmentRows(o) +
            '</div>' + progressHtml(o) +
          '</div></div></div>'
    );
  }

  function specItem(label, value) {
    return '<div class="order-detail-item"><span class="order-detail-label">' + esc(label) +
      '</span><span class="order-detail-value">' + esc(String(value)) + '</span></div>';
  }

  function specItemHtml(label, valueHtml) {
    return '<div class="order-detail-item"><span class="order-detail-label">' + esc(label) +
      '</span><span class="order-detail-value">' + valueHtml + '</span></div>';
  }

  function girdleDisplayHtml(str) {
    if (window.GirdleEngrave && typeof window.GirdleEngrave.toDisplayHtml === 'function') {
      return window.GirdleEngrave.toDisplayHtml(str);
    }
    return esc(str);
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
    var selectAll = tbody.querySelector('#ordersSelectAll');
    if (selectAll) {
      var checks = tbody.querySelectorAll('.order-row-check:not(:disabled)');
      selectAll.checked = checks.length > 0 && ids.length === checks.length;
      selectAll.indeterminate = ids.length > 0 && ids.length < checks.length;
    }
  }

  function fillBulkStatusSelect() {
    if (!bulkStatus) return;
    bulkStatus.innerHTML = BULK_STATUS_OPTIONS.map(function (s) {
      return '<option value="' + s + '">' + statusOptionLabel(s) + '</option>';
    }).join('');
  }

  function fillCancelChips() {
    if (!cancelChips) return;
    cancelChips.innerHTML = CANCEL_REASON_CHIPS.map(function (label) {
      return '<button type="button" class="order-cancel-chip" data-cancel-chip="' +
        esc(label) + '">' + esc(label) + '</button>';
    }).join('');
  }

  function resolveCancelReason() {
    return String(cancelReasonInput && cancelReasonInput.value || '').trim();
  }

  function openCancelDialog(ids) {
    if (!cancelDialog || !ids.length) return;
    cancelContext = { mode: ids.length > 1 ? 'bulk' : 'single', ids: ids.slice() };
    if (cancelReasonInput) cancelReasonInput.value = '';
    if (cancelChips) {
      cancelChips.querySelectorAll('.order-cancel-chip').forEach(function (chip) {
        chip.classList.remove('is-active');
      });
    }
    if (cancelError) cancelError.hidden = true;
    cancelDialog.showModal();
    if (cancelReasonInput) cancelReasonInput.focus();
  }

  function closeCancelDialog() {
    cancelDialog?.close();
    cancelContext = { mode: 'single', ids: [] };
  }

  function submitCancel() {
    var reason = resolveCancelReason();
    if (!reason) {
      if (cancelError) {
        cancelError.textContent = '請填寫取消原因';
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
    if (!confirm('確定將 ' + ids.length + ' 筆訂單狀態改為「' + statusOptionLabel(status) + '」？')) return;
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

  function toOrderTableRow(o) {
    return {
      id: String(o.id),
      orderNumber: String(o.order_number || o.id),
      dateLabel: formatDateTime(o.created_at),
      dateSort: o.created_at || '',
      customerName: o.customer_name || '銘印',
      categoryLabel: CATEGORY_LABELS[o.category] || o.category || '-',
      imageUrl: orderImageUrl(o) || '',
      imageAlt: o.order_number || '',
      imageFallback: orderImageFallback(o) || '',
      styleLabel: styleNamePlain(o),
      totalLabel: formatMoney(o.total_price),
      totalSort: o.total_price != null ? Number(o.total_price) : -Infinity,
      status: o.status,
      statusLabel: statusLabel(o.status, o.fulfillment_method),
      isCancelled: isCancelled(o),
      statusOptions: STATUS_OPTIONS.map(function (s) { return { value: s, label: statusOptionLabel(s) }; }),
      detailId: 'admin-detail-' + o.id,
      detailHtml: detailPanel(o),
    };
  }

  function unmountTable() {
    if (window.AdminTables) window.AdminTables.unmount(tbody);
  }

  function renderRows(orders) {
    if (!orders.length && !_total) {
      unmountTable();
      tbody.innerHTML = '<p class="orders-empty">目前沒有訂單</p>';
      updateBulkBar();
      return;
    }
    if (!window.AdminTables) {
      tbody.innerHTML = '<p class="orders-empty">載入失敗：表格元件未載入</p>';
      return;
    }
    window.AdminTables.renderOrdersTable(tbody, {
      rows: orders.map(toOrderTableRow),
      total: _total,
      pageIndex: _pageIndex,
      pageSize: _pageSize,
      onPaginationChange: function (pagination) {
        var nextIndex = pagination.pageIndex || 0;
        var nextSize = pagination.pageSize || _pageSize;
        if (nextIndex === _pageIndex && nextSize === _pageSize) return;
        _pageIndex = nextIndex;
        _pageSize = nextSize;
        load(_lastQuery || null, true, true);
      },
      onRendered: function () {
        bindRowEvents();
        updateBulkBar();
      },
    });
  }

  function bindRowEvents() {
    var selectAll = tbody.querySelector('#ordersSelectAll');
    if (selectAll) {
      selectAll.addEventListener('change', function () {
        var on = selectAll.checked;
        tbody.querySelectorAll('.order-row-check:not(:disabled)').forEach(function (cb) {
          cb.checked = on;
        });
        updateBulkBar();
      });
    }

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
    var q = (query == null ? _lastQuery : query) || '';
    if (query != null && query !== _lastQuery) {
      _lastQuery = q;
      _pageIndex = 0;
    }
    if (!q && _loaded && !force) return;
    if (!silent) {
      unmountTable();
      tbody.innerHTML = window.SkeletonUI
        ? window.SkeletonUI.table({
          headers: ['', '縮圖', '品項', '客戶', '金額', '狀態', '操作'],
          rows: 6,
          rowFn: window.SkeletonUI.orderTableRow,
          label: '載入訂單中',
        })
        : '<p class="orders-empty">載入中…</p>';
    }
    var params = {
      page: _pageIndex + 1,
      page_size: _pageSize,
    };
    if (q) params.q = q;
    api.admin.getOrders(params).then(function (res) {
      if (res.error) {
        unmountTable();
        tbody.innerHTML = '<p class="orders-empty">載入失敗</p>';
        return;
      }
      _total = typeof res.total === 'number' ? res.total : (res.orders || []).length;
      if (typeof res.page === 'number' && res.page > 0) _pageIndex = res.page - 1;
      if (typeof res.page_size === 'number' && res.page_size > 0) _pageSize = res.page_size;
      renderRows(res.orders || []);
      if (!q) _loaded = true;
    });
  }

  function ensureLoaded() {
    // Always allow first paint; refresh in background if already loaded
    if (_loaded) load(null, true, true);
    else load(null, false, false);
  }

  fillBulkStatusSelect();
  fillCancelChips();

  bulkApply?.addEventListener('click', applyBulkStatus);
  bulkClear?.addEventListener('click', function () {
    tbody.querySelectorAll('.order-row-check').forEach(function (cb) { cb.checked = false; });
    updateBulkBar();
  });

  cancelChips?.addEventListener('click', function (e) {
    var chip = e.target.closest('[data-cancel-chip]');
    if (!chip || !cancelReasonInput) return;
    var label = chip.getAttribute('data-cancel-chip') || '';
    cancelReasonInput.value = label === '其他' ? '' : label;
    cancelChips.querySelectorAll('.order-cancel-chip').forEach(function (el) {
      el.classList.toggle('is-active', el === chip);
    });
    if (cancelError) cancelError.hidden = true;
    cancelReasonInput.focus();
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

  document.getElementById('btnExportOrdersCsv')?.addEventListener('click', function () {
    var q = (searchInput && searchInput.value.trim()) || _lastQuery || '';
    var params = new URLSearchParams();
    if (q) params.set('q', q);
    params.set('_', String(Date.now()));
    window.location.href = (window.IMPRINT_API_BASE || '')
      + '/api/admin/orders/export?' + params.toString();
  });

  document.getElementById('btnNewOrder')?.addEventListener('click', function () {
    if (window.AdminPanel && window.AdminPanel.openNewOrderModal) {
      window.AdminPanel.openNewOrderModal(load);
    }
  });

  window.AdminOrdersPanel = { load: load, ensureLoaded: ensureLoaded };
})();
