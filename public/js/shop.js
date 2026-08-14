function tr(k) { return window.t ? window.t(k) : k; }
function shopLang() { return localStorage.getItem('appLang') || 'zh'; }

/** Grey + aria-disable listed option; keep pointer events so click can toast. */
function setShopOptionDisabled(el, locked, { title, reasonKey } = {}) {
  if (!el) return;
  const on = !!locked;
  el.classList.toggle('is-disabled', on);
  el.classList.toggle('shop-option--disabled', on);
  if (on) {
    el.setAttribute('aria-disabled', 'true');
    if (title) el.title = title;
    if (reasonKey) el.dataset.blockedReason = reasonKey;
  } else {
    el.removeAttribute('aria-disabled');
    el.removeAttribute('title');
    delete el.dataset.blockedReason;
  }
}

function shopOptionIsDisabled(el) {
  return !!el?.disabled
    || el?.getAttribute?.('aria-disabled') === 'true'
    || el?.classList?.contains('is-disabled')
    || el?.classList?.contains('shop-option--disabled');
}

function toastShopBlocked(messageKey) {
  const key = messageKey || 'diamond_shape_min_carat_blocked';
  const toast = window.showToast || ((msg) => alert(msg));
  toast(tr(key), 'info');
}

const shopMode = (window.shopConfig && window.shopConfig.mode) || 'order';
const isGuestShop = shopMode === 'guest';

/* ponytail: shopConfig.mode is never actually set to 'guest' anywhere in the
   app (checked — only calculator.html sets it, always to 'order'), so
   isGuestShop above is permanently false. Real login state has to come from
   the session endpoint instead. shopIsLoggedIn stays null (unknown) until
   that resolves, so the UI doesn't flash a wrong state for logged-in users. */
let shopIsLoggedIn = null;
let shopLoginPromise = null;
function fetchShopSessionState() {
  return shopApiFetch('/api/auth/session').then(({ data }) => {
    shopIsLoggedIn = !!(data && data.user);
    updateSummary();
    return shopIsLoggedIn;
  });
}
function refreshShopLoginState() {
  if (shopLoginPromise) return shopLoginPromise;
  /* Fail closed, with one retry: a dead session check must not masquerade as
     logged-in — the cart POST would 401 and bounce to login mid-submit, which
     looks like "order can't send". Both slots reset so the next click re-checks
     fresh instead of reusing a stale failure. */
  shopLoginPromise = fetchShopSessionState()
    .catch(() => fetchShopSessionState())
    .catch(() => {
      shopIsLoggedIn = null;
      shopLoginPromise = null;
      return false;
    });
  return shopLoginPromise;
}

async function ensureShopLoginState() {
  if (shopIsLoggedIn !== null) return shopIsLoggedIn;
  return refreshShopLoginState();
}

if (new URLSearchParams(window.location.search).get('preview') === '1') {
  window.shopConfig = Object.assign({}, window.shopConfig || {}, { preview: true, useApi: true });
  (function showAdminPreviewBanner() {
    const style = document.createElement('style');
    style.textContent = [
      '#admin-preview-banner{position:sticky;top:0;z-index:99999;width:100%;',
      'display:flex;align-items:center;justify-content:center;gap:14px;flex-wrap:wrap;',
      'background:#E0A458;color:#2B2320;font-weight:600;font-size:13px;',
      'padding:10px 16px;box-shadow:0 2px 8px rgba(0,0,0,.15);}',
      '#admin-preview-return-btn{position:relative;overflow:hidden;flex-shrink:0;',
      'display:inline-flex;align-items:center;height:30px;padding:0 16px;border:0;',
      'border-radius:6px;background:#2B2320;color:#fff;font-size:12px;font-weight:600;',
      'font-family:inherit;cursor:pointer;}',
      '#admin-preview-return-btn .apb-label{transition:opacity .3s ease;white-space:nowrap;padding-left:20px;}',
      '#admin-preview-return-btn:hover .apb-label{opacity:0;}',
      '#admin-preview-return-btn .apb-icon{position:absolute;inset:0;width:25%;',
      'display:flex;align-items:center;justify-content:center;',
      'background:rgba(255,255,255,.15);transition:width .3s ease;}',
      '#admin-preview-return-btn:hover .apb-icon{width:100%;}',
    ].join('');
    document.head.appendChild(style);

    const banner = document.createElement('div');
    banner.id = 'admin-preview-banner';

    const text = document.createElement('span');
    text.textContent = '⚠ 商品上架預覽模式 — 此頁僅供管理員檢視商品畫面，非顧客看到的正式頁面，無法送出訂單';
    banner.appendChild(text);

    const returnBtn = document.createElement('button');
    returnBtn.type = 'button';
    returnBtn.id = 'admin-preview-return-btn';
    returnBtn.innerHTML =
      '<span class="apb-label">返回商品上架</span>' +
      '<span class="apb-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg></span>';
    returnBtn.addEventListener('click', function () {
      window.location.href = '/admin#products';
    });
    banner.appendChild(returnBtn);

    document.body.prepend(banner);
  })();
}

/** Static calculator: bundled catalog + client pricing (no backend). Set useApi:true to enable API. */
function shopUsesApi() {
  if (window.shopConfig && window.shopConfig.useApi === true) return true;
  if (window.shopConfig && window.shopConfig.useApi === false) return false;
  return !!(window.imprintAPI || shopApiBase());
}

function shopApiBase() {
  return (window.shopConfig && window.shopConfig.apiBase)
    || (window.imprintAPI && window.imprintAPI.getBase && window.imprintAPI.getBase())
    || '';
}

function shopApiConfigured() {
  const base = shopApiBase();
  if (/YOUR-BACKEND-PROJECT/i.test(base)) return false;
  // Empty base = same-origin /api (local uvicorn or single-app Render deploy).
  if (window.shopConfig?.useApi === true || window.imprintAPI) return true;
  return Boolean(base);
}

/** Offline/demo only — prefer GET /api/prices + POST /api/quote when API is up. */
function shopUsesLocalPricing() {
  return Boolean(window.ShopPricingLocal?.computeOrderPricing) && !shopUsesApi();
}

/** Bundled shop-catalog-data.js is offline/demo only; prod must not resurrect SKUs when API fails. */
function shopAllowsStaticCatalog() {
  return !shopUsesApi();
}

const SHOP_RESUME_KEY = 'imprint_shop_resume_v1';

/** Snapshot the in-progress step-3 selections so login can hand them back via takeShopResumeSnapshot(). */
function saveShopResumeSnapshot() {
  if (!state.category || !state.type) return;
  try {
    ensureStoneCountDefault();
    sessionStorage.setItem(SHOP_RESUME_KEY, JSON.stringify({
      category: state.category,
      type: state.type,
      gold: state.gold,
      color: effectiveColor() || state.color,
      carat: state.carat,
      ringSize: state.ringSize,
      engravingBand: state.engravingBand,
      engravingRemark: state.engravingRemark,
      engravingGirdle: state.engravingGirdle,
      lengthCm: state.lengthCm,
      includeChain: state.includeChain,
      chainProductId: state.chainProductId,
      chainGold: state.chainGold,
      chainColor: state.chainColor,
      chainThickness: state.chainThickness,
      chainLength: state.chainLength,
      diamondKind: state.diamondKind,
      fancyColor: state.fancyColor,
      stoneCount: state.stoneCount,
      diamondShape: state.diamondShape,
      quantity: state.quantity,
    }));
  } catch (_) { /* sessionStorage unavailable — resume just won't restore, no big deal */ }
}

