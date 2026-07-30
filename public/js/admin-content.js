/* 銘印鑽石｜首頁圖片與內容管理 */
(function () {
  'use strict';

  var api = window.imprintAPI;
  if (!api || !api.admin) return;

  var root = document.getElementById('contentRoot');
  if (!root) return;

  var _loaded = false;
  var _tab = 'banners';
  var _pageImagePage = '';
  var _testimonials = [];
  var _faqItems = [];
  var _faqCategories = [];
  var _faqCategoryId = '';
  var _banners = [];
  var _pageImages = [];

  var PAGE_LINKS = [
    { value: '/', label: '首頁' },
    { value: '/shop/calculator/', label: '客製試算' },
    { value: '/price.html', label: 'DNA 鑽石價格' },
    { value: '/gold-price.html', label: '台銀金價' },
    { value: '/series.html', label: '系列總覽' },
    { value: '/what-is-dna-diamond.html', label: 'DNA 鑽石的誕生' },
    { value: '/faq.html', label: '常見問題' },
    { value: '/about.html', label: '品牌故事' },
    { value: '/stories.html', label: '客戶見證' },
    { value: '/contact.html', label: '聯絡我們' },
    { value: '/track-order.html', label: '查詢訂製進度' },
    { value: '/jewelry/', label: '飾品訂製' },
    { value: '#home-poem', label: '首頁・詩文區塊' },
    { value: '#series', label: '首頁・系列區塊' },
    { value: 'https://lin.ee/ktVBtmx', label: '官方 LINE' },
  ];

  var TESTIMONIAL_CATEGORIES = [
    '寵物鑽石', '結髮鑽石', '生命鑽石', '毛髮鑽石', '全家福鑽石', '初生鑽石',
  ];

  var TAIWAN_CITIES = [
    '台北市', '新北市', '桃園市', '台中市', '台南市', '高雄市',
    '基隆市', '新竹市', '新竹縣', '苗栗縣', '彰化縣', '南投縣',
    '雲林縣', '嘉義市', '嘉義縣', '屏東縣', '宜蘭縣', '花蓮縣',
    '台東縣', '澎湖縣', '金門縣', '連江縣',
  ];

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

  function cityDatalistOptions() {
    return TAIWAN_CITIES.map(function (c) {
      return '<option value="' + esc(c) + '">';
    }).join('');
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
    var seen = {};
    return _pageImages.reduce(function (pages, row) {
      if (!seen[row.page_key]) {
        seen[row.page_key] = true;
        pages.push({ value: row.page_key, label: row.label || row.page_key });
      }
      return pages;
    }, []);
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
        renderShell();
      });
    });

    root.querySelectorAll('[data-page-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var pageKey = btn.dataset.pageTab;
        if (!pageKey || pageKey === _pageImagePage) return;
        _pageImagePage = pageKey;
        renderShell();
      });
    });

    var body = document.getElementById('contentPanelBody');
    if (_tab === 'pages') renderCmsPages(body);
    else if (_tab === 'faq') {
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
      getMedia: function () { return api.admin.getCmsMedia(); },
      getFaqCategories: function () { return api.admin.getFaqCategories(); },
      uploadMedia: function (file) { return api.admin.uploadCmsMedia(file); },
      deleteMedia: function (id) { return api.admin.cmsMediaAction(id, 'delete'); },
      uploadPageImage: function (file) { return api.admin.uploadPageImage(file); },
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
      getCopySlots: function () { return api.admin.getPageCopySlots(); },
      updateCopySlot: function (fields) { return api.admin.updatePageCopySlot(fields); },
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
      };
    });

    var testimonialRows = _testimonials.slice().sort(function (a, b) {
      return Number(a.sort_order || 0) - Number(b.sort_order || 0);
    }).map(function (t) {
      return {
        id: String(t.id),
        name: t.name || '',
        category: t.category || '',
        city: t.city || '',
        text: t.text || '',
        sort_order: Number(t.sort_order || 0),
        is_published: !!t.is_published,
        image_url: t.image_url || '',
      };
    });

    var pageImageRows = _pageImages
      .filter(function (p) {
        return p.page_key === _pageImagePage;
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
        if (action === 'delete') {
          var label = _tab === 'banners' ? '首頁圖片' : _tab === 'testimonials' ? '見證' : 'FAQ';
          if (!confirm('確定刪除此' + label + '？')) return;
        }
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
      },
      onClose: close,
      onSaved: function () {
        close();
        load(true, true);
      },
      uploadImage: function (file) {
        return api.admin.uploadPageImage(file);
      },
      updatePageImage: function (fields) {
        return api.admin.updatePageImage(fields);
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
            '<label class="ap-field"><span>城市' + reqStar() + '</span>' +
              '<input name="city" list="acTaiwanCities" required autocomplete="off" placeholder="輸入或選擇縣市" value="' + esc(isEdit ? t.city : '') + '">' +
              '<datalist id="acTaiwanCities">' + cityDatalistOptions() + '</datalist></label>' +
            '<label class="ap-field ap-field--full"><span>訂製款式圖片' + reqStar() + '</span>' +
              '<div id="acTestimonialImageUploadMount"></div>' +
              '<p class="ap-section-hint">PNG / JPG / WEBP，1MB 內。前台顯示角色為「分類・城市」。</p>' +
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
    var payload = {
      id: id || undefined,
      name: String(fd.get('namePart') || '').trim(),
      honorific: String(fd.get('honorific') || '小姐').trim(),
      category: String(fd.get('category') || '').trim(),
      city: String(fd.get('city') || '').trim(),
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
    if (!payload.city) {
      if (errEl) { errEl.textContent = '請選擇城市'; errEl.hidden = false; }
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

  function load(silent, force) {
    if (_loaded && !force) return;
    if (!silent) {
      root.setAttribute('aria-busy', 'true');
      root.classList.add('skel-panel');
      root.innerHTML = window.SkeletonUI && window.SkeletonUI.contentShell
        ? window.SkeletonUI.contentShell()
        : '<p class="adx-loading-inline">載入內容中…</p>';
    }
    Promise.all([
      api.admin.getTestimonials(),
      api.admin.getFaqItems(),
      api.admin.getBanners(),
      api.admin.getPageImages(),
    ]).then(function (results) {
      var tRes = results[0];
      var fRes = results[1];
      var bRes = results[2];
      var pRes = results[3];
      if (tRes.error || fRes.error || bRes.error || pRes.error) {
        root.innerHTML =
          '<p class="note warn">載入失敗：' +
          esc(tRes.error || fRes.error || bRes.error || pRes.error) +
          '</p>';
        root.removeAttribute('aria-busy');
        return;
      }
      _testimonials = tRes.testimonials || [];
      _faqItems = fRes.items || [];
      _faqCategories = fRes.categories || [];
      _banners = bRes.banners || [];
      _pageImages = (pRes.pageImages || []).filter(function (row) {
        var key = String(row.page_key || '');
        var group = String(row.group_key || '');
        if (key.indexOf('/shop/') === 0) return false;
        if (key === '/jewelry/' || key.indexOf('/jewelry/') === 0) return false;
        if (group === 'jewelry') return false;
        return true;
      });
      _loaded = true;
      root.removeAttribute('aria-busy');
      root.classList.remove('skel-panel');
      renderShell();
    });
  }

  function ensureLoaded() {
    load(_loaded);
  }

  window.AdminContentPanel = { load: load, ensureLoaded: ensureLoaded };

  document.querySelectorAll('.side-nav button[data-panel="content"]').forEach(function (btn) {
    btn.addEventListener('click', ensureLoaded);
  });

  if (root && window.SkeletonUI && !_loaded && root.querySelector('.skel-line')) {
    root.innerHTML = window.SkeletonUI.contentShell
      ? window.SkeletonUI.contentShell()
      : root.innerHTML;
  }

  var panel = document.getElementById('panel-content');
  if (panel && panel.classList.contains('is-active')) ensureLoaded();
})();
