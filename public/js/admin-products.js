/* 銘印鑽石｜商品上架管理 */
(function () {
  'use strict';

  var api = window.imprintAPI;
  if (!api || !api.admin) return;

  var CATEGORY_ORDER = ['diamond', 'pendant', 'ring', 'earring', 'bracelet', 'chain'];
  var GOLDS = ['9k', '14k', '18k', 'pt950', 's925'];
  var CARATS = [
    '0.1', '0.2', '0.3', '0.5', '0.6', '0.7', '0.8', '0.9', '1.0',
    '1.5', '2.0', '3.0',
  ];
  var CHAIN_CARATS = ['1.0mm', '1.5mm', '2.0mm', '2.5mm', '3.0mm'];
  var CHAIN_LENGTHS_CM = [36, 41, 46, 51, 61, 76, 80];
  // Positive integer floor only — no hard upper ceiling.
  var RING_SIZE_MIN = 1;
  // Soft UX placeholders / omitted-max default (not a hard reject ceiling).
  var RING_SIZE_SOFT_MIN = 5;
  var RING_SIZE_SOFT_MAX = 18;
  var COLORS = ['white', 'yellow', 'rose'];
  var GOLD_LABELS = { '9k': '9K', '14k': '14K', '18k': '18K', 'pt950': 'PT950', 's925': 'S925' };
  // 蠟重(錢) × factor → 成品金重(錢)；試算頁下單時以後端 app/pricing.py 的同一份係數為準，這裡僅供上架時預覽估算。
  var WAX_TO_METAL_CHIN = { '9k': 11.5, '14k': 14.0, '18k': 16.0, 'pt950': 24.0, 's925': 11.0 };
  var COLOR_LABELS = { white: '白金', yellow: '黃金', rose: '玫瑰金' };
  var DIAMOND_COLOR_LABELS = { white: '白鑽', yellow: '黃鑽', blue: '藍鑽', pink: '粉鑽' };
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
  // Memorial diamond product = gem color; image slots = cut shapes (same as shop 選擇鑽石切工).
  // Built-in fallback; live list grows from API diamondShapes (incl. Asscher + custom cuts).
  var DIAMOND_SHAPE_SLOT_OPTIONS = [
    { value: 'round', label: '圓形' },
    { value: 'marquise', label: '馬眼型' },
    { value: 'oval', label: '橢圓形' },
    { value: 'princess', label: '公主方' },
    { value: 'trilliant', label: '三角形' },
    { value: 'emerald', label: '祖母綠形' },
    { value: 'heart', label: '心形' },
    { value: 'radiant', label: '雷地恩形' },
    { value: 'pear', label: '梨形' },
    { value: 'cushion', label: '枕形' },
    { value: 'asscher', label: '阿斯切' },
  ];
  var NEW_SHAPE_VALUE = '__new__';
  var METAL_SLOT_VALUES = METAL_SLOT_OPTIONS.map(function (o) { return o.value; });
  var DIAMOND_SLOT_VALUES = DIAMOND_SLOT_OPTIONS.map(function (o) { return o.value; });
  var DIAMOND_SHAPE_SLOT_VALUES = DIAMOND_SHAPE_SLOT_OPTIONS.map(function (o) { return o.value; });

  function diamondShapeOptionsLive() {
    var rows = state.diamondShapes;
    if (rows && rows.length) {
      return rows.map(function (row) {
        return {
          value: String(row.id || row.value || ''),
          label: String(row.labelZh || row.label_zh || row.label || row.id || ''),
        };
      }).filter(function (o) { return o.value; });
    }
    return DIAMOND_SHAPE_SLOT_OPTIONS.slice();
  }

  function diamondShapeValuesLive() {
    return diamondShapeOptionsLive().map(function (o) { return o.value; });
  }

  function isKnownDiamondShape(key) {
    var k = String(key || '').toLowerCase();
    if (!k || k === NEW_SHAPE_VALUE) return false;
    if (diamondShapeValuesLive().indexOf(k) >= 0) return true;
    // Allow custom slug not yet in cached list (just created / other tab).
    return /^[a-z][a-z0-9-]{0,40}$/.test(k)
      && ['other', 'white', 'yellow', 'blue', 'pink', 'rose', 'new', 'custom'].indexOf(k) < 0;
  }

  function rememberDiamondShape(shape) {
    if (!shape || !shape.id) return;
    state.diamondShapes = state.diamondShapes || [];
    if (state.diamondShapes.some(function (s) { return s.id === shape.id; })) return;
    state.diamondShapes.push({
      id: shape.id,
      labelZh: shape.labelZh || shape.label_zh || shape.id,
      labelEn: shape.labelEn || shape.label_en || shape.id,
      label_zh: shape.labelZh || shape.label_zh || shape.id,
      label_en: shape.labelEn || shape.label_en || shape.id,
    });
  }
  // Shop memorial color product keys — seeded for admin name/shape-image edits.
  var MEMORIAL_DIAMOND_STYLE_KEYS = [
    'diamond-white',
    'diamond-yellow',
    'diamond-blue',
    'diamond-pink',
  ];

  // Match server _ALLOWED_IMAGE_EXT: JPG / PNG / WEBP. Source ≤1MB; stored ≤500KB WebP.
  var IMAGE_ACCEPT = 'image/jpeg,image/png,image/webp';
  var IMAGE_MIME_OK = { 'image/jpeg': 1, 'image/png': 1, 'image/webp': 1 };
  var IMAGE_EXT_OK = { '.jpg': 1, '.jpeg': 1, '.png': 1, '.webp': 1 };
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
      if (!isAllowedImageFile(list[i])) return '僅支援 JPG / PNG / WEBP';
      if (list[i].size > MAX_IMAGE_BYTES) return '來源圖片需小於 1MB';
    }
    return '';
  }

  /** UTF-8 → base64url (matches server app.storage.encode_unicode_filename_stem). */
  function utf8ToBase64Url(str) {
    var bytes = new TextEncoder().encode(String(str || ''));
    var bin = '';
    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
  }

  /**
   * Supabase Storage rejects raw Chinese keys. Rename File to ASCII `u-<base64url>`
   * before upload so the carousel can show after success.
   */
  function storageSafeUploadFile(file) {
    if (!file || !file.name) return file;
    var name = String(file.name);
    if (!/[^\x00-\x7F]/.test(name)) return file;
    if (/^u-[A-Za-z0-9_-]+\.[A-Za-z0-9]+$/.test(name)) return file;
    var ext = imageFileExt(name) || '.webp';
    var stem = name.slice(0, Math.max(0, name.length - ext.length)) || 'image';
    var safeName = 'u-' + utf8ToBase64Url(stem) + ext;
    try {
      return new File([file], safeName, {
        type: file.type || 'application/octet-stream',
        lastModified: file.lastModified || Date.now(),
      });
    } catch (e) {
      return file;
    }
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
    if (category === 'diamond') {
      return diamondShapeValuesLive();
    }
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
    categoryCounts: {},
    diamondShapes: DIAMOND_SHAPE_SLOT_OPTIONS.map(function (o) {
      return { id: o.value, labelZh: o.label, labelEn: o.value, label_zh: o.label, label_en: o.value };
    }),
    listTotal: 0,
    chainCatalog: null,
    activeTab: 'cat-diamond',
    editingId: null,
    view: 'list',
  };
  var _pageIndex = 0;
  var _pageSize = 10;
  var _loaded = false;
  var _loading = false;
  var _loadSeq = 0;
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

  /**
   * Cache-buster for admin previews only — data-url keeps the clean URL so a
   * busted URL is never persisted. product_images has no updated_at column, so
   * the shared save epoch (bumped after a replace) is the version source.
   */
  function bustImageUrl(url, updatedAt) {
    return window.AdminImageUrls && window.AdminImageUrls.bust
      ? window.AdminImageUrls.bust(url, updatedAt)
      : String(url || '').trim();
  }

  function bumpImageCacheEpoch() {
    if (window.AdminImageUrls && window.AdminImageUrls.bumpEpoch) {
      window.AdminImageUrls.bumpEpoch();
    }
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
    // productPhoto can be picky; keep absolute Storage / https image URLs.
    if (
      (!resolved || isDeadCatalogPlaceholder(resolved))
      && /^https?:\/\//i.test(String(path).trim())
      && /\.(png|jpe?g|webp)(\?|#|$)/i.test(String(path).trim())
    ) {
      resolved = String(path).trim();
    }
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

  function imageCoversDefaultColor(imageColor, defaultColor, category) {
    var key = String(imageColor || '').toLowerCase();
    var def = String(defaultColor || '').toLowerCase();
    if (!key || !def) return false;
    if (category === 'diamond') {
      // Product defaultColor is gem color; image slots are shapes.
      if (DIAMOND_SLOT_VALUES.indexOf(def) < 0) return false;
      return isKnownDiamondShape(key);
    }
    if (COLORS.indexOf(def) < 0) return false;
    return key === def || key.indexOf(def + '-') === 0;
  }

  function productThumb(product) {
    var images = product.images || [];
    var def = product.default_color || 'white';
    var match = null;
    if (product.category === 'diamond') {
      match = images.find(function (img) { return img.color === 'round'; })
        || images.find(function (img) {
          return imageCoversDefaultColor(img.color, def, product.category);
        });
    } else {
      match = images.find(function (img) {
        return imageCoversDefaultColor(img.color, def, product.category);
      });
    }
    match = match || images[0];
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
    // Memorial diamond: name + image + color only (no metal/price variants).
    if (product.category !== 'diamond' && !variants.length) {
      return { ok: false, reason: '請先新增至少一個款式選項' };
    }
    if (!images.length) return { ok: false, reason: '請先上傳至少一張商品照片' };
    var def = product.default_color || 'white';
    if (!images.some(function (img) {
      return imageCoversDefaultColor(img.color, def, product.category);
    })) {
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

  function categoryAddonValue(slug) {
    var info = categoryInfo(slug);
    if (!info) return 0;
    var raw = info.addonPrice != null ? info.addonPrice : info.addon_price_twd;
    var n = Number(raw);
    return Number.isFinite(n) && n >= 0 ? Math.round(n) : 0;
  }

  function categoryRingSizeConfig(slug) {
    var info = categoryInfo(slug);
    if (!info) return null;
    return info.ringSizeConfig || info.ring_size_config || null;
  }

  function categoryRingSizeSectionHtml(cat) {
    if (cat !== 'ring') return '';
    var cfg = categoryRingSizeConfig(cat);
    var minSize = ringSizeFieldValue(cfg, 'minSize', 'min_size', 'startSize', 'start_size');
    var maxSize = ringSizeFieldValue(cfg, 'maxSize', 'max_size');
    if (maxSize === '' && cfg) maxSize = RING_SIZE_SOFT_MAX;
    var chargeAfter = ringSizeFieldValue(
      cfg, 'chargeAfter', 'charge_after', 'priceFromSize', 'price_from_size'
    );
    if (chargeAfter === '' && minSize !== '') chargeAfter = minSize;
    var pricePer = ringSizeFieldValue(cfg, 'pricePerSizeTwd', 'price_per_size_twd');
    return (
      '<div id="apRingSizeSection" class="ap-category-ring-block" data-slug="' + esc(cat) + '">' +
        '<h4 class="ap-category-addon-label">戒圍設定</h4>' +
        '<p class="ap-category-addon-hint ap-category-ring-hint">' +
          'N ≤ 從多少之後開始加價 → 加價 0；否則 (N − 閾值) × 加多少。須為 ≥ 1 的整數，且最小 ≤ 最大、加價閾值在區間內。與品項加價分開疊加。' +
        '</p>' +
        '<div class="ap-category-ring-row">' +
          '<label><span>最小</span>' +
            '<input type="number" id="apCategoryRingMin" name="ringMinSize" min="' + RING_SIZE_MIN +
              '" step="1" placeholder="' + RING_SIZE_SOFT_MIN +
              '" value="' + esc(minSize) + '">' +
          '</label>' +
          '<label><span>最大</span>' +
            '<input type="number" id="apCategoryRingMax" name="ringMaxSize" min="' + RING_SIZE_MIN +
              '" step="1" placeholder="' + RING_SIZE_SOFT_MAX +
              '" value="' + esc(maxSize) + '">' +
          '</label>' +
          '<label><span>從多少之後開始加價</span>' +
            '<input type="number" id="apCategoryRingChargeAfter" name="ringChargeAfter" min="' +
              RING_SIZE_MIN + '" step="1" placeholder="' +
              esc(minSize || RING_SIZE_SOFT_MIN) + '" value="' + esc(chargeAfter) + '">' +
          '</label>' +
          '<label><span>加多少 (NT$)</span>' +
            '<input type="number" id="apCategoryRingPricePer" name="ringPricePerSize" min="0" step="1" ' +
              'placeholder="0" value="' + esc(pricePer) + '">' +
          '</label>' +
          '<button type="button" class="btn-sm btn-primary" id="apCategoryRingSizeSave">儲存</button>' +
        '</div>' +
        '<p class="ap-category-addon-hint" id="apCategoryRingSizeStatus" hidden></p>' +
      '</div>'
    );
  }

  function categoryPanelHtml() {
    var cat = state.activeTab.replace('cat-', '');
    var label = state.categoryLabels[cat] || cat;
    var published = publishedCountInCategory(cat);
    var thumb = categoryThumbUrl(cat);
    var addon = categoryAddonValue(cat);
    return (
      '<div class="ap-category-header">' +
        '<div class="ap-category-panel" id="apCategoryPanel">' +
          '<div class="ap-category-panel-inner">' +
            '<div class="ap-category-panel-text">' +
              '<h4 class="ap-section-title ap-section-title--inline">' + esc(label) + ' · 試算頁 Step 1 品項圖</h4>' +
              '<p class="ap-section-hint">此圖顯示於客製試算「選品項」步驟。' +
              '品項需至少有一件<strong>已上架</strong>商品才會出現在試算頁' +
              (published ? '（目前 ' + published + ' 件已上架）。' : '（尚無已上架商品，試算頁不會顯示此品項）。') +
              '</p>' +
            '</div>' +
            '<div class="ap-category-thumb-row">' +
              '<div class="ap-category-thumb-block">' +
                '<div class="ap-category-thumb-preview">' +
                  (thumb
                    ? '<img src="' + esc(thumb) + '" alt="" loading="lazy" decoding="async">'
                    : '<span class="ap-category-thumb-empty">預設圖</span>') +
                '</div>' +
                '<label class="btn-sm ap-category-thumb-upload">' +
                  '更換圖片' +
                  '<input type="file" accept="' + IMAGE_ACCEPT + '" hidden id="apCategoryThumbInput">' +
                '</label>' +
              '</div>' +
              '<button type="button" class="btn-sm ap-category-delete-btn" id="apDeleteCategoryBtn" data-slug="' + esc(cat) + '" data-label="' + esc(label) + '">刪除此品項</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
        '<div class="ap-category-pricing-row">' +
          '<div class="ap-category-addon-block" data-slug="' + esc(cat) + '">' +
            '<label class="ap-category-addon-label" for="apCategoryAddonInput">品項加價 (NT$)</label>' +
            '<div class="ap-category-addon-row">' +
              '<input type="number" id="apCategoryAddonInput" class="ap-category-addon-input" ' +
                'min="0" step="1" inputmode="numeric" value="' + addon + '" data-slug="' + esc(cat) + '">' +
              '<button type="button" class="btn-sm btn-primary" id="apCategoryAddonSave">儲存</button>' +
              '<button type="button" class="btn-sm" id="apCategoryAddonForce">強制覆蓋</button>' +
            '</div>' +
            '<p class="ap-category-addon-hint" id="apCategoryAddonStatus" hidden></p>' +
          '</div>' +
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

  function addDiamondShapeDialogHtml() {
    return (
      '<dialog id="apAddDiamondShapeDialog" class="ap-delete-dialog">' +
        '<form method="dialog" id="apAddDiamondShapeForm">' +
          '<h3>新增鑽石切工</h3>' +
          '<label class="ap-add-cat-label"><span>中文名稱</span>' +
            '<input id="apNewShapeLabelZh" maxlength="50" autocomplete="off" required placeholder="例如：阿斯切">' +
          '</label>' +
          '<label class="ap-add-cat-label"><span>英文名稱（選填，作代號）</span>' +
            '<input id="apNewShapeLabelEn" maxlength="80" autocomplete="off" placeholder="例如：Asscher">' +
          '</label>' +
          '<p class="ap-hint">建立後可在紀念鑽石圖片選項選擇，並顯示於試算頁切工列表。</p>' +
          '<p class="ap-form-error" id="apAddDiamondShapeError" hidden></p>' +
          '<div class="ap-delete-actions">' +
            '<button type="button" class="btn-sm" id="apAddDiamondShapeCancel">取消</button>' +
            '<button type="submit" class="btn-sm btn-primary">建立</button>' +
          '</div>' +
        '</form>' +
      '</dialog>'
    );
  }

  function ensureAddDiamondShapeDialog() {
    var dialog = document.getElementById('apAddDiamondShapeDialog');
    if (dialog) return dialog;
    var wrap = document.createElement('div');
    wrap.innerHTML = addDiamondShapeDialogHtml();
    dialog = wrap.firstElementChild;
    document.body.appendChild(dialog);
    return dialog;
  }

  /**
   * Prompt for a new cut name. Resolves with shape row or null if cancelled.
   */
  function promptCreateDiamondShape() {
    return new Promise(function (resolve) {
      var dialog = ensureAddDiamondShapeDialog();
      var form = document.getElementById('apAddDiamondShapeForm');
      var errEl = document.getElementById('apAddDiamondShapeError');
      var zhInput = document.getElementById('apNewShapeLabelZh');
      var enInput = document.getElementById('apNewShapeLabelEn');
      var cancelBtn = document.getElementById('apAddDiamondShapeCancel');
      if (!dialog || !form || !zhInput) {
        resolve(null);
        return;
      }
      var settled = false;
      function finish(value) {
        if (settled) return;
        settled = true;
        form.onsubmit = null;
        if (cancelBtn) cancelBtn.onclick = null;
        try { dialog.close(); } catch (e) { /* ignore */ }
        resolve(value);
      }
      if (errEl) { errEl.hidden = true; errEl.textContent = ''; }
      zhInput.value = '';
      if (enInput) enInput.value = '';
      cancelBtn.onclick = function () { finish(null); };
      form.onsubmit = function (ev) {
        if (ev && ev.preventDefault) ev.preventDefault();
        var labelZh = zhInput.value.trim();
        var labelEn = enInput ? enInput.value.trim() : '';
        if (!labelZh) {
          if (errEl) { errEl.textContent = '請填寫切工名稱'; errEl.hidden = false; }
          return;
        }
        if (!api.admin.createDiamondShape) {
          if (errEl) { errEl.textContent = '請強制重新整理頁面後再試'; errEl.hidden = false; }
          return;
        }
        api.admin.createDiamondShape({ labelZh: labelZh, labelEn: labelEn || undefined }).then(function (res) {
          if (res.error || !res.shape) {
            if (errEl) {
              errEl.textContent = res.error || '建立失敗';
              errEl.hidden = false;
            }
            return;
          }
          rememberDiamondShape(res.shape);
          finish(res.shape);
        }, function () {
          if (errEl) { errEl.textContent = '建立失敗'; errEl.hidden = false; }
        });
      };
      if (typeof dialog.showModal === 'function') dialog.showModal();
      else dialog.setAttribute('open', '');
      zhInput.focus();
    });
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

  function chainThicknessKey(raw) {
    var value = String(raw == null ? '' : raw).trim().replace(/mm$/i, '').trim();
    return value ? value + 'mm' : '';
  }

  function chainThicknessDisplay(raw) {
    return String(raw == null ? '' : raw).trim().replace(/mm$/i, '').trim();
  }

  function chainThicknessesForForm(form, chainType, lengthWeights) {
    var values = chainTypeThicknesses(chainType).slice();
    Object.keys(lengthWeights || {}).forEach(function (thick) {
      if (values.indexOf(String(thick)) < 0) values.push(String(thick));
    });
    if (form) {
      form.querySelectorAll('#apVariantGrid [name="carat"]').forEach(function (input) {
        var thick = chainThicknessKey(input.value);
        if (thick && values.indexOf(thick) < 0) values.push(thick);
      });
    }
    return values;
  }

  function syncChainVariantThicknessOptions(form) {
    if (!form) return;
    var category = (form.querySelector('#apCategory') || {}).value
      || (form.elements && form.elements.category && form.elements.category.value)
      || '';
    if (category !== 'chain') return;
    var options = [];
    form.querySelectorAll('#apChainLengthWeights .ap-chain-thickness-block').forEach(function (block) {
      var thick = String(block.dataset.thickness || '').trim();
      if (thick && options.indexOf(thick) < 0) options.push(thick);
    });
    if (!options.length) options = chainTypeThicknesses(getFormChainType(form)).slice();
    form.querySelectorAll('#apVariantGrid [name="carat"]').forEach(function (control) {
      var current = control.tagName === 'SELECT' ? control.value : chainThicknessKey(control.value);
      var select = control;
      if (control.tagName !== 'SELECT') {
        select = document.createElement('select');
        select.name = 'carat';
        var legacyUnit = control.closest('.ap-thickness-input');
        if (legacyUnit) legacyUnit.replaceWith(select);
        else control.replaceWith(select);
      }
      var values = options.slice();
      select.innerHTML = values.map(function (thick) {
        return '<option value="' + esc(thick) + '">' + esc(thick) + '</option>';
      }).join('');
      select.value = values.indexOf(current) >= 0 ? current : '';
    });
  }

  function productsInCategory(cat) {
    return state.products.filter(function (p) { return p.category === cat; });
  }

  function categoryCount(cat) {
    if (state.categoryCounts && state.categoryCounts[cat] != null) {
      return Number(state.categoryCounts[cat]) || 0;
    }
    return productsInCategory(cat).length;
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
      var count = categoryCount(cat);
      var active = state.activeTab === 'cat-' + cat;
      return '<button type="button" class="ap-tab-btn' + (active ? ' is-active' : '') + '" data-tab="cat-' + cat + '" role="tab" aria-selected="' + (active ? 'true' : 'false') + '">' +
        esc(label) + '<span class="ap-tab-count">' + count + '</span></button>';
    }).join('');
    tabs += '<button type="button" class="ap-tab-btn ap-tab-btn--add" id="apAddCategory" title="新增品項" aria-label="新增品項">+</button>';

    setRoot(
      '<p class="note">管理商品款式、金屬選項與照片。上架後會顯示於客製試算頁；拖曳列可調整排序。</p>' +
      '<p class="note ap-memorial-note">紀念鑽石：編輯款式名稱、鑽石顏色與照片以連結試算頁；不含金屬／價格（價格請用「前往價格設定」）。</p>' +
      '<div class="ap-toolbar">' +
        '<button type="button" class="btn-sm" id="btnGotoPricing">前往價格設定</button>' +
        '<button type="button" class="btn-sm btn-primary" id="btnNewProduct">+ 新增商品</button>' +
      '</div>' +
      '<div class="ap-category-tabs" role="tablist">' + tabs + '</div>' +
      categoryPanelHtml() +
      '<div class="ap-table-root" id="apProductsTableRoot">' + tableAreaSkeletonHtml() + '</div>' +
      categoryRingSizeSectionHtml(state.activeTab.replace('cat-', '')) +
      '<dialog id="apDeleteDialog" class="ap-delete-dialog"><form method="dialog" id="apDeleteForm">' +
        '<h3>刪除商品</h3><p id="apDeleteTarget"></p>' +
        '<p class="ap-hint">刪除後無法復原，若已有訂單引用建議改為下架。</p>' +
        '<div class="ap-delete-actions">' +
          '<button type="button" class="btn-sm" id="apDeleteCancel">取消</button>' +
          '<button type="submit" class="btn-sm btn-primary">確認刪除</button>' +
        '</div></form></dialog>' +
      addCategoryDialogHtml() +
      addDiamondShapeDialogHtml() +
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

  var _tablesLoadRequested = false;

  function whenAdminTablesReady(fn, tries) {
    tries = tries == null ? 120 : tries;
    if (window.AdminTables) {
      fn();
      return;
    }
    /* 觸發按需載入，不再空等輪詢逾時（面板也可能由側欄點擊／hash 直連開啟）。 */
    if (!_tablesLoadRequested && typeof window.__adminLoadTables === 'function') {
      _tablesLoadRequested = true;
      window.__adminLoadTables().then(null, function () {});
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
    if (!_tablesLoadRequested && typeof window.__adminLoadTables === 'function') {
      _tablesLoadRequested = true;
      window.__adminLoadTables().then(null, function () {});
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
        total: state.listTotal,
        pageIndex: _pageIndex,
        pageSize: _pageSize,
        emptyLabel: '此品項尚無商品。',
        onPaginationChange: function (pagination) {
          var nextIndex = pagination.pageIndex || 0;
          var nextSize = pagination.pageSize || _pageSize;
          if (nextIndex === _pageIndex && nextSize === _pageSize) return;
          _pageIndex = nextIndex;
          _pageSize = nextSize;
          load(true, true);
        },
        onRendered: bindProductRowEvents,
      });
    });
  }

  function bindShellEvents() {
    root.querySelectorAll('.ap-tab-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (btn.classList.contains('ap-tab-btn--add')) return;
        var nextTab = btn.dataset.tab;
        if (!nextTab) return;
        state.activeTab = nextTab;
        _pageIndex = 0;
        root.querySelectorAll('.ap-tab-btn').forEach(function (b) {
          var active = b.dataset.tab === state.activeTab;
          b.classList.toggle('is-active', active);
          b.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        unmountProductsTable();
        var tableRoot = document.getElementById('apProductsTableRoot');
        if (tableRoot) tableRoot.innerHTML = tableAreaSkeletonHtml();
        load(true, true);
        refreshCategoryPanel();
        refreshRingSizeSection();
      });
    });

    var addCatBtn = document.getElementById('apAddCategory');
    if (addCatBtn) addCatBtn.addEventListener('click', openAddCategoryDialog);

    bindCategoryThumbUpload();
    bindCategoryAddonSave();
    bindCategoryRingSizeSave();
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

    var pricingBtn = document.getElementById('btnGotoPricing');
    if (pricingBtn) {
      pricingBtn.addEventListener('click', function () {
        if (window.Admin1Shell && typeof window.Admin1Shell.switchPanel === 'function') {
          window.Admin1Shell.switchPanel('pricing');
          return;
        }
        var navBtn = document.querySelector('.side-nav button[data-panel="pricing"]');
        if (navBtn) navBtn.click();
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
      runAction(deleteId, 'delete').then(function (ok) {
        if (!ok) return;
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
    var root = panel.closest('.ap-category-header') || panel;
    var wrap = document.createElement('div');
    wrap.innerHTML = categoryPanelHtml();
    var next = wrap.firstElementChild;
    if (next) {
      root.replaceWith(next);
      bindCategoryThumbUpload();
      bindCategoryAddonSave();
      bindCategoryDeleteButton();
    }
  }

  function refreshRingSizeSection() {
    var table = document.getElementById('apProductsTableRoot');
    if (!table) return;
    var cat = state.activeTab.replace('cat-', '');
    var html = categoryRingSizeSectionHtml(cat);
    var existing = document.getElementById('apRingSizeSection');
    if (!html) {
      if (existing) existing.remove();
      return;
    }
    var wrap = document.createElement('div');
    wrap.innerHTML = html;
    var next = wrap.firstElementChild;
    if (!next) return;
    if (existing) existing.replaceWith(next);
    else table.insertAdjacentElement('afterend', next);
    bindCategoryRingSizeSave();
  }

  function setCategoryAddonStatus(msg, isError) {
    var el = document.getElementById('apCategoryAddonStatus');
    if (!el) return;
    if (!msg) {
      el.hidden = true;
      el.textContent = '';
      el.classList.remove('is-error', 'is-ok');
      return;
    }
    el.hidden = false;
    el.textContent = msg;
    el.classList.toggle('is-error', !!isError);
    el.classList.toggle('is-ok', !isError);
  }

  function saveCategoryAddon(opts) {
    opts = opts || {};
    var input = document.getElementById('apCategoryAddonInput');
    var btn = document.getElementById('apCategoryAddonSave');
    if (!input) return Promise.resolve();
    var slug = input.dataset.slug || state.activeTab.replace('cat-', '');
    var raw = String(input.value || '').trim();
    var amount = Number(raw);
    if (!Number.isFinite(amount) || amount < 0 || Math.floor(amount) !== amount) {
      setCategoryAddonStatus('請輸入非負整數', true);
      return Promise.resolve();
    }
    amount = Math.round(amount);
    if (!opts.force && amount === categoryAddonValue(slug)) {
      setCategoryAddonStatus('');
      return Promise.resolve();
    }
    if (!api.admin.updateProductCategory) {
      setCategoryAddonStatus('請強制重新整理頁面（Ctrl+F5）後再儲存', true);
      return Promise.resolve();
    }
    setCategoryAddonStatus('儲存中…', false);
    if (btn) btn.disabled = true;
    return api.admin.updateProductCategory(slug, { addonPrice: amount }).then(function (res) {
      if (btn) btn.disabled = false;
      if (res.error) {
        setCategoryAddonStatus(apiError(res), true);
        if (window.Toast) {
          window.Toast.create({ type: 'error', title: '品項加價儲存失敗', description: apiError(res) });
        }
        return;
      }
      if (!res.category || (res.category.addonPrice == null && res.category.addon_price_twd == null)) {
        setCategoryAddonStatus('儲存回應異常，請重新整理後確認', true);
        return;
      }
      var idx = (state.categories || []).findIndex(function (c) { return c.slug === slug; });
      if (idx >= 0) state.categories[idx] = res.category;
      else if (state.categories) state.categories.push(res.category);
      var live = document.getElementById('apCategoryAddonInput');
      if (live) live.value = categoryAddonValue(slug);
      setCategoryAddonStatus('已儲存', false);
      if (window.Toast) {
        window.Toast.create({ type: 'success', title: '品項加價已儲存' });
      }
    }).catch(function (err) {
      if (btn) btn.disabled = false;
      var msg = (err && err.message) ? String(err.message) : '儲存失敗，請稍後再試';
      setCategoryAddonStatus(msg, true);
      if (window.Toast) {
        window.Toast.create({ type: 'error', title: '品項加價儲存失敗', description: msg });
      }
    });
  }

  function applyForceAddonToLocalProducts(slug, amount) {
    (state.products || []).forEach(function (p) {
      if (p.category !== slug || !Array.isArray(p.variants)) return;
      p.variants.forEach(function (v) {
        v.addon_price_twd = amount;
        v.addonPriceTwd = amount;
      });
    });
  }

  function forceOverwriteCategoryAddon() {
    var input = document.getElementById('apCategoryAddonInput');
    var btn = document.getElementById('apCategoryAddonForce');
    var saveBtn = document.getElementById('apCategoryAddonSave');
    if (!input) return Promise.resolve();
    var slug = input.dataset.slug || state.activeTab.replace('cat-', '');
    var raw = String(input.value || '').trim();
    var amount = Number(raw);
    if (!Number.isFinite(amount) || amount < 0 || Math.floor(amount) !== amount) {
      setCategoryAddonStatus('請輸入非負整數', true);
      return Promise.resolve();
    }
    amount = Math.round(amount);
    if (!window.confirm('確定要以目前品項加價覆蓋此品項下所有款式列？')) {
      return Promise.resolve();
    }
    if (!api.admin.forceProductCategoryAddon) {
      setCategoryAddonStatus('請強制重新整理頁面（Ctrl+F5）後再試', true);
      return Promise.resolve();
    }
    setCategoryAddonStatus('覆蓋中…', false);
    if (btn) btn.disabled = true;
    if (saveBtn) saveBtn.disabled = true;
    return api.admin.forceProductCategoryAddon(slug, { addonPrice: amount }).then(function (res) {
      if (btn) btn.disabled = false;
      if (saveBtn) saveBtn.disabled = false;
      if (res.error) {
        setCategoryAddonStatus(apiError(res), true);
        if (window.Toast) {
          window.Toast.create({ type: 'error', title: '強制覆蓋失敗', description: apiError(res) });
        }
        return;
      }
      if (!res.category || (res.category.addonPrice == null && res.category.addon_price_twd == null)) {
        setCategoryAddonStatus('覆蓋回應異常，請重新整理後確認', true);
        return;
      }
      var idx = (state.categories || []).findIndex(function (c) { return c.slug === slug; });
      if (idx >= 0) state.categories[idx] = res.category;
      else if (state.categories) state.categories.push(res.category);
      applyForceAddonToLocalProducts(slug, categoryAddonValue(slug));
      var live = document.getElementById('apCategoryAddonInput');
      if (live) live.value = categoryAddonValue(slug);
      var n = res.updatedVariants != null ? Number(res.updatedVariants) : 0;
      var okMsg = Number.isFinite(n) ? ('已覆蓋 ' + n + ' 列款式') : '已強制覆蓋';
      setCategoryAddonStatus(okMsg, false);
      if (window.Toast) {
        window.Toast.create({ type: 'success', title: '品項加價已強制覆蓋', description: okMsg });
      }
      _loaded = false;
      load(true, true);
    }).catch(function (err) {
      if (btn) btn.disabled = false;
      if (saveBtn) saveBtn.disabled = false;
      var msg = (err && err.message) ? String(err.message) : '覆蓋失敗，請稍後再試';
      setCategoryAddonStatus(msg, true);
      if (window.Toast) {
        window.Toast.create({ type: 'error', title: '強制覆蓋失敗', description: msg });
      }
    });
  }

  function bindCategoryAddonSave() {
    var input = document.getElementById('apCategoryAddonInput');
    var btn = document.getElementById('apCategoryAddonSave');
    var forceBtn = document.getElementById('apCategoryAddonForce');
    if (input && !input.dataset.bound) {
      input.dataset.bound = '1';
      input.addEventListener('blur', function () { saveCategoryAddon(); });
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          saveCategoryAddon({ force: true });
        }
      });
    }
    if (btn && !btn.dataset.bound) {
      btn.dataset.bound = '1';
      btn.addEventListener('click', function () { saveCategoryAddon({ force: true }); });
    }
    if (forceBtn && !forceBtn.dataset.bound) {
      forceBtn.dataset.bound = '1';
      forceBtn.addEventListener('click', function () { forceOverwriteCategoryAddon(); });
    }
  }

  function setCategoryRingSizeStatus(msg, isError) {
    var el = document.getElementById('apCategoryRingSizeStatus');
    if (!el) return;
    if (!msg) {
      el.hidden = true;
      el.textContent = '';
      el.classList.remove('is-error', 'is-ok');
      return;
    }
    el.hidden = false;
    el.textContent = msg;
    el.classList.toggle('is-error', !!isError);
    el.classList.toggle('is-ok', !isError);
  }

  function collectCategoryRingSizeConfig() {
    var minEl = document.getElementById('apCategoryRingMin');
    var maxEl = document.getElementById('apCategoryRingMax');
    var chargeEl = document.getElementById('apCategoryRingChargeAfter');
    var priceEl = document.getElementById('apCategoryRingPricePer');
    if (!minEl) return null;
    var minRaw = String(minEl.value || '').trim();
    var maxRaw = maxEl ? String(maxEl.value || '').trim() : '';
    var chargeRaw = chargeEl ? String(chargeEl.value || '').trim() : '';
    var priceRaw = priceEl ? String(priceEl.value || '').trim() : '';
    if (minRaw === '' && maxRaw === '' && chargeRaw === '' && priceRaw === '') return null;
    var minSize = minRaw === '' ? null : parseInt(minRaw, 10);
    var maxSize = maxRaw === '' ? null : parseInt(maxRaw, 10);
    var chargeAfter = chargeRaw === '' ? minSize : parseInt(chargeRaw, 10);
    var pricePerSizeTwd = priceRaw === '' ? 0 : parseFloat(priceRaw);
    return {
      minSize: Number.isFinite(minSize) ? minSize : null,
      maxSize: Number.isFinite(maxSize) ? maxSize : null,
      chargeAfter: Number.isFinite(chargeAfter) ? chargeAfter : null,
      pricePerSizeTwd: Number.isFinite(pricePerSizeTwd) ? pricePerSizeTwd : 0,
    };
  }

  function validateCategoryRingSizeConfig(rc) {
    if (!rc) return null;
    var minS = rc.minSize;
    var maxS = rc.maxSize;
    var charge = rc.chargeAfter;
    var step = rc.pricePerSizeTwd;
    if (minS == null && (maxS != null || step != null || charge != null)) {
      return '請填寫最小';
    }
    if (minS != null && (!Number.isFinite(minS) || minS < RING_SIZE_MIN)) {
      return '最小須為 ≥ 1 的整數';
    }
    if (maxS != null && (!Number.isFinite(maxS) || maxS < RING_SIZE_MIN)) {
      return '最大須為 ≥ 1 的整數';
    }
    if (minS != null && maxS != null && minS > maxS) {
      return '最小不可大於最大';
    }
    if (charge != null && (!Number.isFinite(charge) || charge < RING_SIZE_MIN)) {
      return '從多少之後開始加價須為 ≥ 1 的整數';
    }
    if (
      charge != null && minS != null && maxS != null &&
      (charge < minS || charge > maxS)
    ) {
      return '從多少之後開始加價須在最小與最大之間';
    }
    if (step != null && (!Number.isFinite(Number(step)) || Number(step) < 0)) {
      return '加多少不可為負';
    }
    return null;
  }

  function saveCategoryRingSize() {
    var btn = document.getElementById('apCategoryRingSizeSave');
    var section = document.getElementById('apRingSizeSection');
    if (!section) return Promise.resolve();
    var slug = section.dataset.slug || 'ring';
    var rc = collectCategoryRingSizeConfig();
    var err = validateCategoryRingSizeConfig(rc);
    if (err) {
      setCategoryRingSizeStatus(err, true);
      return Promise.resolve();
    }
    if (!api.admin.updateProductCategory) {
      setCategoryRingSizeStatus('請強制重新整理頁面（Ctrl+F5）後再儲存', true);
      return Promise.resolve();
    }
    setCategoryRingSizeStatus('儲存中…', false);
    if (btn) btn.disabled = true;
    return api.admin.updateProductCategory(slug, { ringSizeConfig: rc }).then(function (res) {
      if (btn) btn.disabled = false;
      if (res.error) {
        setCategoryRingSizeStatus(apiError(res), true);
        if (window.Toast) {
          window.Toast.create({ type: 'error', title: '戒圍設定儲存失敗', description: apiError(res) });
        }
        return;
      }
      if (!res.category) {
        setCategoryRingSizeStatus('儲存回應異常，請重新整理後確認', true);
        return;
      }
      var idx = (state.categories || []).findIndex(function (c) { return c.slug === slug; });
      if (idx >= 0) state.categories[idx] = res.category;
      else if (state.categories) state.categories.push(res.category);
      setCategoryRingSizeStatus('已儲存', false);
      if (window.Toast) {
        window.Toast.create({ type: 'success', title: '戒圍設定已儲存' });
      }
    }).catch(function (e) {
      if (btn) btn.disabled = false;
      var msg = (e && e.message) ? String(e.message) : '儲存失敗，請稍後再試';
      setCategoryRingSizeStatus(msg, true);
      if (window.Toast) {
        window.Toast.create({ type: 'error', title: '戒圍設定儲存失敗', description: msg });
      }
    });
  }

  function bindCategoryRingSizeSave() {
    var btn = document.getElementById('apCategoryRingSizeSave');
    if (btn && !btn.dataset.bound) {
      btn.dataset.bound = '1';
      btn.addEventListener('click', function () { saveCategoryRingSize(); });
    }
    ['apCategoryRingMin', 'apCategoryRingMax', 'apCategoryRingPricePer'].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el || el.dataset.bound) return;
      el.dataset.bound = '1';
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          saveCategoryRingSize();
        }
      });
    });
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
        var msg = apiError(res);
        if (window.showToast) window.showToast(msg, 'error');
        else alert(msg);
        return false;
      }
      if (action === 'delete' && window.showToast) {
        window.showToast('已刪除商品', 'success');
      }
      load(true, true);
      return true;
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
      opts = '<option value="douyuan" selected>O字鍊</option>';
    }
    return (
      '<label class="ap-field-wide ap-chain-type-field">' +
        '<span>項鍊類型</span>' +
        '<select name="chainType" id="apChainType">' + opts + '</select>' +
        '<span class="ap-section-hint">依 Excel 鍊條價格表選擇項鍊款式。選類型後，商店「選擇鏈條長度」與報價自動用該表，不必每件商品手填。</span>' +
      '</label>'
    );
  }

  function chainLengthWeightBlockHtml(thick, lengthWeights) {
    var lengths = chainLengthsCm();
    var rows = lengths.map(function (len) {
      var val = chainLengthWaxValue(lengthWeights, thick, len);
      return (
        '<div class="ap-chain-length-row" data-thickness="' + esc(thick) + '" data-length="' + len + '">' +
          '<span class="ap-chain-length-label">' + len + ' cm</span>' +
          '<input type="number" name="chainLengthWax" step="0.0001" min="0.0001" ' +
            'data-thickness="' + esc(thick) + '" data-length="' + len + '" ' +
            'placeholder="蠟重" value="' + esc(val) + '">' +
        '</div>'
      );
    }).join('');
    return (
      '<div class="ap-chain-thickness-block" data-thickness="' + esc(thick) + '">' +
        '<h5 class="ap-chain-thickness-title">厚度</h5>' +
        '<div class="ap-chain-length-head"><span>長度</span><span>蠟重（錢）</span></div>' +
        '<div class="ap-chain-length-grid">' + rows + '</div>' +
      '</div>'
    );
  }

  function chainLengthWeightsGridInnerHtml(lengthWeights, chainType, extraThicknesses) {
    var configuredThicknesses = Object.keys(lengthWeights || {});
    var thicknesses = configuredThicknesses.length
      ? configuredThicknesses.slice()
      : chainTypeThicknesses(chainType).slice();
    (extraThicknesses || []).forEach(function (thick) {
      thick = String(thick || '').trim();
      if (thick && thicknesses.indexOf(thick) < 0) thicknesses.push(thick);
    });
    Object.keys(lengthWeights || {}).forEach(function (thick) {
      if (thicknesses.indexOf(thick) < 0) thicknesses.push(thick);
    });
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

  function chainLengthWeightsBlockHtml(lengthWeights, category, chainType, variants) {
    if (category !== 'chain') return '';
    return (
      '<h4 class="ap-section-title">長度蠟重（選填）</h4>' +
      '<p class="ap-section-hint">在此填寫各厚度×長度的蠟重（錢）。選項來自 Excel 鍊條價格表（O字鍊／抖圓鏈）。預設帶入標準值；留空格子＝用標準表。款式選項只選金屬／厚度，不再填 46cm 蠟重。</p>' +
      '<div class="ap-chain-length-weights" id="apChainLengthWeights">' +
        chainLengthWeightsGridInnerHtml(lengthWeights, chainType,
          (variants || []).map(function (variant) { return variant && variant.carat; })) +
      '</div>' +
      '<button type="button" class="btn-sm" id="apAddChainThickness">+ 新增厚度表</button> ' +
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
    host.querySelectorAll('.ap-chain-thickness-block').forEach(function (block) {
      var title = block.querySelector('.ap-chain-thickness-title');
      if (!title || title.dataset.editable) return;
      var input = document.createElement('input');
      input.type = 'text';
      input.name = 'chainThickness';
      input.value = chainThicknessDisplay(block.dataset.thickness);
      input.maxLength = 16;
      input.inputMode = 'decimal';
      input.required = true;
      input.dataset.previousThickness = block.dataset.thickness || '';
      title.textContent = '厚度 ';
      title.appendChild(input);
      title.appendChild(document.createTextNode(' mm'));
      var remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'ap-remove-chain-thickness';
      remove.textContent = '刪除';
      remove.title = '刪除此厚度表';
      title.appendChild(remove);
      title.dataset.editable = '1';
      input.addEventListener('input', function () {
        if (input.dataset.previousThickness == null) {
          input.dataset.previousThickness = block.dataset.thickness || '';
        }
        var thickness = chainThicknessKey(input.value);
        block.dataset.thickness = thickness;
        block.querySelectorAll('[data-thickness]').forEach(function (el) {
          el.dataset.thickness = thickness;
        });
        form.querySelectorAll('#apVariantGrid [name="carat"]').forEach(function (select) {
          if (select.value !== input.dataset.previousThickness &&
              select.dataset.tableThickness !== input.dataset.previousThickness) return;
          if (!Array.from(select.options).some(function (option) { return option.value === thickness; })) {
            select.appendChild(new Option(thickness, thickness));
          }
          select.value = thickness;
          select.dataset.tableThickness = thickness;
        });
      });
      input.addEventListener('change', function () {
        var previous = input.dataset.previousThickness || '';
        var next = block.dataset.thickness || '';
        var duplicate = Array.from(host.querySelectorAll('.ap-chain-thickness-block')).some(function (other) {
          return other !== block && other.dataset.thickness === next;
        });
        if (duplicate) {
          input.value = chainThicknessDisplay(previous);
          block.dataset.thickness = previous;
          block.querySelectorAll('[data-thickness]').forEach(function (el) {
            el.dataset.thickness = previous;
          });
          form.querySelectorAll('#apVariantGrid [name="carat"]').forEach(function (select) {
            if (select.value === next || select.dataset.tableThickness === next) {
              select.value = previous;
              select.dataset.tableThickness = previous;
            }
          });
          delete input.dataset.previousThickness;
          syncChainVariantThicknessOptions(form);
          return;
        }
        if (previous && next && previous !== next) {
          form.querySelectorAll('#apVariantGrid [name="carat"]').forEach(function (select) {
            if (select.value !== previous && select.dataset.tableThickness !== previous) return;
            if (!Array.from(select.options).some(function (option) { return option.value === next; })) {
              select.appendChild(new Option(next, next));
            }
            select.value = next;
            select.dataset.tableThickness = next;
          });
        }
        delete input.dataset.previousThickness;
        syncChainVariantThicknessOptions(form);
      });
      remove.addEventListener('click', function () {
        var removedThickness = block.dataset.thickness || '';
        form.querySelectorAll('#apVariantGrid .ap-variant-row').forEach(function (row) {
          var select = row.querySelector('[name="carat"]');
          if (select && select.value === removedThickness) row.remove();
        });
        block.remove();
        syncChainVariantThicknessOptions(form);
      });
    });
  }

  function refreshChainLengthGrid(form, category, chainType) {
    var section = form.querySelector('#apChainLengthSection');
    if (!section || category !== 'chain') return;
    var preserved = collectChainLengthWeights(form) || {};
    var weightsHost = section.querySelector('#apChainLengthWeights');
    if (weightsHost) {
      delete weightsHost.dataset.bound;
      weightsHost.innerHTML = chainLengthWeightsGridInnerHtml(
        preserved, chainType, chainThicknessesForForm(form, chainType, preserved)
      );
    }
    rebindChainLengthGrid(form);
    syncChainVariantThicknessOptions(form);
  }

  function toggleChainLengthSection(form, category) {
    var section = form.querySelector('#apChainLengthSection');
    if (!section) return;
    section.hidden = category !== 'chain';
  }

  function ringSizeFieldValue(cfg, camel, snake, legacyCamel, legacySnake) {
    if (!cfg) return '';
    if (cfg[camel] != null && cfg[camel] !== '') return cfg[camel];
    if (snake && cfg[snake] != null && cfg[snake] !== '') return cfg[snake];
    if (legacyCamel && cfg[legacyCamel] != null && cfg[legacyCamel] !== '') return cfg[legacyCamel];
    if (legacySnake && cfg[legacySnake] != null && cfg[legacySnake] !== '') return cfg[legacySnake];
    return '';
  }

  function variantHeadHtml(category) {
    if (category === 'chain') {
      return (
        '<div class="ap-variant-head">' +
          '<span>金屬</span><span>厚度</span><span>品項加價 (NT$)</span><span>手動定價</span><span></span>' +
        '</div>'
      );
    }
    var earClaspHead = category === 'earring' ? '<span>耳扣價錢</span>' : '';
    return (
      '<div class="ap-variant-head">' +
        '<span>金屬</span><span>克拉</span><span>蠟重（錢）</span><span>預估金重</span>' +
        '<span>配鑽 cts</span><span>一克拉價格</span><span>配鑽價錢</span>' +
        '<span>品項加價 (NT$)</span>' +
        earClaspHead +
        '<span>手動定價</span><span></span>' +
      '</div>'
    );
  }

  /** Prefill 品項加價: row value when set, else category default. */
  function variantAddonDisplayValue(variant, category) {
    if (variant) {
      if (variant.addon_price_twd != null && variant.addon_price_twd !== '') {
        return variant.addon_price_twd;
      }
      if (variant.addonPriceTwd != null && variant.addonPriceTwd !== '') {
        return variant.addonPriceTwd;
      }
    }
    return categoryAddonValue(category);
  }

  /** Prefill 手動定價 from API (snake) or collected form (camel). Empty when unset. */
  function variantManualPriceDisplayValue(variant) {
    if (!variant) return '';
    var raw = variant.manual_price_twd;
    if (raw == null || raw === '') raw = variant.manualPriceTwd;
    if (raw == null || raw === '') return '';
    var n = Number(raw);
    return Number.isFinite(n) ? n : '';
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
    var thicknesses = chainThicknessesForForm(form, chainType, {});
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
    var price = variantManualPriceDisplayValue(variant);
    var addonPrice = variantAddonDisplayValue(variant, category);
    var addonInput =
      '<input type="number" name="addonPrice" step="1" min="0" placeholder="品項加價 (NT$)" value="' +
      esc(addonPrice) + '" title="預設帶入品項加價；可逐列調整。清空則回退品項預設。">';
    var manualPriceInput =
      '<input type="number" name="price" step="1" min="0" placeholder="手動定價" value="' +
      esc(price) + '" title="填寫後試算總價改用此固定價（清空＝公式計價）">';
    if (category === 'chain') {
      return (
        '<div class="ap-variant-row">' +
          '<select name="gold">' + goldOpts + '</select>' +
          '<span class="ap-thickness-input"><input type="text" name="carat" value="' +
            esc(chainThicknessDisplay(variant && variant.carat)) + '" placeholder="厚度" maxlength="12" ' +
            'inputmode="decimal" required><span aria-hidden="true">mm</span></span>' +
          addonInput +
          manualPriceInput +
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
    var earClasp = '';
    if (category === 'earring' && variant) {
      if (variant.ear_clasp_price_twd != null) earClasp = variant.ear_clasp_price_twd;
      else if (variant.ear_cuff_price_twd != null) earClasp = variant.ear_cuff_price_twd;
    }
    var earClaspInput = category === 'earring'
      ? '<input type="number" name="earClaspPrice" step="1" min="0" placeholder="耳扣價錢" value="' + esc(earClasp) + '">'
      : '';
    var gold = (variant && variant.gold) || GOLDS[0];
    return '<div class="ap-variant-row">' +
      '<select name="gold">' + goldOpts + '</select>' +
      '<select name="carat">' + caratOpts + '</select>' +
      '<input type="number" name="weight" step="0.0001" min="0.0001" placeholder="蠟重（錢）" value="' + esc(weight) + '">' +
      '<output class="ap-metal-weight-out" name="metalWeight">' + metalWeightLabel(weight, gold) + '</output>' +
      '<input type="number" name="sideStoneCarat" step="any" min="0" placeholder="配鑽 cts" value="' + esc(sideStoneCts) + '">' +
      '<input type="number" name="sideStonePrice" step="1" min="0" placeholder="一克拉價格" value="' + esc(sideStone) + '">' +
      '<input type="number" name="sideStoneTotal" step="1" min="0" placeholder="配鑽價錢" value="' +
        esc(sideStoneTotalDisplay) + '"' + sideStoneFixedAttr + ' title="自動 = 配鑽 cts × 一克拉價格；手動改寫後為固定總價">' +
      addonInput +
      earClaspInput +
      manualPriceInput +
      '<button type="button" class="ap-remove-row" aria-label="移除">✕</button></div>';
  }

  function imageSlideHtml(urlOrSlide, color) {
    var slide = (urlOrSlide && typeof urlOrSlide === 'object')
      ? urlOrSlide
      : { url: urlOrSlide, id: '', previousFilePath: '' };
    var url = slide.url || '';
    // Bundled shop-product PNGs are never shown — uploads only.
    if (isAutoStockProductImage(url)) return '';
    var persistUrl = persistableImageUrl(url, color);
    if (!persistUrl) return '';
    var imageId = slide.id || '';
    var previousUrl = persistableImageUrl(slide.previousFilePath || slide.previous_file_path || '', color) || '';
    var restoreHidden = previousUrl ? '' : ' hidden';
    var replaceDisabled = imageId ? '' : ' disabled title="請先儲存商品後再取代"';
    return (
      '<div class="ap-carousel-item" data-url="' + esc(persistUrl) + '" data-color="' + esc(color || '') + '"' +
        (imageId ? ' data-image-id="' + esc(imageId) + '"' : '') +
        (previousUrl ? ' data-previous-url="' + esc(previousUrl) + '"' : '') +
        '>' +
        '<div class="ap-carousel-card">' +
          '<div class="ap-carousel-card-media">' +
            '<img class="ap-carousel-img" src="' + esc(bustImageUrl(persistUrl)) +
              '" alt="" data-fallback="' + esc(bustImageUrl(persistUrl)) +
              '" loading="lazy" decoding="async" width="180" height="180">' +
            '<button type="button" class="ap-remove-image" aria-label="移除">X</button>' +
            '<div class="ap-carousel-actions">' +
              '<button type="button" class="ap-replace-image"' + replaceDisabled + '>取代</button>' +
              '<button type="button" class="ap-restore-image"' + restoreHidden + '>還原</button>' +
            '</div>' +
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

  function slotPairSelectHtml(selectedKey, category) {
    if (category === 'diamond') {
      var opts = diamondShapeOptionsLive();
      var shape = isKnownDiamondShape(selectedKey) ? selectedKey : 'round';
      if (isKnownDiamondShape(selectedKey) && !opts.some(function (o) { return o.value === selectedKey; })) {
        opts = opts.concat([{ value: selectedKey, label: selectedKey }]);
      }
      opts = opts.concat([{ value: NEW_SHAPE_VALUE, label: '+ 新增切工…' }]);
      return (
        '<label class="ap-image-slot-pair">' +
          '<span>鑽石切工</span>' +
          '<select class="ap-image-slot-diamond-only">' +
            slotSelectHtml(opts, shape) +
          '</select>' +
        '</label>'
      );
    }
    var parsed = parseSlotKey(selectedKey) || { metal: 'white', diamond: 'white', chainMetal: null };
    if (category === 'chain') {
      return (
        '<label class="ap-image-slot-pair">' +
          '<span>金屬</span>' +
          '<select class="ap-image-slot-metal">' + slotSelectHtml(METAL_SLOT_OPTIONS, parsed.metal) + '</select>' +
        '</label>'
      );
    }
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
      if (groups[color].some(function (s) { return s.url === url; })) return;
      groups[color].push({
        url: url,
        id: img.id ? String(img.id) : '',
        previousFilePath: persistableImageUrl(
          img.previous_file_path || img.previousFilePath || '',
          color
        ) || '',
      });
    });
    return groups;
  }

  /** After save/autosave, replace stale _pending carousel URLs with promoted Storage paths. */
  function syncEditorImagesFromProduct(form, images) {
    if (!form || !images || !images.length) return;
    var groups = groupImagesForSlots(images);
    form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
      var color = slotColorKey(slot);
      var slides = groups[color] || [];
      var items = slot.querySelectorAll('.ap-carousel-item[data-url]');
      items.forEach(function (item, index) {
        var slide = slides[index];
        if (!slide || !slide.url) return;
        item.dataset.url = slide.url;
        if (slide.id) item.dataset.imageId = slide.id;
        else delete item.dataset.imageId;
        if (slide.previousFilePath) item.dataset.previousUrl = slide.previousFilePath;
        else delete item.dataset.previousUrl;
        var img = item.querySelector('.ap-carousel-img');
        if (img) {
          var slideSrc = bustImageUrl(slide.url);
          img.src = slideSrc;
          if (img.dataset) img.dataset.fallback = slideSrc;
        }
        var restoreBtn = item.querySelector('.ap-restore-image');
        if (restoreBtn) restoreBtn.hidden = !slide.previousFilePath;
        var replaceBtn = item.querySelector('.ap-replace-image');
        if (replaceBtn) {
          replaceBtn.disabled = !slide.id;
          if (slide.id) replaceBtn.removeAttribute('title');
          else replaceBtn.title = '請先儲存商品後再取代';
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

    function mergeInto(targetKey, slides) {
      if (!groups[targetKey]) groups[targetKey] = [];
      (slides || []).forEach(function (slide) {
        var url = typeof slide === 'string' ? slide : (slide && slide.url);
        if (!url) return;
        if (groups[targetKey].some(function (s) { return s.url === url; })) return;
        groups[targetKey].push(typeof slide === 'string' ? { url: slide, id: '', previousFilePath: '' } : slide);
      });
    }

    if (category === 'diamond') {
      slotOrderFromImages(images).forEach(pushSlot);
      Object.keys(groups).forEach(function (key) {
        if (seen[key]) return;
        if (!(groups[key] && groups[key].length)) return;
        pushSlot(key);
      });
      if (!slots.length) slots.push({ color: 'round', urls: [] });
      return slots;
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
    var color = slot.color || (category === 'diamond' ? 'round' : 'white-white');
    var slides = (slot.urls || []).map(function (slide) {
      return imageSlideHtml(slide, color);
    }).join('');

    return (
      '<div class="ap-image-slot" data-slot-id="' + slotId + '" data-category="' + esc(category || '') + '">' +
        '<div class="ap-image-slot-head">' +
          '<div class="ap-image-slot-label ap-image-slot-label--pair">' +
            '<span>圖片選項</span>' +
            slotPairSelectHtml(color, category) +
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
                    '<span class="ap-upload-hint">或點擊瀏覽<br>JPG / PNG / WEBP，來源 ≤1MB<br>上傳後轉 WebP 並壓縮至 ≤500KB<br>可選裁切，預設保留原圖</span>' +
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
    var diamondOnly = slotEl.querySelector('.ap-image-slot-diamond-only');
    if (diamondOnly) return diamondOnly.value || '';
    var metalSel = slotEl.querySelector('.ap-image-slot-metal');
    var diamondSel = slotEl.querySelector('.ap-image-slot-diamond');
    if (metalSel && diamondSel) {
      return buildSlotKey(metalSel.value, diamondSel.value, null);
    }
    if (metalSel && slotEl.dataset.category === 'chain') {
      return buildSlotKey(metalSel.value, 'white', null);
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
          // Crop island missing — still upload original so the carousel can show.
          resolve(file);
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
          var uploadFile = storageSafeUploadFile(file);
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
              else if (typeof res.error === 'string') { /* keep */ }
              else res.error = (api && api.apiErrorMessage) ? api.apiErrorMessage(res) : ('HTTP ' + xhr.status);
            }
            progressByIndex[index] = 100;
            updateProgress();
            resolve(res);
          };
          xhr.onerror = function () { resolve({ error: 'network' }); };
          var fd = new FormData();
          fd.append('file', uploadFile, uploadFile.name || 'image.webp');
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
        var lastError = '';
        results.forEach(function (res) {
          if (res.error || !res.url || isBrowserLocalImageUrl(res.url)) {
            hadError = true;
            lastError = res.error || lastError || '上傳失敗';
            return;
          }
          // Existing product: server must confirm the product_images row,
          // otherwise the preview would show an image the shop can never see.
          if (state.editingId && !(res.image && res.image.id)) {
            hadError = true;
            lastError = '圖片已上傳但未寫入資料庫，請重新整理後再試';
            return;
          }
          var imageMeta = res.image || {};
          var wrap = document.createElement('div');
          wrap.innerHTML = imageSlideHtml({
            url: res.url,
            id: imageMeta.id || '',
            previousFilePath: imageMeta.previous_file_path || imageMeta.previousFilePath || '',
          }, color);
          var item = wrap.firstElementChild;
          if (!item) {
            // Fallback slide if URL helpers rejected Storage URL.
            wrap.innerHTML = imageSlideHtml({ url: res.url, id: imageMeta.id || '' }, color)
              || (
                '<div class="ap-carousel-item" data-url="' + esc(res.url) + '" data-color="' + esc(color || '') + '">' +
                  '<div class="ap-carousel-card"><div class="ap-carousel-card-media">' +
                    '<img class="ap-carousel-img" src="' + esc(res.url) + '" alt="" width="180" height="180">' +
                    '<button type="button" class="ap-remove-image" aria-label="移除">X</button>' +
                  '</div></div></div>'
              );
            item = wrap.firstElementChild;
          }
          if (!item) { hadError = true; lastError = '無法顯示上傳圖片'; return; }
          item.dataset.url = res.url;
          item.dataset.color = color;
          track.insertBefore(item, uploadItem);
          bindCarouselItemActions(item, slot, form);
        });
        refreshAllCarousels(form);
        if (hadError) {
          if (uploading) {
            uploading.hidden = false;
            uploading.textContent = lastError || '上傳失敗';
          }
          alert(lastError || '上傳失敗');
        }
        endImageBusy();
      }, function () {
        endImageBusy();
      });
    }, function () {
      endImageBusy();
    });
  }

  function applyImageRowToSlide(item, imageRow, fallbackUrl) {
    if (!item || !imageRow) return;
    var url = imageRow.file_path || imageRow.url || fallbackUrl || '';
    var previous = imageRow.previous_file_path || imageRow.previousFilePath || '';
    if (url) {
      item.dataset.url = url;
      var img = item.querySelector('.ap-carousel-img');
      if (img) {
        // A replace can reuse the same Storage key, so force a refetch.
        bumpImageCacheEpoch();
        var nextSrc = bustImageUrl(url);
        img.src = nextSrc;
        if (img.dataset) img.dataset.fallback = nextSrc;
      }
    }
    if (imageRow.id) item.dataset.imageId = String(imageRow.id);
    if (previous) item.dataset.previousUrl = previous;
    else delete item.dataset.previousUrl;
    var restoreBtn = item.querySelector('.ap-restore-image');
    if (restoreBtn) restoreBtn.hidden = !previous;
    var replaceBtn = item.querySelector('.ap-replace-image');
    if (replaceBtn) {
      replaceBtn.disabled = !item.dataset.imageId;
      if (item.dataset.imageId) replaceBtn.removeAttribute('title');
    }
  }

  function replaceSlideImage(item, slot, form) {
    var imageId = item && item.dataset ? item.dataset.imageId : '';
    if (!imageId) {
      alert('請先儲存商品後再取代圖片');
      return;
    }
    if (!state.editingId) {
      alert('請先儲存商品後再取代圖片');
      return;
    }
    var input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/png,image/jpeg,image/webp';
    input.addEventListener('change', function () {
      var files = Array.from(input.files || []);
      var bad = validateImageFiles(files);
      if (bad) {
        alert(bad);
        return;
      }
      var file = files[0];
      if (!file) return;
      var color = slotColorKey(slot) || item.dataset.color || 'white';
      beginImageBusy();
      openProductImageCrop(file).then(function (cropped) {
        if (!cropped) {
          endImageBusy();
          return;
        }
        var uploadFile = storageSafeUploadFile(cropped);
        var fd = new FormData();
        fd.append('file', uploadFile, uploadFile.name || 'image.webp');
        fd.append('product_id', state.editingId);
        fd.append('color', color);
        fd.append('replace_image_id', imageId);
        return fetch('/api/admin/product-upload', {
          method: 'POST',
          credentials: 'include',
          body: fd,
        }).then(function (res) {
          return res.json().catch(function () { return {}; }).then(function (data) {
            if (!res.ok || data.error || !data.url) {
              alert((data && data.error) || '取代失敗');
              return;
            }
            // Replace must echo the persisted row — a bare url means the DB
            // still points at the old image and the shop will not change.
            if (!(data.image && data.image.id)) {
              alert('圖片已上傳但未寫入資料庫，請重新整理後再試');
              return;
            }
            applyImageRowToSlide(item, data.image, data.url);
            refreshAllCarousels(form);
          });
        }).catch(function () {
          alert('取代失敗');
        }).then(function () {
          endImageBusy();
        });
      }, function () {
        endImageBusy();
      });
    });
    input.click();
  }

  function restoreSlideImage(item, form) {
    var imageId = item && item.dataset ? item.dataset.imageId : '';
    var previousUrl = item && item.dataset ? item.dataset.previousUrl : '';
    if (!imageId || !previousUrl) return;
    beginImageBusy();
    api.admin.productImageAction(imageId, 'restore').then(function (res) {
      if (res.error || !res.image) {
        alert(res.error || '還原失敗');
        endImageBusy();
        return;
      }
      applyImageRowToSlide(item, res.image, previousUrl);
      refreshAllCarousels(form);
      endImageBusy();
    }, function () {
      alert('還原失敗');
      endImageBusy();
    });
  }

  function bindCarouselItemActions(item, slot, form) {
    if (!item || item.classList.contains('ap-carousel-item--upload')) return;
    item.querySelector('.ap-remove-image')?.addEventListener('click', function () {
      item.remove();
      var carousel = slot.querySelector('[data-carousel]');
      if (carousel && carousel._refreshCarousel) carousel._refreshCarousel();
    });
    item.querySelector('.ap-replace-image')?.addEventListener('click', function () {
      replaceSlideImage(item, slot, form);
    });
    item.querySelector('.ap-restore-image')?.addEventListener('click', function () {
      restoreSlideImage(item, form);
    });
  }

  function bindSlotKeySelectors(slot, form) {
    var metalSel = slot.querySelector('.ap-image-slot-metal');
    var diamondSel = slot.querySelector('.ap-image-slot-diamond');
    var diamondOnly = slot.querySelector('.ap-image-slot-diamond-only');

    slot.dataset.lastKey = slotColorKey(slot);

    function restoreDiamondOnly(prevKey) {
      if (!diamondOnly) return;
      var fallback = isKnownDiamondShape(prevKey) ? prevKey : 'round';
      if (!Array.from(diamondOnly.options).some(function (o) { return o.value === fallback; })) {
        diamondOnly.appendChild(new Option(fallback, fallback));
      }
      diamondOnly.value = fallback;
    }

    function applyDiamondShapeKey(key) {
      var used = usedSlotKeys(form, slot);
      if (used[key]) {
        alert('此組合已用於其他圖片選項，請選擇不同的組合。');
        restoreDiamondOnly(slot.dataset.lastKey || 'round');
        return;
      }
      slot.dataset.lastKey = key;
      slot.querySelectorAll('.ap-carousel-item[data-url]').forEach(function (item) {
        item.dataset.color = key;
      });
    }

    function onSlotKeyChange() {
      if (diamondOnly && diamondOnly.value === NEW_SHAPE_VALUE) {
        var prevKey = slot.dataset.lastKey || 'round';
        restoreDiamondOnly(prevKey);
        promptCreateDiamondShape().then(function (shape) {
          if (!shape || !shape.id) return;
          refreshImageSlotCategory(slot, form, 'diamond');
          diamondOnly = slot.querySelector('.ap-image-slot-diamond-only');
          if (diamondOnly) {
            if (!Array.from(diamondOnly.options).some(function (o) { return o.value === shape.id; })) {
              diamondOnly.insertBefore(
                new Option(shape.labelZh || shape.label_zh || shape.id, shape.id),
                diamondOnly.querySelector('option[value="' + NEW_SHAPE_VALUE + '"]')
              );
            }
            diamondOnly.value = shape.id;
          }
          applyDiamondShapeKey(shape.id);
        });
        return;
      }
      var key = slotColorKey(slot);
      if (diamondOnly) {
        applyDiamondShapeKey(key);
        return;
      }
      var used = usedSlotKeys(form, slot);
      if (used[key]) {
        alert('此組合已用於其他圖片選項，請選擇不同的組合。');
        var prev = parseSlotKey(slot.dataset.lastKey || 'white') || { metal: 'white', diamond: 'white', chainMetal: null };
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
    diamondOnly?.addEventListener('change', onSlotKeyChange);
  }

  function refreshImageSlotCategory(slot, form, category) {
    var currentKey = slotColorKey(slot);
    var baseColor = category === 'diamond'
      ? (isKnownDiamondShape(currentKey) ? currentKey : 'round')
      : (parseSlotKey(currentKey)
        ? currentKey
        : buildSlotKey('white', 'white', null));
    slot.dataset.category = category || '';
    var pairWrap = slot.querySelector('.ap-image-slot-label--pair');
    if (!pairWrap) return;
    pairWrap.innerHTML = '<span>圖片選項</span>' + slotPairSelectHtml(baseColor, category);
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

      slot.querySelectorAll('.ap-carousel-item[data-url]').forEach(function (item) {
        bindCarouselItemActions(item, slot, form);
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
          '<span class="ap-switch-label">可戒圈/金屬刻字</span>' +
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

  function defaultColorOptionsHtml(product, category) {
    var current = product ? product.default_color : 'white';
    if (category === 'diamond') {
      return DIAMOND_SLOT_VALUES.map(function (c) {
        var sel = current === c ? ' selected' : '';
        return '<option value="' + c + '"' + sel + '>' + DIAMOND_COLOR_LABELS[c] + '</option>';
      }).join('');
    }
    return COLORS.map(function (c) {
      var sel = current === c ? ' selected' : '';
      return '<option value="' + c + '"' + sel + '>' + COLOR_LABELS[c] + '</option>';
    }).join('');
  }

  function productStyleKey(product) {
    if (!product) return '';
    return product.styleKey || product.style_key || '';
  }

  function imageSectionHint(category) {
    if (category === 'diamond') {
      return '商品＝鑽石顏色；此處依切工形狀上傳照片（圓形／馬眼／橢圓…）。列表縮圖用圓形。價格請至「前往價格設定」。';
    }
    return '試算頁會依「金屬 × 鑽石顏色」切換商品圖'
      + (category === 'pendant' ? '；含鍊預覽沿用項墜金屬色（無需另傳異色鍊圖）' : '')
      + '。請為需要的金屬 × 鑽石組合上傳商品照片。';
  }

  function editorFormHtml(product, defaultCategory) {
    var isEdit = !!product;
    var category = (product && product.category) || defaultCategory || 'ring';
    var isDiamond = category === 'diamond';
    var chainType = resolveChainType(product && (product.chainType || product.chain_type));
    var variants = (product && product.variants && product.variants.length)
      ? product.variants.map(function (v) { return variantRowHtml(v, category, chainType); }).join('')
      : variantRowHtml(null, category, chainType);
    var styleKey = productStyleKey(product);
    var styleKeyLocked = MEMORIAL_DIAMOND_STYLE_KEYS.indexOf(styleKey) >= 0;

    var catOpts = categoryOrderList().map(function (c) {
      var sel = category === c ? ' selected' : '';
      return '<option value="' + c + '"' + sel + '>' + esc(state.categoryLabels[c] || c) + '</option>';
    }).join('');
    var colorOpts = defaultColorOptionsHtml(product, category);

    return (
      '<div class="ap-editor-page">' +
        '<header class="ap-editor-head">' +
          '<button type="button" class="btn-sm ap-editor-back" id="apEditorBack">← 返回商品列表</button>' +
          '<div class="ap-editor-head-text">' +
            '<h2>' + (isEdit ? '編輯商品' : '新增商品') + '</h2>' +
            '<p class="ap-editor-sub">' +
              (isDiamond
                ? '商品名稱為鑽石顏色；上傳各切工形狀照片以連結試算頁（不含金屬／價格）。'
                : '填寫款式選項並上傳商品照片後可上架至客製試算頁。') +
            '</p>' +
          '</div>' +
        '</header>' +
        '<div class="ap-editor-body">' +
          '<p class="ap-form-error" id="apFormError" hidden></p>' +
          '<form id="apProductForm" class="ap-form">' +
            '<div class="ap-form-grid">' +
              '<label><span>品項</span><select name="category" id="apCategory">' + catOpts + '</select></label>' +
              '<label><span>' + (isDiamond ? '預設鑽石顏色' : '預設顏色') + '</span><select name="defaultColor" id="apDefaultColor">' + colorOpts + '</select></label>' +
              '<label><span>中文名稱 <span class="ap-required" aria-hidden="true">*</span></span><input name="nameZh" maxlength="150" autocomplete="off" value="' + esc(product && product.name_zh) + '"></label>' +
              '<label><span>英文名稱（資料用） <span class="ap-required" aria-hidden="true">*</span></span><input name="nameEn" maxlength="150" required autocomplete="off" value="' + esc(product && product.name_en) + '"></label>' +
              '<label id="apStyleKeyField"' + (isDiamond ? '' : ' hidden') + '><span>試算連結代碼</span>' +
                '<input name="styleKey" maxlength="48" autocomplete="off" placeholder="diamond-…" value="' + esc(styleKey) + '"' +
                (styleKeyLocked ? ' readonly' : '') + '>' +
              '</label>' +
              '<label class="ap-field-wide"><span>中文描述</span><textarea class="ap-textarea" name="descriptionZh" rows="3" placeholder="商品中文說明…">' + esc(product && product.description_zh) + '</textarea></label>' +
              '<label class="ap-field-wide"><span>英文描述</span><textarea class="ap-textarea" name="descriptionEn" rows="3" placeholder="Product description…">' + esc(product && product.description_en) + '</textarea></label>' +
              saveForLaterToggleHtml(product) +
              '<div id="apEngravingToggleWrap"' + (isDiamond ? ' hidden' : '') + '>' + allowsEngravingToggleHtml(product) + '</div>' +
              '<div id="apFancyShapesToggleWrap"' + (isDiamond ? ' hidden' : '') + '>' + allowsFancyShapesToggleHtml(product) + '</div>' +
              pendantSellModeTogglesHtml(product, category) +
            '</div>' +
            '<div id="apVariantSection"' + (isDiamond ? ' hidden' : '') + '>' +
              '<h4 class="ap-section-title">款式選項</h4>' +
              '<div class="ap-variant-block' +
                (category === 'chain' ? ' ap-variant-block--chain' : '') +
                (['ring', 'pendant', 'earring'].indexOf(category) >= 0 ? ' ap-variant-block--no-carat' : '') +
                (category === 'earring' ? ' ap-variant-block--earring' : '') +
              '">' +
                variantHeadHtml(category) +
                '<div id="apVariantGrid">' + variants + '</div>' +
              '</div>' +
              '<div class="ap-variant-actions">' +
                '<button type="button" class="btn-sm" id="apAddVariant">+ 新增款式</button>' +
                '<button type="button" class="btn-sm" id="apGenerateAllChainVariants"' +
                  (category === 'chain' ? '' : ' hidden') +
                  '>一鍵產生全部款式</button>' +
              '</div>' +
            '</div>' +
            '<div id="apChainLengthSection"' + (category === 'chain' ? '' : ' hidden') + '>' +
              chainTypeSelectorHtml(product, category) +
              chainLengthWeightsBlockHtml(
                product && product.lengthWeights, category, chainType, product && product.variants
              ) +
            '</div>' +
            '<h4 class="ap-section-title">商品照片</h4>' +
            '<p class="ap-section-hint">' + imageSectionHint(category) + '</p>' +
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
      syncChainVariantThicknessOptions(form);
    });

    document.getElementById('apGenerateAllChainVariants')?.addEventListener('click', function () {
      if (catSel.value !== 'chain') return;
      var added = generateAllChainVariantRows(grid, form);
      bindRemoveRows();
      syncChainVariantThicknessOptions(form);
      if (!added) alert('全部金屬 × 厚度組合已存在，無需再產生');
    });

    document.getElementById('apFillChainLengthDefaults')?.addEventListener('click', function () {
      fillChainLengthDefaults(form);
    });

    document.getElementById('apAddChainThickness')?.addEventListener('click', function () {
      var host = form.querySelector('#apChainLengthWeights');
      if (!host || catSel.value !== 'chain') return;
      host.insertAdjacentHTML('beforeend', chainLengthWeightBlockHtml('', {}));
      delete host.dataset.bound;
      rebindChainLengthGrid(form);
      syncChainVariantThicknessOptions(form);
      var blocks = host.querySelectorAll('.ap-chain-thickness-block');
      var last = blocks[blocks.length - 1];
      last?.querySelector('[name="chainThickness"]')?.focus();
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
    syncChainVariantThicknessOptions(form);

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
        if (e.target.name === 'carat' && catSel.value === 'chain') {
          refreshChainLengthGrid(form, 'chain', getFormChainType(form));
        }
      });
    }

    bindImageSlots(form);

    document.getElementById('apAddImageSlot')?.addEventListener('click', function () {
      var host = document.getElementById('apImageSlots');
      if (!host) return;
      var cat = catSel.value;
      var used = usedSlotKeys(form);

      function appendSlot(pick) {
        var wrap = document.createElement('div');
        wrap.innerHTML = imageSlotHtml({ color: pick, urls: [] }, cat);
        var slot = wrap.firstElementChild;
        host.appendChild(slot);
        bindImageSlot(slot, form);
        (slot.querySelector('.ap-image-slot-diamond-only')
          || slot.querySelector('.ap-image-slot-metal'))?.focus();
      }

      var pick = presetSlotKeysForCategory(cat).find(function (v) { return !used[v]; });
      if (pick) {
        appendSlot(pick);
        return;
      }
      // Diamond cuts: open create-cut dialog instead of hard wall.
      if (cat === 'diamond') {
        promptCreateDiamondShape().then(function (shape) {
          if (!shape || !shape.id) return;
          if (used[shape.id]) {
            alert('此切工已用於其他圖片選項');
            return;
          }
          appendSlot(shape.id);
        });
        return;
      }
      alert('所有組合都已建立，無法再新增圖片選項');
    });

    function syncDiamondEditorChrome(cat) {
      var isDiamond = cat === 'diamond';
      var variantSection = document.getElementById('apVariantSection');
      if (variantSection) variantSection.hidden = isDiamond;
      var styleKeyField = document.getElementById('apStyleKeyField');
      if (styleKeyField) styleKeyField.hidden = !isDiamond;
      var engravingWrap = document.getElementById('apEngravingToggleWrap');
      if (engravingWrap) engravingWrap.hidden = isDiamond;
      var fancyWrap = document.getElementById('apFancyShapesToggleWrap');
      if (fancyWrap) fancyWrap.hidden = isDiamond;
      var defaultColorSel = document.getElementById('apDefaultColor');
      if (defaultColorSel) {
        var prev = defaultColorSel.value;
        defaultColorSel.innerHTML = defaultColorOptionsHtml(
          { default_color: prev },
          cat
        );
        var allowed = isDiamond ? DIAMOND_SLOT_VALUES : COLORS;
        if (allowed.indexOf(prev) >= 0) defaultColorSel.value = prev;
      }
      var defaultColorLabel = defaultColorSel && defaultColorSel.closest('label');
      var labelSpan = defaultColorLabel && defaultColorLabel.querySelector('span');
      if (labelSpan) labelSpan.textContent = isDiamond ? '預設鑽石顏色' : '預設顏色';
    }

    catSel?.addEventListener('change', function () {
      var cat = catSel.value;
      syncDiamondEditorChrome(cat);
      var block = form.querySelector('.ap-variant-block');
      if (block) {
        block.classList.toggle('ap-variant-block--chain', cat === 'chain');
        block.classList.toggle('ap-variant-block--earring', cat === 'earring');
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
          addon_price_twd: row.querySelector('[name="addonPrice"]')?.value,
          ear_clasp_price_twd: row.querySelector('[name="earClaspPrice"]')?.value,
        });
      });
      var chainType = getFormChainType(form);
      if (grid) {
        grid.innerHTML = (preserved.length ? preserved : [null]).map(function (v) {
          return variantRowHtml(v, cat, chainType);
        }).join('');
        bindRemoveRows();
      }
      var host = document.getElementById('apImageSlots');
      var hint = form.querySelector('.ap-section-hint');
      if (host) {
        resetDeferredImages();
        var currentImages = [];
        form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
          var color = slotColorKey(slot);
          slot.querySelectorAll('.ap-carousel-item[data-url]').forEach(function (item) {
            var url = persistableImageUrl(item.dataset.url, color);
            if (!url) return;
            currentImages.push({
              color: color,
              file_path: url,
              id: item.dataset.imageId || '',
              previous_file_path: item.dataset.previousUrl || '',
            });
          });
        });
        _slotCounter = 0;
        host.innerHTML = imageSlotsHtml(currentImages, catSel.value);
        host.querySelectorAll('.ap-image-slot').forEach(function (slot) {
          slot.setAttribute('data-category', catSel.value);
        });
        if (catSel.value !== 'diamond' && host.querySelector('.ap-image-slot-diamond-only')) {
          host.innerHTML = imageSlotsHtml([], catSel.value);
          host.querySelectorAll('.ap-image-slot').forEach(function (slot) {
            slot.setAttribute('data-category', catSel.value);
          });
        } else if (catSel.value === 'diamond' && host.querySelector('.ap-image-slot-metal')) {
          host.innerHTML = imageSlotsHtml([], catSel.value);
          host.querySelectorAll('.ap-image-slot').forEach(function (slot) {
            slot.setAttribute('data-category', catSel.value);
          });
        }
        bindImageSlots(form);
      }
      if (hint) hint.textContent = imageSectionHint(cat);
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
    function parseOptionalNumber(raw) {
      if (raw === '' || raw == null) return null;
      var n = parseFloat(raw);
      return Number.isFinite(n) ? n : null;
    }
    if (category !== 'diamond') {
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
        var earClasp = row.querySelector('[name="earClaspPrice"]')?.value;
        var addonPrice = row.querySelector('[name="addonPrice"]')?.value;
        if (!gold || !carat) return;
        // Chain: wax in 長度蠟重; no 配鑽 / no per-variant 46cm wax field.
        if (category !== 'chain' && !weight) return;
        var isChain = category === 'chain';
        if (isChain) carat = chainThicknessKey(carat);
        var isEarring = category === 'earring';
        // Prefill shows category default — persist null when unchanged so row
        // does not pin 0 / category value and block later category updates.
        var addonParsed = parseOptionalNumber(addonPrice);
        var catAddon = categoryAddonValue(category);
        if (addonParsed != null && addonParsed === catAddon) addonParsed = null;
        variants.push({
          gold: gold,
          carat: carat,
          weightChin: isChain ? null : parseFloat(weight),
          manualPriceTwd: parseOptionalNumber(price),
          sideStonePriceTwd: isChain ? null : parseOptionalNumber(sideStone),
          sideStoneCarat: isChain ? null : parseOptionalNumber(sideStoneCts),
          sideStoneTotalTwd: isChain || !sideStoneTotalFixed
            ? null
            : parseOptionalNumber(sideStoneTotal),
          addonPriceTwd: addonParsed,
          earClaspPriceTwd: !isEarring ? null : parseOptionalNumber(earClasp),
        });
      });
    }
    var images = [];
    form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
      var color = slotColorKey(slot);
      if (!color) return;
      slot.querySelectorAll('.ap-carousel-item[data-url]').forEach(function (item) {
        var url = persistableImageUrl(item.dataset.url, color);
        if (!url) return;
        var entry = { color: color, url: url };
        if (item.dataset.previousUrl) {
          entry.previousFilePath = item.dataset.previousUrl;
        }
        images.push(entry);
      });
    });
    var allowsEngravingInput = form.querySelector('[name="allowsEngraving"]');
    var allowsFancyShapesInput = form.querySelector('[name="allowsFancyShapes"]');
    var sellWithChainInput = form.querySelector('[name="sellWithChain"]');
    var chainOnly = !!(sellWithChainInput && sellWithChainInput.checked);
    // Left: both modes → shop shows choose switch. Right: chain-only.
    var allowsPendantOnly = category === 'pendant' ? !chainOnly : true;
    var allowsWithChain = true;
    var payload = {
      category: category,
      nameZh: String(fd.get('nameZh') || '').trim(),
      nameEn: String(fd.get('nameEn') || '').trim(),
      descriptionZh: String(fd.get('descriptionZh') || '').trim(),
      descriptionEn: String(fd.get('descriptionEn') || '').trim(),
      defaultColor: fd.get('defaultColor') || 'white',
      allowsEngraving: category === 'diamond'
        ? false
        : !!(allowsEngravingInput && allowsEngravingInput.checked),
      allowsFancyShapes: !!(allowsFancyShapesInput && allowsFancyShapesInput.checked),
      allowsPendantOnly: allowsPendantOnly,
      allowsWithChain: allowsWithChain,
      isPublished: !isSaveForLater(form),
      variants: variants,
      lengthWeights: category === 'chain' ? collectChainLengthWeights(form) : null,
      chainType: category === 'chain' ? getFormChainType(form) : null,
      images: images,
    };
    if (category === 'diamond') {
      payload.styleKey = String(fd.get('styleKey') || '').trim();
    }
    return payload;
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

  function fetchProducts(category) {
    var cat = category != null && category !== ''
      ? category
      : state.activeTab.replace('cat-', '');
    return api.admin.getProducts({
      page: _pageIndex + 1,
      pageSize: _pageSize,
      category: cat || undefined,
    });
  }

  function showProductsLoadError(res) {
    unmountProductsTable();
    var retry = res.timeout
      ? ' <button type="button" class="btn-sm" id="apRetryLoad">重試</button>'
      : '';
    root.innerHTML = '<p class="note warn">載入失敗：' + esc(apiError(res)) + retry + '</p>';
    var retryBtn = document.getElementById('apRetryLoad');
    if (retryBtn) retryBtn.addEventListener('click', function () { load(false, true); });
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

    var seq = ++_loadSeq;
    var requestedCat = state.activeTab.replace('cat-', '');
    _loading = true;
    var settled = false;
    var timer = setTimeout(function () {
      if (seq !== _loadSeq) return;
      if (settled) return;
      settled = true;
      _loading = false;
      showProductsLoadError({ error: '載入逾時，請檢查網路後重試。', timeout: true });
    }, LOAD_TIMEOUT_MS);

    fetchProducts(requestedCat).then(function (res) {
      clearTimeout(timer);
      if (seq !== _loadSeq) {
        settled = true;
        return;
      }
      settled = true;
      _loading = false;
      if (res.error) {
        showProductsLoadError(res);
        return;
      }
      var currentCat = state.activeTab.replace('cat-', '');
      if (requestedCat !== currentCat) {
        load(true, true);
        return;
      }
      var incoming = (res.products || []).filter(function (p) {
        return !p.category || p.category === currentCat;
      });
      state.products = incoming;
      state.categoryLabels = res.categoryLabels || {};
      state.categories = res.categories || [];
      state.categoryOrder = res.categoryOrder || categoryOrderList();
      state.categoryCounts = res.categoryCounts || {};
      state.listTotal = typeof res.total === 'number' ? res.total : state.products.length;
      if (typeof res.page === 'number' && res.page > 0) _pageIndex = res.page - 1;
      if (typeof res.page_size === 'number' && res.page_size > 0) _pageSize = res.page_size;
      /* 編輯（下架／改品項／刪除）可能讓目前頁超出範圍：退回上一頁重抓，避免誤顯示「此品項尚無商品」。 */
      if (!state.products.length && state.listTotal > 0 && _pageIndex > 0) {
        _pageIndex -= 1;
        load(true, true);
        return;
      }
      state.chainCatalog = res.chainCatalog || state.chainCatalog;
      if (res.diamondShapes && res.diamondShapes.length) {
        state.diamondShapes = res.diamondShapes;
      } else if (res.matrixShapes && res.matrixShapes.length) {
        state.diamondShapes = res.matrixShapes.map(function (s) {
          return {
            id: s.id,
            labelZh: s.labelZh || s.label_zh || s.id,
            labelEn: s.labelEn || s.label_en || s.id,
            label_zh: s.labelZh || s.label_zh || s.id,
            label_en: s.labelEn || s.label_en || s.id,
          };
        });
      }
      /* Keep the clicked slug even if this payload's order list is incomplete. Never snap back to categoryOrder[0]. */
      if (
        currentCat !== requestedCat &&
        state.categoryOrder.indexOf(currentCat) < 0 &&
        state.categoryOrder.length
      ) {
        state.activeTab = 'cat-' + state.categoryOrder[0];
        _pageIndex = 0;
        _loading = false;
        load(true, true);
        return;
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
    load(false, true);
  }

  window.AdminProductsPanel = { load: load, ensureLoaded: ensureLoaded, prefetch: prefetch };

  if (root && !root.innerHTML.trim() && window.SkeletonUI) {
    showLoadingSkeleton();
  }
})();