/** One-time read: consumes (clears) the snapshot so a later unrelated visit doesn't resurrect it. */
function takeShopResumeSnapshot() {
  try {
    const raw = sessionStorage.getItem(SHOP_RESUME_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(SHOP_RESUME_KEY);
    return JSON.parse(raw);
  } catch (_) { return null; }
}

function guestLoginUrl() {
  const base = (window.shopConfig && window.shopConfig.loginUrl) || '/login';
  const returnTo = window.location.pathname + window.location.search + window.location.hash;
  const sep = base.indexOf('?') === -1 ? '?' : '&';
  saveShopResumeSnapshot();
  return base + sep + 'next=' + encodeURIComponent(returnTo);
}

function orderSuccessUrl(orderNumber, options) {
  const base = (window.shopConfig && window.shopConfig.successUrl) || '/success';
  const params = new URLSearchParams();
  if (orderNumber) params.set('order', String(orderNumber));
  if (options && options.updated) params.set('updated', '1');
  const qs = params.toString();
  return qs ? base + '?' + qs : base;
}

function redirectGuestToLogin() {
  window.location.href = guestLoginUrl();
}

const SHOP_REQUEST_CACHE_TTL_MS = 60_000;
const shopRequestCache = new Map();
const shopRequestInflight = new Map();

function shopRequestKey(path, method, body) {
  return `${method} ${path}${body === undefined ? '' : ` ${JSON.stringify(body)}`}`;
}

async function shopApiFetch(path, options = {}) {
  const method = String(options.method || 'GET').toUpperCase();
  const cacheable = method === 'GET'
    && options.cache !== false
    && (path.startsWith('/api/catalog') || path === '/api/prices' || path === '/api/auth/session');
  const key = shopRequestKey(path, method, options.body);
  if (cacheable) {
    const cached = shopRequestCache.get(key);
    if (cached && cached.expiresAt > Date.now()) return cached.value;
    if (cached) shopRequestCache.delete(key);
    const inflight = shopRequestInflight.get(key);
    if (inflight) return inflight;
  }

  const request = (async () => {
    const headers = options.headers || (options.body ? { 'Content-Type': 'application/json' } : undefined);
    const res = await fetch(shopApiBase() + path, {
      method,
      credentials: 'include',
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    });
    const text = await res.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch (_) { data = { error: text.slice(0, 200) }; }
    const value = { res, data };
    if (cacheable && res.ok) {
      shopRequestCache.set(key, { expiresAt: Date.now() + SHOP_REQUEST_CACHE_TTL_MS, value });
    }
    return value;
  })();
  if (!cacheable) return request;
  shopRequestInflight.set(key, request);
  try {
    return await request;
  } finally {
    if (shopRequestInflight.get(key) === request) shopRequestInflight.delete(key);
  }
}

function shopApiErrorMessage(data, res) {
  if (data?.message) return data.message;
  if (data?.error) return data.error;
  if (res?.status === 429) return tr('rate_limit_error');
  return tr('generic_error');
}

// ── Fixed business rules (physical/tax facts, NOT catalog content) ────────
// Which metals require a color choice, and which colors they offer.
const METAL_COLORS = {
  '9k':    ['white'],
  '14k':   ['white', 'yellow', 'rose'],
  '18k':   ['white', 'yellow', 'rose'],
  'pt950': [],
  's925':  [],
};
const METAL_MATERIAL_LABELS = {
  '9k:white': 'material_9k_white',
  '14k:white': 'material_14k_white',
  '14k:yellow': 'material_14k_yellow',
  '14k:rose': 'material_14k_rose',
  '18k:white': 'material_18k_white',
  '18k:yellow': 'material_18k_yellow',
  '18k:rose': 'material_18k_rose',
  'pt950:white': 'material_pt950',
  's925:white': 'material_s925',
};
const GOLD_COLOR_METALS = ['9k', '14k', '18k'];
const METAL_DISPLAY_ORDER = ['9k', '14k', '18k', 'pt950', 's925'];

function sortGolds(golds) {
  const order = Object.fromEntries(METAL_DISPLAY_ORDER.map((g, i) => [g, i]));
  return [...golds].sort((a, b) => (order[a] ?? 99) - (order[b] ?? 99));
}

function findStaticCatalogProduct(category, product) {
  const list = window.shopCatalogData?.categories?.[category];
  if (!list || !product) return null;
  const styleKey = product.styleKey ? String(product.styleKey) : '';
  const id = String(product.id);
  return list.find((p) => {
    const staticId = String(p.id);
    const staticKey = p.styleKey ? String(p.styleKey) : '';
    if (styleKey && (staticKey === styleKey || staticId === styleKey)) return true;
    if (staticId === id || staticKey === id) return true;
    return false;
  }) || null;
}

function isColorLockedChainProduct(product) {
  const key = String(product?.styleKey || product?.id || '');
  return key.startsWith('chain-');
}

function productGolds(category, product) {
  if (!product) return [];
  // Only metals that have weight rows — never advertise a gold the lookup can't price.
  const golds = new Set(Object.keys(product.weights || {}));
  (product.golds || []).forEach((g) => {
    if (product.weights?.[g] && Object.keys(product.weights[g]).length) golds.add(g);
  });
  let list = sortGolds([...golds]);
  // Chain A/B/C color is fixed in step 2; 9K is white-only — drop it for rose/yellow styles
  if (isColorLockedChainProduct(product)) {
    const locked = product.defaultColor || 'white';
    if (locked === 'rose' || locked === 'yellow') {
      list = list.filter((g) => g !== '9k');
    }
  }
  return list;
}

function productHasAdminVariants(product) {
  const weights = product?.weights;
  return !!(weights && Object.keys(weights).length > 0);
}

function necklaceTypeLengthWeights(chainType) {
  const key = chainType || 'douyuan';
  const table = chainLengthWeightDefaults[key] || chainLengthWeightDefaults.douyuan;
  return table ? structuredClone(table) : {};
}

function lengthWeightsHasRealWax(lw) {
  if (!lw || typeof lw !== 'object') return false;
  return Object.keys(lw).some((thick) => {
    const table = lw[thick];
    return !!(
      table &&
      typeof table === 'object' &&
      Object.keys(table).some((k) => Number(table[k]) > 0)
    );
  });
}

function effectiveChainLengthWeights(product) {
  const admin = product?.lengthWeights;
  if (lengthWeightsHasRealWax(admin)) return admin;
  // Empty / {} / all-zero = unset. Excel/type defaults for chain SKUs and
  // pendant 含鍊 attached-chain lookup. Do not gate on state.category —
  // pendant flow looks up chain products while category stays 'pendant'.
  return necklaceTypeLengthWeights(product?.chainType || 'douyuan');
}

function mergeProductWeights(product, staticProduct, category) {
  if (category === 'chain') {
    const adminLengths = product.lengthWeights;
    if (lengthWeightsHasRealWax(adminLengths)) {
      product.lengthWeights = structuredClone(adminLengths);
    } else {
      // Excel / 項鍊類型標準表 — empty admin table is unset, not the only table.
      product.lengthWeights = structuredClone(
        necklaceTypeLengthWeights(product.chainType || 'douyuan')
      );
    }
    if (!product.chainType) product.chainType = 'douyuan';
  }
  if (!staticProduct?.weights) return;
  // Admin 款式選項 from API — never replace with bundled static full matrix.
  if (productHasAdminVariants(product)) return;
  void category;
  product.weights = {};
  for (const [gold, carats] of Object.entries(staticProduct.weights)) {
    product.weights[gold] = { ...carats };
  }
  if (category !== 'chain') {
    product.lengthWeights = structuredClone(staticProduct.lengthWeights || {});
  }
  if (Array.isArray(staticProduct.golds) && staticProduct.golds.length) {
    product.golds = [...staticProduct.golds];
  } else {
    product.golds = sortGolds(Object.keys(product.weights));
  }
  product.carats = [...(staticProduct.carats || [])];
}

function enrichCatalogFromStatic() {
  if (!shopAllowsStaticCatalog()) return;
  const staticCats = window.shopCatalogData?.categories;
  if (!staticCats || !catalog) return;
  for (const [category, products] of Object.entries(catalog)) {
    const staticList = staticCats[category];
    if (!staticList) continue;
    for (const product of products) {
      const staticProduct = findStaticCatalogProduct(category, product);
      if (!staticProduct) continue;
      mergeProductWeights(product, staticProduct, category);
      product.golds = productGolds(category, product);
    }
  }
  injectDiamondCatalog();
}

/** True when /api/catalog returned at least one jewelry category (not memorial diamond-only). */
function catalogHasJewelryFromApi() {
  return Object.entries(catalog || {}).some(
    ([cat, products]) => cat !== 'diamond' && Array.isArray(products) && products.length > 0,
  );
}

/** Memorial diamond: API may already merge admin overlays; fill gaps from static only. */
function injectMemorialDiamondCatalogIfNeeded() {
  if (shopAllowsStaticCatalog()) return;
  if ((catalog.diamond || []).length) return;
  injectDiamondCatalog();
}

/** Before memorial configure, guarantee color products exist (static fallback). */
function ensureMemorialDiamondCatalog() {
  if ((catalog.diamond || []).length) return;
  injectDiamondCatalog();
}

function injectDiamondCatalog() {
  const staticDiamond = window.shopCatalogData?.categories?.diamond;
  if (!staticDiamond?.length) return;
  const apiList = Array.isArray(catalog.diamond) ? catalog.diamond : [];
  const byKey = new Map();
  apiList.forEach((p) => {
    const key = String(p?.styleKey || p?.id || '');
    if (key) byKey.set(key, p);
  });
  catalog.diamond = staticDiamond.map((staticP) => {
    const key = String(staticP.styleKey || staticP.id || '');
    const api = key ? byKey.get(key) : null;
    if (!api) {
      return { ...staticP, images: { ...(staticP.images || {}) } };
    }
    byKey.delete(key);
    const images = (api.images && Object.keys(api.images).length)
      ? { ...api.images }
      : { ...(staticP.images || {}) };
    return {
      ...staticP,
      ...api,
      styleKey: key,
      golds: [],
      carats: (api.carats && api.carats.length) ? api.carats : staticP.carats,
      images,
    };
  });
  byKey.forEach((extra) => {
    if (!extra?.draft) catalog.diamond.push(extra);
  });
  const order = (window._catalogCategoryOrder && window._catalogCategoryOrder.length)
    ? [...window._catalogCategoryOrder]
    : [...CATEGORY_DISPLAY_ORDER];
  window._catalogCategoryOrder = ['diamond', ...order.filter((c) => c !== 'diamond')];
}

/** Step 2 chain cards: white → yellow gold → rose (not A/B/C letter order) */
const CHAIN_STYLE_DISPLAY_ORDER = { A: 0, C: 1, B: 2 };

function chainStyleLetter(product) {
  return String(product?.styleKey || product?.id || '').match(/-([A-C])$/i)?.[1]?.toUpperCase() || '';
}

function compareChainStyleOrder(a, b) {
  return (CHAIN_STYLE_DISPLAY_ORDER[chainStyleLetter(a)] ?? 99)
    - (CHAIN_STYLE_DISPLAY_ORDER[chainStyleLetter(b)] ?? 99);
}

// Which carat-unit system each category uses (ct vs chain thickness). Kept as a
// display/UI hint; the actual selectable set per listing comes from the
// catalog (a listing only offers the carats it has variants for).
const CATEGORY_CARAT_UNIT = {
  diamond: 'ct', pendant: 'ct', ring: 'ct', earring: 'ct', bracelet: 'ct', chain: 'mm',
};
const CATEGORY_DISPLAY_ORDER = ['diamond', 'pendant', 'ring', 'earring', 'bracelet', 'chain'];

// ── Live catalog data (from /api/catalog) — replaces the old hardcoded
//    CATEGORY_STYLES / STYLE_NAMES / CATEGORY_METALS / WEIGHT_TABLE. ───────
let catalog = {};          // { category: [ {id, nameZh, nameEn, defaultColor, golds, carats, colors, images, weights, manualPrices}, ... ] }
let catalogLoaded = false;
let catalogPublishedTotal = 0;
/** Per-category paging: { pageSize, total, loaded, complete } */
const catalogPaging = {};
const CATALOG_PAGE_SIZE = 20;

/**
 * Admin product replacements can reuse the same Storage object URL. The
 * static middleware serves query-bearing image URLs as immutable, so the
 * storefront must give each API payload a fresh image URL when it is loaded.
 */
function bustCatalogImageUrl(url, token) {
  const value = String(url || '').trim();
  if (!value || /^(data|blob):/i.test(value) || /[?&]v=/.test(value)) return value;
  return `${value}${value.includes('?') ? '&' : '?'}v=${token}`;
}

function bustCatalogProductImages(product, token) {
  if (!product || !token) return product;
  const images = product.images && typeof product.images === 'object'
    ? Object.fromEntries(Object.entries(product.images).map(([key, urls]) => [
      key,
      Array.isArray(urls)
        ? urls.map((url) => bustCatalogImageUrl(url, token))
        : bustCatalogImageUrl(urls, token),
    ]))
    : product.images;
  return {
    ...product,
    ...(product.thumbUrl ? { thumbUrl: bustCatalogImageUrl(product.thumbUrl, token) } : {}),
    ...(images ? { images } : {}),
  };
}

function bustCatalogPayloadImages(data) {
  if (!data || typeof data !== 'object') return data;
  const token = Date.now();
  const categories = data.categories && typeof data.categories === 'object'
    ? Object.fromEntries(Object.entries(data.categories).map(([category, products]) => [
      category,
      Array.isArray(products)
        ? products.map((product) => bustCatalogProductImages(product, token))
        : products,
    ]))
    : data.categories;
  return categories ? { ...data, categories } : data;
}

function productsFor(category) {
  const list = catalog[category] || [];
  if (category !== 'chain' || list.length < 2) return list;
  return [...list].sort(compareChainStyleOrder);
}

function catalogCategories() {
  // Keys may be empty arrays seeded by paged /api/catalog (available but not loaded yet).
  const present = Object.keys(catalog).filter((cat) => Array.isArray(catalog[cat]));
  const preferred = (window._catalogCategoryOrder && window._catalogCategoryOrder.length)
    ? window._catalogCategoryOrder
    : CATEGORY_DISPLAY_ORDER;
  const ordered = preferred.filter(cat => present.includes(cat));
  return ordered.concat(present.filter(cat => !ordered.includes(cat)));
}

function mergeCategoryProducts(category, incoming) {
  if (!category || !Array.isArray(incoming)) return catalog[category] || [];
  const list = catalog[category] || (catalog[category] = []);
  const byId = new Map(list.map((p) => [String(p.id), p]));
  incoming.forEach((product) => {
    if (!product?.id) return;
    const id = String(product.id);
    const prev = byId.get(id);
    if (prev) {
      const idx = list.findIndex((p) => String(p.id) === id);
      const merged =
        !product.thumbUrl && prev?.thumbUrl
          ? { ...product, thumbUrl: prev.thumbUrl }
          : { ...prev, ...product };
      if (idx >= 0) list[idx] = merged;
      byId.set(id, merged);
    } else {
      list.push(product);
      byId.set(id, product);
    }
  });
  return list;
}

async function fetchCatalogPage({ category, page, pageSize } = {}) {
  const params = new URLSearchParams({
    page: String(page || 1),
    page_size: String(pageSize || CATALOG_PAGE_SIZE),
  });
  if (category) params.set('category', category);
  if (window.shopConfig?.preview) params.set('preview', '1');
  const { res, data } = await shopApiFetch(`/api/catalog?${params.toString()}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return bustCatalogPayloadImages(data);
}

function applyCatalogMeta(data) {
  if (!data) return;
  if (data.categoryMeta) {
    window._catalogCategoryMeta = {
      ...(window._catalogCategoryMeta || {}),
      ...data.categoryMeta,
    };
    applyCategoryAddonPricesFromMeta(window._catalogCategoryMeta);
  }
  if (data.categoryOrder?.length) {
    window._catalogCategoryOrder = data.categoryOrder;
  }
}

function getProduct(category, typeId) {
  if (!category || typeId == null) return null;
  const ref = String(typeId);
  const list = productsFor(category);
  return list.find((p) => String(p.id) === ref)
    || list.find((p) => String(p.styleKey || '') === ref)
    || null;
}

function getSelectedProduct() {
  return getProduct(state.category, state.type);
}

function productName(product) {
  if (!product) return '';
  return shopLang() === 'en' ? (product.nameEn || product.nameZh) : product.nameZh;
}

const METAL_COLOR_KEYS = ['white', 'yellow', 'rose'];

function materialColor(gold) {
  return (METAL_COLORS[gold] || []).length === 1 ? METAL_COLORS[gold][0] : 'white';
}

function materialLabel(gold, color) {
  return tr(METAL_MATERIAL_LABELS[`${gold}:${color || materialColor(gold)}`] || `metal_${gold}`);
}

/** Metal colors from admin 圖片選項 slots (empty → no restriction yet). */
function designedMetalColors(product) {
  const found = new Set();
  const images = product?.images;
  if (images && typeof images === 'object' && !Array.isArray(images)) {
    Object.keys(images).forEach((key) => {
      const urls = images[key];
      if (!urls || (Array.isArray(urls) && !urls.length)) return;
      const metal = String(key).split('-')[0].toLowerCase();
      if (METAL_COLOR_KEYS.includes(metal)) found.add(metal);
    });
  }
  (product?.colors || []).forEach((key) => {
    const metal = String(key).split('-')[0].toLowerCase();
    if (METAL_COLOR_KEYS.includes(metal)) found.add(metal);
  });
  if (!found.size) return [];
  // Always keep 預設顏色 available when slots exist.
  const def = String(product?.defaultColor || '').toLowerCase();
  if (METAL_COLOR_KEYS.includes(def)) found.add(def);
  return METAL_COLOR_KEYS.filter((c) => found.has(c));
}

function availableColorsForGold(gold, product) {
  const physical = (METAL_COLORS[gold] && METAL_COLORS[gold].length)
    ? [...METAL_COLORS[gold]]
    : ['white'];
  const designed = designedMetalColors(product);
  // No admin color design yet → keep physical defaults (14k/18k all three, etc.).
  if (!designed.length) return physical;
  const filtered = physical.filter((c) => designed.includes(c));
  return filtered.length ? filtered : physical;
}

function needsColorSelection(gold, product) {
  // Chain SKUs lock metal color via style pick (A white / B rose / C yellow)
  if (isColorLockedChainProduct(product)) return false;
  if (!gold || !GOLD_COLOR_METALS.includes(gold)) return false;
  // Always show the color step when the metal has color options (1, 2, or 3).
  return availableColorsForGold(gold, product).length >= 1;
}

function updateColorStepLabel(labelId, gold) {
  const label = document.getElementById(labelId);
  if (!label) return;
  if (gold && GOLD_COLOR_METALS.includes(gold)) {
    const key = 'step_color_' + gold;
    label.setAttribute('data-i18n', key);
    label.textContent = tr(key);
  } else {
    label.setAttribute('data-i18n', 'step_color');
    label.textContent = tr('step_color');
  }
}

function renderMetalButtons(rowId, golds, selectedGold, onSelect) {
  const row = document.getElementById(rowId);
  if (!row) return;
  row.innerHTML = '';
  sortGolds(golds).forEach(gold => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'metal-btn variant-chip';
    btn.dataset.gold = gold;
    btn.textContent = tr('metal_' + gold);
    btn.classList.toggle('active', selectedGold === gold);
    btn.addEventListener('click', () => onSelect(gold));
    row.appendChild(btn);
  });
}

function renderColorButtons(rowId, gold, product, selectedColor, onSelect) {
  const row = document.getElementById(rowId);
  if (!row) return;
  row.innerHTML = '';
  row.classList.add('variant-chips--colors');
  availableColorsForGold(gold, product).forEach(color => {
    const labelText = materialLabel(gold, color);
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'color-btn variant-chip color-swatch-labeled';
    btn.dataset.color = color;
    btn.setAttribute('aria-label', labelText);

    const swatch = document.createElement('span');
    swatch.className = 'color-swatch-dot';
    swatch.dataset.color = color;
    swatch.setAttribute('aria-hidden', 'true');

    const label = document.createElement('span');
    label.className = 'color-swatch-label';
    label.textContent = labelText;

    btn.classList.toggle('active', selectedColor === color);
    btn.appendChild(swatch);
    btn.appendChild(label);
    btn.addEventListener('click', () => onSelect(color));
    row.appendChild(btn);
  });
}

/** Shop-product JPG/PNG id — legacy slug (pendant-A) or API styleKey when id is a UUID. */
function styleKeyFromProductImages(product) {
  if (!product?.images) return '';
  for (const list of Object.values(product.images)) {
    const url = (Array.isArray(list) ? list[0] : list) || '';
    const match = String(url).match(/\/([a-z]+)-([A-C])\.(?:svg|png|jpe?g)/i);
    if (match) return `${match[1].toLowerCase()}-${match[2].toUpperCase()}`;
  }
  return '';
}

function productAssetId(product) {
  if (!product) return '';
  // Real admin uploads — never map to bundled letter-stock PNGs (bracelet-A etc.).
  if (product.thumbUrl && isUsableCatalogImageUrl(product.thumbUrl)) return '';
  if (productHasCatalogImages(product)) return '';
  const fromImages = styleKeyFromProductImages(product);
  if (fromImages) return fromImages;
  if (product.styleKey && /^[a-z]+-[A-C]$/i.test(String(product.styleKey))) {
    return String(product.styleKey);
  }
  const id = String(product.id || '');
  if (/^[a-z]+-[A-C]$/i.test(id)) return id;
  // Never invent A–C from sortOrder — shop-product letter PNGs are not product photos.
  return '';
}

/** Skip seed SVG placeholders and bundled shop-product letter stock. */
function isUsableCatalogImageUrl(url) {
  if (!url) return false;
  const path = String(url).split('?', 1)[0].replace(/\\/g, '/').toLowerCase();
  if (path.endsWith('.svg')) return false;
  if (/\/images\/shop\/styles\//i.test(path)) return false;
  if (/(?:^|\/)(?:static\/)?images\/shop-product(?:\/|$)/.test(path)) return false;
  // Autosave temp uploads — objects may be deleted or never promoted.
  if (/\/products\/_pending\//i.test(path) || /\/_pending\//i.test(path)) return false;
  return true;
}

/** True when product already has at least one admin/catalog raster (not empty new item). */
function productHasCatalogImages(product) {
  if (!product?.images || typeof product.images !== 'object') return false;
  return Object.values(product.images).some((list) => {
    const arr = Array.isArray(list) ? list : list ? [list] : [];
    return arr.some(isUsableCatalogImageUrl);
  });
}

/** Pick catalog image URLs for exact slot keys (no legacy metal-only fallback). */
function catalogImagesForKeys(product, keys) {
  if (!product?.images || !keys?.length) return [];
  const pick = (key) => {
    const val = product.images[key];
    if (Array.isArray(val)) return val.filter(isUsableCatalogImageUrl);
    if (typeof val === 'string' && isUsableCatalogImageUrl(val)) return [val];
    return [];
  };
  for (const key of keys) {
    const list = pick(key);
    if (list.length) return list;
  }
  return [];
}

/** Admin 圖片選項 metal × diamond axes (matches admin-products presetSlotKeysForCategory). */
const IMAGE_SLOT_METALS = ['white', 'yellow', 'rose'];
const IMAGE_SLOT_DIAMONDS = ['white', 'yellow', 'blue', 'pink'];

function presetImageSlotKeys(category) {
  const cat = String(category || '').toLowerCase();
  if (cat === 'chain') {
    return IMAGE_SLOT_METALS.map((metal) => `${metal}-white`);
  }
  const keys = [];
  for (const metal of IMAGE_SLOT_METALS) {
    for (const diamond of IMAGE_SLOT_DIAMONDS) {
      keys.push(`${metal}-${diamond}`);
    }
  }
  return keys;
}

/** Lookup keys for one admin slot (legacy metal-only folds into metal-white). */
function catalogUrlsForImageSlot(product, slotKey) {
  const parts = String(slotKey || '').split('-');
  if (
    parts.length >= 2
    && IMAGE_SLOT_METALS.includes(parts[0])
    && IMAGE_SLOT_DIAMONDS.includes(parts[1])
  ) {
    const keys = window.ShopAssets?.imageSlotKeysForLookup
      ? window.ShopAssets.imageSlotKeysForLookup(parts[0], parts[1], null)
      : [slotKey, parts[0]];
    return catalogImagesForKeys(product, keys);
  }
  if (IMAGE_SLOT_METALS.includes(slotKey)) {
    const keys = window.ShopAssets?.imageSlotKeysForLookup
      ? window.ShopAssets.imageSlotKeysForLookup(slotKey, 'white', null)
      : [slotKey, `${slotKey}-white`];
    return catalogImagesForKeys(product, keys);
  }
  return catalogImagesForKeys(product, [slotKey]);
}

/** defaultColor is metal-only; slots may be metal, metal-diamond, or metal-diamond-chain. */
function imageSlotCoversDefaultColor(slotKey, defaultColor) {
  const key = String(slotKey || '').toLowerCase();
  const def = String(defaultColor || 'white').toLowerCase();
  if (!key || !def) return false;
  if (key === def) return true;
  return key.startsWith(`${def}-`);
}

/** Preferred slot keys for 預設顏色 — white diamond first, then fancy on same metal. */
function defaultColorImageSlotKeys(product) {
  const metal = String(product?.defaultColor || 'white').toLowerCase();
  const cat = String(product?.category || '').toLowerCase();
  if (cat === 'chain') return [`${metal}-white`, metal];
  const keys = [`${metal}-white`];
  for (const diamond of IMAGE_SLOT_DIAMONDS) {
    if (diamond !== 'white') keys.push(`${metal}-${diamond}`);
  }
  return keys;
}

/** Slot keys — 預設顏色 first, then admin imageSlotOrder, then colors / preset fallback. */
function catalogImageSlotKeyOrder(product) {
  if (!product?.images) return [];
  const seen = new Set();
  const order = [];
  const pushKey = (key) => {
    if (!key || seen.has(key)) return;
    if (!catalogUrlsForImageSlot(product, key).length) return;
    seen.add(key);
    order.push(key);
  };
  for (const key of defaultColorImageSlotKeys(product)) pushKey(key);
  for (const key of product.imageSlotOrder || []) pushKey(key);
  for (const key of product.colors || []) pushKey(key);
  for (const key of presetImageSlotKeys(product.category)) pushKey(key);
  for (const key of Object.keys(product.images)) {
    if (IMAGE_SLOT_METALS.includes(key)) pushKey(`${key}-white`);
    else pushKey(key);
  }
  return order;
}

/** All usable catalog URLs in admin slot order (each slot, carousel order preserved). */
function orderedCatalogImageUrls(product) {
  if (!product?.images) return [];
  const out = [];
  const seen = new Set();
  for (const slotKey of catalogImageSlotKeyOrder(product)) {
    for (const url of catalogUrlsForImageSlot(product, slotKey)) {
      if (!url || !isUsableCatalogImageUrl(url) || seen.has(url)) continue;
      seen.add(url);
      out.push(url);
    }
  }
  return out;
}

/** First usable admin upload in admin 圖片選項 slot order. */
function firstAnyCatalogImageUrl(product) {
  return orderedCatalogImageUrls(product)[0] || '';
}

/**
 * Missing white diamond slot → same-metal fancy uploads; missing fancy → white;
 * still empty → any next catalog upload. Does not apply legacy metal-only keys
 * when the caller asked for an explicit fancy stone (preview uses stock first).
 */
function catalogImageCrossDiamondFallback(product, metal, diamond, chainMetal, opts) {
  opts = opts || {};
  if (!product?.images) return '';
  const m = metal || 'white';
  const d = diamond || 'white';
  const chain = chainMetal || null;
  const fancyIds = ['yellow', 'blue', 'pink'];

  if (d === 'white') {
    for (const fd of fancyIds) {
      const keys = window.ShopAssets?.imageSlotKeysForLookup
        ? window.ShopAssets.imageSlotKeysForLookup(m, fd, chain)
        : (chain ? [`${m}-${fd}-${chain}`, `${m}-${fd}`] : [`${m}-${fd}`]);
      const urls = catalogImagesForKeys(product, keys);
      if (urls.length) return urls[0];
    }
  } else if (fancyIds.includes(d) && opts.allowWhiteForFancy !== false) {
    const keys = window.ShopAssets?.imageSlotKeysForLookup
      ? window.ShopAssets.imageSlotKeysForLookup(m, 'white', chain)
      : (chain ? [`${m}-white-${chain}`, m, `${m}-white`] : [m, `${m}-white`]);
    const urls = catalogImagesForKeys(product, keys);
    if (urls.length) return urls[0];
  }

  return firstAnyCatalogImageUrl(product);
}

/** Admin-upload catalog URL only — same slot order as step-2 style grid / image_urls.py. */
function catalogPreviewSrc(product, metal, diamond, chainMetal) {
  if (!product?.images) return '';
  const d = diamond || 'white';
  // Fancy: exact metal-diamond[-chain] only. Never legacy metal-only / white-stone —
  // that froze preview on 白鑽 PNG when user picked 黃/藍/粉.
  let keys;
  if (d !== 'white') {
    keys = [];
    if (chainMetal) {
      keys.push(
        window.ShopAssets?.buildImageSlotKey
          ? window.ShopAssets.buildImageSlotKey(metal, d, chainMetal)
          : `${metal}-${d}-${chainMetal}`,
      );
    }
    keys.push(
      window.ShopAssets?.buildImageSlotKey
        ? window.ShopAssets.buildImageSlotKey(metal, d)
        : `${metal}-${d}`,
    );
  } else {
    keys = window.ShopAssets?.imageSlotKeysForLookup
      ? window.ShopAssets.imageSlotKeysForLookup(metal, d, chainMetal || null)
      : [
        chainMetal ? `${metal}-${d}-${chainMetal}` : null,
        `${metal}-${d}`,
        metal,
      ].filter(Boolean);
  }
  const urls = catalogImagesForKeys(product, keys);
  return urls.find((u) => !isPendantLayerAssetUrl(u)) || '';
}

function normalizePreviewSrc(url) {
  if (!url) return '';
  return String(url).replace(/([?&])_=\d+(?=&|$)/, '$1').replace(/[?&]$/, '');
}

/** Currently visible large preview (ignores cache-buster query). */
function readDisplayedPreviewSrc() {
  const compositeEl = document.getElementById('product-preview-composite');
  if (compositeEl && !compositeEl.classList.contains('hidden')) {
    const pendant = document.getElementById('large-image-pendant');
    const pSrc = pendant?.currentSrc || pendant?.src || '';
    if (pSrc && !pSrc.endsWith('/')) return normalizePreviewSrc(pSrc);
  }
  const img = document.getElementById('large-image');
  const src = img?.currentSrc || img?.src || '';
  if (src && !src.endsWith('/') && img?.style.visibility !== 'hidden') {
    return normalizePreviewSrc(src);
  }
  return '';
}

/** No catalog slot for requested metal/diamond — keep live preview or default-color catalog only. */
function previewSrcWhenCatalogMissing(product, metal, diamond, chainMetal, opts) {
  opts = opts || {};
  const current = readDisplayedPreviewSrc();
  if (current) {
    return {
      composite: false,
      src: current,
      pendantOnly: !!opts.pendantOnly,
      keepPrevious: true,
      fromCatalog: false,
    };
  }
  const fallbackMetal = product?.defaultColor || metal || 'white';
  const fallbackSrc = catalogPreviewSrc(product, fallbackMetal, diamond, chainMetal);
  if (fallbackSrc) {
    return {
      composite: false,
      src: fallbackSrc,
      pendantOnly: !!opts.pendantOnly,
      keepPrevious: false,
      fromCatalog: true,
    };
  }
  return {
    composite: false,
    src: '',
    pendantOnly: !!opts.pendantOnly,
    keepPrevious: false,
    fromCatalog: false,
  };
}

function previewColor() {
  if (state.color) return state.color;
  const product = getSelectedProduct();
  if (product) return product.defaultColor || 'white';
  return 'white';
}

/** Attached-chain color: free swatch (ignore chain-A/B/C SKU lock). */
function attachedChainColor(gold, preferred) {
  if (!gold) return preferred || null;
  const colors = availableColorsForGold(gold);
  if (preferred && colors.includes(preferred)) return preferred;
  if (state.color && colors.includes(state.color)) return state.color;
  return colors[0] || null;
}

function previewChainMetalForImage() {
  return state.chainColor || (state.chainGold ? materialColor(state.chainGold) : null) || previewColor();
}

function usesPendantCompositePreview() {
  // Cross-metal combo still prefers a pre-rendered full PNG; composite is fallback only.
  return state.category === 'pendant' && state.includeChain;
}

function previewPendantOnlyMode() {
  return state.category === 'pendant' && !state.includeChain;
}

function pendantPreviewImageOpts() {
  // 僅墜子: never attach chainColor / combo paths — only cropped `_only` PNG.
  if (state.category === 'pendant' && !state.includeChain) {
    return { pendantOnly: true };
  }
  const opts = { pendantOnly: false };
  if (state.category === 'pendant' && state.includeChain) {
    opts.chainColor = previewChainMetalForImage();
  }
  return opts;
}

function productLayerImage(product, metal, diamond, layerOpts) {
  const assetId = productAssetId(product);
  if (!assetId || !window.ShopAssets?.productImage) return '';
  return window.ShopAssets.productImage(
    assetId,
    metal,
    product?.defaultColor,
    diamond,
    layerOpts,
  ) || '';
}

function isPendantLayerAssetUrl(url) {
  // Crop-layer files end in "_only.png" or bare "_chain.png"; full combo files
  // use "_chain_{metal}[_diamond].png" and must NOT match here.
  const s = String(url || '');
  if (/\/thumbs\//i.test(s)) return true;
  // Explicit allow: pre-rendered mixed-metal necklaces
  if (/_chain_(?:silver|gold|rose)(?:_(?:white|yellow|blue|pink))?\.(?:png|jpe?g|webp)(?:\?|$)/i.test(s)) {
    return false;
  }
  return /_(?:only|chain)\.(?:png|jpe?g|webp)(?:\?|$)/i.test(s);
}

function pendantWithChainImageUrl(product, pendantMetal, chainMetal, diamond) {
  const d = diamond || 'white';
  const fromCatalog = catalogPreviewSrc(product, pendantMetal, d, chainMetal);
  if (fromCatalog) return fromCatalog;
  const assetId = productAssetId(product);
  if (!assetId || !window.ShopAssets) return '';
  // Prefer direct productImage so white-diamond combos are not lost to resolve quirks.
  if (window.ShopAssets.productImage) {
    const direct = window.ShopAssets.productImage(
      assetId,
      pendantMetal,
      product?.defaultColor,
      d,
      { chainColor: chainMetal },
    );
    if (direct && !isPendantLayerAssetUrl(direct)) return direct;
  }
  if (window.ShopAssets.productImageResolve) {
    const resolved = window.ShopAssets.productImageResolve(
      assetId,
      pendantMetal,
      product?.defaultColor,
      d,
      { chainColor: chainMetal },
    );
    const src = resolved.src || '';
    if (src && !isPendantLayerAssetUrl(src)) return src;
  }
  return '';
}

function pendantPreviewLayers(product) {
  const diamond = selectedDiamondColorId() || 'white';
  const metal = previewColor();
  const opts = pendantPreviewImageOpts();

  if (usesPendantCompositePreview()) {
    const chainMetal = previewChainMetalForImage();
    const fromCatalog = catalogPreviewSrc(product, metal, diamond, chainMetal);
    if (fromCatalog) {
      return { composite: false, src: fromCatalog, pendantOnly: false, fromCatalog: true };
    }
    const combo = pendantWithChainImageUrl(product, metal, chainMetal, diamond);
    if (combo) {
      return { composite: false, src: combo, pendantOnly: false, fromCatalog: false };
    }
    const composite = pendantCompositeFallback(product);
    if (composite) return composite;
    return previewSrcWhenCatalogMissing(product, metal, diamond, chainMetal, { pendantOnly: false });
  }

  const catalogSrc = catalogPreviewSrc(product, metal, diamond, opts.chainColor || null);
  if (catalogSrc) {
    return {
      composite: false,
      src: catalogSrc,
      pendantOnly: opts.pendantOnly,
      fromCatalog: true,
    };
  }
  // Catalog miss (common: white slot only) → letter shop-product fancy PNG.
  const stockSrc = productImagesForColor(product, metal, diamond, opts)[0] || '';
  if (stockSrc) {
    return {
      composite: false,
      src: stockSrc,
      pendantOnly: opts.pendantOnly,
      fromCatalog: false,
    };
  }
  return previewSrcWhenCatalogMissing(product, metal, diamond, opts.chainColor || null, opts);
}

function pendantCompositeFallback(product) {
  const diamond = selectedDiamondColorId();
  const pendantMetal = previewColor();
  const chainMetal = previewChainMetalForImage();
  const pendant = productLayerImage(product, pendantMetal, diamond, { pendantOnly: true });
  const chain = productLayerImage(product, chainMetal, 'white', { chainOnly: true });
  if (!pendant || !chain) return null;
  return { composite: true, pendant, chain };
}

function showCompositeProductPreview(chainImg, pendantImg, compositeEl, previewRoot, img, preview) {
  compositeEl.classList.remove('hidden');
  compositeEl.setAttribute('aria-hidden', 'false');
  previewRoot?.classList.remove('is-pendant-only');
  chainImg.onerror = null;
  pendantImg.onerror = null;
  chainImg.loading = 'eager';
  pendantImg.loading = 'eager';
  if (img) {
    img.style.visibility = 'hidden';
    img.onerror = null;
  }
  chainImg.src = preview.chain;
  pendantImg.src = preview.pendant;
}

/** Image URLs for metal + diamond color, falling back through legacy keys. */
function productImagesForColor(product, metalColor, diamondColor, opts) {
  opts = opts || {};
  const metal = metalColor ?? previewColor();
  const diamond = diamondColor ?? selectedDiamondColorId() ?? 'white';
  // Prefer explicit opts, else derive from 僅墜子 / 含鍊 so callers can't leak chainColor.
  const pendantOnly = opts.pendantOnly != null
    ? !!opts.pendantOnly
    : previewPendantOnlyMode();
  const imageOpts = { pendantOnly };
  let chainMetal = null;
  if (!pendantOnly && state.category === 'pendant' && state.includeChain) {
    chainMetal = opts.chainColor || previewChainMetalForImage();
    imageOpts.chainColor = chainMetal;
  }
  const assetId = productAssetId(product);
  const compoundKey = window.ShopAssets?.buildImageSlotKey
    ? window.ShopAssets.buildImageSlotKey(metal, diamond)
    : `${metal}-${diamond}`;

  // Exact admin uploads first (match app/image_urls.py). Never let legacy metal-only
  // slots override fancy-diamond / cross-metal renders.
  if (diamond !== 'white') {
    const exactKeys = [];
    if (chainMetal) {
      exactKeys.push(
        window.ShopAssets?.buildImageSlotKey
          ? window.ShopAssets.buildImageSlotKey(metal, diamond, chainMetal)
          : `${metal}-${diamond}-${chainMetal}`,
      );
    }
    exactKeys.push(compoundKey);
    const fromExact = catalogImagesForKeys(product, exactKeys);
    if (fromExact.length) return fromExact;
  } else {
    const whiteKeys = window.ShopAssets?.imageSlotKeysForLookup
      ? window.ShopAssets.imageSlotKeysForLookup(metal, 'white', chainMetal)
      : (chainMetal
        ? [`${metal}-white-${chainMetal}`, metal, `${metal}-white`]
        : [metal, `${metal}-white`]);
    const fromWhite = catalogImagesForKeys(product, whiteKeys);
    if (fromWhite.length) return fromWhite;
    const crossWhite = catalogImageCrossDiamondFallback(product, metal, 'white', chainMetal);
    if (crossWhite) return [crossWhite];
  }

  // Empty product with no letter-SKU mapping → no invent. Letter A–C stock may
  // fill metal×diamond when admin only uploaded white (or omitted images).
  if (!productHasCatalogImages(product) && !assetId) return [];

  // Shop-product PNGs when no exact admin slot for this metal/diamond[/chain].
  if (assetId && window.ShopAssets?.productImageResolve) {
    const resolved = window.ShopAssets.productImageResolve(
      assetId,
      metal,
      product?.defaultColor,
      diamond,
      imageOpts,
    );
    if (resolved.src) {
      return [resolved.src];
    }
  }
  if (assetId && window.ShopAssets?.productImage) {
    const resolved = window.ShopAssets.productImage(
      assetId,
      metal,
      product?.defaultColor,
      diamond,
      imageOpts,
    );
    if (resolved) return [resolved];
  }

  // Fancy: letter stock first; white / any catalog upload only when stock misses.
  if (diamond !== 'white') {
    const crossFancy = catalogImageCrossDiamondFallback(product, metal, diamond, chainMetal);
    if (crossFancy) return [crossFancy];
  }

  // White diamond: broader catalog + letter-stock fallbacks after shop-product miss.
  if (diamond === 'white') {
    for (const key of [product?.defaultColor, 'white']) {
      const list = catalogImagesForKeys(product, [key]);
      if (list.length) return list;
    }
    const anyCatalog = firstAnyCatalogImageUrl(product);
    if (anyCatalog) return [anyCatalog];
    if (assetId && window.ShopAssets?.productImages) {
      const list = window.ShopAssets.productImages(assetId, product?.defaultColor);
      if (list.length) return list;
    }
  }

  return [];
}

/** Best available image URL for a product (first of the color set). */
function productImageUrl(product, metalColor, diamondColor, opts) {
  const fromColor = productImagesForColor(product, metalColor, diamondColor, opts)[0];
  if (fromColor && !/\/images\/shop\/styles\/[a-z]+-[A-C]\.svg/i.test(fromColor)) {
    return fromColor;
  }
  // No catalog uploads and no letter stock mapping → stay blank.
  const assetId = productAssetId(product);
  if (!productHasCatalogImages(product) && !assetId) return '';
  if (assetId && window.ShopAssets) return window.ShopAssets.styleThumb(assetId);
  return '';
}

function optimizedCategoryImageUrl(url) {
  const value = String(url || '').trim();
  if (!value) return '';
  try {
    const parsed = new URL(value);
    if (!/\.supabase\.co$/i.test(parsed.hostname)) return value;
    const marker = '/storage/v1/object/public/';
    if (!parsed.pathname.includes(marker)) return value;
    parsed.pathname = parsed.pathname.replace(marker, '/storage/v1/render/image/public/');
    parsed.searchParams.set('width', '320');
    parsed.searchParams.set('height', '320');
    parsed.searchParams.set('resize', 'contain');
    parsed.searchParams.set('quality', '60');
    parsed.searchParams.set('format', 'webp');
    return parsed.toString();
  } catch (_) {
    return value;
  }
}

function categoryImageUrl(category) {
  const meta = window._catalogCategoryMeta?.[category];
  if (meta?.thumbUrl) return optimizedCategoryImageUrl(meta.thumbUrl);
  return optimizedCategoryImageUrl(window.ShopAssets?.categoryThumb(category) || '');
}

function categoryLabel(cat) {
  const meta = window._catalogCategoryMeta?.[cat];
  if (meta?.labelZh) return meta.labelZh;
  const key = 'cat_' + cat;
  const t = tr(key);
  return t && t !== key ? t : cat;
}

function applyStaticCatalogFallback() {
  if (!shopAllowsStaticCatalog()) return false;
  if (!window.shopCatalogData?.categories) return false;
  const cats = Object.keys(window.shopCatalogData.categories).filter(
    (cat) => (window.shopCatalogData.categories[cat] || []).length > 0,
  );
  if (!cats.length) return false;
  catalog = window.shopCatalogData.categories;
  window._catalogCategoryOrder = window.shopCatalogData.categoryOrder || null;
  injectDiamondCatalog();
  catalogLoaded = true;
  console.warn('shop: using bundled static catalog (API returned no products)');
  return true;
}

function renderCatalogSkeleton(count) {
  const grid = document.getElementById('catalog-grid');
  if (!grid || grid.querySelector('.cat-btn')) return;
  const emptyBoot = document.getElementById('catalog-empty');
  emptyBoot?.classList.add('hidden');
  if (emptyBoot) emptyBoot.hidden = true;
  const n = count || 5;
  grid.classList.add('is-loading');
  grid.setAttribute('aria-busy', 'true');
  grid.innerHTML = '';
  for (let i = 0; i < n; i++) {
    const tile = document.createElement('div');
    tile.className = 'catalog-tile catalog-tile--skeleton';
    tile.setAttribute('aria-hidden', 'true');
    tile.innerHTML = '<span class="catalog-tile-skeleton-img"></span><span class="catalog-tile-skeleton-label"></span>';
    grid.appendChild(tile);
  }
}

function finishShopBoot() {
  document.getElementById('shop-price-panel')?.classList.remove('is-loading-prices');
}

function productHasFullDetail(product) {
  return !!(product && product.weights != null && typeof product.weights === 'object');
}

function findProductCategory(productId) {
  if (productId == null) return null;
  const id = String(productId);
  for (const cat of Object.keys(catalog)) {
    if ((catalog[cat] || []).some((p) => String(p.id) === id)) return cat;
  }
  return null;
}

function mergeProductIntoCatalog(category, product) {
  if (!category || !product?.id) return product;
  const list = catalog[category] || (catalog[category] = []);
  const idx = list.findIndex((p) => String(p.id) === String(product.id));
  if (idx >= 0) {
    const prev = list[idx];
    // Full detail often omits lite thumbUrl — keep usable admin thumb for step-2 grid.
    const merged =
      !product.thumbUrl && prev?.thumbUrl
        ? { ...product, thumbUrl: prev.thumbUrl }
        : product;
    list[idx] = merged;
    return merged;
  }
  list.push(product);
  return product;
}

async function ensureProductDetail(productId, category) {
  if (!productId || !shopUsesApi() || !shopApiConfigured()) return null;
  if (String(productId).startsWith('diamond-')) return getProduct(category || 'diamond', productId);
  const cat = category || state.category || findProductCategory(productId);
  const existing = cat ? getProduct(cat, productId) : null;
  if (existing && productHasFullDetail(existing)) return existing;

  const params = new URLSearchParams();
  if (window.shopConfig?.preview) params.set('preview', '1');
  const qs = params.toString() ? `?${params.toString()}` : '';
  try {
    const { res, data } = await shopApiFetch(
      `/api/catalog/product/${encodeURIComponent(productId)}${qs}`,
    );
    if (!res.ok) throw new Error(`API ${res.status}`);
    const full = bustCatalogProductImages(data?.product, Date.now());
    if (!full?.id) return existing;
    const targetCat = cat || findProductCategory(full.id) || state.category;
    if (targetCat) return mergeProductIntoCatalog(targetCat, full);
    return full;
  } catch (err) {
    console.error('failed to load product detail', err);
    return existing;
  }
}

function incomingCategoryProducts(data, category) {
  const keyed = data?.categories?.[category];
  if (Array.isArray(keyed) && keyed.length) return keyed;
  const bags = data?.categories && typeof data.categories === 'object'
    ? Object.values(data.categories)
    : [];
  const flat = bags.flat().filter((p) => p && p.category === category);
  return flat.length ? flat : (Array.isArray(keyed) ? keyed : []);
}

async function ensureCategoryCatalog(category) {
  if (!category || category === 'diamond' || !shopUsesApi() || !shopApiConfigured()) return;
  const paging = catalogPaging[category];
  if (paging?.complete) return;
  try {
    let page = 1;
    const pageSize = CATALOG_PAGE_SIZE;
    let total = Infinity;
    // Load pages until category is complete (no full-catalog dump).
    while (page === 1 || ((catalog[category] || []).length < total && page <= 50)) {
      const data = await fetchCatalogPage({ category, page, pageSize });
      applyCatalogMeta(data);
      const incoming = incomingCategoryProducts(data, category);
      mergeCategoryProducts(category, incoming);
      total = Number.isFinite(Number(data.total)) ? Number(data.total) : incoming.length;
      catalogPaging[category] = {
        pageSize,
        total,
        loaded: (catalog[category] || []).length,
        complete: (catalog[category] || []).length >= total || (incoming.length === 0 && total === 0),
      };
      if (catalogPaging[category].complete || !incoming.length) break;
      page += 1;
    }
  } catch (err) {
    console.error('failed to load category catalog', err);
  }
}

function applyCategoryAddonPricesFromMeta(meta) {
  if (!meta || typeof meta !== 'object') return;
  const map = {};
  Object.keys(meta).forEach((slug) => {
    const row = meta[slug];
    if (!row || row.addonPrice == null) return;
    const n = Number(row.addonPrice);
    if (Number.isFinite(n) && n >= 0) map[slug] = n;
  });
  if (Object.keys(map).length) {
    window.ShopPricingLocal?.setCategoryAddons?.(map);
  }
}

async function loadCatalog() {
  const grid = document.querySelector('.catalog-grid');
  renderCatalogSkeleton();
  let errEl = document.getElementById('catalog-error');
  try {
    if (!shopUsesApi()) {
      if (!window.shopCatalogData) throw new Error('STATIC_CATALOG_MISSING');
      catalog = window.shopCatalogData.categories || {};
      window._catalogCategoryOrder = window.shopCatalogData.categoryOrder || null;
      injectDiamondCatalog();
      catalogLoaded = true;
      if (errEl) errEl.remove();
      requestAnimationFrame(() => renderCatalogTiles());
      return;
    }
    if (!shopApiConfigured()) throw new Error('API_NOT_CONFIGURED');
    // Boot: paged meta + available category keys (empty arrays OK). Styles load per category.
    const data = await fetchCatalogPage({ page: 1, pageSize: 1 });
    catalog = data.categories || {};
    applyCatalogMeta(data);
    catalogPublishedTotal = Number(data.total) || 0;
    // Seed published category keys from order even if this page has no rows.
    (data.categoryOrder || []).forEach((cat) => {
      if (!Array.isArray(catalog[cat])) catalog[cat] = [];
    });
    // Mark first-page crumbs incomplete so ensureCategoryCatalog refetches full category.
    Object.keys(catalog).forEach((cat) => {
      if (cat === 'diamond') {
        catalogPaging.diamond = { complete: true, total: (catalog.diamond || []).length };
        return;
      }
      const n = (catalog[cat] || []).length;
      catalogPaging[cat] = {
        pageSize: CATALOG_PAGE_SIZE,
        total: n > 0 ? Number(data.total) || n : 0,
        loaded: n,
        complete: false,
      };
      // Drop boot crumb products — category fetch loads a clean page-1 set.
      if (n > 0) catalog[cat] = [];
    });
    if (shopAllowsStaticCatalog()) {
      enrichCatalogFromStatic();
    } else {
      injectMemorialDiamondCatalogIfNeeded();
    }
    catalogLoaded = true;
    if (errEl) errEl.remove();
    if (!catalogCategories().length && catalogPublishedTotal > 0) {
      CATEGORY_DISPLAY_ORDER.forEach((cat) => {
        if (!Array.isArray(catalog[cat])) catalog[cat] = [];
      });
    }
    if (!catalogCategories().length && catalogPublishedTotal <= 0) {
      throw new Error('CATALOG_EMPTY');
    }
    requestAnimationFrame(() => renderCatalogTiles());
  } catch (err) {
    if (applyStaticCatalogFallback()) {
      if (errEl) errEl.remove();
      requestAnimationFrame(() => renderCatalogTiles());
      return;
    }
    catalogLoaded = false;
    catalog = {};
    catalogPublishedTotal = 0;
    window._catalogCategoryOrder = null;
    console.error('failed to load catalog', err);
    if (err?.message === 'CATALOG_EMPTY') {
      catalogLoaded = true;
      renderCatalogTiles();
    } else {
      document.getElementById('catalog-empty')?.classList.add('hidden');
      renderCatalogTiles();
    }
    const messageKey = err?.message === 'STATIC_CATALOG_MISSING'
      ? 'catalog_static_missing'
      : err?.message === 'API_NOT_CONFIGURED'
      ? 'catalog_setup_required'
      : err?.message === 'CATALOG_EMPTY'
        ? 'catalog_empty'
        : 'catalog_load_failed';
    if (err?.message === 'CATALOG_EMPTY') {
      document.getElementById('catalog-error')?.remove();
      return;
    }
    if (grid && !errEl) {
      errEl = document.createElement('div');
      errEl.id = 'catalog-error';
      errEl.className = 'catalog-error';
      errEl.innerHTML = `<p>${tr(messageKey)}</p><button type="button" class="btn-secondary" id="catalog-retry">${tr('catalog_retry')}</button>`;
      grid.parentElement?.insertBefore(errEl, grid);
      errEl.querySelector('#catalog-retry')?.addEventListener('click', () => {
        errEl.remove();
        loadCatalog().then(() => { if (state.category) renderTypeCards(); });
      });
    } else if (errEl) {
      const p = errEl.querySelector('p');
      if (p) p.textContent = tr(messageKey);
    }
  }
}

function renderCatalogTiles() {
  const grid = document.querySelector('.catalog-grid');
  const empty = document.getElementById('catalog-empty');
  if (!grid) return;

  if (!catalogLoaded) {
    empty?.classList.add('hidden');
    if (empty) empty.hidden = true;
    return;
  }

  const cats = catalogCategories();
  const showEmpty = !cats.length && catalogPublishedTotal <= 0;
  empty?.classList.toggle('hidden', !showEmpty);
  if (empty) {
    empty.hidden = !showEmpty;
    const emptyCopy = empty.querySelector('p');
    if (showEmpty && emptyCopy && !emptyCopy.textContent) {
      emptyCopy.textContent = tr('catalog_empty');
    }
  }
  grid.innerHTML = '';
  if (!cats.length) {
    grid.classList.remove('is-loading');
    grid.setAttribute('aria-busy', 'false');
    return;
  }
  cats.forEach((cat) => {
    const products = productsFor(cat);
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'catalog-tile cat-btn';
    btn.dataset.cat = cat;
    if (state.category === cat) btn.classList.add('active');

    const img = document.createElement('img');
    // The memorial-diamond tile is the primary first-step choice. Let it paint
    // first while browsers keep the remaining category images low priority.
    img.loading = cat === 'diamond' ? 'eager' : 'lazy';
    img.fetchPriority = cat === 'diamond' ? 'high' : 'low';
    img.decoding = 'async';
    img.alt = '';
    const catUrl = categoryImageUrl(cat);
    img.src = catUrl || (products[0] ? styleGridImageUrl(products[0]) : '');
    // WebP category thumbs keep their pre-WebP original as onerror fallback.
    window.ShopAssets?.attachImageFallback(img, window.ShopAssets?.categoryThumbLegacy?.(cat) || catUrl);

    const media = document.createElement('span');
    media.className = 'catalog-tile__media';
    media.appendChild(img);

    const label = document.createElement('span');
    label.className = 'catalog-tile-label';
    label.textContent = categoryLabel(cat);

    btn.appendChild(media);
    btn.appendChild(label);
    btn.addEventListener('click', () => selectCategory(cat));
    grid.appendChild(btn);
  });
  grid.classList.remove('is-loading');
  grid.setAttribute('aria-busy', 'false');
  if (state.category) populateCatalogFilters({ keepSelection: true, category: state.category });
}

// Weight/pricing constants loaded from /api/prices (server is source of truth)
let laborFeeTwd = 5000;
let chinToGrams = 3.75;
let taxRate = 0.05;
let ringSizeMin = 5;
let ringSizeMax = 18;
// Soft UX defaults when product/category config omitted — not a hard ceiling.
const RING_SIZE_DEFAULT_MIN = 5;
const RING_SIZE_DEFAULT_MAX = 18;
const RING_SIZE_FLOOR = 1;
let ringSizeReference = {};

// ── Live price data (from /api/prices) ────────────────────────────────────

let diamondPrice = { "0.1": null, "0.3": null, "0.5": null, "1.0": null };
let diamondOptions = {
  diamondColors: [],
  kinds: [],
  fancyColors: [],
  shapes: [],
  stoneCounts: [2, 3, 4],
  stoneCountCategories: [],
  fancyMinCarat: 0.3,
  nonRoundShapeMinCarat: 0.3,
  nonRoundShapeSurcharge: 0.10,
  defaultStoneCountByCategory: { ring: 2, pendant: 2 },
  earringQuantityMin: 1,
  earringQuantityMax: 2,
};
let pricePerGram = {};  // filled by loadMetalPrices()
let waxToMetalChin = {};
let chainLengthWeightDefaults = {};
let pricesLoaded = false;
let quoteTimer = null;
let quoteRequestId = 0;
let lastQuoteTotal = null;
let lastQuoteFailed = false;
let quoteRefreshPending = false;
let activeQuoteController = null;
const quoteCache = new Map();
let lastSummaryFingerprint = null;
let lastSummaryLoginState = null;
let productImageIndex = 0;

// ── State ──────────────────────────────────────────────────────────────────

let state = {
  category: null,   // pendant / ring / earring / bracelet / chain
  type: null,       // Product id (string)
  gold: null,       // 9k / 14k / 18k / pt950 / s925
  color: null,      // white / yellow / rose / null
  carat: null,      // diamond carat or chain thickness (1.0mm–3.0mm)
  ringSize: null,   // positive integer (>= 1); picker bounds from product config
  engravingBand: '',
  engravingRemark: '',
  engravingGirdle: '',
  lengthCm: null,
  includeChain: false,
  chainProductId: null,
  chainGold: null,
  chainColor: null,
  chainThickness: null,
  chainLength: null,
  diamondKind: 'white',
  fancyColor: null,
  stoneCount: null,
  diamondShape: 'round',
  quantity: 1, // earring single units (1–2); ignored for other categories
};

function isDiamondOnlyCategory(category = state.category) {
  return category === 'diamond';
}

let shopView = 'catalog';
const BRACELET_LENGTH_OPTIONS_CM = [15, 16, 17, 18, 19, 20, 21];
const BRACELET_REFERENCE_LENGTH_CM = 18;

function lengthTableHasWeights(table) {
  return !!(
    table &&
    typeof table === 'object' &&
    Object.keys(table).some((k) => Number(table[k]) > 0)
  );
}

/** Lengths (cm) from admin override or Excel/type standard table. */
function chainLengthOptionsCm(product, thickness) {
  if (!thickness) return [];
  let table = effectiveChainLengthWeights(product)?.[thickness];
  if (!lengthTableHasWeights(table)) {
    // Skip Excel fallback only when this thickness already has real admin wax.
    table = necklaceTypeLengthWeights(product?.chainType || 'douyuan')[thickness];
  }
  if (!table || typeof table !== 'object') return [];
  return Object.keys(table)
    .map((k) => parseInt(k, 10))
    .filter((n) => !Number.isNaN(n) && Number(table[String(n)]) > 0)
    .sort((a, b) => a - b);
}

function thicknessesFromLengthWeights(lw) {
  if (!lw || !Object.keys(lw).length) return [];
  return Object.keys(lw)
    .filter((t) => lengthTableHasWeights(lw[t]))
    .sort((a, b) => parseFloat(a) - parseFloat(b));
}

function chainConfiguredThicknesses(product) {
  const fromProduct = thicknessesFromLengthWeights(effectiveChainLengthWeights(product));
  if (fromProduct.length) return fromProduct;
  return thicknessesFromLengthWeights(
    necklaceTypeLengthWeights(product?.chainType || 'douyuan'),
  );
}

function syncChainThicknessState(options) {
  if (state.chainThickness && options.includes(state.chainThickness)) return;
  // Keep the selector on its placeholder until the customer explicitly
  // chooses a thickness; do not silently select the first/default option.
  state.chainThickness = null;
}

function syncChainLengthState(options, stateKey) {
  const current = state[stateKey] != null ? Number(state[stateKey]) : null;
  if (current != null && options.includes(current)) return;
  state[stateKey] = options.length ? options[0] : null;
}

// ── Shop view ─────────────────────────────────────────────────────────────

const CONFIG_HINT_FADE_MS = 400; // must match .ui-alert transition duration in shop-wizard.css
const configNoticeFadeTimers = new WeakMap();
const CONFIG_NOTICE_STORAGE_KEYS = {
  'ui-alert--default': 'imprint_shop_hint_dismissed_v1',
  'ui-alert--warning': 'imprint_shop_warning_dismissed_v1',
};
function noticeStorageKey(alert) {
  const cls = Object.keys(CONFIG_NOTICE_STORAGE_KEYS).find((cls) => alert.classList.contains(cls));
  return cls ? CONFIG_NOTICE_STORAGE_KEYS[cls] : null;
}
function isNoticeDismissed(alert) {
  const key = noticeStorageKey(alert);
  if (!key) return false;
  try { return localStorage.getItem(key) === '1'; } catch (_) { return false; }
}
function markNoticeDismissed(alert) {
  const key = noticeStorageKey(alert);
  if (!key) return;
  try { localStorage.setItem(key, '1'); } catch (_) {}
}
function resetConfigNotices() {
  document.querySelectorAll('.shop-config-notices .ui-alert').forEach((alert) => {
    clearTimeout(configNoticeFadeTimers.get(alert));
    if (isNoticeDismissed(alert)) {
      alert.classList.add('ui-alert--dismissed');
      alert.style.display = 'none';
    } else {
      alert.classList.remove('ui-alert--dismissed');
      alert.style.display = '';
    }
  });
}
function dismissConfigNotice(alert) {
  if (!alert) return;
  clearTimeout(configNoticeFadeTimers.get(alert));
  markNoticeDismissed(alert);
  alert.classList.add('ui-alert--dismissed');
  configNoticeFadeTimers.set(alert, setTimeout(() => { alert.style.display = 'none'; }, CONFIG_HINT_FADE_MS));
}
document.getElementById('shop-config-hint-close')?.addEventListener('click', () =>
  dismissConfigNotice(document.querySelector('.shop-config-notices .ui-alert--default')));
document.getElementById('shop-config-warning-close')?.addEventListener('click', () =>
  dismissConfigNotice(document.querySelector('.shop-config-notices .ui-alert--warning')));

/** Wizard history depth from the entry landing (0). Each forward step pushState +1. */
let shopHistoryDepth = 0;

function shopViewDepth(view) {
  if (view === 'product') return 2;
  if (view === 'styles') return 1;
  return 0;
}

function buildShopUrl() {
  const params = new URLSearchParams();
  if (window.shopConfig?.preview || new URLSearchParams(window.location.search).get('preview') === '1') {
    params.set('preview', '1');
  }
  if ((shopView === 'styles' || shopView === 'product') && state.category) {
    params.set('category', state.category);
  }
  if (shopView === 'product' && state.type) {
    params.set('product', state.type);
  }
  const qs = params.toString();
  return window.location.pathname + (qs ? '?' + qs : '') + window.location.hash;
}

function shopHistoryState() {
  return {
    shop: true,
    depth: shopHistoryDepth,
    view: shopView,
    category: state.category || null,
    type: state.type || null,
  };
}

/** Keep address bar in sync with wizard depth.
    empty at catalog, ?category= at styles, ?category=&product= at configure.
    Skipped in cart/order-edit so cart_edit=/editOrder= survive refresh.
    mode: 'push' | 'replace' | 'none' */
function syncShopUrl(mode) {
  if (mode === 'none' || window.cartEditData || window.editData) return;
  const url = buildShopUrl();
  const current = window.location.pathname + window.location.search + window.location.hash;
  if (mode === 'push') {
    shopHistoryDepth += 1;
    history.pushState(shopHistoryState(), '', url);
    return;
  }
  if (url !== current || !history.state?.shop) {
    history.replaceState(shopHistoryState(), '', url);
  }
}

function clearShopWizardSelection() {
  state.category = null;
  state.type = null;
  state.gold = null;
  state.color = null;
  state.carat = null;
  state.ringSize = null;
  state.engravingBand = '';
  state.engravingRemark = '';
  state.engravingGirdle = '';
  state.lengthCm = null;
  state.includeChain = false;
  state.chainProductId = null;
  state.chainGold = null;
  state.chainColor = null;
  state.chainThickness = null;
  state.chainLength = null;
  document.querySelectorAll('.cat-btn, #metal-btn-row .metal-btn, #color-btn-row .color-btn').forEach(b => b.classList.remove('active'));
  clearRingSizeSelection();
  updateChainOptions();
}

/** Prefer real history when we pushed steps; else fall back to caller UI reset. */
function shopInAppHistoryBack(targetView) {
  if (shopHistoryDepth <= 0) return false;
  if (targetView === 'catalog') {
    history.go(-shopHistoryDepth);
    return true;
  }
  if (targetView === 'styles') {
    history.back();
    return true;
  }
  return false;
}

async function applyShopHistoryState(st) {
  const view = (st && st.view) || 'catalog';
  const category = st && st.category;
  const typeId = st && st.type;
  const opts = { history: 'none', skipScroll: true };

  if (view === 'catalog' || !category) {
    clearShopWizardSelection();
    setShopView('catalog', opts);
    updateSummary();
    return;
  }

  if (view === 'styles') {
    if (category === 'diamond') {
      if (state.category !== category || shopView === 'catalog') {
        await selectCategory(category, { ...opts, typeId: typeId || undefined });
      } else if (typeId && state.type !== typeId) {
        await selectType(typeId, opts);
      } else {
        setShopView('product', opts);
        updateSummary();
      }
      return;
    }
    if (state.category !== category || shopView === 'catalog') {
      await selectCategory(category, opts);
    } else {
      setShopView('styles', opts);
      renderTypeCards();
      updateSummary();
    }
    return;
  }

  if (state.category !== category || (isDiamondOnlyCategory(category) && shopView !== 'product')) {
    await selectCategory(category, opts);
  }
  if (typeId && state.type !== typeId) {
    await selectType(typeId, opts);
  } else {
    setShopView('product', opts);
    updateSummary();
  }
}

window.addEventListener('popstate', (event) => {
  if (window.cartEditData || window.editData) return;
  if (!document.getElementById('shop-catalog')) return;

  const st = event.state;
  if (st && st.shop) {
    shopHistoryDepth = typeof st.depth === 'number' ? st.depth : 0;
    applyShopHistoryState(st);
    return;
  }

  shopHistoryDepth = 0;
  const params = new URLSearchParams(window.location.search);
  const category = params.get('category');
  const type = params.get('product') || params.get('type') || params.get('series');
  if (type && category) applyShopHistoryState({ view: 'product', category, type });
  else if (category) {
    applyShopHistoryState({
      view: category === 'diamond' ? 'product' : 'styles',
      category,
      type,
    });
  }
  else applyShopHistoryState({ view: 'catalog' });
});

function setShopView(view, options) {
  const opts = options || {};
  if (view === 'styles' && isDiamondOnlyCategory()) view = 'product';
  const prevView = shopView;
  shopView = view;
  const catalogSection = document.getElementById('shop-catalog');
  const styles = document.getElementById('shop-styles');
  const product = document.getElementById('shop-product');
  if (catalogSection) catalogSection.classList.toggle('hidden', view !== 'catalog');
  if (styles) styles.classList.toggle('hidden', view !== 'styles');
  if (product) product.classList.toggle('hidden', view !== 'product');

  const page = document.querySelector('.shop-page');
  page?.classList.toggle('shop-view--product', view === 'product');
  page?.classList.remove('shop-step-catalog', 'shop-step-styles', 'shop-step-product');
  page?.classList.add('shop-step-' + view);
  updateLengthStep();
  updateRingSizeStep();
  updateBreadcrumb();
  updateSummary();
  updateShopProgress();
  updateWizardGuide();
  updateDiamondWizardChrome();
  if (view === 'product') { updateLargeImage(); resetConfigNotices(); }
  else resetMobilePriceSheet();
  const hist = opts.history;
  if (hist !== 'none') {
    const mode = hist || (shopViewDepth(view) > shopViewDepth(prevView) ? 'push' : 'replace');
    syncShopUrl(mode);
  }
  const skipScroll = opts.skipScroll || document.documentElement.classList.contains('shop-tour-active');
  if (!skipScroll) {
    // Reset window + nested shop scroller so style→configure lands at top on mobile.
    window.scrollTo({ top: 0, behavior: 'smooth' });
    document.querySelector('.shop-scroll')?.scrollTo({ top: 0, behavior: 'smooth' });
    document.querySelector('.shop-main')?.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

const SHOP_STEPS = {
  catalog: { step: 1, progress: 12 },
  styles: { step: 2, progress: 50 },
  product: { step: 3, progress: 100 },
};

// Memorial diamond: catalog → configure (skip style grid; color picked on step 3).
const DIAMOND_SHOP_STEPS = {
  catalog: { step: 1, progress: 50 },
  styles: { step: 2, progress: 50 },
  product: { step: 3, progress: 100 },
};

const DIAMOND_WHITE_PREVIEW_PATH = 'diamonds/colors/white.png';
const MEMORIAL_DIAMOND_COLOR_IDS = ['white', 'yellow', 'blue', 'pink'];

function activeShopSteps() {
  return isDiamondOnlyCategory() ? DIAMOND_SHOP_STEPS : SHOP_STEPS;
}

function memorialDiamondColorFromProduct(product) {
  const fromDefault = String(product?.defaultColor || '').toLowerCase();
  if (MEMORIAL_DIAMOND_COLOR_IDS.includes(fromDefault)) return fromDefault;
  const key = String(product?.styleKey || product?.id || '').toLowerCase();
  const m = key.match(/^diamond-(white|yellow|blue|pink)$/);
  return m ? m[1] : null;
}

function memorialDiamondProductForColor(colorId) {
  const color = String(colorId || '').toLowerCase();
  if (!MEMORIAL_DIAMOND_COLOR_IDS.includes(color)) return null;
  const list = productsFor('diamond');
  return list.find((p) => memorialDiamondColorFromProduct(p) === color)
    || list.find((p) => String(p?.styleKey || '') === `diamond-${color}`)
    || null;
}

/** Default memorial SKU when entering configure (white, else first catalog row). */
function defaultMemorialDiamondTypeId() {
  const white = memorialDiamondProductForColor('white');
  if (white?.id != null) return String(white.id);
  if (white?.styleKey) return String(white.styleKey);
  const list = productsFor('diamond');
  const first = list[0];
  if (first?.id != null) return String(first.id);
  if (first?.styleKey) return String(first.styleKey);
  return 'diamond-white';
}

function applyMemorialDiamondProductColor(product) {
  const color = memorialDiamondColorFromProduct(product);
  if (!color) return;
  if (color === 'white') {
    state.diamondKind = 'white';
    state.fancyColor = null;
  } else {
    state.diamondKind = 'fancy';
    state.fancyColor = color;
  }
}

function updateDiamondWizardChrome() {
  const skipStyles = isDiamondOnlyCategory();
  const stylesStep = document.getElementById('wizard-step-styles');
  const backBtn = document.getElementById('back-to-styles');
  if (stylesStep) stylesStep.hidden = skipStyles;
  if (backBtn) backBtn.textContent = skipStyles ? tr('shop_back_catalog') : tr('shop_back_styles');
}

const WIZARD_GUIDE = {
  catalog: {
    eyebrow: 'DNA 紀念鑽石 · 六大系列',
    title: '六大 DNA 紀念鑽石系列線上試算',
    desc: '滿月鑽石、寵物鑽石、結髮鑽石、全家福鑽石、生命鑽石、真我鑽石，選擇系列與珠寶款式後即可設定規格並查看訂製參考價格。',
  },
  styles: {
    eyebrow: '線上訂製 · 三步完成',
    title: '挑選喜歡的款式',
    desc: '點選卡片進入配置；需要時可展開「篩選款式」。',
  },
  product: {
    eyebrow: '線上訂製 · 三步完成',
    title: '配置您的專屬設計',
    desc: '選擇下方規格，右側會即時更新試算價格。',
  },
};

function updateWizardGuide() {
  let copy = WIZARD_GUIDE[shopView] || WIZARD_GUIDE.catalog;
  if (isDiamondOnlyCategory() && shopView === 'product') {
    copy = {
      eyebrow: '線上訂製 · 三步完成',
      title: '配置您的紀念鑽石',
      desc: '選擇鑽石顏色、切工與克拉，右側即時更新試算價格。',
    };
  }
  const eyebrow = document.getElementById('shop-wizard-eyebrow');
  const title = document.getElementById('shop-wizard-title');
  const desc = document.getElementById('shop-wizard-desc');
  if (eyebrow) eyebrow.textContent = copy.eyebrow;
  if (title) title.textContent = copy.title;
  if (desc) desc.textContent = copy.desc;
}

function updateShopProgress() {
  const steps = activeShopSteps();
  const meta = steps[shopView] || steps.catalog;

  const skipStyles = isDiamondOnlyCategory();
  document.querySelectorAll('.shop-stepper-step').forEach((btn) => {
    const step = btn.dataset.step;
    if (skipStyles && step === 'styles') {
      btn.hidden = true;
      return;
    }
    btn.hidden = false;
    const stepNum = steps[step]?.step || 0;
    const current = meta.step;
    const effectiveView = skipStyles && shopView === 'product' ? 'product' : shopView;
    btn.classList.toggle('is-active', step === effectiveView);
    btn.classList.toggle('is-done', stepNum < current);
    btn.disabled = stepNum > current;
    if (step === 'catalog') btn.disabled = false;
    if (step === 'styles') btn.disabled = !state.category;
    if (step === 'product') btn.disabled = !state.category || !state.type;
  });

  updateFavoriteButton();
}

function updateFavoriteButton() {
  const button = document.getElementById('favorite-btn');
  if (!button) return;
  // Always clickable on product step — not gated on price or full options
  button.disabled = shopView !== 'product';
}

function initWizardRail() {
  document.getElementById('wizard-step-catalog')?.addEventListener('click', () => {
    if (shopView !== 'catalog') document.getElementById('back-to-catalog')?.click();
  });
  document.getElementById('wizard-step-styles')?.addEventListener('click', () => {
    if (!state.category || isDiamondOnlyCategory()) return;
    if (shopView === 'product') document.getElementById('back-to-styles')?.click();
    else if (shopView === 'catalog') selectCategory(state.category);
  });
  document.getElementById('wizard-step-product')?.addEventListener('click', () => {
    if (!state.type) return;
    if (shopView !== 'product') {
      if (isDiamondOnlyCategory()) selectType(state.type, { skipScroll: true });
      else {
        const card = document.querySelector(`.type-card[data-type="${state.type}"]`);
        if (card) card.click();
      }
    }
  });
}

function updateBreadcrumb() {
  const el = document.getElementById('shop-breadcrumb');
  if (!el) return;
  const ol = document.createElement('ol');
  ol.className = 'shop-breadcrumb-list';

  const addLink = (label, onClick) => {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'shop-breadcrumb-link';
    btn.textContent = label;
    btn.addEventListener('click', onClick);
    li.appendChild(btn);
    ol.appendChild(li);
  };

  const addCurrent = (label) => {
    const li = document.createElement('li');
    li.className = 'is-current';
    li.textContent = label;
    ol.appendChild(li);
  };

  if (shopView === 'catalog') {
    addCurrent(tr('shop_breadcrumb_shop'));
  } else {
    addLink(tr('shop_breadcrumb_shop'), () => {
      document.getElementById('back-to-catalog')?.click();
    });
    if (shopView === 'styles' && state.category) {
      addCurrent(tr('cat_' + state.category));
    } else if (shopView === 'product') {
      if (state.category) {
        addLink(tr('cat_' + state.category), () => {
          if (isDiamondOnlyCategory()) document.getElementById('back-to-catalog')?.click();
          else document.getElementById('back-to-styles')?.click();
        });
      }
      const product = getSelectedProduct();
      addCurrent(product ? productName(product) : tr('shop_breadcrumb_shop'));
    }
  }

  el.innerHTML = '';
  el.appendChild(ol);
}

function updateProductHeader() {
  const title = document.getElementById('product-title');
  const subtitle = document.getElementById('product-subtitle');
  const description = document.getElementById('product-description');
  const previewColorTitle = document.getElementById('product-preview-color-title');
  const previewColorDesc = document.getElementById('product-preview-color-desc');
  const isChain = state.category === 'chain';
  if (previewColorTitle) {
    const titleKey = isChain ? 'shop_preview_color_title_chain' : 'shop_preview_color_title';
    previewColorTitle.setAttribute('data-i18n', titleKey);
    previewColorTitle.textContent = tr(titleKey);
  }
  if (previewColorDesc) {
    const descKey = isChain ? 'shop_preview_color_desc_chain' : 'shop_preview_color_desc';
    previewColorDesc.setAttribute('data-i18n', descKey);
    previewColorDesc.textContent = tr(descKey);
  }
  if (!title) return;
  const product = getSelectedProduct();
  if (product) {
    // Memorial diamond product name = gem color (白鑽/黃鑽/…).
    title.textContent = productName(product);
    if (subtitle) {
      let sub = tr('cat_' + state.category);
      const badge = stoneCountBadgeText();
      if (badge) sub = sub ? `${sub} · ${badge}` : badge;
      subtitle.textContent = sub;
    }
    if (description) {
      const desc = shopLang() === 'en'
        ? (product.descriptionEn || product.descriptionZh || '')
        : (product.descriptionZh || product.descriptionEn || '');
      description.textContent = desc || tr('shop_no_description');
      description.hidden = false;
    }
  } else {
    title.textContent = '—';
    if (subtitle) subtitle.textContent = '';
    if (description) {
      description.textContent = tr('shop_no_description');
      description.hidden = false;
    }
  }
}

function initProductTabs() {
  const nav = document.querySelector('.product-tab-nav');
  if (!nav) return;
  nav.querySelectorAll('.product-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      nav.querySelectorAll('.product-tab-btn').forEach(b => {
        const active = b.dataset.tab === tab;
        b.classList.toggle('active', active);
        b.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      document.querySelectorAll('.product-tab-panel').forEach(panel => {
        const show = panel.id === `product-panel-${tab}`;
        panel.classList.toggle('active', show);
        panel.hidden = !show;
      });
    });
  });
}

function updateConfigChips() {
  const container = document.getElementById('config-chips');
  if (!container) return;
  container.innerHTML = '';
  const chips = [];
  if (state.carat) {
    chips.push(state.category === 'chain' ? state.carat : state.carat + ' ct');
  }
  if (state.gold) chips.push(materialLabel(state.gold, state.color));
  if (state.category !== 'chain') {
    const colorId = selectedDiamondColorId();
    const colorMeta = diamondColorOptions().find(c => c.id === colorId);
    if (colorMeta) chips.push(diamondMetaLabel(colorMeta));
    const stoneBadge = stoneCountBadgeText();
    if (stoneBadge) chips.push(stoneBadge);
  }
  if (state.category !== 'chain' && isNonRoundShape()) {
    const shape = diamondShapeDisplayMeta();
    if (shape) chips.push(diamondMetaLabel(shape));
  }
  if (state.ringSize) chips.push('#' + state.ringSize);
  if (state.engravingBand) chips.push(`${tr('step_engraving_band')}: ${state.engravingBand}`);
  if (state.engravingRemark) chips.push(`${tr('step_engraving_remark')}: ${state.engravingRemark}`);
  chips.forEach(text => {
    const span = document.createElement('span');
    span.className = 'config-chip';
    span.textContent = text;
    container.appendChild(span);
  });
  if (state.engravingGirdle) {
    const span = document.createElement('span');
    span.className = 'config-chip config-chip--engrave';
    span.textContent = tr('step_engraving_girdle') + ': ' + state.engravingGirdle;
    container.appendChild(span);
  }
}

function effectiveColor() {
  if (state.color) return state.color;
  const product = getSelectedProduct();
  if (state.category === 'chain' && state.gold) {
    return product?.defaultColor || materialColor(state.gold);
  }
  if (product) return product.defaultColor || 'white';
  return null;
}

const SUBMIT_FIELD_TARGETS = {
  category: () => document.getElementById('shop-catalog'),
  type: () => (isDiamondOnlyCategory()
    ? document.getElementById('fancy-diamond-step')
    : document.getElementById('shop-styles')),
  carat: () => document.getElementById('carat-step'),
  gold: () => document.getElementById('metal-step'),
  color: () => document.getElementById('color-step'),
  ringSize: () => document.getElementById('ringsize-step'),
  length: () => document.getElementById('chain-length-step'),
  fancyColor: () => document.getElementById('fancy-diamond-step'),
  diamondShape: () => document.getElementById('diamond-shape-step'),
  pendantChain: () => document.getElementById('pendant-chain-step'),
  pendantChainThickness: () => document.querySelector('#pendant-chain-options .pendant-chain-thickness'),
  pendantChainLength: () => document.querySelector('#pendant-chain-options .pendant-chain-length'),
};

function getMissingSubmitFields() {
  const missing = [];
  if (!state.category) missing.push('category');
  if (!state.type) missing.push('type');
  if (!isDiamondOnlyCategory()) {
    if (!state.gold) missing.push('gold');
    else {
      const product = getSelectedProduct();
      if (needsColorSelection(state.gold, product) && !state.color) missing.push('color');
    }
  }
  if (!state.carat) missing.push('carat');
  if (state.category === 'ring' && !state.ringSize) missing.push('ringSize');
  if (state.category === 'chain' && !state.lengthCm) missing.push('length');
  if (state.category === 'bracelet' && !state.lengthCm) missing.push('length');
  if (state.category !== 'chain' && state.diamondKind === 'fancy' && !state.fancyColor) {
    missing.push('fancyColor');
  }
  if (state.category !== 'chain' && isDiamondShapeOtherPending()) {
    missing.push('diamondShape');
  }
  if (state.category === 'pendant' && state.includeChain) {
    if (!state.chainProductId) missing.push('pendantChain');
    if (!state.chainThickness) missing.push('pendantChainThickness');
    if (!state.chainLength) missing.push('pendantChainLength');
  }
  return missing;
}

function isReadyToSubmit() {
  if (getMissingSubmitFields().length) return false;
  if (state.category === 'chain' && state.gold === '9k') {
    const chainProduct = getSelectedProduct();
    if (chainProduct && chainProduct.defaultColor !== 'white') return false;
  }
  return true;
}

function clearAllSubmitFieldHighlights() {
  document.querySelectorAll('.shop-field-invalid').forEach((el) => {
    el.classList.remove('shop-field-invalid', 'shop-field-invalid--flash');
  });
}

function clearFixedSubmitFieldHighlights() {
  const missing = new Set(getMissingSubmitFields());
  Object.entries(SUBMIT_FIELD_TARGETS).forEach(([key, getEl]) => {
    const el = getEl();
    if (!el || missing.has(key)) return;
    el.classList.remove('shop-field-invalid', 'shop-field-invalid--flash');
  });
}

function navigateToMissingSubmitView(missing) {
  if (!missing.length) return;
  const first = missing[0];
  if (first === 'category') {
    setShopView('catalog');
    return;
  }
  if (first === 'type') {
    if (isDiamondOnlyCategory()) {
      const typeId = defaultMemorialDiamondTypeId();
      if (typeId) {
        selectType(typeId, { skipScroll: true });
        return;
      }
    }
    setShopView('styles');
    return;
  }
  if (state.category && state.type) {
    setShopView('product', { skipScroll: true });
  }
}

function highlightMissingSubmitFields(missing) {
  navigateToMissingSubmitView(missing);
  requestAnimationFrame(() => {
    missing.forEach((key, index) => {
      const el = SUBMIT_FIELD_TARGETS[key]?.();
      if (!el) return;
      el.classList.add('shop-field-invalid');
      if (index === 0) {
        el.classList.add('shop-field-invalid--flash');
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });
  });
}

function isSubmitPriceReady() {
  if (!shopUsesApi()) return true;
  if (!isReadyToSubmit()) return false;
  return lastQuoteTotal != null;
}

function effectiveQuoteTotal(total) {
  if (total != null) return total;
  if (quoteRefreshPending && lastQuoteTotal != null) return lastQuoteTotal;
  return null;
}

function updatePriceHint(total) {
  const hint = document.getElementById('price-hint');
  if (!hint) return;
  const optionsReady = isReadyToSubmit();
  const displayTotal = effectiveQuoteTotal(total);
  const canOrder = optionsReady && (displayTotal != null || !shopUsesApi());
  if (canOrder) {
    hint.hidden = true;
    return;
  }
  hint.hidden = false;
  if (total == null && quoteRefreshPending && lastQuoteTotal != null) {
    hint.hidden = true;
  } else if (!optionsReady) {
    lastQuoteFailed = false;
    hint.textContent = tr('shop_complete_options');
  } else if (lastQuoteFailed && total == null) {
    hint.textContent = tr('shop_price_unavailable');
  } else {
    hint.textContent = tr('shop_complete_options');
  }
}

function updateCtaState(total) {
  const optionsReady = isReadyToSubmit();
  const displayTotal = effectiveQuoteTotal(total);
  const ready = optionsReady && (displayTotal != null || !shopUsesApi());

  const confirmBtns = [document.getElementById('confirm-btn'), document.getElementById('confirm-btn-mobile')];
  const cartBtns = [document.getElementById('cart-btn'), document.getElementById('cart-btn-mobile')];
  ['share-config-btn', 'quote-sheet-btn'].forEach(id => {
    const button = document.getElementById(id);
    if (button) button.disabled = !ready;
  });
  updateFavoriteButton();

  if (isGuestShop || shopIsLoggedIn === false) {
    confirmBtns.forEach(btn => {
      if (!btn) return;
      btn.hidden = false;
      btn.disabled = false;
      btn.textContent = tr('shop_guest_login');
    });
    cartBtns.forEach(btn => { if (btn) { btn.hidden = true; btn.disabled = true; } });
  } else if (window.cartEditData) {
    cartBtns.forEach(btn => {
      if (!btn) return;
      btn.hidden = true;
      btn.disabled = true;
    });
    confirmBtns.forEach(btn => {
      if (!btn) return;
      btn.hidden = false;
      btn.disabled = false;
      btn.textContent = btn.id === 'confirm-btn-mobile' ? tr('cart_update_short') : tr('cart_update');
    });
  } else {
    confirmBtns.forEach(btn => {
      if (!btn) return;
      btn.hidden = false;
      btn.disabled = false;
      if (window.editData) {
        btn.textContent = tr('btn_update');
      } else {
        btn.textContent = tr('btn_add_order');
      }
    });
    cartBtns.forEach(btn => {
      if (!btn) return;
      btn.hidden = false;
      btn.disabled = !!window.editData;
      btn.textContent = btn.id === 'cart-btn-mobile' ? tr('btn_add_cart_short') : tr('btn_add_cart');
    });
  }

  clearFixedSubmitFieldHighlights();
  updatePriceHint(total);
  const bar = document.getElementById('mobile-buy-bar');
  const showMobileBar = shopView === 'product' && !!state.category;
  if (bar) bar.classList.toggle('hidden', !showMobileBar);
  document.body.classList.toggle('shop-mobile-bar', showMobileBar);
}

// ── Helpers ───────────────────────────────────────────────────────────────

/** Weight in chin (錢) for a product's metal+carat variant, or null. */
function lookupWeight(category, type, gold, carat) {
  const product = getProduct(category, type);
  const w = product?.weights?.[gold]?.[carat];
  return w == null ? null : w;
}

/** Seller-set fixed price override (TWD) for a variant, or null if the
 * price should be computed from the live formula instead. */
function lookupManualPrice(category, type, gold, carat) {
  const product = getProduct(category, type);
  const p = product?.manualPrices?.[gold]?.[carat];
  return p == null ? null : p;
}

/**
 * Step 2 style grid candidates — admin block order, thumb (lite), letter stock.
 */
function styleGridImageCandidates(product) {
  const cat = String(product?.category || state.category || '').toLowerCase();
  const out = [];
  const seen = new Set();
  const add = (url) => {
    if (!url || seen.has(url)) return;
    seen.add(url);
    out.push(url);
  };

  // Chain A/B/C are color-locked SKUs — keep style metal (not forced silver).
  if (cat === 'chain') {
    add(productImageUrl(product, product?.defaultColor || 'white', 'white'));
    if (product?.thumbUrl && isUsableCatalogImageUrl(product.thumbUrl)) add(product.thumbUrl);
    return out;
  }

  // Memorial diamond color cards: prefer round cut thumb for that color.
  if (cat === 'diamond' || isMemorialDiamondProduct(product)) {
    const round = product?.images?.round;
    if (Array.isArray(round)) round.filter(Boolean).forEach(add);
    if (product?.thumbUrl && isUsableCatalogImageUrl(product.thumbUrl)) add(product.thumbUrl);
    for (const url of orderedCatalogImageUrls(product)) add(url);
    const color = memorialDiamondColorFromProduct(product) || 'white';
    add(diamondMatrixImageUrl('round', color));
    return out;
  }

  const liteCatalog = !product?.images || !Object.keys(product.images).length;
  // Full catalog: 預設顏色 slots first; lite uses server thumbUrl (same priority).
  for (const url of orderedCatalogImageUrls(product)) add(url);

  if (product?.thumbUrl && isUsableCatalogImageUrl(product.thumbUrl)) {
    add(product.thumbUrl);
  }

  const assetId = productAssetId(product);
  if (assetId && window.ShopAssets) {
    const opts = cat === 'pendant' ? { pendantOnly: true } : {};
    if (window.ShopAssets.productImageResolve) {
      const resolved = window.ShopAssets.productImageResolve(
        assetId, 'white', 'white', 'white', opts,
      );
      if (resolved.src && !/\/images\/shop\/styles\/[a-z]+-[A-C]\.svg/i.test(resolved.src)) {
        add(resolved.src);
      }
      (resolved.fallbacks || []).forEach(add);
    }
    const png = window.ShopAssets.productImage?.(assetId, 'white', 'white', 'white', opts);
    if (png) add(png);
    add(window.ShopAssets.styleThumb?.(assetId));
  }

  return out;
}

/** Step 2 style grid — silver (white metal) + white diamond. Fancy/other metals = step 3. */
function styleGridImageUrl(product) {
  return styleGridImageCandidates(product)[0] || '';
}

function imageUrl(category, type, metalColor, diamondColor) {
  return productImageUrl(
    getProduct(category, type),
    metalColor ?? previewColor(),
    diamondColor ?? selectedDiamondColorId(),
  );
}

// ── Metal price fetch ─────────────────────────────────────────────────────

/**
 * /api/prices only returns money numbers — never diamondColors/fancyColors tables.
 * Always seed UI option metadata from ShopPricingLocal so API mode still shows 黃/藍/粉.
 */
function ensureDiamondOptionTables() {
  const localOpts = window.ShopPricingLocal?.pricesPayload?.()?.diamondOptions;
  if (!localOpts || typeof localOpts !== 'object') return false;
  const needColors = !diamondOptions.diamondColors?.length;
  const needFancy = !diamondOptions.fancyColors?.length;
  const needShapes = !diamondOptions.shapes?.length;
  if (!needColors && !needFancy && !needShapes) return false;
  diamondOptions = {
    ...diamondOptions,
    ...localOpts,
    // Keep any API-provided money-adjacent fields already on diamondOptions.
    diamondColors: needColors
      ? (localOpts.diamondColors || diamondOptions.diamondColors)
      : diamondOptions.diamondColors,
    fancyColors: needFancy
      ? (localOpts.fancyColors || diamondOptions.fancyColors)
      : diamondOptions.fancyColors,
    shapes: needShapes
      ? (localOpts.shapes || diamondOptions.shapes)
      : diamondOptions.shapes,
  };
  return true;
}

async function loadMetalPrices() {
  const pricePanel = document.getElementById("shop-price-panel");
  pricePanel?.classList.add("is-loading-prices");
  // Seed color/shape tables before first product render (API path skips local money).
  ensureDiamondOptionTables();
  try {
    const localPayload = window.ShopPricingLocal?.pricesPayload?.();
    if (localPayload && (shopUsesLocalPricing() || !shopUsesApi())) {
      Object.assign(pricePerGram, localPayload.perGram);
      Object.assign(diamondPrice, localPayload.diamond);
      if (localPayload.laborFeeTwd != null) laborFeeTwd = Number(localPayload.laborFeeTwd);
      else if (typeof localPayload.laborFee === 'number') laborFeeTwd = localPayload.laborFee;
      if (localPayload.chinToGrams != null) chinToGrams = localPayload.chinToGrams;
      if (localPayload.taxRate != null) taxRate = localPayload.taxRate;
      if (localPayload.ringSizeMin != null) ringSizeMin = localPayload.ringSizeMin;
      if (localPayload.ringSizeMax != null) ringSizeMax = localPayload.ringSizeMax;
      ringSizeReference = localPayload.ringSizeReference || {};
      if (localPayload.diamondOptions) {
        diamondOptions = { ...diamondOptions, ...localPayload.diamondOptions };
      }
      pricesLoaded = true;
      populateRingSizeSelect();
      renderRingSizeGuide();
      updateSummary();
      const initialData = window.cartEditData || window.editData || window.prefillData;
      if (initialData?.ringSize) {
        setRingSizeActive(initialData.ringSize);
      }
      return;
    }
    if (!shopUsesApi()) {
      throw new Error('static pricing missing');
    }
    const { res, data } = await shopApiFetch('/api/prices');
    if (!res.ok) throw new Error(`API ${res.status}`);
    Object.assign(pricePerGram, data.perGram);
    Object.assign(diamondPrice, data.diamond);
    if (data.laborFeeTwd != null) laborFeeTwd = Number(data.laborFeeTwd);
    else if (typeof data.laborFee === 'number') laborFeeTwd = data.laborFee;
    if (data.categoryAddonPrices) {
      window.ShopPricingLocal?.setCategoryAddons?.(data.categoryAddonPrices);
    }
    if (data.waxToMetalChin && typeof data.waxToMetalChin === 'object') {
      waxToMetalChin = data.waxToMetalChin;
    }
    if (data.chainLengthWeights && typeof data.chainLengthWeights === 'object') {
      chainLengthWeightDefaults = data.chainLengthWeights;
    }
    if (data.chinToGrams != null) chinToGrams = data.chinToGrams;
    if (data.taxRate != null) taxRate = data.taxRate;
    if (data.ringSizeMin != null) ringSizeMin = data.ringSizeMin;
    if (data.ringSizeMax != null) ringSizeMax = data.ringSizeMax;
    ringSizeReference = data.ringSizeReference || {};
    if (data.diamondOptions) {
      diamondOptions = { ...diamondOptions, ...data.diamondOptions };
    }
    // API omits diamond option tables — keep ShopPricingLocal UI metadata.
    ensureDiamondOptionTables();
    pricesLoaded = true;
    populateRingSizeSelect();
    renderRingSizeGuide();
    if (state.type) updateDiamondSteps();
    updateSummary();
    const initialData = window.cartEditData || window.editData || window.prefillData;
    if (initialData?.ringSize) {
      setRingSizeActive(initialData.ringSize);
    }
  } catch (err) {
    pricesLoaded = false;
    ensureDiamondOptionTables();
    updateSummary();
  } finally {
    pricePanel?.classList.remove("is-loading-prices");
  }
}

/** Soft poll: GET /api/bot-gold every ~25s while calculator tab visible (cache read only). */
const GOLD_POLL_MS = 25 * 1000;
let lastLiveGoldRatesKey = null;
let goldPollTimer = null;
let liveGoldPollInitialized = false;

function alloyRatesKey(rates) {
  if (!rates || typeof rates !== 'object') return '';
  return Object.keys(rates)
    .sort()
    .map((k) => `${k}:${rates[k]}`)
    .join('|');
}

function applyLiveGoldRates(alloyRates) {
  const key = alloyRatesKey(alloyRates);
  if (key === lastLiveGoldRatesKey) return false;
  lastLiveGoldRatesKey = key;
  quoteCache.clear();
  window.ShopPricingLocal?.setLiveGoldRates?.(alloyRates);
  Object.assign(pricePerGram, alloyRates);
  return true;
}

async function loadLiveGoldRates() {
  try {
    const { res, data } = await shopApiFetch('/api/bot-gold', { cache: false });
    if (!res.ok || !data?.alloyRates) return;
    if (!applyLiveGoldRates(data.alloyRates)) return;
    // Re-quote when metal picked; local + API both read gold_price_cache via quote path.
    if (state.gold) scheduleQuoteRefresh({ force: true });
  } catch (err) {
    console.error('failed to load live gold rates', err);
  }
}

function stopLiveGoldPoll() {
  if (goldPollTimer == null) return;
  clearInterval(goldPollTimer);
  goldPollTimer = null;
}

function startLiveGoldPoll() {
  stopLiveGoldPoll();
  if (document.visibilityState !== 'visible') return;
  goldPollTimer = setInterval(() => {
    if (document.visibilityState !== 'visible') return;
    loadLiveGoldRates();
  }, GOLD_POLL_MS);
}

function initLiveGoldPoll() {
  loadLiveGoldRates();
  startLiveGoldPoll();
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      loadLiveGoldRates();
      startLiveGoldPoll();
    } else {
      stopLiveGoldPoll();
    }
  });
}

function ensureLiveGoldPolling() {
  if (liveGoldPollInitialized) return;
  liveGoldPollInitialized = true;
  initLiveGoldPoll();
}

// ── Render helpers ────────────────────────────────────────────────────────

function applyTypeGridLayout(grid, count) {
  if (!grid) return;
  ['xl', 'lg', 'md', 'sm', 'xs'].forEach((size) =>
    grid.classList.remove(`type-grid--size-${size}`));
  grid.dataset.count = String(count);

  let size;
  let cols;
  if (count <= 1) {
    size = 'xl';
    cols = 1;
  } else if (count <= 3) {
    size = 'lg';
    cols = count;
  } else if (count <= 4) {
    size = 'md';
    cols = 2;
  } else if (count <= 6) {
    size = 'md';
    cols = 3;
  } else if (count <= 9) {
    size = 'sm';
    cols = 3;
  } else if (count <= 12) {
    size = 'sm';
    cols = 4;
  } else {
    size = 'xs';
    cols = null;
  }

  grid.classList.add(`type-grid--size-${size}`);
  if (cols != null) {
    grid.style.setProperty('--type-cols', String(cols));
  } else {
    grid.style.removeProperty('--type-cols');
  }
}

function estimatedProductPrice(product) {
  const manual = Object.values(product.manualPrices || {})
    .flatMap(group => Object.values(group || {}))
    .filter(value => Number.isFinite(Number(value)))
    .map(Number);
  if (manual.length) return Math.min(...manual);

  // Loose memorial diamonds — diamond list price only
  if (!(product.golds || []).length && (product.carats || []).length) {
    const loose = (product.carats || [])
      .map((c) => Number(diamondPrice[c]))
      .filter((n) => Number.isFinite(n) && n > 0);
    if (loose.length) return Math.min(...loose);
  }

  const estimates = [];
  Object.entries(product.weights || {}).forEach(([gold, byCarat]) => {
    const rate = pricePerGram[gold];
    if (!rate) return;
    Object.entries(byCarat || {}).forEach(([carat, waxChin]) => {
      const diamond = Number(diamondPrice[carat] || 0);
      const waxFactor = waxToMetalChin[gold] ?? 1;
      const perChin = rate * chinToGrams;
      const metalChin = waxFactor * Number(waxChin);
      const metal = metalChin * perChin;
      estimates.push(diamond + metal * (1 + taxRate) + laborFeeTwd);
    });
  });
  return estimates.length ? Math.min(...estimates) : null;
}

function catalogCaratOptionLabel(value, isChain) {
  if (isChain) return String(value);
  const n = parseFloat(value);
  return Number.isNaN(n) ? String(value) : `${n.toFixed(1)} ct`;
}

const CATALOG_PRICE_BAND_DEFS = [
  { value: 'under30000', label: 'NT$ 30,000 以下' },
  { value: '30000to80000', label: 'NT$ 30,000–80,000' },
  { value: 'over80000', label: 'NT$ 80,000 以上' },
];

function sortCaratValues(values) {
  return [...values].sort((a, b) => {
    const na = parseFloat(a);
    const nb = parseFloat(b);
    if (!Number.isNaN(na) && !Number.isNaN(nb) && na !== nb) return na - nb;
    return String(a).localeCompare(String(b), undefined, { numeric: true });
  });
}

/** Distinct carats/thicknesses a listing offers (variants + weight rows). */
function catalogCaratsForProduct(product) {
  const set = new Set();
  (product?.carats || []).forEach((c) => {
    if (c == null || c === '') return;
    set.add(String(c));
  });
  Object.values(product?.weights || {}).forEach((byCarat) => {
    Object.keys(byCarat || {}).forEach((c) => {
      if (c) set.add(String(c));
    });
  });
  return sortCaratValues([...set]);
}

function collectCategoryCarats(category) {
  const set = new Set();
  productsFor(category).forEach((product) => {
    catalogCaratsForProduct(product).forEach((c) => set.add(c));
  });
  return sortCaratValues([...set]);
}

function collectCategoryMetals(category) {
  const set = new Set();
  productsFor(category).forEach((product) => {
    const golds = productHasAdminVariants(product)
      ? productGolds(category, product)
      : (product.golds || []);
    golds.forEach((g) => set.add(g));
  });
  return sortGolds([...set]);
}

function collectCategoryPriceBands(category) {
  return CATALOG_PRICE_BAND_DEFS.filter((band) =>
    productsFor(category).some((product) => {
      const price = estimatedProductPrice(product);
      return price != null && productMatchesPriceBand(price, band.value);
    }),
  );
}

function productOffersCarat(product, carat) {
  if (!carat) return true;
  const target = String(carat);
  return catalogCaratsForProduct(product).some((c) => c === target);
}

function catalogMetalOptionLabel(gold) {
  const label = tr(`metal_${gold}`);
  return label && label !== `metal_${gold}` ? label : gold.toUpperCase();
}

function setCatalogFilterOptions(id, options, config) {
  if (window.CatalogMultiFilter?.setOptions) {
    window.CatalogMultiFilter.setOptions(id, options, config);
    return;
  }
  const sel = document.getElementById(id);
  if (!sel || sel.tagName !== 'SELECT') return;
  const prev = config.keepSelection ? sel.value : '';
  sel.innerHTML = '';
  const all = document.createElement('option');
  all.value = '';
  if (config.defaultLabelKey) all.dataset.i18n = config.defaultLabelKey;
  all.textContent = tr(config.defaultLabelKey, config.defaultLabelFallback || '');
  sel.appendChild(all);
  (options || []).forEach((o) => {
    const opt = document.createElement('option');
    opt.value = o.value;
    opt.textContent = o.label;
    if (o.i18n) opt.dataset.i18n = o.i18n;
    sel.appendChild(opt);
  });
  sel.value = options.some((o) => o.value === prev) ? prev : '';
  if (typeof config.hidden === 'boolean') sel.hidden = config.hidden;
  if (config.ariaLabelKey) {
    sel.setAttribute('aria-label', tr(config.ariaLabelKey, config.ariaLabelFallback || ''));
  }
}

function caratsForProductGold(product, gold) {
  if (!product) return [];
  const byGold = gold ? product.weights?.[gold] : null;
  let carats;
  if (byGold && Object.keys(byGold).length) {
    carats = Object.keys(byGold).sort((a, b) => {
      const na = parseFloat(a);
      const nb = parseFloat(b);
      if (!Number.isNaN(na) && !Number.isNaN(nb) && na !== nb) return na - nb;
      return String(a).localeCompare(String(b), undefined, { numeric: true });
    });
  } else {
    carats = [...(product.carats || [])];
  }
  // Thickness×length table is chain-only — never filter pendant/ring cts against mm keys.
  if (state.category === 'chain') {
    const configured = chainConfiguredThicknesses(product);
    if (configured.length) {
      const allowed = new Set(configured);
      carats = carats.filter((c) => allowed.has(c));
    }
  }
  return carats;
}

function enforceCaratForGold(product, gold) {
  if (!product || !gold || isDiamondOnlyCategory()) return;
  const carats = listProductCaratOptions(product, gold);
  if (!carats.length) {
    state.carat = null;
    return;
  }
  const current = state.carat != null ? String(state.carat) : '';
  if (!current || !carats.some((c) => String(c) === current)) {
    state.carat = carats[0];
  }
}

function catalogFilterValues(id) {
  return window.CatalogMultiFilter?.getValues(id) || [];
}

function productMatchesPriceBand(price, band) {
  if (band === 'under30000') return price < 30000;
  if (band === '30000to80000') return price >= 30000 && price <= 80000;
  if (band === 'over80000') return price > 80000;
  return false;
}

function populateCatalogMetalFilter({ keepSelection = true, category = state.category } = {}) {
  const metals = category ? collectCategoryMetals(category) : [];
  const options = metals.map((g) => ({
    value: g,
    label: catalogMetalOptionLabel(g),
    i18n: `metal_${g}`,
  }));
  setCatalogFilterOptions('catalog-metal-filter', options, {
    keepSelection,
    defaultLabelKey: 'catalog_all_metals',
    ariaLabelKey: 'catalog_metal_filter_label',
    hidden: category === 'diamond' || !metals.length,
  });
}

function populateCatalogPriceFilter({ keepSelection = true, category = state.category } = {}) {
  const bands = category ? collectCategoryPriceBands(category) : [];
  const options = bands.map((b) => ({
    value: b.value,
    label: b.label,
  }));
  setCatalogFilterOptions('catalog-price-filter', options, {
    keepSelection,
    defaultLabelKey: 'catalog_all_prices',
    ariaLabelKey: 'catalog_price_filter_label',
    hidden: !bands.length,
  });
}

function populateCatalogCaratFilter({ keepSelection = true, category = state.category } = {}) {
  const isChain = category === 'chain';
  const carats = category ? collectCategoryCarats(category) : [];
  const options = carats.map((c) => ({
    value: c,
    label: catalogCaratOptionLabel(c, isChain),
  }));

  setCatalogFilterOptions('catalog-carat-filter', options, {
    keepSelection,
    defaultLabelKey: isChain ? 'catalog_all_thicknesses' : 'catalog_all_carats',
    ariaLabelKey: isChain ? 'catalog_thickness_filter_label' : 'catalog_carat_filter_label',
    hidden: !carats.length,
  });
}

function catalogSearchOrFiltersActive() {
  const query = (document.getElementById('catalog-search-input')?.value || '').trim();
  return !!(query
    || catalogFilterValues('catalog-metal-filter').length
    || catalogFilterValues('catalog-price-filter').length
    || catalogFilterValues('catalog-carat-filter').length);
}

function syncCatalogFilterEmpty(hasProducts) {
  const empty = document.getElementById('catalog-filter-empty');
  if (!empty) return;
  const filtersOn = catalogSearchOrFiltersActive();
  const pagingDone = !!catalogPaging[state.category]?.complete;
  if (hasProducts || (!filtersOn && !pagingDone)) {
    empty.classList.add('hidden');
    return;
  }
  empty.classList.remove('hidden');
  const p = empty.querySelector('p');
  const clearBtn = document.getElementById('catalog-filter-empty-clear');
  if (filtersOn) {
    if (p) {
      p.setAttribute('data-i18n', 'catalog_no_matches');
      p.textContent = tr('catalog_no_matches');
    }
    clearBtn?.classList.remove('hidden');
    return;
  }
  if (p) {
    p.removeAttribute('data-i18n');
    p.textContent = '此品項暫無上架款式。';
  }
  clearBtn?.classList.add('hidden');
}

function populateCatalogFilters({ keepSelection = true, category = state.category } = {}) {
  if (!category) return;
  populateCatalogMetalFilter({ keepSelection, category });
  populateCatalogPriceFilter({ keepSelection, category });
  populateCatalogCaratFilter({ keepSelection, category });
}

function filteredProductsForCurrentCategory() {
  const query = (document.getElementById('catalog-search-input')?.value || '').trim().toLowerCase();
  const metals = catalogFilterValues('catalog-metal-filter');
  const priceBands = catalogFilterValues('catalog-price-filter');
  const carats = catalogFilterValues('catalog-carat-filter');
  return productsFor(state.category).filter(product => {
    const names = `${product.nameZh || ''} ${product.nameEn || ''}`.toLowerCase();
    if (query && !names.includes(query)) return false;
    const golds = product.golds || [];
    if (metals.length && golds.length && !metals.some((m) => golds.includes(m))) return false;
    if (carats.length && !carats.some((c) => productOffersCarat(product, c))) return false;
    if (priceBands.length) {
      const price = estimatedProductPrice(product);
      if (price == null) return false;
      if (!priceBands.some((band) => productMatchesPriceBand(price, band))) return false;
    }
    return true;
  });
}

function renderTypeCards() {
  const grid = document.getElementById("type-grid");
  if (!grid) return;
  if (isDiamondOnlyCategory()) {
    grid.innerHTML = '';
    document.getElementById('catalog-filter-empty')?.classList.add('hidden');
    return;
  }
  grid.innerHTML = "";
  const products = filteredProductsForCurrentCategory();
  products.forEach(product => {
    const styleId = String(product.id);
    const card = document.createElement("button");
    card.type = "button";
    card.className = "type-card";
    card.dataset.type = styleId;
    if (state.type === styleId) card.classList.add("active");

    const media = document.createElement('span');
    media.className = 'type-card__media';
    const candidates = styleGridImageCandidates(product);
    const imgSrc = candidates[0] || '';
    if (imgSrc) {
      const img = document.createElement("img");
      img.src = imgSrc;
      img.alt = productName(product);
      img.loading = "lazy";
      img.decoding = "async";
      window.ShopAssets?.attachImageFallbackChain(img, candidates.slice(1));
      media.appendChild(img);
    } else {
      const ph = document.createElement("span");
      ph.className = "img-placeholder is-missing";
      ph.setAttribute("aria-hidden", "true");
      media.appendChild(ph);
    }
    card.appendChild(media);

    const name = document.createElement("span");
    name.className = "type-name";
    name.textContent = productName(product);

    card.appendChild(name);
    if (product.draft) {
      const badge = document.createElement("span");
      badge.className = "type-draft-badge";
      badge.textContent = "草稿預覽";
      card.appendChild(badge);
    }
    card.addEventListener("click", () => selectType(styleId));
    grid.appendChild(card);
  });
  applyTypeGridLayout(grid, products.length);
  syncCatalogFilterEmpty(products.length > 0);
}

function syncVariantChipActiveStates() {
  const caratSel = document.getElementById('carat-select');
  if (caratSel) caratSel.value = state.carat != null ? String(state.carat) : '';
  document.querySelectorAll('#metal-btn-row .metal-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.gold === state.gold));
  document.querySelectorAll('#color-btn-row .color-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.color === state.color));
  const sel = document.getElementById('ring-size-select');
  if (sel) sel.value = state.ringSize != null ? String(state.ringSize) : '';
}

function updateMetalButtons() {
  const metalStep = document.getElementById('metal-step');
  if (isDiamondOnlyCategory()) {
    metalStep?.classList.add('hidden');
    state.gold = null;
    state.color = null;
    const row = document.getElementById('metal-btn-row');
    if (row) row.innerHTML = '';
    updateColorStep();
    return;
  }
  metalStep?.classList.remove('hidden');
  const product = getSelectedProduct();
  const golds = productGolds(state.category, product);
  renderMetalButtons('metal-btn-row', golds, state.gold, selectMetal);
  if (state.gold && product && !golds.includes(state.gold)) {
    state.gold = null;
    state.color = null;
  }
  updateColorStep();
}

function enforceMetalColor(gold, color, product) {
  if (!gold) return null;
  if (isColorLockedChainProduct(product)) {
    return product.defaultColor || materialColor(gold);
  }
  const colors = availableColorsForGold(gold, product);
  if (!colors.length) return materialColor(gold);
  if (colors.length === 1) return colors[0];
  return colors.includes(color) ? color : colors[0];
}

function updateColorStep(goldOverride) {
  const product = getSelectedProduct();
  const step = document.getElementById('color-step');
  const row = document.getElementById('color-btn-row');
  if (!step) return;
  const gold = goldOverride ?? state.gold;
  const show = gold && needsColorSelection(gold, product);
  const collapse = !show && (isDiamondOnlyCategory() || isColorLockedChainProduct(product));
  updateColorStepLabel('color-step-label', gold);
  step.classList.remove('hidden');
  step.classList.toggle('hidden-collapse', collapse);
  step.classList.toggle('is-placeholder', !show && !collapse);
  step.setAttribute('aria-hidden', show ? 'false' : 'true');
  if (!show) {
    if (gold) state.color = enforceMetalColor(gold, state.color, product);
    if (row) row.innerHTML = '';
    return;
  }
  state.color = enforceMetalColor(gold, state.color, product);
  renderColorButtons('color-btn-row', gold, product, state.color, selectColor);
}

/**
 * Admin/catalog carats for a product+gold (unfiltered).
 * White dropdown + fancy-color gating use this full list.
 */
function listAdminProductCaratOptions(product, gold) {
  if (!product) return [];
  const fromGold = gold ? caratsForProductGold(product, gold) : null;
  const raw = (fromGold && fromGold.length)
    ? fromGold
    : [...(product.carats || [])];
  return raw.map(String).filter(Boolean);
}

/**
 * Shop carat dropdown options.
 * White: all admin carats. Fancy (黃/藍/粉): intersect admin list with ≥ fancyMinCarat (0.3).
 */
function listProductCaratOptions(product, gold) {
  const options = listAdminProductCaratOptions(product, gold);
  if (state.category === 'chain' || state.diamondKind !== 'fancy') return options;
  const minCarat = fancyMinCaratValue();
  return options.filter((c) => {
    const n = parseFloat(c);
    return !Number.isNaN(n) && n >= minCarat;
  });
}

function productConfiguredCarats() {
  return listAdminProductCaratOptions(getSelectedProduct(), state.gold);
}

/** @deprecated Prefer listProductCaratOptions fancy filter. Always false. */
function isCaratHiddenForShop(_carat) {
  return false;
}

const FANCY_DIAMOND_COLOR_IDS = ['yellow', 'blue', 'pink'];

function fancyMinCaratValue() {
  const n = Number(diamondOptions.fancyMinCarat || 0.3);
  return Number.isNaN(n) ? 0.3 : n;
}

/** Non-round cuts need ≥ this carat (default 0.3 / 30 points). Matches configurator.js. */
function nonRoundShapeMinCaratValue() {
  const n = Number(diamondOptions.nonRoundShapeMinCarat || 0.3);
  return Number.isNaN(n) ? 0.3 : n;
}

function caratAllowsNonRoundShape(carat = state.carat) {
  if (carat == null || carat === '') return false;
  const n = parseFloat(carat);
  return !Number.isNaN(n) && n >= nonRoundShapeMinCaratValue();
}

/** True when admin carats include at least one ≥ fancy min (0.3). */
function productOffersFancyMinCaratOrAbove() {
  const minCarat = fancyMinCaratValue();
  return productConfiguredCarats().some((c) => {
    const n = parseFloat(c);
    return !Number.isNaN(n) && n >= minCarat;
  });
}

/** Collect yellow/blue/pink from slot keys (images map or lite `colors` list). */
function addFancyColorsFromSlotKeys(keys, found) {
  if (!keys) return;
  const list = Array.isArray(keys) ? keys : Object.keys(keys);
  list.forEach((key) => {
    const parsed = window.ShopAssets?.parseImageSlotKey?.(key);
    if (parsed && FANCY_DIAMOND_COLOR_IDS.includes(parsed.diamond)) {
      found.add(parsed.diamond);
      return;
    }
    const parts = String(key).toLowerCase().split('-');
    if (parts.length >= 2 && FANCY_DIAMOND_COLOR_IDS.includes(parts[1])) {
      found.add(parts[1]);
    }
  });
}

/** Memorial / loose diamond series (static catalog, not letter SKUs). */
function isMemorialDiamondProduct(product) {
  const id = String(product?.id || '');
  const key = String(product?.styleKey || '');
  return id.startsWith('diamond-') || key.startsWith('diamond-');
}

/**
 * Fancy colors with bundled matrix PNGs under public/images/diamonds/matrix/.
 * Memorial preview uses these — not shop-product letter SKUs / lifestyle heroes.
 */
function matrixFancyDiamondColors() {
  return FANCY_DIAMOND_COLOR_IDS.slice();
}

/** Fancy diamond colors from catalog uploads and/or bundled letter-SKU stock PNGs. */
function designedFancyDiamondColors(product) {
  const found = new Set();
  // Memorial diamonds: lifestyle heroes are white-only; unlock matrix yellow/blue/pink.
  if (isMemorialDiamondProduct(product) || isDiamondOnlyCategory()) {
    matrixFancyDiamondColors().forEach((c) => found.add(c));
    return FANCY_DIAMOND_COLOR_IDS.filter((c) => found.has(c));
  }
  const images = product?.images;
  if (images && typeof images === 'object' && !Array.isArray(images)) {
    Object.keys(images).forEach((key) => {
      const urls = images[key];
      if (!urls || (Array.isArray(urls) && !urls.length)) return;
      addFancyColorsFromSlotKeys([key], found);
    });
  }
  // Lite catalog omits `images` but keeps slot keys in `colors`.
  addFancyColorsFromSlotKeys(product?.colors, found);
  const styleKey = productAssetId(product);
  const stock = window.ShopAssets?.stockFancyDiamondColors?.(styleKey) || [];
  stock.forEach((c) => {
    if (FANCY_DIAMOND_COLOR_IDS.includes(c)) found.add(c);
  });
  return FANCY_DIAMOND_COLOR_IDS.filter((c) => found.has(c));
}

/**
 * Show 黃鑽/藍鑽/粉鑽 only when BOTH:
 *   1) product has at least one admin carat ≥ fancyMinCarat (0.3), AND
 *   2) that color has a catalog image slot OR letter-SKU stock PNG
 *      (memorial: bundled matrix PNG under diamonds/matrix/).
 * Do not unlock all fancy colors from carat alone. White always separate.
 * Bracelet/chain: stock remaps fancy→white — no stock fancy offered.
 */
function isFancyDiamondColorOffered(colorId) {
  if (!FANCY_DIAMOND_COLOR_IDS.includes(colorId)) return false;
  if (!productOffersFancyMinCaratOrAbove()) return false;
  return designedFancyDiamondColors(getSelectedProduct()).includes(colorId);
}

function offeredFancyDiamondColorIds() {
  return FANCY_DIAMOND_COLOR_IDS.filter(isFancyDiamondColorOffered);
}

function syncFancyMinCaratNotice() {
  const notice = document.getElementById('diamond-fancy-min-carat-notice');
  if (!notice) return;
  // Product-level gate only: show whenever fancy UI is offered.
  // Do not hide on 白鑽 selection or when selected carat ≥ min.
  const show = productOffersFancyMinCaratOrAbove()
    && designedFancyDiamondColors(getSelectedProduct()).length > 0;
  notice.classList.toggle('hidden', !show);
}

function ensureOfferedDiamondColorSelection() {
  const active = selectedDiamondColorId();
  if (active && active !== 'white' && !isFancyDiamondColorOffered(active)) {
    state.diamondKind = 'white';
    state.fancyColor = null;
  }
}

function ensureChainCaratDefault() {
  if (state.category !== 'chain') return;
  const product = getSelectedProduct();
  const carats = listProductCaratOptions(product, state.gold);
  if (!carats.length) return;
  const current = state.carat != null ? String(state.carat) : '';
  if (!current || !carats.includes(current)) {
    state.carat = null;
  }
}

/** Default to smallest/first admin carat when unset or no longer offered. */
function ensureProductCaratDefault(validCarats) {
  const carats = Array.isArray(validCarats) ? validCarats.map(String) : [];
  if (!carats.length) {
    state.carat = null;
    return;
  }
  const current = state.carat != null ? String(state.carat) : '';
  if (!current || !carats.includes(current)) {
    state.carat = carats[0];
  }
}

function updateCaratButtons() {
  const product = getSelectedProduct();
  const validCarats = listProductCaratOptions(product, state.gold);
  if (state.gold && product) enforceCaratForGold(product, state.gold);
  else if (product) ensureProductCaratDefault(validCarats);
  // Re-read after enforce/default may have changed state.carat.
  const options = listProductCaratOptions(product, state.gold);
  ensureProductCaratDefault(options);
  const isChain = state.category === 'chain';
  document.getElementById('carat-step')?.classList.remove('hidden');
  const label = document.querySelector('#carat-step .variant-label');
  if (label) label.textContent = tr(isChain ? 'step_chain_thickness' : 'step_carat');
  if (isChain) {
    ensureChainCaratDefault();
  }
  const sel = document.getElementById('carat-select');
  if (!sel) return;
  sel.innerHTML = '';
  const placeholder = document.createElement('option');
  placeholder.value = '';
  if (isChain) {
    placeholder.textContent = '選擇厚度';
  } else {
    const ph = tr('carat_placeholder');
    placeholder.textContent = (ph && ph !== 'carat_placeholder') ? ph : '選擇克拉';
  }
  sel.appendChild(placeholder);
  // List admin carats; fancy below min stays visible but grey-disabled (selectable = options).
  const adminOptions = isChain
    ? options
    : listAdminProductCaratOptions(product, state.gold);
  const displayOptions = adminOptions.length ? adminOptions : options;
  displayOptions.forEach((v) => {
    const n = parseFloat(v);
    const opt = document.createElement('option');
    opt.value = String(v);
    opt.textContent = isChain ? String(v) : (Number.isNaN(n) ? String(v) : `${n.toFixed(1)} ct`);
    const blocked = !isChain
      && state.diamondKind === 'fancy'
      && !options.includes(String(v));
    if (blocked) {
      opt.disabled = true;
      opt.title = tr('diamond_fancy_min_carat');
      opt.dataset.blockedReason = 'diamond_fancy_min_carat';
    }
    sel.appendChild(opt);
  });
  const selected = state.carat != null ? String(state.carat) : '';
  sel.value = selected && options.includes(selected) ? selected : '';
  syncShopDropdown(sel);
  syncFancyMinCaratNotice();
  updateDiamondSteps();
}

// Expose for regression tests (Node / browser console).
window.listAdminProductCaratOptions = listAdminProductCaratOptions;
window.listProductCaratOptions = listProductCaratOptions;
window.isCaratHiddenForShop = isCaratHiddenForShop;
window.productOffersFancyMinCaratOrAbove = productOffersFancyMinCaratOrAbove;
window.isFancyDiamondColorOffered = isFancyDiamondColorOffered;
window.offeredFancyDiamondColorIds = offeredFancyDiamondColorIds;

function resetDiamondOptions() {
  state.diamondKind = 'white';
  state.fancyColor = null;
  state.stoneCount = null;
  state.diamondShape = 'round';
}

function diamondMetaLabel(item) {
  if (!item) return '';
  return shopLang() === 'en' ? (item.labelEn || item.labelZh) : item.labelZh;
}

function diamondAssetUrl(relativePath) {
  if (!relativePath) return '';
  return `/static/images/${relativePath}?v=23`;
}

function diamondMatrixImagePath(shapeId, colorId) {
  const shape = shapeId || 'round';
  const color = colorId || 'white';
  return `diamonds/matrix/${shape}-${color}.png`;
}

function diamondMatrixImageUrl(shapeId, colorId) {
  return diamondAssetUrl(diamondMatrixImagePath(shapeId, colorId));
}

/** Prefer admin shape image on selected color product; else bundled matrix PNG. */
function memorialDiamondShapeImageUrl(shapeId, colorId) {
  const shape = shapeId || 'round';
  const product = getSelectedProduct();
  if (isMemorialDiamondProduct(product) || isDiamondOnlyCategory()) {
    const urls = product?.images?.[shape];
    const custom = Array.isArray(urls) ? urls.find(Boolean) : null;
    if (custom && isUsableCatalogImageUrl(custom)) {
      return custom.startsWith('/') || /^https?:/i.test(custom)
        ? custom
        : diamondAssetUrl(custom);
    }
  }
  return diamondMatrixImageUrl(shape, colorId || selectedDiamondColorId() || 'white');
}

function nonRoundMatrixShapes() {
  const shapes = diamondOptions.matrixShapes?.length
    ? diamondOptions.matrixShapes
    : [
      { id: 'marquise', labelZh: '馬眼型', labelEn: 'Marquise' },
      { id: 'oval', labelZh: '橢圓形', labelEn: 'Oval' },
      { id: 'princess', labelZh: '公主方', labelEn: 'Princess' },
      { id: 'trilliant', labelZh: '三角形', labelEn: 'Trilliant' },
      { id: 'emerald', labelZh: '祖母綠形', labelEn: 'Emerald' },
      { id: 'heart', labelZh: '心形', labelEn: 'Heart' },
      { id: 'radiant', labelZh: '雷地恩形', labelEn: 'Radiant' },
      { id: 'pear', labelZh: '梨形', labelEn: 'Pear' },
      { id: 'cushion', labelZh: '枕形', labelEn: 'Cushion' },
    ];
  return shapes.filter((s) => s.id !== 'round');
}

function isNonRoundShape(shapeId = state.diamondShape) {
  return !!shapeId && shapeId !== 'round';
}

function isDiamondShapeOtherPending(shapeId = state.diamondShape) {
  return shapeId === 'other';
}

function resolvedDiamondShape(shapeId = state.diamondShape) {
  const id = shapeId || 'round';
  return id === 'other' ? 'round' : id;
}

function isDiamondShapeChipActive(chipId) {
  const current = state.diamondShape || 'round';
  if (chipId === 'round') return current === 'round';
  if (chipId === 'other') return isNonRoundShape(current);
  return current === chipId;
}

function diamondShapeDisplayMeta(shapeId = state.diamondShape) {
  if (!shapeId || shapeId === 'round' || shapeId === 'other') return null;
  return nonRoundMatrixShapes().find((s) => s.id === shapeId)
    || diamondShapeOptions().find((s) => s.id === shapeId)
    || { id: shapeId, labelZh: shapeId, labelEn: shapeId };
}

function diamondShapeOptions() {
  if (isDiamondOnlyCategory()) {
    const matrix = diamondOptions.matrixShapes?.length
      ? diamondOptions.matrixShapes
      : [
        { id: 'round', labelZh: '圓形', labelEn: 'Round' },
        { id: 'marquise', labelZh: '馬眼型', labelEn: 'Marquise' },
        { id: 'oval', labelZh: '橢圓形', labelEn: 'Oval' },
        { id: 'princess', labelZh: '公主方', labelEn: 'Princess' },
        { id: 'trilliant', labelZh: '三角形', labelEn: 'Trilliant' },
        { id: 'emerald', labelZh: '祖母綠形', labelEn: 'Emerald' },
        { id: 'heart', labelZh: '心形', labelEn: 'Heart' },
        { id: 'radiant', labelZh: '雷地恩形', labelEn: 'Radiant' },
        { id: 'pear', labelZh: '梨形', labelEn: 'Pear' },
        { id: 'cushion', labelZh: '枕形', labelEn: 'Cushion' },
      ];
    // Never-available non-round: omit from matrix picker (not greyed).
    return productAllowsFancyShapes()
      ? matrix
      : matrix.filter((s) => s.id === 'round');
  }
  if (diamondOptions.shapes?.length) {
    return productAllowsFancyShapes()
      ? diamondOptions.shapes
      : diamondOptions.shapes.filter((s) => s.id === 'round');
  }
  if (!productAllowsFancyShapes()) {
    return [{ id: 'round', labelZh: '圓形明亮式', labelEn: 'Round' }];
  }
  return [
    { id: 'round', labelZh: '圓形明亮式', labelEn: 'Round' },
    { id: 'other', labelZh: '其它形狀', labelEn: 'Other (+10%)' },
  ];
}

function usesAutoStoneCount(category = state.category) {
  const cats = diamondOptions.stoneCountCategories || [];
  return cats.includes(category);
}

function usesStoneCountPicker(category = state.category) {
  return category === 'diamond';
}

function usesEarringQuantity(category = state.category) {
  return category === 'earring';
}

function earringQuantityMin() {
  const n = Number(diamondOptions.earringQuantityMin);
  return Number.isNaN(n) ? 1 : Math.max(1, n);
}

function earringQuantityMax() {
  const n = Number(diamondOptions.earringQuantityMax);
  return Number.isNaN(n) ? 2 : Math.max(earringQuantityMin(), n);
}

function normalizeEarringQuantity(raw) {
  const n = parseInt(raw, 10);
  if (Number.isNaN(n)) return earringQuantityMin();
  return Math.min(earringQuantityMax(), Math.max(earringQuantityMin(), n));
}

function defaultStoneCountForCategory(category = state.category) {
  if (category === 'diamond') return 1;
  return diamondOptions.defaultStoneCountByCategory?.[category] || 2;
}

function stoneCountBadgeText() {
  if (usesEarringQuantity()) {
    return tr('stone_count_badge').replace('{n}', String(normalizeEarringQuantity(state.quantity)));
  }
  if (usesStoneCountPicker() && state.stoneCount && state.stoneCount > 1) {
    return tr('stone_count_badge').replace('{n}', String(state.stoneCount));
  }
  if (!usesAutoStoneCount() || !state.stoneCount) return null;
  return tr('stone_count_badge').replace('{n}', String(state.stoneCount));
}

function ensureStoneCountDefault() {
  if (usesEarringQuantity()) {
    state.quantity = normalizeEarringQuantity(state.quantity || 1);
    state.stoneCount = null;
    return;
  }
  if (usesStoneCountPicker()) {
    if (!state.stoneCount) state.stoneCount = 1;
    return;
  }
  if (!usesAutoStoneCount()) {
    state.stoneCount = null;
    return;
  }
  state.stoneCount = defaultStoneCountForCategory();
}

/** Built-in swatch defs when /api/prices + empty diamondOptions leave fancyColors=[]. */
const FALLBACK_DIAMOND_COLOR_DEFS = [
  { id: 'white', kind: 'white', labelZh: '白鑽', labelEn: 'White', swatch: '#e8e8e8', image: 'diamonds/colors/white.png' },
  { id: 'yellow', kind: 'fancy', labelZh: '黃鑽', labelEn: 'Yellow', swatch: '#e6c200', image: 'diamonds/colors/yellow.png' },
  { id: 'blue', kind: 'fancy', labelZh: '藍鑽', labelEn: 'Blue', swatch: '#7ec8e3', image: 'diamonds/colors/blue.png' },
  { id: 'pink', kind: 'fancy', labelZh: '粉鑽', labelEn: 'Pink', swatch: '#f4a6c8', image: 'diamonds/colors/pink.png' },
];

/** All diamond color defs (white + fancy), including currently unselectable. */
function allDiamondColorDefs() {
  ensureDiamondOptionTables();
  let all = diamondOptions.diamondColors?.length
    ? diamondOptions.diamondColors
    : [
      FALLBACK_DIAMOND_COLOR_DEFS[0],
      ...(diamondOptions.fancyColors || []),
    ];
  // API mode historically left fancyColors empty — merge fallbacks for offered ids.
  const byId = new Map();
  all.forEach((c) => { if (c?.id) byId.set(c.id, c); });
  FALLBACK_DIAMOND_COLOR_DEFS.forEach((def) => {
    if (!byId.has(def.id)) byId.set(def.id, def);
  });
  return FALLBACK_DIAMOND_COLOR_DEFS.map((def) => byId.get(def.id)).filter(Boolean);
}

/** Selectable diamond colors only (fancy gated by carat + designed image). */
function diamondColorOptions() {
  return allDiamondColorDefs().filter((color) => {
    if (!color || color.id === 'white' || color.kind === 'white') return true;
    return isFancyDiamondColorOffered(color.id);
  });
}

function selectedDiamondColorId() {
  return state.diamondKind === 'white' ? 'white' : state.fancyColor;
}

function updateCarouselNav({ carouselId, prevId, nextId }) {
  const carousel = document.getElementById(carouselId);
  const prev = document.getElementById(prevId);
  const next = document.getElementById(nextId);
  if (!carousel || !prev || !next) return;

  const scrollable = carousel.scrollWidth > carousel.clientWidth + 1;
  prev.hidden = !scrollable;
  next.hidden = !scrollable;
  carousel.closest('.diamond-carousel-wrap')?.classList.toggle('diamond-carousel-wrap--no-nav', !scrollable);
}

const DIAMOND_CAROUSELS = [
  { carouselId: 'fancy-color-carousel', prevId: 'fancy-color-prev', nextId: 'fancy-color-next' },
];

function updateAllDiamondCarouselNav() {
  DIAMOND_CAROUSELS.forEach(updateCarouselNav);
}

function scheduleDiamondCarouselNavUpdate() {
  requestAnimationFrame(() => requestAnimationFrame(updateAllDiamondCarouselNav));
}

function renderDiamondColorCarousel() {
  const carousel = document.getElementById('fancy-color-carousel');
  if (!carousel) return;
  ensureOfferedDiamondColorSelection();
  carousel.innerHTML = '';
  const activeId = selectedDiamondColorId();
  // Never-available fancy (no ≥min carat and/or no designed image): omit.
  // Temp carat gate lives on the carat dropdown, not greyed color chips.
  diamondColorOptions().forEach((color) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'diamond-carousel-item fancy-color-item';
    btn.dataset.color = color.id;
    btn.classList.toggle('active', activeId === color.id);
    const icon = document.createElement('span');
    icon.className = 'gem-icon';
    // Prefer the memorial color product's admin-editable 圓形 image (same slot
    // as the calculator preview) over the bundled static swatch PNG.
    const colorProduct = memorialDiamondProductForColor(color.id);
    const roundUrls = colorProduct?.images?.round;
    const adminIcon = (Array.isArray(roundUrls) ? roundUrls.find(Boolean) : null)
      || colorProduct?.thumbUrl
      || '';
    const usableAdminIcon = adminIcon && isUsableCatalogImageUrl(adminIcon) ? adminIcon : '';
    const imagePath = usableAdminIcon || color.image || DIAMOND_WHITE_PREVIEW_PATH;
    if (imagePath) {
      const img = document.createElement('img');
      img.src = usableAdminIcon && (usableAdminIcon.startsWith('/') || /^https?:/i.test(usableAdminIcon))
        ? usableAdminIcon
        : diamondAssetUrl(imagePath);
      img.alt = diamondMetaLabel(color);
      img.loading = 'lazy';
      img.decoding = 'async';
      icon.appendChild(img);
    } else {
      icon.style.background = color.swatch || '#eee';
    }
    const label = document.createElement('span');
    label.className = 'gem-label';
    label.textContent = diamondMetaLabel(color);
    btn.appendChild(icon);
    btn.appendChild(label);
    btn.addEventListener('click', () => selectDiamondColor(color.id));
    carousel.appendChild(btn);
  });
  scheduleDiamondCarouselNavUpdate();
}


function scrollCarousel(carouselId, direction) {
  const el = document.getElementById(carouselId);
  if (!el) return;
  el.scrollBy({ left: direction * 120, behavior: 'smooth' });
}

function updateDiamondSteps() {
  const isChain = state.category === 'chain';
  const isDiamond = isDiamondOnlyCategory();
  const fancyStep = document.getElementById('fancy-diamond-step');
  const shapeStep = document.getElementById('diamond-shape-step');
  const stoneStep = document.getElementById('stone-count-step');
  const minCaratNotice = document.getElementById('diamond-shape-min-carat-notice');
  fancyStep?.classList.toggle('hidden', isChain);
  shapeStep?.classList.toggle('hidden', isChain);
  stoneStep?.classList.toggle('hidden', !isDiamond);
  if (isChain) {
    resetDiamondOptions();
    updateEarringQuantityStep();
    return;
  }
  enforceRoundOnlyShape();
  minCaratNotice?.classList.toggle('hidden', isChain || !productAllowsFancyShapes());
  syncFancyMinCaratNotice();
  renderDiamondColorCarousel();
  renderDiamondShapeButtons();
  renderStoneCountButtons();
  ensureStoneCountDefault();
  updateEarringQuantityStep();
  updateGirdlePreview();
}

function renderDiamondShapeButtons() {
  const row = document.getElementById('diamond-shape-row');
  if (!row) return;
  const allowsFancy = productAllowsFancyShapes();
  const shapes = diamondShapeOptions();
  const useMatrix = isDiamondOnlyCategory();
  // Diamond-only: reuse diamond-shape-picker. Jewelry keeps chips + other picker.
  row.classList.remove('variant-chips--matrix-shapes');
  row.classList.toggle('diamond-shape-row--select', useMatrix);
  row.innerHTML = '';
  row.hidden = useMatrix;

  if (useMatrix) {
    syncDiamondShapeOtherDropdown();
    return;
  }

  // Never-available (product round-only): omit non-round chips entirely.
  // Temp-blocked (carat < min): keep chip, grey-disabled — may unlock later.
  shapes.forEach((shape) => {
    const isRound = shape.id === 'round';
    if (!isRound && !allowsFancy) return;
    const caratLocked = !isRound && !caratAllowsNonRoundShape();
    const reasonKey = caratLocked ? 'diamond_shape_min_carat_blocked' : undefined;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.dataset.shape = shape.id;
    const isActive = !caratLocked && isDiamondShapeChipActive(shape.id);
    btn.className = `variant-chip diamond-shape-btn${isActive ? ' active' : ''}`;
    btn.textContent = diamondMetaLabel(shape);
    if (shape.id === 'round') {
      btn.textContent = shopLang() === 'en' ? 'Round Brilliant' : '圓形明亮式';
    } else if (shape.id === 'other') {
      btn.textContent = shopLang() === 'en' ? 'Other (+10%)' : '其它形狀 +10%';
    }
    setShopOptionDisabled(btn, caratLocked, {
      title: reasonKey ? tr(reasonKey) : undefined,
      reasonKey,
    });
    btn.addEventListener('click', () => {
      if (caratLocked || shopOptionIsDisabled(btn)) {
        toastShopBlocked(reasonKey || 'diamond_shape_min_carat_blocked');
        return;
      }
      selectDiamondShape(shape.id);
    });
    row.appendChild(btn);
  });
  syncDiamondShapeOtherDropdown();
}

let diamondShapePickerBound = false;

function diamondShapePickerOptions() {
  return Array.from(document.querySelectorAll(
    '#diamond-shape-other-listbox .diamond-shape-picker__option'
  ));
}

function setDiamondShapePickerOpen(open, { focus = null, restoreFocus = false } = {}) {
  const trigger = document.getElementById('diamond-shape-other-trigger');
  const popover = document.getElementById('diamond-shape-other-popover');
  if (!trigger || !popover) return;

  const shouldOpen = !!open;
  trigger.setAttribute('aria-expanded', String(shouldOpen));
  popover.hidden = !shouldOpen;

  if (!shouldOpen) {
    if (restoreFocus) trigger.focus();
    return;
  }

  requestAnimationFrame(() => {
    const options = diamondShapePickerOptions();
    if (!options.length) return;
    const enabled = options.filter((option) => !diamondShapePickerOptionDisabled(option));
    const pool = enabled.length ? enabled : options;
    let target = pool.find((option) => option.getAttribute('aria-selected') === 'true');
    if (focus === 'first') target = pool[0];
    if (focus === 'last') target = pool[pool.length - 1];
    if (focus === 'selected' && !target) target = pool[0];
    target?.scrollIntoView({ block: 'nearest' });
    if (focus) target?.focus();
  });
}

function diamondShapePickerOptionDisabled(option) {
  return shopOptionIsDisabled(option);
}

function moveDiamondShapePickerFocus(direction) {
  const options = diamondShapePickerOptions();
  if (!options.length) return;
  const current = options.indexOf(document.activeElement);
  const len = options.length;
  for (let step = 1; step <= len; step += 1) {
    const idx = current < 0
      ? (direction > 0 ? step - 1 : len - step)
      : (current + direction * step + len * step) % len;
    const target = options[idx];
    if (diamondShapePickerOptionDisabled(target)) continue;
    target.focus();
    target.scrollIntoView({ block: 'nearest' });
    return;
  }
}

function diamondShapePickerMeta(shape) {
  const primary = diamondMetaLabel(shape);
  const alternate = shopLang() === 'en' ? shape.labelZh : shape.labelEn;
  const parts = [alternate && alternate !== primary ? alternate : ''];
  if (shape?.id && shape.id !== 'round') {
    const rawSurcharge = Number(diamondOptions.nonRoundShapeSurcharge ?? 0.10);
    const surcharge = Math.round((rawSurcharge <= 1 ? rawSurcharge * 100 : rawSurcharge) * 100) / 100;
    parts.push(`+${surcharge}%`);
  }
  return parts.filter(Boolean).join(' · ');
}

function bindDiamondShapeOtherPicker() {
  if (diamondShapePickerBound) return;
  const picker = document.getElementById('diamond-shape-other-picker');
  const trigger = document.getElementById('diamond-shape-other-trigger');
  const popover = document.getElementById('diamond-shape-other-popover');
  const optionsRoot = document.getElementById('diamond-shape-other-listbox');
  if (!picker || !trigger || !popover || !optionsRoot) return;
  diamondShapePickerBound = true;

  trigger.addEventListener('click', () => {
    const isOpen = trigger.getAttribute('aria-expanded') === 'true';
    setDiamondShapePickerOpen(!isOpen);
  });

  trigger.addEventListener('keydown', (event) => {
    const isOpen = trigger.getAttribute('aria-expanded') === 'true';
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      setDiamondShapePickerOpen(true, { focus: event.key === 'ArrowDown' ? 'selected' : 'last' });
    } else if ((event.key === 'Enter' || event.key === ' ') && !isOpen) {
      event.preventDefault();
      setDiamondShapePickerOpen(true, { focus: 'selected' });
    } else if (event.key === 'Escape' && isOpen) {
      event.preventDefault();
      setDiamondShapePickerOpen(false);
    } else if (event.key === 'Tab' && isOpen) {
      setDiamondShapePickerOpen(false);
    }
  });

  optionsRoot.addEventListener('click', (event) => {
    const option = event.target.closest('.diamond-shape-picker__option');
    if (!option || !optionsRoot.contains(option)) return;
    if (diamondShapePickerOptionDisabled(option)) {
      toastShopBlocked(option.dataset.blockedReason || 'diamond_shape_min_carat_blocked');
      document.getElementById('diamond-shape-min-carat-notice')?.classList.remove('hidden');
      return;
    }
    const shapeId = option.dataset.shape;
    if (!shapeId) return;
    setDiamondShapePickerOpen(false);
    selectDiamondShape(shapeId);
    trigger.focus();
  });

  optionsRoot.addEventListener('keydown', (event) => {
    const option = event.target.closest('.diamond-shape-picker__option');
    if (!option) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      moveDiamondShapePickerFocus(1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      moveDiamondShapePickerFocus(-1);
    } else if (event.key === 'Home') {
      event.preventDefault();
      diamondShapePickerOptions()[0]?.focus();
    } else if (event.key === 'End') {
      event.preventDefault();
      const options = diamondShapePickerOptions();
      options[options.length - 1]?.focus();
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (!diamondShapePickerOptionDisabled(option)) option.click();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      setDiamondShapePickerOpen(false, { restoreFocus: true });
    } else if (event.key === 'Tab') {
      setDiamondShapePickerOpen(false);
    }
  });

  document.addEventListener('pointerdown', (event) => {
    if (!picker.contains(event.target)) setDiamondShapePickerOpen(false);
  });
}

function syncDiamondShapeOtherDropdown() {
  bindDiamondShapeOtherPicker();
  const wrap = document.getElementById('diamond-shape-other-wrap');
  const trigger = document.getElementById('diamond-shape-other-trigger');
  const image = document.getElementById('diamond-shape-other-image');
  const value = document.getElementById('diamond-shape-other-value');
  const meta = document.getElementById('diamond-shape-other-meta');
  const optionsRoot = document.getElementById('diamond-shape-other-listbox');
  if (!wrap || !trigger || !image || !value || !meta || !optionsRoot) return;

  const useMatrix = isDiamondOnlyCategory();
  const options = useMatrix ? diamondShapeOptions() : nonRoundMatrixShapes();
  const avatar = trigger.querySelector('.diamond-shape-picker__avatar');
  let selected = options.find((shape) => shape.id === state.diamondShape);
  if (!useMatrix && isNonRoundShape() && state.diamondShape !== 'other' && !selected) {
    state.diamondShape = 'other';
    selected = null;
  }
  if (useMatrix && !selected) {
    selected = options.find((shape) => shape.id === 'round') || options[0] || null;
    if (selected && state.diamondShape !== selected.id) state.diamondShape = selected.id;
  }
  const isPending = !useMatrix && isDiamondShapeOtherPending();
  if (isPending) selected = null;
  const show = useMatrix || isPending || !!selected;
  wrap.hidden = !show;
  wrap.classList.toggle('diamond-shape-other-wrap--matrix', useMatrix);
  if (!show) {
    setDiamondShapePickerOpen(false);
    return;
  }

  if (isPending) {
    if (avatar) avatar.hidden = true;
    image.removeAttribute('src');
    image.alt = '';
    value.textContent = tr('step_diamond_shape_other');
    meta.textContent = '';
    trigger.classList.add('diamond-shape-picker__trigger--placeholder');
  } else if (selected) {
    if (avatar) avatar.hidden = false;
    image.src = memorialDiamondShapeImageUrl(selected.id, selectedDiamondColorId());
    image.alt = '';
    value.textContent = diamondMetaLabel(selected);
    meta.textContent = diamondShapePickerMeta(selected);
    trigger.classList.remove('diamond-shape-picker__trigger--placeholder');
  }

  optionsRoot.innerHTML = '';
  const lockNonRound = !caratAllowsNonRoundShape();
  options.forEach((shape) => {
    const isSelected = !!selected && shape.id === selected.id;
    const locked = lockNonRound && isNonRoundShape(shape.id);
    const option = document.createElement('button');
    option.type = 'button';
    option.id = `diamond-shape-option-${shape.id}`;
    option.className = 'diamond-shape-picker__option';
    option.dataset.shape = shape.id;
    option.setAttribute('role', 'option');
    option.setAttribute('aria-selected', String(isSelected && !locked));
    option.tabIndex = -1;
    setShopOptionDisabled(option, locked, {
      title: locked ? tr('diamond_shape_min_carat_blocked') : undefined,
      reasonKey: locked ? 'diamond_shape_min_carat_blocked' : undefined,
    });

    const optionAvatar = document.createElement('span');
    optionAvatar.className = 'diamond-shape-picker__avatar';
    optionAvatar.setAttribute('aria-hidden', 'true');
    const avatarImage = document.createElement('img');
    avatarImage.src = memorialDiamondShapeImageUrl(shape.id, selectedDiamondColorId());
    avatarImage.alt = '';
    avatarImage.loading = 'lazy';
    avatarImage.decoding = 'async';
    optionAvatar.appendChild(avatarImage);

    const text = document.createElement('span');
    text.className = 'diamond-shape-picker__text';
    const name = document.createElement('span');
    name.className = 'diamond-shape-picker__value';
    name.textContent = diamondMetaLabel(shape);
    const detail = document.createElement('span');
    detail.className = 'diamond-shape-picker__meta';
    detail.textContent = locked
      ? tr('diamond_shape_min_carat_blocked')
      : diamondShapePickerMeta(shape);
    text.appendChild(name);
    text.appendChild(detail);

    const check = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    check.classList.add('diamond-shape-picker__check');
    check.setAttribute('viewBox', '0 0 24 24');
    check.setAttribute('width', '16');
    check.setAttribute('height', '16');
    check.setAttribute('fill', 'none');
    check.setAttribute('stroke', 'currentColor');
    check.setAttribute('stroke-width', '2');
    check.setAttribute('stroke-linecap', 'round');
    check.setAttribute('stroke-linejoin', 'round');
    check.setAttribute('aria-hidden', 'true');
    const checkPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    checkPath.setAttribute('d', 'm20 6-11 11-5-5');
    check.appendChild(checkPath);

    option.appendChild(optionAvatar);
    option.appendChild(text);
    option.appendChild(check);
    optionsRoot.appendChild(option);
  });
}

function selectDiamondShape(shapeId) {
  const nextId = shapeId || 'round';
  if (!productAllowsFancyShapes() && isNonRoundShape(nextId)) {
    toastShopBlocked('diamond_shape_round_only');
    return;
  }
  // Block non-round /「其它形狀」below nonRoundShapeMinCarat (0.3) for all products.
  if (isNonRoundShape(nextId) && !caratAllowsNonRoundShape()) {
    toastShopBlocked('diamond_shape_min_carat_blocked');
    document.getElementById('diamond-shape-min-carat-notice')?.classList.remove('hidden');
    return;
  }
  if (nextId === 'other') {
    if (state.diamondShape === 'round') state.diamondShape = 'other';
  } else {
    state.diamondShape = nextId;
  }
  // Keep admin carats selectable; mins are notices only (see isCaratHiddenForShop).
  updateCaratButtons();
  renderDiamondShapeButtons();
  if (isDiamondOnlyCategory()) {
    renderDiamondColorCarousel();
    productImageIndex = 0;
    if (shopView === 'product') updateLargeImage();
  }
  updateGirdlePreview();
  updateSummary();
}

function stoneCountMin() {
  return 1;
}

function stoneCountMax() {
  const counts = diamondOptions.stoneCounts?.length
    ? diamondOptions.stoneCounts.map(Number)
    : [2, 3, 4];
  return Math.max(stoneCountMin(), ...counts);
}

function normalizeStoneCount(raw) {
  const n = parseInt(String(raw), 10);
  if (Number.isNaN(n)) return stoneCountMin();
  return Math.min(stoneCountMax(), Math.max(stoneCountMin(), n));
}

let stoneCountStepperBound = false;

function bindStoneCountStepper() {
  if (stoneCountStepperBound) return;
  const dec = document.getElementById('stone-count-dec');
  const inc = document.getElementById('stone-count-inc');
  const input = document.getElementById('stone-count-input');
  if (!dec || !inc || !input) return;
  stoneCountStepperBound = true;

  dec.addEventListener('click', () => selectStoneCount(normalizeStoneCount((state.stoneCount || 1) - 1)));
  inc.addEventListener('click', () => selectStoneCount(normalizeStoneCount((state.stoneCount || 1) + 1)));

  input.addEventListener('keydown', (e) => {
    if (e.key === '.' || e.key === ',' || e.key === 'e' || e.key === 'E' || e.key === '+' || e.key === '-') {
      e.preventDefault();
    }
  });

  input.addEventListener('input', () => {
    const digits = input.value.replace(/[^\d]/g, '');
    if (digits !== input.value) input.value = digits;
    if (!digits) return;
    const next = normalizeStoneCount(digits);
    state.stoneCount = next;
    input.value = String(next);
    if (dec) dec.disabled = next <= stoneCountMin();
    if (inc) inc.disabled = next >= stoneCountMax();
    updateSummary();
  });

  input.addEventListener('blur', () => {
    selectStoneCount(normalizeStoneCount(input.value || stoneCountMin()));
  });
}

function syncStoneCountStepper() {
  bindStoneCountStepper();
  const stepper = document.getElementById('stone-count-stepper');
  const input = document.getElementById('stone-count-input');
  const dec = document.getElementById('stone-count-dec');
  const inc = document.getElementById('stone-count-inc');
  if (!stepper || !input) return;

  const show = usesStoneCountPicker();
  stepper.hidden = !show;
  if (!show) return;

  const min = stoneCountMin();
  const max = stoneCountMax();
  const value = normalizeStoneCount(state.stoneCount || min);
  if (state.stoneCount !== value) state.stoneCount = value;

  input.min = String(min);
  input.max = String(max);
  input.step = '1';
  input.value = String(value);

  if (dec) dec.disabled = value <= min;
  if (inc) inc.disabled = value >= max;
}

function renderStoneCountButtons() {
  syncStoneCountStepper();
}

function selectStoneCount(count) {
  state.stoneCount = normalizeStoneCount(count);
  syncStoneCountStepper();
  updateSummary();
}

let earringQtyStepperBound = false;

function bindEarringQuantityStepper() {
  if (earringQtyStepperBound) return;
  const dec = document.getElementById('earring-qty-dec');
  const inc = document.getElementById('earring-qty-inc');
  const input = document.getElementById('earring-qty-input');
  if (!dec || !inc || !input) return;
  earringQtyStepperBound = true;

  dec.addEventListener('click', () => selectEarringQuantity(normalizeEarringQuantity((state.quantity || 1) - 1)));
  inc.addEventListener('click', () => selectEarringQuantity(normalizeEarringQuantity((state.quantity || 1) + 1)));
  input.addEventListener('input', () => {
    const digits = String(input.value || '').replace(/\D/g, '');
    if (!digits) return;
    const next = normalizeEarringQuantity(digits);
    state.quantity = next;
    input.value = String(next);
    if (dec) dec.disabled = next <= earringQuantityMin();
    if (inc) inc.disabled = next >= earringQuantityMax();
    updateSummary();
  });
  input.addEventListener('blur', () => {
    selectEarringQuantity(normalizeEarringQuantity(input.value || earringQuantityMin()));
  });
}

function selectEarringQuantity(count) {
  state.quantity = normalizeEarringQuantity(count);
  syncEarringQuantityStepper();
  updateSummary();
}

function syncEarringQuantityStepper() {
  bindEarringQuantityStepper();
  const stepper = document.getElementById('earring-qty-stepper');
  const input = document.getElementById('earring-qty-input');
  const dec = document.getElementById('earring-qty-dec');
  const inc = document.getElementById('earring-qty-inc');
  if (!stepper || !input) return;

  const show = usesEarringQuantity();
  stepper.hidden = !show;
  if (!show) return;

  const min = earringQuantityMin();
  const max = earringQuantityMax();
  const value = normalizeEarringQuantity(state.quantity || min);
  if (state.quantity !== value) state.quantity = value;

  input.min = String(min);
  input.max = String(max);
  input.step = '1';
  input.value = String(value);
  if (dec) dec.disabled = value <= min;
  if (inc) inc.disabled = value >= max;
}

function updateEarringQuantityStep() {
  const step = document.getElementById('earring-quantity-step');
  if (step) step.classList.toggle('hidden', !usesEarringQuantity());
  if (usesEarringQuantity()) {
    state.quantity = normalizeEarringQuantity(state.quantity || 1);
  }
  syncEarringQuantityStepper();
}

function selectDiamondColor(colorId) {
  const meta = diamondColorOptions().find(c => c.id === colorId);
  if (!meta) return;
  if (meta.kind === 'white' || colorId === 'white') {
    state.diamondKind = 'white';
    state.fancyColor = null;
  } else {
    state.diamondKind = 'fancy';
    state.fancyColor = colorId;
  }
  // Color-as-product: keep selected catalog row in sync with color picker.
  if (isDiamondOnlyCategory()) {
    const match = memorialDiamondProductForColor(colorId);
    if (match && String(match.id) !== String(state.type)) {
      state.type = String(match.id);
      document.querySelectorAll('.type-card').forEach((c) => {
        c.classList.toggle('active', c.dataset.type === state.type);
      });
    }
  }
  ensureStoneCountDefault();
  updateDiamondSteps();
  updateCaratButtons();
  productImageIndex = 0;
  if (shopView === 'product') updateLargeImage(usesPendantCompositePreview() ? 'pendant' : undefined);
  updateGirdlePreview();
  updateSummary();
}


function buildQuotePayload() {
  ensureStoneCountDefault();
  if (state.category === 'pendant') {
    applyPendantSellMode(getSelectedProduct());
    // Keep chain SKU/gold filled whenever 含鍊 is on (catalog may load late in API mode).
    if (state.includeChain) syncAttachedChainFromPendant();
  }
  return {
    category: state.category,
    type: state.type,
    gold: state.gold,
    color: effectiveColor() || state.color,
    carat: state.carat,
    ringSize: state.ringSize,
    lengthCm: state.lengthCm,
    includeChain: state.includeChain,
    chainProductId: state.chainProductId,
    chainGold: state.chainGold,
    chainColor: state.chainColor,
    chainThickness: state.chainThickness,
    chainLength: state.chainLength,
    diamondKind: state.diamondKind,
    fancyColor: state.fancyColor,
    stoneCount: state.stoneCount,
    diamondShape: state.diamondShape,
    quantity: usesEarringQuantity() ? normalizeEarringQuantity(state.quantity) : undefined,
  };
}

async function fetchQuote() {
  const payload = buildQuotePayload();
  const fingerprint = JSON.stringify(payload);
  const id = ++quoteRequestId;
  activeQuoteController?.abort();
  activeQuoteController = null;
  if (quoteCache.has(fingerprint)) return quoteCache.get(fingerprint);

  const compute = window.ShopPricingLocal?.computeOrderPricing;
  if (compute && (shopUsesLocalPricing() || !shopUsesApi())) {
    const localQuote = compute(payload, catalog);
    quoteCache.set(fingerprint, localQuote);
    return localQuote;
  }
  const controller = new AbortController();
  activeQuoteController = controller;
  try {
    const quotePath = window.shopConfig?.preview ? '/api/quote?preview=1' : '/api/quote';
    const { res, data } = await shopApiFetch(quotePath, {
      method: 'POST',
      body: payload,
      signal: controller.signal,
    });
    if (!res.ok) return null;
    if (id !== quoteRequestId || controller.signal.aborted) return null;
    quoteCache.set(fingerprint, data);
    return data;
  } catch (err) {
    if (err?.name === 'AbortError') return null;
    console.error('quote fetch failed', err);
    return null;
  } finally {
    if (activeQuoteController === controller) activeQuoteController = null;
  }
}

function scheduleQuoteRefresh() {
  clearTimeout(quoteTimer);
  quoteRefreshPending = true;
  quoteTimer = setTimeout(() => { refreshQuotePrices(); }, 120);
}

function parseDisplayedTotal(text) {
  if (text == null) return null;
  const trimmed = String(text).trim();
  if (!trimmed || trimmed === '?' || trimmed === '—' || trimmed === '-') return null;
  const n = Number(trimmed.replace(/,/g, ''));
  return Number.isFinite(n) ? n : null;
}

/** Show mint sale + struck mint compare-at when multi-stone discount applies. */
function updateCompareAtDisplay(saleTotal, compareAtTotal) {
  const hero = document.getElementById('hero-price');
  const compareEl = document.getElementById('sum-total-compare');
  const mobileCompare = document.getElementById('sum-total-mobile-compare');
  const mobileAmount = mobileCompare?.closest('.mobile-buy-amount');
  const sale = saleTotal != null ? Math.round(Number(saleTotal)) : null;
  const compare = compareAtTotal != null ? Math.round(Number(compareAtTotal)) : null;
  const show = Number.isFinite(sale) && Number.isFinite(compare) && compare > sale;
  hero?.classList.toggle('hero-price--sale', show);
  mobileAmount?.classList.toggle('mobile-buy-amount--sale', show);
  if (compareEl) {
    if (show) {
      compareEl.hidden = false;
      compareEl.textContent = 'NT$ ' + compare.toLocaleString();
    } else {
      compareEl.hidden = true;
      compareEl.textContent = '';
    }
  }
  if (mobileCompare) {
    if (show) {
      mobileCompare.hidden = false;
      mobileCompare.textContent = compare.toLocaleString();
    } else {
      mobileCompare.hidden = true;
      mobileCompare.textContent = '';
    }
  }
}

/** Animate the large hero total (#sum-total) with count-up/down + color flash. */
function animateShopTotal(el, targetValue) {
  if (!el) return;
  const target = Math.round(Number(targetValue));
  if (!Number.isFinite(target)) {
    if (el._priceAnimFrame) cancelAnimationFrame(el._priceAnimFrame);
    el.classList.remove('hero-price-tick--up', 'hero-price-tick--down');
    el.textContent = '—';
    delete el.dataset.lastValue;
    return;
  }

  const stored = el.dataset.lastValue;
  const fromStored = stored !== undefined && stored !== '' ? Number(stored) : null;
  const fromDisplay = parseDisplayedTotal(el.textContent);
  let from;
  if (Number.isFinite(fromStored)) from = fromStored;
  else if (Number.isFinite(fromDisplay)) from = fromDisplay;
  else from = 0;

  el.dataset.lastValue = String(target);

  if (from === target) {
    el.textContent = target.toLocaleString();
    return;
  }

  if (el._priceAnimFrame) cancelAnimationFrame(el._priceAnimFrame);

  const direction = target > from ? 'up' : 'down';
  el.classList.remove('hero-price-tick--up', 'hero-price-tick--down');
  void el.offsetWidth;
  el.classList.add(direction === 'up' ? 'hero-price-tick--up' : 'hero-price-tick--down');

  const duration = 520;
  const startValue = from;
  const delta = target - from;
  const startTime = performance.now();
  const gen = (el._priceAnimGen = (el._priceAnimGen || 0) + 1);

  function finish() {
    el.textContent = target.toLocaleString();
    window.setTimeout(() => {
      if (el._priceAnimGen === gen) {
        el.classList.remove('hero-price-tick--up', 'hero-price-tick--down');
      }
    }, 700);
  }

  function tick(now) {
    if (el._priceAnimGen !== gen) return;
    const t = Math.min(1, (now - startTime) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(startValue + delta * eased).toLocaleString();
    if (t < 1) {
      el._priceAnimFrame = requestAnimationFrame(tick);
    } else {
      el._priceAnimFrame = 0;
      finish();
    }
  }

  el._priceAnimFrame = requestAnimationFrame(tick);
}

window.animateCountUp = animateShopTotal;

/** Fill #sum-chain-row for 含鍊 pendants. Row stays visible; amount may be "-" until quote ready. */
function renderChainFeeRow(chainRow, quote) {
  const wantsChain = state.category === 'pendant' && !!state.includeChain;
  chainRow?.classList.toggle('hidden', !wantsChain);
  const chainPriceEl = document.getElementById('sum-chain-price');
  if (!chainPriceEl) return;
  if (!wantsChain) {
    chainPriceEl.textContent = '-';
    return;
  }
  const amount = quote && quote.chainPrice != null ? Number(quote.chainPrice) : null;
  chainPriceEl.textContent = Number.isFinite(amount)
    ? Math.round(amount).toLocaleString()
    : '-';
}

async function refreshQuotePrices() {
  const pricePanel = document.getElementById('shop-price-panel');
  // API boot leaves catalog.chain empty until ensureCategoryCatalog — without this,
  // 含鍊 length UI still works (Excel fallback) but chainProductId stays null and
  // 鍊條費用 never appears (chainPrice omitted; fee looks folded into 金工).
  if (state.category === 'pendant' && state.includeChain) {
    await ensureCategoryCatalog('chain');
    syncAttachedChainFromPendant();
  }
  const requestFingerprint = JSON.stringify(buildQuotePayload());
  // Keep last known breakdown/total visible while recalculating.
  // Skeleton (is-loading-prices) is only for initial boot via HTML + loadMetalPrices.
  let quote;
  try {
    quote = await fetchQuote();
  } finally {
    quoteRefreshPending = false;
    pricePanel?.classList.remove('is-loading-prices');
  }
  if (requestFingerprint !== JSON.stringify(buildQuotePayload())) return;
  const diamondRow = document.getElementById('sum-diamond-row');
  const chainRow = document.getElementById('sum-chain-row');
  const totalEl = document.getElementById('sum-total');
  const mobileTotal = document.getElementById('sum-total-mobile');

  if (!quote || !quote.ready) {
    const keepStaleQuote = isReadyToSubmit() && lastQuoteTotal != null;
    if (keepStaleQuote) {
      updatePriceHint(lastQuoteTotal);
      updateCtaState(lastQuoteTotal);
      return;
    }
    if (quote && quote.error && window.showToast) {
      window.showToast(tr('price_unavailable'), 'error');
    } else if (isReadyToSubmit() && window.showToast) {
      window.showToast(tr('price_unavailable'), 'error');
    }
    if (diamondRow) diamondRow.style.display = state.category === 'chain' ? 'none' : '';
    renderChainFeeRow(chainRow, null);
    document.getElementById('sum-side-stone-row')?.classList.add('hidden');
    document.getElementById('sum-side-stone-cts-row')?.classList.add('hidden');
    document.getElementById('sum-diamond-price').textContent = state.carat ? '-' : '0';
    document.getElementById('sum-metalwork-price').textContent = '-';
    if (totalEl) animateShopTotal(totalEl, NaN);
    if (mobileTotal) mobileTotal.textContent = '—';
    updateCompareAtDisplay(null, null);
    lastQuoteTotal = null;
    lastQuoteFailed = isReadyToSubmit();
    updatePriceHint(null);
    updateCtaState(null);
    return;
  }

  const sideStoneRow = document.getElementById('sum-side-stone-row');
  const sideStoneCtsRow = document.getElementById('sum-side-stone-cts-row');
  if (quote.manualOverride) {
    if (diamondRow) diamondRow.style.display = 'none';
    sideStoneRow?.classList.add('hidden');
    sideStoneCtsRow?.classList.add('hidden');
    renderChainFeeRow(chainRow, quote);
    document.getElementById('sum-metalwork-price').textContent = '—';
  } else {
    if (diamondRow) diamondRow.style.display = state.category === 'chain' ? 'none' : '';
    if (quote.diamondPrice != null) {
      document.getElementById('sum-diamond-price').textContent = Math.round(quote.diamondPrice).toLocaleString();
    }
    const showSideStoneCts = quote.sideStoneCarat != null && Number(quote.sideStoneCarat) > 0;
    sideStoneCtsRow?.classList.toggle('hidden', !showSideStoneCts);
    if (showSideStoneCts) {
      const ctsEl = document.getElementById('sum-side-stone-cts');
      if (ctsEl) {
        const n = Number(quote.sideStoneCarat);
        ctsEl.textContent = Number.isInteger(n) ? String(n) : String(Math.round(n * 100) / 100);
      }
    }
    const showSideStone = quote.sideStonePrice != null && Number(quote.sideStonePrice) > 0;
    sideStoneRow?.classList.toggle('hidden', !showSideStone);
    if (showSideStone) {
      const sideEl = document.getElementById('sum-side-stone-price');
      if (sideEl) sideEl.textContent = Math.round(quote.sideStonePrice).toLocaleString();
    }
    const metalworkRow = document.getElementById('sum-metalwork-price')?.closest('.summary-row');
    if (isDiamondOnlyCategory()) {
      metalworkRow?.classList.add('hidden');
      document.getElementById('sum-metalwork-price').textContent = '0';
    } else {
      metalworkRow?.classList.remove('hidden');
      // 金工 = pendant taijin+labor only. Chain is never folded in (see metalworkPrice).
      const metalwork = quote.metalworkPrice != null
        ? quote.metalworkPrice
        : (quote.taijinPrice != null && quote.laborPrice != null ? quote.taijinPrice + quote.laborPrice : null);
      if (metalwork != null) {
        document.getElementById('sum-metalwork-price').textContent = Math.round(metalwork).toLocaleString();
      }
    }
    renderChainFeeRow(chainRow, quote);
  }

  const total = quote.total;
  const roundedTotal = total != null ? Math.round(total) : null;
  lastQuoteFailed = false;
  if (roundedTotal != null) lastQuoteTotal = roundedTotal;
  if (totalEl) animateShopTotal(totalEl, roundedTotal != null ? roundedTotal : NaN);
  if (mobileTotal) {
    mobileTotal.textContent = roundedTotal != null ? roundedTotal.toLocaleString() : '—';
  }
  updateCompareAtDisplay(roundedTotal, quote.compareAtTotal);
  updatePriceHint(total);
  updateCtaState(total);
}

function updateRingSizeStep() {
  const step = document.getElementById("ringsize-step");
  const guideStep = document.getElementById("ringsize-guide-step");
  const isRing = state.category === 'ring';
  const inProductView = document.querySelector('.shop-page')?.classList.contains('shop-view--product');
  step?.classList.toggle('hidden', !isRing);
  // Guide sits below .shop-body so sticky summary stops above it
  guideStep?.classList.toggle('hidden', !isRing || !inProductView);
  if (!isRing) state.ringSize = null;
}

// 0.3ct+ diamonds have enough girdle surface to engrave legible Chinese strokes.
function caratAllowsChineseEngraving() {
  const n = parseFloat(state.carat);
  return !Number.isNaN(n) && n >= 0.3;
}

function productAllowsEngraving() {
  const product = getProduct(state.category, state.type);
  if (!product) return false;
  return product.allowsEngraving !== false;
}

function productAllowsFancyShapes() {
  const product = getProduct(state.category, state.type);
  if (!product) return true;
  return product.allowsFancyShapes !== false;
}

function enforceRoundOnlyShape() {
  if (!productAllowsFancyShapes() && isNonRoundShape()) {
    state.diamondShape = 'round';
  }
  // Non-round needs ≥ nonRoundShapeMinCarat (0.3) on every product that offers fancy shapes.
  enforceNonRoundShapeMinCarat();
}

/** Reset non-round → round when carat drops below min (all categories). */
function enforceNonRoundShapeMinCarat() {
  if (isNonRoundShape() && !caratAllowsNonRoundShape()) {
    state.diamondShape = 'round';
  }
}

function updateEngravingSteps() {
  const bandStep = document.getElementById('engraving-band-step');
  const remarkStep = document.getElementById('engraving-remark-step');
  const girdleStep = document.getElementById('engraving-girdle-step');
  const allows = productAllowsEngraving();
  const hasBand = allows && state.category === 'ring';
  // Metal-body remark (手鍊鋼印等) — not for rings; rings use band engraving only.
  const hasRemark = allows && state.category !== 'chain' && state.category !== 'ring' && !isDiamondOnlyCategory();
  // Girdle is diamond-surface engraving — always offer except chain (backend keeps it too).
  const hasGirdle = state.category !== 'chain';
  bandStep?.classList.toggle('hidden', !hasBand);
  remarkStep?.classList.toggle('hidden', !hasRemark);
  girdleStep?.classList.toggle('hidden', !hasGirdle);
  if (!hasGirdle) {
    const preview = document.getElementById('shop-girdle-engrave-preview');
    if (preview) preview.innerHTML = '';
  }
  if (!hasBand) state.engravingBand = '';
  if (!hasRemark) state.engravingRemark = '';
  if (!hasGirdle) state.engravingGirdle = '';
  const bandInput = document.getElementById('engraving-band-input');
  if (bandInput) bandInput.value = state.engravingBand;
  const remarkInput = document.getElementById('engraving-remark-input');
  if (remarkInput) remarkInput.value = state.engravingRemark;
  const allowChinese = caratAllowsChineseEngraving();
  const girdleCtrl = ensureGirdleEngrave();
  if (girdleCtrl) {
    girdleCtrl.setAllowChinese(allowChinese);
    girdleCtrl.setValue(state.engravingGirdle || '');
    girdleCtrl.setPreviewShapeAndColor(resolvedDiamondShape(), selectedDiamondColorId() || 'white');
  }
  const hint = document.getElementById('shop-girdle-engrave-hint');
  if (hint) {
    const key = allowChinese ? 'engraving_girdle_hint_cjk' : 'engraving_girdle_hint';
    hint.setAttribute('data-i18n', key);
    hint.textContent = tr(key);
  }
  if (hasGirdle) scheduleGirdleEngraveLoad();
}

function closeAllShopDropdowns(except) {
  document.querySelectorAll('.shop-dd.is-open').forEach((dd) => {
    if (except && dd === except) return;
    dd.classList.remove('is-open');
    const trigger = dd.querySelector('.shop-dd__trigger');
    const menu = dd.querySelector('.shop-dd__menu');
    if (trigger) trigger.setAttribute('aria-expanded', 'false');
    if (menu) menu.hidden = true;
  });
}

function ensureShopDropdown(select) {
  if (!select) return null;
  let wrap = select.closest('.shop-dd');
  if (wrap) return wrap;

  wrap = document.createElement('div');
  wrap.className = 'shop-dd';
  select.parentNode.insertBefore(wrap, select);
  wrap.appendChild(select);
  select.classList.add('sr-only');
  select.tabIndex = -1;

  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'shop-dd__trigger';
  trigger.setAttribute('aria-haspopup', 'listbox');
  trigger.setAttribute('aria-expanded', 'false');
  trigger.innerHTML =
    '<span class="shop-dd__label"></span>' +
    '<svg class="shop-dd__chevron" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';

  const menu = document.createElement('div');
  menu.className = 'shop-dd__menu';
  menu.setAttribute('role', 'listbox');
  menu.hidden = true;

  wrap.appendChild(trigger);
  wrap.appendChild(menu);

  trigger.addEventListener('click', (e) => {
    e.preventDefault();
    const open = !wrap.classList.contains('is-open');
    closeAllShopDropdowns(open ? wrap : null);
    wrap.classList.toggle('is-open', open);
    trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
    menu.hidden = !open;
  });

  menu.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-value]');
    if (!btn) return;
    if (shopOptionIsDisabled(btn)) {
      toastShopBlocked(btn.dataset.blockedReason || 'diamond_fancy_min_carat');
      return;
    }
    const value = btn.getAttribute('data-value') || '';
    select.value = value;
    syncShopDropdown(select);
    select.dispatchEvent(new Event('change', { bubbles: true }));
    closeAllShopDropdowns();
  });

  return wrap;
}

function syncShopDropdown(select) {
  const wrap = ensureShopDropdown(select);
  if (!wrap) return;
  const trigger = wrap.querySelector('.shop-dd__trigger');
  const label = wrap.querySelector('.shop-dd__label');
  const menu = wrap.querySelector('.shop-dd__menu');
  if (!trigger || !label || !menu) return;

  const selectedOpt = select.selectedOptions && select.selectedOptions[0];
  label.textContent = selectedOpt ? selectedOpt.textContent : '';
  trigger.classList.toggle('shop-dd__trigger--placeholder', !select.value);

  menu.innerHTML = '';
  Array.from(select.options).forEach((opt) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'shop-dd__option';
    btn.setAttribute('role', 'option');
    btn.setAttribute('data-value', opt.value);
    btn.setAttribute('aria-selected', opt.value === select.value ? 'true' : 'false');
    btn.textContent = opt.textContent;
    if (opt.value === select.value) btn.classList.add('is-selected');
    if (opt.disabled) {
      setShopOptionDisabled(btn, true, {
        title: opt.title || undefined,
        reasonKey: opt.dataset.blockedReason || undefined,
      });
    }
    menu.appendChild(btn);
  });
}

function renderLengthSelect(selectId, options, selected, placeholderKey) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const n = selected != null ? Number(selected) : null;
  const current = n != null && options.includes(n) ? n : null;
  sel.innerHTML = '';
  const ph = document.createElement('option');
  ph.value = '';
  ph.textContent = tr(placeholderKey);
  sel.appendChild(ph);
  options.forEach((length) => {
    const opt = document.createElement('option');
    opt.value = String(length);
    opt.textContent = `${length} cm`;
    sel.appendChild(opt);
  });
  sel.value = current != null ? String(current) : '';
  syncShopDropdown(sel);
}

function renderThicknessSelect(selectId, options, selected, placeholderKey) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const current = selected && options.includes(selected) ? selected : null;
  sel.innerHTML = '';
  const ph = document.createElement('option');
  ph.value = '';
  ph.textContent = tr(placeholderKey);
  sel.appendChild(ph);
  options.forEach((thick) => {
    const opt = document.createElement('option');
    opt.value = thick;
    opt.textContent = thick;
    sel.appendChild(opt);
  });
  sel.value = current || '';
  syncShopDropdown(sel);
}

function updateLengthStep() {
  const endBlock = document.getElementById('chain-length-end');
  const step = document.getElementById('chain-length-step');
  const guideStep = document.getElementById('chain-length-guide-step');
  const label = step?.querySelector('.variant-label');
  const necklaceGuide = document.getElementById('chain-length-guide-necklace-inline');
  const braceletGuide = document.getElementById('chain-length-guide-bracelet-inline');
  const isChain = state.category === 'chain';
  const isBracelet = state.category === 'bracelet';
  const inProductView = document.querySelector('.shop-page')?.classList.contains('shop-view--product');
  const showSelect = isChain || isBracelet;
  const showPendantGuide = state.category === 'pendant' && !!state.includeChain;
  // Guide section sits below .shop-body so sticky summary stops at the red-line boundary
  const showGuideEnd = inProductView && (showSelect || showPendantGuide);

  step?.classList.toggle('hidden', !showSelect);
  guideStep?.classList.toggle('hidden', !showSelect);
  endBlock?.classList.toggle('hidden', !showGuideEnd);

  if (label) {
    const key = isBracelet ? 'step_bracelet_length' : 'step_chain_length';
    label.setAttribute('data-i18n', key);
    label.textContent = tr(key);
  }
  necklaceGuide?.classList.toggle('hidden', !isChain);
  braceletGuide?.classList.toggle('hidden', !isBracelet);

  if (isChain) {
    const product = getSelectedProduct();
    const options = chainLengthOptionsCm(product, state.carat);
    syncChainLengthState(options, 'lengthCm');
    renderLengthSelect('chain-length-select', options, state.lengthCm, 'chain_length_placeholder');
  } else if (isBracelet) {
    syncChainLengthState(BRACELET_LENGTH_OPTIONS_CM, 'lengthCm');
    renderLengthSelect('chain-length-select', BRACELET_LENGTH_OPTIONS_CM, state.lengthCm, 'bracelet_length_placeholder');
  } else {
    state.lengthCm = null;
    const sel = document.getElementById('chain-length-select');
    if (sel) sel.value = '';
  }
}

function defaultChainProductId() {
  const chains = productsFor('chain');
  return chains.length ? String(chains[0].id) : null;
}

/** Per-product 僅墜子 / 含鍊賣 flags from catalog (default both allowed). */
function pendantSellFlags(product) {
  return {
    allowOnly: !product || product.allowsPendantOnly !== false,
    allowChain: !product || product.allowsWithChain !== false,
  };
}

/** Force includeChain when product only allows one sell mode. */
function applyPendantSellMode(product) {
  const { allowOnly, allowChain } = pendantSellFlags(product);
  if (allowChain && !allowOnly) state.includeChain = true;
  else if (allowOnly && !allowChain) state.includeChain = false;
}

/**
 * Chain metal/color no longer user-picked — inherit from pendant body.
 * Pricing still needs a chain SKU + gold; pick first published chain product.
 */
function syncAttachedChainFromPendant() {
  if (!state.includeChain) {
    state.chainProductId = null;
    state.chainGold = null;
    state.chainColor = null;
    state.chainThickness = null;
    return;
  }
  const chains = productsFor('chain');
  const chainIds = chains.map((p) => String(p.id));
  if (!chainIds.includes(String(state.chainProductId))) {
    state.chainProductId = defaultChainProductId();
  }
  const chainProduct = getProduct('chain', state.chainProductId);
  const chainGolds = productGolds('chain', chainProduct);
  if (state.gold && chainGolds.includes(state.gold)) {
    state.chainGold = state.gold;
  } else if (chainGolds.length) {
    state.chainGold = chainGolds[0];
  } else {
    state.chainGold = state.gold || null;
  }
  state.chainColor = attachedChainColor(state.chainGold, state.color || previewColor());
}

async function updateChainOptions() {
  const pendantStep = document.getElementById('pendant-chain-step');
  const pendantGuideStep = document.getElementById('pendant-chain-guide-step');
  const toggleRow = document.getElementById('pendant-chain-toggle-row');
  const isPendant = state.category === 'pendant';
  const product = isPendant ? getSelectedProduct() : null;
  const { allowOnly, allowChain } = pendantSellFlags(product);

  if (!isPendant) {
    state.includeChain = false;
    state.chainProductId = null;
    state.chainGold = null;
    state.chainColor = null;
    pendantStep?.classList.add('hidden');
    pendantGuideStep?.classList.add('hidden');
    updateLengthStep();
    return;
  }

  applyPendantSellMode(product);

  // pendant-only: hide 搭配鏈條; otherwise show step
  if (!allowChain && allowOnly) {
    pendantStep?.classList.add('hidden');
  } else {
    pendantStep?.classList.remove('hidden');
  }

  // both → segmented buttons; with-chain-only → hide toggle, length only
  const showToggle = allowOnly && allowChain;
  toggleRow?.classList.toggle('hidden', !showToggle);
  document.querySelectorAll('.pendant-chain-seg__btn').forEach((btn) => {
    const wantChain = btn.dataset.includeChain === 'true';
    const active = (!!state.includeChain) === wantChain;
    btn.classList.toggle('is-active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
  });

  const options = document.getElementById('pendant-chain-options');
  options?.classList.toggle('hidden', !state.includeChain);
  pendantGuideStep?.classList.toggle('hidden', !state.includeChain);
  updateLengthStep();

  if (!state.includeChain) {
    syncAttachedChainFromPendant();
    return;
  }

  // Must load chain SKUs before defaultChainProductId — Excel length tables work
  // without a product, but pricing/鍊條費用 row needs chainProductId.
  await ensureCategoryCatalog('chain');
  syncAttachedChainFromPendant();
  if (state.chainProductId) {
    await ensureProductDetail(state.chainProductId, 'chain');
  }
  const chainProduct = getProduct('chain', state.chainProductId);
  const thicknesses = chainConfiguredThicknesses(chainProduct);
  syncChainThicknessState(thicknesses);
  renderThicknessSelect(
    'pendant-chain-thickness-select',
    thicknesses,
    state.chainThickness,
    'chain_thickness_placeholder',
  );
  const pendantChainLengths = chainLengthOptionsCm(chainProduct, state.chainThickness);
  syncChainLengthState(pendantChainLengths, 'chainLength');
  renderLengthSelect('pendant-chain-length-select', pendantChainLengths, state.chainLength, 'chain_length_placeholder');
}

function currentProductImages() {
  const product = getSelectedProduct();
  if (!product || usesPendantCompositePreview()) return [];
  if (isDiamondOnlyCategory()) {
    return [memorialDiamondShapeImageUrl(resolvedDiamondShape(), selectedDiamondColorId())];
  }
  const imageOpts = pendantPreviewImageOpts();
  const forColor = productImagesForColor(
    product,
    previewColor(),
    selectedDiamondColorId(),
    imageOpts,
  );
  if (forColor.length) return forColor;
  const catalog = catalogPreviewSrc(
    product,
    previewColor(),
    selectedDiamondColorId(),
    imageOpts.chainColor || null,
  );
  return catalog ? [catalog] : [];
}

function renderProductThumbnails(images) {
  const row = document.getElementById('product-image-thumbs');
  if (!row) return;
  row.innerHTML = '';
  if (images.length <= 1) {
    row.hidden = true;
    return;
  }
  row.hidden = false;
  images.forEach((url, index) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'product-thumb-btn' + (index === productImageIndex ? ' active' : '');
    btn.setAttribute('aria-label', `Image ${index + 1}`);
    const thumb = document.createElement('img');
    thumb.src = url;
    thumb.alt = '';
    thumb.loading = 'lazy';
    thumb.decoding = 'async';
    btn.appendChild(thumb);
    btn.addEventListener('click', () => {
      productImageIndex = index;
      updateLargeImage();
    });
    row.appendChild(btn);
  });
}

function updateGalleryNav(images) {
  const scrollable = images.length > 1;
  const prevBtn = document.getElementById('product-gallery-prev');
  const nextBtn = document.getElementById('product-gallery-next');
  const counter = document.getElementById('product-gallery-counter');
  if (prevBtn) {
    prevBtn.hidden = !scrollable;
    prevBtn.disabled = !scrollable;
  }
  if (nextBtn) {
    nextBtn.hidden = !scrollable;
    nextBtn.disabled = !scrollable;
  }
  if (counter) {
    counter.hidden = !scrollable;
    counter.textContent = scrollable ? `${productImageIndex + 1} / ${images.length}` : '';
  }
}

function stepProductImage(delta) {
  const images = currentProductImages();
  if (images.length <= 1) return;
  productImageIndex = (productImageIndex + delta + images.length) % images.length;
  updateLargeImage();
}

function productPreviewFallbackSrc(product) {
  const opts = pendantPreviewImageOpts();
  const catalog = catalogPreviewSrc(
    product,
    previewColor(),
    selectedDiamondColorId(),
    opts.chainColor || null,
  );
  if (catalog) return catalog;
  const stock = productImagesForColor(
    product,
    previewColor(),
    selectedDiamondColorId(),
    opts,
  )[0];
  if (stock) return stock;
  return readDisplayedPreviewSrc() || '';
}

function resetProductPreviewComposite() {
  const compositeEl = document.getElementById('product-preview-composite');
  const chainImg = document.getElementById('large-image-chain');
  const pendantImg = document.getElementById('large-image-pendant');
  compositeEl?.classList.add('hidden');
  compositeEl?.setAttribute('aria-hidden', 'true');
  if (chainImg) {
    chainImg.onerror = null;
    chainImg.removeAttribute('src');
  }
  if (pendantImg) {
    pendantImg.onerror = null;
    pendantImg.removeAttribute('src');
  }
}

function showSingleProductPreview(img, previewRoot, src, pendantOnly) {
  const compositeEl = document.getElementById('product-preview-composite');
  compositeEl?.classList.add('hidden');
  compositeEl?.setAttribute('aria-hidden', 'true');
  previewRoot?.classList.toggle('is-pendant-only', !!pendantOnly && !!src);
  if (img) {
    img.style.visibility = '';
    img.src = src || '';
  }
}

function updateLargeImage(layer) {
  if (shopView !== 'product' || !state.category || !state.type) return;
  const product = getSelectedProduct();
  const preview = product ? pendantPreviewLayers(product) : { composite: false, src: '', pendantOnly: false };
  const compositeEl = document.getElementById('product-preview-composite');
  const chainImg = document.getElementById('large-image-chain');
  const pendantImg = document.getElementById('large-image-pendant');
  const img = document.getElementById('large-image');
  const zoomBtn = document.getElementById('product-zoom-btn');
  const thumbs = document.getElementById('product-image-thumbs');
  const previewRoot = document.getElementById('large-image-container');

  if (preview.composite && compositeEl && chainImg && pendantImg && preview.chain && preview.pendant) {
    const fullFallback = product ? productPreviewFallbackSrc(product) : '';
    showCompositeProductPreview(chainImg, pendantImg, compositeEl, previewRoot, img, preview);
    const failComposite = () => {
      chainImg.onerror = null;
      pendantImg.onerror = null;
      if (fullFallback) showSingleProductPreview(img, previewRoot, fullFallback, false);
    };
    chainImg.onerror = failComposite;
    pendantImg.onerror = failComposite;
    if (zoomBtn) zoomBtn.hidden = false;
    if (thumbs) thumbs.hidden = true;
    document.getElementById('product-gallery-prev')?.setAttribute('hidden', '');
    document.getElementById('product-gallery-next')?.setAttribute('hidden', '');
    document.getElementById('product-gallery-counter')?.setAttribute('hidden', '');
    return;
  }

  resetProductPreviewComposite();

  const images = currentProductImages();
  if (productImageIndex >= images.length) productImageIndex = 0;
  const multiImageGallery = images.length > 1;
  const indexedSrc = images[productImageIndex] || '';

  // Catalog product.images (e.g. diamond-loose white.png) must not override matrix previews.
  if (isDiamondOnlyCategory()) {
    previewRoot?.classList.remove('is-pendant-only');
    const nextSrc = images[productImageIndex]
      || memorialDiamondShapeImageUrl(resolvedDiamondShape(), selectedDiamondColorId());
    if (img) {
      img.style.visibility = '';
      img.onerror = null;
      if (img.getAttribute('src') === nextSrc && nextSrc) {
        img.removeAttribute('src');
      }
      img.src = nextSrc;
      if (zoomBtn) zoomBtn.hidden = !(img.src && !img.src.endsWith('/'));
    }
    renderProductThumbnails(images);
    updateGalleryNav(images);
    return;
  }

  // pendantPreviewLayers resolves slot [0] via catalogPreviewSrc. Multi-image slots must
  // honor productImageIndex — never swap sibling carousel URLs via preview.src/fallback.
  let primarySrc = preview.composite
    ? ''
    : (multiImageGallery
      ? indexedSrc
      : (preview.src || (preview.keepPrevious ? '' : (indexedSrc || imageUrl(state.category, state.type) || ''))));
  let fallbacks = [];
  const pendantOnly = !!preview.pendantOnly;
  previewRoot?.classList.toggle('is-pendant-only', pendantOnly && !!primarySrc);
  if (img) {
    img.style.visibility = '';
    const imageOpts = pendantPreviewImageOpts();
    if (!preview.keepPrevious && product && window.ShopAssets?.productImageResolve && !preview.composite) {
      const resolved = window.ShopAssets.productImageResolve(
        productAssetId(product),
        previewColor(),
        product?.defaultColor,
        selectedDiamondColorId(),
        imageOpts,
      );
      if (!primarySrc && resolved.src) primarySrc = resolved.src;
      fallbacks = resolved.fallbacks || [];
      // If layers picked a different URL than resolve, keep layers (it knows chain metal).
      if (preview.src && !multiImageGallery) primarySrc = preview.src;
    } else if (preview.src && !multiImageGallery) {
      primarySrc = preview.src;
    }
    img.onerror = null;
    if (preview.keepPrevious && primarySrc) {
      const shown = normalizePreviewSrc(img.currentSrc || img.getAttribute('src') || '');
      if (shown === normalizePreviewSrc(primarySrc)) {
        if (zoomBtn) zoomBtn.hidden = !(img.src && !img.src.endsWith('/'));
        renderProductThumbnails(images);
        updateGalleryNav(images);
        return;
      }
    }
    // Force browser to apply new metal asset even when cached aggressively.
    // Use cache-buster — do NOT removeAttribute(src) after attaching onerror
    // (that races and can swap in a fallback / look like 僅墜子).
    let nextSrc = primarySrc || '';
    if (nextSrc && !preview.keepPrevious && img.getAttribute('src') === nextSrc) {
      nextSrc += (nextSrc.includes('?') ? '&' : '?') + '_=' + Date.now();
    }
    if (
      fallbacks.length
      && window.ShopAssets?.attachImageFallbackChain
      && !preview.fromCatalog
      && !preview.keepPrevious
      && !multiImageGallery
    ) {
      window.ShopAssets.attachImageFallbackChain(img, fallbacks);
    } else if (usesPendantCompositePreview() && product && !preview.keepPrevious && !multiImageGallery) {
      const fullFallback = productPreviewFallbackSrc(product);
      if (fullFallback && fullFallback !== primarySrc) {
        img.onerror = () => {
          img.onerror = null;
          showSingleProductPreview(img, previewRoot, fullFallback, false);
        };
      }
    }
    img.src = nextSrc;
    if (zoomBtn) zoomBtn.hidden = !(img.src && !img.src.endsWith('/'));
  }
  renderProductThumbnails(images);
  updateGalleryNav(images);
}

function syncLightboxImage() {
  const images = currentProductImages();
  const lbImg = document.getElementById("product-lightbox-img");
  const prevBtn = document.getElementById("product-lightbox-prev");
  const nextBtn = document.getElementById("product-lightbox-next");
  if (!lbImg) return;
  const src = images[productImageIndex] || document.getElementById("large-image")?.src || '';
  lbImg.src = src;
  lbImg.alt = document.getElementById("product-title")?.textContent || '';
  const multi = images.length > 1;
  if (prevBtn) prevBtn.hidden = !multi;
  if (nextBtn) nextBtn.hidden = !multi;
}

function openStaticImageLightbox(src, alt) {
  const lb = document.getElementById("product-image-lightbox");
  const lbImg = document.getElementById("product-lightbox-img");
  const prevBtn = document.getElementById("product-lightbox-prev");
  const nextBtn = document.getElementById("product-lightbox-next");
  if (!lb || !lbImg || !src) return;
  lbImg.src = src;
  lbImg.alt = alt || "";
  if (prevBtn) prevBtn.hidden = true;
  if (nextBtn) nextBtn.hidden = true;
  if (typeof lb.showModal === "function") lb.showModal();
}

function openProductImageLightbox() {
  const src = document.getElementById("large-image")?.src;
  if (!src || src.endsWith('/')) return;
  const lb = document.getElementById("product-image-lightbox");
  if (!lb) return;
  syncLightboxImage();
  if (typeof lb.showModal === 'function') lb.showModal();
}

function initProductImageLightbox() {
  document.getElementById("product-zoom-btn")?.addEventListener("click", openProductImageLightbox);
  document.getElementById("large-image")?.addEventListener("click", openProductImageLightbox);
  document.getElementById("product-gallery-prev")?.addEventListener("click", (e) => {
    e.stopPropagation();
    stepProductImage(-1);
  });
  document.getElementById("product-gallery-next")?.addEventListener("click", (e) => {
    e.stopPropagation();
    stepProductImage(1);
  });
  document.getElementById("product-lightbox-close")?.addEventListener("click", () => {
    document.getElementById("product-image-lightbox")?.close();
  });
  document.getElementById("product-lightbox-prev")?.addEventListener("click", () => {
    stepProductImage(-1);
    syncLightboxImage();
  });
  document.getElementById("product-lightbox-next")?.addEventListener("click", () => {
    stepProductImage(1);
    syncLightboxImage();
  });
  document.getElementById("product-image-lightbox")?.addEventListener("click", e => {
    if (e.target.id === 'product-image-lightbox') {
      e.target.close();
    }
  });

  const zoomHint = typeof tr === "function" ? tr("shop_zoom_image") : "放大圖片";
  document.querySelectorAll(".guide-image").forEach(img => {
    img.title = zoomHint;
    img.setAttribute("role", "button");
    img.tabIndex = 0;
  });
  document.querySelector(".shop-wizard")?.addEventListener("click", e => {
    const img = e.target.closest(".guide-image");
    if (!img || img.classList.contains("hidden") || !img.src) return;
    e.preventDefault();
    openStaticImageLightbox(img.currentSrc || img.src, img.alt);
  });
  document.querySelector(".shop-wizard")?.addEventListener("keydown", e => {
    const img = e.target.closest(".guide-image");
    if (!img || (e.key !== "Enter" && e.key !== " ")) return;
    e.preventDefault();
    openStaticImageLightbox(img.currentSrc || img.src, img.alt);
  });
}

// ── Summary update ────────────────────────────────────────────────────────

function updateSummary() {
  const summaryFingerprint = `${JSON.stringify(buildQuotePayload())}|prices:${pricesLoaded}`;
  const stateChanged = summaryFingerprint !== lastSummaryFingerprint;
  const loginChanged = shopIsLoggedIn !== lastSummaryLoginState;
  if (!stateChanged && !loginChanged) return;
  lastSummaryFingerprint = summaryFingerprint;
  lastSummaryLoginState = shopIsLoggedIn;

  // Category
  document.getElementById("sum-cat").textContent =
    state.category ? tr('cat_' + state.category) : '-';

  // Style — diamond standalone has no style pick (series SKU ≠ jewelry 款式)
  const selectedProduct = getSelectedProduct();
  const typeRow = document.getElementById('sum-type-row');
  const sumType = document.getElementById('sum-type');
  if (isDiamondOnlyCategory()) {
    typeRow?.classList.add('hidden');
    if (sumType) sumType.textContent = '-';
  } else {
    typeRow?.classList.remove('hidden');
    if (sumType) sumType.textContent = selectedProduct ? productName(selectedProduct) : '-';
  }

  document.getElementById("sum-material").textContent =
    isDiamondOnlyCategory()
      ? tr('sum_loose_diamond')
      : (state.gold ? materialLabel(state.gold, state.color) : '-');

  // Diamond carat or chain thickness
  const caratRow = document.getElementById('sum-carat-row');
  if (caratRow) caratRow.style.display = '';
  {
    const caratBase = state.carat
      ? (state.category === 'chain' ? state.carat : state.carat + 'ct')
      : '-';
    const badge = stoneCountBadgeText();
    const caratDisplay = badge && state.carat && state.category !== 'chain'
      ? `${caratBase} ${badge}`
      : caratBase;
    document.getElementById("sum-carat").textContent = caratDisplay;
  }

  const diamondColorRow = document.getElementById('sum-diamond-color-row');
  const sumDiamondColor = document.getElementById('sum-diamond-color');
  if (state.category === 'chain') {
    if (diamondColorRow) diamondColorRow.style.display = 'none';
  } else {
    if (diamondColorRow) diamondColorRow.style.display = '';
    const colorMeta = diamondColorOptions().find(c => c.id === selectedDiamondColorId());
    if (sumDiamondColor) {
      sumDiamondColor.textContent = colorMeta ? diamondMetaLabel(colorMeta) : '-';
    }
  }

  // Length — standalone chain/bracelet length, or the pendant's attached-chain length
  const lengthRow = document.getElementById('sum-length-row');
  const sumLength = document.getElementById('sum-length');
  const lengthCm = (state.category === 'chain' || state.category === 'bracelet')
    ? state.lengthCm
    : (state.category === 'pendant' && state.includeChain) ? state.chainLength : null;
  lengthRow?.classList.toggle('hidden', lengthCm == null);
  if (lengthCm != null && sumLength) {
    sumLength.textContent = `${lengthCm} cm`;
  }

  // Weight lookup (from the selected product's own variant data)
  const baseChin = (state.category && state.type && state.gold && state.carat)
    ? lookupWeight(state.category, state.type, state.gold, state.carat)
    : null;
  const chin = baseChin !== null && state.category === 'chain' && state.lengthCm
    ? getSelectedProduct()?.lengthWeights?.[state.carat]?.[String(state.lengthCm)] ?? null
    : baseChin !== null && state.category === 'bracelet' && state.lengthCm
      ? baseChin * (state.lengthCm / BRACELET_REFERENCE_LENGTH_CM)
      : baseChin;

  if (stateChanged) scheduleQuoteRefresh();

  updateCtaState(lastQuoteTotal);
  updateBreadcrumb();
  updateConfigChips();
  updateProductHeader();
}

function clearRingSizeSelection() {
  state.ringSize = null;
  state.engravingBand = '';
  state.engravingRemark = '';
  state.engravingGirdle = '';
  state.lengthCm = null;
  state.includeChain = false;
  state.chainProductId = null;
  state.chainGold = null;
  state.chainColor = null;
  state.chainThickness = null;
  state.chainLength = null;
  resetDiamondOptions();
  const sel = document.getElementById('ring-size-select');
  if (sel) sel.value = '';
}

function selectRingSize(size) {
  const parsed = size != null && size !== '' ? parseFloat(size) : null;
  state.ringSize = parsed;
  const sel = document.getElementById('ring-size-select');
  if (sel) sel.value = parsed != null ? String(parsed) : '';
  updateSummary();
}

function setRingSizeActive(size) {
  selectRingSize(size);
}

function productRingBoundInt(raw) {
  if (raw == null || raw === '') return null;
  const n = Math.round(Number(raw));
  if (!Number.isFinite(n) || n < RING_SIZE_FLOOR) return null;
  return n;
}

function productRingStartSize(product) {
  const cfg = product && (product.ringSizeConfig || product.ring_size_config);
  if (!cfg) return null;
  const raw = cfg.minSize != null ? cfg.minSize
    : (cfg.min_size != null ? cfg.min_size
      : (cfg.startSize != null ? cfg.startSize : cfg.start_size));
  return productRingBoundInt(raw);
}

function productRingMaxSize(product) {
  const cfg = product && (product.ringSizeConfig || product.ring_size_config);
  if (!cfg) return null;
  const raw = cfg.maxSize != null ? cfg.maxSize : cfg.max_size;
  return productRingBoundInt(raw);
}

/** Apply product min/max as picker bounds; optionally select min as default. */
function applyProductRingSizeBounds(product, options) {
  const opts = options || {};
  const selectDefault = opts.selectDefault !== false;
  const start = productRingStartSize(product);
  const max = productRingMaxSize(product);
  ringSizeMin = start != null ? start : RING_SIZE_DEFAULT_MIN;
  ringSizeMax = max != null ? max : RING_SIZE_DEFAULT_MAX;
  if (ringSizeMin > ringSizeMax) {
    ringSizeMin = RING_SIZE_DEFAULT_MIN;
    ringSizeMax = RING_SIZE_DEFAULT_MAX;
  }
  populateRingSizeSelect();
  if (selectDefault && start != null) {
    setRingSizeActive(start);
  }
  return start;
}

function populateRingSizeSelect() {
  const sel = document.getElementById('ring-size-select');
  if (!sel) return;
  const current = state.ringSize;
  const placeholder = tr('ring_size_placeholder');
  sel.innerHTML = '';
  const ph = document.createElement('option');
  ph.value = '';
  ph.textContent = placeholder;
  sel.appendChild(ph);
  for (let s = ringSizeMin; s <= ringSizeMax; s += 1) {
    const opt = document.createElement('option');
    opt.value = String(s);
    opt.textContent = tr('ring_size_option') + s;
    sel.appendChild(opt);
  }
  if (current != null && current >= ringSizeMin && current <= ringSizeMax) {
    sel.value = String(current);
  }
}

function renderRingSizeGuide() {
  const body = document.getElementById('ring-size-guide-body');
  if (!body) return;
  body.innerHTML = '';
  for (let size = ringSizeMin; size <= ringSizeMax; size += 1) {
    const ref = ringSizeReference[String(size)] || ringSizeReference[size] || {};
    const row = document.createElement('tr');
    const values = [
      `#${size}`,
      ref.diameter_cm != null ? `${Number(ref.diameter_cm).toFixed(2)} cm` : '—',
      ref.circumference_cm != null ? `${Number(ref.circumference_cm).toFixed(2)} cm` : '—',
      ref.jp != null ? `#${ref.jp}` : '—',
      ref.us != null ? `#${ref.us}` : '—',
      ref.eu != null ? `#${ref.eu}` : '—',
    ];
    values.forEach(value => {
      const cell = document.createElement('td');
      cell.textContent = value;
      row.appendChild(cell);
    });
    body.appendChild(row);
  }
}

