/* 銘印鑽石｜管理後台真實資料串接
   權限設計：後端 /api/admin/* 每個請求都會檢查目前登入者是否在 staff_admins
   表中，不是 admin 一律回 403。這支程式在拿到 403/401 時額外顯示明確的
   提示畫面，避免留白畫面讓人誤會壞掉。
*/
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var api = window.imprintAPI;
    if (!api) return;

    if (window.SkeletonUI) {
      var dashHosts = {
        dashStatusList: window.SkeletonUI.statusCards(4),
        dashTopProducts: window.SkeletonUI.rankList(4),
        dashTopSeries: window.SkeletonUI.rankList(4),
        dashRecentOrders: window.SkeletonUI.recentList(5),
      };
      Object.keys(dashHosts).forEach(function (id) {
        var el = document.getElementById(id);
        if (el && !el.innerHTML.trim()) el.innerHTML = dashHosts[id];
      });
    }

    var statusLabel = window.ImprintOrderStatus ? window.ImprintOrderStatus.label : function (s) { return s; };
    var mainEl = document.querySelector('.main');
    var topMeta = document.getElementById('topMeta');

    var STATUS_OPTIONS = ['received', 'dna_lab', 'deposit_confirmed', 'in_production', 'quality_check', 'shipped', 'completed'];
    var STATUS_CHIP = {
      received: 'chip-new', dna_lab: 'chip-grow', deposit_confirmed: 'chip-talk',
      in_production: 'chip-grow', quality_check: 'chip-cut', shipped: 'chip-talk', completed: 'chip-done'
    };

    function escapeHtml(s) {
      return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
      });
    }

    function formatDateTime(iso) {
      if (!iso) return '-';
      var d = new Date(iso);
      var pad = function (n) { return n < 10 ? '0' + n : n; };
      return (d.getMonth() + 1) + '/' + d.getDate() + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
    }

    function showAccessDenied(message) {
      mainEl.innerHTML = '<div class="note warn" style="margin-top:60px;max-width:560px;">' + message + '</div>';
    }

    /* ---------- 共用彈窗（新增訂單／更新進度） ---------- */
    var modalOverlay = document.createElement('div');
    modalOverlay.className = 'qr-modal-overlay';
    document.body.appendChild(modalOverlay);

    function closeModal() {
      modalOverlay.classList.remove('is-open');
      modalOverlay.innerHTML = '';
      document.body.style.overflow = '';
    }
    modalOverlay.addEventListener('click', function (e) {
      if (e.target === modalOverlay) closeModal();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modalOverlay.classList.contains('is-open')) closeModal();
    });

    function openModal(innerHtml) {
      modalOverlay.innerHTML = innerHtml;
      modalOverlay.classList.add('is-open');
      document.body.style.overflow = 'hidden';
      modalOverlay.querySelectorAll('[data-modal-close]').forEach(function (btn) {
        btn.addEventListener('click', closeModal);
      });
    }

    function formatCurrency(amount) {
      return 'NT$ ' + Number(amount || 0).toLocaleString('zh-TW', { maximumFractionDigits: 0 });
    }

    function setText(id, value) {
      var el = document.getElementById(id);
      if (el) {
        el.classList.remove('skel-metric');
        el.textContent = value;
      }
    }

    function showDashboardListSkeletons() {
      var S = window.SkeletonUI;
      if (!S) return;
      var hosts = {
        dashStatusList: S.statusCards(4),
        dashTopProducts: S.rankList(4),
        dashTopSeries: S.rankList(4),
        dashRecentOrders: S.recentList(5),
      };
      Object.keys(hosts).forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.innerHTML = hosts[id];
      });
    }

    var dashParams = { granularity: 'month' };

    function readDashParamsFromUrl() {
      var qs = new URLSearchParams(window.location.search);
      dashParams = {
        granularity: qs.get('granularity') || 'month',
        period: qs.get('period') || '',
        start: qs.get('start') || '',
        end: qs.get('end') || '',
      };
    }

    function writeDashParamsToUrl() {
      var qs = new URLSearchParams();
      qs.set('granularity', dashParams.granularity || 'month');
      if (dashParams.granularity === 'day') {
        if (dashParams.start) qs.set('start', dashParams.start);
        if (dashParams.end) qs.set('end', dashParams.end);
      } else if (dashParams.period) {
        qs.set('period', dashParams.period);
      }
      var next = window.location.pathname + '?' + qs.toString();
      window.history.replaceState(null, '', next);
    }

    function dashboardRequestParams() {
      var p = { granularity: dashParams.granularity || 'month' };
      if (p.granularity === 'day') {
        if (dashParams.start) p.start = dashParams.start;
        if (dashParams.end) p.end = dashParams.end;
      } else if (dashParams.period) {
        p.period = dashParams.period;
      }
      return p;
    }

    function renderGranularityButtons(granularity) {
      var host = document.getElementById('dashGranularity');
      if (!host) return;
      host.querySelectorAll('[data-granularity]').forEach(function (btn) {
        btn.classList.toggle('is-active', btn.dataset.granularity === granularity);
      });
    }

    function renderRangeControls(stats) {
      var gran = stats.granularity || 'month';
      var monthSel = document.getElementById('dashPeriodMonth');
      var weekSel = document.getElementById('dashPeriodWeek');
      var startInp = document.getElementById('dashPeriodStart');
      var endInp = document.getElementById('dashPeriodEnd');
      var sep = document.getElementById('dashPeriodSep');
      if (!monthSel || !weekSel || !startInp || !endInp) return;

      monthSel.hidden = gran !== 'month';
      weekSel.hidden = gran !== 'week';
      startInp.hidden = gran !== 'day';
      endInp.hidden = gran !== 'day';
      if (sep) sep.hidden = gran !== 'day';

      if (gran === 'month') {
        monthSel.innerHTML = (stats.monthOptions || []).map(function (opt) {
          return '<option value="' + escapeHtml(opt.value) + '">' + escapeHtml(opt.label) + '</option>';
        }).join('');
        monthSel.value = stats.period || '';
      } else if (gran === 'week') {
        weekSel.innerHTML = (stats.weekOptions || []).map(function (opt) {
          return '<option value="' + escapeHtml(opt.value) + '">' + escapeHtml(opt.label) + '</option>';
        }).join('');
        weekSel.value = stats.period || '';
      } else {
        startInp.value = stats.start || '';
        endInp.value = stats.end || '';
      }

      renderGranularityButtons(gran);
      setText('dashPeriodLabel', stats.periodLabel || '');
      setText('dashToolbarPeriod', stats.periodLabel || '');

      var exportBtn = document.getElementById('dashExportBtn');
      if (exportBtn) {
        exportBtn.href = api.admin.dashboardExportUrl(dashboardRequestParams());
      }
    }

    function bindDashboardRangeControls() {
      var granHost = document.getElementById('dashGranularity');
      if (granHost && !granHost.dataset.bound) {
        granHost.dataset.bound = '1';
        granHost.querySelectorAll('[data-granularity]').forEach(function (btn) {
          btn.addEventListener('click', function () {
            dashParams.granularity = btn.dataset.granularity;
            dashParams.period = '';
            dashParams.start = '';
            dashParams.end = '';
            writeDashParamsToUrl();
            loadDashboardStats();
          });
        });
      }

      var form = document.getElementById('dashRangeForm');
      if (form && !form.dataset.bound) {
        form.dataset.bound = '1';
        ['dashPeriodMonth', 'dashPeriodWeek', 'dashPeriodStart', 'dashPeriodEnd'].forEach(function (id) {
          var el = document.getElementById(id);
          if (!el) return;
          el.addEventListener('change', function () {
            if (id === 'dashPeriodMonth') {
              dashParams.granularity = 'month';
              dashParams.period = el.value;
            } else if (id === 'dashPeriodWeek') {
              dashParams.granularity = 'week';
              dashParams.period = el.value;
            } else {
              dashParams.granularity = 'day';
              dashParams.start = document.getElementById('dashPeriodStart').value;
              dashParams.end = document.getElementById('dashPeriodEnd').value;
            }
            writeDashParamsToUrl();
            loadDashboardStats();
          });
        });
      }
    }

    function renderTrendChart(trend) {
      if (window.AdminDashboardChart) {
        window.AdminDashboardChart.init(trend || []);
      }
    }

    function statusRingSvg(pct, color) {
      var r = 30;
      var c = 2 * Math.PI * r;
      var dash = Math.max(0, Math.min(100, pct)) / 100 * c;
      return (
        '<svg class="dash-stat-ring-svg" viewBox="0 0 80 80" aria-hidden="true">' +
          '<circle class="dash-stat-ring-bg" cx="40" cy="40" r="' + r + '" />' +
          '<circle class="dash-stat-ring-fill" cx="40" cy="40" r="' + r + '" stroke="' + color + '"' +
            ' stroke-dasharray="' + dash + ' ' + c + '" transform="rotate(-90 40 40)" />' +
        '</svg>'
      );
    }

    function renderStatusRows(rows) {
      var host = document.getElementById('dashStatusList');
      if (!host) return;

      var groups = [
        { key: 'pending', label: '待處理', color: 'hsl(200, 70%, 50%)', codes: ['received', 'dna_lab', 'deposit_confirmed'] },
        { key: 'making', label: '製作中', color: 'hsl(120, 70%, 50%)', codes: ['in_production', 'quality_check'] },
        { key: 'shipped', label: '已出貨', color: 'hsl(340, 70%, 50%)', codes: ['shipped'] },
        { key: 'done', label: '已完成', color: 'hsl(280, 70%, 50%)', codes: ['completed'] },
      ];
      var byCode = {};
      (rows || []).forEach(function (r) { byCode[r.code] = r; });
      var total = (rows || []).reduce(function (s, r) { return s + (r.count || 0); }, 0);

      if (!total) {
        host.innerHTML = '<p class="dash-recent-empty">尚無訂單</p>';
        return;
      }

      host.innerHTML = groups.map(function (g) {
        var count = 0;
        g.codes.forEach(function (c) {
          if (byCode[c]) count += byCode[c].count;
        });
        var pct = Math.round(1000 * count / total) / 10;
        var pctLabel = pct % 1 === 0 ? String(Math.round(pct)) : pct.toFixed(1);
        return (
          '<article class="dash-stat-card dash-stat-card--ring" data-goto-panel="orders" role="button" tabindex="0">' +
            '<div class="dash-stat-card-inner">' +
              '<div class="dash-stat-ring-wrap">' +
                statusRingSvg(pct, g.color) +
                '<span class="dash-stat-ring-pct">' + pctLabel + '%</span>' +
              '</div>' +
              '<div class="dash-stat-card-text">' +
                '<p class="dash-stat-card-title">' + escapeHtml(g.label) + '</p>' +
                '<p class="dash-stat-card-sub">' + count + ' / ' + total + ' 筆</p>' +
              '</div>' +
            '</div>' +
          '</article>'
        );
      }).join('');

      host.querySelectorAll('[data-goto-panel]').forEach(function (el) {
        function go() {
          var panel = el.dataset.gotoPanel;
          var navBtn = document.querySelector('.side-nav button[data-panel="' + panel + '"]');
          if (navBtn) navBtn.click();
        }
        el.addEventListener('click', go);
        el.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); }
        });
      });
    }

    function renderTopProducts(items) {
      var host = document.getElementById('dashTopProducts');
      if (!host) return;
      if (!items || !items.length) {
        host.innerHTML = '<p class="dash-recent-empty">尚無訂單</p>';
        return;
      }
      host.innerHTML = items.map(function (item) {
        var initial = (item.name || '?').slice(0, 1);
        return (
          '<div class="dash-rank-item">' +
            '<div class="dash-rank-left">' +
              '<span class="dash-rank-avatar">' + escapeHtml(initial) + '</span>' +
              '<div><p class="dash-rank-name">' + escapeHtml(item.name) + '</p><p class="dash-rank-sub">累計訂單</p></div>' +
            '</div>' +
            '<span class="dash-rank-val">' + item.orders + ' 筆</span>' +
          '</div>'
        );
      }).join('');
    }

    function renderTopSeries(items) {
      var host = document.getElementById('dashTopSeries');
      if (!host) return;
      if (!items || !items.length) {
        host.innerHTML = '<p class="dash-recent-empty">尚無資料</p>';
        return;
      }
      host.innerHTML = items.map(function (item, i) {
        var initial = (item.name || '?').slice(0, 1);
        return (
          '<div class="dash-rank-item">' +
            '<div class="dash-rank-left">' +
              '<span class="dash-rank-avatar">' + escapeHtml(initial) + '</span>' +
              '<div><p class="dash-rank-name">' + escapeHtml(item.name) + '</p>' +
                '<p class="dash-rank-sub">' + item.orders + ' 筆訂單</p></div>' +
            '</div>' +
            '<span class="dash-rank-val">' + formatCurrency(item.revenue) + '</span>' +
          '</div>'
        );
      }).join('');
    }

    function renderRecentOrders(orders) {
      var host = document.getElementById('dashRecentOrders');
      if (!host) return;
      if (!orders || !orders.length) {
        host.innerHTML = '<p class="dash-recent-empty">尚無訂單</p>';
        return;
      }
      host.innerHTML = orders.map(function (o) {
        var product = o.product_type || o.category || '訂製品項';
        return (
          '<div class="dash-recent-item">' +
            '<div>' +
              '<div class="dash-recent-amt">' + formatCurrency(o.total_price) + '</div>' +
              '<div class="dash-recent-meta">' + escapeHtml(product) + ' · ' + escapeHtml(o.customer_name || '客戶') + '</div>' +
            '</div>' +
            '<div class="dash-recent-time">' + formatDateTime(o.created_at) + '<br>' + escapeHtml(o.order_number || '') + '</div>' +
          '</div>'
        );
      }).join('');
    }

    /* ---------- 儀表板 ---------- */
    function loadDashboardStats() {
      showDashboardListSkeletons();
      api.admin.getDashboardStats(dashboardRequestParams()).then(function (stats) {
        if (stats.error) return;
        var pendingTotal = (stats.newMessages || 0) + (stats.pendingQuotes || 0) + (stats.activeOrders || 0);
        var orderCount = stats.periodOrderCount != null ? stats.periodOrderCount : (stats.totalOrders || 0);

        setText('statNewMessages', stats.newMessages != null ? stats.newMessages : '-');
        setText('statPendingQuotes', stats.pendingQuotes != null ? stats.pendingQuotes : '-');
        setText('statActiveOrders', stats.activeOrders != null ? stats.activeOrders : '-');
        setText('statPendingTotal', pendingTotal);
        setText('statOrderCount', orderCount);
        setText('statTotalRevenue', formatCurrency(stats.totalRevenue));
        setText('statAverageSale', formatCurrency(stats.averageSale));

        dashParams.granularity = stats.granularity || dashParams.granularity;
        dashParams.period = stats.period || '';
        dashParams.start = stats.start || '';
        dashParams.end = stats.end || '';
        renderRangeControls(stats);
        bindDashboardRangeControls();

        renderTrendChart(stats.monthlyTrend || []);
        renderStatusRows(stats.statusRows || []);
        renderTopProducts(stats.topProducts || []);
        renderTopSeries(stats.topSeries || []);
        renderRecentOrders(stats.recentOrders || []);
      });
    }

    var leadsLoaded = false;

    /* ---------- 諮詢名單（合併聯絡表單＋線上估價） ---------- */
    var _leadsByKey = {};

    function leadDetailRow(label, value) {
      if (value == null || value === '') return '';
      return (
        '<div class="lead-detail__row">' +
          '<span class="lead-detail__label">' + escapeHtml(label) + '</span>' +
          '<span class="lead-detail__value">' + escapeHtml(String(value)) + '</span>' +
        '</div>'
      );
    }

    function openLeadDetail(key) {
      var item = _leadsByKey[key];
      if (!item) return;
      var raw = item.raw || {};
      var body = '';
      if (item.type === 'message') {
        body =
          leadDetailRow('姓名', item.name) +
          leadDetailRow('電話', item.phone) +
          leadDetailRow('Email', item.email) +
          leadDetailRow('來源頁', raw.source_page) +
          leadDetailRow('狀態', item.status) +
          leadDetailRow('建立時間', formatDateTime(item.created_at)) +
          '<div class="lead-detail__block">' +
            '<span class="lead-detail__label">留言內容</span>' +
            '<p class="lead-detail__message">' + escapeHtml(raw.message || item.summary || '—') + '</p>' +
          '</div>';
      } else {
        body =
          leadDetailRow('姓名', item.name) +
          leadDetailRow('電話', item.phone) +
          leadDetailRow('Email', item.email) +
          leadDetailRow('系列', raw.series) +
          leadDetailRow('品項', raw.product_type) +
          leadDetailRow('克拉', raw.carat) +
          leadDetailRow('顏色', raw.color) +
          leadDetailRow('造型', raw.shape) +
          leadDetailRow('材質', raw.metal) +
          leadDetailRow('數量', raw.quantity != null ? String(raw.quantity) : '') +
          leadDetailRow(
            '預估金額',
            raw.estimated_price != null ? ('NT$ ' + Number(raw.estimated_price).toLocaleString('en-US')) : ''
          ) +
          leadDetailRow('狀態', item.status) +
          leadDetailRow('建立時間', formatDateTime(item.created_at));
      }

      openModal(
        '<div class="qr-modal lead-detail-modal" role="dialog" aria-modal="true">' +
          '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
          '<h3>' + (item.type === 'message' ? '聯絡留言詳情' : '線上估價詳情') + '</h3>' +
          '<div class="lead-detail">' + body + '</div>' +
          '<div class="ap-form-actions" style="margin-top:16px">' +
            '<button type="button" class="btn-sm" data-modal-close>關閉</button>' +
          '</div>' +
        '</div>'
      );
    }

    function loadLeads(silent, force) {
      var tbody = document.getElementById('leadsTableBody');
      if (!tbody) return;
      if (leadsLoaded && !force) return;
      if (!silent) {
        var S = window.SkeletonUI;
        tbody.innerHTML = S
          ? S.tableBodyRows(5, S.leadsTableRow)
          : '<tr><td colspan="8" class="table-placeholder">載入中…</td></tr>';
      }

      function fail(msg) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--ink-faint);">' +
          escapeHtml(msg || '載入失敗，請重新整理頁面。') + '</td></tr>';
        leadsLoaded = false;
      }

      function attr(s) {
        return escapeHtml(String(s == null ? '' : s)).replace(/\r?\n/g, ' ');
      }

      api.admin.getLeads().then(function (res) {
        if (res.error) {
          fail(typeof res.error === 'string' ? res.error : (res.error.message || '載入失敗'));
          return;
        }
        try {
          var messages = (res.messages || []).map(function (m) {
            return {
              type: 'message',
              id: m.id,
              name: m.name,
              phone: m.phone,
              email: m.email,
              summary: m.message,
              created_at: m.created_at,
              status: m.status,
              raw: m,
            };
          });
          var quotes = (res.quotes || []).map(function (q) {
            var parts = [];
            if (q.series) parts.push(q.series);
            if (q.carat) parts.push(q.carat + ' 克拉');
            if (q.product_type) parts.push(q.product_type);
            if (q.estimated_price != null) parts.push('NT$ ' + Number(q.estimated_price).toLocaleString('en-US'));
            return {
              type: 'quote',
              id: q.id,
              name: q.name,
              phone: q.phone,
              email: q.email,
              summary: parts.join('・') || '線上估價需求',
              created_at: q.created_at,
              status: q.status,
              raw: q,
            };
          });
          var all = messages.concat(quotes).sort(function (a, b) {
            return new Date(b.created_at) - new Date(a.created_at);
          });
          _leadsByKey = {};

          if (!all.length) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--ink-faint);">目前沒有諮詢紀錄。</td></tr>';
            leadsLoaded = true;
          } else {
            tbody.innerHTML = all.map(function (item) {
              var key = item.type + ':' + item.id;
              _leadsByKey[key] = item;
              var sourceLabel = item.type === 'message' ? '官網留言表單' : '線上估價';
              var isDone = ['replied', 'contacted', 'converted', 'closed'].indexOf(item.status) !== -1;
              var statusLabel = isDone ? '已處理' : '待處理';
              var summaryPreview = String(item.summary || '');
              if (summaryPreview.length > 48) summaryPreview = summaryPreview.slice(0, 48) + '…';
              var phone = item.phone || '';
              var email = item.email || '';
              return (
                '<tr data-sort-name="' + attr(item.name) + '"' +
                  ' data-sort-phone="' + attr(phone) + '"' +
                  ' data-sort-email="' + attr(email) + '"' +
                  ' data-sort-source="' + attr(sourceLabel) + '"' +
                  ' data-sort-summary="' + attr(item.summary) + '"' +
                  ' data-sort-created="' + attr(item.created_at || '') + '"' +
                  ' data-sort-status="' + attr(statusLabel) + '">' +
                  '<td class="name">' + escapeHtml(item.name) + '</td>' +
                  '<td>' + (phone ? escapeHtml(phone) : '<span class="adx-muted">—</span>') + '</td>' +
                  '<td>' + (email
                    ? '<a class="lead-email-link" href="mailto:' + escapeHtml(email) + '">' + escapeHtml(email) + '</a>'
                    : '<span class="adx-muted">—</span>') + '</td>' +
                  '<td>' + sourceLabel + '</td>' +
                  '<td>' + escapeHtml(summaryPreview) + '</td>' +
                  '<td>' + formatDateTime(item.created_at) + '</td>' +
                  '<td><span class="chip ' + (isDone ? 'chip-done' : 'chip-new') + '">' + statusLabel + '</span></td>' +
                  '<td><div class="adx-actions">' +
                    '<button type="button" class="btn-sm" data-lead-detail="' + escapeHtml(key) + '">詳情</button>' +
                    (isDone ? '' : '<button type="button" class="btn-sm" data-mark-done="' + escapeHtml(key) + '">標記已處理</button>') +
                  '</div></td>' +
                '</tr>'
              );
            }).join('');
            leadsLoaded = true;
          }

          var leadsTable = tbody.closest('table');
          if (leadsTable && window.AdminTableSort) window.AdminTableSort.bind(leadsTable);

          tbody.querySelectorAll('[data-lead-detail]').forEach(function (btn) {
            btn.addEventListener('click', function () {
              openLeadDetail(btn.dataset.leadDetail);
            });
          });

          tbody.querySelectorAll('[data-mark-done]').forEach(function (btn) {
            btn.addEventListener('click', function () {
              var sep = btn.dataset.markDone.indexOf(':');
              var kind = btn.dataset.markDone.slice(0, sep);
              var id = btn.dataset.markDone.slice(sep + 1);
              btn.disabled = true;
              btn.textContent = '更新中…';
              api.admin.markLeadDone(kind, id).then(function (doneRes) {
                if (doneRes.error) {
                  console.error('[admin]', doneRes.error);
                  btn.disabled = false;
                  btn.textContent = '更新失敗，再試一次';
                  return;
                }
                loadLeads(true, true);
                loadDashboardStats();
              });
            });
          });
        } catch (err) {
          console.error('[admin] leads render', err);
          fail('畫面渲染失敗，請重新整理。');
        }
      }).catch(function (err) {
        console.error('[admin] leads fetch', err);
        fail('系統連線異常，請稍後再試。');
      });
    }

    /* ---------- 訂單：由 admin-orders.js 渲染 ---------- */
    function openNewOrderModal(onDone) {
      openModal(
        '<div class="qr-modal" role="dialog" aria-modal="true">' +
          '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
          '<h3>新增訂單</h3>' +
          '<form id="newOrderForm" novalidate>' +
            '<div class="form-field"><label for="noName">客戶姓名 <span class="req">*</span></label><input type="text" id="noName" required></div>' +
            '<div class="form-field"><label for="noPhone">客戶電話 <span class="req">*</span></label><input type="tel" id="noPhone" required></div>' +
            '<div class="form-field"><label for="noEmail">Email</label><input type="email" id="noEmail"></div>' +
            '<div class="form-field"><label for="noSeries">系列</label><input type="text" id="noSeries" placeholder="例如：滿月鑽石"></div>' +
            '<div class="form-field"><label for="noProduct">品項規格</label><input type="text" id="noProduct" placeholder="例如：0.5ct 白鑽 戒指"></div>' +
            '<button type="submit" class="btn btn-dark" id="noSubmitBtn">建立訂單</button>' +
            '<p class="form-msg" id="noMsg"></p>' +
          '</form>' +
        '</div>'
      );

      document.getElementById('newOrderForm').addEventListener('submit', function (e) {
        e.preventDefault();
        var name = document.getElementById('noName').value.trim();
        var phone = document.getElementById('noPhone').value.trim();
        var email = document.getElementById('noEmail').value.trim();
        var series = document.getElementById('noSeries').value.trim();
        var product = document.getElementById('noProduct').value.trim();
        var btn = document.getElementById('noSubmitBtn');
        var msg = document.getElementById('noMsg');

        if (!name || !phone) {
          msg.textContent = '請填寫客戶姓名與電話。';
          msg.className = 'form-msg is-err';
          return;
        }

        btn.disabled = true;
        btn.textContent = '建立中…';

        api.admin.createOrder({
          customerName: name, customerPhone: phone, customerEmail: email || null,
          series: series || null, productType: product || null
        }).then(function (res) {
          if (res.error) {
            msg.textContent = '建立失敗：' + res.error;
            msg.className = 'form-msg is-err';
            btn.disabled = false;
            btn.textContent = '建立訂單';
            return;
          }
          closeModal();
          if (typeof onDone === 'function') onDone();
          loadDashboardStats();
        });
      });
    }

    /* ---------- 啟動：登入與員工權限檢查 ---------- */
    api.getSession().then(function (res) {
      if (!res || !res.user) {
        window.location.href = 'login.html?next=admin.html';
        return;
      }

      if (!res.isAdmin) {
        showAccessDenied('您的帳號（' + escapeHtml(res.user.email) + '）目前沒有後台權限。請聯繫系統管理員，將您的帳號加入員工名單（staff_admins）後再重新登入。');
        return;
      }

      if (topMeta) topMeta.textContent = res.user.email;
      readDashParamsFromUrl();
      bindDashboardRangeControls();
      loadDashboardStats();

      window.AdminPanel = {
        currentUserId: res.user.id,
        openModal: openModal,
        closeModal: closeModal,
        escapeHtml: escapeHtml,
        openNewOrderModal: openNewOrderModal,
        onPanelSwitch: function (panel) {
          var main = document.querySelector('.main');
          if (main) main.classList.toggle('is-orders-view', panel === 'orders');
          if (panel === 'dash') loadDashboardStats();
          if (panel === 'leads') loadLeads(leadsLoaded);
          if (panel === 'orders' && window.AdminOrdersPanel) window.AdminOrdersPanel.ensureLoaded();
          if (panel === 'products' && window.AdminProductsPanel) window.AdminProductsPanel.ensureLoaded();
          if (panel === 'invites' && window.AdminInvitesPanel) window.AdminInvitesPanel.ensureLoaded();
          if (panel === 'coupons' && window.AdminCouponsPanel) window.AdminCouponsPanel.ensureLoaded();
          if (panel === 'content' && window.AdminContentPanel) window.AdminContentPanel.ensureLoaded();
          if (panel === 'accounts' && window.AdminAccountsPanel) window.AdminAccountsPanel.ensureLoaded();
        }
      };

      var activeNav = document.querySelector('.side-nav button.is-active');
      if (activeNav && activeNav.dataset.panel) {
        window.AdminPanel.onPanelSwitch(activeNav.dataset.panel);
      }
      if (typeof window.__adminFlushPendingPanel === 'function') {
        window.__adminFlushPendingPanel();
      }

      if (window.AdminProductsPanel && window.AdminProductsPanel.prefetch) {
        window.AdminProductsPanel.prefetch();
      }
    });
  });
})();
