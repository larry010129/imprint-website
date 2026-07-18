(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Display = global.ImprintOrderDisplay;

  function bucket(status) {
    var s = (status || '').toLowerCase();
    if (s === 'cancelled' || s === 'canceled') return 'cancelled';
    if (s === 'completed' || s === 'shipped') return 'complete';
    return 'incomplete';
  }

  var ordersByNumber = {};

  function renderRows(list, statusLabel) {
    if (!Display) return '';
    return list.map(function (o) {
      return Display.rowHtml(o, statusLabel, M.escapeHtml);
    }).join('');
  }

  function applySearch(query) {
    var q = (query || '').toLowerCase().trim();
    document.querySelectorAll('#mvc-history tr.order-row-main').forEach(function (row) {
      var blob = row.getAttribute('data-search') || '';
      var match = !q || blob.indexOf(q) >= 0;
      row.hidden = !match;
      var detailRow = row.nextElementSibling;
      if (detailRow && detailRow.classList.contains('order-detail-row') && !match) {
        detailRow.hidden = true;
        var btn = row.querySelector('.order-detail-btn');
        if (btn) btn.setAttribute('aria-expanded', 'false');
        row.classList.remove('is-detail-open');
      }
    });
  }

  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.History = {
    render: function (orders, statusLabel) {
      statusLabel = statusLabel || function (s) { return s; };
      var loading = document.getElementById('history-loading');
      if (loading) loading.classList.add('hidden');
      ordersByNumber = {};
      (orders || []).forEach(function (o) {
        if (o.order_number) ordersByNumber[o.order_number] = o;
      });
      var buckets = { incomplete: [], complete: [], cancelled: [] };
      (orders || []).forEach(function (o) { buckets[bucket(o.status)].push(o); });
      ['incomplete', 'complete', 'cancelled'].forEach(function (key) {
        var tbody = document.getElementById('history-tbody-' + key);
        var count = document.getElementById('history-tabcount-' + key);
        var list = buckets[key];
        if (count) count.textContent = String(list.length);
        if (!tbody) return;
        if (!list.length) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;color:var(--ink-faint);">目前沒有訂單。完成「確認訂購」後，訂單會顯示在此。</td></tr>';
          return;
        }
        tbody.innerHTML = renderRows(list, statusLabel);
      });

      var searchInput = document.getElementById('history-search-input');
      if (searchInput && searchInput.value) applySearch(searchInput.value);
    },
    renderError: function (message) {
      var loading = document.getElementById('history-loading');
      if (loading) loading.classList.add('hidden');
      ['incomplete', 'complete', 'cancelled'].forEach(function (key) {
        var tbody = document.getElementById('history-tbody-' + key);
        if (tbody) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;color:var(--ink-faint);">載入失敗：' + M.escapeHtml(message || '請稍後再試') + '</td></tr>';
        }
      });
    },
    bindTabs: function () {
      document.querySelectorAll('#mvc-history .member-tab').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var tab = btn.dataset.tab;
          document.querySelectorAll('#mvc-history .member-tab').forEach(function (b) {
            b.classList.toggle('is-active', b === btn);
          });
          document.querySelectorAll('#mvc-history .member-tab-panel').forEach(function (p) {
            var show = p.dataset.tabPanel === tab;
            p.classList.toggle('hidden', !show);
            p.hidden = !show;
          });
        });
      });
    },
    bindSearch: function () {
      var form = document.getElementById('history-search-form');
      var input = document.getElementById('history-search-input');
      if (!input) return;
      input.addEventListener('input', function () { applySearch(input.value); });
      if (form) {
        form.addEventListener('submit', function (e) {
          e.preventDefault();
          applySearch(input.value);
        });
      }
    },
    getOrder: function (orderNumber) {
      return ordersByNumber[orderNumber] || null;
    },
    bindEdit: function () {
      var root = document.getElementById('mvc-history');
      if (!root || !Display) return;
      root.addEventListener('click', function (e) {
        var btn = e.target.closest('.member-order-edit-btn');
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();
        var no = btn.getAttribute('data-order-number');
        var order = ordersByNumber[no];
        if (!order || !Display.canEditOrder(order)) return;
        try {
          sessionStorage.setItem('imprint_order_edit', JSON.stringify(Display.orderToShopConfig(order)));
        } catch (err) {
          console.error(err);
        }
        global.location.href = '/shop/calculator/?editOrder=' + encodeURIComponent(no);
      });
    },
  };
})(window);