// ── Selection handlers ────────────────────────────────────────────────────

async function selectCategory(cat, options) {
  const opts = options || {};
  state.category = cat;
  state.type = null;
  state.gold = null;
  state.color = null;
  state.carat = null;
  state.ringSize = null;
  ringSizeMin = RING_SIZE_DEFAULT_MIN;
  ringSizeMax = RING_SIZE_DEFAULT_MAX;
  state.engravingBand = '';
  state.engravingRemark = '';
  state.engravingGirdle = '';
  state.lengthCm = null;
  state.includeChain = false;
  state.chainProductId = null;
  state.chainGold = null;
  state.chainColor = null;
  state.chainThickness = null;
  state.chainLength = null;
  state.quantity = 1;

  document.querySelectorAll(".cat-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.cat === cat));

  if (window.CatalogMultiFilter) {
    window.CatalogMultiFilter.setHidden('catalog-metal-filter', cat === 'diamond');
    if (cat === 'diamond') window.CatalogMultiFilter.clearValues('catalog-metal-filter');
  } else {
    const metalFilter = document.getElementById('catalog-metal-filter');
    if (metalFilter) {
      metalFilter.hidden = cat === 'diamond';
      if (cat === 'diamond') metalFilter.value = '';
    }
  }
  populateCatalogFilters({ keepSelection: false, category: cat });
  updateDiamondWizardChrome();

  if (cat === 'diamond') {
    ensureMemorialDiamondCatalog();
    const typeId = resolveMemorialDiamondTypeRef(
      opts.typeId || defaultMemorialDiamondTypeId(),
    );
    await selectType(typeId, opts);
    return;
  }

  await ensureCategoryCatalog(cat);
  populateCatalogFilters({ keepSelection: false });
  renderTypeCards();
  const titleEl = document.getElementById("shop-category-title");
  if (titleEl) titleEl.textContent = tr('cat_' + cat);

  document.querySelectorAll("#metal-btn-row .metal-btn, #color-btn-row .color-btn").forEach(b => b.classList.remove("active"));
  clearRingSizeSelection();
  updateMetalButtons();
  updateCaratButtons();
  updateChainOptions();

  setShopView('styles', opts);
  updateSummary();
}

function resolveMemorialDiamondTypeRef(typeRef) {
  const raw = String(typeRef || '').trim();
  // Old series deep-links (滿月/寵物/…) → white color product.
  if (/^diamond-(first-love|pet|love|family|heirloom)$/i.test(raw)) {
    return defaultMemorialDiamondTypeId();
  }
  const match = getProduct('diamond', raw);
  if (match?.id != null) return String(match.id);
  if (match?.styleKey) return String(match.styleKey);
  return raw || defaultMemorialDiamondTypeId();
}

async function selectType(typeId, options) {
  const opts = options || {};
  const resolvedType = state.category === 'diamond'
    ? resolveMemorialDiamondTypeRef(typeId)
    : typeId;
  state.type = resolvedType;
  state.carat = null;
  state.gold = null;
  state.color = null;
  state.ringSize = null;
  state.engravingBand = '';
  state.engravingRemark = '';
  state.engravingGirdle = '';
  state.quantity = 1;
  resetDiamondOptions();

  document.querySelectorAll(".type-card").forEach(c =>
    c.classList.toggle("active", c.dataset.type === resolvedType));

  // Reveal the configure step immediately using the already-loaded catalog
  // (lite) product data, so the click feels instant instead of waiting on
  // the network. Full detail (weights/gold options) streams in below and
  // refreshes the step-3 controls once it arrives.
  setShopView('product', opts);

  await ensureProductDetail(resolvedType, state.category);
  ensureLiveGoldPolling();
  const product = getSelectedProduct();
  if (isDiamondOnlyCategory()) applyMemorialDiamondProductColor(product);

  // Default carat = smallest admin option before metal is chosen.
  const initialCarats = listProductCaratOptions(product, null);
  if (state.category === 'chain') state.carat = null;
  else if (initialCarats.length) state.carat = initialCarats[0];
  updateCaratButtons();
  updateMetalButtons();
  document.querySelectorAll("#metal-btn-row .metal-btn, #color-btn-row .color-btn").forEach(b => b.classList.remove("active"));
  clearRingSizeSelection();
  if (state.category === 'ring') {
    applyProductRingSizeBounds(product);
  } else {
    ringSizeMin = RING_SIZE_DEFAULT_MIN;
    ringSizeMax = RING_SIZE_DEFAULT_MAX;
  }

  productImageIndex = 0;
  updateLargeImage();
  updateRingSizeStep();
  updateEngravingSteps();
  updateDiamondSteps();
  await updateChainOptions();
  updateSummary();
}

function selectMetal(gold) {
  const product = getSelectedProduct();
  const golds = productGolds(state.category, product);
  if (product && gold && !golds.includes(gold)) return;
  state.gold = gold;
  state.color = enforceMetalColor(gold, state.color, product);
  enforceCaratForGold(product, gold);
  renderMetalButtons('metal-btn-row', golds, gold, selectMetal);
  updateColorStep(gold);
  updateCaratButtons();
  updateRingSizeStep();
  updateEngravingSteps();
  updateDiamondSteps();
  updateChainOptions();
  updateLargeImage(usesPendantCompositePreview() ? 'pendant' : undefined);
  updateSummary();
}

function selectColor(color) {
  const product = getSelectedProduct();
  if (!needsColorSelection(state.gold, product)) return;
  const colors = availableColorsForGold(state.gold, product);
  if (!colors.includes(color)) return;
  // Pendant color only — do not touch state.chainColor (mixed metal).
  state.color = color;
  document.querySelectorAll('#color-btn-row .color-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.color === color));
  productImageIndex = 0;
  updateRingSizeStep();
  updateEngravingSteps();
  updateDiamondSteps();
  updateChainOptions();
  updateLargeImage(usesPendantCompositePreview() ? 'pendant' : undefined);
  updateSummary();
}

function selectCarat(carat) {
  const product = getSelectedProduct();
  const selectable = listProductCaratOptions(product, state.gold);
  if (
    carat
    && state.category !== 'chain'
    && state.diamondKind === 'fancy'
    && !selectable.includes(String(carat))
  ) {
    toastShopBlocked('diamond_fancy_min_carat');
    updateCaratButtons();
    return;
  }
  state.carat = carat;

  const sel = document.getElementById('carat-select');
  if (sel) sel.value = carat != null ? String(carat) : '';

  updateMetalButtons();
  updateRingSizeStep();
  updateEngravingSteps();
  updateDiamondSteps();
  updateChainOptions();
  syncVariantChipActiveStates();
  updateLargeImage();
  updateSummary();
}

// ── Event wiring ──────────────────────────────────────────────────────────

document.getElementById('carat-select')?.addEventListener('change', (e) =>
  selectCarat(e.target.value || null));

document.getElementById('ring-size-select')?.addEventListener('change', (e) =>
  selectRingSize(e.target.value));

document.getElementById('chain-length-select')?.addEventListener('change', (e) => {
  const v = e.target.value;
  state.lengthCm = v ? Number(v) : null;
  updateSummary();
});

document.getElementById('pendant-chain-thickness-select')?.addEventListener('change', (e) => {
  const v = e.target.value || null;
  state.chainThickness = v;
  const chainProduct = getProduct('chain', state.chainProductId);
  const opts = chainLengthOptionsCm(chainProduct, state.chainThickness);
  syncChainLengthState(opts, 'chainLength');
  renderLengthSelect('pendant-chain-length-select', opts, state.chainLength, 'chain_length_placeholder');
  updateSummary();
});

document.getElementById('pendant-chain-length-select')?.addEventListener('change', (e) => {
  const v = e.target.value;
  state.chainLength = v ? Number(v) : null;
  updateSummary();
});

document.getElementById('engraving-band-input')?.addEventListener('input', (e) => {
  state.engravingBand = e.target.value;
  updateSummary();
});

document.getElementById('engraving-remark-input')?.addEventListener('input', (e) => {
  state.engravingRemark = e.target.value;
  updateSummary();
});

function updateGirdlePreview() {
  const ctrl = ensureGirdleEngrave();
  const shapeId = resolvedDiamondShape();
  const colorId = selectedDiamondColorId() || 'white';
  if (ctrl?.setPreviewShapeAndColor) {
    ctrl.setPreviewShapeAndColor(shapeId, colorId);
  } else if (ctrl?.setPreviewColor) {
    ctrl.setPreviewColor(colorId);
  }
}

let girdleEngraveCtrl = null;
let girdleEngraveLoadPromise = null;
let girdleEngraveObserver = null;

function syncGirdleEngrave() {
  const ctrl = ensureGirdleEngrave();
  if (!ctrl) return;
  ctrl.setAllowChinese(caratAllowsChineseEngraving());
  ctrl.setValue(state.engravingGirdle || '');
  ctrl.setPreviewShapeAndColor(resolvedDiamondShape(), selectedDiamondColorId() || 'white');
}

function loadGirdleEngrave() {
  if (window.GirdleEngrave) return Promise.resolve(window.GirdleEngrave);
  if (girdleEngraveLoadPromise) return girdleEngraveLoadPromise;
  girdleEngraveLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = '/static/js/girdle-engrave.js?v=26';
    script.async = true;
    script.onload = () => resolve(window.GirdleEngrave);
    script.onerror = () => reject(new Error('girdle engraving script failed to load'));
    document.head.appendChild(script);
  }).then((api) => {
    syncGirdleEngrave();
    return api;
  }).catch((error) => {
    girdleEngraveLoadPromise = null;
    console.warn(error);
    return null;
  });
  return girdleEngraveLoadPromise;
}

