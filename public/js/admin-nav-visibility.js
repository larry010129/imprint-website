(function () {
  'use strict';

  var ITEMS = [
    ['dash', '儀表板'], ['orders', '訂單管理'], ['products', '商品上架'],
    ['accounts', '帳戶管理'], ['member-search', '搜尋會員'], ['invites', '邀請碼'],
    ['coupons', '優惠券'], ['leads', '諮詢名單'], ['pricing', '價格設定'],
    ['membership', '會員等級'], ['content', '內容與頁面圖片'],
    ['featured-video', '首頁品牌影片'], ['settings', '系統設定'], ['plugins', '插件']
  ];
  var endpoint = '/api/admin/nav-visibility';
  var loaded = false;
  var current = {};

  function allVisible() {
    var result = {};
    ITEMS.forEach(function (item) { result[item[0]] = true; });
    return result;
  }

  function applyVisibility(visibility) {
    var map = visibility || allVisible();
    document.querySelectorAll('.side-nav button[data-panel]').forEach(function (item) {
      var key = item.getAttribute('data-panel');
      item.hidden = map[key] === false;
    });
    document.querySelectorAll('.side-nav a.side-nav-link').forEach(function (item) {
      var href = item.getAttribute('href') || '';
      var key = href === '/admin/settings' ? 'settings' : href === '/admin/plugins' ? 'plugins' : '';
      if (key) item.hidden = map[key] === false;
    });
    document.querySelectorAll('.side-nav-group').forEach(function (group) {
      var children = group.querySelectorAll('.side-nav-sub button[data-panel]');
      var visible = Array.prototype.some.call(children, function (item) { return !item.hidden; });
      group.hidden = !visible;
    });
    document.querySelectorAll('.side-nav-section').forEach(function (section) {
      var items = section.querySelectorAll('.side-nav-items > button, .side-nav-items > a, .side-nav-sub button');
      if (!items.length) return;
      section.hidden = !Array.prototype.some.call(items, function (item) { return !item.hidden; });
    });
  }

  function loadVisibility() {
    return fetch(endpoint, { credentials: 'include' })
      .then(function (res) {
        if (!res.ok) throw new Error('無法載入後台分頁設定');
        return res.json();
      })
      .then(function (data) {
        current = Object.assign(allVisible(), data && data.visibility);
        loaded = true;
        applyVisibility(current);
        return current;
      });
  }

  function saveVisibility(visibility) {
    return fetch(endpoint, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ visibility: visibility })
    }).then(function (res) {
      if (!res.ok) throw new Error('儲存後台分頁設定失敗');
      return res.json();
    }).then(function (data) {
      current = Object.assign(allVisible(), data && data.visibility);
      applyVisibility(current);
      return current;
    });
  }

  function renderSettings(root, visibility) {
    var rows = ITEMS.map(function (item) {
      var key = item[0];
      return '<label class="admin-nav-visibility-row">' +
        '<span><strong>' + item[1] + '</strong><small>' + key + '</small></span>' +
        '<input type="checkbox" data-nav-visibility-key="' + key + '"' +
          (visibility[key] !== false ? ' checked' : '') + '>' +
        '<em data-nav-visibility-state="' + key + '">' +
          (visibility[key] !== false ? '顯示' : '隱藏') + '</em>' +
      '</label>';
    }).join('');
    root.innerHTML =
      '<div class="admin-nav-visibility-panel" data-admin-root="">' +
        '<div class="space-y-1"><h2>後台分頁顯示設定</h2>' +
          '<p>選擇左側管理選單要顯示或隱藏的分頁；設定會套用到所有管理員。</p></div>' +
        '<div class="admin-nav-visibility-list">' + rows + '</div>' +
        '<div class="admin-nav-visibility-actions"><button type="button" class="btn-sm" data-nav-visibility-reset>全部顯示</button>' +
          '<button type="button" class="btn-sm btn-primary" data-nav-visibility-save>儲存設定</button>' +
          '<span role="status" data-nav-visibility-message></span></div>' +
      '</div>';
    root.querySelectorAll('[data-nav-visibility-key]').forEach(function (input) {
      input.addEventListener('change', function () {
        var state = root.querySelector('[data-nav-visibility-state="' + input.getAttribute('data-nav-visibility-key') + '"]');
        if (state) state.textContent = input.checked ? '顯示' : '隱藏';
      });
    });
    root.querySelector('[data-nav-visibility-reset]').addEventListener('click', function () {
      root.querySelectorAll('[data-nav-visibility-key]').forEach(function (input) {
        input.checked = true;
        input.dispatchEvent(new Event('change'));
      });
    });
    root.querySelector('[data-nav-visibility-save]').addEventListener('click', function () {
      var button = root.querySelector('[data-nav-visibility-save]');
      var message = root.querySelector('[data-nav-visibility-message]');
      var next = {};
      root.querySelectorAll('[data-nav-visibility-key]').forEach(function (input) {
        next[input.getAttribute('data-nav-visibility-key')] = input.checked;
      });
      button.disabled = true;
      message.textContent = '儲存中…';
      saveVisibility(next).then(function () {
        message.textContent = '已儲存';
      }).catch(function (error) {
        message.textContent = error.message || '儲存失敗';
      }).finally(function () { button.disabled = false; });
    });
  }

  function bindReleaseNotesTabs() {
    var root = document.querySelector('[data-rn-tab-panel]') && document.getElementById('admin-nav-visibility-root');
    var triggers = document.querySelectorAll('[data-rn-tab]');
    if (!triggers.length) return;
    function activate(id) {
      triggers.forEach(function (trigger) {
        trigger.classList.toggle('is-active', trigger.getAttribute('data-rn-tab') === id);
      });
      document.querySelectorAll('[data-rn-tab-panel]').forEach(function (panel) {
        panel.hidden = panel.getAttribute('data-rn-tab-panel') !== id;
      });
      if (id === 'nav-visibility' && root && !loaded) {
        loadVisibility().then(function (visibility) { renderSettings(root, visibility); })
          .catch(function (error) { root.textContent = error.message || '載入設定失敗'; });
      }
    }
    triggers.forEach(function (trigger) {
      trigger.addEventListener('click', function () { activate(trigger.getAttribute('data-rn-tab')); });
    });
    activate('release-notes');
  }

  if (document.getElementById('admin-nav-visibility-root')) bindReleaseNotesTabs();
  if (document.querySelector('.side-nav button[data-panel]')) loadVisibility().catch(function () {});
})();
