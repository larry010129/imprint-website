/* 銘印鑽石｜優惠券管理 */
(function () {
  'use strict';

  var api = window.imprintAPI;
  if (!api || !api.admin) return;

  var root = document.getElementById('couponsRoot');
  if (!root) return;

  var _loaded = false;
  var _coupons = [];

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

  function formatExpiry(iso) {
    return iso ? formatDate(iso) : '不限期';
  }

  function toDateInput(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    var pad = function (n) { return n < 10 ? '0' + n : n; };
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  }

  function formatMoney(n) {
    if (n == null || n === '') return '—';
    return 'NT$' + Math.round(Number(n)).toLocaleString('zh-Hant-TW');
  }

  function discountLabel(c) {
    if (c.discount_type === 'percent') return Math.round(Number(c.discount_value)) + '%';
    return formatMoney(c.discount_value);
  }

  function couponStatus(c) {
    if (!c.is_active) return { label: '已停用', cls: 'adx-badge--revoked' };
    if (c.expires_at && new Date(c.expires_at) < new Date()) {
      return { label: '已過期', cls: 'adx-badge--revoked' };
    }
    if (c.starts_at && new Date(c.starts_at) > new Date()) {
      return { label: '尚未開始', cls: 'adx-badge--revoked' };
    }
    if (c.max_uses != null && c.used_count >= c.max_uses) {
      return { label: '已用完', cls: 'adx-badge--revoked' };
    }
    return { label: '有效', cls: 'adx-badge--active' };
  }

  function usesLabel(c) {
    var used = c.used_count || 0;
    var max = c.max_uses;
    return max == null ? used + ' / 不限' : used + ' / ' + max;
  }

  function findCoupon(id) {
    for (var i = 0; i < _coupons.length; i++) {
      if (String(_coupons[i].id) === String(id)) return _coupons[i];
    }
    return null;
  }

  function renderRow(c) {
    var status = couponStatus(c);
    var canDeactivate = c.is_active;
    var canActivate = !c.is_active;
    return '<tr data-id="' + esc(c.id) + '"' +
      ' data-sort-code="' + esc(c.code) + '"' +
      ' data-sort-label="' + esc(c.label || '') + '"' +
      ' data-sort-discount="' + esc(String(c.discount_value || 0)) + '"' +
      ' data-sort-uses="' + esc(String(c.used_count || 0)) + '"' +
      ' data-sort-status="' + esc(status.label) + '"' +
      ' data-sort-expires="' + esc(c.expires_at || '') + '"' +
      ' data-sort-created="' + esc(c.created_at || '') + '">' +
      '<td><code class="adx-code">' + esc(c.code) + '</code></td>' +
      '<td>' + esc(c.label || '—') + '</td>' +
      '<td>' + esc(discountLabel(c)) + '</td>' +
      '<td>' + esc(usesLabel(c)) + '</td>' +
      '<td>' + (c.max_uses_per_user == null ? '不限' : esc(String(c.max_uses_per_user))) + '</td>' +
      '<td>' + (c.min_order_amount != null ? esc(formatMoney(c.min_order_amount)) : '—') + '</td>' +
      '<td><span class="adx-badge ' + status.cls + '">' + status.label + '</span></td>' +
      '<td class="adx-muted">' + esc(formatExpiry(c.expires_at)) + '</td>' +
      '<td class="adx-muted">' + esc(formatDate(c.created_at)) + '</td>' +
      '<td><div class="adx-actions">' +
        '<button type="button" class="btn-sm" data-action="edit" data-id="' + esc(c.id) + '">編輯</button>' +
        '<button type="button" class="btn-sm" data-action="copy" data-code="' + esc(c.code) + '">複製</button>' +
        (canDeactivate ? '<button type="button" class="btn-sm" data-action="deactivate" data-id="' + esc(c.id) + '">停用</button>' : '') +
        (canActivate ? '<button type="button" class="btn-sm" data-action="activate" data-id="' + esc(c.id) + '">啟用</button>' : '') +
        '<button type="button" class="btn-sm adx-action--danger" data-action="delete" data-id="' + esc(c.id) + '">刪除</button>' +
      '</div></td></tr>';
  }

  function renderTable(coupons) {
    if (!coupons.length) {
      return '<p class="adx-table-empty">尚無優惠券。點「建立優惠券」新增折扣碼。</p>';
    }
    var rows = coupons.map(renderRow).join('');
    return (
      '<div class="adx-table-card">' +
        '<div class="adx-table-wrap">' +
          '<table class="adx-table adx-table--center">' +
            '<thead><tr>' +
              '<th data-sort-key="code" data-sortable="text">優惠碼</th>' +
              '<th data-sort-key="label" data-sortable="text">備註</th>' +
              '<th data-sort-key="discount" data-sortable="number">折扣</th>' +
              '<th data-sort-key="uses" data-sortable="number">已使用 / 上限</th>' +
              '<th data-sortable="false">每人上限</th>' +
              '<th data-sortable="false">最低消費</th>' +
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

  function renderShell(coupons) {
    _coupons = coupons || [];
    root.innerHTML =
      '<p class="adx-panel-note">建立結帳優惠碼（百分比或固定金額）。可設定最低消費、使用次數、每人上限與有效期限。</p>' +
      '<div class="adx-panel-toolbar"><button type="button" class="btn-sm btn-primary" id="btnCreateCoupon">+ 建立優惠券</button></div>' +
      renderTable(_coupons);
    bindEvents();
    var table = root.querySelector('.adx-table');
    if (table && window.AdminTableSort) window.AdminTableSort.bind(table);
  }

  function openCouponModal(coupon) {
    var isEdit = !!(coupon && coupon.id);
    var title = isEdit ? '編輯優惠券' : '建立優惠券';
    var sub = isEdit
      ? '修改折扣規則與有效期限。留空到期日＝不限期。'
      : '可自訂優惠碼，或產生隨機碼。留空到期日＝不限期。';
    var codeVal = isEdit ? esc(coupon.code || '') : '';
    var labelVal = isEdit ? esc(coupon.label || '') : '';
    var discountType = isEdit ? (coupon.discount_type || 'percent') : 'percent';
    var discountValue = isEdit && coupon.discount_value != null ? String(Math.round(Number(coupon.discount_value))) : '';
    var minOrder = isEdit && coupon.min_order_amount != null ? String(Math.round(Number(coupon.min_order_amount))) : '';
    var maxUses = isEdit && coupon.max_uses != null ? String(coupon.max_uses) : '';
    var maxPerUser = isEdit && coupon.max_uses_per_user != null ? String(coupon.max_uses_per_user) : '';
    var startsAt = isEdit ? toDateInput(coupon.starts_at) : '';
    var expiresAt = isEdit ? toDateInput(coupon.expires_at) : '';
    var isActive = isEdit ? !!coupon.is_active : true;

    var foreverOn = !(startsAt || expiresAt);

    var html =
      '<div class="qr-modal ai-modal" role="dialog" aria-modal="true">' +
        '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
        '<h3>' + title + '</h3>' +
        '<p class="qr-modal-sub">' + sub + '</p>' +
        '<p class="ap-form-error" id="acFormError" hidden></p>' +
        '<form id="acCouponForm" class="ap-form" data-mode="' + (isEdit ? 'edit' : 'create') + '"' +
          (isEdit ? ' data-id="' + esc(coupon.id) + '"' : '') + '>' +
          '<div class="ap-form-grid">' +
            '<label class="ap-field ap-field--full">' +
              '<span>優惠碼</span>' +
              '<div class="ac-code-row">' +
                '<input type="text" name="code" id="acCodeInput" maxlength="32" placeholder="例如 SAVE10" autocomplete="off" value="' + codeVal + '">' +
                (isEdit ? '' : '<button type="button" class="btn-sm" id="acGenCode">產生隨機碼</button>') +
              '</div>' +
            '</label>' +
            '<label class="ap-field">' +
              '<span>備註名稱</span>' +
              '<input type="text" name="label" placeholder="內部備註（選填）" value="' + labelVal + '">' +
            '</label>' +
            '<label class="ap-field">' +
              '<span>折扣類型</span>' +
              '<select name="discountType" id="acDiscountType">' +
                '<option value="percent"' + (discountType === 'percent' ? ' selected' : '') + '>百分比 (%)</option>' +
                '<option value="fixed"' + (discountType === 'fixed' ? ' selected' : '') + '>固定金額 (TWD)</option>' +
              '</select>' +
            '</label>' +
            '<label class="ap-field">' +
              '<span id="acValueLabel">' + (discountType === 'fixed' ? '折扣金額 (NT$)' : '折扣數值 (%)') + '</span>' +
              '<input type="number" name="discountValue" min="1" step="1" required placeholder="10" value="' + esc(discountValue) + '">' +
            '</label>' +
            '<label class="ap-field">' +
              '<span>最低消費 (NT$)</span>' +
              '<input type="number" name="minOrderAmount" min="0" step="1" placeholder="不限" value="' + esc(minOrder) + '">' +
            '</label>' +
            '<label class="ap-field">' +
              '<span>總使用上限</span>' +
              '<input type="number" name="maxUses" min="1" step="1" placeholder="不限" value="' + esc(maxUses) + '">' +
            '</label>' +
            '<label class="ap-field">' +
              '<span>每人上限</span>' +
              '<input type="number" name="maxUsesPerUser" min="1" step="1" placeholder="不限" value="' + esc(maxPerUser) + '">' +
            '</label>' +
            '<div class="ap-switch-wrap">' +
              '<label class="ap-switch">' +
                '<input type="checkbox" class="ap-switch-input" id="acForeverSwitch"' + (foreverOn ? ' checked' : '') + '>' +
                '<span class="ap-switch-track" aria-hidden="true"><span class="ap-switch-thumb"></span></span>' +
                '<span class="ap-switch-label">不限期</span>' +
              '</label>' +
            '</div>' +
            '<label class="ap-field" id="acStartsField">' +
              '<span>開始日</span>' +
              '<input type="date" name="startsAt" id="acStartsAt" value="' + esc(foreverOn ? '' : startsAt) + '"' + (foreverOn ? ' disabled' : '') + '>' +
            '</label>' +
            '<label class="ap-field" id="acExpiresField">' +
              '<span>到期日</span>' +
              '<input type="date" name="expiresAt" id="acExpiresAt" value="' + esc(foreverOn ? '' : expiresAt) + '"' + (foreverOn ? ' disabled' : '') + '>' +
            '</label>' +
            '<label class="ap-field ap-field--check">' +
              '<input type="checkbox" name="isActive"' + (isActive ? ' checked' : '') + '>' +
              '<span>' + (isEdit ? '啟用中' : '立即啟用') + '</span>' +
            '</label>' +
          '</div>' +
          '<div class="ap-form-actions">' +
            '<button type="button" class="btn-sm" data-modal-close>取消</button>' +
            '<button type="submit" class="btn-sm btn-primary" id="acSubmitBtn">' + (isEdit ? '儲存' : '建立') + '</button>' +
          '</div>' +
        '</form>' +
      '</div>';

    if (!window.AdminPanel || !window.AdminPanel.openModal) return;
    window.AdminPanel.openModal(html);
    bindModalHelpers();
  }

  function applyForeverState(on) {
    var starts = document.getElementById('acStartsAt');
    var expires = document.getElementById('acExpiresAt');
    var startsField = document.getElementById('acStartsField');
    var expiresField = document.getElementById('acExpiresField');
    if (on) {
      if (starts) { starts.value = ''; starts.disabled = true; }
      if (expires) { expires.value = ''; expires.disabled = true; }
    } else {
      if (starts) starts.disabled = false;
      if (expires) expires.disabled = false;
    }
    if (startsField) startsField.classList.toggle('is-disabled', !!on);
    if (expiresField) expiresField.classList.toggle('is-disabled', !!on);
  }

  function bindModalHelpers() {
    var typeEl = document.getElementById('acDiscountType');
    var valueLabel = document.getElementById('acValueLabel');
    function syncValueLabel() {
      if (!valueLabel || !typeEl) return;
      valueLabel.textContent = typeEl.value === 'fixed' ? '折扣金額 (NT$)' : '折扣數值 (%)';
    }
    if (typeEl) typeEl.addEventListener('change', syncValueLabel);

    var genBtn = document.getElementById('acGenCode');
    var codeInput = document.getElementById('acCodeInput');
    if (genBtn && codeInput) {
      genBtn.addEventListener('click', function () {
        var alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
        var out = '';
        for (var i = 0; i < 8; i++) {
          out += alphabet.charAt(Math.floor(Math.random() * alphabet.length));
        }
        codeInput.value = out;
      });
    }

    var foreverSwitch = document.getElementById('acForeverSwitch');
    if (foreverSwitch) {
      foreverSwitch.addEventListener('change', function () {
        applyForeverState(foreverSwitch.checked);
      });
      applyForeverState(foreverSwitch.checked);
    }

    var form = document.getElementById('acCouponForm');
    if (form) form.addEventListener('submit', submitCouponForm);
  }

  function submitCouponForm(e) {
    e.preventDefault();
    var form = e.target;
    var fd = new FormData(form);
    var errEl = document.getElementById('acFormError');
    var btn = document.getElementById('acSubmitBtn');
    var isEdit = form.dataset.mode === 'edit';
    var code = String(fd.get('code') || '').trim();

    var foreverSwitch = document.getElementById('acForeverSwitch');
    var foreverOn = !!(foreverSwitch && foreverSwitch.checked);

    var payload = {
      code: code || undefined,
      generate: !isEdit && !code,
      label: String(fd.get('label') || '').trim() || undefined,
      discountType: String(fd.get('discountType') || 'percent'),
      discountValue: fd.get('discountValue'),
      minOrderAmount: fd.get('minOrderAmount') === '' ? null : fd.get('minOrderAmount'),
      maxUses: fd.get('maxUses') === '' ? null : fd.get('maxUses'),
      maxUsesPerUser: fd.get('maxUsesPerUser') === '' ? null : fd.get('maxUsesPerUser'),
      startsAt: foreverOn ? null : (fd.get('startsAt') === '' || fd.get('startsAt') == null ? null : fd.get('startsAt')),
      expiresAt: foreverOn ? null : (fd.get('expiresAt') === '' || fd.get('expiresAt') == null ? null : fd.get('expiresAt')),
      isActive: !!form.querySelector('[name="isActive"]') && form.querySelector('[name="isActive"]').checked,
    };
    if (isEdit) payload.id = form.dataset.id;

    if (btn) {
      btn.disabled = true;
      btn.textContent = isEdit ? '儲存中…' : '建立中…';
    }
    if (errEl) errEl.hidden = true;

    var req = isEdit
      ? api.admin.updateCoupon(payload)
      : api.admin.createCoupon(payload);

    req.then(function (res) {
      if (btn) {
        btn.disabled = false;
        btn.textContent = isEdit ? '儲存' : '建立';
      }
      if (res.error) {
        if (errEl) {
          errEl.textContent = typeof res.error === 'string' ? res.error : (res.error.message || '操作失敗');
          errEl.hidden = false;
        } else {
          alert(res.error);
        }
        return;
      }
      if (window.AdminPanel.closeModal) window.AdminPanel.closeModal();
      if (!isEdit && res.coupon && res.coupon.code) copyCode(res.coupon.code);
      load(true, true);
    });
  }

  function copyCode(code) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(code).then(function () {
        alert('已複製優惠碼：' + code);
      }).catch(function () {
        prompt('請手動複製優惠碼：', code);
      });
    } else {
      prompt('請手動複製優惠碼：', code);
    }
  }

  function bindEvents() {
    var createBtn = document.getElementById('btnCreateCoupon');
    if (createBtn) createBtn.addEventListener('click', function () { openCouponModal(null); });

    root.querySelectorAll('[data-action]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var action = btn.dataset.action;
        if (action === 'copy') {
          copyCode(btn.dataset.code);
          return;
        }
        if (action === 'edit') {
          var coupon = findCoupon(btn.dataset.id);
          if (!coupon) {
            alert('找不到此優惠券，請重新整理');
            return;
          }
          openCouponModal(coupon);
          return;
        }
        var id = btn.dataset.id;
        if (!id) return;
        if (action === 'delete' && !confirm('確定刪除此優惠券？已使用紀錄仍保留於訂單。')) return;
        if (action === 'deactivate' && !confirm('確定停用此優惠券？')) return;

        var row = btn.closest('tr');
        btn.disabled = true;
        api.admin.couponAction(id, action).then(function (res) {
          btn.disabled = false;
          if (res.error) {
            alert('操作失敗：' + (res.error.message || res.error));
            return;
          }
          if (action === 'delete' && row) {
            row.remove();
            _coupons = _coupons.filter(function (c) { return String(c.id) !== String(id); });
            if (!root.querySelector('.adx-table tbody tr')) {
              var card = root.querySelector('.adx-table-card');
              if (card) {
                card.outerHTML = '<p class="adx-table-empty">尚無優惠券。點「建立優惠券」新增折扣碼。</p>';
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
    if (!api.admin.getCoupons) {
      root.innerHTML = '<p class="note warn">載入失敗：請重新整理頁面（API 方法缺失）</p>';
      return;
    }
    if (!silent) {
      root.innerHTML = window.SkeletonUI && window.SkeletonUI.invitesShell
        ? window.SkeletonUI.invitesShell()
        : '<p class="adx-loading-inline">載入優惠券中…</p>';
    }
    api.admin.getCoupons().then(function (res) {
      if (res.error) {
        root.innerHTML = '<p class="note warn">載入失敗：' + esc(res.error) + '</p>';
        return;
      }
      _loaded = true;
      root.removeAttribute('aria-busy');
      renderShell(res.coupons || []);
    }).catch(function (err) {
      root.innerHTML = '<p class="note warn">載入失敗：' + esc(err && err.message ? err.message : err) + '</p>';
    });
  }

  function ensureLoaded() {
    load(_loaded);
  }

  window.AdminCouponsPanel = { load: load, ensureLoaded: ensureLoaded };

  document.querySelectorAll('.side-nav button[data-panel="coupons"]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      ensureLoaded();
    });
  });

  if (root && window.SkeletonUI && !_loaded && root.querySelector('.skel-line')) {
    root.innerHTML = window.SkeletonUI.invitesShell
      ? window.SkeletonUI.invitesShell()
      : root.innerHTML;
  }

  var panel = document.getElementById('panel-coupons');
  if (panel && panel.classList.contains('is-active')) {
    ensureLoaded();
  }
})();