function scheduleGirdleEngraveLoad() {
  const root = document.getElementById('engraving-girdle-step');
  if (!root || root.classList.contains('hidden') || window.GirdleEngrave) return;
  if (!girdleEngraveObserver && 'IntersectionObserver' in window) {
    girdleEngraveObserver = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      girdleEngraveObserver.disconnect();
      girdleEngraveObserver = null;
      void loadGirdleEngrave();
    }, { rootMargin: '160px 0px' });
    girdleEngraveObserver.observe(root);
  }
  root.addEventListener('pointerdown', () => void loadGirdleEngrave(), { once: true });
  root.addEventListener('focusin', () => void loadGirdleEngrave(), { once: true });
}

function ensureGirdleEngrave() {
  if (girdleEngraveCtrl) return girdleEngraveCtrl;
  const input = document.getElementById('shop-girdle-engrave-input');
  if (!input || !window.GirdleEngrave) return null;
  girdleEngraveCtrl = window.GirdleEngrave.init({
    input,
    countEl: document.getElementById('shop-girdle-engrave-count'),
    previewEl: document.getElementById('shop-girdle-engrave-preview'),
    emblemsRoot: document.getElementById('engraving-girdle-step'),
    previewShape: resolvedDiamondShape(),
    previewColor: selectedDiamondColorId() || 'white',
    allowChinese: caratAllowsChineseEngraving(),
    max: 12,
    onChange: (val) => {
      state.engravingGirdle = val;
      updateSummary();
    },
  });
  return girdleEngraveCtrl;
}
document.getElementById('pendant-chain-toggle-row')?.addEventListener('click', async (ev) => {
  const btn = ev.target.closest('.pendant-chain-seg__btn');
  if (!btn) return;
  const flags = pendantSellFlags(getSelectedProduct());
  const wantChain = btn.dataset.includeChain === 'true';
  if (wantChain && !flags.allowChain) return;
  if (!wantChain && !flags.allowOnly) return;
  state.includeChain = wantChain;
  if (state.includeChain) {
    await ensureCategoryCatalog('chain');
    syncAttachedChainFromPendant();
    if (state.chainProductId) await ensureProductDetail(state.chainProductId, 'chain');
    const chainProduct = getProduct('chain', state.chainProductId);
    const thicknesses = chainConfiguredThicknesses(chainProduct);
    syncChainThicknessState(thicknesses);
    const opts = chainLengthOptionsCm(chainProduct, state.chainThickness);
    syncChainLengthState(opts, 'chainLength');
  } else {
    state.chainThickness = null;
  }
  productImageIndex = 0;
  await updateChainOptions();
  updateSummary();
  updateLargeImage(state.includeChain ? 'chain' : 'pendant');
});

