/* 銘印鑽石｜邀請碼管理 */
(function () {
  'use strict';

  var api = window.imprintAPI;
  if (!api || !api.admin) return;

  var root = document.getElementById('invitesRoot');
  if (!root) return;

  var _loaded = false;

  function esc(s) {
    return window.AdminPanel && window.AdminPanel.escapeHtml
      ? window.AdminPanel.escapeHtml(s)
      : String(s == null ? '' : s);
  }

  function formatDate(iso) {
    if (!iso) return '—';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    var pad = function (n) { return n < 10 ? '0' + n : n; };
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  }

  function inviteStatus(inv) {
    if (!inv.is_active) return { label: '已停用', cls: 'adx-badge--revoked' };
    if (inv.expires_at && new Date(inv.expires_at) < new Date()) {
      return { label: '已過期', cls: 'adx-badge--revoked' };
    }
    if (inv.max_uses != null && inv.use_count >= inv.max_uses) {
      return { label: '已用完', cls: 'adx-badge--revoked' };
    }
    return { label: '有效', cls: 'adx-badge--active' };
  }

  function usesLabel(inv) {
    var used = inv.use_count || 0;
    var max = inv.max_uses;
    return max == null ? used + ' / 不限' : used + ' / ' + max;
  }

  function roleLabel(inv) {
    if (inv.grants_admin) return { text: '管理員', cls: 'adx-badge--role-admin' };
    if (inv.grants_partner) return { text: '合作廠商', cls: 'adx-badge--role-partner' };
    return { text: '一般會員', cls: 'adx-badge--role-member' };
  }

  function renderRow(inv) {
    var status = inviteStatus(inv);
    var role = roleLabel(inv);
    var canRevoke = inv.is_active && status.cls === 'adx-badge--active';
    return '<tr data-id="' + esc(inv.id) + '"' +
      ' data-sort-code="' + esc(inv.code) + '"' +
      ' data-sort-label="' + esc(inv.label || '') + '"' +
      ' data-sort-uses="' + esc(String(inv.use_count || 0)) + '"' +
      ' data-sort-role="' + esc(role.text) + '"' +
      ' data-sort-status="' + esc(status.label) + '"' +
      ' data-sort-expires="' + esc(inv.expires_at || '') + '"' +
      ' data-sort-created="' + esc(inv.created_at || '') + '">' +
      '<td><code class="adx-code">' + esc(inv.code) + '</code></td>' +
      '<td>' + esc(inv.label || '—') + '</td>' +
      '<td>' + esc(usesLabel(inv)) + '</td>' +
      '<td><span class="adx-badge ' + role.cls + '">' + esc(role.text) + '</span></td>' +
      '<td><span class="adx-badge ' + status.cls + '">' + status.label + '</span></td>' +
      '<td class="adx-muted">' + esc(formatDate(inv.expires_at)) + '</td>' +
      '<td class="adx-muted">' + esc(formatDate(inv.created_at)) + '</td>' +
      '<td><div class="adx-actions">' +
        '<button type="button" class="btn-sm" data-action="copy" data-code="' + esc(inv.code) + '">複製</button>' +
        (canRevoke ? '<button type="button" class="btn-sm" data-action="revoke" data-id="' + esc(inv.id) + '">停用</button>' : '') +
        '<button type="button" class="btn-sm adx-action--danger" data-action="delete" data-id="' + esc(inv.id) + '">刪除</button>' +
      '</div></td></tr>';
  }

  function renderTable(invites) {
    if (!invites.length) {
      return '<p class="adx-table-empty">尚無邀請碼。點「建立邀請碼」為合作廠商產生註冊碼。</p>';
    }
    var rows = invites.map(renderRow).join('');
    return (
      '<div class="adx-table-card">' +
        '<div class="adx-table-wrap">' +
          '<table class="adx-table">' +
            '<thead><tr>' +
              '<th data-sort-key="code" data-sortable="text">邀請碼</th>' +
              '<th data-sort-key="label" data-sortable="text">合作廠商</th>' +
              '<th data-sort-key="uses" data-sortable="number">已使用 / 上限</th>' +
              '<th data-sort-key="role" data-sortable="text">權限</th>' +
              '<th data-sort-key="status" data-sortable="text">狀態</th>' +
              '<th data-sort-key="expires" data-sortable="date">到期日</th>' +
              '<th data-sort-key="created" data-sortable="date">建立時間</th>' +
              '<th data-sortable="false">操作</th>' +
            '</tr></thead>' +
            '<tbody>' + rows + '</tbody>' +
          '</table>' +
        '</div>' +
      '</div>'
    );
  }

  function renderShell(invites) {
    root.innerHTML =
      '<p class="adx-panel-note">建立邀請碼供合作廠商註冊帳號。可設定名稱、使用次數與有效期限；刪除邀請碼不影響已註冊帳戶。</p>' +
      '<div class="adx-panel-toolbar"><button type="button" class="btn-sm btn-primary" id="btnCreateInvite">+ 建立邀請碼</button></div>' +
      renderTable(invites);
    bindEvents();
    var table = root.querySelector('.adx-table');
    if (table && window.AdminTableSort) window.AdminTableSort.bind(table);
  }

  function openCreateModal() {
    var html =
      '<div class="qr-modal ai-modal" role="dialog" aria-modal="true">' +
        '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
        '<h3>建立邀請碼</h3>' +
        '<p class="qr-modal-sub">產生隨機邀請碼，可指定合作廠商名稱、使用次數與有效期限。</p>' +
        '<p class="ap-form-error" id="aiFormError" hidden></p>' +
        '<form id="aiCreateForm" class="ap-form">' +
          '<div class="ap-form-grid">' +
            '<label class="ap-field-wide"><span>合作廠商名稱</span>' +
              '<input name="label" maxlength="120" placeholder="例：台北鑽石行"></label>' +
            '<label><span>可使用次數</span>' +
              '<input type="number" name="maxUses" min="1" step="1" placeholder="留空 = 不限"></label>' +
            '<label><span>有效天數</span>' +
              '<input type="number" name="expiresInDays" min="1" step="1" placeholder="留空 = 永久"></label>' +
            '<p class="ai-section-label ap-field-wide">帳號類型（請擇一）</p>' +
            '<label class="ap-checkbox ap-field-wide">' +
              '<input type="checkbox" name="grantsPartner" id="aiGrantsPartner" checked> 以此碼註冊為合作廠商帳號</label>' +
            '<p class="ai-hint ap-field-wide" id="aiPartnerHint">可設定上方「可使用次數」與「有效天數」。</p>' +
            '<label class="ap-checkbox ap-field-wide">' +
              '<input type="checkbox" name="grantsAdmin" id="aiGrantsAdmin"> 以此碼註冊為管理員帳號</label>' +
            '<p class="ai-hint ap-field-wide" id="aiAdminHint" hidden>管理員邀請碼僅限使用 1 次，建立時需輸入您目前登入帳號的密碼。</p>' +
            '<label class="ap-field-wide" id="aiPasswordField" hidden><span>管理員密碼</span>' +
              '<input type="password" name="adminPassword" autocomplete="current-password"></label>' +
          '</div>' +
          '<div class="ap-form-actions">' +
            '<button type="button" class="btn-sm" data-modal-close>取消</button>' +
            '<button type="submit" class="btn-sm btn-primary" id="aiSubmitBtn">建立</button>' +
          '</div>' +
        '</form></div>';

    if (!window.AdminPanel || !window.AdminPanel.openModal) {
      alert('無法開啟表單，請重新整理頁面。');
      return;
    }
    window.AdminPanel.openModal(html);

    var form = document.getElementById('aiCreateForm');
    var grantsAdmin = document.getElementById('aiGrantsAdmin');
    var grantsPartner = document.getElementById('aiGrantsPartner');
    var hint = document.getElementById('aiAdminHint');
    var partnerHint = document.getElementById('aiPartnerHint');
    var pwdField = document.getElementById('aiPasswordField');
    var maxUses = form.querySelector('[name="maxUses"]');

    function syncRoleFields() {
      var isAdmin = grantsAdmin && grantsAdmin.checked;
      var isPartner = grantsPartner && grantsPartner.checked;
      if (hint) hint.hidden = !isAdmin;
      if (pwdField) pwdField.hidden = !isAdmin;
      if (partnerHint) partnerHint.hidden = !isPartner || isAdmin;
      if (maxUses) {
        maxUses.disabled = isAdmin;
        if (isAdmin) maxUses.value = '1';
      }
    }

    grantsAdmin?.addEventListener('change', function () {
      if (grantsAdmin.checked && grantsPartner) grantsPartner.checked = false;
      syncRoleFields();
    });
    grantsPartner?.addEventListener('change', function () {
      if (grantsPartner.checked && grantsAdmin) grantsAdmin.checked = false;
      syncRoleFields();
    });
    syncRoleFields();

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      submitCreate(form);
    });
  }

  function submitCreate(form) {
    var fd = new FormData(form);
    var errEl = document.getElementById('aiFormError');
    var btn = document.getElementById('aiSubmitBtn');
    var grantsAdminChecked = !!form.querySelector('[name="grantsAdmin"]')?.checked;
    var grantsPartnerChecked = !!form.querySelector('[name="grantsPartner"]')?.checked;

    if (!grantsAdminChecked && !grantsPartnerChecked) {
      if (errEl) {
        errEl.textContent = '請選擇帳號類型：合作廠商或管理員';
        errEl.hidden = false;
      } else {
        alert('請選擇帳號類型：合作廠商或管理員');
      }
      return;
    }

    var payload = {
      label: String(fd.get('label') || '').trim(),
      maxUses: fd.get('maxUses') === '' ? null : fd.get('maxUses'),
      expiresInDays: fd.get('expiresInDays') === '' ? null : fd.get('expiresInDays'),
      grantsAdmin: grantsAdminChecked,
      grantsPartner: grantsPartnerChecked,
      adminPassword: grantsAdminChecked ? String(fd.get('adminPassword') || '') : undefined,
    };

    if (btn) { btn.disabled = true; btn.textContent = '建立中…'; }
    if (errEl) errEl.hidden = true;

    api.admin.createInvite(payload).then(function (res) {
      if (btn) { btn.disabled = false; btn.textContent = '建立'; }
      if (res.error) {
        if (errEl) {
          errEl.textContent = typeof res.error === 'string' ? res.error : (res.error.message || '建立失敗');
          errEl.hidden = false;
        } else {
          alert(res.error);
        }
        return;
      }
      if (window.AdminPanel.closeModal) window.AdminPanel.closeModal();
      if (res.invite && res.invite.code) copyCode(res.invite.code);
      load(true, true);
    });
  }

  function copyCode(code) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(code).then(function () {
        alert('已複製邀請碼：' + code);
      }).catch(function () {
        prompt('請手動複製邀請碼：', code);
      });
    } else {
      prompt('請手動複製邀請碼：', code);
    }
  }

  function bindEvents() {
    var createBtn = document.getElementById('btnCreateInvite');
    if (createBtn) createBtn.addEventListener('click', openCreateModal);

    root.querySelectorAll('[data-action]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var action = btn.dataset.action;
        if (action === 'copy') {
          copyCode(btn.dataset.code);
          return;
        }
        var id = btn.dataset.id;
        if (!id) return;
        if (action === 'delete' && !confirm('確定刪除此邀請碼？已註冊的帳戶不受影響。')) return;
        if (action === 'revoke' && !confirm('確定停用此邀請碼？')) return;

        var row = btn.closest('tr');
        btn.disabled = true;
        api.admin.inviteAction(id, action).then(function (res) {
          btn.disabled = false;
          if (res.error) {
            alert('操作失敗：' + (res.error.message || res.error));
            return;
          }
          if (action === 'delete' && row) {
            row.remove();
            if (!root.querySelector('.adx-table tbody tr')) {
              var card = root.querySelector('.adx-table-card');
              if (card) {
                card.outerHTML = '<p class="adx-table-empty">尚無邀請碼。點「建立邀請碼」為合作廠商產生註冊碼。</p>';
              }
            }
            return;
          }
          load(true, true);
        });
      });
    });
  }

  function load(silent, force) {
    if (_loaded && !force) return;
    if (!silent) {
      root.innerHTML = window.SkeletonUI ? window.SkeletonUI.invitesShell() : '<p class="adx-loading-inline">載入邀請碼中…</p>';
    }
    api.admin.getInvites().then(function (res) {
      if (res.error) {
        root.innerHTML = '<p class="note warn">載入失敗：' + esc(res.error) + '</p>';
        return;
      }
      _loaded = true;
      renderShell(res.invites || []);
    });
  }

  function ensureLoaded() {
    load(_loaded);
  }

  window.AdminInvitesPanel = { load: load, ensureLoaded: ensureLoaded };

  if (root && window.SkeletonUI && !_loaded && root.querySelector('.skel-line')) {
    root.innerHTML = window.SkeletonUI.invitesShell();
  }
})();
