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
      var closeBtn = modalOverlay.querySelector('[data-modal-close]');
      if (closeBtn) closeBtn.addEventListener('click', closeModal);
    }

    /* ---------- 儀表板 ---------- */
    function loadDashboardStats() {
      api.admin.getDashboardStats().then(function (stats) {
        if (stats.error) return;
        var map = {
          statNewMessages: stats.newMessages,
          statPendingQuotes: stats.pendingQuotes,
          statActiveOrders: stats.activeOrders,
          statCompletedOrders: stats.completedOrders
        };
        Object.keys(map).forEach(function (id) {
          var el = document.getElementById(id);
          if (el) el.textContent = (map[id] != null ? map[id] : '-');
        });
      });
    }

    /* ---------- 諮詢名單（合併聯絡表單＋線上估價） ---------- */
    function loadLeads() {
      var tbody = document.getElementById('leadsTableBody');
      if (!tbody) return;
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--ink-faint);">載入中…</td></tr>';

      api.admin.getLeads().then(function (res) {
        if (res.error) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--ink-faint);">載入失敗，請重新整理頁面。</td></tr>';
          return;
        }
        var messages = (res.messages || []).map(function (m) {
          return { type: 'message', id: m.id, name: m.name, phone: m.phone, email: m.email, summary: m.message, created_at: m.created_at, status: m.status };
        });
        var quotes = (res.quotes || []).map(function (q) {
          var parts = [];
          if (q.series) parts.push(q.series);
          if (q.carat) parts.push(q.carat + ' 克拉');
          if (q.product_type) parts.push(q.product_type);
          if (q.estimated_price != null) parts.push('NT$ ' + Number(q.estimated_price).toLocaleString('en-US'));
          return { type: 'quote', id: q.id, name: q.name, phone: q.phone, email: q.email, summary: parts.join('・') || '線上估價需求', created_at: q.created_at, status: q.status };
        });
        var all = messages.concat(quotes).sort(function (a, b) { return new Date(b.created_at) - new Date(a.created_at); });

        if (!all.length) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--ink-faint);">目前沒有諮詢紀錄。</td></tr>';
          return;
        }

        tbody.innerHTML = all.map(function (item) {
          var sourceLabel = item.type === 'message' ? '官網留言表單' : '線上估價';
          var isDone = ['replied', 'contacted', 'converted', 'closed'].indexOf(item.status) !== -1;
          return (
            '<tr>' +
              '<td class="name">' + escapeHtml(item.name) + '<span class="sub">' + escapeHtml(item.phone || item.email || '') + '</span></td>' +
              '<td>' + sourceLabel + '</td>' +
              '<td>' + escapeHtml(item.summary) + '</td>' +
              '<td>' + formatDateTime(item.created_at) + '</td>' +
              '<td><span class="chip ' + (isDone ? 'chip-done' : 'chip-new') + '">' + (isDone ? '已處理' : '待處理') + '</span></td>' +
              '<td>' + (isDone ? '' : '<button class="btn-sm" data-mark-done="' + item.type + ':' + item.id + '">標記已處理</button>') + '</td>' +
            '</tr>'
          );
        }).join('');

        tbody.querySelectorAll('[data-mark-done]').forEach(function (btn) {
          btn.addEventListener('click', function () {
            var sep = btn.dataset.markDone.indexOf(':');
            var kind = btn.dataset.markDone.slice(0, sep);
            var id = btn.dataset.markDone.slice(sep + 1);
            btn.disabled = true;
            btn.textContent = '更新中…';
            api.admin.markLeadDone(kind, id).then(function (res) {
              if (res.error) {
                console.error('[admin]', res.error);
                btn.disabled = false;
                btn.textContent = '更新失敗，再試一次';
                return;
              }
              loadLeads();
              loadDashboardStats();
            });
          });
        });
      });
    }

    /* ---------- 訂單與製作進度 ---------- */
    function loadOrders() {
      var tbody = document.getElementById('ordersTableBody');
      if (!tbody) return;
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--ink-faint);">載入中…</td></tr>';

      api.admin.getOrders().then(function (res) {
        if (res.error) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--ink-faint);">載入失敗，請重新整理頁面。</td></tr>';
          return;
        }
        var orders = res.orders || [];
        if (!orders.length) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--ink-faint);">目前沒有訂單，點右上角「+ 新增訂單」建立第一筆。</td></tr>';
          return;
        }

        tbody.innerHTML = orders.map(function (o) {
          var spec = [o.series, o.product_type].filter(Boolean).join(' ・ ') || '-';
          return (
            '<tr>' +
              '<td class="name">' + o.order_number + '<span class="sub">' + escapeHtml(o.customer_name) + '・' + escapeHtml(o.customer_phone) + '</span></td>' +
              '<td>' + escapeHtml(spec) + '</td>' +
              '<td><span class="chip ' + (STATUS_CHIP[o.status] || 'chip-new') + '">' + statusLabel(o.status) + '</span></td>' +
              '<td>' + escapeHtml(o.status_note || '-') + '</td>' +
              '<td>' + formatDateTime(o.created_at) + '</td>' +
              '<td><button class="btn-sm" data-update-order="' + o.id + '">更新進度</button></td>' +
            '</tr>'
          );
        }).join('');

        tbody.querySelectorAll('[data-update-order]').forEach(function (btn) {
          btn.addEventListener('click', function () {
            var order = orders.filter(function (o) { return o.id === btn.dataset.updateOrder; })[0];
            if (order) openUpdateOrderModal(order);
          });
        });
      });
    }

    function openUpdateOrderModal(order) {
      var optionsHtml = STATUS_OPTIONS.map(function (s) {
        return '<option value="' + s + '"' + (s === order.status ? ' selected' : '') + '>' + statusLabel(s) + '</option>';
      }).join('');

      openModal(
        '<div class="qr-modal" role="dialog" aria-modal="true">' +
          '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
          '<h3>更新訂單進度</h3>' +
          '<p class="qr-modal-sub">' + order.order_number + '・' + escapeHtml(order.customer_name) + '</p>' +
          '<form id="updateOrderForm" novalidate>' +
            '<div class="form-field"><label for="uoStatus">目前狀態</label>' +
              '<select id="uoStatus" style="width:100%;font-family:inherit;font-size:14px;padding:11px 14px;border:1px solid #E3DCD3;border-radius:6px;background:#FBFAF8;color:var(--ink);">' + optionsHtml + '</select>' +
            '</div>' +
            '<div class="form-field"><label for="uoNote">給客戶看的備註</label><textarea id="uoNote" rows="3">' + escapeHtml(order.status_note || '') + '</textarea></div>' +
            '<button type="submit" class="btn btn-dark" id="uoSubmitBtn">儲存更新</button>' +
            '<p class="form-msg" id="uoMsg"></p>' +
          '</form>' +
        '</div>'
      );

      document.getElementById('updateOrderForm').addEventListener('submit', function (e) {
        e.preventDefault();
        var newStatus = document.getElementById('uoStatus').value;
        var newNote = document.getElementById('uoNote').value.trim();
        var btn = document.getElementById('uoSubmitBtn');
        var msg = document.getElementById('uoMsg');
        btn.disabled = true;
        btn.textContent = '儲存中…';
        api.admin.updateOrderStatus(order.id, newStatus, newNote).then(function (res) {
          if (res.error) {
            msg.textContent = '更新失敗：' + res.error;
            msg.className = 'form-msg is-err';
            btn.disabled = false;
            btn.textContent = '儲存更新';
            return;
          }
          closeModal();
          loadOrders();
          loadDashboardStats();
        });
      });
    }

    function openNewOrderModal() {
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
          loadOrders();
          loadDashboardStats();
          document.getElementById('newOrderForm').innerHTML =
            '<div class="qr-modal-summary" style="margin-bottom:0;">' +
              '<p style="margin-bottom:8px;">訂單已建立！訂單編號：</p>' +
              '<p style="font-family:var(--serif);font-size:20px;font-weight:600;">' + res.orderNumber + '</p>' +
              '<p style="font-size:12.5px;color:#3A7A7A;margin-top:8px;">請把這組編號提供給客戶，客戶就能在「查詢訂製進度」頁面查詢。</p>' +
            '</div>';
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
      loadDashboardStats();
      loadLeads();
      loadOrders();

      var newOrderBtn = document.getElementById('btnNewOrder');
      if (newOrderBtn) newOrderBtn.addEventListener('click', openNewOrderModal);
    });

    window.AdminPanel = {
      onPanelSwitch: function (panel) {
        if (panel === 'dash') loadDashboardStats();
        if (panel === 'leads') loadLeads();
        if (panel === 'orders') loadOrders();
      }
    };
  });
})();