document.addEventListener('mousedown', (ev) => {
  if (ev.target.closest('.shop-dd')) return;
  closeAllShopDropdowns();
});

document.getElementById('fancy-color-prev')?.addEventListener('click', () => scrollCarousel('fancy-color-carousel', -1));
document.getElementById('fancy-color-next')?.addEventListener('click', () => scrollCarousel('fancy-color-carousel', 1));
window.addEventListener('resize', scheduleDiamondCarouselNavUpdate, { passive: true });

const ringSizeGuideDialog = document.getElementById('ring-size-guide-dialog');
document.getElementById('ring-size-guide-close')?.addEventListener('click', () =>
  ringSizeGuideDialog?.close());

const chainLengthGuideDialog = document.getElementById('chain-length-guide-dialog');
function openChainLengthGuide(mode) {
  const isBracelet = mode === 'bracelet' || (mode !== 'necklace' && state.category === 'bracelet');
  document.getElementById('chain-length-guide-necklace')?.classList.toggle('hidden', isBracelet);
  document.getElementById('chain-length-guide-bracelet')?.classList.toggle('hidden', !isBracelet);
  const title = chainLengthGuideDialog?.querySelector('h2');
  if (title) {
    const key = isBracelet ? 'bracelet_length_guide_title' : 'chain_length_guide_title';
    title.setAttribute('data-i18n', key);
    title.textContent = tr(key);
  }
  const intro = chainLengthGuideDialog?.querySelector('.ring-size-guide-header p');
  if (intro) {
    const key = isBracelet ? 'bracelet_length_guide_intro' : 'chain_length_guide_intro';
    intro.setAttribute('data-i18n', key);
    intro.textContent = tr(key);
  }
  chainLengthGuideDialog?.showModal();
}
document.getElementById('chain-length-guide-open')?.addEventListener('click', () => openChainLengthGuide());
document.getElementById('pendant-chain-length-guide-open')?.addEventListener('click', () => openChainLengthGuide('necklace'));
document.getElementById('chain-length-guide-close')?.addEventListener('click', () =>
  chainLengthGuideDialog?.close());

