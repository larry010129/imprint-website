/* 銘印鑽石｜首頁圖片與內容管理 */
(function () {
  'use strict';

  var api = window.imprintAPI;
  if (!api || !api.admin) return;

  var root = document.getElementById('contentRoot');
  if (!root) return;

  var _loadedTabs = {};
  var _tab = 'banners';
  var _pageImagePage = '';
  var _testimonials = [];
  var _journalPosts = [];
  var _journalError = '';
  var _faqItems = [];
  var _faqCategories = [];
  var _faqCategoryId = '';
  var _banners = [];
  var _pageImages = [];
  var _pageImagePageOptions = [];
  var _pageIndex = 0;
  var _pageSize = 10;
  var _totals = {
    banners: 0,
    testimonials: 0,
    faq: 0,
    'page-images': 0,
    journal: 0,
  };

  var PAGE_LINKS = [
    { value: '/', label: '首頁' },
    { value: '/shop/calculator/', label: '客製試算' },
    { value: '/price', label: 'DNA 鑽石價格' },
    { value: '/gold-price', label: '黃金牌價' },
    { value: '/series', label: '系列總覽' },
    { value: '/what-is-dna-diamond', label: 'DNA 鑽石的誕生' },
    { value: '/faq', label: '常見問題' },
    { value: '/about', label: '品牌故事' },
    { value: '/stories', label: '客戶見證' },
    { value: '/contact', label: '聯絡我們' },
    { value: '/track-order', label: '查詢訂製進度' },
    { value: '/jewelry/', label: '飾品訂製' },
    { value: '#home-poem', label: '首頁・詩文區塊' },
    { value: '#series', label: '首頁・系列區塊' },
    { value: 'https://lin.ee/ktVBtmx', label: '官方 LINE' },
  ];

  var TESTIMONIAL_CATEGORIES = [
    '寵物鑽石', '結髮鑽石', '生命鑽石', '毛髮鑽石', '全家福鑽石', '初生鑽石',
  ];

  // Fallback matches ImprintTaiwanAdminDivisions.testimonialCities (台 spelling; zh-Hant-TW).
  var TAIWAN_CITIES_FALLBACK = [
    '台北市', '基隆市', '新北市', '宜蘭縣', '桃園市', '新竹市', '新竹縣', '苗栗縣',
    '台中市', '彰化縣', '南投縣', '嘉義市', '嘉義縣', '雲林縣', '台南市', '高雄市',
    '澎湖縣', '金門縣', '屏東縣', '台東縣', '花蓮縣', '連江縣', '其他',
  ];

  function taiwanCities() {
    var div = window.ImprintTaiwanAdminDivisions;
    var shared = div && (div.testimonialCities || div.cities);
    return shared && shared.length ? shared : TAIWAN_CITIES_FALLBACK;
  }

  /** Map legacy short / 臺 spellings to canonical 縣市; leave ambiguous stems unchanged. */
  function normalizeTaiwanCity(raw) {
    var v = String(raw || '').trim().replace(/臺/g, '台');
    if (!v) return '';
    var cities = taiwanCities();
    if (cities.indexOf(v) >= 0) return v;
    var matches = [];
    for (var i = 0; i < cities.length; i++) {
      var c = cities[i];
      var stem = c.replace(/[市縣]$/, '');
      if (v === stem) matches.push(c);
    }
    return matches.length === 1 ? matches[0] : v;
  }

  function isTaiwanCity(raw) {
    return taiwanCities().indexOf(normalizeTaiwanCity(raw)) >= 0;
  }

  function reqStar() {
    return ' <span class="ap-required" aria-hidden="true">*</span>';
  }

  function splitTestimonialName(t) {
    if (t && t.name_part != null) {
      return { part: t.name_part || '', honorific: t.honorific || '小姐' };
    }
    var full = String((t && t.name) || '').trim();
    if (full.endsWith('先生')) return { part: full.slice(0, -2), honorific: '先生' };
    if (full.endsWith('小姐')) return { part: full.slice(0, -2), honorific: '小姐' };
    return { part: full, honorific: '小姐' };
  }

  function categoryOptions(selected) {
    selected = String(selected || '').trim();
    var html = '<option value="">— 請選擇 —</option>';
    for (var i = 0; i < TESTIMONIAL_CATEGORIES.length; i++) {
      var c = TESTIMONIAL_CATEGORIES[i];
      html += '<option value="' + esc(c) + '"' + (selected === c ? ' selected' : '') + '>' + esc(c) + '</option>';
    }
    if (selected && TESTIMONIAL_CATEGORIES.indexOf(selected) < 0) {
      html += '<option value="' + esc(selected) + '" selected>' + esc(selected) + '</option>';
    }
    return html;
  }

  var COMBO_CHEVRON =
    '<svg class="ap-combo__chevron" viewBox="0 0 24 24" width="16" height="16" ' +
    'aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>';

  var COMBO_CHECK =
    '<svg class="ap-combo__check" viewBox="0 0 24 24" width="16" height="16" ' +
    'aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" ' +
    'stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg>';

  function filterTaiwanCities(query) {
    var q = String(query || '').trim().replace(/臺/g, '台');
    var cities = taiwanCities();
    if (!q) return cities.slice();
    return cities.filter(function (c) {
      var stem = c.replace(/[市縣]$/, '');
      return c.indexOf(q) >= 0 || stem.indexOf(q) >= 0;
    });
  }

  function cityComboMarkup(selected) {
    selected = normalizeTaiwanCity(selected);
    var label = selected || '選擇縣市';
    var ph = selected ? '' : ' is-placeholder';
    return (
      '<div class="ap-field">' +
        '<span id="acCityLabel">城市' + reqStar() + '</span>' +
        '<div class="ap-combo" id="acCityCombo">' +
          '<input type="hidden" name="city" id="acCityValue" value="' + esc(selected) + '">' +
          '<button type="button" class="ap-combo__trigger" id="acCityTrigger" ' +
            'aria-haspopup="listbox" aria-expanded="false" aria-controls="acCityList" ' +
            'aria-labelledby="acCityLabel">' +
            '<span class="ap-combo__label' + ph + '" id="acCityTriggerLabel">' + esc(label) + '</span>' +
            COMBO_CHEVRON +
          '</button>' +
          '<div class="ap-combo__panel" id="acCityPanel" aria-hidden="true">' +
            '<input type="search" class="ap-combo__search" id="acCitySearch" ' +
              'placeholder="輸入搜尋縣市…" autocomplete="off" aria-label="搜尋縣市">' +
            '<ul class="ap-combo__list" id="acCityList" role="listbox" ' +
              'aria-labelledby="acCityLabel"></ul>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  function countryFieldMarkup(country, city) {
    var show = normalizeTaiwanCity(city) === '其他';
    return (
      '<label class="ap-field" id="acCountryField"' + (show ? '' : ' hidden') + '>' +
        '<span>國家 / 地區' + reqStar() + '</span>' +
        '<input type="text" name="country" id="acCountryInput" maxlength="40" ' +
          'autocomplete="off" placeholder="例：日本" value="' + esc(show ? (country || '') : '') + '"' +
          (show ? ' required' : '') + '>' +
      '</label>'
    );
  }

  function syncCountryField(city) {
    var field = document.getElementById('acCountryField');
    var input = document.getElementById('acCountryInput');
    if (!field || !input) return;
    var show = normalizeTaiwanCity(city) === '其他';
    field.hidden = !show;
    if (show) {
      input.required = true;
    } else {
      input.required = false;
      input.value = '';
    }
  }

  function displayTestimonialCity(t) {
    var city = String((t && t.city) || '').trim();
    var country = String((t && t.country) || '').trim();
    if (city === '其他' && country) return '其他（' + country + '）';
    return city;
  }

  var _cityComboDocBound = false;

  function closeOpenCityCombos(exceptRoot) {
    var nodes = document.querySelectorAll('.ap-combo.is-open');
    for (var i = 0; i < nodes.length; i++) {
      if (exceptRoot && nodes[i] === exceptRoot) continue;
      var closeFn = nodes[i]._apComboClose;
      if (typeof closeFn === 'function') closeFn();
      else {
        nodes[i].classList.remove('is-open');
        var t = nodes[i].querySelector('.ap-combo__trigger');
        var p = nodes[i].querySelector('.ap-combo__panel');
        if (t) t.setAttribute('aria-expanded', 'false');
        if (p) p.setAttribute('aria-hidden', 'true');
      }
    }
  }

  function ensureCityComboDocListeners() {
    if (_cityComboDocBound) return;
    _cityComboDocBound = true;
    document.addEventListener('mousedown', function (e) {
      var openCombo = document.querySelector('.ap-combo.is-open');
      if (!openCombo || openCombo.contains(e.target)) return;
      closeOpenCityCombos();
    });
    // Capture: close combo before admin.js Escape closes the whole modal.
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      var openCombo = document.querySelector('.ap-combo.is-open');
      if (!openCombo) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      closeOpenCityCombos();
      var t = openCombo.querySelector('.ap-combo__trigger');
      if (t) t.focus();
    }, true);
  }

  function bindCityCombo() {
    var root = document.getElementById('acCityCombo');
    if (!root || root.getAttribute('data-bound') === '1') return;
    root.setAttribute('data-bound', '1');
    ensureCityComboDocListeners();

    var trigger = document.getElementById('acCityTrigger');
    var panel = document.getElementById('acCityPanel');
    var search = document.getElementById('acCitySearch');
    var list = document.getElementById('acCityList');
    var hidden = document.getElementById('acCityValue');
    var labelEl = document.getElementById('acCityTriggerLabel');
    if (!trigger || !panel || !search || !list || !hidden || !labelEl) return;

    var open = false;
    var activeIndex = -1;

    function selectedValue() {
      return String(hidden.value || '');
    }

    function setOpen(next) {
      if (next === open) return;
      if (next) closeOpenCityCombos(root);
      open = next;
      root.classList.toggle('is-open', open);
      trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
      panel.setAttribute('aria-hidden', open ? 'false' : 'true');
      if (open) {
        search.value = '';
        activeIndex = -1;
        renderList('');
        setTimeout(function () { search.focus(); }, 20);
      }
    }

    root._apComboClose = function () { setOpen(false); };

    function choose(city) {
      var v = normalizeTaiwanCity(city);
      if (!isTaiwanCity(v)) return;
      hidden.value = v;
      labelEl.textContent = v;
      labelEl.classList.remove('is-placeholder');
      syncCountryField(v);
      setOpen(false);
      trigger.focus();
      if (v === '其他') {
        var countryInput = document.getElementById('acCountryInput');
        if (countryInput) setTimeout(function () { countryInput.focus(); }, 20);
      }
    }

    function renderList(query) {
      var cities = filterTaiwanCities(query);
      var sel = selectedValue();
      if (!cities.length) {
        list.innerHTML = '<li class="ap-combo__empty" role="presentation">無符合縣市</li>';
        activeIndex = -1;
        return;
      }
      list.innerHTML = cities.map(function (c, i) {
        var on = c === sel;
        return (
          '<li class="ap-combo__option' + (on ? ' is-selected' : '') + '" role="option" ' +
            'data-value="' + esc(c) + '" data-index="' + i + '" ' +
            'aria-selected="' + (on ? 'true' : 'false') + '" tabindex="-1">' +
            '<span class="ap-combo__option-label">' + esc(c) + '</span>' +
            (on ? COMBO_CHECK : '') +
          '</li>'
        );
      }).join('');
      activeIndex = -1;
    }

    function moveActive(delta) {
      var opts = list.querySelectorAll('.ap-combo__option');
      if (!opts.length) return;
      if (activeIndex >= 0) opts[activeIndex].classList.remove('is-active');
      activeIndex = (activeIndex + delta + opts.length) % opts.length;
      opts[activeIndex].classList.add('is-active');
      opts[activeIndex].scrollIntoView({ block: 'nearest' });
    }

    trigger.addEventListener('click', function (e) {
      e.preventDefault();
      setOpen(!open);
    });

    search.addEventListener('input', function () {
      renderList(search.value);
    });

    search.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); moveActive(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); moveActive(-1); }
      else if (e.key === 'Enter') {
        e.preventDefault();
        var opts = list.querySelectorAll('.ap-combo__option');
        if (activeIndex >= 0 && opts[activeIndex]) {
          choose(opts[activeIndex].getAttribute('data-value'));
        } else if (opts.length === 1) {
          choose(opts[0].getAttribute('data-value'));
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        setOpen(false);
        trigger.focus();
      }
    });

    list.addEventListener('click', function (e) {
      var opt = e.target.closest('.ap-combo__option');
      if (!opt || !list.contains(opt)) return;
      choose(opt.getAttribute('data-value'));
    });

    renderList('');
  }

  function pageLinkOptions(current) {
    current = String(current || '').trim();
    var known = {};
    var html = '<option value="">— 選擇頁面 —</option>';
    for (var i = 0; i < PAGE_LINKS.length; i++) {
      var p = PAGE_LINKS[i];
      known[p.value] = true;
      html +=
        '<option value="' +
        esc(p.value) +
        '"' +
        (current === p.value ? ' selected' : '') +
        '>' +
        esc(p.label) +
        '</option>';
    }
    if (current && !known[current]) {
      html +=
        '<option value="' +
        esc(current) +
        '" selected>目前連結：' +
        esc(current) +
        '</option>';
    }
    return html;
  }

  function esc(s) {
    return window.AdminPanel && window.AdminPanel.escapeHtml
      ? window.AdminPanel.escapeHtml(s)
      : String(s == null ? '' : s);
  }

  function truncate(s, n) {
    s = String(s || '');
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  function findTestimonial(id) {
    for (var i = 0; i < _testimonials.length; i++) {
      if (String(_testimonials[i].id) === String(id)) return _testimonials[i];
    }
    return null;
  }

  function findJournalPost(id) {
    for (var i = 0; i < _journalPosts.length; i++) {
      if (String(_journalPosts[i].id) === String(id)) return _journalPosts[i];
    }
    return null;
  }

  function todayDateValue() {
    var d = new Date();
    var m = String(d.getMonth() + 1);
    var day = String(d.getDate());
    if (m.length < 2) m = '0' + m;
    if (day.length < 2) day = '0' + day;
    return d.getFullYear() + '-' + m + '-' + day;
  }

  function findFaq(id) {
    for (var i = 0; i < _faqItems.length; i++) {
      if (String(_faqItems[i].id) === String(id)) return _faqItems[i];
    }
    return null;
  }

  function findBanner(id) {
    for (var i = 0; i < _banners.length; i++) {
      if (String(_banners[i].id) === String(id)) return _banners[i];
    }
    return null;
  }

  function catTitle(id) {
    for (var i = 0; i < _faqCategories.length; i++) {
      if (_faqCategories[i].id === id) return _faqCategories[i].title;
    }
    return id || '—';
  }

  function syncFaqCategoryId() {
    if (!_faqCategories.length) {
      _faqCategoryId = '';
      return;
    }
    for (var i = 0; i < _faqCategories.length; i++) {
      if (_faqCategories[i].id === _faqCategoryId) return;
    }
    _faqCategoryId = _faqCategories[0].id;
  }

  function activeFaqCategory() {
    syncFaqCategoryId();
    for (var i = 0; i < _faqCategories.length; i++) {
      if (_faqCategories[i].id === _faqCategoryId) return _faqCategories[i];
    }
    return null;
  }

  function pageImageId(row) {
    return String(row.page_key) + '\u001f' + String(row.slot_key);
  }

  function findPageImage(id) {
    for (var i = 0; i < _pageImages.length; i++) {
      if (pageImageId(_pageImages[i]) === String(id)) return _pageImages[i];
    }
    return null;
  }

  function pageImagePages() {
    if (_pageImagePageOptions.length) return _pageImagePageOptions.slice();
    var seen = {};
    return _pageImages.reduce(function (pages, row) {
      if (!seen[row.page_key]) {
        seen[row.page_key] = true;
        pages.push({ value: row.page_key, label: row.label || row.page_key });
      }
      return pages;
    }, []);
  }

  function rememberPageImagePages(rows) {
    var seen = {};
    _pageImagePageOptions.forEach(function (p) { seen[p.value] = true; });
    (rows || []).forEach(function (row) {
      if (!row || !row.page_key || seen[row.page_key]) return;
      seen[row.page_key] = true;
      _pageImagePageOptions.push({
        value: row.page_key,
        label: row.label || row.page_key,
      });
    });
  }

  function renderShell() {
    ['contentReactMount', 'cmsPagesMount'].forEach(function (id) {
      var oldMount = document.getElementById(id);
      if (oldMount && window.AdminTables && window.AdminTables.unmount) {
        try { window.AdminTables.unmount(oldMount); } catch (e) {}
      }
    });

    var imagePages = pageImagePages();
    if (_tab === 'page-images' && (!_pageImagePage || !imagePages.some(function (p) { return p.value === _pageImagePage; }))) {
      _pageImagePage = imagePages.length ? imagePages[0].value : '';
    }

    var pageSubTabsHtml = '';
    if (_tab === 'page-images' && imagePages.length > 0) {
      pageSubTabsHtml = '<div class="adx-tabs adx-tabs--sub" role="tablist">';
      for (var pi = 0; pi < imagePages.length; pi++) {
        var pg = imagePages[pi];
        pageSubTabsHtml +=
          '<button type="button" class="adx-tab' +
          (_pageImagePage === pg.value ? ' is-active' : '') +
          '" data-page-tab="' +
          esc(pg.value) +
          '">' +
          esc(pg.label) +
          '</button>';
      }
      pageSubTabsHtml += '</div>';
    }

    if (_tab === 'copy') _tab = 'pages';

    root.innerHTML =
      '<p class="adx-panel-note">「頁面」= 編輯現有官網文字／圖片。圖片素材也可用「頁面圖片／首頁圖片」。FAQ／見證用對應分頁。商店試算／上架／價格表不在此編輯。</p>' +
      '<p class="note warn" role="status">Beta 測試功能：開發中，使用請自負風險。</p>' +
      '<div class="adx-tabs" role="tablist">' +
        '<button type="button" class="adx-tab' + (_tab === 'banners' ? ' is-active' : '') + '" data-tab="banners">首頁圖片</button>' +
        '<button type="button" class="adx-tab' + (_tab === 'page-images' ? ' is-active' : '') + '" data-tab="page-images">頁面圖片</button>' +
        '<button type="button" class="adx-tab' + (_tab === 'testimonials' ? ' is-active' : '') + '" data-tab="testimonials">見證</button>' +
        '<button type="button" class="adx-tab' + (_tab === 'journal' ? ' is-active' : '') + '" data-tab="journal">日誌</button>' +
        '<button type="button" class="adx-tab' + (_tab === 'faq' ? ' is-active' : '') + '" data-tab="faq">FAQ</button>' +
        '<button type="button" class="adx-tab' + (_tab === 'pages' ? ' is-active' : '') + '" data-tab="pages">頁面 <span class="adx-risk-tag">Beta · 風險</span></button>' +
      '</div>' +
      pageSubTabsHtml +
      '<div id="contentPanelBody"></div>';

    root.querySelectorAll('[data-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var nextTab = btn.dataset.tab;
        if (!nextTab || nextTab === _tab) return;
        _tab = nextTab;
        if (_pageIndex !== 0) {
          _pageIndex = 0;
          load(true, true);
          return;
        }
        if (!_loadedTabs[_tab]) {
          load(false);
          return;
        }
        renderShell();
      });
    });

    root.querySelectorAll('[data-page-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var pageKey = btn.dataset.pageTab;
        if (!pageKey || pageKey === _pageImagePage) return;
        _pageImagePage = pageKey;
        _pageIndex = 0;
        load(true, true);
      });
    });

    var body = document.getElementById('contentPanelBody');
    if (_tab === 'pages') renderCmsPages(body);
    else if (_tab === 'journal') {
      body.innerHTML = '';
      renderJournal(body);
    } else if (_tab === 'faq') {
      body.innerHTML = '';
      renderFaqCategoryBar(body);
      renderContentReact(body, imagePages);
    } else {
      body.innerHTML = '';
      renderContentReact(body, imagePages);
    }
  }

  function cmsApiBridge() {
    return {
      listPages: function () { return api.admin.listCmsPages(); },
      getPage: function (id) { return api.admin.getCmsPage(id); },
      getCmsSitePage: function (route) { return api.admin.getCmsSitePage(route); },
      updatePage: function (fields) { return api.admin.updateCmsPage(fields); },
      pageAction: function (id, action) { return api.admin.cmsPageAction(id, action); },
      createSection: function (pageId, body) { return api.admin.createCmsSection(pageId, body); },
      updateSection: function (fields) { return api.admin.updateCmsSection(fields); },
      getSectionHtml: function (id) { return api.admin.getCmsSectionHtml(id); },
      sectionAction: function (id, action) { return api.admin.cmsSectionAction(id, action); },
      reorderSections: function (pageId, sectionIds) { return api.admin.reorderCmsSections(pageId, sectionIds); },
      getMedia: function (opts) { return api.admin.getCmsMedia(opts); },
      getFaqCategories: function () { return api.admin.getFaqCategories(); },
      uploadMedia: function (file) { return api.admin.uploadCmsMedia(file); },
      deleteMedia: function (id) { return api.admin.cmsMediaAction(id, 'delete'); },
      uploadPageImage: function (file, pageKey) {
        return api.admin.uploadPageImage(file, pageKey || undefined);
      },
      getPageImages: function () { return api.admin.getPageImages(); },
      updatePageImage: function (fields) { return api.admin.updatePageImage(fields); },
      syncSectionPageImage: function (fields) {
        return api.admin.syncCmsSectionPageImage({
          sectionId: fields.sectionId,
          section_id: fields.sectionId,
          imageUrl: fields.imageUrl,
          image_url: fields.imageUrl,
          imageAlt: fields.imageAlt,
          image_alt: fields.imageAlt,
          action: 'upsert',
        });
      },
      removeSectionPageImage: function (fields) {
        return api.admin.removeCmsSectionPageImage({
          sectionId: fields.sectionId,
          section_id: fields.sectionId,
          action: 'delete',
        });
      },
      getCopySlots: function (pageKey) { return api.admin.getPageCopySlots(pageKey); },
      updateCopySlot: function (fields) { return api.admin.updatePageCopySlot(fields); },
      getJournalPosts: function (opts) { return api.admin.getJournalPosts(opts); },
      createJournalPost: function (fields) { return api.admin.createJournalPost(fields); },
      updateJournalPost: function (fields) { return api.admin.updateJournalPost(fields); },
      journalPostAction: function (id, action) { return api.admin.journalPostAction(id, action); },
    };
  }

  function renderCmsPages(body) {
    if (!body) return;
    if (!window.AdminTables || !window.AdminTables.renderCmsPagesPanel) {
      body.innerHTML = '<p class="note warn">頁面編輯器尚未載入，請重新整理。</p>';
      return;
    }
    body.innerHTML = '<div id="cmsPagesMount"></div>';
    window.AdminTables.renderCmsPagesPanel(document.getElementById('cmsPagesMount'), {
      api: cmsApiBridge(),
    });
  }

  function renderFaqCategoryBar(body) {
    if (!body) return;
    syncFaqCategoryId();
    var active = activeFaqCategory();
    var bar = document.createElement('div');
    bar.className = 'cms-faq-cat-bar';

    var tabsHtml =
      '<div class="adx-tabs adx-tabs--sub cms-faq-cat-tabs" role="tablist" aria-label="FAQ 分類">';
    for (var i = 0; i < _faqCategories.length; i++) {
      var c = _faqCategories[i];
      var isActive = c.id === _faqCategoryId;
      tabsHtml +=
        '<button type="button" class="adx-tab' +
        (isActive ? ' is-active' : '') +
        '" role="tab" aria-selected="' +
        (isActive ? 'true' : 'false') +
        '" data-faq-cat="' +
        esc(c.id) +
        '">' +
        esc(c.title) +
        '</button>';
    }
    tabsHtml +=
      '<button type="button" class="adx-tab cms-faq-cat-add" id="faqCatAddBtn" aria-label="新增分類" title="新增分類">+</button>' +
      '</div>';

    var toolsHtml = '<div class="cms-faq-cat-tools">';
    if (active) {
      toolsHtml +=
        '<form class="cms-faq-cat-form" id="faqCatEditForm">' +
          '<strong>此分類</strong>' +
          '<code class="cms-faq-cat-id" title="分類 id">' + esc(active.id) + '</code>' +
          '<input name="id" type="hidden" value="' + esc(active.id) + '">' +
          '<input name="title" value="' + esc(active.title) + '" placeholder="分類名稱" required>' +
          '<input name="sortOrder" type="number" value="' +
            esc(String(active.sort_order != null ? active.sort_order : 0)) +
            '" title="排序（數字小在前）" aria-label="分類排序" style="width:5.5rem">' +
          '<button type="submit" class="btn-sm">更新</button>' +
          '<button type="button" class="btn-sm" id="faqCatDeleteBtn">刪除分類</button>' +
        '</form>';
    }
    toolsHtml += '</div>';

    bar.innerHTML = tabsHtml + toolsHtml;
    body.appendChild(bar);

    bar.querySelectorAll('[data-faq-cat]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var nextId = btn.getAttribute('data-faq-cat') || '';
        if (!nextId || nextId === _faqCategoryId) return;
        _faqCategoryId = nextId;
        renderShell();
      });
    });

    var addBtn = bar.querySelector('#faqCatAddBtn');
    if (addBtn) {
      addBtn.addEventListener('click', function () {
        var title = window.prompt('新分類名稱');
        if (title == null) return;
        title = String(title).trim();
        if (!title) return;
        api.admin.createFaqCategory({
          title: title,
          id: '',
          sortOrder: 0,
        }).then(function (res) {
          if (res.error) { alert(res.error.message || res.error); return; }
          if (res.category && res.category.id) _faqCategoryId = res.category.id;
          load(true, true);
        });
      });
    }

    var editForm = bar.querySelector('#faqCatEditForm');
    if (editForm) {
      editForm.addEventListener('submit', function (e) {
        e.preventDefault();
        var fd = new FormData(editForm);
        api.admin.updateFaqCategory({
          id: String(fd.get('id') || ''),
          title: String(fd.get('title') || ''),
          sortOrder: fd.get('sortOrder'),
        }).then(function (res) {
          if (res.error) { alert(res.error.message || res.error); return; }
          load(true, true);
        });
      });
      bar.querySelector('#faqCatDeleteBtn').addEventListener('click', function () {
        var id = String(editForm.querySelector('[name="id"]').value || '');
        if (!id || !confirm('刪除此分類？分類下不可有 FAQ。')) return;
        api.admin.faqCategoryAction(id, 'delete').then(function (res) {
          if (res.error) { alert(res.error.message || res.error); return; }
          _faqCategoryId = '';
          load(true, true);
        });
      });
    }
  }

  function renderContentReact(body, imagePages) {
    if (!body) return;
    if (!window.AdminTables || !window.AdminTables.renderContentTables) {
      body.innerHTML = '<p class="note warn">表格元件尚未載入，請重新整理頁面。</p>';
      return;
    }

    var mount = document.getElementById('contentReactMount');
    if (!mount) {
      mount = document.createElement('div');
      mount.id = 'contentReactMount';
      body.appendChild(mount);
    }
    imagePages = imagePages || pageImagePages();

    var faqSource = _faqItems;
    if (_tab === 'faq' && _faqCategoryId) {
      faqSource = _faqItems.filter(function (f) {
        return String(f.category_id) === String(_faqCategoryId);
      });
    }
    var faqRows = faqSource.map(function (f) {
      return {
        id: String(f.id),
        category_title: catTitle(f.category_id),
        question: f.question || '',
        show_in_teaser: !!f.show_in_teaser,
        is_published: !!f.is_published,
      };
    });

    var bannerRows = _banners.map(function (b) {
      return {
        id: String(b.id),
        title: b.title || '',
        eyebrow: b.eyebrow || '',
        sort_order: Number(b.sort_order || 0),
        is_published: !!b.is_published,
        image_url: b.image_url || '',
        image_url_mobile: b.image_url_mobile || '',
        align: b.align || 'left',
      };
    });

    var testimonialRows = _testimonials.slice().sort(function (a, b) {
      return Number(a.sort_order || 0) - Number(b.sort_order || 0);
    }).map(function (t) {
      return {
        id: String(t.id),
        name: t.name || '',
        category: t.category || '',
        city: displayTestimonialCity(t),
        text: t.text || '',
        sort_order: Number(t.sort_order || 0),
        is_published: !!t.is_published,
        image_url: t.image_url || '',
      };
    });

    var pageImageRows = _pageImages
      .filter(function (p) {
        return !_pageImagePage || p.page_key === _pageImagePage;
      })
      .map(function (p) {
        return {
          id: pageImageId(p),
          label: p.label || p.page_key,
          page_key: p.page_key,
          slot_key: p.slot_key,
          slot_label: p.slot_label || p.slot_key,
          group_key: p.group_key || 'brand',
          target_w: Number(p.target_w || 0),
          target_h: Number(p.target_h || 0),
          is_published: !!p.is_published,
          image_url: p.image_url || '',
          display_url: p.display_url || p.image_url || p.default_image_url || '',
        };
      });

    window.AdminTables.renderContentTables(mount, {
      tab: _tab,
      banners: bannerRows,
      testimonials: testimonialRows,
      faqItems: faqRows,
      pageImages: pageImageRows,
      pageImagePage: _pageImagePage,
      total: _totals[_tab] || 0,
      pageIndex: _pageIndex,
      pageSize: _pageSize,
      onPaginationChange: function (pagination) {
        var nextIndex = pagination.pageIndex || 0;
        var nextSize = pagination.pageSize || _pageSize;
        if (nextIndex === _pageIndex && nextSize === _pageSize) return;
        _pageIndex = nextIndex;
        _pageSize = nextSize;
        load(true, true);
      },
      onAdd: function () {
        if (_tab === 'banners') openBannerModal(null);
        else if (_tab === 'testimonials') openTestimonialModal(null);
        else if (_tab === 'faq') openFaqModal(null);
      },
      onEdit: function (id) {
        if (_tab === 'banners') openBannerModal(findBanner(id));
        else if (_tab === 'testimonials') openTestimonialModal(findTestimonial(id));
        else if (_tab === 'page-images') openPageImageModal(findPageImage(id));
        else openFaqModal(findFaq(id));
      },
      onReorder: function (id, direction) {
        if (_tab !== 'testimonials' || !id || !direction) return;
        api.admin.reorderTestimonial(id, direction).then(function (res) {
          if (res.error) {
            alert(res.error.message || res.error);
            return;
          }
          load(true, true);
        });
      },
      onAction: function (id, action) {
        if (!id || !action) return;
        if (_tab === 'page-images') {
          var pageImage = findPageImage(id);
          if (!pageImage) return;
          if (action === 'reset' && !confirm('還原此圖片為預設值？')) return;
          api.admin.pageImageAction(pageImage.page_key, pageImage.slot_key, action).then(function (res) {
            if (res.error) {
              alert(res.error.message || res.error);
              return;
            }
            load(true, true);
          });
          return;
        }
        // Delete is confirmed by AdminContentTables DeleteConfirmDialog — no window.confirm.
        var req =
          _tab === 'banners'
            ? api.admin.bannerAction(id, action)
            : _tab === 'testimonials'
              ? api.admin.testimonialAction(id, action)
              : api.admin.faqAction(id, action);
        req.then(function (res) {
          if (res.error) {
            alert(res.error.message || res.error);
            return;
          }
          load(true, true);
        });
      },
    });
  }

  function openPageImageModal(row) {
    if (!row) return;
    if (!window.AdminTables || !window.AdminTables.renderPageImageEditModal) {
      alert('頁面元件尚未載入，請重新整理後再試。');
      return;
    }
    var mount = document.createElement('div');
    mount.id = 'acPageImageModalMount';
    document.body.appendChild(mount);

    function close() {
      if (window.AdminTables && window.AdminTables.unmount) {
        window.AdminTables.unmount(mount);
      }
      if (mount.parentNode) mount.parentNode.removeChild(mount);
    }

    window.AdminTables.renderPageImageEditModal(mount, {
      row: {
        page_key: row.page_key,
        slot_key: row.slot_key,
        slot_label: row.slot_label,
        label: row.label,
        target_w: row.target_w,
        target_h: row.target_h,
        is_published: !!row.is_published,
        image_url: row.image_url || '',
        image_webp: row.image_webp || '',
        image_alt: row.image_alt || '',
        display_url: row.display_url || '',
        default_image_url: row.default_image_url || '',
        previous_image_url: row.previous_image_url || row.previousImageUrl || '',
        previous_image_webp: row.previous_image_webp || row.previousImageWebp || '',
        previousImageUrl: row.previousImageUrl || row.previous_image_url || '',
        previousImageWebp: row.previousImageWebp || row.previous_image_webp || '',
      },
      onClose: close,
      onSaved: function () {
        close();
        load(true, true);
      },
      uploadImage: function (file) {
        return api.admin.uploadPageImage(file, row.page_key);
      },
      updatePageImage: function (fields) {
        return api.admin.updatePageImage(fields);
      },
      pageImageAction: function (pageKey, slotKey, action) {
        return api.admin.pageImageAction(pageKey, slotKey, action);
      },
    });
  }

  function openPageImageCreateModal() {
    if (!window.AdminTables || !window.AdminTables.renderPageImageCreateModal) {
      alert('頁面元件尚未載入，請重新整理後再試。');
      return;
    }
    api.admin.getPageImageCreateOptions().then(function (res) {
      if (res.error) {
        alert(res.error.message || res.error);
        return;
      }
      var mount = document.createElement('div');
      mount.id = 'acPageImageCreateModalMount';
      document.body.appendChild(mount);

      function closeCreate() {
        if (window.AdminTables && window.AdminTables.unmount) {
          window.AdminTables.unmount(mount);
        }
        if (mount.parentNode) mount.parentNode.removeChild(mount);
      }

      window.AdminTables.renderPageImageCreateModal(mount, {
        options: res.options || [],
        defaultPageKey: _pageImagePage,
        onClose: closeCreate,
        onCreated: function (createdRow) {
          closeCreate();
          _pageImagePage = createdRow.page_key;
          openPageImageModal(createdRow);
          load(true, true);
        },
        createPageImage: function (pageKey, slotKey) {
          return api.admin.createPageImage(pageKey, slotKey);
        },
      });
    });
  }

  function renderBanners(body) {
    renderContentReact(body);
  }

  function bindBannerAction(btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var action = btn.dataset.action;
      var id = btn.dataset.id;
      if (action === 'edit-b') {
        openBannerModal(findBanner(id));
        return;
      }
      var apiAction = action === 'publish-b' ? 'publish' : action === 'unpublish-b' ? 'unpublish' : action === 'delete-b' ? 'delete' : null;
      if (!apiAction || !id) return;
      if (apiAction === 'delete' && !confirm('確定刪除此首頁圖片？')) return;
      btn.disabled = true;
      api.admin.bannerAction(id, apiAction).then(function (res) {
        btn.disabled = false;
        if (res.error) { alert(res.error.message || res.error); return; }
        load(true, true);
      });
    });
  }

  function unmountBannerEditorMounts() {
    if (!window.AdminTables || !window.AdminTables.unmount) return;
    ['acBannerImgCardsMount', 'acPrimaryHrefMount', 'acSecondaryHrefMount'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) window.AdminTables.unmount(el);
    });
  }

  function closeBannerEditor() {
    unmountBannerEditorMounts();
    renderShell();
  }

  /** Full-page editor (not float modal) so crop dialog can sit above the page cleanly. */
  function openBannerModal(b) {
    var isEdit = !!(b && b.id);
    var tone = isEdit ? (b.tone || 'warm') : 'warm';
    var align = isEdit ? (b.align || 'left') : 'left';
    var existDesktop = isEdit ? (b.image_url || '') : '';
    var existMobile = isEdit ? (b.image_url_mobile || '') : '';
    var html =
      '<div class="ap-editor-page ac-banner-editor">' +
        '<div class="ap-editor-head">' +
          '<div class="ap-editor-head-text">' +
            '<h2>' + (isEdit ? '編輯首頁圖片' : '新增首頁圖片') + '</h2>' +
            '<p class="ap-editor-sub">先裁切電腦版（16:9）與手機版（9:16），再填寫文案與按鈕連結。</p>' +
          '</div>' +
          '<button type="button" class="btn-sm ap-editor-back" id="acBannerBack">← 返回首頁圖片列表</button>' +
        '</div>' +
        '<div class="ap-editor-body">' +
          '<p class="ap-form-error" id="acFormError" hidden></p>' +
          '<form id="acBannerForm" class="ap-form" data-id="' + esc(isEdit ? b.id : '') + '">' +
            '<div class="ap-form-grid">' +
              '<label class="ap-field"><span>眉題</span><input name="eyebrow" placeholder="Imprint Diamond" value="' + esc(isEdit ? b.eyebrow : '') + '"></label>' +
              '<label class="ap-field"><span>色調</span><select name="tone">' +
                '<option value="warm"' + (tone === 'warm' ? ' selected' : '') + '>warm</option>' +
                '<option value="light"' + (tone === 'light' ? ' selected' : '') + '>light</option>' +
                '<option value="soft"' + (tone === 'soft' ? ' selected' : '') + '>soft</option>' +
              '</select></label>' +
              '<div class="ap-field ac-banner-align-field"><span>文字位置</span>' +
                '<div class="ac-banner-align" role="group" aria-label="文字位置">' +
                  '<label class="ac-banner-align__option"><input type="radio" name="align" value="left"' + (align === 'left' ? ' checked' : '') + '><span>靠左</span></label>' +
                  '<label class="ac-banner-align__option"><input type="radio" name="align" value="right"' + (align === 'right' ? ' checked' : '') + '><span>靠右</span></label>' +
                '</div>' +
              '</div>' +
              '<label class="ap-field ap-field--full"><span>標題</span><input name="title" required value="' + esc(isEdit ? b.title : '') + '"></label>' +
              '<label class="ap-field ap-field--full"><span>說明</span><textarea name="lead" class="ap-textarea" rows="3">' + esc(isEdit ? b.lead : '') + '</textarea></label>' +
              '<div class="ap-field ap-field--full">' +
                '<input type="hidden" name="imageUrl" id="acBannerImageUrl" value="' + esc(existDesktop) + '">' +
                '<input type="hidden" name="imageUrlMobile" id="acBannerImageUrlMobile" value="' + esc(existMobile) + '">' +
                '<div id="acBannerImgCardsMount"></div>' +
              '</div>' +
              '<label class="ap-field"><span>主按鈕文字</span><input name="ctaPrimaryLabel" value="' + esc(isEdit ? b.cta_primary_label : '') + '"></label>' +
              '<div class="ap-field" id="acPrimaryHrefMount"></div>' +
              '<label class="ap-field"><span>次按鈕文字</span><input name="ctaSecondaryLabel" value="' + esc(isEdit ? b.cta_secondary_label : '') + '"></label>' +
              '<div class="ap-field" id="acSecondaryHrefMount"></div>' +
              '<label class="ap-field"><span>排序</span><input type="number" name="sortOrder" value="' + esc(String(isEdit ? b.sort_order : 0)) + '"></label>' +
              '<label class="ap-field ap-field--check"><input type="checkbox" name="isPublished"' + (!isEdit || b.is_published ? ' checked' : '') + '><span>發布</span></label>' +
            '</div>' +
            '<div class="ap-form-actions ap-editor-actions">' +
              '<button type="button" class="btn-sm" id="acBannerCancel">取消</button>' +
              '<button type="submit" class="btn-sm btn-primary">' + (isEdit ? '儲存' : '建立') + '</button>' +
            '</div>' +
          '</form>' +
        '</div>' +
      '</div>';

    // Unmount list React table before replacing shell
    var listMount = document.getElementById('contentTablesMount') || document.getElementById('contentPanelBody');
    if (listMount && window.AdminTables && window.AdminTables.unmount) {
      try { window.AdminTables.unmount(listMount); } catch (e) { /* ignore */ }
    }

    root.innerHTML = html;
    root.scrollIntoView({ block: 'start', behavior: 'smooth' });

    var backBtn = document.getElementById('acBannerBack');
    var cancelBtn = document.getElementById('acBannerCancel');
    if (backBtn) backBtn.addEventListener('click', closeBannerEditor);
    if (cancelBtn) cancelBtn.addEventListener('click', closeBannerEditor);

    var form = document.getElementById('acBannerForm');
    if (form) form.addEventListener('submit', submitBanner);

    if (window.AdminTables && window.AdminTables.renderPageLinkSelect) {
      var primaryMount = document.getElementById('acPrimaryHrefMount');
      var secondaryMount = document.getElementById('acSecondaryHrefMount');
      if (primaryMount) {
        window.AdminTables.renderPageLinkSelect(primaryMount, {
          name: 'ctaPrimaryHref',
          label: '主按鈕連結',
          value: isEdit ? (b.cta_primary_href || '') : '/shop/calculator/',
          placeholder: '— 選擇頁面 —',
        });
      }
      if (secondaryMount) {
        window.AdminTables.renderPageLinkSelect(secondaryMount, {
          name: 'ctaSecondaryHref',
          label: '次按鈕連結',
          value: isEdit ? (b.cta_secondary_href || '') : '',
          placeholder: '— 選擇頁面 —',
        });
      }
    }

    if (window.AdminTables && window.AdminTables.renderBannerImageUploadCards) {
      var cardsMount = document.getElementById('acBannerImgCardsMount');
      if (cardsMount) {
        window.AdminTables.renderBannerImageUploadCards(cardsMount, {
          initialDesktopUrl: existDesktop,
          initialMobileUrl: existMobile,
          onDesktopUrlChange: function (url) {
            var el = document.getElementById('acBannerImageUrl');
            if (el) el.value = url;
          },
          onMobileUrlChange: function (url) {
            var el = document.getElementById('acBannerImageUrlMobile');
            if (el) el.value = url;
          },
          uploadImage: function (file) {
            if (!file || !file.size) {
              return Promise.resolve({ error: '請選擇圖片' });
            }
            return api.admin.uploadBanner(file);
          },
        });
      }
    }
  }

  function submitBanner(e) {
    e.preventDefault();
    var form = e.target;
    var fd = new FormData(form);
    var errEl = document.getElementById('acFormError');
    var id = form.dataset.id;
    var payload = {
      id: id || undefined,
      eyebrow: String(fd.get('eyebrow') || '').trim(),
      title: String(fd.get('title') || '').trim(),
      lead: String(fd.get('lead') || '').trim(),
      imageUrl: String(fd.get('imageUrl') || '').trim(),
      imageUrlMobile: String(fd.get('imageUrlMobile') || '').trim(),
      ctaPrimaryLabel: String(fd.get('ctaPrimaryLabel') || '').trim(),
      ctaPrimaryHref: String(fd.get('ctaPrimaryHref') || '').trim(),
      ctaSecondaryLabel: String(fd.get('ctaSecondaryLabel') || '').trim(),
      ctaSecondaryHref: String(fd.get('ctaSecondaryHref') || '').trim(),
      tone: String(fd.get('tone') || 'warm').trim(),
      align: String(fd.get('align') || 'left').trim(),
      sortOrder: fd.get('sortOrder'),
      isPublished: !!form.querySelector('[name="isPublished"]').checked,
    };
    if (!payload.imageUrl) {
      if (errEl) {
        errEl.textContent = '請先上傳並裁切電腦版圖片';
        errEl.hidden = false;
      } else {
        alert('請先上傳並裁切電腦版圖片');
      }
      return;
    }
    var req = id ? api.admin.updateBanner(payload) : api.admin.createBanner(payload);
    req.then(function (res) {
      if (res.error) {
        if (errEl) { errEl.textContent = res.error.message || res.error; errEl.hidden = false; }
        else alert(res.error);
        return;
      }
      unmountBannerEditorMounts();
      load(true, true);
    });
  }

  function journalRowsSorted() {
    return _journalPosts.slice().sort(function (a, b) {
      var da = String(a.posted_at || '');
      var db = String(b.posted_at || '');
      if (da !== db) return db.localeCompare(da);
      return Number(a.sort_order || 0) - Number(b.sort_order || 0);
    });
  }

  function renderJournalRow(p) {
    var published = !!p.is_published;
    var archived = !!p.is_archived;
    var thumb = p.image_url
      ? '<img src="' + esc(p.image_url) + '" alt="" width="40" height="40" loading="lazy" decoding="async" style="object-fit:cover;border-radius:4px">'
      : '—';
    return (
      '<tr data-id="' + esc(String(p.id)) + '">' +
        '<td>' + esc(p.posted_at || '') + '</td>' +
        '<td>' + esc(p.title || '') + '</td>' +
        '<td>' + esc(truncate(p.body || '', 48)) + '</td>' +
        '<td>' + thumb + '</td>' +
        '<td>' + (archived
          ? '<span class="ap-status-badge ap-status-badge--offline">活動已結束</span>'
          : '<span class="ap-status-badge ap-status-badge--draft">進行中</span>') + '</td>' +
        '<td>' + (published
          ? '<span class="ap-status-badge ap-status-badge--live">已發布</span>'
          : '<span class="ap-status-badge ap-status-badge--draft">未發布</span>') + '</td>' +
        '<td><div class="adx-actions">' +
          '<button type="button" class="btn-sm" data-j-action="edit" data-id="' + esc(String(p.id)) + '">編輯</button>' +
          '<button type="button" class="btn-sm" data-j-action="' + (published ? 'unpublish' : 'publish') +
            '" data-id="' + esc(String(p.id)) + '">' + (published ? '下架' : '發布') + '</button>' +
          '<button type="button" class="btn-sm adx-action--danger" data-j-action="delete" data-id="' +
            esc(String(p.id)) + '">刪除</button>' +
        '</div></td>' +
      '</tr>'
    );
  }

  function renderJournal(body) {
    if (!body) return;
    if (_journalError) {
      body.innerHTML =
        '<p class="note warn">日誌文章載入失敗：' + esc(_journalError) + '</p>' +
        '<button type="button" class="btn-sm" id="acJournalRetryBtn">重新載入</button>';
      var retry = document.getElementById('acJournalRetryBtn');
      if (retry) retry.addEventListener('click', function () { load(true, true); });
      return;
    }
    var rows = journalRowsSorted();
    var tableHtml = !rows.length
      ? '<p class="adx-table-empty">尚無日誌。點「新增日誌」建立第一則。</p>'
      : (
        '<div class="adx-table-card"><div class="adx-table-wrap"><table class="adx-table">' +
          '<thead><tr>' +
            '<th>日期</th><th>標題</th><th>內容</th><th>圖片</th><th>活動</th><th>狀態</th><th>操作</th>' +
          '</tr></thead><tbody>' + rows.map(renderJournalRow).join('') + '</tbody></table></div></div>'
      );
    body.innerHTML =
      '<div class="adx-panel-toolbar">' +
        '<button type="button" class="btn-sm btn-primary" id="acJournalAddBtn">+ 新增日誌</button>' +
      '</div>' + tableHtml;
    var addBtn = document.getElementById('acJournalAddBtn');
    if (addBtn) addBtn.addEventListener('click', function () { openJournalModal(null); });
    body.querySelectorAll('[data-j-action]').forEach(bindJournalAction);
  }

  function bindJournalAction(btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var action = btn.getAttribute('data-j-action');
      var id = btn.getAttribute('data-id');
      if (!id || !action) return;
      if (action === 'edit') {
        openJournalModal(findJournalPost(id));
        return;
      }
      if (action === 'delete' && !confirm('確定刪除此日誌？')) return;
      btn.disabled = true;
      api.admin.journalPostAction(id, action).then(function (res) {
        btn.disabled = false;
        if (res.error) { alert(res.error.message || res.error); return; }
        load(true, true);
      });
    });
  }

  function openJournalModal(p) {
    var isEdit = !!(p && p.id);
    var imageUrl = isEdit ? (p.image_url || '') : '';
    var postedAt = String((isEdit && p.posted_at) || '').trim().slice(0, 10) || todayDateValue();
    var html =
      '<div class="qr-modal ai-modal" role="dialog" aria-modal="true">' +
        '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
        '<h3>' + (isEdit ? '編輯日誌' : '新增日誌') + '</h3>' +
        '<p class="ap-form-error" id="acFormError" hidden></p>' +
        '<form id="acJournalForm" class="ap-form" novalidate data-id="' + esc(isEdit ? p.id : '') + '">' +
          '<div class="ap-form-grid">' +
            '<label class="ap-field"><span>日期' + reqStar() + '</span>' +
              '<input type="date" name="posted_at" required value="' + esc(postedAt) + '"></label>' +
            '<label class="ap-field ap-field--full"><span>標題' + reqStar() + '</span>' +
              '<input name="title" required maxlength="200" value="' + esc(isEdit ? (p.title || '') : '') + '"></label>' +
            '<label class="ap-field ap-field--full"><span>內容</span>' +
              '<textarea name="body" class="ap-textarea" rows="8" placeholder="日誌內容…">' +
                esc(isEdit ? (p.body || '') : '') + '</textarea></label>' +
            '<div class="ap-field ap-field--full"><span>圖片（選填）</span>' +
              '<div id="acJournalImageUploadMount"></div>' +
              '<p class="ap-section-hint">JPG / PNG / WEBP；上傳後轉 WebP。可留空；已有圖不必重傳。</p>' +
              '<input type="hidden" name="image_url" id="acJournalImageUrl" value="' + esc(imageUrl) + '">' +
            '</div>' +
            '<label class="ap-field ap-field--check"><input type="checkbox" name="is_archived"' +
              (isEdit && p.is_archived ? ' checked' : '') + '><span>活動已結束</span></label>' +
            '<label class="ap-field ap-field--check"><input type="checkbox" name="is_published"' +
              (!isEdit || p.is_published ? ' checked' : '') + '><span>發布</span></label>' +
          '</div>' +
          '<div class="ap-form-actions">' +
            '<button type="button" class="btn-sm" data-modal-close>取消</button>' +
            '<button type="submit" class="btn-sm btn-primary">' + (isEdit ? '儲存' : '建立') + '</button>' +
          '</div>' +
        '</form></div>';

    if (!window.AdminPanel || !window.AdminPanel.openModal) return;
    window.AdminPanel.openModal(html);
    var form = document.getElementById('acJournalForm');
    if (form) form.addEventListener('submit', submitJournal);

    var urlInput = document.getElementById('acJournalImageUrl');
    if (window.AdminTables && window.AdminTables.renderImageUploadField) {
      var mount = document.getElementById('acJournalImageUploadMount');
      if (mount && urlInput) {
        window.AdminTables.renderImageUploadField(mount, {
          value: imageUrl,
          onChange: function (url) { urlInput.value = url || ''; },
          onUpload: function (file) { return api.admin.uploadPageImage(file, '/journal'); },
          onValidationError: function (message) {
            var errEl = document.getElementById('acFormError');
            if (errEl) { errEl.textContent = String(message || '上傳失敗'); errEl.hidden = false; }
          },
          onPendingDiscarded: function (message) {
            if (typeof window.showToast === 'function') {
              window.showToast(String(message || '尚未確認裁切，將使用原圖/空白'), 'info');
            }
          },
        });
      }
    } else {
      var hintMissing = document.getElementById('acFormError');
      if (hintMissing) {
        hintMissing.textContent = '圖片上傳元件未載入（仍可無圖儲存）。請硬重新整理後再上傳圖片。';
        hintMissing.hidden = false;
      }
    }
  }

  function submitJournal(e) {
    e.preventDefault();
    var form = e.target;
    var fd = new FormData(form);
    var errEl = document.getElementById('acFormError');
    var id = form.dataset.id;
    // image_url optional: null / keep existing hidden value / new URL after confirm upload.
    var payload = {
      id: id || undefined,
      title: String(fd.get('title') || '').trim(),
      body: String(fd.get('body') || '').trim(),
      posted_at: String(fd.get('posted_at') || '').trim().slice(0, 10) || todayDateValue(),
      image_url: String(fd.get('image_url') || '').trim() || null,
      is_archived: !!form.querySelector('[name="is_archived"]').checked,
      is_published: !!form.querySelector('[name="is_published"]').checked,
    };
    if (!payload.title) {
      if (errEl) { errEl.textContent = '請填寫標題'; errEl.hidden = false; }
      return;
    }
    if (!payload.posted_at) {
      if (errEl) { errEl.textContent = '請填寫日期'; errEl.hidden = false; }
      return;
    }
    if (errEl) errEl.hidden = true;
    var req = id ? api.admin.updateJournalPost(payload) : api.admin.createJournalPost(payload);
    req.then(function (res) {
      if (res.error) {
        if (errEl) { errEl.textContent = res.error.message || res.error; errEl.hidden = false; }
        else alert(res.error);
        return;
      }
      if (window.AdminPanel.closeModal) window.AdminPanel.closeModal();
      load(true, true);
    });
  }

  function renderTestimonials(body) {
    renderContentReact(body);
  }

  function bindTestimonialAction(btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var action = btn.dataset.action;
      var id = btn.dataset.id;
      if (action === 'edit-t') {
        openTestimonialModal(findTestimonial(id));
        return;
      }
      var apiAction = action === 'publish-t' ? 'publish' : action === 'unpublish-t' ? 'unpublish' : action === 'delete-t' ? 'delete' : null;
      if (!apiAction || !id) return;
      if (apiAction === 'delete' && !confirm('確定刪除此見證？')) return;
      btn.disabled = true;
      api.admin.testimonialAction(id, apiAction).then(function (res) {
        btn.disabled = false;
        if (res.error) { alert(res.error.message || res.error); return; }
        load(true, true);
      });
    });
  }

  function openTestimonialModal(t) {
    var isEdit = !!(t && t.id);
    var nameParts = splitTestimonialName(t);
    var imageUrl = isEdit ? (t.image_url || '') : '';
    var html =
      '<div class="qr-modal ai-modal" role="dialog" aria-modal="true">' +
        '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
        '<h3>' + (isEdit ? '編輯見證' : '新增見證') + '</h3>' +
        '<p class="ap-form-error" id="acFormError" hidden></p>' +
        '<form id="acTestimonialForm" class="ap-form" data-id="' + esc(isEdit ? t.id : '') + '">' +
          '<div class="ap-form-grid">' +
            '<label class="ap-field"><span>姓名' + reqStar() + '</span>' +
              '<div class="ap-name-row">' +
                '<input name="namePart" required maxlength="30" autocomplete="off" placeholder="姓氏或名字" value="' + esc(nameParts.part) + '">' +
                '<select name="honorific" aria-label="稱謂">' +
                  '<option value="小姐"' + (nameParts.honorific === '小姐' ? ' selected' : '') + '>小姐</option>' +
                  '<option value="先生"' + (nameParts.honorific === '先生' ? ' selected' : '') + '>先生</option>' +
                '</select>' +
              '</div></label>' +
            '<label class="ap-field"><span>分類' + reqStar() + '</span>' +
              '<select name="category" required>' + categoryOptions(isEdit ? t.category : '') + '</select></label>' +
            cityComboMarkup(isEdit ? t.city : '') +
            countryFieldMarkup(isEdit ? t.country : '', isEdit ? t.city : '') +
            '<label class="ap-field ap-field--full"><span>訂製款式圖片' + reqStar() + '</span>' +
              '<div id="acTestimonialImageUploadMount"></div>' +
              '<p class="ap-section-hint">JPG / PNG / WEBP，來源 ≤1MB；上傳後轉 WebP 並壓縮至 ≤500KB。前台顯示角色為「分類・城市／國家」。</p>' +
              '<input type="hidden" name="imageUrl" id="acTestimonialImageUrl" value="' + esc(imageUrl) + '">' +
            '</label>' +
            '<label class="ap-field ap-field--full"><span>見證內容（完整）' + reqStar() + '</span>' +
              '<textarea name="text" class="ap-textarea" rows="8" required placeholder="完整見證文案…">' + esc(isEdit ? t.text : '') + '</textarea></label>' +
            '<label class="ap-field ap-field--check"><input type="checkbox" name="isPublished"' + (!isEdit || t.is_published ? ' checked' : '') + '><span>發布</span></label>' +
          '</div>' +
          '<div class="ap-form-actions">' +
            '<button type="button" class="btn-sm" data-modal-close>取消</button>' +
            '<button type="submit" class="btn-sm btn-primary">' + (isEdit ? '儲存' : '建立') + '</button>' +
          '</div>' +
        '</form></div>';

    if (!window.AdminPanel || !window.AdminPanel.openModal) return;
    window.AdminPanel.openModal(html);
    var form = document.getElementById('acTestimonialForm');
    if (form) form.addEventListener('submit', submitTestimonial);
    bindCityCombo();
    syncCountryField(isEdit ? t.city : '');

    var urlInput = document.getElementById('acTestimonialImageUrl');
    if (window.AdminTables && window.AdminTables.renderImageUploadField) {
      var testimonialUploadMount = document.getElementById('acTestimonialImageUploadMount');
      if (testimonialUploadMount && urlInput) {
        window.AdminTables.renderImageUploadField(testimonialUploadMount, {
          value: imageUrl,
          onChange: function (url) {
            urlInput.value = url || '';
          },
          onUpload: function (file) {
            return api.admin.uploadTestimonial(file);
          },
          onValidationError: function (message) {
            alert(message);
          },
        });
      }
    }
  }

  function submitTestimonial(e) {
    e.preventDefault();
    var form = e.target;
    var fd = new FormData(form);
    var errEl = document.getElementById('acFormError');
    var id = form.dataset.id;
    var imageUrl = String(fd.get('imageUrl') || '').trim();
    var city = normalizeTaiwanCity(fd.get('city'));
    var country = city === '其他' ? String(fd.get('country') || '').trim() : '';
    var payload = {
      id: id || undefined,
      name: String(fd.get('namePart') || '').trim(),
      honorific: String(fd.get('honorific') || '小姐').trim(),
      category: String(fd.get('category') || '').trim(),
      city: city,
      country: country,
      text: String(fd.get('text') || '').trim(),
      imageUrl: imageUrl,
      isPublished: !!form.querySelector('[name="isPublished"]').checked,
    };
    if (!payload.name) {
      if (errEl) { errEl.textContent = '請填寫姓名'; errEl.hidden = false; }
      return;
    }
    if (!payload.category) {
      if (errEl) { errEl.textContent = '請選擇分類'; errEl.hidden = false; }
      return;
    }
    if (!payload.city || !isTaiwanCity(payload.city)) {
      if (errEl) { errEl.textContent = '請從清單選擇城市（縣市）'; errEl.hidden = false; }
      return;
    }
    if (payload.city === '其他' && !payload.country) {
      if (errEl) { errEl.textContent = '請填寫國家 / 地區'; errEl.hidden = false; }
      var countryEl = document.getElementById('acCountryInput');
      if (countryEl) countryEl.focus();
      return;
    }
    if (!payload.imageUrl) {
      if (errEl) { errEl.textContent = '請上傳圖片'; errEl.hidden = false; }
      return;
    }
    if (!payload.text) {
      if (errEl) { errEl.textContent = '請填寫見證內容'; errEl.hidden = false; }
      return;
    }
    if (errEl) errEl.hidden = true;
    var req = id ? api.admin.updateTestimonial(payload) : api.admin.createTestimonial(payload);
    req.then(function (res) {
      if (res.error) {
        if (errEl) { errEl.textContent = res.error.message || res.error; errEl.hidden = false; }
        else alert(res.error);
        return;
      }
      if (window.AdminPanel.closeModal) window.AdminPanel.closeModal();
      load(true, true);
    });
  }

  function renderFaq(body) {
    renderContentReact(body);
  }

  function bindFaqAction(btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var action = btn.dataset.action;
      var id = btn.dataset.id;
      if (action === 'edit-f') {
        openFaqModal(findFaq(id));
        return;
      }
      var apiAction = action === 'publish-f' ? 'publish' : action === 'unpublish-f' ? 'unpublish' : action === 'delete-f' ? 'delete' : null;
      if (!apiAction || !id) return;
      if (apiAction === 'delete' && !confirm('確定刪除此 FAQ？')) return;
      btn.disabled = true;
      api.admin.faqAction(id, apiAction).then(function (res) {
        btn.disabled = false;
        if (res.error) { alert(res.error.message || res.error); return; }
        load(true, true);
      });
    });
  }

  function openFaqModal(f) {
    var isEdit = !!(f && f.id);
    var preferredCat = isEdit ? f.category_id : _faqCategoryId;
    var opts = _faqCategories.map(function (c) {
      var sel = preferredCat === c.id ? ' selected' : '';
      return '<option value="' + esc(c.id) + '"' + sel + '>' + esc(c.title) + '</option>';
    }).join('');

    var html =
      '<div class="qr-modal ai-modal" role="dialog" aria-modal="true">' +
        '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
        '<h3>' + (isEdit ? '編輯 FAQ' : '新增 FAQ') + '</h3>' +
        '<p class="ap-form-error" id="acFormError" hidden></p>' +
        '<form id="acFaqForm" class="ap-form" data-id="' + esc(isEdit ? f.id : '') + '">' +
          '<div class="ap-form-grid">' +
            '<label class="ap-field"><span>分類</span><select name="categoryId" required>' + opts + '</select></label>' +
            '<label class="ap-field"><span>排序</span><input type="number" name="sortOrder" value="' + esc(String(isEdit ? f.sort_order : 0)) + '"></label>' +
            '<label class="ap-field ap-field--full"><span>問題</span><input name="question" required value="' + esc(isEdit ? f.question : '') + '"></label>' +
            '<label class="ap-field ap-field--full"><span>回答（完整）</span><textarea name="answer" class="ap-textarea" rows="8" required>' + esc(isEdit ? f.answer : '') + '</textarea></label>' +
            '<label class="ap-field ap-field--check"><input type="checkbox" name="isPublished"' + (!isEdit || f.is_published ? ' checked' : '') + '><span>發布</span></label>' +
            '<label class="ap-field ap-field--check"><input type="checkbox" name="showInTeaser"' + (isEdit && f.show_in_teaser ? ' checked' : '') + '><span>首頁 FAQ 精選</span></label>' +
          '</div>' +
          '<div class="ap-form-actions">' +
            '<button type="button" class="btn-sm" data-modal-close>取消</button>' +
            '<button type="submit" class="btn-sm btn-primary">' + (isEdit ? '儲存' : '建立') + '</button>' +
          '</div>' +
        '</form></div>';

    if (!window.AdminPanel || !window.AdminPanel.openModal) return;
    window.AdminPanel.openModal(html);
    var form = document.getElementById('acFaqForm');
    if (form) form.addEventListener('submit', submitFaq);
  }

  function submitFaq(e) {
    e.preventDefault();
    var form = e.target;
    var fd = new FormData(form);
    var errEl = document.getElementById('acFormError');
    var id = form.dataset.id;
    var payload = {
      id: id || undefined,
      categoryId: String(fd.get('categoryId') || '').trim(),
      question: String(fd.get('question') || '').trim(),
      answer: String(fd.get('answer') || '').trim(),
      sortOrder: fd.get('sortOrder'),
      isPublished: !!form.querySelector('[name="isPublished"]').checked,
      showInTeaser: !!form.querySelector('[name="showInTeaser"]').checked,
    };
    var req = id ? api.admin.updateFaqItem(payload) : api.admin.createFaqItem(payload);
    req.then(function (res) {
      if (res.error) {
        if (errEl) { errEl.textContent = res.error.message || res.error; errEl.hidden = false; }
        else alert(res.error);
        return;
      }
      if (window.AdminPanel.closeModal) window.AdminPanel.closeModal();
      load(true, true);
    });
  }

  function listPageOpts() {
    return { page: _pageIndex + 1, pageSize: _pageSize };
  }

  function load(silent, force) {
    var tab = _tab === 'copy' ? 'pages' : _tab;
    if (_loadedTabs[tab] && !force) return;
    if (!silent) {
      root.setAttribute('aria-busy', 'true');
      root.classList.add('skel-panel');
      root.innerHTML = window.SkeletonUI && window.SkeletonUI.contentShell
        ? window.SkeletonUI.contentShell()
        : '<p class="adx-loading-inline">載入內容中…</p>';
    }
    /* 只抓目前分頁的資料集；其他分頁第一次切過去時再各自載入。 */
    var opts = listPageOpts();
    var mainP = null;
    if (tab === 'testimonials') mainP = api.admin.getTestimonials(opts);
    else if (tab === 'faq') mainP = api.admin.getFaqItems(opts);
    else if (tab === 'journal') mainP = api.admin.getJournalPosts(opts);
    else if (tab === 'banners') mainP = api.admin.getBanners(opts);
    else if (tab === 'page-images') {
      var pageImageOpts = Object.assign({}, opts);
      if (_pageImagePage) pageImageOpts.page_key = _pageImagePage;
      mainP = api.admin.getPageImages(pageImageOpts);
    }
    var pageImageKeysP = _pageImagePageOptions.length
      ? Promise.resolve(null)
      : api.admin.getPageImages({ page: 1, pageSize: 100 });
    Promise.all([mainP || Promise.resolve(null), pageImageKeysP]).then(function (results) {
      var res = results[0];
      var keysRes = results[1];
      // Soft-fail journal until backend routes land (parallel Phase 1).
      if (res && res.error && tab !== 'journal') {
        root.innerHTML =
          '<p class="note warn">載入失敗：' +
          esc(res.error.message || res.error) +
          '</p>';
        root.removeAttribute('aria-busy');
        return;
      }
      if (res) {
        if (tab === 'testimonials') {
          _testimonials = res.testimonials || [];
          _totals.testimonials = typeof res.total === 'number' ? res.total : _testimonials.length;
        } else if (tab === 'faq') {
          _faqItems = res.items || [];
          _faqCategories = res.categories || [];
          _totals.faq = typeof res.total === 'number' ? res.total : _faqItems.length;
        } else if (tab === 'journal') {
          _journalError = res.error ? String(res.error.message || res.error) : '';
          _journalPosts = (!_journalError && (res.posts || res.journal_posts)) || [];
          _totals.journal = typeof res.total === 'number' ? res.total : _journalPosts.length;
        } else if (tab === 'page-images') {
          _pageImages = res.pageImages || [];
          rememberPageImagePages(_pageImages);
          _totals['page-images'] = typeof res.total === 'number' ? res.total : _pageImages.length;
        } else if (tab === 'banners') {
          _banners = res.banners || [];
          _totals.banners = typeof res.total === 'number' ? res.total : _banners.length;
        }
      }
      if (keysRes && !keysRes.error) rememberPageImagePages(keysRes.pageImages || []);
      _loadedTabs[tab] = true;
      root.removeAttribute('aria-busy');
      root.classList.remove('skel-panel');
      renderShell();
    });
  }

  function ensureLoaded() {
    /* admin-tables.js 按需載入：bundle 就緒後再取資料渲染表格。 */
    if (!window.AdminTables && typeof window.__adminLoadTables === 'function') {
      window.__adminLoadTables().then(
        function () { ensureLoaded(); },
        function () { load(false); }
      );
      return;
    }
    load(_loadedTabs[_tab === 'copy' ? 'pages' : _tab] ? true : false);
  }

  window.AdminContentPanel = { load: load, ensureLoaded: ensureLoaded };

  document.querySelectorAll('.side-nav button[data-panel="content"]').forEach(function (btn) {
    btn.addEventListener('click', ensureLoaded);
  });

  if (root && window.SkeletonUI && !_loadedTabs[_tab] && root.querySelector('.skel-line')) {
    root.innerHTML = window.SkeletonUI.contentShell
      ? window.SkeletonUI.contentShell()
      : root.innerHTML;
  }

  var panel = document.getElementById('panel-content');
  if (panel && panel.classList.contains('is-active')) ensureLoaded();
})();
