/**
 * admin1 shell chrome — sidebar, theme, session, notify, search, KPI.
 * Keeps #adminLayout / #navToggle / #sideBackdrop / data-panel contract.
 */
(function () {
  'use strict';

  var BP = 961;
  var STORAGE_THEME = 'admin1-theme';
  var STORAGE_MENU = 'admin1-menu-state';
  var LOGIN_NEXT = 'login.html?next=admin1.html';
  var PENDING_ORDER = {
    received: 1, order_confirming: 1, dna_lab: 1, deposit_confirmed: 1
  };
  var SEARCH_DEBOUNCE_MS = 280;
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
  var searchTimer = null;
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
    if (!/admin1\.html/i.test(location.pathname)) {
      location.href = '/admin1.html#' + panel;
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

  /* ---- Side-nav filter (fallback) ---- */
  function filterSideNav(q) {
    var needle = (q || '').trim().toLowerCase();
    document.querySelectorAll('.side-nav-section').forEach(function (sec) {
      var visible = 0;
      sec.querySelectorAll('.side-nav-items > button[data-panel], .side-nav-items > a.side-nav-link, .side-nav-sub button[data-panel]').forEach(function (item) {
        var label = (item.textContent || '').trim().toLowerCase();
        var show = !needle || label.indexOf(needle) !== -1;
        item.style.display = show ? '' : 'none';
        if (show) visible++;
      });
      sec.querySelectorAll('.side-nav-group').forEach(function (group) {
        var sub = group.querySelector('.side-nav-sub');
        var any = sub && Array.prototype.some.call(sub.querySelectorAll('button[data-panel]'), function (b) {
          return b.style.display !== 'none';
        });
        group.style.display = !needle || any ? '' : 'none';
        if (any) visible++;
      });
      sec.style.display = !needle || visible > 0 ? '' : 'none';
    });
  }

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

  function searchOrders(orders, q) {
    var out = [];
    (orders || []).forEach(function (o) {
      var blob = [o.order_number, o.customer_name, o.customer_email, o.customer_phone, o.product_type, o.series].join(' ');
      if (!matchText(blob, q)) return;
      out.push({
        panel: 'orders',
        type: '訂單',
        label: o.order_number || String(o.id || ''),
        sub: o.customer_name || ''
      });
    });
    return out.slice(0, 6);
  }

  function searchAccounts(accounts, q) {
    var out = [];
    (accounts || []).forEach(function (acc) {
      var blob = [acc.full_name, acc.email, acc.phone, acc.store_name, acc.id].join(' ');
      if (!matchText(blob, q)) return;
      out.push({
        panel: 'accounts',
        type: '會員',
        label: acc.full_name || acc.email || acc.id,
        sub: acc.email || ''
      });
    });
    return out.slice(0, 6);
  }

  function searchProducts(payload, q) {
    var products = (payload && payload.products) || (Array.isArray(payload) ? payload : []) || [];
    var out = [];
    products.forEach(function (p) {
      var blob = [p.name_zh, p.name_en, p.sku, p.category, p.id].join(' ');
      if (!matchText(blob, q)) return;
      out.push({
        panel: 'products',
        type: '商品',
        label: p.name_zh || p.name_en || p.sku || p.id,
        sub: p.category || ''
      });
    });
    return out.slice(0, 6);
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
    box.innerHTML = rows.map(function (r) {
      return (
        '<button type="button" class="admin1-search-hit" role="option" data-panel="' + esc(r.panel) + '">' +
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
    box.querySelectorAll('[data-panel]').forEach(function (el) {
      el.addEventListener('click', function () {
        hideSearchResults();
        switchPanel(el.getAttribute('data-panel'));
      });
    });
  }

  function runGlobalSearch(q) {
    var a = api();
    if (!a || !a.admin) {
      filterSideNav(q);
      hideSearchResults();
      return;
    }
    var seq = ++searchSeq;
    var needle = q.toLowerCase();
    var ordersP = a.admin.getOrders();
    var accountsP = a.admin.getAccounts(q);
    var productsP = a.admin.getProducts();
    Promise.all([ordersP, accountsP, productsP]).then(function (triple) {
      if (seq !== searchSeq) return;
      var ordersRes = triple[0] || {};
      var accountsRes = triple[1] || {};
      var productsRes = triple[2] || {};
      if (ordersRes.error && accountsRes.error && productsRes.error) {
        filterSideNav(q);
        hideSearchResults();
        return;
      }
      var orders = ordersRes.orders || (Array.isArray(ordersRes) ? ordersRes : []);
      var accounts = accountsRes.accounts || accountsRes.users || (Array.isArray(accountsRes) ? accountsRes : []);
      var rows = []
        .concat(searchOrders(orders, needle))
        .concat(searchAccounts(accounts, needle))
        .concat(searchProducts(productsRes, needle));
      filterSideNav(q);
      renderSearchResults(rows);
    }).catch(function () {
      if (seq !== searchSeq) return;
      filterSideNav(q);
      hideSearchResults();
    });
  }

  function bindSearch() {
    var input = document.getElementById('admin1Search');
    if (!input) return;
    input.addEventListener('input', function () {
      var q = (input.value || '').trim();
      if (searchTimer) clearTimeout(searchTimer);
      if (q.length < SEARCH_MIN) {
        filterSideNav(q);
        hideSearchResults();
        return;
      }
      searchTimer = setTimeout(function () { runGlobalSearch(q); }, SEARCH_DEBOUNCE_MS);
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') hideSearchResults();
    });
    input.addEventListener('blur', function () {
      setTimeout(hideSearchResults, 180);
    });
  }

  /* ---- KPI strip ---- */
  function kpiCard(label, value, hint, tone) {
    var toneClass = tone ? ' dash-metric-v--' + tone : '';
    return (
      '<article class="dash-metric">' +
        '<div class="dash-metric-top"><p class="dash-metric-k">' + esc(label) + '</p></div>' +
        '<p class="dash-metric-v' + toneClass + '">' + esc(value) + '</p>' +
        (hint ? '<p class="dash-metric-d">' + esc(hint) + '</p>' : '') +
      '</article>'
    );
  }

  function renderKpi(stats) {
    var host = document.getElementById('admin1KpiStrip');
    if (!host || !stats || stats.error) return;
    var pending = (stats.newMessages || 0) + (stats.pendingQuotes || 0) + (stats.activeOrders || 0);
    var orders = stats.periodOrderCount != null ? stats.periodOrderCount : (stats.totalOrders || 0);
    host.innerHTML =
      kpiCard('完成營收', formatCurrency(stats.totalRevenue), '區間已完成訂單', 'mint') +
      kpiCard('訂單總數', String(orders), '區間訂單', '') +
      kpiCard('待處理', String(pending), '留言・估價・進行中', '') +
      kpiCard('已完成', String(stats.completedOrders != null ? stats.completedOrders : '—'), '全部已完成訂單', 'blue');
  }

  function loadKpi() {
    var a = api();
    var host = document.getElementById('admin1KpiStrip');
    if (!host || !a || !a.admin || typeof a.admin.getDashboardStats !== 'function') return Promise.resolve();
    return a.admin.getDashboardStats().then(function (stats) {
      renderKpi(stats);
    }).catch(function () { /* keep empty */ });
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
    loadKpi();
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
    refreshNotifications: loadNotifications,
    refreshKpi: loadKpi
  };
})();
