/* 銘印鑽石｜商品上架管理 */
(function () {
  'use strict';

  var api = window.imprintAPI;
  if (!api || !api.admin) return;

  var CATEGORY_ORDER = ['pendant', 'ring', 'earring', 'bracelet', 'chain'];
  var GOLDS = ['9k', '14k', '18k', 'pt950', 's925'];
  var CARATS = [
    '0.1', '0.2', '0.3', '0.5', '0.6', '0.7', '0.8', '0.9', '1.0',
    '1.5', '2.0', '3.0',
  ];
  var CHAIN_CARATS = ['1.0mm', '1.5mm', '2.0mm', '2.5mm', '3.0mm'];
  var CHAIN_LENGTHS_CM = [36, 41, 46, 51, 61, 76, 80];
  var COLORS = ['white', 'yellow', 'rose'];
  var GOLD_LABELS = { '9k': '9K', '14k': '14K', '18k': '18K', 'pt950': 'PT950', 's925': 'S925' };
  // 蠟重(錢) × factor → 成品金重(錢)；試算頁下單時以後端 app/pricing.py 的同一份係數為準，這裡僅供上架時預覽估算。
  var WAX_TO_METAL_CHIN = { '9k': 11.5, '14k': 14.0, '18k': 16.0, 'pt950': 24.0, 's925': 11.0 };
  var COLOR_LABELS = { white: '白金', yellow: '黃金', rose: '玫瑰金' };
  var METAL_SLOT_OPTIONS = [
    { value: 'white', label: '白金' },
    { value: 'yellow', label: '黃金' },
    { value: 'rose', label: '玫瑰金' },
  ];
  var DIAMOND_SLOT_OPTIONS = [
    { value: 'white', label: '白鑽' },
    { value: 'yellow', label: '黃鑽' },
    { value: 'blue', label: '藍鑽' },
    { value: 'pink', label: '粉鑽' },
  ];
  var METAL_SLOT_VALUES = METAL_SLOT_OPTIONS.map(function (o) { return o.value; });
  var DIAMOND_SLOT_VALUES = DIAMOND_SLOT_OPTIONS.map(function (o) { return o.value; });

  // Match server _ALLOWED_IMAGE_EXT / UI copy: PNG / JPG / WEBP, 1MB.
  var IMAGE_ACCEPT = 'image/png,image/jpeg,image/webp';
  var IMAGE_MIME_OK = { 'image/png': 1, 'image/jpeg': 1, 'image/webp': 1 };
  var IMAGE_EXT_OK = { '.png': 1, '.jpg': 1, '.jpeg': 1, '.webp': 1 };
  var MAX_IMAGE_BYTES = 1 * 1024 * 1024;

  function imageFileExt(name) {
    var m = String(name || '').toLowerCase().match(/\.[a-z0-9]+$/);
    return m ? m[0] : '';
  }

  function isAllowedImageFile(file) {
    if (!file) return false;
    var ext = imageFileExt(file.name);
    if (!IMAGE_EXT_OK[ext]) return false;
    if (file.type && !IMAGE_MIME_OK[file.type]) return false;
    return true;
  }

  /** Returns error string, or '' if all files ok. */
  function validateImageFiles(files) {
    var list = Array.from(files || []);
    if (!list.length) return '';
    for (var i = 0; i < list.length; i++) {
      if (!isAllowedImageFile(list[i])) return '僅支援 PNG / JPG / WEBP';
      if (list[i].size > MAX_IMAGE_BYTES) return '圖片需小於 1MB';
    }
    return '';
  }

  // Image slots are metal × diamond. Legacy 3-part keys (metal-diamond-chainMetal)
  // still parse for folding into metal-diamond; calculator no longer picks chain color.
  function buildSlotKey(metal, diamond, chainMetal) {
    return String(metal) + '-' + String(diamond) + (chainMetal ? '-' + chainMetal : '');
  }

  function parseSlotKey(key) {
    var parts = String(key || '').split('-');
    if (parts.length >= 3 && METAL_SLOT_VALUES.indexOf(parts[0]) >= 0
      && DIAMOND_SLOT_VALUES.indexOf(parts[1]) >= 0 && METAL_SLOT_VALUES.indexOf(parts[2]) >= 0) {
      return { metal: parts[0], diamond: parts[1], chainMetal: parts[2] };
    }
    if (parts.length >= 2 && METAL_SLOT_VALUES.indexOf(parts[0]) >= 0 && DIAMOND_SLOT_VALUES.indexOf(parts[1]) >= 0) {
      return { metal: parts[0], diamond: parts[1], chainMetal: null };
    }
    if (METAL_SLOT_VALUES.indexOf(key) >= 0) return { metal: key, diamond: 'white', chainMetal: null };
    return null;
  }

  function allPresetSlotKeys() {
    var keys = [];
    METAL_SLOT_VALUES.forEach(function (metal) {
      DIAMOND_SLOT_VALUES.forEach(function (diamond) {
        keys.push(buildSlotKey(metal, diamond, null));
      });
    });
    return keys;
  }

  /** Calculator image axes per category (matches shop.js preview lookup). */
  function presetSlotKeysForCategory(category) {
    if (category === 'chain') {
      return METAL_SLOT_VALUES.map(function (metal) {
        return buildSlotKey(metal, 'white', null);
      });
    }
    // Pendant matches other jewelry: metal × diamond only (no chain-metal axis).
    return allPresetSlotKeys();
  }

  var root = document.getElementById('productsRoot');
  if (!root) return;

  var state = {
    products: [],
    categoryLabels: {},
    categories: [],
    categoryOrder: [],
    chainCatalog: null,
    activeTab: 'cat-pendant',
    editingId: null,
    view: 'list',
  };
  var _loaded = false;
  var _loading = false;
  var _slotCounter = 0;
  var LOAD_TIMEOUT_MS = 25000;
  var AUTOSAVE_MS = 1500;
  var _imageBusy = 0;
  var _autosave = {
    timer: null,
    waitTimer: null,
    inFlight: false,
    queued: false,
    form: null,
    ctx: null,
  };

  function esc(s) {
    return window.AdminPanel && window.AdminPanel.escapeHtml
      ? window.AdminPanel.escapeHtml(s)
      : String(s == null ? '' : s);
  }

  function imageUrl(path, color) {
    if (window.AdminImageUrls && window.AdminImageUrls.productPhoto) {
      return window.AdminImageUrls.productPhoto(path, color);
    }
    return window.AdminImageUrls ? window.AdminImageUrls.resolve(path) : path;
  }

  /** blob:/data: are tab-local — never persist or preview as SoT. */
  function isBrowserLocalImageUrl(url) {
    return /^(?:blob:|data:)/i.test(String(url || '').trim());
  }

  /** Seed SVG /styles paths 404 — not real uploads. */
  function isDeadCatalogPlaceholder(url) {
    var path = String(url || '').split('?', 1)[0].toLowerCase();
    return /\.svg$/i.test(path) || /\/images\/shop\/styles\//i.test(path);
  }

  /** Bundled letter-SKU stock under shop-product/ — never treat as uploaded photos. */
  function isAutoStockProductImage(url) {
    var path = String(url || '').split('?', 1)[0].replace(/\\/g, '/').toLowerCase();
    return /(?:^|\/)(?:static\/)?images\/shop-product(?:\/|$)/.test(path);
  }

  /** Persistable URL for editor data-url + SQL (real uploads only). */
  function persistableImageUrl(path, color) {
    if (!path || isBrowserLocalImageUrl(path)) return '';
    if (isAutoStockProductImage(path)) return '';
    var resolved = imageUrl(path, color) || path;
    if (
      !resolved
      || isBrowserLocalImageUrl(resolved)
      || isDeadCatalogPlaceholder(resolved)
      || isAutoStockProductImage(resolved)
    ) {
      return '';
    }
    return resolved;
  }

  function imageCoversDefaultColor(imageColor, defaultColor) {
    var key = String(imageColor || '').toLowerCase();
    var def = String(defaultColor || '').toLowerCase();
    if (!key || COLORS.indexOf(def) < 0) return false;
    return key === def || key.indexOf(def + '-') === 0;
  }

  function productThumb(product) {
    var images = product.images || [];
    var def = product.default_color || 'white';
    var match = images.find(function (img) { return imageCoversDefaultColor(img.color, def); }) || images[0];
    if (match) {
      var thumb = window.AdminImageUrls && window.AdminImageUrls.productThumbnail
        ? window.AdminImageUrls.productThumbnail(match.file_path, def)
        : imageUrl(match.file_path, def);
      // Never invent shop-product letter thumbs for products without uploads.
      return persistableImageUrl(thumb || match.file_path, def) || '';
    }
    return '';
  }

  function productStatus(product) {
    if (product.is_published) return { label: '已上架', cls: 'ap-status-badge--live' };
    if (product.first_published_at) return { label: '已下架', cls: 'ap-status-badge--offline' };
    return { label: '草稿', cls: 'ap-status-badge--draft' };
  }

  function publishReady(product) {
    var variants = product.variants || [];
    var images = product.images || [];
    if (!variants.length) return { ok: false, reason: '請先新增至少一個款式選項' };
    if (!images.length) return { ok: false, reason: '請先上傳至少一張商品照片' };
    var def = product.default_color || 'white';
    if (!images.some(function (img) { return imageCoversDefaultColor(img.color, def); })) {
      return { ok: false, reason: '預設顏色必須至少有一張商品照片' };
    }
    return { ok: true, reason: '' };
  }

  function previewUrl(product) {
    return '/shop/calculator/?preview=1&category=' + encodeURIComponent(product.category)
      + '&product=' + encodeURIComponent(product.id);
  }

  function categoryOrderList() {
    return (state.categoryOrder && state.categoryOrder.length) ? state.categoryOrder : CATEGORY_ORDER;
  }

  function categoryInfo(slug) {
    return (state.categories || []).find(function (c) { return c.slug === slug; }) || null;
  }

  function categoryThumbUrl(slug) {
    var info = categoryInfo(slug);
    if (info && info.thumbUrl) return info.thumbUrl;
    if (info && info.thumb_path) return imageUrl(info.thumb_path);
    return window.AdminImageUrls ? window.AdminImageUrls.categoryFallback(slug) : '';
  }

  function publishedCountInCategory(cat) {
    return productsInCategory(cat).filter(function (p) { return p.is_published; }).length;
  }

  function categoryPanelHtml() {
    var cat = state.activeTab.replace('cat-', '');
    var label = state.categoryLabels[cat] || cat;
    var published = publishedCountInCategory(cat);
    var thumb = categoryThumbUrl(cat);
    return (
      '<div class="ap-category-panel" id="apCategoryPanel">' +
        '<div class="ap-category-panel-inner">' +
          '<div class="ap-category-panel-text">' +
            '<h4 class="ap-section-title ap-section-title--inline">' + esc(label) + ' · 試算頁 Step 1 品項圖</h4>' +
            '<p class="ap-section-hint">此圖顯示於客製試算「選品項」步驟。' +
            '品項需至少有一件<strong>已上架</strong>商品才會出現在試算頁' +
            (published ? '（目前 ' + published + ' 件已上架）。' : '（尚無已上架商品，試算頁不會顯示此品項）。') +
            '</p>' +
          '</div>' +
          '<div class="ap-category-thumb-block">' +
            '<div class="ap-category-thumb-preview">' +
              (thumb
                ? '<img src="' + esc(thumb) + '" alt="">'
                : '<span class="ap-category-thumb-empty">預設圖</span>') +
            '</div>' +
            '<label class="btn-sm ap-category-thumb-upload">' +
              '更換圖片' +
              '<input type="file" accept="' + IMAGE_ACCEPT + '" hidden id="apCategoryThumbInput">' +
            '</label>' +
          '</div>' +
          '<button type="button" class="btn-sm ap-category-delete-btn" id="apDeleteCategoryBtn" data-slug="' + esc(cat) + '" data-label="' + esc(label) + '">刪除此品項</button>' +
        '</div>' +
      '</div>'
    );
  }

  function deleteCategoryDialogHtml() {
    return (
      '<dialog id="apDeleteCategoryDialog" class="ap-delete-dialog">' +
        '<form method="dialog" id="apDeleteCategoryForm">' +
          '<h3>刪除品項</h3><p id="apDeleteCategoryTarget"></p>' +
          '<p class="ap-hint">刪除後無法復原。若此品項下仍有商品，需先刪除或搬移商品才能刪除品項。</p>' +
          '<p class="ap-form-error" id="apDeleteCategoryError" hidden></p>' +
          '<div class="ap-delete-actions">' +
            '<button type="button" class="btn-sm" id="apDeleteCategoryCancel">取消</button>' +
            '<button type="submit" class="btn-sm btn-primary">確認刪除</button>' +
          '</div>' +
        '</form>' +
      '</dialog>'
    );
  }

  function addCategoryDialogHtml() {
    return (
      '<dialog id="apAddCategoryDialog" class="ap-delete-dialog">' +
        '<form method="dialog" id="apAddCategoryForm">' +
          '<h3>新增品項</h3>' +
          '<label class="ap-add-cat-label"><span>品項名稱</span>' +
            '<input id="apNewCategoryName" maxlength="50" autocomplete="off" required placeholder="例如：胸針">' +
          '</label>' +
          '<p class="ap-hint">建立後可在此品項下新增商品。試算頁需有至少一件已上架商品才會顯示此品項。</p>' +
          '<p class="ap-form-error" id="apAddCategoryError" hidden></p>' +
          '<div class="ap-delete-actions">' +
            '<button type="button" class="btn-sm" id="apAddCategoryCancel">取消</button>' +
            '<button type="submit" class="btn-sm btn-primary">建立</button>' +
          '</div>' +
        '</form>' +
      '</dialog>'
    );
  }

  function chainCatalogTypes() {
    var cat = state.chainCatalog;
    return (cat && cat.types) || {};
  }

  function defaultChainType() {
    return (state.chainCatalog && state.chainCatalog.defaultType) || 'douyuan';
  }

  function resolveChainType(raw) {
    var types = chainCatalogTypes();
    if (raw && types[raw]) return raw;
    return defaultChainType();
  }

  function chainTypeWaxTable(chainType) {
    var entry = chainCatalogTypes()[resolveChainType(chainType)];
    return (entry && entry.lengthWeights) || {};
  }

  function chainTypeThicknesses(chainType) {
    var entry = chainCatalogTypes()[resolveChainType(chainType)];
    if (entry && entry.thicknesses && entry.thicknesses.length) return entry.thicknesses;
    return CHAIN_CARATS;
  }

  function chainLengthsCm() {
    var fromCat = state.chainCatalog && state.chainCatalog.lengthsCm;
    if (fromCat && fromCat.length) {
      return fromCat.map(function (n) { return parseInt(n, 10); }).filter(function (n) {
        return Number.isFinite(n);
      });
    }
    return CHAIN_LENGTHS_CM.slice();
  }

  function getFormChainType(form) {
    var sel = form && form.querySelector('[name="chainType"]');
    return resolveChainType(sel ? sel.value : null);
  }

  function caratsFor(category, chainType) {
    return category === 'chain' ? chainTypeThicknesses(chainType) : CARATS;
  }

  function productsInCategory(cat) {
    return state.products.filter(function (p) { return p.category === cat; });
  }

  function setRoot(html) {
    root.innerHTML = html;
    root.removeAttribute('aria-busy');
    root.classList.remove('ap-skeleton-shell');
  }

  function loadingSkeletonHtml() {
    return window.SkeletonUI ? window.SkeletonUI.productsShell() : '';
  }

  function tableAreaSkeletonHtml() {
    return window.SkeletonUI
      ? window.SkeletonUI.table({ headers: ['', '縮圖', '品項', '名稱', '狀態', '操作'], rows: 4, label: '載入表格中' })
      : '';
  }

  function showLoadingSkeleton() {
    unmountProductsTable();
    root.classList.add('ap-skeleton-shell');
    root.setAttribute('aria-busy', 'true');
    root.setAttribute('aria-label', '載入商品中');
    root.innerHTML = loadingSkeletonHtml();
  }

  function unmountProductsTable() {
    if (!window.AdminTables) return;
    var el = document.getElementById('apProductsTableRoot');
    if (el) window.AdminTables.unmount(el);
  }

  function renderShell() {
    unmountProductsTable();
    state.view = 'list';
    var tabs = categoryOrderList().map(function (cat) {
      var label = state.categoryLabels[cat] || cat;
      var count = productsInCategory(cat).length;
      var active = state.activeTab === 'cat-' + cat;
      return '<button type="button" class="ap-tab-btn' + (active ? ' is-active' : '') + '" data-tab="cat-' + cat + '" role="tab" aria-selected="' + (active ? 'true' : 'false') + '">' +
        esc(label) + '<span class="ap-tab-count">' + count + '</span></button>';
    }).join('');
    tabs += '<button type="button" class="ap-tab-btn ap-tab-btn--add" id="apAddCategory" title="新增品項" aria-label="新增品項">+</button>';

    setRoot(
      '<p class="note">管理商品款式、金屬選項與照片。上架後會顯示於客製試算頁；拖曳列可調整排序。</p>' +
      '<p class="note ap-memorial-note">紀念鑽石系列（滿月／寵物／結髮／全家福／生命鑽石）為試算頁固定款式，不在此商品 CRUD 管理；價格依克拉試算。</p>' +
      '<div class="ap-toolbar"><button type="button" class="btn-sm btn-primary" id="btnNewProduct">+ 新增商品</button></div>' +
      '<div class="ap-category-tabs" role="tablist">' + tabs + '</div>' +
      categoryPanelHtml() +
      '<div class="ap-table-root" id="apProductsTableRoot">' + tableAreaSkeletonHtml() + '</div>' +
      '<dialog id="apDeleteDialog" class="ap-delete-dialog"><form method="dialog" id="apDeleteForm">' +
        '<h3>刪除商品</h3><p id="apDeleteTarget"></p>' +
        '<p class="ap-hint">刪除後無法復原，若已有訂單引用建議改為下架。</p>' +
        '<div class="ap-delete-actions">' +
          '<button type="button" class="btn-sm" id="apDeleteCancel">取消</button>' +
          '<button type="submit" class="btn-sm btn-primary">確認刪除</button>' +
        '</div></form></dialog>' +
      addCategoryDialogHtml() +
      deleteCategoryDialogHtml()
    );
    bindShellEvents();
    renderActiveCategoryTable();
  }

  function toProductTableRow(product) {
    var status = productStatus(product);
    var ready = publishReady(product);
    return {
      id: product.id,
      category: product.category,
      categoryLabel: state.categoryLabels[product.category] || product.category,
      name: product.name_zh,
      nameEn: product.name_en || '',
      thumbUrl: productThumb(product) || '',
      thumbFallback: window.AdminImageUrls ? window.AdminImageUrls.categoryFallback(product.category) : '',
      statusLabel: status.label,
      statusClass: status.cls,
      previewUrl: previewUrl(product),
      publishAction: product.is_published ? 'unpublish' : 'publish',
      publishLabel: product.is_published ? '下架' : '上架',
      publishDisabled: !product.is_published && !ready.ok,
      publishDisabledReason: ready.reason,
      publishPrimary: !product.is_published && ready.ok,
    };
  }

  function apiError(data) {
    return (api && api.apiErrorMessage) ? api.apiErrorMessage(data) : (data && data.error) || '未知錯誤';
  }

  function whenAdminTablesReady(fn, tries) {
    tries = tries == null ? 120 : tries;
    if (window.AdminTables) {
      fn();
      return;
    }
    if (tries <= 0) {
      var container = document.getElementById('apProductsTableRoot');
      if (container) {
        container.innerHTML = '<p class="ap-empty">載入失敗：表格元件未載入，請重新整理頁面</p>';
      }
      return;
    }
    setTimeout(function () { whenAdminTablesReady(fn, tries - 1); }, 50);
  }

  /** Wait for ProductImageCropModal island (module may load after admin-products.js). */
  function whenProductCropReady(fn, tries) {
    tries = tries == null ? 120 : tries;
    if (window.AdminTables && window.AdminTables.renderProductImageCropModal) {
      fn(true);
      return;
    }
    if (tries <= 0) {
      fn(false);
      return;
    }
    setTimeout(function () { whenProductCropReady(fn, tries - 1); }, 50);
  }

  function renderActiveCategoryTable() {
    var container = document.getElementById('apProductsTableRoot');
    if (!container) return;
    whenAdminTablesReady(function () {
      var cat = state.activeTab.replace('cat-', '');
      window.AdminTables.renderProductsTable(container, {
        rows: productsInCategory(cat).map(toProductTableRow),
        emptyLabel: '此品項尚無商品。',
        onRendered: bindProductRowEvents,
      });
    });
  }

  function bindShellEvents() {
    root.querySelectorAll('.ap-tab-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        state.activeTab = btn.dataset.tab;
        root.querySelectorAll('.ap-tab-btn').forEach(function (b) {
          var active = b.dataset.tab === state.activeTab;
          b.classList.toggle('is-active', active);
          b.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        renderActiveCategoryTable();
        refreshCategoryPanel();
      });
    });

    var addCatBtn = document.getElementById('apAddCategory');
    if (addCatBtn) addCatBtn.addEventListener('click', openAddCategoryDialog);

    bindCategoryThumbUpload();
    bindCategoryDeleteButton();
    bindAddCategoryDialog();
    bindDeleteCategoryDialog();

    var newBtn = document.getElementById('btnNewProduct');
    if (newBtn) {
      newBtn.addEventListener('click', function () {
        var cat = state.activeTab.replace('cat-', '');
        openEditor(null, cat);
      });
    }

    bindDeleteDialog();
  }

  function bindProductRowEvents() {
    var container = document.getElementById('apProductsTableRoot');
    if (!container) return;
    container.querySelectorAll('[data-action]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var action = btn.dataset.action;
        var id = btn.dataset.id;
        if (action === 'edit') {
          var product = state.products.find(function (p) { return p.id === id; });
          if (product) openEditor(product);
          return;
        }
        if (action === 'delete') {
          openDeleteDialog(id, btn.dataset.name);
          return;
        }
        runAction(id, action);
      });
    });

    bindDragReorder(container);
  }

  var deleteId = null;
  function bindDeleteDialog() {
    var dialog = document.getElementById('apDeleteDialog');
    var cancel = document.getElementById('apDeleteCancel');
    var form = document.getElementById('apDeleteForm');
    if (!dialog || !form) return;
    cancel && cancel.addEventListener('click', function () { dialog.close(); });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!deleteId) return;
      runAction(deleteId, 'delete').then(function () {
        dialog.close();
        deleteId = null;
      });
    });
  }

  function openDeleteDialog(id, name) {
    deleteId = id;
    var target = document.getElementById('apDeleteTarget');
    if (target) target.textContent = '即將刪除：' + (name || id);
    document.getElementById('apDeleteDialog')?.showModal();
  }

  function refreshCategoryPanel() {
    var panel = document.getElementById('apCategoryPanel');
    if (!panel) return;
    var wrap = document.createElement('div');
    wrap.innerHTML = categoryPanelHtml();
    var next = wrap.firstElementChild;
    if (next) {
      panel.replaceWith(next);
      bindCategoryThumbUpload();
      bindCategoryDeleteButton();
    }
  }

  var deleteCategorySlug = null;
  function bindCategoryDeleteButton() {
    var btn = document.getElementById('apDeleteCategoryBtn');
    if (!btn || btn.dataset.bound) return;
    btn.dataset.bound = '1';
    btn.addEventListener('click', function () {
      openDeleteCategoryDialog(btn.dataset.slug, btn.dataset.label);
    });
  }

  function openDeleteCategoryDialog(slug, label) {
    deleteCategorySlug = slug;
    var target = document.getElementById('apDeleteCategoryTarget');
    if (target) target.textContent = '即將刪除品項：' + (label || slug);
    var err = document.getElementById('apDeleteCategoryError');
    if (err) { err.hidden = true; err.textContent = ''; }
    document.getElementById('apDeleteCategoryDialog')?.showModal();
  }

  function bindDeleteCategoryDialog() {
    var dialog = document.getElementById('apDeleteCategoryDialog');
    var cancel = document.getElementById('apDeleteCategoryCancel');
    var form = document.getElementById('apDeleteCategoryForm');
    if (!dialog || !form || dialog.dataset.bound) return;
    dialog.dataset.bound = '1';
    cancel && cancel.addEventListener('click', function () { dialog.close(); });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!deleteCategorySlug) return;
      var err = document.getElementById('apDeleteCategoryError');
      var removedSlug = deleteCategorySlug;
      api.admin.deleteProductCategory(removedSlug).then(function (res) {
        if (res.error) {
          if (err) { err.hidden = false; err.textContent = apiError(res); }
          return;
        }
        dialog.close();
        deleteCategorySlug = null;
        var remaining = categoryOrderList().filter(function (c) { return c !== removedSlug; });
        if (remaining.length) state.activeTab = 'cat-' + remaining[0];
        load(true, true);
      });
    });
  }

  function openAddCategoryDialog() {
    var dialog = document.getElementById('apAddCategoryDialog');
    var input = document.getElementById('apNewCategoryName');
    var err = document.getElementById('apAddCategoryError');
    if (!dialog) return;
    if (input) input.value = '';
    if (err) { err.hidden = true; err.textContent = ''; }
    dialog.showModal();
    input && input.focus();
  }

  function bindAddCategoryDialog() {
    var dialog = document.getElementById('apAddCategoryDialog');
    var cancel = document.getElementById('apAddCategoryCancel');
    var form = document.getElementById('apAddCategoryForm');
    if (!dialog || !form) return;
    cancel && cancel.addEventListener('click', function () { dialog.close(); });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var name = document.getElementById('apNewCategoryName')?.value.trim();
      var err = document.getElementById('apAddCategoryError');
      if (!name) {
        if (err) { err.hidden = false; err.textContent = '請填寫品項名稱'; }
        return;
      }
      if (err) err.hidden = true;
      api.admin.createProductCategory({ labelZh: name }).then(function (res) {
        if (res.error) {
          if (err) { err.hidden = false; err.textContent = apiError(res); }
          return;
        }
        dialog.close();
        if (res.category && res.category.slug) {
          state.activeTab = 'cat-' + res.category.slug;
        }
        load(true, true);
      });
    });
  }

  function bindCategoryThumbUpload() {
    var input = document.getElementById('apCategoryThumbInput');
    if (!input || input.dataset.bound) return;
    input.dataset.bound = '1';
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      input.value = '';
      if (!file) return;
      var bad = validateImageFiles([file]);
      if (bad) {
        alert(bad);
        return;
      }
      var cat = state.activeTab.replace('cat-', '');
      // Same ProductImageCropModal as product slots (freeform; optional 1:1 for catalog tiles).
      openProductImageCrop(file).then(function (cropped) {
        if (!cropped) return;
        return api.admin.uploadProductCategoryThumb(cat, cropped).then(function (res) {
          if (res.error) {
            alert('上傳失敗：' + apiError(res));
            return;
          }
          if (res.category) {
            var idx = (state.categories || []).findIndex(function (c) { return c.slug === cat; });
            if (idx >= 0) state.categories[idx] = res.category;
            else if (state.categories) state.categories.push(res.category);
          }
          refreshCategoryPanel();
        });
      });
    });
  }

  function bindDragReorder(scope) {
    var dragged = null;
    (scope || root).querySelectorAll('.ap-table tbody').forEach(function (tbody) {
      tbody.querySelectorAll('tr[data-id]').forEach(function (row) {
        row.addEventListener('dragstart', function () {
          dragged = row;
          row.classList.add('is-dragging');
        });
        row.addEventListener('dragend', function () {
          row.classList.remove('is-dragging');
          dragged = null;
          var ids = [...tbody.querySelectorAll('tr[data-id]')].map(function (r) { return r.dataset.id; });
          if (!ids.length) return;
          api.admin.reorderProducts(ids).then(function (res) {
            if (res.error) {
              alert('排序失敗：' + apiError(res));
              load(true, true);
            }
          });
        });
        row.addEventListener('dragover', function (e) {
          e.preventDefault();
          if (!dragged || dragged === row) return;
          var box = row.getBoundingClientRect();
          tbody.insertBefore(dragged, e.clientY < box.top + box.height / 2 ? row : row.nextSibling);
        });
      });
    });
  }

  function runAction(id, action) {
    return api.admin.productAction(id, action).then(function (res) {
      if (res.error) {
        alert(apiError(res));
        return;
      }
      load(true, true);
    });
  }

  function metalWeightLabel(weightChin, gold) {
    var n = parseFloat(weightChin);
    var factor = WAX_TO_METAL_CHIN[gold];
    if (!n || !factor) return '—';
    return (n * factor).toFixed(2) + ' 錢';
  }

  function updateVariantRowMetalWeight(row) {
    if (!row) return;
    var out = row.querySelector('.ap-metal-weight-out');
    if (!out) return;
    var weightInput = row.querySelector('[name="weight"]');
    var goldSelect = row.querySelector('[name="gold"]');
    out.textContent = metalWeightLabel(weightInput ? weightInput.value : '', goldSelect ? goldSelect.value : GOLDS[0]);
  }

  /** Auto 配鑽價錢 = cts × 一克拉價格; empty if inputs incomplete. */
  function sideStoneFormulaTotal(cts, ppc) {
    var c = parseFloat(cts);
    var p = parseFloat(ppc);
    if (!isFinite(c) || !isFinite(p) || c < 0 || p < 0) return '';
    return String(Math.round(c * p));
  }

  function syncSideStoneTotalDisplay(row, fromUserEdit) {
    if (!row) return;
    var totalInput = row.querySelector('[name="sideStoneTotal"]');
    if (!totalInput) return;
    var cts = row.querySelector('[name="sideStoneCarat"]');
    var ppc = row.querySelector('[name="sideStonePrice"]');
    var autoVal = sideStoneFormulaTotal(
      cts ? cts.value : '',
      ppc ? ppc.value : ''
    );
    if (fromUserEdit) {
      if (totalInput.value === '' || totalInput.value == null) {
        totalInput.dataset.fixed = '';
        totalInput.value = autoVal;
      } else {
        totalInput.dataset.fixed = '1';
      }
      return;
    }
    if (totalInput.dataset.fixed === '1') return;
    totalInput.value = autoVal;
  }

  function chainLengthWaxValue(lengthWeights, thickness, lengthCm) {
    var table = lengthWeights && lengthWeights[thickness];
    if (!table) return '';
    var val = table[String(lengthCm)];
    return val == null ? '' : val;
  }

  function chainTypeSelectorHtml(product, category) {
    if (category !== 'chain') return '';
    var types = chainCatalogTypes();
    var selected = resolveChainType(product && (product.chainType || product.chain_type));
    var opts = Object.keys(types).map(function (slug) {
      var label = types[slug].labelZh || slug;
      var sel = slug === selected ? ' selected' : '';
      return '<option value="' + esc(slug) + '"' + sel + '>' + esc(label) + '</option>';
    }).join('');
    if (!opts) {
      opts = '<option value="douyuan" selected>抖圓鏈</option>';
    }
    return (
      '<label class="ap-field-wide ap-chain-type-field">' +
        '<span>項鍊類型</span>' +
        '<select name="chainType" id="apChainType">' + opts + '</select>' +
        '<span class="ap-section-hint">依 Excel 鍊條價格表選擇項鍊款式。選類型後，商店「選擇鏈條長度」與報價自動用該表，不必每件商品手填。</span>' +
      '</label>'
    );
  }

  function chainLengthWeightsGridInnerHtml(lengthWeights, chainType) {
    var thicknesses = chainTypeThicknesses(chainType);
    var lengths = chainLengthsCm();
    var effective = lengthWeights && Object.keys(lengthWeights).length
      ? lengthWeights
      : chainTypeWaxTable(chainType);
    return thicknesses.map(function (thick) {
      var rows = lengths.map(function (len) {
        var val = chainLengthWaxValue(effective, thick, len);
        return (
          '<div class="ap-chain-length-row" data-thickness="' + esc(thick) + '" data-length="' + len + '">' +
            '<span class="ap-chain-length-label">' + len + ' cm</span>' +
            '<input type="number" name="chainLengthWax" step="0.0001" min="0.0001" ' +
              'data-thickness="' + esc(thick) + '" data-length="' + len + '" ' +
              'placeholder="蠟重（錢）" value="' + esc(val) + '">' +
          '</div>'
        );
      }).join('');
      return (
        '<div class="ap-chain-thickness-block" data-thickness="' + esc(thick) + '">' +
          '<h5 class="ap-chain-thickness-title">厚度 ' + esc(thick) + '</h5>' +
          '<div class="ap-chain-length-head"><span>長度</span><span>蠟重（錢）</span></div>' +
          '<div class="ap-chain-length-grid">' + rows + '</div>' +
        '</div>'
      );
    }).join('');
  }

  function chainLengthWeightsBlockHtml(lengthWeights, category, chainType) {
    if (category !== 'chain') return '';
    return (
      '<h4 class="ap-section-title">長度蠟重（選填）</h4>' +
      '<p class="ap-section-hint">在此填寫各厚度×長度的蠟重（錢）。選項來自 Excel 鍊條價格表（抖圓鏈等）。預設帶入標準值；留空格子＝用標準表。款式選項只選金屬／厚度，不再填 46cm 蠟重。</p>' +
      '<div class="ap-chain-length-weights" id="apChainLengthWeights">' +
        chainLengthWeightsGridInnerHtml(lengthWeights, chainType) +
      '</div>' +
      '<button type="button" class="btn-sm" id="apFillChainLengthDefaults">重填標準蠟重表</button>'
    );
  }

  function collectChainLengthWeights(form) {
    var out = {};
    form.querySelectorAll('#apChainLengthWeights input[name="chainLengthWax"]').forEach(function (input) {
      var thick = input.dataset.thickness;
      var len = input.dataset.length;
      var raw = String(input.value || '').trim();
      if (!thick || !len || !raw) return;
      var wax = parseFloat(raw);
      if (!Number.isFinite(wax) || wax <= 0) return;
      if (!out[thick]) out[thick] = {};
      out[thick][String(len)] = wax;
    });
    return Object.keys(out).length ? out : null;
  }

  function fillChainLengthDefaults(form) {
    var host = form.querySelector('#apChainLengthWeights');
    if (!host) return;
    var chainType = getFormChainType(form);
    var table = chainTypeWaxTable(chainType);
    var thicknesses = chainTypeThicknesses(chainType);
    var lengths = chainLengthsCm();
    thicknesses.forEach(function (thick) {
      lengths.forEach(function (len) {
        var input = host.querySelector(
          'input[name="chainLengthWax"][data-thickness="' + thick + '"][data-length="' + len + '"]'
        );
        if (!input || String(input.value || '').trim()) return;
        var wax = table[thick] && table[thick][String(len)];
        if (wax != null) input.value = wax;
      });
    });
  }

  function rebindChainLengthGrid(form) {
    var host = form.querySelector('#apChainLengthWeights');
    if (!host || host.dataset.bound) return;
    host.dataset.bound = '1';
  }

  function refreshChainLengthGrid(form, category, chainType) {
    var section = form.querySelector('#apChainLengthSection');
    if (!section || category !== 'chain') return;
    var preserved = collectChainLengthWeights(form) || {};
    var weightsHost = section.querySelector('#apChainLengthWeights');
    if (weightsHost) {
      delete weightsHost.dataset.bound;
      weightsHost.innerHTML = chainLengthWeightsGridInnerHtml(preserved, chainType);
    }
    rebindChainLengthGrid(form);
  }

  function toggleChainLengthSection(form, category) {
    var section = form.querySelector('#apChainLengthSection');
    if (!section) return;
    section.hidden = category !== 'chain';
  }

  function variantHeadHtml(category) {
    if (category === 'chain') {
      return (
        '<div class="ap-variant-head">' +
          '<span>金屬</span><span>厚度</span><span>手動定價</span><span></span>' +
        '</div>'
      );
    }
    return (
      '<div class="ap-variant-head">' +
        '<span>金屬</span><span>克拉</span><span>蠟重（錢）</span><span>預估金重</span>' +
        '<span>配鑽 cts</span><span>一克拉價格</span><span>配鑽價錢</span><span>手動定價</span><span></span>' +
      '</div>'
    );
  }

  function variantComboKey(gold, carat) {
    return String(gold || '') + '|' + String(carat || '');
  }

  function existingVariantComboKeys(grid) {
    var keys = {};
    if (!grid) return keys;
    grid.querySelectorAll('.ap-variant-row').forEach(function (row) {
      var gold = row.querySelector('[name="gold"]')?.value;
      var carat = row.querySelector('[name="carat"]')?.value;
      if (!gold || !carat) return;
      keys[variantComboKey(gold, carat)] = true;
    });
    return keys;
  }

  /** All admin metals × chain thicknesses; skip combos already in the grid. */
  function generateAllChainVariantRows(grid, form) {
    if (!grid) return 0;
    var chainType = getFormChainType(form);
    var thicknesses = chainTypeThicknesses(chainType);
    var existing = existingVariantComboKeys(grid);
    var html = [];
    GOLDS.forEach(function (gold) {
      thicknesses.forEach(function (thick) {
        var key = variantComboKey(gold, thick);
        if (existing[key]) return;
        existing[key] = true;
        html.push(variantRowHtml({ gold: gold, carat: thick }, 'chain', chainType));
      });
    });
    if (!html.length) return 0;
    grid.insertAdjacentHTML('beforeend', html.join(''));
    return html.length;
  }

  function syncChainVariantActions(category) {
    var genBtn = document.getElementById('apGenerateAllChainVariants');
    if (genBtn) genBtn.hidden = category !== 'chain';
  }

  function variantRowHtml(variant, category, chainType) {
    var carats = caratsFor(category, chainType);
    var goldOpts = GOLDS.map(function (g) {
      var sel = variant && variant.gold === g ? ' selected' : '';
      return '<option value="' + g + '"' + sel + '>' + (GOLD_LABELS[g] || g) + '</option>';
    }).join('');
    var caratOpts = carats.map(function (c) {
      var sel = variant && String(variant.carat) === c ? ' selected' : '';
      return '<option value="' + c + '"' + sel + '>' + c + '</option>';
    }).join('');
    var price = variant && variant.manual_price_twd != null ? variant.manual_price_twd : '';
    if (category === 'chain') {
      return (
        '<div class="ap-variant-row">' +
          '<select name="gold">' + goldOpts + '</select>' +
          '<select name="carat">' + caratOpts + '</select>' +
          '<input type="number" name="price" step="1" min="0" placeholder="手動定價" value="' + esc(price) + '">' +
          '<button type="button" class="ap-remove-row" aria-label="移除">✕</button>' +
        '</div>'
      );
    }
    var weight = variant ? variant.weight_chin : '';
    var sideStone = variant && variant.side_stone_price_twd != null ? variant.side_stone_price_twd : '';
    var sideStoneCts = variant && variant.side_stone_carat != null ? variant.side_stone_carat : '';
    var sideStoneTotalFixed = variant && variant.side_stone_total_twd != null
      ? variant.side_stone_total_twd
      : '';
    var sideStoneTotalDisplay = sideStoneTotalFixed !== ''
      ? sideStoneTotalFixed
      : sideStoneFormulaTotal(sideStoneCts, sideStone);
    var sideStoneFixedAttr = sideStoneTotalFixed !== '' ? ' data-fixed="1"' : '';
    var gold = (variant && variant.gold) || GOLDS[0];
    return '<div class="ap-variant-row">' +
      '<select name="gold">' + goldOpts + '</select>' +
      '<select name="carat">' + caratOpts + '</select>' +
      '<input type="number" name="weight" step="0.0001" min="0.0001" placeholder="蠟重（錢）" value="' + esc(weight) + '">' +
      '<output class="ap-metal-weight-out" name="metalWeight">' + metalWeightLabel(weight, gold) + '</output>' +
      '<input type="number" name="sideStoneCarat" step="0.01" min="0" placeholder="配鑽 cts" value="' + esc(sideStoneCts) + '">' +
      '<input type="number" name="sideStonePrice" step="1" min="0" placeholder="一克拉價格" value="' + esc(sideStone) + '">' +
      '<input type="number" name="sideStoneTotal" step="1" min="0" placeholder="配鑽價錢" value="' +
        esc(sideStoneTotalDisplay) + '"' + sideStoneFixedAttr + ' title="自動 = 配鑽 cts × 一克拉價格；手動改寫後為固定總價">' +
      '<input type="number" name="price" step="1" min="0" placeholder="手動定價" value="' + esc(price) + '">' +
      '<button type="button" class="ap-remove-row" aria-label="移除">✕</button></div>';
  }

  function imageSlideHtml(url, color) {
    // Bundled shop-product PNGs are never shown — uploads only.
    if (isAutoStockProductImage(url)) return '';
    var persistUrl = persistableImageUrl(url, color);
    if (!persistUrl) return '';
    return (
      '<div class="ap-carousel-item" data-url="' + esc(persistUrl) + '" data-color="' + esc(color || '') + '">' +
        '<div class="ap-carousel-card">' +
          '<div class="ap-carousel-card-media">' +
            '<img class="ap-carousel-img" src="' + esc(persistUrl) + '" alt="" data-fallback="' + esc(persistUrl) +
              '" loading="eager" decoding="async" width="180" height="180">' +
            '<button type="button" class="ap-remove-image" aria-label="移除">X</button>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  var deferredImageObserver = null;

  function loadDeferredImage(img) {
    var src = img && img.dataset ? img.dataset.src : '';
    if (!src) return;
    img.src = src;
    img.removeAttribute('data-src');
  }

  function observeDeferredImages(scope) {
    if (!scope) return;
    var images = scope.querySelectorAll('img.ap-carousel-img[data-src]');
    if (!images.length) return;
    if (!('IntersectionObserver' in window)) {
      images.forEach(loadDeferredImage);
      return;
    }
    if (!deferredImageObserver) {
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          observer.unobserve(entry.target);
          loadDeferredImage(entry.target);
        });
      }, { rootMargin: '160px 0px' });
      deferredImageObserver = observer;
    }
    images.forEach(function (img) { deferredImageObserver.observe(img); });
  }

  function resetDeferredImages() {
    if (!deferredImageObserver) return;
    deferredImageObserver.disconnect();
    deferredImageObserver = null;
  }

  function slotSelectHtml(options, selected) {
    return options.map(function (opt) {
      return '<option value="' + opt.value + '"' + (opt.value === selected ? ' selected' : '') + '>' + esc(opt.label) + '</option>';
    }).join('');
  }

  function slotPairSelectHtml(selectedKey) {
    var parsed = parseSlotKey(selectedKey) || { metal: 'white', diamond: 'white', chainMetal: null };
    return (
      '<label class="ap-image-slot-pair">' +
        '<span>金屬</span>' +
        '<select class="ap-image-slot-metal">' + slotSelectHtml(METAL_SLOT_OPTIONS, parsed.metal) + '</select>' +
      '</label>' +
      '<label class="ap-image-slot-pair">' +
        '<span>鑽石</span>' +
        '<select class="ap-image-slot-diamond">' + slotSelectHtml(DIAMOND_SLOT_OPTIONS, parsed.diamond) + '</select>' +
      '</label>'
    );
  }

  function groupImagesForSlots(images) {
    var groups = {};
    (images || []).forEach(function (img) {
      var color = img.color || 'white';
      var raw = img.file_path || img.url;
      var url = persistableImageUrl(raw, color);
      if (!url) return;
      if (!groups[color]) groups[color] = [];
      if (groups[color].indexOf(url) < 0) groups[color].push(url);
    });
    return groups;
  }

  /** After save/autosave, replace stale _pending carousel URLs with promoted Storage paths. */
  function syncEditorImagesFromProduct(form, images) {
    if (!form || !images || !images.length) return;
    var groups = groupImagesForSlots(images);
    form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
      var color = slotColorKey(slot);
      var urls = groups[color] || [];
      var items = slot.querySelectorAll('.ap-carousel-item[data-url]');
      items.forEach(function (item, index) {
        var url = urls[index];
        if (!url) return;
        item.dataset.url = url;
        var img = item.querySelector('.ap-carousel-img');
        if (img) {
          img.src = url;
          if (img.dataset) img.dataset.fallback = url;
        }
      });
    });
  }

  /** First-seen color in product_images sort_order = admin block order. */
  function slotOrderFromImages(images) {
    var order = [];
    var seen = {};
    (images || []).forEach(function (img) {
      var color = img.color || 'white';
      if (seen[color]) return;
      seen[color] = true;
      order.push(color);
    });
    return order;
  }

  /**
   * Real uploads only. Legacy metal / metal-diamond-chainMetal keys normalize
   * into metal-diamond slots. Never invent shop-product letter previews.
   */
  function slotsForEditor(images, category) {
    var groups = groupImagesForSlots(images);
    var seen = {};
    var slots = [];

    function pushSlot(key) {
      if (!key || seen[key]) return;
      var urls = groups[key] ? groups[key].slice() : [];
      if (!urls.length) return;
      seen[key] = true;
      slots.push({ color: key, urls: urls });
    }

    function mergeInto(targetKey, urls) {
      if (!groups[targetKey]) groups[targetKey] = [];
      (urls || []).forEach(function (url) {
        if (groups[targetKey].indexOf(url) < 0) groups[targetKey].push(url);
      });
    }

    // Legacy metal-only (white/yellow/rose) → metal-white so selects stay truthful.
    COLORS.forEach(function (metal) {
      if (!groups[metal] || !groups[metal].length) return;
      mergeInto(buildSlotKey(metal, 'white', null), groups[metal]);
    });

    // Fold legacy metal-diamond-chainMetal into metal-diamond (chain color no longer configured).
    Object.keys(groups).forEach(function (key) {
      var parsed = parseSlotKey(key);
      if (!parsed || !parsed.chainMetal) return;
      mergeInto(buildSlotKey(parsed.metal, parsed.diamond, null), groups[key]);
      delete groups[key];
    });

    // Admin save order (DOM block order), then any leftover keys.
    slotOrderFromImages(images).forEach(pushSlot);
    Object.keys(groups).forEach(function (key) {
      if (COLORS.indexOf(key) >= 0) return; // folded into metal-white above
      if (seen[key]) return;
      if (!(groups[key] && groups[key].length)) return;
      pushSlot(key);
    });

    if (!slots.length) slots.push({ color: 'white-white', urls: [] });
    return slots;
  }

  function imageSlotHtml(slot, category) {
    var slotId = 'slot-' + (++_slotCounter);
    var color = slot.color || 'white-white';
    var slides = (slot.urls || []).map(function (url) {
      return imageSlideHtml(url, color);
    }).join('');

    return (
      '<div class="ap-image-slot" data-slot-id="' + slotId + '" data-category="' + esc(category || '') + '">' +
        '<div class="ap-image-slot-head">' +
          '<div class="ap-image-slot-label ap-image-slot-label--pair">' +
            '<span>圖片選項</span>' +
            slotPairSelectHtml(color) +
          '</div>' +
          '<button type="button" class="ap-remove-slot" aria-label="移除此選項">✕</button>' +
        '</div>' +
        '<div class="ap-carousel" data-carousel>' +
          '<button type="button" class="ap-carousel-btn ap-carousel-prev" aria-label="上一張" disabled>' +
            '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>' +
          '</button>' +
          '<div class="ap-carousel-viewport">' +
            '<div class="ap-carousel-track">' +
              slides +
              '<div class="ap-carousel-item ap-carousel-item--upload">' +
                '<div class="ap-carousel-card ap-carousel-card--upload" data-dropzone>' +
                  '<label class="ap-image-upload-btn">' +
                    '<span class="ap-upload-icon">' +
                      '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>' +
                    '</span>' +
                    '<span class="ap-upload-title">上傳圖片</span>' +
                    '<span class="ap-upload-hint">或點擊瀏覽<br>PNG / JPG / WEBP，1MB 內<br>可選裁切，預設保留原圖</span>' +
                    '<input type="file" class="ap-image-input" accept="' + IMAGE_ACCEPT + '" multiple hidden>' +
                  '</label>' +
                  '<div class="ap-upload-progress" hidden><div class="ap-upload-progress-bar"></div></div>' +
                  '<span class="ap-uploading" hidden>上傳中…</span>' +
                '</div>' +
              '</div>' +
            '</div>' +
          '</div>' +
          '<button type="button" class="ap-carousel-btn ap-carousel-next" aria-label="下一張">' +
            '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 18l6-6-6-6"/></svg>' +
          '</button>' +
        '</div>' +
      '</div>'
    );
  }

  function imageSlotsHtml(images, category) {
    var slots = slotsForEditor(images, category);
    return slots.map(function (slot) { return imageSlotHtml(slot, category); }).join('');
  }

  function initCarousel(carousel) {
    if (carousel.dataset.carouselBound) return;
    carousel.dataset.carouselBound = '1';
    var viewport = carousel.querySelector('.ap-carousel-viewport');
    var track = carousel.querySelector('.ap-carousel-track');
    var prev = carousel.querySelector('.ap-carousel-prev');
    var next = carousel.querySelector('.ap-carousel-next');
    if (!viewport || !track || !prev || !next) return;

    function updateButtons() {
      var maxScroll = track.scrollWidth - viewport.clientWidth;
      prev.disabled = viewport.scrollLeft <= 1;
      next.disabled = viewport.scrollLeft >= maxScroll - 1;
    }

    function scrollByItem(dir) {
      var item = track.querySelector('.ap-carousel-item');
      var gap = 8;
      var step = item ? item.offsetWidth + gap : viewport.clientWidth * 0.85;
      viewport.scrollBy({ left: dir * step, behavior: 'smooth' });
      window.setTimeout(updateButtons, 280);
    }

    prev.addEventListener('click', function () { scrollByItem(-1); });
    next.addEventListener('click', function () { scrollByItem(1); });
    viewport.addEventListener('scroll', updateButtons, { passive: true });
    window.addEventListener('resize', updateButtons);
    updateButtons();
    carousel._refreshCarousel = updateButtons;
  }

  function refreshAllCarousels(form) {
    form.querySelectorAll('[data-carousel]').forEach(function (el) {
      if (el._refreshCarousel) el._refreshCarousel();
    });
  }

  function slotColorKey(slotEl) {
    var metalSel = slotEl.querySelector('.ap-image-slot-metal');
    var diamondSel = slotEl.querySelector('.ap-image-slot-diamond');
    if (metalSel && diamondSel) {
      return buildSlotKey(metalSel.value, diamondSel.value, null);
    }
    var legacy = slotEl.querySelector('.ap-image-slot-key');
    return legacy ? legacy.value : '';
  }

  function usedSlotKeys(form, exceptSlot) {
    var used = {};
    form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
      if (slot === exceptSlot) return;
      var key = slotColorKey(slot);
      if (key && key !== '__custom__') used[key] = true;
    });
    return used;
  }

  /**
   * Open CMS-style crop modal (freeform by default). Resolves File or null if cancelled.
   * Same ImageCropEditor stack as 內容與頁面圖片 / AdminTables.renderPageImageEditModal.
   */
  function openProductImageCrop(file) {
    return new Promise(function (resolve) {
      whenProductCropReady(function (ready) {
        if (!ready) {
          alert('裁切元件尚未載入，請重新整理後再試。');
          resolve(null);
          return;
        }
        var previewUrl = URL.createObjectURL(file);
        var mount = document.createElement('div');
        mount.id = 'apProductImageCropMount';
        document.body.appendChild(mount);

        function cleanup(result) {
          try { URL.revokeObjectURL(previewUrl); } catch (e) { /* ignore */ }
          if (window.AdminTables && window.AdminTables.unmount) {
            try { window.AdminTables.unmount(mount); } catch (e2) { /* ignore */ }
          }
          if (mount.parentNode) mount.parentNode.removeChild(mount);
          resolve(result);
        }

        window.AdminTables.renderProductImageCropModal(mount, {
          previewUrl: previewUrl,
          file: file,
          fileLabel: file.name || '',
          onComplete: function (result) {
            cleanup(result && result.file ? result.file : file);
          },
          onCancel: function () {
            cleanup(null);
          },
        });
      });
    });
  }

  /** Sequential crop dialogs, then upload prepared files. Cancel skips that file only. */
  function prepareFilesWithCrop(files) {
    var list = Array.from(files || []);
    var prepared = [];
    function next(i) {
      if (i >= list.length) return Promise.resolve(prepared);
      return openProductImageCrop(list[i]).then(function (out) {
        if (out) prepared.push(out);
        return next(i + 1);
      });
    }
    return next(0);
  }

  function beginImageBusy() {
    _imageBusy += 1;
  }

  function endImageBusy() {
    _imageBusy = Math.max(0, _imageBusy - 1);
    if (_imageBusy === 0) scheduleAutosave();
  }

  function isImageBusy() {
    return _imageBusy > 0 || !!document.getElementById('apProductImageCropMount');
  }

  function uploadFilesToSlot(files, slot, form) {
    var track = slot.querySelector('.ap-carousel-track');
    var uploadItem = slot.querySelector('.ap-carousel-item--upload');
    var uploading = slot.querySelector('.ap-uploading');
    var progressWrap = slot.querySelector('.ap-upload-progress');
    var progressBar = slot.querySelector('.ap-upload-progress-bar');
    if (!files.length || !track || !uploadItem) return;

    var color = slotColorKey(slot) || 'white';

    beginImageBusy();
    prepareFilesWithCrop(files).then(function (readyFiles) {
      if (!readyFiles.length) {
        endImageBusy();
        return;
      }

      var progressByIndex = readyFiles.map(function () { return 0; });

      function updateProgress() {
        if (!progressBar) return;
        var avg = progressByIndex.reduce(function (a, b) { return a + b; }, 0) / progressByIndex.length;
        progressBar.style.width = avg + '%';
      }

      function uploadOne(file, index) {
        return new Promise(function (resolve) {
          var xhr = new XMLHttpRequest();
          xhr.open('POST', '/api/admin/product-upload');
          xhr.withCredentials = true;
          xhr.upload.addEventListener('progress', function (ev) {
            if (ev.lengthComputable) {
              progressByIndex[index] = (ev.loaded / ev.total) * 100;
              updateProgress();
            }
          });
          xhr.onload = function () {
            var res = {};
            try { res = JSON.parse(xhr.responseText); } catch (e) { res = { error: 'parse' }; }
            if (!res.error && xhr.status >= 400) {
              if (typeof res.detail === 'string') res.error = res.detail;
              else res.error = (api && api.apiErrorMessage) ? api.apiErrorMessage(res) : ('HTTP ' + xhr.status);
            }
            progressByIndex[index] = 100;
            updateProgress();
            resolve(res);
          };
          xhr.onerror = function () { resolve({ error: 'network' }); };
          var fd = new FormData();
          fd.append('file', file);
          // Existing product: persist URL into product_images immediately (SQL SoT).
          if (state.editingId) {
            fd.append('product_id', state.editingId);
            fd.append('color', color);
          }
          xhr.send(fd);
        });
      }

      if (uploading) uploading.hidden = true;
      if (progressWrap) progressWrap.hidden = false;
      updateProgress();

      Promise.all(readyFiles.map(uploadOne)).then(function (results) {
        if (progressWrap) progressWrap.hidden = true;
        if (progressBar) progressBar.style.width = '0%';
        var hadError = false;
        results.forEach(function (res) {
          if (res.error || !res.url || isBrowserLocalImageUrl(res.url)) { hadError = true; return; }
          var wrap = document.createElement('div');
          wrap.innerHTML = imageSlideHtml(res.url, color);
          var item = wrap.firstElementChild;
          if (!item) { hadError = true; return; }
          item.dataset.url = res.url;
          item.dataset.color = color;
          track.insertBefore(item, uploadItem);
          item.querySelector('.ap-remove-image')?.addEventListener('click', function () {
            item.remove();
            var carousel = slot.querySelector('[data-carousel]');
            if (carousel && carousel._refreshCarousel) carousel._refreshCarousel();
          });
        });
        refreshAllCarousels(form);
        if (hadError && uploading) {
          uploading.hidden = false;
          uploading.textContent = '上傳失敗';
        }
        endImageBusy();
      }, function () {
        endImageBusy();
      });
    }, function () {
      endImageBusy();
    });
  }

  function bindSlotKeySelectors(slot, form) {
    var metalSel = slot.querySelector('.ap-image-slot-metal');
    var diamondSel = slot.querySelector('.ap-image-slot-diamond');

    slot.dataset.lastKey = slotColorKey(slot);

    function onSlotKeyChange() {
      var key = slotColorKey(slot);
      var used = usedSlotKeys(form, slot);
      if (used[key]) {
        alert('此組合已用於其他圖片選項，請選擇不同的組合。');
        var prev = parseSlotKey(slot.dataset.lastKey) || { metal: 'white', diamond: 'white', chainMetal: null };
        if (metalSel) metalSel.value = prev.metal;
        if (diamondSel) diamondSel.value = prev.diamond;
        return;
      }
      slot.dataset.lastKey = key;
      slot.querySelectorAll('.ap-carousel-item[data-url]').forEach(function (item) {
        item.dataset.color = key;
      });
    }

    metalSel?.addEventListener('change', onSlotKeyChange);
    diamondSel?.addEventListener('change', onSlotKeyChange);
  }

  function refreshImageSlotCategory(slot, form, category) {
    var metalSel = slot.querySelector('.ap-image-slot-metal');
    var diamondSel = slot.querySelector('.ap-image-slot-diamond');
    var baseColor = buildSlotKey(metalSel ? metalSel.value : 'white', diamondSel ? diamondSel.value : 'white', null);
    slot.dataset.category = category || '';
    var pairWrap = slot.querySelector('.ap-image-slot-label--pair');
    if (!pairWrap) return;
    pairWrap.innerHTML = '<span>圖片選項</span>' + slotPairSelectHtml(baseColor);
    bindSlotKeySelectors(slot, form);
    var key = slotColorKey(slot);
    slot.querySelectorAll('.ap-carousel-item[data-url]').forEach(function (item) {
      item.dataset.color = key;
    });
  }

  function bindImageSlot(slot, form) {
    if (slot.dataset.bound) return;
    slot.dataset.bound = '1';

    var carousel = slot.querySelector('[data-carousel]');
    if (carousel) initCarousel(carousel);
    observeDeferredImages(slot);

    bindSlotKeySelectors(slot, form);

    var removeSlot = slot.querySelector('.ap-remove-slot');

      removeSlot?.addEventListener('click', function () {
        if (form.querySelectorAll('.ap-image-slot').length <= 1) {
          alert('至少保留一個圖片選項');
          return;
        }
        slot.remove();
        refreshAllCarousels(form);
      });

      slot.querySelectorAll('.ap-remove-image').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var item = btn.closest('.ap-carousel-item');
          if (item && !item.classList.contains('ap-carousel-item--upload')) item.remove();
          var carousel = slot.querySelector('[data-carousel]');
          if (carousel && carousel._refreshCarousel) carousel._refreshCarousel();
        });
      });

      var input = slot.querySelector('.ap-image-input');
      var dropzone = slot.querySelector('[data-dropzone]');

      input?.addEventListener('change', function () {
        var files = Array.from(input.files || []);
        input.value = '';
        var bad = validateImageFiles(files);
        if (bad) {
          alert(bad);
          return;
        }
        uploadFilesToSlot(files, slot, form);
      });

      if (dropzone) {
        dropzone.addEventListener('dragover', function (e) {
          e.preventDefault();
          dropzone.classList.add('is-dragover');
        });
        dropzone.addEventListener('dragleave', function () {
          dropzone.classList.remove('is-dragover');
        });
        dropzone.addEventListener('drop', function (e) {
          e.preventDefault();
          dropzone.classList.remove('is-dragover');
          var files = Array.from((e.dataTransfer && e.dataTransfer.files) || []);
          var bad = validateImageFiles(files);
          if (bad) {
            alert(bad);
            return;
          }
          uploadFilesToSlot(files, slot, form);
        });
      }
  }

  function bindImageSlots(form) {
    form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
      bindImageSlot(slot, form);
    });
  }

  function setAutosaveStatus(text) {
    var el = document.getElementById('apAutosaveStatus');
    if (el) el.textContent = text || '';
  }

  function clearAutosaveTimer() {
    if (_autosave.timer) {
      clearTimeout(_autosave.timer);
      _autosave.timer = null;
    }
  }

  function clearAutosave() {
    clearAutosaveTimer();
    if (_autosave.waitTimer) {
      clearInterval(_autosave.waitTimer);
      _autosave.waitTimer = null;
    }
    _autosave.inFlight = false;
    _autosave.queued = false;
    _autosave.form = null;
    _autosave.ctx = null;
    setAutosaveStatus('');
  }

  function scheduleAutosave() {
    if (!_autosave.form || !_autosave.ctx || state.view !== 'editor') return;
    clearAutosaveTimer();
    _autosave.timer = setTimeout(function () {
      _autosave.timer = null;
      flushAutosave();
    }, AUTOSAVE_MS);
  }

  function flushAutosave() {
    if (!_autosave.form || !_autosave.ctx || state.view !== 'editor') return;
    if (_autosave.inFlight) {
      _autosave.queued = true;
      return;
    }
    if (isImageBusy()) {
      scheduleAutosave();
      return;
    }
    _autosave.inFlight = true;
    saveProduct(_autosave.form, _autosave.ctx, { autosave: true }).then(function (result) {
      _autosave.inFlight = false;
      if (result && result.skipped) {
        if (!result.errorShown) setAutosaveStatus('');
      } else if (result && result.error) {
        setAutosaveStatus('自動儲存失敗');
      } else if (result && result.ok) {
        setAutosaveStatus('已自動儲存');
      }
      if (_autosave.queued) {
        _autosave.queued = false;
        scheduleAutosave();
      }
    });
  }

  function bindAutosave(form, ctx) {
    clearAutosave();
    _autosave.form = form;
    _autosave.ctx = ctx;
    form.addEventListener('input', scheduleAutosave);
    form.addEventListener('change', scheduleAutosave);
  }

  function closeEditor() {
    clearAutosave();
    _imageBusy = 0;
    resetDeferredImages();
    state.view = 'list';
    state.editingId = null;
    renderShell();
  }

  function isSaveForLater(form) {
    return !!form.querySelector('[name="saveForLater"]')?.checked;
  }

  function updateSaveButton(form, isEdit) {
    var btn = document.getElementById('apSaveProduct');
    if (!btn || !form) return;
    if (isSaveForLater(form)) {
      btn.classList.remove('btn-primary');
      btn.textContent = '儲存草稿';
    } else {
      btn.classList.add('btn-primary');
      btn.textContent = isEdit ? '儲存並上架' : '建立並上架';
    }
  }

  function saveForLaterToggleHtml(product) {
    var saveForLater = product ? !product.is_published : true;
    var checked = saveForLater ? ' checked' : '';
    return (
      '<div class="ap-switch-wrap">' +
        '<label class="ap-switch">' +
          '<input type="checkbox" class="ap-switch-input" name="saveForLater"' + checked + '>' +
          '<span class="ap-switch-track" aria-hidden="true"><span class="ap-switch-thumb"></span></span>' +
          '<span class="ap-switch-label">稍後上架</span>' +
        '</label>' +
      '</div>'
    );
  }

  function allowsEngravingToggleHtml(product) {
    // Default on for new products / legacy rows without the column yet.
    var on = !product || product.allows_engraving !== false;
    var checked = on ? ' checked' : '';
    return (
      '<div class="ap-switch-wrap">' +
        '<label class="ap-switch">' +
          '<input type="checkbox" class="ap-switch-input" name="allowsEngraving"' + checked + '>' +
          '<span class="ap-switch-track" aria-hidden="true"><span class="ap-switch-thumb"></span></span>' +
          '<span class="ap-switch-label">可戒圈刻字</span>' +
        '</label>' +
      '</div>'
    );
  }

  function allowsFancyShapesToggleHtml(product) {
    var on = !product || product.allows_fancy_shapes !== false;
    var checked = on ? ' checked' : '';
    return (
      '<div class="ap-switch-wrap">' +
        '<label class="ap-switch">' +
          '<input type="checkbox" class="ap-switch-input" name="allowsFancyShapes"' + checked + '>' +
          '<span class="ap-switch-track" aria-hidden="true"><span class="ap-switch-thumb"></span></span>' +
          '<span class="ap-switch-label">可選其它形狀</span>' +
        '</label>' +
      '</div>'
    );
  }

  function pendantSellModeTogglesHtml(product, category) {
    // Left 不含鍊賣 = customer may choose with/without chain.
    // Right 含鍊賣 = with-chain only (no choice).
    var chainOnly = !!(product && product.allows_with_chain !== false
      && product.allows_pendant_only === false);
    if (!product) chainOnly = false;
    var hiddenAttr = category === 'pendant' ? '' : ' hidden';
    return (
      '<div class="ap-pendant-sell-modes ap-field-wide" id="apPendantSellModes"' + hiddenAttr + '>' +
        '<div class="ap-sell-mode-dual' + (chainOnly ? ' is-chain' : '') + '" id="apSellModeDual">' +
          '<button type="button" class="ap-sell-mode-side" data-side="only">不含鍊賣</button>' +
          '<label class="ap-switch ap-cine-switch">' +
            '<input type="checkbox" class="ap-switch-input" name="sellWithChain"' +
              (chainOnly ? ' checked' : '') + ' aria-label="項墜販售方式">' +
            '<span class="ap-cine-track" aria-hidden="true"><span class="ap-cine-thumb"></span></span>' +
          '</label>' +
          '<button type="button" class="ap-sell-mode-side" data-side="chain">含鍊賣</button>' +
        '</div>' +
        '<p class="ap-section-hint ap-pendant-sell-hint">' +
          '左＝不含鍊賣：客人可選要不要鍊；右＝含鍊賣：只能含鍊、客人不能選不含鍊。' +
        '</p>' +
      '</div>'
    );
  }

  function editorFormHtml(product, defaultCategory) {
    var isEdit = !!product;
    var category = (product && product.category) || defaultCategory || 'ring';
    var chainType = resolveChainType(product && (product.chainType || product.chain_type));
    var variants = (product && product.variants && product.variants.length)
      ? product.variants.map(function (v) { return variantRowHtml(v, category, chainType); }).join('')
      : variantRowHtml(null, category, chainType);

    var catOpts = categoryOrderList().map(function (c) {
      var sel = category === c ? ' selected' : '';
      return '<option value="' + c + '"' + sel + '>' + esc(state.categoryLabels[c] || c) + '</option>';
    }).join('');
    var colorOpts = COLORS.map(function (c) {
      var sel = (product ? product.default_color : 'white') === c ? ' selected' : '';
      return '<option value="' + c + '"' + sel + '>' + COLOR_LABELS[c] + '</option>';
    }).join('');

    return (
      '<div class="ap-editor-page">' +
        '<header class="ap-editor-head">' +
          '<button type="button" class="btn-sm ap-editor-back" id="apEditorBack">← 返回商品列表</button>' +
          '<div class="ap-editor-head-text">' +
            '<h2>' + (isEdit ? '編輯商品' : '新增商品') + '</h2>' +
            '<p class="ap-editor-sub">填寫款式選項並上傳商品照片後可上架至客製試算頁。</p>' +
          '</div>' +
        '</header>' +
        '<div class="ap-editor-body">' +
          '<p class="ap-form-error" id="apFormError" hidden></p>' +
          '<form id="apProductForm" class="ap-form">' +
            '<div class="ap-form-grid">' +
              '<label><span>品項</span><select name="category" id="apCategory">' + catOpts + '</select></label>' +
              '<label><span>預設顏色</span><select name="defaultColor">' + colorOpts + '</select></label>' +
              '<label><span>中文名稱 <span class="ap-required" aria-hidden="true">*</span></span><input name="nameZh" maxlength="150" autocomplete="off" value="' + esc(product && product.name_zh) + '"></label>' +
              '<label><span>英文名稱（資料用） <span class="ap-required" aria-hidden="true">*</span></span><input name="nameEn" maxlength="150" required autocomplete="off" value="' + esc(product && product.name_en) + '"></label>' +
              '<label class="ap-field-wide"><span>中文描述</span><textarea class="ap-textarea" name="descriptionZh" rows="3" placeholder="商品中文說明…">' + esc(product && product.description_zh) + '</textarea></label>' +
              '<label class="ap-field-wide"><span>英文描述</span><textarea class="ap-textarea" name="descriptionEn" rows="3" placeholder="Product description…">' + esc(product && product.description_en) + '</textarea></label>' +
              saveForLaterToggleHtml(product) +
              allowsEngravingToggleHtml(product) +
              allowsFancyShapesToggleHtml(product) +
              pendantSellModeTogglesHtml(product, category) +
            '</div>' +
            '<h4 class="ap-section-title">款式選項</h4>' +
            '<div class="ap-variant-block' + (category === 'chain' ? ' ap-variant-block--chain' : '') + '">' +
              variantHeadHtml(category) +
              '<div id="apVariantGrid">' + variants + '</div>' +
            '</div>' +
            '<div class="ap-variant-actions">' +
              '<button type="button" class="btn-sm" id="apAddVariant">+ 新增款式</button>' +
              '<button type="button" class="btn-sm" id="apGenerateAllChainVariants"' +
                (category === 'chain' ? '' : ' hidden') +
                '>一鍵產生全部款式</button>' +
            '</div>' +
            '<div id="apChainLengthSection"' + (category === 'chain' ? '' : ' hidden') + '>' +
              chainTypeSelectorHtml(product, category) +
              chainLengthWeightsBlockHtml(product && product.lengthWeights, category, chainType) +
            '</div>' +
            '<h4 class="ap-section-title">商品照片</h4>' +
            '<p class="ap-section-hint">試算頁會依「金屬 × 鑽石顏色」切換商品圖' +
              (category === 'pendant' ? '；含鍊預覽沿用項墜金屬色（無需另傳異色鍊圖）' : '') +
              '。請為需要的金屬 × 鑽石組合上傳商品照片。</p>' +
            '<div class="ap-image-slots" id="apImageSlots">' + imageSlotsHtml(product && product.images, category) + '</div>' +
            '<button type="button" class="btn-sm" id="apAddImageSlot">+ 新增圖片選項</button>' +
            '<div class="ap-form-actions ap-editor-actions">' +
              '<span id="apAutosaveStatus" class="ap-autosave-status" aria-live="polite"></span>' +
              '<button type="button" class="btn-sm" id="apEditorCancel">取消</button>' +
              '<button type="submit" class="btn-sm" id="apSaveProduct">儲存草稿</button>' +
            '</div>' +
          '</form>' +
        '</div>' +
      '</div>'
    );
  }

  function bindPendantSellModeSwitch(form) {
    var dual = document.getElementById('apSellModeDual');
    var input = form && form.querySelector('[name="sellWithChain"]');
    if (!dual || !input) return;

    function sync() {
      dual.classList.toggle('is-chain', !!input.checked);
    }

    input.addEventListener('change', sync);
    dual.querySelectorAll('.ap-sell-mode-side').forEach(function (btn) {
      btn.addEventListener('click', function () {
        input.checked = btn.getAttribute('data-side') === 'chain';
        sync();
      });
    });
    sync();
  }

  function bindEditorEvents(product) {
    var form = document.getElementById('apProductForm');
    var grid = document.getElementById('apVariantGrid');
    var catSel = document.getElementById('apCategory');
    var editorCtx = { product: product || null };

    document.getElementById('apEditorBack')?.addEventListener('click', closeEditor);
    document.getElementById('apEditorCancel')?.addEventListener('click', closeEditor);
    bindPendantSellModeSwitch(form);

    document.getElementById('apAddVariant')?.addEventListener('click', function () {
      grid.insertAdjacentHTML('beforeend', variantRowHtml(null, catSel.value, getFormChainType(form)));
      bindRemoveRows();
    });

    document.getElementById('apGenerateAllChainVariants')?.addEventListener('click', function () {
      if (catSel.value !== 'chain') return;
      var added = generateAllChainVariantRows(grid, form);
      bindRemoveRows();
      if (!added) alert('全部金屬 × 厚度組合已存在，無需再產生');
    });

    document.getElementById('apFillChainLengthDefaults')?.addEventListener('click', function () {
      fillChainLengthDefaults(form);
    });

    rebindChainLengthGrid(form);

    document.getElementById('apChainType')?.addEventListener('change', function () {
      refreshChainLengthGrid(form, catSel.value, getFormChainType(form));
    });

    catSel?.addEventListener('change', function () {
      toggleChainLengthSection(form, catSel.value);
      syncChainVariantActions(catSel.value);
      if (catSel.value === 'chain') {
        refreshChainLengthGrid(form, 'chain', getFormChainType(form));
      }
    });

    function bindRemoveRows() {
      grid.querySelectorAll('.ap-remove-row').forEach(function (btn) {
        btn.onclick = function () { btn.closest('.ap-variant-row')?.remove(); };
      });
    }
    bindRemoveRows();

    if (!grid.dataset.metalWeightBound) {
      grid.dataset.metalWeightBound = '1';
      grid.addEventListener('input', function (e) {
        var row = e.target.closest('.ap-variant-row');
        if (!row) return;
        if (e.target.name === 'weight') updateVariantRowMetalWeight(row);
        if (e.target.name === 'sideStoneCarat' || e.target.name === 'sideStonePrice') {
          syncSideStoneTotalDisplay(row, false);
        }
        if (e.target.name === 'sideStoneTotal') {
          syncSideStoneTotalDisplay(row, true);
        }
      });
      grid.addEventListener('change', function (e) {
        if (e.target.name === 'gold') updateVariantRowMetalWeight(e.target.closest('.ap-variant-row'));
      });
    }

    bindImageSlots(form);

    document.getElementById('apAddImageSlot')?.addEventListener('click', function () {
      var host = document.getElementById('apImageSlots');
      if (!host) return;
      var cat = catSel.value;
      var used = usedSlotKeys(form);
      var pick = presetSlotKeysForCategory(cat).find(function (v) { return !used[v]; });
      if (!pick) {
        alert('所有組合都已建立，無法再新增圖片選項');
        return;
      }
      var wrap = document.createElement('div');
      wrap.innerHTML = imageSlotHtml({ color: pick, urls: [] }, cat);
      var slot = wrap.firstElementChild;
      host.appendChild(slot);
      bindImageSlot(slot, form);
      slot.querySelector('.ap-image-slot-metal')?.focus();
    });

    catSel?.addEventListener('change', function () {
      var cat = catSel.value;
      var block = form.querySelector('.ap-variant-block');
      if (block) {
        block.classList.toggle('ap-variant-block--chain', cat === 'chain');
        var head = block.querySelector('.ap-variant-head');
        if (head) head.outerHTML = variantHeadHtml(cat);
      }
      var preserved = [];
      grid.querySelectorAll('.ap-variant-row').forEach(function (row) {
        var totalEl = row.querySelector('[name="sideStoneTotal"]');
        preserved.push({
          gold: row.querySelector('[name="gold"]')?.value,
          carat: row.querySelector('[name="carat"]')?.value,
          weight_chin: row.querySelector('[name="weight"]')?.value,
          manual_price_twd: row.querySelector('[name="price"]')?.value,
          side_stone_price_twd: row.querySelector('[name="sideStonePrice"]')?.value,
          side_stone_carat: row.querySelector('[name="sideStoneCarat"]')?.value,
          side_stone_total_twd: totalEl && totalEl.dataset.fixed === '1'
            ? totalEl.value
            : null,
        });
      });
      var chainType = getFormChainType(form);
      grid.innerHTML = (preserved.length ? preserved : [null]).map(function (v) {
        return variantRowHtml(v, cat, chainType);
      }).join('');
      bindRemoveRows();
      var host = document.getElementById('apImageSlots');
      var hint = form.querySelector('.ap-section-hint');
      if (host) {
        resetDeferredImages();
        var currentImages = [];
        form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
          var color = slotColorKey(slot);
          slot.querySelectorAll('.ap-carousel-item[data-url]').forEach(function (item) {
            var url = persistableImageUrl(item.dataset.url, color);
            if (url) currentImages.push({ color: color, file_path: url });
          });
        });
        _slotCounter = 0;
        host.innerHTML = imageSlotsHtml(currentImages, cat);
        bindImageSlots(form);
      }
      if (hint) {
        hint.textContent = '試算頁會依「金屬 × 鑽石顏色」切換商品圖'
          + (cat === 'pendant' ? '；含鍊預覽沿用項墜金屬色（無需另傳異色鍊圖）' : '')
          + '。請為需要的金屬 × 鑽石組合上傳商品照片。';
      }
      var sellModes = document.getElementById('apPendantSellModes');
      if (sellModes) sellModes.hidden = cat !== 'pendant';
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      clearAutosaveTimer();
      _autosave.queued = false;
      if (_autosave.waitTimer) {
        clearInterval(_autosave.waitTimer);
        _autosave.waitTimer = null;
      }
      function runManualSave() {
        saveProduct(form, editorCtx, { autosave: false });
      }
      if (_autosave.inFlight) {
        // Wait for in-flight autosave, then manual save once.
        _autosave.waitTimer = setInterval(function () {
          if (_autosave.inFlight) return;
          clearInterval(_autosave.waitTimer);
          _autosave.waitTimer = null;
          if (state.view !== 'editor') return;
          runManualSave();
        }, 50);
        return;
      }
      runManualSave();
    });

    form.querySelector('[name="saveForLater"]')?.addEventListener('change', function () {
      updateSaveButton(form, !!editorCtx.product);
      scheduleAutosave();
    });
    updateSaveButton(form, !!editorCtx.product);
    bindAutosave(form, editorCtx);
  }

  function renderEditor(product, defaultCategory) {
    _slotCounter = 0;
    unmountProductsTable();
    setRoot(editorFormHtml(product, defaultCategory));
    bindEditorEvents(product);
    root.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }

  function openEditor(product, defaultCategory) {
    state.view = 'editor';
    state.editingId = product ? product.id : null;
    renderEditor(product, defaultCategory);
  }

  function isValidImageKey(key) {
    return /^[a-z0-9][a-z0-9_-]{0,31}$/.test(key);
  }

  function collectForm(form) {
    var fd = new FormData(form);
    var category = fd.get('category');
    var variants = [];
    form.querySelectorAll('#apVariantGrid .ap-variant-row').forEach(function (row) {
      var gold = row.querySelector('[name="gold"]')?.value;
      var carat = row.querySelector('[name="carat"]')?.value;
      var weight = row.querySelector('[name="weight"]')?.value;
      var price = row.querySelector('[name="price"]')?.value;
      var sideStone = row.querySelector('[name="sideStonePrice"]')?.value;
      var sideStoneCts = row.querySelector('[name="sideStoneCarat"]')?.value;
      var sideStoneTotalEl = row.querySelector('[name="sideStoneTotal"]');
      var sideStoneTotal = sideStoneTotalEl ? sideStoneTotalEl.value : '';
      var sideStoneTotalFixed = !!(sideStoneTotalEl && sideStoneTotalEl.dataset.fixed === '1');
      if (!gold || !carat) return;
      // Chain: wax in 長度蠟重; no 配鑽 / no per-variant 46cm wax field.
      if (category !== 'chain' && !weight) return;
      var isChain = category === 'chain';
      variants.push({
        gold: gold,
        carat: carat,
        weightChin: isChain ? null : parseFloat(weight),
        manualPriceTwd: price === '' || price == null ? null : parseFloat(price),
        sideStonePriceTwd: isChain || sideStone === '' || sideStone == null
          ? null
          : parseFloat(sideStone),
        sideStoneCarat: isChain || sideStoneCts === '' || sideStoneCts == null
          ? null
          : parseFloat(sideStoneCts),
        sideStoneTotalTwd: isChain || !sideStoneTotalFixed
          || sideStoneTotal === '' || sideStoneTotal == null
          ? null
          : parseFloat(sideStoneTotal),
      });
    });
    var images = [];
    form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
      var color = slotColorKey(slot);
      if (!color) return;
      slot.querySelectorAll('.ap-carousel-item[data-url]').forEach(function (item) {
        var url = persistableImageUrl(item.dataset.url, color);
        if (url) images.push({ color: color, url: url });
      });
    });
    var allowsEngravingInput = form.querySelector('[name="allowsEngraving"]');
    var allowsFancyShapesInput = form.querySelector('[name="allowsFancyShapes"]');
    var sellWithChainInput = form.querySelector('[name="sellWithChain"]');
    var chainOnly = !!(sellWithChainInput && sellWithChainInput.checked);
    // Left: both modes → shop shows choose switch. Right: chain-only.
    var allowsPendantOnly = category === 'pendant' ? !chainOnly : true;
    var allowsWithChain = true;
    return {
      category: category,
      nameZh: String(fd.get('nameZh') || '').trim(),
      nameEn: String(fd.get('nameEn') || '').trim(),
      descriptionZh: String(fd.get('descriptionZh') || '').trim(),
      descriptionEn: String(fd.get('descriptionEn') || '').trim(),
      defaultColor: fd.get('defaultColor') || 'white',
      allowsEngraving: !!(allowsEngravingInput && allowsEngravingInput.checked),
      allowsFancyShapes: !!(allowsFancyShapesInput && allowsFancyShapesInput.checked),
      allowsPendantOnly: allowsPendantOnly,
      allowsWithChain: allowsWithChain,
      isPublished: !isSaveForLater(form),
      variants: variants,
      lengthWeights: category === 'chain' ? collectChainLengthWeights(form) : null,
      chainType: category === 'chain' ? getFormChainType(form) : null,
      images: images,
    };
  }

  function validateProductPayload(form, payload, isDraft) {
    if (!payload.nameEn) {
      return { error: '請填寫英文名稱（資料用，必填）', focus: '[name="nameEn"]' };
    }
    // 儲存草稿不要求中文／照片；只有正式上架才需要完整資料。
    if (!isDraft) {
      if (!payload.nameZh) {
        return { error: '請填寫中文名稱（必填）', focus: '[name="nameZh"]' };
      }
      var slotKeys = [];
      var slotError = '';
      form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
        var key = slotColorKey(slot);
        if (!key) {
          slotError = '請為每個圖片選項設定代碼';
          return;
        }
        if (!isValidImageKey(key)) {
          slotError = '圖片選項代碼僅能使用英文小寫、數字、底線或連字號';
          return;
        }
        if (slotKeys.indexOf(key) >= 0) {
          slotError = '圖片選項代碼不可重複：' + key;
          return;
        }
        slotKeys.push(key);
      });
      if (slotError) return { error: slotError };
    }
    return null;
  }

  function saveProduct(form, ctx, opts) {
    opts = opts || {};
    var isAutosave = !!opts.autosave;
    var product = ctx && ctx.product;
    var payload = collectForm(form);
    if (product) payload.id = product.id;
    var btn = document.getElementById('apSaveProduct');
    var errEl = document.getElementById('apFormError');
    var isDraft = isSaveForLater(form);
    if (isAutosave) {
      // Autosave is draft/temp only — never flip shop visibility from the checkbox.
      payload.isPublished = product ? !!product.is_published : false;
      payload.autosave = true;
      isDraft = true;
    }

    var validation = validateProductPayload(form, payload, isDraft);
    if (validation) {
      if (isAutosave) return Promise.resolve({ skipped: true });
      if (errEl) {
        errEl.textContent = validation.error;
        errEl.hidden = false;
      }
      if (validation.focus) form.querySelector(validation.focus)?.focus();
      return Promise.resolve({ skipped: true, errorShown: true });
    }

    if (errEl) errEl.hidden = true;
    if (isAutosave) setAutosaveStatus('自動儲存中…');
    if (!isAutosave && btn) {
      btn.disabled = true;
      btn.textContent = '儲存中…';
    }
    var toastId = null;
    if (!isAutosave && window.Toast) {
      toastId = window.Toast.create({
        type: 'loading',
        title: isDraft ? '草稿儲存中…' : '商品上架中…',
        description: '正在將商品資料寫入後台，請稍候。',
        duration: Infinity
      });
    }
    if (!isAutosave) _autosave.inFlight = true;

    var req = product ? api.admin.updateProduct(payload) : api.admin.saveProduct(payload);
    return req.then(function (res) {
      if (!isAutosave) _autosave.inFlight = false;
      if (!isAutosave && btn) {
        btn.disabled = false;
        updateSaveButton(form, !!(ctx && ctx.product));
      }
      if (res.error) {
        if (!isAutosave) {
          if (errEl) {
            errEl.textContent = apiError(res);
            errEl.hidden = false;
          } else {
            alert(apiError(res));
          }
          if (toastId && window.Toast) {
            window.Toast.update(toastId, {
              type: 'error',
              title: isDraft ? '草稿儲存失敗' : '商品上架失敗',
              description: apiError(res),
              duration: 6000
            });
          }
        }
        return { error: true, message: apiError(res) };
      }

      if (res.product && ctx) {
        ctx.product = res.product;
        state.editingId = res.product.id;
        syncEditorImagesFromProduct(form, res.product.images || []);
      }

      if (isAutosave) {
        if (btn) updateSaveButton(form, !!(ctx && ctx.product));
        // Keep editor open; quietly refresh list cache for when user returns.
        load(true, true);
        return { ok: true };
      }

      if (toastId && window.Toast) {
        window.Toast.update(toastId, {
          type: 'success',
          title: isDraft ? '草稿已儲存！' : '商品上架完成！',
          description: payload.nameZh ? payload.nameZh : '',
          duration: 4000
        });
      }
      clearAutosave();
      state.view = 'list';
      state.editingId = null;
      load(true, true);
      return { ok: true };
    });
  }

  function fetchProducts() {
    return new Promise(function (resolve) {
      var done = false;
      var timer = setTimeout(function () {
        if (done) return;
        done = true;
        resolve({ error: '載入逾時，請檢查網路後重試。', timeout: true });
      }, LOAD_TIMEOUT_MS);
      api.admin.getProducts().then(function (res) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        resolve(res);
      });
    });
  }

  function load(silent, force) {
    if (_loading && !force) {
      if (!silent && state.view !== 'editor') showLoadingSkeleton();
      return;
    }
    if (_loaded && !force && state.view === 'editor') return;
    if (_loaded && !force) {
      if (state.view === 'list') renderShell();
      return;
    }

    if (!silent && state.view !== 'editor') showLoadingSkeleton();

    _loading = true;
    fetchProducts().then(function (res) {
      _loading = false;
      if (res.error) {
        unmountProductsTable();
        var retry = res.timeout
          ? ' <button type="button" class="btn-sm" id="apRetryLoad">重試</button>'
          : '';
        root.innerHTML = '<p class="note warn">載入失敗：' + esc(apiError(res)) + retry + '</p>';
        var retryBtn = document.getElementById('apRetryLoad');
        if (retryBtn) retryBtn.addEventListener('click', function () { load(false, true); });
        return;
      }
      state.products = res.products || [];
      state.categoryLabels = res.categoryLabels || {};
      state.categories = res.categories || [];
      state.categoryOrder = res.categoryOrder || categoryOrderList();
      state.chainCatalog = res.chainCatalog || state.chainCatalog;
      if (state.categoryOrder.indexOf(state.activeTab.replace('cat-', '')) < 0 && state.categoryOrder.length) {
        state.activeTab = 'cat-' + state.categoryOrder[0];
      }
      _loaded = true;
      if (state.view === 'editor') return;
      renderShell();
    });
  }

  function prefetch() {
    if (_loaded || _loading) return;
    load(true, false);
  }

  function ensureLoaded() {
    if (_loaded) {
      if (state.view === 'list') renderShell();
      return;
    }
    load(false, false);
  }

  window.AdminProductsPanel = { load: load, ensureLoaded: ensureLoaded, prefetch: prefetch };

  if (root && !root.innerHTML.trim() && window.SkeletonUI) {
    showLoadingSkeleton();
  }
})();
