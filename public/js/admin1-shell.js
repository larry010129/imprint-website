/**
 * admin1 shell chrome — sidebar, theme, session, notify, search, KPI.
 * Keeps #adminLayout / #navToggle / #sideBackdrop / data-panel contract.
 */
(function () {
  'use strict';

  var BP = 961;
  var STORAGE_THEME = 'admin1-theme';
  var STORAGE_MENU = 'admin1-menu-state';
  var LOGIN_NEXT = '/login?next=/admin';
  var PENDING_ORDER = {
    received: 1, order_confirming: 1, dna_lab: 1, deposit_confirmed: 1
  };
  var SEARCH_MIN = 2;
  var NOTIFY_LIMIT = 8;

  var layout = document.getElementById('adminLayout');
  var side = document.getElementById('adminSide');
  var toggle = document.getElementById('navToggle');
  var backdrop = document.getElementById('sideBackdrop');
  if (!layout) return;

  var menuState = 'full';
  var prevDesktop = 'full';
  var hoverExpand = false;
  var searchSeq = 0;

  function api() {
    return window.imprintAPI || null;
  }

  function isDesktop() {
    return window.matchMedia('(min-width: ' + BP + 'px)').matches;
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text == null ? '' : String(text);
  }

  function formatCurrency(n) {
    var num = Number(n);
    if (!isFinite(num)) return '—';
    return 'NT$ ' + Math.round(num).toLocaleString('en-US');
  }

  function relativeTime(iso) {
    if (!iso) return '';
    var t = new Date(iso).getTime();
    if (isNaN(t)) return '';
    var diff = Math.max(0, Date.now() - t);
    var min = Math.floor(diff / 60000);
    if (min < 1) return '剛剛';
    if (min < 60) return min + ' 分鐘前';
    var hr = Math.floor(min / 60);
    if (hr < 24) return hr + ' 小時前';
    if (hr < 48) return '昨天';
    return Math.floor(hr / 24) + ' 天前';
  }

  function sessionName(res) {
    var profile = res && res.profile;
    var name = profile && (profile.full_name || profile.fullName);
    if (name && String(name).trim()) return String(name).trim();
    var email = res && res.user && res.user.email;
    return email ? String(email).split('@')[0] : '管理員';
  }

  function sessionInitial(name) {
    var s = String(name || '管').trim();
    return s ? s.charAt(0) : '管';
  }

  function switchPanel(panel) {
    if (!panel) return;
    var btn = document.querySelector('.side-nav button[data-panel="' + panel + '"]');
    if (btn) {
      btn.click();
      return;
    }
    if (!/^\/admin\/?$/i.test(location.pathname)) {
      location.href = panel === 'dash' ? '/admin' : '/admin/' + panel;
    }
  }

  /* ---- Menu state ---- */
  function applyMenuState() {
    layout.setAttribute('data-menu-state', menuState);
    layout.classList.toggle('is-menu-collapsed', menuState === 'collapsed');
    layout.classList.toggle('is-menu-hidden', menuState === 'hidden');
    layout.classList.toggle('is-menu-hover', hoverExpand && menuState === 'collapsed' && isDesktop());
    try {
      if (isDesktop() && menuState !== 'hidden') {
        localStorage.setItem(STORAGE_MENU, menuState);
      }
    } catch (e) { /* ignore */ }
    if (toggle) {
      var open = layout.classList.contains('is-nav-open');
      var menuLabels = { full: '展開', collapsed: '收合', hidden: '隱藏' };
      var menuLabel = menuLabels[menuState] || menuState;
      if (isDesktop()) {
        toggle.setAttribute('aria-expanded', menuState !== 'hidden' ? 'true' : 'false');
        toggle.setAttribute('aria-label', '切換側欄狀態（目前：' + menuLabel + '）');
        toggle.setAttribute('title', '側欄：' + menuLabel);
      } else {
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        toggle.setAttribute('aria-label', open ? '關閉導覽' : '開啟導覽');
        toggle.setAttribute('title', '選單');
      }
    }
  }

  function setMobileOpen(open) {
    layout.classList.toggle('is-nav-open', open);
    document.body.classList.toggle('is-admin-nav-open', open);
    applyMenuState();
  }

  function cycleMenuState() {
    if (menuState === 'full') menuState = 'collapsed';
    else if (menuState === 'collapsed') menuState = 'hidden';
    else menuState = 'full';
    hoverExpand = false;
    if (menuState !== 'hidden') prevDesktop = menuState;
    applyMenuState();
  }

  function setMenuState(state) {
    if (state !== 'full' && state !== 'collapsed' && state !== 'hidden') return;
    menuState = state;
    hoverExpand = false;
    if (state !== 'hidden') prevDesktop = state;
    applyMenuState();
  }

  /* ---- Theme ---- */
  function applyTheme(mode) {
    var dark = mode === 'dark';
    document.documentElement.classList.toggle('dark', dark);
    document.body.classList.toggle('dark', dark);
    try { localStorage.setItem(STORAGE_THEME, dark ? 'dark' : 'light'); } catch (e) { /* ignore */ }
    document.querySelectorAll('[data-admin1-theme-icon]').forEach(function (el) {
      el.hidden = (el.getAttribute('data-admin1-theme-icon') === 'sun') ? dark : !dark;
    });
  }

  function initTheme() {
    var saved = null;
    try { saved = localStorage.getItem(STORAGE_THEME); } catch (e) { /* ignore */ }
    if (saved === 'dark' || saved === 'light') applyTheme(saved);
    else applyTheme(document.documentElement.classList.contains('dark') ? 'dark' : 'light');
  }

  /* ---- Dropdowns ---- */
  function closeDropdowns(except) {
    document.querySelectorAll('.admin1-dropdown.is-open').forEach(function (el) {
      if (el !== except) el.classList.remove('is-open');
    });
  }

  function bindDropdown(wrap) {
    if (!wrap) return;
    var btn = wrap.querySelector('[data-admin1-dropdown-btn]');
    if (!btn) return;
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = !wrap.classList.contains('is-open');
      closeDropdowns(wrap);
      wrap.classList.toggle('is-open', open);
    });
  }

  /* The sidebar is never filtered by the top search: every item stays visible. */

  /* ---- Session / avatar ---- */
  function applySession(res) {
    if (!res || !res.user) return null;
    var name = sessionName(res);
    var email = res.user.email || '';
    var initial = sessionInitial(name);
    setText('admin1AvatarInitial', initial);
    setText('admin1AvatarName', name);
    setText('admin1AvatarEmail', email);
    document.querySelectorAll('.admin1-avatar').forEach(function (el) {
      if (el.id !== 'admin1AvatarInitial') el.textContent = initial;
    });
    var topMeta = document.getElementById('topMeta');
    if (topMeta && !topMeta.getAttribute('data-admin1-meta-static')) {
      topMeta.textContent = email || name;
    }
    return { name: name, email: email, user: res.user, profile: res.profile || null };
  }

  function loadSession() {
    var a = api();
    if (!a || typeof a.getSession !== 'function') return Promise.resolve(null);
    return a.getSession().then(function (res) {
      if (!res || !res.user) return null;
      return applySession(res);
    }).catch(function () { return null; });
  }

  function bindSignOut() {
    var btn = document.getElementById('admin1SignOut');
    if (!btn) return;
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var a = api();
      var go = function () { window.location.href = LOGIN_NEXT; };
      if (a && typeof a.logout === 'function') {
        a.logout().finally(go);
        return;
      }
      go();
    });
  }

  /* ---- Notifications ---- */
  function isPendingOrder(o) {
    return !!(o && PENDING_ORDER[o.status]);
  }

  function isPendingLead(item) {
    if (!item) return false;
    if (item.type === 'message') return item.status === 'new';
    if (item.type === 'quote') return item.status === 'pending';
    return false;
  }

  function notifyItemsFromPayload(ordersRes, leadsRes) {
    var items = [];
    var orders = (ordersRes && ordersRes.orders) || (Array.isArray(ordersRes) ? ordersRes : []) || [];
    orders.forEach(function (o) {
      if (!isPendingOrder(o)) return;
      var num = o.order_number || o.id || '';
      var who = o.customer_name || '客戶';
      items.push({
        panel: 'orders',
        title: '待處理訂單 ' + num,
        sub: who + (o.created_at ? ' · ' + relativeTime(o.created_at) : ''),
        at: o.created_at || ''
      });
    });
    var messages = (leadsRes && leadsRes.messages) || [];
    var quotes = (leadsRes && leadsRes.quotes) || [];
    messages.forEach(function (m) {
      var item = { type: 'message', status: m.status, name: m.name, created_at: m.created_at };
      if (!isPendingLead(item)) return;
      items.push({
        panel: 'leads',
        title: '新留言・' + (m.name || '訪客'),
        sub: relativeTime(m.created_at) || '諮詢名單',
        at: m.created_at || ''
      });
    });
    quotes.forEach(function (q) {
      var item = { type: 'quote', status: q.status, name: q.name, created_at: q.created_at };
      if (!isPendingLead(item)) return;
      items.push({
        panel: 'leads',
        title: '待估價・' + (q.name || '訪客'),
        sub: relativeTime(q.created_at) || '諮詢名單',
        at: q.created_at || ''
      });
    });
    items.sort(function (a, b) {
      return new Date(b.at || 0) - new Date(a.at || 0);
    });
    return items;
  }

  function renderNotify(items) {
    var list = document.getElementById('admin1NotifyList');
    var badge = document.getElementById('admin1NotifyBadge');
    var btn = document.getElementById('admin1NotifyBtn');
    if (!list) return;
    var count = items.length;
    if (badge) {
      badge.textContent = count > 99 ? '99+' : String(count);
      badge.hidden = count === 0;
    }
    if (btn) {
      btn.setAttribute('aria-label', count ? ('通知（' + count + '）') : '通知');
    }
    if (!count) {
      list.innerHTML = '<div class="admin1-notify-empty">尚無新通知</div>';
      return;
    }
    list.innerHTML = items.slice(0, NOTIFY_LIMIT).map(function (it) {
      return (
        '<button type="button" class="admin1-notify-row" data-panel="' + esc(it.panel) + '">' +
          esc(it.title) +
          '<small>' + esc(it.sub) + '</small>' +
        '</button>'
      );
    }).join('');
    list.querySelectorAll('[data-panel]').forEach(function (el) {
      el.addEventListener('click', function () {
        closeDropdowns();
        switchPanel(el.getAttribute('data-panel'));
      });
    });
  }

  function loadNotifications() {
    var a = api();
    if (!a || !a.admin) return Promise.resolve();
    var ordersP = typeof a.admin.getOrders === 'function'
      ? a.admin.getOrders()
      : Promise.resolve({ orders: [] });
    var leadsP = typeof a.admin.getLeads === 'function'
      ? a.admin.getLeads()
      : Promise.resolve({ messages: [], quotes: [] });
    return Promise.all([ordersP, leadsP]).then(function (pair) {
      var ordersRes = pair[0] || {};
      var leadsRes = pair[1] || {};
      if (ordersRes.error || leadsRes.error) {
        renderNotify([]);
        return;
      }
      renderNotify(notifyItemsFromPayload(ordersRes, leadsRes));
    }).catch(function () {
      renderNotify([]);
    });
  }

  /* ---- Global search ---- */
  function hideSearchResults() {
    var box = document.getElementById('admin1SearchResults');
    var wrap = document.getElementById('admin1SearchWrap');
    if (box) {
      box.hidden = true;
      box.innerHTML = '';
    }
    if (wrap) wrap.classList.remove('is-search-open');
  }

  function matchText(hay, q) {
    return String(hay || '').toLowerCase().indexOf(q) !== -1;
  }

  var SEARCH_HITS_PER_TYPE = 6;

  /* A panel loads its data itself; hand it the search first, then show the panel. */
  function openPanelWithSearch(panel, handlerName, query) {
    var owner = { orders: window.AdminOrdersPanel, products: window.AdminProductsPanel }[panel];
    if (owner && typeof owner[handlerName] === 'function') owner[handlerName](query);
    switchPanel(panel);
  }

  /* The server does the matching (whole database, not just the first page), so these
     only turn its rows into clickable hits. */
  function hitsFromOrders(res) {
    var orders = (res && (res.orders || (Array.isArray(res) ? res : []))) || [];
    return orders.slice(0, SEARCH_HITS_PER_TYPE).map(function (o) {
      var number = o.order_number || String(o.id || '');
      return {
        type: '訂單',
        label: number,
        sub: o.customer_name || '',
        open: function () { openPanelWithSearch('orders', 'searchFor', number); }
      };
    });
  }

  function hitsFromProducts(res) {
    var products = (res && (res.products || (Array.isArray(res) ? res : []))) || [];
    return products.slice(0, SEARCH_HITS_PER_TYPE).map(function (p) {
      var key = p.custom_id || p.name_zh || p.name_en || String(p.id || '');
      return {
        type: '商品',
        label: p.name_zh || p.name_en || p.custom_id || String(p.id || ''),
        sub: [p.custom_id, p.category].filter(Boolean).join(' · '),
        open: function () { openPanelWithSearch('products', 'searchFor', key); }
      };
    });
  }

  function hitsFromAccounts(accounts) {
    return (accounts || []).slice(0, SEARCH_HITS_PER_TYPE).map(function (acc) {
      return {
        type: '會員',
        label: acc.full_name || acc.email || String(acc.id || ''),
        sub: acc.email || '',
        open: function () {
          var members = window.AdminMemberSearchPanel;
          if (members && members.openAccountDetail) members.openAccountDetail(acc.id);
          else switchPanel('accounts');
        }
      };
    });
  }

  /* 諮詢名單 returns the latest 50 messages and 50 quote requests; match those here. */
  function hitsFromLeads(res, needle) {
    var out = [];
    ((res && res.messages) || []).forEach(function (m) {
      if (matchText([m.name, m.phone, m.email, m.message, m.source_page].join(' '), needle)) {
        out.push({ type: '諮詢', label: m.name || m.email || '留言', sub: m.phone || m.email || '' });
      }
    });
    ((res && res.quotes) || []).forEach(function (r) {
      if (matchText([r.name, r.phone, r.email, r.series, r.product_type].join(' '), needle)) {
        out.push({ type: '估價', label: r.name || r.email || '估價', sub: [r.series, r.product_type].filter(Boolean).join(' · ') });
      }
    });
    return out.slice(0, SEARCH_HITS_PER_TYPE).map(function (hit) {
      hit.open = function () { switchPanel('leads'); };
      return hit;
    });
  }

  function renderSearchResults(rows) {
    var box = document.getElementById('admin1SearchResults');
    var wrap = document.getElementById('admin1SearchWrap');
    if (!box) return;
    if (!rows.length) {
      box.innerHTML = '<div class="admin1-search-empty">找不到符合結果</div>';
      box.hidden = false;
      if (wrap) wrap.classList.add('is-search-open');
      return;
    }
    box.innerHTML = rows.map(function (r, index) {
      return (
        '<button type="button" class="admin1-search-hit" role="option" data-hit="' + index + '">' +
          '<span class="admin1-search-chip">' + esc(r.type) + '</span>' +
          '<span class="admin1-search-hit-text">' +
            '<strong>' + esc(r.label) + '</strong>' +
            (r.sub ? '<small>' + esc(r.sub) + '</small>' : '') +
          '</span>' +
        '</button>'
      );
    }).join('');
    box.hidden = false;
    if (wrap) wrap.classList.add('is-search-open');
    box.querySelectorAll('[data-hit]').forEach(function (el) {
      el.addEventListener('click', function () {
        var hit = rows[Number(el.getAttribute('data-hit'))];
        hideSearchResults();
        if (hit && typeof hit.open === 'function') hit.open();
      });
    });
  }

  function showSearchMessage(text) {
    var box = document.getElementById('admin1SearchResults');
    var wrap = document.getElementById('admin1SearchWrap');
    if (!box) return;
    box.innerHTML = '<div class="admin1-search-empty">' + esc(text) + '</div>';
    box.hidden = false;
    if (wrap) wrap.classList.add('is-search-open');
  }

  function runGlobalSearch(q) {
    var a = api();
    if (!a || !a.admin) {
      hideSearchResults();
      return;
    }
    /* A full 12-digit card number whose check digit is wrong is a typo: say so. */
    var digits = q.replace(/[\s-]/g, '');
    var memberId = window.ImprintMemberId;
    if (/^\d{12}$/.test(digits) && memberId && memberId.isValidMemberNumber && !memberId.isValidMemberNumber(digits)) {
      ++searchSeq;
      showSearchMessage('這組卡面編號的檢查碼不正確，可能輸入錯誤，請再確認一次。');
      return;
    }
    var seq = ++searchSeq;
    var needle = q.toLowerCase();
    var members = window.AdminMemberSearchPanel;
    /* Everything is asked of the server with the search text, so any page of any list is found. */
    var ordersP = a.admin.getOrders({ q: q, pageSize: SEARCH_HITS_PER_TYPE });
    var productsP = a.admin.getProducts({ q: q, pageSize: SEARCH_HITS_PER_TYPE });
    var leadsP = a.admin.getLeads();
    var accountsP = (members && members.lookup)
      ? members.lookup(q).then(function (accounts) { return { accounts: accounts }; }, function (err) { return { error: err || true }; })
      : a.admin.getAccounts({ q: q, pageSize: SEARCH_HITS_PER_TYPE });
    Promise.all([ordersP, accountsP, productsP, leadsP]).then(function (all) {
      if (seq !== searchSeq) return;
      var ordersRes = all[0] || {};
      var accountsRes = all[1] || {};
      var productsRes = all[2] || {};
      var leadsRes = all[3] || {};
      if (ordersRes.error && accountsRes.error && productsRes.error && leadsRes.error) {
        hideSearchResults();
        return;
      }
      var accounts = accountsRes.accounts || accountsRes.users || (Array.isArray(accountsRes) ? accountsRes : []);
      var rows = []
        .concat(hitsFromOrders(ordersRes))
        .concat(hitsFromAccounts(accounts))
        .concat(hitsFromProducts(productsRes))
        .concat(hitsFromLeads(leadsRes, needle));
      renderSearchResults(rows);
    }).catch(function () {
      if (seq !== searchSeq) return;
      hideSearchResults();
    });
  }

  function bindSearch() {
    var input = document.getElementById('admin1Search');
    if (!input) return;
    /* The search runs on button click / Enter only, so it never interrupts
       typing, and it never touches the sidebar. */
    var submit = function () {
      var q = (input.value || '').trim();
      if (q.length < SEARCH_MIN) {
        hideSearchResults();
        return;
      }
      runGlobalSearch(q);
    };
    input.addEventListener('input', function () {
      var q = (input.value || '').trim();
      if (q.length < SEARCH_MIN) hideSearchResults();
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') hideSearchResults();
      if (e.key === 'Enter') { e.preventDefault(); submit(); }
    });
    var btn = document.getElementById('admin1SearchBtn');
    if (btn) {
      btn.addEventListener('mousedown', function (e) { e.preventDefault(); });
      btn.addEventListener('click', submit);
    }
    input.addEventListener('blur', function () {
      setTimeout(hideSearchResults, 180);
    });
  }

  /* ---- Nested groups ---- */
  function bindGroups() {
    document.querySelectorAll('.side-nav-group-toggle').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var group = btn.closest('.side-nav-group');
        if (!group) return;
        var open = !group.classList.contains('is-open');
        group.classList.toggle('is-open', open);
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    });
  }

  /* ---- Companion page tabs ---- */
  function bindTabs() {
    var root = document.querySelector('[data-admin1-tabs]');
    if (!root) return;
    var triggers = root.querySelectorAll('[data-tab]');
    var panels = root.querySelectorAll('[data-tab-panel]');
    triggers.forEach(function (t) {
      t.addEventListener('click', function () {
        var id = t.getAttribute('data-tab');
        triggers.forEach(function (x) { x.classList.toggle('is-active', x === t); });
        panels.forEach(function (p) {
          p.classList.toggle('is-active', p.getAttribute('data-tab-panel') === id);
        });
      });
    });
    var hash = (location.hash || '').replace(/^#/, '');
    if (hash) {
      var match = root.querySelector('[data-tab="' + hash + '"]');
      if (match) match.click();
    }
  }

  /* ---- Nav toggle ---- */
  function bindNavToggle() {
    if (!toggle) return;
    toggle.addEventListener('click', function () {
      if (isDesktop()) {
        cycleMenuState();
        return;
      }
      setMobileOpen(!layout.classList.contains('is-nav-open'));
    });
    if (backdrop) {
      backdrop.addEventListener('click', function () { setMobileOpen(false); });
    }
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        closeDropdowns();
        hideSearchResults();
        if (!isDesktop()) setMobileOpen(false);
      }
    });
    document.querySelectorAll('.side-nav button[data-panel]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (!isDesktop()) setMobileOpen(false);
      });
    });
    document.querySelectorAll('.side-nav a.side-nav-link').forEach(function (a) {
      a.addEventListener('click', function () {
        if (!isDesktop()) setMobileOpen(false);
      });
    });
  }

  function bindHoverExpand() {
    if (!side) return;
    side.addEventListener('mouseenter', function () {
      if (isDesktop() && menuState === 'collapsed') {
        hoverExpand = true;
        applyMenuState();
      }
    });
    side.addEventListener('mouseleave', function () {
      if (hoverExpand) {
        hoverExpand = false;
        applyMenuState();
      }
    });
  }

  function bindThemeBtn() {
    var btn = document.getElementById('admin1ThemeToggle');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var dark = document.documentElement.classList.contains('dark');
      applyTheme(dark ? 'light' : 'dark');
    });
  }

  function bindResize() {
    var mq = window.matchMedia('(min-width: ' + BP + 'px)');
    function onChange(e) {
      if (e.matches) {
        setMobileOpen(false);
        if (menuState === 'hidden' && prevDesktop !== 'hidden') {
          menuState = prevDesktop;
        }
      } else {
        if (menuState !== 'hidden') prevDesktop = menuState;
        menuState = 'hidden';
        hoverExpand = false;
        setMobileOpen(false);
      }
      applyMenuState();
    }
    if (mq.addEventListener) mq.addEventListener('change', onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }

  function initMenuFromStorage() {
    var saved = null;
    try { saved = localStorage.getItem(STORAGE_MENU); } catch (e) { /* ignore */ }
    if (isDesktop()) {
      if (saved === 'full' || saved === 'collapsed') menuState = saved;
      else menuState = 'full';
      prevDesktop = menuState === 'hidden' ? 'full' : menuState;
    } else {
      menuState = 'hidden';
    }
    applyMenuState();
  }

  function bootData() {
    loadSession();
    loadNotifications();
  }

  document.addEventListener('click', function () {
    closeDropdowns();
    hideSearchResults();
  });
  document.querySelectorAll('.admin1-dropdown').forEach(function (wrap) {
    wrap.addEventListener('click', function (e) { e.stopPropagation(); });
    bindDropdown(wrap);
  });
  var searchWrap = document.getElementById('admin1SearchWrap');
  if (searchWrap) {
    searchWrap.addEventListener('click', function (e) { e.stopPropagation(); });
  }

  initTheme();
  initMenuFromStorage();
  bindNavToggle();
  bindHoverExpand();
  bindThemeBtn();
  bindSearch();
  bindGroups();
  bindSignOut();
  bindTabs();
  bindResize();
  bootData();

  window.Admin1Shell = {
    setMenuState: setMenuState,
    cycleMenuState: cycleMenuState,
    applyTheme: applyTheme,
    getMenuState: function () { return menuState; },
    loadSession: loadSession,
    applySession: applySession,
    switchPanel: switchPanel,
    refreshNotifications: loadNotifications
  };
})();