document.getElementById('back-to-catalog')?.addEventListener('click', () => {
  if (shopInAppHistoryBack('catalog')) return;
  clearShopWizardSelection();
  setShopView('catalog', { history: 'replace' });
  updateSummary();
});

document.getElementById('back-to-styles')?.addEventListener('click', () => {
  if (!state.category) return;
  if (isDiamondOnlyCategory()) {
    document.getElementById('back-to-catalog')?.click();
    return;
  }
  if (shopInAppHistoryBack('styles')) return;
  setShopView('styles', { history: 'replace' });
  renderTypeCards();
  updateSummary();
});

// ── Submit / Update ───────────────────────────────────────────────────────

function liveCalculatorPreviewUrls() {
  const compositeEl = document.getElementById('product-preview-composite');
  if (compositeEl && !compositeEl.classList.contains('hidden')) {
    const pendant = document.getElementById('large-image-pendant');
    const chain = document.getElementById('large-image-chain');
    const pSrc = pendant?.currentSrc || pendant?.src || '';
    const cSrc = chain?.currentSrc || chain?.src || '';
    if (pSrc && !pSrc.endsWith('/') && cSrc && !cSrc.endsWith('/')) {
      return { composite: true, pendant: pSrc, chain: cSrc };
    }
  }
  const img = document.getElementById('large-image');
  const src = img?.currentSrc || img?.src || '';
  if (src && !src.endsWith('/') && img?.style.visibility !== 'hidden') {
    return { composite: false, primary: src };
  }
  return null;
}

