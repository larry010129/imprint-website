(function (global) {
  'use strict';
  var M = global.ImprintMVC;

  function bucket(status) {
    var s = (status || '').toLowerCase();
    if (s === 'cancelled' || s === 'canceled') return 'cancelled';
    if (s === 'completed' || s === 'shipped') return 'complete';
    return 'incomplete';
  }

  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.History = {
    render: function (orders, statusLabel) {
      statusLabel = statusLabel || function (s) { return s; };
      var loading = document.getElementById('history-loading');
      if (loading) loading.classList.add('hidden');
      var buckets = { incomplete: [], complete: [], cancelled: [] };
      (orders || []).forEach(function (o) { buckets[bucket(o.status)].push(o); });
      ['incomplete', 'complete', 'cancelled'].forEach(function (key) {
        var tbody = document.getElementById('history-tbody-' + key);
        var count = document.getElementById('history-tabcount-' + key);
        var list = buckets[key];
        if (count) count.textContent = String(list.length);
        if (!tbody) return;
        if (!list.length) {
          tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--ink-faint);">目前沒有訂單</td></tr>';
          return;
        }
        tbody.innerHTML = list.map(function (o) {
          var id = o.id || o.order_number;
          var price = o.total_price != null ? o.total_price : o.totalPrice;
          return '<tr data-search="' + M.escapeHtml((o.summary || o.product_type || '') + ' ' + id) + '">' +
            '<td>' + M.escapeHtml(String(id)) + '</td>' +
            '<td>' + M.escapeHtml(o.created_at_display || o.created_at || '—') + '</td>' +
            '<td>' + M.escapeHtml(o.summary || o.product_type || '—') + '</td>' +
            '<td>' + (price != null ? Math.round(price).toLocaleString('en-US') : '—') + '</td>' +
            '<td>' + M.escapeHtml(statusLabel(o.status) || '—') + '</td></tr>';
        }).join('');
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
  };
})(window);
