/* 銘印鑽石｜帳戶管理 */
window.ImprintMemberId = window.ImprintMemberId || (function () {
  'use strict';
  function deriveMemberDisplayNumber(id) {
    var compact = String(id || '').replace(/[\s-]/g, '').trim().toLowerCase();
    if (!compact || !/^[0-9a-f]+$/.test(compact)) return '';
    try {
      var n = BigInt('0x' + compact) % BigInt('1000000000000');
      return n.toString().padStart(12, '0');
    } catch (e) {
      return '';
    }
  }
  function formatMemberDisplayGroups(id) {
    var number = deriveMemberDisplayNumber(id);
    if (!number) return '—';
    return number.replace(/(.{4})/g, '$1 ').trim();
  }
  return { deriveMemberDisplayNumber: deriveMemberDisplayNumber, formatMemberDisplayGroups: formatMemberDisplayGroups };
})();

(function () {
  'use strict';

  var api = window.imprintAPI;
  if (!api || !api.admin) return;

  var root = document.getElementById('accountsRoot');
  if (!root) return;

  var _loaded = false;
  var _allAccounts = [];
  var _query = '';
  var _searchTimer = null;
  var _membershipEnabled = true;
  var _page = 1;
  var _pageSize = 20;
  var _total = 0;

  function membershipProgramOn() {
    return _membershipEnabled !== false;
  }

  function esc(s) {
    return window.AdminPanel && window.AdminPanel.escapeHtml
      ? window.AdminPanel.escapeHtml(s)
      : String(s == null ? '' : s);
  }

  function formatMonth(iso) {
    if (!iso) return '—';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    var months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
    return d.getFullYear() + '年' + months[d.getMonth()];
  }

  function shortId(id) {
    return window.ImprintMemberId
      ? window.ImprintMemberId.formatMemberDisplayGroups(id)
      : String(id || '').slice(0, 12);
  }

  function initials(account) {
    var name = (account.full_name || account.email || '?').trim();
    if (!name) return '?';
    var parts = name.split(/\s+/);
    if (parts.length > 1) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
  }

  function accountRole(account) {
    if (account.is_admin) return 'admin';
    if (account.is_partner) return 'partner';
    return 'member';
  }

  function matchesAccount(account, q) {
    var needle = String(q || '').trim().toLowerCase();
    if (!needle) return true;
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
      window.ImprintMemberId ? window.ImprintMemberId.deriveMemberDisplayNumber(account.id) : '',
      accountRole(account) === 'admin' ? '管理員' : (accountRole(account) === 'partner' ? '合作廠商' : '會員'),
    ];
    for (var i = 0; i < fields.length; i++) {
      var v = String(fields[i] || '').toLowerCase();
      if (!v) continue;
      if (v.indexOf(needle) >= 0) return true;
      if (compact && v.replace(/[\s\-]/g, '').indexOf(compact) >= 0) return true;
    }
    return false;
  }

  function filteredAccounts() {
    return _allAccounts.slice();
  }

  function pagerHtml() {
    var pageCount = Math.max(1, Math.ceil(_total / Math.max(_pageSize, 1)));
    if (pageCount <= 1 && !_query) {
      return '<p class="adx-member-search-count" id="accountsSearchCount">共 ' + _total + ' 筆</p>';
    }
    return (
      '<div class="adx-pager" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0;">' +
        '<p class="adx-member-search-count" id="accountsSearchCount" style="margin:0;">' +
          (_query ? ('搜尋結果 ' + _total + ' 筆') : ('共 ' + _total + ' 筆')) +
          ' · 第 ' + _page + ' / ' + pageCount + ' 頁' +
        '</p>' +
        '<button type="button" class="btn-sm" id="accountsPrevPage"' + (_page <= 1 ? ' disabled' : '') + '>上一頁</button>' +
        '<button type="button" class="btn-sm" id="accountsNextPage"' + (_page >= pageCount ? ' disabled' : '') + '>下一頁</button>' +
      '</div>'
    );
  }

  function roleSelect(account) {
    var role = accountRole(account);
    var selfId = window.AdminPanel && window.AdminPanel.currentUserId;
    var isSelf = selfId && String(account.id) === String(selfId);
    return (
      '<select class="adx-role-select" data-action="set-role" data-id="' + esc(account.id) + '"' +
        (isSelf ? ' disabled title="無法變更自己的權限"' : '') + '>' +
        '<option value="member"' + (role === 'member' ? ' selected' : '') + '>會員</option>' +
        '<option value="partner"' + (role === 'partner' ? ' selected' : '') + '>合作廠商</option>' +
        '<option value="admin"' + (role === 'admin' ? ' selected' : '') + '>管理員</option>' +
      '</select>'
    );
  }

  function renderRow(account) {
    var name = account.full_name || account.email || '—';
    var active = account.is_active !== false;
    var role = accountRole(account);
    var roleLabel = role === 'admin' ? '管理員' : (role === 'partner' ? '合作廠商' : '會員');
    return (
      '<div class="adx-member-row" data-id="' + esc(account.id) + '"' +
        ' data-sort-name="' + esc(name) + '"' +
        ' data-sort-role="' + esc(roleLabel) + '"' +
        ' data-sort-status="' + esc(active ? '啟用' : '停用') + '"' +
        ' data-sort-joined="' + esc(account.created_at || '') + '"' +
        ' data-sort-store="' + esc(account.store_name || '') + '"' +
        ' data-sort-orders="' + esc(String(account.order_count || 0)) + '">' +
        '<div class="adx-col-grow adx-member-identity">' +
          '<div class="adx-avatar-wrap">' +
            '<div class="adx-avatar" aria-hidden="true">' + esc(initials(account)) + '</div>' +
            '<span class="adx-avatar-dot ' + (active ? 'adx-avatar-dot--on' : 'adx-avatar-dot--off') + '" title="' + (active ? '啟用' : '停用') + '"></span>' +
          '</div>' +
          '<div class="adx-member-text">' +
            '<div class="adx-member-name">' + esc(name) + '</div>' +
            '<div class="adx-member-email">' + esc(account.email || '—') + '</div>' +
          '</div>' +
        '</div>' +
        '<div class="adx-col-role">' + roleSelect(account) +
          (membershipProgramOn()
            ? ('<div class="adx-muted" style="margin-top:6px;font-size:11px;line-height:1.5">' +
                '<label><input type="checkbox" data-action="set-imprint-invited" data-id="' + esc(account.id) + '"' +
                  (account.imprint_invited ? ' checked' : '') + '> 銘鑽邀請</label><br>' +
                '<label><input type="checkbox" data-action="set-partner-imprint-invited" data-id="' + esc(account.id) + '"' +
                  (account.partner_imprint_invited ? ' checked' : '') + '> 合作銘鑽邀請</label>' +
              '</div>')
            : '') +
        '</div>' +
        '<div class="adx-col-status"><span class="adx-chip ' + (active ? 'adx-chip--success' : 'adx-chip--default') + '">' + (active ? '啟用' : '停用') + '</span></div>' +
        '<div class="adx-col-joined adx-muted">' + esc(formatMonth(account.created_at)) + '</div>' +
        '<div class="adx-col-store adx-muted adx-truncate" title="' + esc(account.store_name || '') + '">' + esc(account.store_name || '—') + '</div>' +
        '<div class="adx-col-orders adx-muted">' + esc(String(account.order_count || 0)) + '</div>' +
        '<div class="adx-col-actions adx-account-actions">' +
          '<span class="adx-muted adx-pwd-hint">已加密儲存</span>' +
          '<div class="adx-actions">' +
            '<button type="button" class="btn-sm' + (active ? ' adx-action--danger' : '') + '" data-action="toggle-active" data-id="' + esc(account.id) + '" data-active="' + (active ? '1' : '0') + '">' + (active ? '停用' : '啟用') + '</button>' +
            '<button type="button" class="btn-sm" data-action="reset-password" data-id="' + esc(account.id) + '">重設</button>' +
            '<button type="button" class="btn-sm adx-action--danger" data-action="delete-account" data-id="' + esc(account.id) + '" data-email="' + esc(account.email || '') + '" data-orders="' + esc(String(account.order_count || 0)) + '" data-name="' + esc(name) + '">刪除帳號</button>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  function renderList(accounts) {
    if (!_total && !_query) {
      return '<p class="adx-table-empty">尚無註冊帳號。</p>';
    }
    if (!accounts.length) {
      return '<p class="adx-table-empty">' +
        (_query ? ('找不到符合「' + esc(_query) + '」的帳號。') : '此頁沒有帳號。') +
        '</p>';
    }
    var rows = accounts.map(renderRow).join('');
    return (
      '<div class="adx-member-head">' +
        '<div class="adx-col-grow" data-sort-key="name" data-sortable="text">帳號</div>' +
        '<div class="adx-col-role" data-sort-key="role" data-sortable="text">權限</div>' +
        '<div class="adx-col-status" data-sort-key="status" data-sortable="text">狀態</div>' +
        '<div class="adx-col-joined" data-sort-key="joined" data-sortable="date">註冊</div>' +
        '<div class="adx-col-store" data-sort-key="store" data-sortable="text">店家</div>' +
        '<div class="adx-col-orders" data-sort-key="orders" data-sortable="number">訂單</div>' +
        '<div class="adx-col-actions" data-sortable="false">操作</div>' +
      '</div>' + rows
    );
  }

  function clearPanelBusy() {
    root.removeAttribute('aria-busy');
    root.classList.remove('skel-panel');
  }

  function renderShell(accounts) {
    _allAccounts = accounts || [];
    clearPanelBusy();
    var shown = filteredAccounts();
    root.innerHTML =
      '<p class="adx-panel-note">已註冊帳號（密碼以加密方式儲存，無法顯示原文）</p>' +
      '<div class="adx-security-banner">為保護帳號安全，系統不儲存也不顯示明文密碼。如需協助店家登入，請使用「重設」設定新密碼後私下告知該店家。</div>' +
      '<div class="orders-search adx-accounts-search">' +
        '<input type="search" id="accountsSearchInput" placeholder="搜尋姓名、Email、電話、店家、編號…" aria-label="搜尋帳號" autocomplete="off" value="' + esc(_query) + '">' +
      '</div>' +
      pagerHtml() +
      '<div class="adx-member-list">' + renderList(shown) + '</div>';
    bindEvents();
    bindSearch();
    bindPager();
    var list = root.querySelector('.adx-member-list');
    if (list && window.AdminTableSort) window.AdminTableSort.bindMemberList(list);
  }

  function bindSearch() {
    var input = document.getElementById('accountsSearchInput');
    if (!input) return;
    input.addEventListener('input', function () {
      clearTimeout(_searchTimer);
      _searchTimer = setTimeout(function () {
        _query = input.value.trim();
        _page = 1;
        load(true, true);
      }, 200);
    });
  }

  function bindPager() {
    var prev = document.getElementById('accountsPrevPage');
    var next = document.getElementById('accountsNextPage');
    if (prev) {
      prev.addEventListener('click', function () {
        if (_page <= 1) return;
        _page -= 1;
        load(true, true);
      });
    }
    if (next) {
      next.addEventListener('click', function () {
        var pageCount = Math.max(1, Math.ceil(_total / Math.max(_pageSize, 1)));
        if (_page >= pageCount) return;
        _page += 1;
        load(true, true);
      });
    }
  }

  function bindEvents() {
    root.querySelectorAll('[data-action="toggle-active"]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        var id = btn.dataset.id;
        var isActive = btn.dataset.active === '1';
        var msg = isActive ? '確定停用此帳號？停用後無法登入。' : '確定啟用此帳號？';
        if (!confirm(msg)) return;
        var step = (api.collectStepUp && api.collectStepUp(isActive ? '停用帳號' : '啟用帳號'))
          || { error: '已取消（需管理員密碼）' };
        if (step.error) {
          alert(step.error);
          return;
        }
        btn.disabled = true;
        api.admin.accountAction(id, 'toggle-active', {
          password: step.password,
          totpCode: step.totpCode,
        }).then(function (res) {
          btn.disabled = false;
          if (res.error) {
            alert('操作失敗：' + (res.error.message || res.error));
            return;
          }
          load(true, true);
        });
      });
    });

    root.querySelectorAll('[data-action="set-imprint-invited"], [data-action="set-partner-imprint-invited"]').forEach(function (box) {
      box.addEventListener('change', function () {
        var id = box.dataset.id;
        var action = box.dataset.action;
        var value = !!box.checked;
        box.disabled = true;
        api.admin.accountAction(id, action, { value: value }).then(function (res) {
          box.disabled = false;
          if (res.error) {
            alert('變更失敗：' + (res.error.message || res.error));
            box.checked = !value;
            return;
          }
        });
      });
    });

    root.querySelectorAll('[data-action="set-role"]').forEach(function (sel) {
      sel.addEventListener('change', function () {
        var id = sel.dataset.id;
        var role = sel.value;
        var prev = sel.dataset.prevRole || sel.value;
        if (!confirm('確定將此帳號權限改為「' + sel.options[sel.selectedIndex].text + '」？')) {
          sel.value = prev;
          return;
        }
        sel.disabled = true;
        api.admin.accountAction(id, 'set-role', { role: role }).then(function (res) {
          sel.disabled = false;
          if (res.error) {
            alert('變更失敗：' + (res.error.message || res.error));
            sel.value = prev;
            return;
          }
          sel.dataset.prevRole = role;
          load(true, true);
        });
      });
      sel.dataset.prevRole = sel.value;
    });

    root.querySelectorAll('[data-action="reset-password"]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        var id = btn.dataset.id;
        var pwd = prompt('請輸入新密碼（至少 8 碼）：');
        if (!pwd) return;
        if (pwd.length < 8) {
          alert('密碼至少需要 8 碼');
          return;
        }
        btn.disabled = true;
        api.admin.accountAction(id, 'reset-password', { newPassword: pwd }).then(function (res) {
          btn.disabled = false;
          if (res.error) alert('重設失敗：' + (res.error.message || res.error));
          else alert('密碼已重設');
        });
      });
    });

    root.querySelectorAll('[data-action="delete-account"]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        var id = btn.dataset.id;
        var email = btn.dataset.email || '';
        var orders = btn.dataset.orders || '0';
        var label = btn.dataset.name || email || id;
        if (!confirm('確定刪除帳號「' + label + '」？其 ' + orders + ' 筆訂單將一併刪除，且無法復原。')) return;
        var typed = prompt('請輸入該帳戶 Email 以確認刪除：\n' + email);
        if (typed == null) return;
        if (String(typed).trim().toLowerCase() !== String(email).trim().toLowerCase()) {
          alert('Email 不符，已取消刪除。');
          return;
        }
        var adminPwd = prompt('請輸入您的管理員密碼以確認刪除：');
        if (adminPwd == null || !String(adminPwd).trim()) {
          alert('已取消刪除（需管理員密碼）。');
          return;
        }
        var adminTotp = prompt('若已啟用 Authenticator（用於重設密碼／敏感操作），請輸入驗證碼；否則留空後確定：') || '';
        btn.disabled = true;
        api.admin.accountAction(id, 'delete', {
          confirmEmail: typed.trim(),
          password: String(adminPwd),
          totpCode: String(adminTotp).trim() || undefined,
        }).then(function (res) {
          btn.disabled = false;
          if (res.error) {
            var msg = res.error.message || res.error;
            if (window.showToast) window.showToast('刪除失敗：' + msg, 'error');
            else alert('刪除失敗：' + msg);
            return;
          }
          _allAccounts = _allAccounts.filter(function (a) { return String(a.id) !== String(id); });
          updateListOnly();
          if (window.showToast) window.showToast('已刪除帳號', 'success');
          else alert('已刪除帳號');
        });
      });
    });
  }

  function load(silent, force) {
    if (_loaded && !force) return;
    clearPanelBusy();
    if (!silent) {
      root.innerHTML = window.SkeletonUI ? window.SkeletonUI.accountsShell() : '<p class="adx-loading-inline">載入帳戶中…</p>';
    }
    var accountsP = api.admin.getAccounts({
      q: _query || undefined,
      page: _page,
      pageSize: _pageSize,
    });
    var membershipP = api.getMembershipConfig
      ? api.getMembershipConfig()
      : Promise.resolve({ config: { enabled: true } });
    Promise.all([accountsP, membershipP]).then(function (results) {
      var res = results[0] || {};
      var membershipRes = results[1] || {};
      var cfg = membershipRes.config || {};
      _membershipEnabled = !membershipRes.error && cfg.enabled !== false;
      if (res.error) {
        clearPanelBusy();
        root.innerHTML = '<p class="note warn">載入失敗：' + esc(res.error) + '</p>';
        return;
      }
      _total = typeof res.total === 'number' ? res.total : (res.accounts || []).length;
      if (typeof res.page === 'number' && res.page > 0) _page = res.page;
      if (typeof res.page_size === 'number' && res.page_size > 0) _pageSize = res.page_size;
      _loaded = true;
      renderShell(res.accounts || []);
    });
  }

  function ensureLoaded() {
    load(_loaded);
  }

  window.AdminAccountsPanel = { load: load, ensureLoaded: ensureLoaded };
})();