function sharePreviewImageUrl() {
  const live = liveCalculatorPreviewUrls();
  if (live?.composite) return live.pendant;
  if (live?.primary) return live.primary;
  const product = getSelectedProduct();
  if (!product) return '';
  const layers = pendantPreviewLayers(product);
  if (layers.composite) return layers.pendant || layers.chain || '';
  return layers.src || readDisplayedPreviewSrc() || '';
}

function sharePreviewChainImageUrl() {
  const live = liveCalculatorPreviewUrls();
  if (live?.composite) return live.chain || '';
  const product = getSelectedProduct();
  if (!product || !usesPendantCompositePreview()) return '';
  const layers = pendantPreviewLayers(product);
  return layers.composite ? (layers.chain || '') : '';
}

function buildSubmitPayload() {
  ensureStoneCountDefault();
  if (state.category === 'pendant') applyPendantSellMode(getSelectedProduct());
  const submitColor = effectiveColor();
  const payload = {
    category: state.category,
    type:     state.type,
    gold:     state.gold,
    color:    submitColor || state.color,
    carat:    state.carat,
    ringSize: state.ringSize,
    engravingBand: state.engravingBand,
    engravingRemark: state.engravingRemark,
    engravingGirdle: state.engravingGirdle,
    lengthCm: state.lengthCm,
    includeChain: state.includeChain,
    chainProductId: state.chainProductId,
    chainGold: state.chainGold,
    chainColor: state.chainColor,
    chainThickness: state.chainThickness,
    chainLength: state.chainLength,
    diamondKind: state.diamondKind,
    fancyColor: state.fancyColor,
    stoneCount: state.stoneCount,
    diamondShape: state.diamondShape,
  };
  if (usesEarringQuantity()) {
    payload.quantity = normalizeEarringQuantity(state.quantity);
  }
  const product = getSelectedProduct();
  if (product) {
    payload.summaryZh = productName(product);
    const assetId = productAssetId(product);
    if (assetId) payload.styleKey = assetId;
    if (product.defaultColor) payload.defaultColor = product.defaultColor;
    const previewImage = sharePreviewImageUrl();
    if (previewImage) payload.previewImage = previewImage;
    const previewChain = sharePreviewChainImageUrl();
    if (previewChain) payload.previewChainImage = previewChain;
  }
  if (state.category !== 'chain') payload.diamondColor = selectedDiamondColorId();
  return payload;
}

