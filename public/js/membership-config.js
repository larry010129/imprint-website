/* Admin 會員等級設定 — table layout like front-page comparison */
(function () {
  'use strict';

  var MEMBER_IDS = ['ice', 'platinum', 'rose', 'star', 'imprint'];
  var PARTNER_IDS = [
    'partner_entry', 'partner_platinum', 'partner_rose', 'partner_star', 'partner_imprint'
  ];

  var state = {
    track: 'member',
    config: null,
    loaded: false
  };

  function api() {
    return window.imprintAPI || null;
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function setMsg(text, ok) {
    var el = document.getElementById('membershipMsg');
    if (!el) return;
    el.textContent = text || '';
    el.className = 'msg' + (ok === true ? ' ok' : ok === false ? ' err' : '');
  }

  function defaultConfig() {
    return {
      enabled: true,
      member: {
        tiers: [
          { id: 'ice', name: '冰藍卡', minOrders: 0, minSpendTwd: 0, minInvites: 0, inviteOnly: false },
          { id: 'platinum', name: '白金卡', minOrders: 1, minSpendTwd: 50000, minInvites: 3, inviteOnly: false },
          { id: 'rose', name: '玫瑰金', minOrders: 2, minSpendTwd: 120000, minInvites: 5, inviteOnly: false },
          { id: 'star', name: '星鑽卡', minOrders: 3, minSpendTwd: 280000, minInvites: 10, inviteOnly: false },
          { id: 'imprint', name: '銘鑽卡', minOrders: 0, minSpendTwd: 0, minInvites: 0, inviteOnly: true }
        ],
        benefitGroups: []
      },
      partner: {
        tiers: [
          { id: 'partner_entry', name: '合作入門', minOrdersPerMonth: 0, minOrdersPerYear: 0, inviteOnly: false },
          { id: 'partner_platinum', name: '合作白金', minOrdersPerMonth: 10, minOrdersPerYear: 120, inviteOnly: false },
          { id: 'partner_rose', name: '合作玫瑰金', minOrdersPerMonth: 30, minOrdersPerYear: 360, inviteOnly: false },
          { id: 'partner_star', name: '合作星鑽', minOrdersPerMonth: 50, minOrdersPerYear: 600, inviteOnly: false },
          { id: 'partner_imprint', name: '合作銘鑽', minOrdersPerMonth: 0, minOrdersPerYear: 0, inviteOnly: true }
        ],
        benefitGroups: []
      }
    };
  }

  function trackBlock() {
    return state.config[state.track];
  }

  function tierIds() {
    return state.track === 'member' ? MEMBER_IDS : PARTNER_IDS;
  }

  function isEnabled() {
    return !state.config || state.config.enabled !== false;
  }

  function benefitMode(v) {
    if (v === true) return 'yes';
    if (v === false || v == null || v === '') return 'no';
    if (typeof v === 'string') {
      var s = v.trim().toLowerCase();
      if (s === 'yes' || s === 'true' || s === '1' || s === 'y' || s === '有') return 'yes';
      if (s === 'no' || s === 'false' || s === '0' || s === 'n' || s === '無') return 'no';
      if (v.trim() === '即將推出') return 'soon';
    }
    return 'custom';
  }

  function benefitRadioCell(gi, fi, vi, value) {
    var mode = benefitMode(value);
    var name = 'ms-val-' + gi + '-' + fi + '-' + vi;
    var customText = mode === 'custom' ? String(value == null ? '' : value) : '';
    function row(val, label) {
      return (
        '<label class="ms-radio-row">' +
          '<input type="radio" name="' + name + '" value="' + val + '"' +
            (mode === val ? ' checked' : '') +
            ' data-ms-radio="1" data-gi="' + gi + '" data-fi="' + fi + '" data-vi="' + vi + '">' +
          '<span>' + label + '</span>' +
        '</label>'
      );
    }
    return (
      '<div class="ms-radio-group" role="radiogroup" aria-label="權益值">' +
        row('yes', '有') +
        row('no', '無') +
        row('soon', '即將推出') +
        row('custom', '自訂') +
        '<input type="text" class="ms-radio-custom" data-ms-custom="1" data-gi="' + gi +
          '" data-fi="' + fi + '" data-vi="' + vi + '" value="' + esc(customText) +
          '" placeholder="自訂文字"' + (mode !== 'custom' ? ' disabled' : '') + '>' +
      '</div>'
    );
  }

  function renderMaster() {
    var root = document.getElementById('membershipMaster');
    if (!root || !state.config) return;
    var on = isEnabled();
    root.innerHTML =
      '<div class="card-head">' +
        '<h2>會員制度總開關</h2>' +
        '<span class="hint">關閉後，前台帳戶／個人頁不顯示等級進度與權益比較（設定仍保留）</span>' +
      '</div>' +
      '<div class="admin-panel-pad" style="display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap">' +
        '<div>' +
          '<strong style="font-size:15px">' + (on ? '已啟用' : '已關閉') + '</strong>' +
          '<p class="note" style="margin:6px 0 0">' +
            (on ? '前台會依門檻計算並顯示會員／合作等級。' : '前台不啟動會員等級制度；儲存後立即生效。') +
          '</p>' +
        '</div>' +
        '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">' +
          '<button type="button" class="btn-sm' + (on ? ' btn-primary' : '') + '" id="btnMembershipOn">開啟制度</button>' +
          '<button type="button" class="btn-sm' + (!on ? ' btn-primary' : '') + '" id="btnMembershipOff">關閉制度</button>' +
        '</div>' +
      '</div>';
    var btnOn = document.getElementById('btnMembershipOn');
    var btnOff = document.getElementById('btnMembershipOff');
    if (btnOn) {
      btnOn.addEventListener('click', function () {
        state.config.enabled = true;
        renderMaster();
      });
    }
    if (btnOff) {
      btnOff.addEventListener('click', function () {
        state.config.enabled = false;
        renderMaster();
      });
    }
  }

  function renderTabs() {
    var root = document.getElementById('membershipTabs');
    if (!root) return;
    root.innerHTML =
      '<button type="button" class="btn-sm' + (state.track === 'member' ? ' btn-primary' : '') + '" data-track="member">一般會員</button> ' +
      '<button type="button" class="btn-sm' + (state.track === 'partner' ? ' btn-primary' : '') + '" data-track="partner">合作廠商</button>';
    root.querySelectorAll('[data-track]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        collectFromDom();
        state.track = btn.getAttribute('data-track');
        render();
      });
    });
  }

  function numInput(field, idx, value, opts) {
    opts = opts || {};
    var dis = opts.disabled ? ' disabled' : '';
    return (
      '<input type="number" min="0" step="1" data-f="' + field + '" data-i="' + idx + '"' +
      ' value="' + esc(value == null ? 0 : value) + '"' + dis +
      ' style="width:100%;min-width:72px;box-sizing:border-box">'
    );
  }

  function textInput(field, idx, value) {
    return (
      '<input type="text" data-f="' + field + '" data-i="' + idx + '"' +
      ' value="' + esc(value || '') + '" style="width:100%;min-width:88px;box-sizing:border-box">'
    );
  }

  function checkInput(field, idx, checked) {
    return (
      '<label style="display:inline-flex;align-items:center;gap:4px;justify-content:center;width:100%">' +
        '<input type="checkbox" data-f="' + field + '" data-i="' + idx + '"' + (checked ? ' checked' : '') + '>' +
        '<span style="font-size:12px">邀請制</span>' +
      '</label>'
    );
  }

  function renderComparisonTable() {
    var root = document.getElementById('membershipTable');
    if (!root || !state.config) return;

    var tiers = trackBlock().tiers || [];
    var groups = trackBlock().benefitGroups || [];
    var isMember = state.track === 'member';
    var colCount = 7; // label + 5 tiers + actions

    var html = '';
    html += '<div class="card" style="margin-top:8px">';
    html += '<div class="card-head"><h2>等級與權益比較表</h2>';
    html += '<span class="hint">欄位對應前台比較表；權益用單選：有／無／即將推出／自訂</span></div>';
    html += '<div class="admin-scroll">';
    html += '<table class="price-edit-table" id="membershipCompareTable" style="min-width:1100px">';

    // Header: tier names
    html += '<thead><tr>';
    html += '<th style="min-width:120px">項目</th>';
    for (var i = 0; i < 5; i++) {
      var t = tiers[i] || { id: tierIds()[i], name: '' };
      html +=
        '<th style="min-width:128px;text-align:center">' +
          '<div style="font-size:11px;color:var(--ink-faint,#888);margin-bottom:4px">' + esc(t.id) + '</div>' +
          textInput('name', i, t.name) +
        '</th>';
    }
    html += '<th style="min-width:96px;white-space:nowrap;text-align:center">操作</th>';
    html += '</tr></thead><tbody>';

    // Threshold section
    html +=
      '<tr style="background:#fafaf8"><td colspan="' + colCount +
      '" style="font-weight:600;padding:10px 12px">達成／維持門檻</td></tr>';

    html += '<tr><td>邀請制</td>';
    for (i = 0; i < 5; i++) {
      html += '<td style="text-align:center">' + checkInput('inviteOnly', i, !!(tiers[i] && tiers[i].inviteOnly)) + '</td>';
    }
    html += '<td></td></tr>';

    if (isMember) {
      html += '<tr><td>訂單筆數（近 2 年）</td>';
      for (i = 0; i < 5; i++) {
        var inv = !!(tiers[i] && tiers[i].inviteOnly);
        html += '<td>' + numInput('minOrders', i, tiers[i] ? tiers[i].minOrders : 0, { disabled: inv }) + '</td>';
      }
      html += '<td></td></tr>';

      html += '<tr><td>消費金額 TWD</td>';
      for (i = 0; i < 5; i++) {
        inv = !!(tiers[i] && tiers[i].inviteOnly);
        html += '<td>' + numInput('minSpendTwd', i, tiers[i] ? tiers[i].minSpendTwd : 0, { disabled: inv }) + '</td>';
      }
      html += '<td></td></tr>';

      html += '<tr><td>維持邀請人數</td>';
      for (i = 0; i < 5; i++) {
        inv = !!(tiers[i] && tiers[i].inviteOnly);
        html += '<td>' + numInput('minInvites', i, tiers[i] ? tiers[i].minInvites : 0, { disabled: inv }) + '</td>';
      }
      html += '<td></td></tr>';
    } else {
      html += '<tr><td>每月訂單筆數</td>';
      for (i = 0; i < 5; i++) {
        inv = !!(tiers[i] && tiers[i].inviteOnly);
        html += '<td>' + numInput('minOrdersPerMonth', i, tiers[i] ? tiers[i].minOrdersPerMonth : 0, { disabled: inv }) + '</td>';
      }
      html += '<td></td></tr>';

      html += '<tr><td>每年訂單筆數</td>';
      for (i = 0; i < 5; i++) {
        inv = !!(tiers[i] && tiers[i].inviteOnly);
        html += '<td>' + numInput('minOrdersPerYear', i, tiers[i] ? tiers[i].minOrdersPerYear : 0, { disabled: inv }) + '</td>';
      }
      html += '<td></td></tr>';
    }

    // Benefits
    if (!groups.length) {
      html +=
        '<tr style="background:#fafaf8"><td colspan="' + colCount +
        '" style="font-weight:600;padding:10px 12px">權益比較</td></tr>';
      html +=
        '<tr><td colspan="' + colCount +
        '" class="note" style="padding:14px">尚無權益列。請按下方「＋ 新增權益區塊」開始編輯。</td></tr>';
    }

    groups.forEach(function (g, gi) {
      html += '<tr style="background:#fafaf8">';
      html +=
        '<td colspan="6" style="padding:8px 12px">' +
          '<label style="display:flex;align-items:center;gap:8px;font-weight:600">' +
            '<span>權益區塊</span>' +
            '<input type="text" data-bg="section" data-gi="' + gi + '" value="' + esc(g.section || '') +
              '" style="flex:1;min-width:160px;font-weight:600">' +
          '</label>' +
        '</td>';
      html +=
        '<td style="text-align:center;white-space:nowrap">' +
          '<button type="button" class="btn-sm" data-rm-group="' + gi + '" title="刪除此權益區塊" style="white-space:nowrap">刪除區塊</button>' +
        '</td></tr>';

      (g.features || []).forEach(function (f, fi) {
        html += '<tr>';
        html +=
          '<td><input type="text" data-bg="label" data-gi="' + gi + '" data-fi="' + fi +
          '" value="' + esc(f.label || '') + '" placeholder="權益名稱" style="width:100%;box-sizing:border-box"></td>';
        for (var vi = 0; vi < 5; vi++) {
          var v = (f.values && f.values[vi] != null) ? f.values[vi] : false;
          html += '<td style="vertical-align:top;padding-top:10px;padding-bottom:10px">' +
            benefitRadioCell(gi, fi, vi, v) + '</td>';
        }
        html +=
          '<td style="text-align:center;white-space:nowrap">' +
            '<button type="button" class="btn-sm" data-rm-feat="' + gi + ':' + fi + '" title="刪除此權益" style="white-space:nowrap">刪除</button>' +
          '</td></tr>';
      });

      html += '<tr>';
      html +=
        '<td colspan="' + colCount + '" style="padding:8px 12px">' +
          '<button type="button" class="btn-sm" data-add-feat="' + gi + '">＋ 新增權益</button>' +
        '</td></tr>';
    });

    html += '</tbody></table></div>';
    html +=
      '<div class="admin-panel-pad" style="display:flex;gap:8px;flex-wrap:wrap">' +
        '<button type="button" class="btn-sm btn-primary" id="btnAddBenefitGroup">＋ 新增權益區塊</button>' +
        '<button type="button" class="btn-sm" id="btnAddBenefitRow">＋ 新增權益（加到最後區塊）</button>' +
      '</div></div>';

    root.innerHTML = html;
    bindTableActions();
  }

  function ensureBenefitGroups() {
    var block = trackBlock();
    if (!Array.isArray(block.benefitGroups)) block.benefitGroups = [];
    return block.benefitGroups;
  }

  function bindTableActions() {
    var root = document.getElementById('membershipTable');
    if (!root) return;

    root.querySelectorAll('[data-f="inviteOnly"]').forEach(function (box) {
      box.addEventListener('change', function () {
        collectFromDom();
        renderComparisonTable();
      });
    });

    root.querySelectorAll('[data-ms-radio]').forEach(function (radio) {
      radio.addEventListener('change', function () {
        var gi = radio.getAttribute('data-gi');
        var fi = radio.getAttribute('data-fi');
        var vi = radio.getAttribute('data-vi');
        var custom = root.querySelector(
          '.ms-radio-custom[data-gi="' + gi + '"][data-fi="' + fi + '"][data-vi="' + vi + '"]'
        );
        if (custom) {
          custom.disabled = radio.value !== 'custom';
          if (radio.value === 'custom') custom.focus();
        }
      });
    });

    var addG = document.getElementById('btnAddBenefitGroup');
    if (addG) {
      addG.addEventListener('click', function () {
        collectFromDom();
        ensureBenefitGroups().push({
          section: '新區塊',
          features: [{ label: '新權益', values: [true, true, true, true, true] }]
        });
        renderComparisonTable();
      });
    }

    var addRow = document.getElementById('btnAddBenefitRow');
    if (addRow) {
      addRow.addEventListener('click', function () {
        collectFromDom();
        var groups = ensureBenefitGroups();
        if (!groups.length) {
          groups.push({
            section: '權益',
            features: [{ label: '新權益', values: [false, false, false, false, false] }]
          });
        } else {
          var last = groups[groups.length - 1];
          if (!Array.isArray(last.features)) last.features = [];
          last.features.push({ label: '新權益', values: [false, false, false, false, false] });
        }
        renderComparisonTable();
      });
    }

    root.querySelectorAll('[data-add-feat]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        collectFromDom();
        var gi = Number(btn.getAttribute('data-add-feat'));
        var groups = ensureBenefitGroups();
        if (!groups[gi]) return;
        if (!Array.isArray(groups[gi].features)) groups[gi].features = [];
        groups[gi].features.push({ label: '新權益', values: [false, false, false, false, false] });
        renderComparisonTable();
      });
    });

    root.querySelectorAll('[data-rm-group]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (!confirm('確定刪除此權益區塊？')) return;
        collectFromDom();
        ensureBenefitGroups().splice(Number(btn.getAttribute('data-rm-group')), 1);
        renderComparisonTable();
      });
    });

    root.querySelectorAll('[data-rm-feat]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        collectFromDom();
        var parts = String(btn.getAttribute('data-rm-feat') || '').split(':');
        var gi = Number(parts[0]);
        var fi = Number(parts[1]);
        var groups = ensureBenefitGroups();
        if (!groups[gi] || !Array.isArray(groups[gi].features)) return;
        groups[gi].features.splice(fi, 1);
        // Drop empty section after last feature deleted
        if (!groups[gi].features.length) {
          groups.splice(gi, 1);
        }
        renderComparisonTable();
      });
    });
  }

  function collectFromDom() {
    if (!state.config) return;
    if (typeof state.config.enabled !== 'boolean') state.config.enabled = true;

    var tiers = trackBlock().tiers || [];
    var table = document.getElementById('membershipTable');
    if (!table) return;

    table.querySelectorAll('[data-f]').forEach(function (inp) {
      var i = Number(inp.getAttribute('data-i'));
      var f = inp.getAttribute('data-f');
      if (!tiers[i]) return;
      if (f === 'inviteOnly') {
        tiers[i].inviteOnly = !!inp.checked;
      } else if (f === 'name') {
        tiers[i].name = inp.value.trim();
      } else if (!inp.disabled) {
        var n = Number(inp.value);
        tiers[i][f] = Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
      }
    });

    // Clear numeric unlock when invite-only
    tiers.forEach(function (t) {
      if (!t.inviteOnly) return;
      if (state.track === 'member') {
        t.minOrders = 0;
        t.minSpendTwd = 0;
        t.minInvites = 0;
      } else {
        t.minOrdersPerMonth = 0;
        t.minOrdersPerYear = 0;
      }
    });

    var groups = ensureBenefitGroups();
    table.querySelectorAll('[data-bg="section"], [data-bg="label"]').forEach(function (inp) {
      var kind = inp.getAttribute('data-bg');
      var gi = Number(inp.getAttribute('data-gi'));
      if (!groups[gi]) return;
      if (kind === 'section') {
        groups[gi].section = inp.value.trim() || '權益';
      } else if (kind === 'label') {
        var fi = Number(inp.getAttribute('data-fi'));
        if (groups[gi].features && groups[gi].features[fi]) {
          groups[gi].features[fi].label = inp.value.trim();
        }
      }
    });

    table.querySelectorAll('.ms-radio-group').forEach(function (groupEl) {
      var checked = groupEl.querySelector('input[type="radio"]:checked');
      if (!checked) return;
      var gi = Number(checked.getAttribute('data-gi'));
      var fi = Number(checked.getAttribute('data-fi'));
      var vi = Number(checked.getAttribute('data-vi'));
      if (!groups[gi] || !groups[gi].features || !groups[gi].features[fi]) return;
      if (!Array.isArray(groups[gi].features[fi].values)) {
        groups[gi].features[fi].values = [false, false, false, false, false];
      }
      var mode = checked.value;
      var out;
      if (mode === 'yes') out = true;
      else if (mode === 'no') out = false;
      else if (mode === 'soon') out = '即將推出';
      else {
        var custom = groupEl.querySelector('.ms-radio-custom');
        out = custom && custom.value.trim() ? custom.value.trim() : '';
        if (!out) out = false;
      }
      groups[gi].features[fi].values[vi] = out;
    });
  }

  function render() {
    renderMaster();
    renderTabs();
    renderComparisonTable();
  }

  function load() {
    var client = api();
    if (!client || !client.getAdminMembershipConfig) {
      setMsg('API 尚未就緒', false);
      return;
    }
    setMsg('載入中…');
    client.getAdminMembershipConfig().then(function (res) {
      if (res && res.error) {
        setMsg(res.error.message || res.error || '載入失敗', false);
        state.config = defaultConfig();
        state.loaded = true;
        render();
        return;
      }
      state.config = (res && res.config) ? res.config : defaultConfig();
      if (typeof state.config.enabled !== 'boolean') state.config.enabled = true;
      state.loaded = true;
      setMsg('');
      render();
    }).catch(function () {
      state.config = defaultConfig();
      state.loaded = true;
      setMsg('載入失敗，顯示預設值', false);
      render();
    });
  }

  function save(reset) {
    collectFromDom();
    var client = api();
    if (!client || !client.saveAdminMembershipConfig) {
      setMsg('API 尚未就緒', false);
      return;
    }
    setMsg('儲存中…');
    var promise = reset
      ? client.resetAdminMembershipConfig()
      : client.saveAdminMembershipConfig(state.config);
    promise.then(function (res) {
      if (res && res.error) {
        setMsg(res.error.message || res.error || '儲存失敗', false);
        return;
      }
      state.config = (res && res.config) ? res.config : state.config;
      setMsg(reset ? '已還原預設值' : '已儲存會員等級設定', true);
      render();
    }).catch(function () {
      setMsg('儲存失敗', false);
    });
  }

  function bindSaveBar() {
    var saveBtn = document.getElementById('btnSaveMembership');
    var resetBtn = document.getElementById('btnResetMembership');
    if (saveBtn) {
      saveBtn.addEventListener('click', function () { save(false); });
    }
    if (resetBtn) {
      resetBtn.addEventListener('click', function () {
        if (!confirm('確定還原成系統預設等級與權益？')) return;
        save(true);
      });
    }
  }

  function init() {
    if (!document.getElementById('panel-membership')) return;
    bindSaveBar();
    load();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.ImprintMembershipConfig = { reload: load, getState: function () { return state; } };
})();
