/* 銘印鑽石｜搜尋會員 */
(function () {
  'use strict';

  var api = window.imprintAPI;
  if (!api || !api.admin) return;

  var root = document.getElementById('memberSearchRoot');
  if (!root) return;

  var _ready = false;
  var _timer = null;
  var _lastQ = '';
  var _cache = null;
  var _cachePromise = null;
  var _resultsById = {};

  function esc(s) {
    return window.AdminPanel && window.AdminPanel.escapeHtml
      ? window.AdminPanel.escapeHtml(s)
      : String(s == null ? '' : s);
  }

  function formatDate(iso) {
    if (!iso) return '—';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    return d.getFullYear() + '/' + (d.getMonth() + 1) + '/' + d.getDate();
  }

  function formatDateTime(iso) {
    if (!iso) return '—';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    var pad = function (n) { return n < 10 ? '0' + n : String(n); };
    return (
      d.getFullYear() + '/' + (d.getMonth() + 1) + '/' + d.getDate() +
      ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes())
    );
  }

  function shortId(id) {
    var s = String(id || '').replace(/-/g, '').toUpperCase();
    if (s.length < 10) return s || '—';
    return s.slice(0, 4) + ' ' + s.slice(4, 8) + ' ' + s.slice(8, 10);
  }

  function roleLabel(account) {
    if (account.is_admin) return '管理員';
    if (account.is_partner) return '合作廠商';
    return '會員';
  }

  function money(n) {
    if (n == null || n === '') return '—';
    return 'NT$ ' + Number(n).toLocaleString('zh-TW');
  }

  function detailRow(label, value) {
    if (value == null || value === '') return '';
    return (
      '<div class="lead-detail__row">' +
        '<span class="lead-detail__label">' + esc(label) + '</span>' +
        '<span class="lead-detail__value">' + esc(String(value)) + '</span>' +
      '</div>'
    );
  }

  function loadCache(force) {
    if (_cache && !force) return Promise.resolve(_cache);
    if (_cachePromise && !force) return _cachePromise;
    _cachePromise = api.admin.getAccounts().then(function (res) {
      _cachePromise = null;
      if (res.error) throw new Error(res.error.message || res.error);
      _cache = res.accounts || [];
      return _cache;
    });
    return _cachePromise;
  }

  function matchesAccount(account, q) {
    var needle = String(q || '').trim().toLowerCase();
    if (!needle) return false;
    var compact = needle.replace(/[\s\-]/g, '');
    var idCompact = String(account.id || '').replace(/-/g, '').toLowerCase();
    var fields = [
      account.email,
      account.full_name,
      account.phone,
      account.store_name,
      account.referral_code,
      account.id,
      idCompact,
      shortId(account.id),
    ];
    for (var i = 0; i < fields.length; i++) {
      var v = String(fields[i] || '').toLowerCase();
      if (!v) continue;
      if (v.indexOf(needle) >= 0) return true;
      if (compact && v.replace(/[\s\-]/g, '').indexOf(compact) >= 0) return true;
    }
    return false;
  }

  function renderResult(account) {
    var name = account.full_name || account.email || '—';
    var active = account.is_active !== false;
    return (
      '<button type="button" class="adx-member-search-card" data-account-id="' + esc(account.id) + '">' +
        '<div class="adx-member-search-card-main">' +
          '<div class="adx-member-search-name">' + esc(name) + '</div>' +
          '<div class="adx-member-search-meta">' +
            '<span>' + esc(account.email || '—') + '</span>' +
            '<span>' + esc(account.phone || '—') + '</span>' +
            '<span>' + esc(account.store_name || '—') + '</span>' +
          '</div>' +
          '<div class="adx-member-search-id" title="' + esc(account.id) + '">編號 ' + esc(shortId(account.id)) +
            (account.referral_code ? ' · 推薦碼 ' + esc(account.referral_code) : '') +
          '</div>' +
        '</div>' +
        '<div class="adx-member-search-side">' +
          '<span class="adx-chip ' + (active ? 'adx-chip--success' : 'adx-chip--default') + '">' +
            (active ? '啟用' : '停用') +
          '</span>' +
          '<span class="adx-chip adx-chip--default">' + esc(roleLabel(account)) + '</span>' +
          '<span class="adx-muted">訂單 ' + esc(String(account.order_count || 0)) + '</span>' +
          '<span class="adx-muted">註冊 ' + esc(formatDate(account.created_at)) + '</span>' +
          '<span class="adx-member-search-open">查看詳情 →</span>' +
        '</div>' +
      '</button>'
    );
  }

  function bindResultClicks() {
    var list = root.querySelector('#memberSearchResults');
    if (!list) return;
    list.querySelectorAll('[data-account-id]').forEach(function (el) {
      el.addEventListener('click', function () {
        openAccountDetail(el.getAttribute('data-account-id'));
      });
    });
  }

  function renderResults(accounts, q) {
    var list = root.querySelector('#memberSearchResults');
    if (!list) return;
    _resultsById = {};
    (accounts || []).forEach(function (a) {
      if (a && a.id) _resultsById[String(a.id)] = a;
    });
    if (!q) {
      list.innerHTML = '<p class="adx-table-empty">輸入姓名、Email、電話、店家、推薦碼或會員編號開始搜尋。</p>';
      return;
    }
    if (!accounts.length) {
      list.innerHTML = '<p class="adx-table-empty">找不到符合「' + esc(q) + '」的會員。</p>';
      return;
    }
    list.innerHTML =
      '<p class="adx-member-search-count">找到 ' + accounts.length + ' 位會員 · 點擊查看詳情</p>' +
      accounts.map(renderResult).join('');
    bindResultClicks();
  }

  function renderOrderRows(orders) {
    if (!orders || !orders.length) {
      return '<p class="adx-muted" style="margin:8px 0 0;font-size:12.5px">尚無訂單</p>';
    }
    return (
      '<div class="adx-member-detail-orders">' +
        orders.map(function (o) {
          return (
            '<div class="adx-member-detail-order">' +
              '<div>' +
                '<strong>' + esc(o.order_number || o.id || '—') + '</strong>' +
                '<span class="adx-muted"> · ' + esc(o.status || '—') + '</span>' +
              '</div>' +
              '<div class="adx-muted">' + esc(o.summary_zh || '—') + '</div>' +
              '<div class="adx-member-detail-order-meta">' +
                '<span>' + esc(money(o.total_price)) + '</span>' +
                '<span>' + esc(formatDateTime(o.created_at)) + '</span>' +
              '</div>' +
            '</div>'
          );
        }).join('') +
      '</div>'
    );
  }

  function openAccountDetail(accountId) {
    if (!accountId || !window.AdminPanel || !window.AdminPanel.openModal) return;
    var cached = _resultsById[String(accountId)];
    window.AdminPanel.openModal(
      '<div class="qr-modal lead-detail-modal adx-member-detail-modal" role="dialog" aria-modal="true">' +
        '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
        '<h3>會員詳情</h3>' +
        '<p class="qr-modal-sub">載入中…</p>' +
      '</div>'
    );

    api.admin.getAccount(accountId).then(function (res) {
      if (res.error) {
        window.AdminPanel.openModal(
          '<div class="qr-modal lead-detail-modal" role="dialog" aria-modal="true">' +
            '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
            '<h3>會員詳情</h3>' +
            '<p class="note warn">載入失敗：' + esc(res.error.message || res.error) + '</p>' +
            '<div class="ap-form-actions" style="margin-top:16px">' +
              '<button type="button" class="btn-sm" data-modal-close>關閉</button>' +
            '</div>' +
          '</div>'
        );
        return;
      }
      showAccountDetail(res.account || cached || {}, res.orders || []);
    }).catch(function (err) {
      window.AdminPanel.openModal(
        '<div class="qr-modal lead-detail-modal" role="dialog" aria-modal="true">' +
          '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
          '<h3>會員詳情</h3>' +
          '<p class="note warn">載入失敗：' + esc(err.message || err) + '</p>' +
        '</div>'
      );
    });
  }

  function showAccountDetail(account, orders) {
    var name = account.full_name || account.email || '—';
    var active = account.is_active !== false;
    var addressBits = [account.shipping_postal, account.shipping_city, account.shipping_address]
      .filter(Boolean)
      .join(' ');
    var body =
      detailRow('姓名', account.full_name || '—') +
      detailRow('Email', account.email || '—') +
      detailRow('電話', account.phone || '—') +
      detailRow('店家', account.store_name || '—') +
      detailRow('收件地址', addressBits || '—') +
      detailRow('權限', roleLabel(account)) +
      detailRow('狀態', active ? '啟用' : '停用') +
      detailRow('卡面編號', shortId(account.id)) +
      detailRow('帳號 ID', account.id || '—') +
      detailRow('推薦碼', account.referral_code || '—') +
      detailRow('推薦人', account.referred_by_label || account.referred_by || '—') +
      detailRow('銘鑽邀請', account.imprint_invited ? '是' : '否') +
      detailRow('合作銘鑽邀請', account.partner_imprint_invited ? '是' : '否') +
      detailRow('訂單數', String(account.order_count != null ? account.order_count : (orders || []).length)) +
      detailRow('註冊時間', formatDateTime(account.created_at)) +
      detailRow('最近登入', formatDateTime(account.last_login_at)) +
      '<div class="lead-detail__block" style="margin-top:12px">' +
        '<span class="lead-detail__label">近期訂單</span>' +
        renderOrderRows(orders) +
      '</div>';

    window.AdminPanel.openModal(
      '<div class="qr-modal lead-detail-modal adx-member-detail-modal" role="dialog" aria-modal="true" data-detail-id="' + esc(account.id) + '">' +
        '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
        '<h3>' + esc(name) + '</h3>' +
        '<p class="qr-modal-sub">' + esc(roleLabel(account)) + ' · ' + esc(active ? '啟用' : '停用') + '</p>' +
        '<div class="lead-detail">' + body + '</div>' +
        '<div class="ap-form-actions adx-member-detail-actions" style="margin-top:16px">' +
          '<button type="button" class="btn-sm" data-detail-action="toggle-active">' + (active ? '停用帳號' : '啟用帳號') + '</button>' +
          '<button type="button" class="btn-sm" data-detail-action="reset-password">重設密碼</button>' +
          '<button type="button" class="btn-sm" data-modal-close>關閉</button>' +
        '</div>' +
      '</div>'
    );

    var overlay = document.querySelector('.qr-modal-overlay.is-open');
    if (!overlay) return;
    var id = account.id;
    overlay.querySelectorAll('[data-detail-action]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var action = btn.getAttribute('data-detail-action');
        if (action === 'toggle-active') {
          var msg = active ? '確定停用此帳號？停用後無法登入。' : '確定啟用此帳號？';
          if (!confirm(msg)) return;
          btn.disabled = true;
          api.admin.accountAction(id, 'toggle-active').then(function (res) {
            btn.disabled = false;
            if (res.error) {
              alert('操作失敗：' + (res.error.message || res.error));
              return;
            }
            _cache = null;
            openAccountDetail(id);
            if (_lastQ) search(_lastQ);
          });
        } else if (action === 'reset-password') {
          var pwd = prompt('請輸入新密碼（至少 6 碼）：');
          if (!pwd) return;
          if (pwd.length < 6) {
            alert('密碼至少需要 6 碼');
            return;
          }
          btn.disabled = true;
          api.admin.accountAction(id, 'reset-password', { newPassword: pwd }).then(function (res) {
            btn.disabled = false;
            if (res.error) alert('重設失敗：' + (res.error.message || res.error));
            else alert('密碼已重設');
          });
        }
      });
    });
  }

  function search(q) {
    var query = (q || '').trim();
    _lastQ = query;
    var list = root.querySelector('#memberSearchResults');
    if (!list) return;
    if (!query) {
      renderResults([], '');
      return;
    }
    list.innerHTML = '<p class="adx-loading-inline">搜尋中…</p>';

    api.admin.getAccounts(query).then(function (res) {
      if (query !== _lastQ) return;
      var serverHits = (!res.error && res.accounts) ? res.accounts : null;
      if (serverHits && serverHits.length) {
        renderResults(serverHits, query);
        return;
      }
      return loadCache(!!res.error).then(function (all) {
        if (query !== _lastQ) return;
        renderResults(all.filter(function (a) { return matchesAccount(a, query); }), query);
      });
    }).catch(function (err) {
      if (query !== _lastQ) return;
      list.innerHTML = '<p class="note warn">搜尋失敗：' + esc(err.message || err) + '</p>';
    });
  }

  function renderShell() {
    root.innerHTML =
      '<header class="adx-member-search-head">' +
        '<h2>搜尋會員</h2>' +
        '<p class="adx-panel-note">依姓名、Email、電話、店家、推薦碼或卡面會員編號查詢；點擊結果查看詳情。</p>' +
      '</header>' +
      '<div class="orders-search adx-member-search-bar">' +
        '<input type="search" id="memberSearchInput" placeholder="搜尋姓名、Email、電話、店家、編號…" aria-label="搜尋會員" autocomplete="off">' +
      '</div>' +
      '<div id="memberSearchResults" class="adx-member-search-results" aria-live="polite">' +
        '<p class="adx-table-empty">輸入關鍵字開始搜尋。</p>' +
      '</div>';

    var input = document.getElementById('memberSearchInput');
    if (input) {
      input.addEventListener('input', function () {
        clearTimeout(_timer);
        _timer = setTimeout(function () {
          search(input.value);
        }, 300);
      });
      input.focus();
    }
  }

  function ensureLoaded() {
    if (!_ready) {
      renderShell();
      _ready = true;
      loadCache(false).catch(function () { /* ignore prefetch errors */ });
    } else {
      var input = document.getElementById('memberSearchInput');
      if (input) input.focus();
    }
  }

  window.AdminMemberSearchPanel = {
    search: search,
    ensureLoaded: ensureLoaded,
    openAccountDetail: openAccountDetail,
  };
})();