function encodeConfigToken(payload) {
  const bytes = new TextEncoder().encode(JSON.stringify(payload));
  let binary = '';
  bytes.forEach(byte => { binary += String.fromCharCode(byte); });
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function openQuoteSheet() {
  const token = encodeConfigToken(buildSubmitPayload());
  const base = window.shopConfig?.quoteSheetUrl || '/quote-sheet';
  window.open(`${base}?config=${encodeURIComponent(token)}`, '_blank', 'noopener');
}

function openShareSummary() {
  const token = encodeConfigToken(buildSubmitPayload());
  const template = window.shopConfig?.shareBaseUrl || '/s/TOKEN';
  window.open(template.replace('TOKEN', encodeURIComponent(token)), '_blank', 'noopener');
}

function buildInquirySummaryLines() {
  const product = getSelectedProduct();
  const pricing = window.ShopPricingLocal?.computeOrderPricing?.(buildQuotePayload(), catalog)
    || (lastQuoteTotal != null ? { total: lastQuoteTotal } : null);
  const lines = [
    '【品項訂製諮詢】',
    `品項：${state.category ? tr('cat_' + state.category) : '-'}`,
    `款式：${productName(product) || '-'}`,
    `金屬：${state.gold || '-'}`,
  ];
  if (state.color) lines.push(`成色：${tr('color_' + state.color) || state.color}`);
  if (state.carat) {
    lines.push(state.category === 'chain' ? `厚度：${state.carat}` : `克拉：${state.carat}`);
  }
  if (state.ringSize) lines.push(`戒圍：${state.ringSize}`);
  if (state.lengthCm) lines.push(`長度：${state.lengthCm} cm`);
  if (pricing?.total != null) lines.push(`試算參考價：NT$ ${Math.round(pricing.total).toLocaleString()}`);
  if (state.engravingBand) lines.push(`戒台刻字：${state.engravingBand}`);
  if (state.engravingRemark) lines.push(`金屬刻字：${state.engravingRemark}`);
  if (state.engravingGirdle) lines.push(`腰圍刻字：${state.engravingGirdle}`);
  lines.push('', '請協助確認報價與交期，謝謝。');
  return lines;
}

function openContactForOrder() {
  const toast = (msg, type) => window.showToast ? window.showToast(msg, type || 'info') : alert(msg);
  if (!validateBeforeSubmit(toast)) return;
  try {
    sessionStorage.setItem('shopInquiryDraft', buildInquirySummaryLines().join('\n'));
  } catch (_) { /* ignore */ }
  window.location.href = window.shopConfig?.contactUrl || '/contact';
}

async function addCurrentFavorite() {
  const button = document.getElementById('favorite-btn');
  if (!button || button.disabled) return;
  const toast = (msg, type) => window.showToast ? window.showToast(msg, type || 'info') : alert(msg);
  if (!state.category) { toast(tr('alert_pick_category')); return; }
  if (!state.type) { toast(tr('alert_pick_type')); return; }
  button.disabled = true;
  try {
    if (!shopUsesApi()) {
      const key = 'shopLocalFavorites';
      const list = JSON.parse(localStorage.getItem(key) || '[]');
      list.push(buildSubmitPayload());
      localStorage.setItem(key, JSON.stringify(list));
      button.textContent = '♥';
      button.classList.add('is-saved');
      (window.showToast || alert)(tr('favorite_added'), 'success');
      return;
    }
    const { res, data } = await shopApiFetch('/api/favorites', {
      method: 'POST',
      body: buildSubmitPayload(),
    });
    if (res.status === 401) {
      redirectGuestToLogin();
      return;
    }
    if (!res.ok || data.error) throw new Error(data.error || 'favorite failed');
    button.textContent = '♥';
    button.classList.add('is-saved');
    const toast = window.showToast || alert;
    toast(tr('favorite_added'), 'success');
  } catch (error) {
    console.error(error);
    (window.showToast || alert)(tr('generic_error'), 'error');
  } finally {
    updateFavoriteButton();
  }
}

function validateBeforeSubmit(toast, opts = {}) {
  const highlight = opts.highlight !== false;
  const missing = getMissingSubmitFields();
  if (missing.length) {
    // Inline red highlights + #price-hint only — no alert()/toast popup
    if (highlight) highlightMissingSubmitFields(missing);
    updatePriceHint(null);
    return false;
  }

  if (state.category === 'chain' && state.gold === '9k') {
    const product = getSelectedProduct();
    if (product && product.defaultColor !== 'white') {
      toast(tr('alert_chain_9k_white_only'));
      return false;
    }
  }

  if (shopUsesApi() && !isSubmitPriceReady()) {
    toast(tr('shop_price_unavailable'));
    return false;
  }

  clearAllSubmitFieldHighlights();
  return true;
}

async function handleAddToCart() {
  if (window.cartEditData) {
    return handleCartUpdate();
  }

  const toast = (msg, type) => window.showToast ? window.showToast(msg, type || 'error') : alert(msg);
  if (!shopUsesApi()) {
    openContactForOrder();
    return;
  }
  if (window.shopConfig?.preview) {
    toast(tr('cart_preview_blocked'));
    return;
  }
  if (!validateBeforeSubmit(toast)) return;
  if (isGuestShop || !(await ensureShopLoginState())) {
    redirectGuestToLogin();
    return;
  }

  const btns = [document.getElementById('cart-btn'), document.getElementById('cart-btn-mobile')];
  const originalLabels = btns.map(b => b?.textContent);
  btns.forEach(b => { if (b) { b.disabled = true; b.classList.add('is-loading'); } });

  try {
    const { res, data } = await shopApiFetch('/api/cart', {
      method: 'POST',
      body: buildSubmitPayload(),
    });
    if (res.status === 401) { window.location.href = guestLoginUrl(); return; }
    if (res.ok && data.item) {
      toast(tr('cart_added'), 'success');
      if (typeof window.updateCartBadge === 'function') window.updateCartBadge(data.count);
    } else {
      toast(tr('save_failed') + shopApiErrorMessage(data, res));
    }
  } catch (err) {
    console.error(err);
    toast(tr('generic_error'));
  } finally {
    btns.forEach((b, i) => {
      if (b) {
        b.disabled = false;
        b.textContent = originalLabels[i];
        b.classList.remove('is-loading');
      }
    });
    updateSummary();
  }
}

async function handleCartUpdate() {
  const toast = (msg, type) => window.showToast ? window.showToast(msg, type || 'error') : alert(msg);
  if (!validateBeforeSubmit(toast)) return;

  const btns = [document.getElementById('confirm-btn'), document.getElementById('confirm-btn-mobile')];
  const originalLabels = btns.map(b => b?.textContent);
  btns.forEach(b => { if (b) { b.disabled = true; b.classList.add('is-loading'); } });

  try {
    const { res, data } = await shopApiFetch('/api/cart-item?id=' + encodeURIComponent(window.cartEditData.id), {
      method: 'PUT',
      body: Object.assign({ id: window.cartEditData.id }, buildSubmitPayload()),
    });
    if (res.status === 401) { window.location.href = guestLoginUrl(); return; }
    if (res.ok && data.item) {
      toast(tr('cart_updated'), 'success');
      if (typeof window.updateCartBadge === 'function') window.updateCartBadge(data.count);
      const params = new URLSearchParams(window.location.search);
      if (params.get('returnTo') === 'checkout') {
        const items = params.get('items') || window.cartEditData.id;
        const base = window.shopConfig?.checkoutUrl || '/checkout';
        window.location.href = base + '?items=' + encodeURIComponent(items);
        return;
      }
      window.location.href = window.shopConfig?.cartUrl || '/cart';
    } else {
      toast(tr('save_failed') + shopApiErrorMessage(data, res));
    }
  } catch (err) {
    console.error(err);
    toast(tr('generic_error'));
  } finally {
    btns.forEach((b, i) => {
      if (b) {
        b.disabled = false;
        b.textContent = originalLabels[i];
        b.classList.remove('is-loading');
      }
    });
    updateSummary();
  }
}

async function handleOrderUpdate() {
  const toast = (msg, type) => window.showToast ? window.showToast(msg, type || 'error') : alert(msg);
  if (!validateBeforeSubmit(toast)) return;

  const edit = window.editData;
  if (!edit?.orderId && !edit?.orderNumber) {
    toast(tr('generic_error'));
    return;
  }

  const btns = [document.getElementById('confirm-btn'), document.getElementById('confirm-btn-mobile')];
  const originalLabels = btns.map(b => b?.textContent);
  btns.forEach(b => { if (b) { b.disabled = true; b.textContent = tr('btn_submitting'); b.classList.add('is-loading'); } });

  try {
    const body = Object.assign({}, buildSubmitPayload(), {
      orderId: edit.orderId,
      orderNumber: edit.orderNumber,
    });
    const { res, data } = await shopApiFetch('/api/order', { method: 'PUT', body });
    if (res.status === 401) { window.location.href = guestLoginUrl(); return; }
    if (res.ok && data.ok) {
      toast(tr('order_updated'), 'success');
      window.location.href = orderSuccessUrl(data.orderNumber || edit.orderNumber, { updated: true });
      return;
    }
    toast(tr('save_failed') + shopApiErrorMessage(data, res));
  } catch (err) {
    console.error(err);
    toast(tr('generic_error'));
  } finally {
    btns.forEach((b, i) => {
      if (b) {
        b.disabled = false;
        b.textContent = originalLabels[i];
        b.classList.remove('is-loading');
      }
    });
    updateSummary();
  }
}

async function handleSubmit() {
  if (window.cartEditData) {
    return handleCartUpdate();
  }
  if (window.editData) {
    return handleOrderUpdate();
  }

  const toast = (msg) => window.showToast ? window.showToast(msg, 'error') : alert(msg);
  if (!shopUsesApi()) {
    openContactForOrder();
    return;
  }
  if (!validateBeforeSubmit(toast)) return;
  if (isGuestShop || !(await ensureShopLoginState())) {
    redirectGuestToLogin();
    return;
  }

  const btns = [document.getElementById("confirm-btn"), document.getElementById("confirm-btn-mobile")];
  const originalLabels = btns.map(b => b?.textContent);
  btns.forEach(b => { if (b) { b.disabled = true; b.textContent = tr('btn_submitting'); b.classList.add('is-loading'); } });
  const resetButtons = () => btns.forEach((b, i) => {
    if (b) { b.disabled = false; b.textContent = originalLabels[i]; b.classList.remove('is-loading'); }
  });

  const payload = buildSubmitPayload();

  try {
    const addResult = await shopApiFetch('/api/cart', { method: 'POST', body: payload });
    if (addResult.res.status === 401) { window.location.href = guestLoginUrl(); return; }
    if (!addResult.res.ok || !addResult.data.item) {
      resetButtons();
      toast(tr('save_failed') + shopApiErrorMessage(addResult.data, addResult.res));
      return;
    }

    const itemId = addResult.data.item.id;
    const checkoutUrl = window.shopConfig?.checkoutUrl || '/checkout';
    window.location.href = checkoutUrl + '?item=' + encodeURIComponent(itemId);
  } catch (err) {
    console.error(err);
    resetButtons();
    toast(tr('generic_error') + (err && err.message ? ': ' + err.message : ''));
  } finally {
    updateSummary();
  }
}

document.getElementById("confirm-btn")?.addEventListener("click", handleSubmit);
document.getElementById("confirm-btn-mobile")?.addEventListener("click", handleSubmit);
document.getElementById("cart-btn")?.addEventListener("click", handleAddToCart);
document.getElementById("cart-btn-mobile")?.addEventListener("click", handleAddToCart);
document.getElementById("quote-sheet-btn")?.addEventListener("click", openQuoteSheet);
document.getElementById("share-config-btn")?.addEventListener("click", openShareSummary);
document.getElementById("favorite-btn")?.addEventListener("click", addCurrentFavorite);

(function setupMobileBuyBarMetrics() {
  const bar = document.getElementById('mobile-buy-bar');
  if (!bar) return;

  const root = document.documentElement;
  const siteChrome = document.querySelector('.site-chrome');
  const mobileQuery = window.matchMedia('(max-width: 900px)');

  function syncMobileBuyBarHeight() {
    const isVisible =
      mobileQuery.matches &&
      !bar.classList.contains('hidden') &&
      window.getComputedStyle(bar).display !== 'none';
    const height = isVisible ? Math.ceil(bar.getBoundingClientRect().height) : 0;

    if (height > 0) {
      root.style.setProperty('--shop-mobile-buy-bar-height', `${height}px`);
    } else {
      root.style.removeProperty('--shop-mobile-buy-bar-height');
    }
  }

  function syncMobileSiteChromeHeight() {
    const height = siteChrome ? Math.ceil(siteChrome.getBoundingClientRect().height) : 0;
    if (height > 0) {
      root.style.setProperty('--shop-mobile-site-chrome-height', `${height}px`);
    } else {
      root.style.removeProperty('--shop-mobile-site-chrome-height');
    }
  }

  if (typeof ResizeObserver === 'function') {
    new ResizeObserver(syncMobileBuyBarHeight).observe(bar);
    if (siteChrome) {
      new ResizeObserver(syncMobileSiteChromeHeight).observe(siteChrome);
    }
  }

  new MutationObserver(() => {
    window.requestAnimationFrame(syncMobileBuyBarHeight);
  }).observe(bar, { attributes: true, attributeFilter: ['class'] });

  mobileQuery.addEventListener?.('change', syncMobileBuyBarHeight);
  window.addEventListener('resize', syncMobileBuyBarHeight, { passive: true });
  window.addEventListener('resize', syncMobileSiteChromeHeight, { passive: true });
  window.requestAnimationFrame(() => {
    syncMobileBuyBarHeight();
    syncMobileSiteChromeHeight();
  });
})();

(function setupMobileChatOffset() {
  const styleId = 'shop-mobile-buy-bar-chat-offset';

  function installChatOffsetStyle() {
    const shadowRoot = document.querySelector('.bpChatContainer > #fab-root')?.shadowRoot;
    if (!shadowRoot) return false;
    if (shadowRoot.getElementById(styleId)) return true;

    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
      @media (max-width: 900px) {
        #message-preview-root {
          bottom: calc(var(--shop-mobile-buy-bar-height, 0px) + 104px) !important;
          visibility: var(--shop-mobile-chat-visibility, visible) !important;
        }
      }
    `;
    shadowRoot.appendChild(style);
    return true;
  }

  installChatOffsetStyle();
  const pollId = window.setInterval(installChatOffsetStyle, 250);
  window.setTimeout(() => {
    installChatOffsetStyle();
    window.clearInterval(pollId);
  }, 15000);
})();

function resetMobilePriceSheet() {
  const details = document.getElementById('price-breakdown-details');
  const toggle = document.getElementById('mobile-price-toggle');
  const panel = document.getElementById('shop-price-panel');
  panel?.classList.remove('is-mobile-open');
  if (details) {
    delete details.dataset.userOpened;
    if (window.matchMedia('(max-width: 900px)').matches) details.open = false;
  }
  toggle?.setAttribute('aria-expanded', 'false');
}

(function setupMobilePricePanel() {
  const details = document.getElementById('price-breakdown-details');
  const toggle = document.getElementById('mobile-price-toggle');
  const panel = document.getElementById('shop-price-panel');
  const panelHead = panel?.querySelector('.shop-price-panel-head');

  function isMobileShop() {
    return window.matchMedia('(max-width: 900px)').matches;
  }

  function syncMobileChatVisibility() {
    const hideChat = isMobileShop() && panel?.classList.contains('is-mobile-open');
    if (hideChat) {
      document.documentElement.style.setProperty('--shop-mobile-chat-visibility', 'hidden');
    } else {
      document.documentElement.style.removeProperty('--shop-mobile-chat-visibility');
    }
  }

  function setMobileSheetOpen(willOpen) {
    if (!panel || !details) return;
    panel.classList.toggle('is-mobile-open', willOpen);
    if (willOpen) details.dataset.userOpened = '1';
    else delete details.dataset.userOpened;
    details.open = willOpen;
    toggle?.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
    syncMobileChatVisibility();
    if (willOpen) panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function syncDetailsOpen() {
    if (!details) return;
    if (!isMobileShop()) {
      details.open = true;
      panel?.classList.remove('is-mobile-open');
      toggle?.setAttribute('aria-expanded', 'false');
      syncMobileChatVisibility();
      return;
    }
    if (!details.dataset.userOpened) details.open = false;
    syncMobileChatVisibility();
  }

  syncDetailsOpen();
  window.addEventListener('resize', syncDetailsOpen);
  if (panel) {
    new MutationObserver(syncMobileChatVisibility).observe(panel, {
      attributes: true,
      attributeFilter: ['class'],
    });
  }

  toggle?.addEventListener('click', () => {
    if (!panel || !details) return;
    setMobileSheetOpen(!panel.classList.contains('is-mobile-open'));
  });

  panelHead?.addEventListener('click', (event) => {
    if (!isMobileShop() || !panel?.classList.contains('is-mobile-open')) return;
    if (event.target.closest('#mobile-price-toggle, .shop-cta, button, a')) return;
    setMobileSheetOpen(false);
  });
})();

function initCatalogFilterControls() {
  const ms = window.CatalogMultiFilter;
  if (ms) {
    ['catalog-metal-filter', 'catalog-price-filter', 'catalog-carat-filter'].forEach((id) => {
      const sel = document.getElementById(id);
      if (sel?.tagName === 'SELECT') ms.upgradeSelect(sel, { onChange: renderTypeCards });
    });
  } else {
    ['catalog-metal-filter', 'catalog-price-filter', 'catalog-carat-filter'].forEach((id) => {
      const element = document.getElementById(id);
      element?.addEventListener('change', renderTypeCards);
    });
  }
  document.getElementById('catalog-search-input')?.addEventListener('input', renderTypeCards);
}

function clearCatalogFilters() {
  const search = document.getElementById('catalog-search-input');
  if (search) search.value = '';
  if (window.CatalogMultiFilter) {
    window.CatalogMultiFilter.clearAll();
  } else {
    ['catalog-metal-filter', 'catalog-price-filter', 'catalog-carat-filter'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
  }
  renderTypeCards();
}

initCatalogFilterControls();
document.getElementById('catalog-filter-clear')?.addEventListener('click', clearCatalogFilters);
document.getElementById('catalog-filter-empty-clear')?.addEventListener('click', clearCatalogFilters);

document.addEventListener('langchange', () => {
  populateRingSizeSelect();
  updateMetalButtons();
  updateColorStep();
  updateChainOptions();
  renderCatalogTiles();
  renderDiamondShapeButtons();
  window.CatalogMultiFilter?.refreshAll();
  populateCatalogFilters({ keepSelection: true });
  const titleEl = document.getElementById("shop-category-title");
  if (titleEl && state.category) titleEl.textContent = tr('cat_' + state.category);
  updateSummary();
  if (state.category) renderTypeCards();
  if (shopView === 'product') updateLargeImage();
  updateShopProgress();
});

// ── Bootstrap: load the catalog first (type cards/images depend on it),
//    then wire up the initial view + optional deep-link/edit-mode restore. ─

function orderApiRowToEditConfig(o) {
  const type = o.product_id || o.product_type;
  const saved = (o.config_json && typeof o.config_json === 'object') ? o.config_json : {};
  const cfg = {
    orderId: o.id,
    orderNumber: o.order_number,
    category: o.category,
    type,
    gold: o.gold_purity,
    color: o.color,
    carat: o.carat,
    ringSize: o.ring_size,
    engravingBand: o.engraving_band || '',
    engravingRemark: o.engraving_remark || '',
    engravingGirdle: o.engraving_girdle || '',
    diamondKind: o.diamond_kind || 'white',
    fancyColor: o.fancy_color,
    stoneCount: o.stone_count,
    quantity: saved.quantity != null ? saved.quantity : (o.quantity != null ? o.quantity : 1),
    diamondShape: o.diamond_shape || 'round',
    includeChain: !!o.include_chain,
    chainGold: o.chain_gold,
    chainColor: o.chain_color,
    chainThickness: saved.chainThickness || null,
    chainProductId: saved.chainProductId || null,
  };
  if (o.category === 'chain') cfg.lengthCm = o.chain_length_cm;
  else cfg.chainLength = o.chain_length_cm;
  if (o.product_name) cfg.summaryZh = o.product_name;
  return cfg;
}

async function restoreShopConfig(cfg) {
  if (!cfg?.category || !cfg?.type) return;

  const typeId = cfg.category === 'diamond'
    ? resolveMemorialDiamondTypeRef(cfg.type)
    : String(cfg.type);
  state.category = cfg.category;
  state.type = typeId;

  document.querySelectorAll('.cat-btn').forEach((btn) =>
    btn.classList.toggle('active', btn.dataset.cat === cfg.category));

  const titleEl = document.getElementById('shop-category-title');
  if (titleEl) titleEl.textContent = tr('cat_' + cfg.category);

  await ensureCategoryCatalog(cfg.category);
  populateCatalogFilters({ keepSelection: false, category: cfg.category });
  await ensureProductDetail(typeId, cfg.category);
  ensureLiveGoldPolling();
  if (cfg.chainProductId) await ensureProductDetail(cfg.chainProductId, 'chain');

  renderTypeCards();
  document.querySelectorAll('.type-card').forEach((card) =>
    card.classList.toggle('active', card.dataset.type === typeId));

  updateCaratButtons();
  updateMetalButtons();

  if (cfg.carat) selectCarat(cfg.carat);
  if (cfg.gold) selectMetal(cfg.gold);
  if (cfg.color && needsColorSelection(cfg.gold, getSelectedProduct())) {
    selectColor(cfg.color);
  }

  state.engravingBand = cfg.engravingBand || '';
  state.engravingRemark = cfg.engravingRemark || '';
  state.engravingGirdle = cfg.engravingGirdle || '';
  state.lengthCm = cfg.lengthCm != null ? cfg.lengthCm : null;
  state.includeChain = !!cfg.includeChain;
  state.chainProductId = cfg.chainProductId || null;
  state.chainGold = cfg.chainGold || null;
  state.chainColor = cfg.chainColor || null;
  state.chainThickness = cfg.chainThickness || null;
  state.chainLength = cfg.chainLength != null ? cfg.chainLength : null;
  state.diamondKind = cfg.diamondKind || 'white';
  state.fancyColor = cfg.fancyColor || null;
  state.stoneCount = cfg.stoneCount || null;
  state.quantity = cfg.quantity != null ? cfg.quantity : 1;
  ensureStoneCountDefault();
  state.diamondShape = cfg.diamondShape || 'round';
  if (state.diamondShape !== 'round' && state.diamondShape !== 'other') {
    const restoredShape = nonRoundMatrixShapes().find((shape) => shape.id === state.diamondShape);
    if (!restoredShape) state.diamondShape = 'other';
  }

  if (cfg.category === 'ring') {
    applyProductRingSizeBounds(getSelectedProduct(), { selectDefault: false });
  }
  if (cfg.ringSize != null && cfg.ringSize !== '') {
    const restored = Math.round(Number(cfg.ringSize));
    if (Number.isFinite(restored) && restored < ringSizeMin) {
      ringSizeMin = restored;
      populateRingSizeSelect();
    }
    setRingSizeActive(cfg.ringSize);
  } else if (cfg.category === 'ring') {
    const start = productRingStartSize(getSelectedProduct());
    if (start != null) setRingSizeActive(start);
  }

  updateRingSizeStep();
  updateDiamondSteps();
  updateCaratButtons();
  updateEngravingSteps();
  await updateChainOptions();
  updateLengthStep();
  syncVariantChipActiveStates();
  productImageIndex = 0;
  updateLargeImage();
  setShopView('product', { skipScroll: true, history: 'replace' });
  updateSummary();
}

async function initCartEdit() {
  const cartId = new URLSearchParams(window.location.search).get('cart_edit');
  if (!cartId || window.editData) return;

  const toast = (msg, type) => window.showToast ? window.showToast(msg, type || 'error') : alert(msg);
  if (!shopUsesApi()) {
    toast('此頁面需登入後才能編輯購物車品項');
    return;
  }
  if (isGuestShop || !(await ensureShopLoginState())) {
    redirectGuestToLogin();
    return;
  }

  try {
    const { res, data } = await shopApiFetch('/api/cart-item?id=' + encodeURIComponent(cartId));
    if (res.status === 401) { window.location.href = guestLoginUrl(); return; }
    if (!res.ok || !data.item) {
      toast(data?.error || data?.message || '無法載入購物車品項');
      return;
    }
    const item = data.item;
    const cfg = Object.assign({}, item.config_json || {}, {
      category: item.category || item.config_json?.category,
      type: item.style_type || item.config_json?.type,
    });
    window.cartEditData = Object.assign({ id: String(item.id) }, cfg);
  } catch (err) {
    console.error(err);
    toast(tr('generic_error'));
  }
}

async function initOrderEdit() {
  const editOrderNo = new URLSearchParams(window.location.search).get('editOrder');
  if (!editOrderNo) return;

  const toast = (msg, type) => window.showToast ? window.showToast(msg, type || 'error') : alert(msg);
  if (!shopUsesApi()) {
    toast('此頁面需登入後才能修改訂單');
    return;
  }
  if (isGuestShop || !(await ensureShopLoginState())) {
    redirectGuestToLogin();
    return;
  }

  let cfg = null;
  try {
    const raw = sessionStorage.getItem('imprint_order_edit');
    if (raw) {
      const parsed = JSON.parse(raw);
      if (!parsed.orderNumber || parsed.orderNumber === editOrderNo) cfg = parsed;
    }
  } catch (_) {}

  if (!cfg) {
    try {
      const { res, data } = await shopApiFetch('/api/order?orderNumber=' + encodeURIComponent(editOrderNo));
      if (res.status === 401) { window.location.href = guestLoginUrl(); return; }
      if (!res.ok || !data.order) {
        toast(data.message || data.error || '無法載入訂單');
        return;
      }
      const o = data.order;
      if ((o.status || '').toLowerCase() !== 'received') {
        toast('僅「已收到申請」狀態的訂單可修改');
        return;
      }
      cfg = window.ImprintOrderDisplay?.orderToShopConfig?.(o) || orderApiRowToEditConfig(o);
    } catch (err) {
      console.error(err);
      toast(tr('generic_error'));
      return;
    }
  }

  window.editData = cfg;
  try { sessionStorage.removeItem('imprint_order_edit'); } catch (_) {}
}

async function bootShopCore() {
  initWizardRail();
  await initOrderEdit();
  await initCartEdit();
  await loadCatalog();
  initProductImageLightbox();
  initProductTabs();

  populateRingSizeSelect();
  loadMetalPrices();
  updateDiamondWizardChrome();
}

async function applyInitialShopState() {
  const prefillData = window.cartEditData || window.editData || window.prefillData || takeShopResumeSnapshot();
  const histReplace = { history: 'replace', skipScroll: true };
  if (prefillData) {
    await restoreShopConfig(prefillData);
  } else {
    setShopView('catalog', histReplace);
    updateWizardGuide();
  }

  const urlCategory = new URLSearchParams(window.location.search).get('category');
  const urlType = new URLSearchParams(window.location.search).get('type')
    || new URLSearchParams(window.location.search).get('product')
    || new URLSearchParams(window.location.search).get('series');
  if (urlCategory && productsFor(urlCategory).length && !prefillData) {
    if (urlCategory === 'diamond') {
      const typeId = urlType ? resolveMemorialDiamondTypeRef(urlType) : null;
      await selectCategory(urlCategory, {
        ...histReplace,
        ...(typeId ? { typeId } : {}),
      });
      if (typeId && productsFor('diamond').some((p) => String(p.id) === typeId) && state.type !== typeId) {
        await selectType(typeId, histReplace);
      }
    } else {
      await selectCategory(urlCategory, histReplace);
      if (urlType) {
        const typeId = urlType;
        if (productsFor(urlCategory).some((p) => p.id === typeId)) {
          await selectType(typeId, histReplace);
        }
      }
    }
  }

  const previewProduct = new URLSearchParams(window.location.search).get('product');
  if (window.shopConfig?.preview && previewProduct && urlCategory && !prefillData && !urlType) {
    if (productsFor(urlCategory).some((p) => p.id === previewProduct)) {
      await selectType(previewProduct, histReplace);
    }
  }
}

async function init() {
  if (window.ensureShopTermsAccepted) {
    const termsOk = await window.ensureShopTermsAccepted();
    if (!termsOk) return;
  }

  await bootShopCore();
  await applyInitialShopState();
  finishShopBoot();
}

// ── Onboarding tour (React shop-tour) — navigate real shop views, no mock page ─

function shopTourFirstCategory() {
  const cats = catalogLoaded ? catalogCategories() : [];
  return cats[0] || null;
}

function shopTourFirstTypeId() {
  const products = filteredProductsForCurrentCategory();
  const id = products[0]?.id;
  return id != null ? String(id) : null;
}

function shopTourScrollTop() {
  window.scrollTo(0, 0);
  document.querySelector('.shop-scroll')?.scrollTo(0, 0);
  document.querySelector('.shop-main')?.scrollTo(0, 0);
  document.querySelector('.product-buy-col')?.scrollTo(0, 0);
}

function shopTourScrollToProductConfig() {
  const run = () => {
    const layout = document.getElementById('product-layout');
    const buyCol = document.getElementById('product-buy-col');
    const productSection = document.getElementById('shop-product');
    if (!layout || !buyCol || productSection?.classList.contains('hidden')) return false;

    const gallery = layout.querySelector('.product-gallery-col');
    let scrollTop = buyCol.offsetTop;
    if (gallery && buyCol.offsetParent === layout) {
      scrollTop = buyCol.offsetTop;
    } else if (gallery) {
      scrollTop = gallery.offsetHeight + (parseFloat(getComputedStyle(layout).gap) || 0);
    }

    layout.scrollTop = Math.max(0, scrollTop - 4);

    const section = document.getElementById('shop-product');
    if (section && section.scrollHeight > section.clientHeight + 1) {
      const top =
        buyCol.getBoundingClientRect().top -
        section.getBoundingClientRect().top +
        section.scrollTop;
      section.scrollTop = Math.max(0, top - 4);
    }

    buyCol.scrollTop = 0;
    window.dispatchEvent(new Event('resize'));
    return true;
  };

  run();
  requestAnimationFrame(run);
  [120, 350, 600, 900].forEach((ms) => window.setTimeout(run, ms));
}

function shopTourCloseMobilePrice() {
  document.getElementById('shop-price-panel')?.classList.remove('is-mobile-open');
  const toggle = document.getElementById('mobile-price-toggle');
  if (toggle) toggle.setAttribute('aria-expanded', 'false');
}

function shopTourGoToStep(stepIndex) {
  shopTourCloseMobilePrice();
  if (stepIndex <= 1) {
    setShopView('catalog', { skipScroll: true });
    shopTourScrollTop();
    return;
  }
  if (stepIndex === 2) {
    const cat = state.category || shopTourFirstCategory();
    if (!cat) {
      setShopView('catalog', { skipScroll: true });
      shopTourScrollTop();
      return;
    }
    if (cat === 'diamond') {
      if (shopView !== 'product') selectCategory(cat);
      else setShopView('product', { skipScroll: true });
      shopTourScrollToProductConfig();
      return;
    }
    if (shopView !== 'styles' || state.category !== cat) selectCategory(cat);
    else setShopView('styles', { skipScroll: true });
    shopTourScrollTop();
    return;
  }
  const cat = state.category || shopTourFirstCategory();
  if (!cat) {
    setShopView('catalog', { skipScroll: true });
    shopTourScrollTop();
    return;
  }
  if (!state.category) selectCategory(cat);
  const typeId = state.type || shopTourFirstTypeId();
  if (typeId && (shopView !== 'product' || state.type !== typeId)) selectType(typeId);
  else setShopView('product', { skipScroll: true });
  if (stepIndex === 3) shopTourScrollToProductConfig();
  else shopTourScrollTop();
}

function shopTourReset() {
  state.category = null;
  state.type = null;
  document.querySelectorAll('.cat-btn.active, .type-card.active').forEach((el) => {
    el.classList.remove('active');
  });
  setShopView('catalog', { skipScroll: true });
  updateSummary();
}


window.shopTour = {
  isReady() {
    const grid = document.getElementById('catalog-grid');
    return !!(grid && !grid.classList.contains('is-loading') && grid.querySelector('.catalog-tile'));
  },
  goToStep: shopTourGoToStep,
  scrollToProductConfig: shopTourScrollToProductConfig,
  reset: shopTourReset,
};

init();
