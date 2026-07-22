function tr(k) { return window.t ? window.t(k) : k; }
function shopLang() { return localStorage.getItem('appLang') || 'zh'; }

const shopMode = (window.shopConfig && window.shopConfig.mode) || 'order';
const isGuestShop = shopMode === 'guest';

/* ponytail: shopConfig.mode is never actually set to 'guest' anywhere in the
   app (checked — only calculator.html sets it, always to 'order'), so
   isGuestShop above is permanently false. Real login state has to come from
   the session endpoint instead. shopIsLoggedIn stays null (unknown) until
   that resolves, so the UI doesn't flash a wrong state for logged-in users. */
let shopIsLoggedIn = null;
function refreshShopLoginState() {
  shopApiFetch('/api/auth/session').then(({ data }) => {
    shopIsLoggedIn = !!(data && data.user);
    updateSummary();
  }).catch(() => { shopIsLoggedIn = true; }); // fail open — don't block checkout on a network hiccup
}

if (new URLSearchParams(window.location.search).get('preview') === '1') {
  window.shopConfig = Object.assign({}, window.shopConfig || {}, { preview: true, useApi: true });
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

/** ponytail: FastAPI has /api/catalog but not /api/prices|quote yet — use bundled calculator math when present. */
function shopUsesLocalPricing() {
  return Boolean(window.ShopPricingLocal?.computeOrderPricing);
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
      engravingGirdle: state.engravingGirdle,
      lengthCm: state.lengthCm,
      includeChain: state.includeChain,
      chainProductId: state.chainProductId,
      chainGold: state.chainGold,
      chainColor: state.chainColor,
      chainLength: state.chainLength,
      diamondKind: state.diamondKind,
      fancyColor: state.fancyColor,
      stoneCount: state.stoneCount,
      diamondShape: state.diamondShape,
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
  const base = (window.shopConfig && window.shopConfig.loginUrl) || '/login.html';
  const returnTo = window.location.pathname + window.location.search + window.location.hash;
  const sep = base.indexOf('?') === -1 ? '?' : '&';
  saveShopResumeSnapshot();
  return base + sep + 'next=' + encodeURIComponent(returnTo);
}

function orderSuccessUrl(orderNumber, options) {
  const base = (window.shopConfig && window.shopConfig.successUrl) || '/success.html';
  const params = new URLSearchParams();
  if (orderNumber) params.set('order', String(orderNumber));
  if (options && options.updated) params.set('updated', '1');
  const qs = params.toString();
  return qs ? base + '?' + qs : base;
}

function redirectGuestToLogin() {
  window.location.href = guestLoginUrl();
}

async function shopApiFetch(path, options = {}) {
  const res = await fetch(shopApiBase() + path, {
    method: options.method || 'GET',
    credentials: 'include',
    headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const text = await res.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch (_) { data = { error: text.slice(0, 200) }; }
  return { res, data };
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

function mergeProductWeights(product, staticProduct, category) {
  if (!staticProduct?.weights) return;
  // ponytail: DB may still store legacy 金重; static catalog is 蠟重. Prefer static until migrate_wax_weights runs.
  // upgrade: migrate DB weight_chin to wax, then fill-only-null merge is enough.
  void category;
  product.weights = {};
  for (const [gold, carats] of Object.entries(staticProduct.weights)) {
    product.weights[gold] = { ...carats };
  }
  if (Array.isArray(staticProduct.golds) && staticProduct.golds.length) {
    product.golds = [...staticProduct.golds];
  } else {
    product.golds = sortGolds(Object.keys(product.weights));
  }
}

function enrichCatalogFromStatic() {
  const staticCats = window.shopCatalogData?.categories;
  if (!staticCats || !catalog) return;
  for (const [category, products] of Object.entries(catalog)) {
    const staticList = staticCats[category];
    if (!staticList) continue;
    for (const product of products) {
      const staticProduct = findStaticCatalogProduct(category, product);
      if (!staticProduct) continue;
      product.golds = productGolds(category, product);
      mergeProductWeights(product, staticProduct, category);
    }
  }
  if (staticCats.chain) {
    catalog.chain = catalog.chain || [];
    for (const staticChain of staticCats.chain) {
      const staticKey = String(staticChain.styleKey || staticChain.id);
      const exists = catalog.chain.some((p) => {
        const apiKey = String(p.styleKey || p.id);
        if (apiKey === staticKey) return true;
        const match = findStaticCatalogProduct('chain', p);
        return match && String(match.id) === String(staticChain.id);
      });
      if (!exists) catalog.chain.push({ ...staticChain });
    }
    catalog.chain.sort(compareChainStyleOrder);
  }
  injectDiamondCatalog();
}

function injectDiamondCatalog() {
  const staticDiamond = window.shopCatalogData?.categories?.diamond;
  if (!staticDiamond?.length) return;
  catalog.diamond = staticDiamond.map((p) => ({ ...p, images: { ...(p.images || {}) } }));
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

// Which carat-unit system each category uses (ct vs chain's 分). Kept as a
// display/UI hint; the actual selectable set per listing comes from the
// catalog (a listing only offers the carats it has variants for).
const CATEGORY_CARAT_UNIT = {
  diamond: 'ct', pendant: 'ct', ring: 'ct', earring: 'ct', bracelet: 'ct', chain: 'fen',
};
const CATEGORY_DISPLAY_ORDER = ['diamond', 'pendant', 'ring', 'earring', 'bracelet', 'chain'];

// ── Live catalog data (from /api/catalog) — replaces the old hardcoded
//    CATEGORY_STYLES / STYLE_NAMES / CATEGORY_METALS / WEIGHT_TABLE. ───────
let catalog = {};          // { category: [ {id, nameZh, nameEn, defaultColor, golds, carats, colors, images, weights, manualPrices}, ... ] }
let catalogLoaded = false;

function productsFor(category) {
  const list = catalog[category] || [];
  if (category !== 'chain' || list.length < 2) return list;
  return [...list].sort(compareChainStyleOrder);
}

function catalogCategories() {
  const present = Object.keys(catalog).filter(cat => productsFor(cat).length > 0);
  const preferred = (window._catalogCategoryOrder && window._catalogCategoryOrder.length)
    ? window._catalogCategoryOrder
    : CATEGORY_DISPLAY_ORDER;
  const ordered = preferred.filter(cat => present.includes(cat));
  return ordered.concat(present.filter(cat => !ordered.includes(cat)));
}

function getProduct(category, typeId) {
  if (!category || typeId == null) return null;
  return productsFor(category).find(p => String(p.id) === String(typeId)) || null;
}

function getSelectedProduct() {
  return getProduct(state.category, state.type);
}

function productName(product) {
  if (!product) return '';
  return shopLang() === 'en' ? (product.nameEn || product.nameZh) : product.nameZh;
}

function materialColor(gold) {
  return (METAL_COLORS[gold] || []).length === 1 ? METAL_COLORS[gold][0] : 'white';
}

function materialLabel(gold, color) {
  return tr(METAL_MATERIAL_LABELS[`${gold}:${color || materialColor(gold)}`] || `metal_${gold}`);
}

function availableColorsForGold(gold, product) {
  const metalColors = METAL_COLORS[gold];
  if (metalColors?.length) return [...metalColors];
  return ['white'];
}

function needsColorSelection(gold, product) {
  // Chain SKUs lock metal color via style pick (A white / B rose / C yellow)
  if (isColorLockedChainProduct(product)) return false;
  return !!(gold && GOLD_COLOR_METALS.includes(gold));
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
  const fromImages = styleKeyFromProductImages(product);
  if (fromImages) return fromImages;
  if (product.styleKey && /^[a-z]+-[A-C]$/i.test(String(product.styleKey))) {
    return String(product.styleKey);
  }
  const id = String(product.id || '');
  if (/^[a-z]+-[A-C]$/i.test(id)) return id;
  return '';
}

/** Pick catalog image URLs for exact slot keys (no legacy metal-only fallback). */
function catalogImagesForKeys(product, keys) {
  if (!product?.images || !keys?.length) return [];
  const pick = (key) => {
    const val = product.images[key];
    if (Array.isArray(val)) return val.filter(Boolean);
    if (typeof val === 'string' && val) return [val];
    return [];
  };
  for (const key of keys) {
    const list = pick(key);
    if (list.length) return list;
  }
  return [];
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
  return /_(?:only|chain)\.[a-z0-9]+$/i.test(String(url || '')) || /\/thumbs\//.test(String(url || ''));
}

function pendantWithChainImageUrl(product, pendantMetal, chainMetal, diamond) {
  const assetId = productAssetId(product);
  if (!assetId || !window.ShopAssets) return '';
  if (window.ShopAssets.productImageResolve) {
    const resolved = window.ShopAssets.productImageResolve(
      assetId,
      pendantMetal,
      product?.defaultColor,
      diamond,
      { chainColor: chainMetal },
    );
    return resolved.src || '';
  }
  if (!window.ShopAssets.productImage) return '';
  return window.ShopAssets.productImage(
    assetId,
    pendantMetal,
    product?.defaultColor,
    diamond,
    { chainColor: chainMetal },
  ) || '';
}

function pendantPreviewLayers(product) {
  const diamond = selectedDiamondColorId();
  const metal = previewColor();
  const opts = pendantPreviewImageOpts();

  if (usesPendantCompositePreview()) {
    const chainMetal = previewChainMetalForImage();
    const combo = pendantWithChainImageUrl(product, metal, chainMetal, diamond);
    if (combo && !isPendantLayerAssetUrl(combo)) {
      return { composite: false, src: combo, pendantOnly: false };
    }
    const composite = pendantCompositeFallback(product);
    if (composite) return composite;
  }

  const src = productImagesForColor(product, metal, diamond, opts)[0]
    || productImageUrl(product, metal, diamond, opts);
  return { composite: false, src, pendantOnly: opts.pendantOnly };
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
  if (!pendantOnly && state.category === 'pendant' && state.includeChain) {
    imageOpts.chainColor = opts.chainColor || previewChainMetalForImage();
  }
  const assetId = productAssetId(product);
  const compoundKey = window.ShopAssets?.buildImageSlotKey
    ? window.ShopAssets.buildImageSlotKey(metal, diamond)
    : (diamond !== 'white' ? `${metal}-${diamond}` : `${metal}-white`);

  // Shop-product PNGs (incl. cross-metal chain combos) must win over admin
  // catalog slots — those are often metal-only and hide rose-chain / fancy renders.
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

  // Admin-uploaded compound slot (e.g. white-pink) — only after shop-product miss.
  if (!pendantOnly && diamond !== 'white') {
    const fromCompound = catalogImagesForKeys(product, [compoundKey]);
    if (fromCompound.length) return fromCompound;
  }

  // White diamond: catalog metal slots, then any legacy upload.
  if (diamond === 'white') {
    const metalKeys = window.ShopAssets?.imageSlotKeysForLookup
      ? window.ShopAssets.imageSlotKeysForLookup(metal, 'white')
      : [metal, `${metal}-white`];
    const fromMetal = catalogImagesForKeys(product, metalKeys);
    if (fromMetal.length) return fromMetal;
    for (const key of [product?.defaultColor, 'white']) {
      const list = catalogImagesForKeys(product, [key]);
      if (list.length) return list;
    }
    if (product?.images) {
      for (const list of Object.values(product.images)) {
        const normalized = Array.isArray(list) ? list.filter(Boolean) : (list ? [list] : []);
        if (normalized.length) return normalized;
      }
    }
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
  const assetId = productAssetId(product);
  if (assetId && window.ShopAssets) return window.ShopAssets.styleThumb(assetId);
  return '';
}

function categoryImageUrl(category) {
  return window.ShopAssets?.categoryThumb(category) || '';
}

function applyStaticCatalogFallback() {
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
  document.getElementById('catalog-empty')?.classList.add('hidden');
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
    const catalogPath = window.shopConfig?.preview ? '/api/catalog?preview=1' : '/api/catalog';
    const { res, data } = await shopApiFetch(catalogPath);
    if (!res.ok) throw new Error(`API ${res.status}`);
    catalog = data.categories || {};
    window._catalogCategoryOrder = data.categoryOrder || null;
    enrichCatalogFromStatic();
    if (!catalogCategories().length && applyStaticCatalogFallback()) {
      if (errEl) errEl.remove();
      requestAnimationFrame(() => renderCatalogTiles());
      return;
    }
    catalogLoaded = true;
    if (errEl) errEl.remove();
    if (!catalogCategories().length) {
      throw new Error('CATALOG_EMPTY');
    }
    requestAnimationFrame(() => renderCatalogTiles());
  } catch (err) {
    if (shopUsesApi() && applyStaticCatalogFallback()) {
      if (errEl) errEl.remove();
      requestAnimationFrame(() => renderCatalogTiles());
      return;
    }
    catalogLoaded = false;
    catalog = {};
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
    return;
  }

  const cats = catalogCategories();
  empty?.classList.toggle('hidden', cats.length > 0);
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
    img.loading = 'lazy';
    img.alt = '';
    img.src = categoryImageUrl(cat) || (products[0] ? styleGridImageUrl(products[0]) : '');
    window.ShopAssets?.attachImageFallback(img, categoryImageUrl(cat));

    const label = document.createElement('span');
    label.textContent = tr('cat_' + cat);

    btn.appendChild(img);
    btn.appendChild(label);
    btn.addEventListener('click', () => selectCategory(cat));
    grid.appendChild(btn);
  });
  grid.classList.remove('is-loading');
  grid.setAttribute('aria-busy', 'false');
}

// Weight/pricing constants loaded from /api/prices (server is source of truth)
let laborFeeTwd = 5000;
let chinToGrams = 3.75;
let taxRate = 0.05;
let ringSizeMin = 5;
let ringSizeMax = 18;
let ringSizeReference = {};

// ── Live price data (from /api/prices) ────────────────────────────────────

let diamondPrice = { "0.1": null, "0.3": null, "0.5": null, "1.0": null };
let diamondOptions = {
  diamondColors: [],
  kinds: [],
  fancyColors: [],
  shapes: [],
  stoneCounts: [2, 3, 4],
  stoneCountCategories: ['earring'],
  fancyMinCarat: 0.3,
  nonRoundShapeMinCarat: 0.3,
  nonRoundShapeSurcharge: 0.10,
  defaultStoneCountByCategory: { earring: 2, ring: 2, pendant: 2 },
};
let pricePerGram = {};  // filled by loadMetalPrices()
let pricesLoaded = false;
let quoteTimer = null;
let quoteRequestId = 0;
let productImageIndex = 0;

// ── State ──────────────────────────────────────────────────────────────────

let state = {
  category: null,   // pendant / ring / earring / bracelet / chain
  type: null,       // Product id (string)
  gold: null,       // 9k / 14k / 18k / pt950 / s925
  color: null,      // white / yellow / rose / null
  carat: null,      // 0.1 / 0.3 / 0.5 / 1.0 / 3fen / 4fen
  ringSize: null,   // integer 5–18
  engravingBand: '',
  engravingGirdle: '',
  lengthCm: null,
  includeChain: false,
  chainProductId: null,
  chainGold: null,
  chainColor: null,
  chainLength: null,
  diamondKind: 'white',
  fancyColor: null,
  stoneCount: null,
  diamondShape: 'round',
};

function isDiamondOnlyCategory(category = state.category) {
  return category === 'diamond';
}

let shopView = 'catalog';
const CHAIN_LENGTH_OPTIONS_CM = [35, 40, 46, 50, 56, 60, 66, 70, 76, 90, 102];
const CHAIN_REFERENCE_LENGTH_CM = 45;
const BRACELET_LENGTH_OPTIONS_CM = [15, 16, 17, 18, 19, 20, 21];
const BRACELET_REFERENCE_LENGTH_CM = 18;

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

function setShopView(view, options) {
  const opts = options || {};
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
  const skipScroll = opts.skipScroll || document.documentElement.classList.contains('shop-tour-active');
  if (!skipScroll) {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

const SHOP_STEPS = {
  catalog: { step: 1, progress: 12 },
  styles: { step: 2, progress: 50 },
  product: { step: 3, progress: 100 },
};

// ponytail: diamond category skips step 2 (style grid); upgrade = separate memorial-series picker if needed
const DIAMOND_SHOP_STEPS = {
  catalog: { step: 1, progress: 50 },
  styles: { step: 1, progress: 50 },
  product: { step: 2, progress: 100 },
};

const DIAMOND_LOOSE_PRODUCT_ID = 'diamond-loose';
const DIAMOND_WHITE_PREVIEW_PATH = 'diamonds/colors/white.png';

function activeShopSteps() {
  return isDiamondOnlyCategory() ? DIAMOND_SHOP_STEPS : SHOP_STEPS;
}

function diamondLooseProductId() {
  const list = productsFor('diamond');
  if (list.some((p) => p.id === DIAMOND_LOOSE_PRODUCT_ID)) return DIAMOND_LOOSE_PRODUCT_ID;
  return list[0]?.id || null;
}

function updateDiamondWizardChrome() {
  const isDiamond = state.category === 'diamond';
  const stylesStep = document.getElementById('wizard-step-styles');
  const backBtn = document.getElementById('back-to-styles');
  if (stylesStep) stylesStep.hidden = isDiamond;
  if (backBtn) {
    backBtn.textContent = isDiamond ? tr('shop_back_catalog') : tr('shop_back_styles');
  }
}

function enterDiamondLooseProduct() {
  const typeId = diamondLooseProductId();
  if (!typeId) {
    setShopView('styles');
    renderTypeCards();
    updateSummary();
    return;
  }
  selectType(typeId);
}

const WIZARD_GUIDE = {
  catalog: {
    eyebrow: '線上訂製 · 三步完成',
    title: '先選擇您要的品項',
    desc: '戒指、項墜、耳飾、手鍊或鍊條——點選一個類別即可開始。',
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
  const copy = WIZARD_GUIDE[shopView] || WIZARD_GUIDE.catalog;
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

  document.querySelectorAll('.shop-stepper-step').forEach((btn) => {
    const step = btn.dataset.step;
    if (step === 'styles' && state.category === 'diamond') return;
    const stepNum = steps[step]?.step || 0;
    const current = meta.step;
    btn.classList.toggle('is-active', step === shopView);
    btn.classList.toggle('is-done', stepNum < current);
    btn.disabled = stepNum > current;
    if (step === 'catalog') btn.disabled = false;
    if (step === 'styles') btn.disabled = !state.category || state.category === 'diamond';
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
    if (!state.category || state.category === 'diamond') return;
    if (shopView === 'product') document.getElementById('back-to-styles')?.click();
    else if (shopView === 'catalog') selectCategory(state.category);
  });
  document.getElementById('wizard-step-product')?.addEventListener('click', () => {
    if (!state.type) return;
    if (shopView !== 'product') {
      const card = document.querySelector(`.type-card[data-type="${state.type}"]`);
      if (card) card.click();
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
          if (isDiamondOnlyCategory()) {
            document.getElementById('back-to-catalog')?.click();
          } else {
            document.getElementById('back-to-styles')?.click();
          }
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
    title.textContent = productName(product);
    if (subtitle) {
      let sub = tr('cat_' + state.category);
      const badge = stoneCountBadgeText();
      if (badge) sub = `${sub} · ${badge}`;
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
  if (state.carat && state.category !== 'chain') {
    chips.push(
      state.carat === '3fen' ? tr('chain_3fen')
        : state.carat === '4fen' ? tr('chain_4fen')
          : state.carat + ' ct'
    );
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
  chips.forEach(text => {
    const span = document.createElement('span');
    span.className = 'config-chip';
    span.textContent = text;
    container.appendChild(span);
  });
  if (state.engravingGirdle) {
    const span = document.createElement('span');
    span.className = 'config-chip config-chip--engrave';
    const label = tr('step_engraving_girdle') + ': ';
    if (window.GirdleEngrave && window.GirdleEngrave.toDisplayHtml) {
      span.innerHTML = label.replace(/&/g, '&amp;').replace(/</g, '&lt;') +
        window.GirdleEngrave.toDisplayHtml(state.engravingGirdle);
    } else {
      span.textContent = label + state.engravingGirdle;
    }
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

function isReadyToSubmit() {
  if (!state.category || !state.type || !state.carat) return false;
  if (!isDiamondOnlyCategory() && !state.gold) return false;
  const product = getSelectedProduct();
  if (!isDiamondOnlyCategory() && state.gold && needsColorSelection(state.gold, product) && !state.color) return false;
  if (state.category === 'ring' && !state.ringSize) return false;
  if (state.category === 'chain' && !state.lengthCm) return false;
  if (state.category === 'bracelet' && !state.lengthCm) return false;
  if (state.category !== 'chain' && state.diamondKind === 'fancy' && !state.fancyColor) return false;
  if (state.category === 'pendant' && state.includeChain
    && (!state.chainProductId || !state.chainGold || !state.chainColor || !state.chainLength)) return false;
  if (state.category === 'chain' && state.gold === '9k') {
    const chainProduct = getSelectedProduct();
    if (chainProduct && chainProduct.defaultColor !== 'white') return false;
  }
  return true;
}

function missingSubmitLabels() {
  const missing = [];
  if (!state.category) missing.push(tr('step_category'));
  if (!state.type) missing.push(tr('sum_style'));
  if (!isDiamondOnlyCategory()) {
    if (!state.gold) missing.push(tr('step_metal'));
    else {
      const product = getSelectedProduct();
      if (needsColorSelection(state.gold, product) && !state.color) missing.push(tr('step_color'));
    }
  }
  if (!state.carat) missing.push(tr('step_carat'));
  if (state.category === 'ring' && !state.ringSize) missing.push(tr('step_ring_size'));
  if (state.category === 'chain' && !state.lengthCm) missing.push(tr('step_chain_length'));
  if (state.category === 'bracelet' && !state.lengthCm) missing.push(tr('step_bracelet_length'));
  if (state.category !== 'chain' && state.diamondKind === 'fancy' && !state.fancyColor) {
    missing.push(tr('step_diamond_color'));
  }
  if (state.category === 'pendant' && state.includeChain) {
    if (!state.chainProductId || !state.chainGold || !state.chainColor || !state.chainLength) {
      missing.push(tr('step_pendant_chain'));
    }
  }
  return missing;
}

function updatePriceHint(total) {
  const hint = document.getElementById('price-hint');
  if (!hint) return;
  const optionsReady = isReadyToSubmit();
  const canOrder = optionsReady && (total != null || !shopUsesApi());
  if (canOrder) {
    hint.hidden = true;
    return;
  }
  hint.hidden = false;
  const missing = missingSubmitLabels();
  if (missing.length) {
    hint.textContent = `${tr('shop_complete_missing')}：${missing.join('、')}`;
  } else if (total == null) {
    hint.textContent = tr('shop_price_unavailable');
  } else {
    hint.textContent = tr('shop_complete_options');
  }
}

function updateCtaState(total) {
  const optionsReady = isReadyToSubmit();
  const ready = optionsReady && (total != null || !shopUsesApi());

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
      btn.disabled = !ready;
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
      btn.disabled = !ready;
      btn.textContent = btn.id === 'confirm-btn-mobile' ? tr('cart_update_short') : tr('cart_update');
    });
  } else if (isDiamondOnlyCategory()) {
    // Memorial loose diamonds: LINE consult (no API product variants yet)
    cartBtns.forEach(btn => {
      if (!btn) return;
      btn.hidden = true;
      btn.disabled = true;
    });
    confirmBtns.forEach(btn => {
      if (!btn) return;
      btn.hidden = false;
      btn.disabled = !ready;
      btn.textContent = tr('btn_line_consult');
    });
  } else {
    confirmBtns.forEach(btn => {
      if (!btn) return;
      btn.hidden = false;
      btn.disabled = !ready;
      if (window.editData) {
        btn.textContent = tr('btn_update');
      } else {
        btn.textContent = tr('btn_add_order');
      }
    });
    cartBtns.forEach(btn => {
      if (!btn) return;
      btn.hidden = false;
      btn.disabled = !ready || !!window.editData;
      btn.textContent = btn.id === 'cart-btn-mobile' ? tr('btn_add_cart_short') : tr('btn_add_cart');
    });
  }

  updatePriceHint(total);
  const bar = document.getElementById('mobile-buy-bar');
  const showMobileBar = !!state.category;
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

/** Step 2 style grid — always white-diamond preview; fancy color only on step 3 gallery. */
function styleGridImageUrl(product) {
  return productImageUrl(product, product?.defaultColor || 'white', 'white');
}

function imageUrl(category, type, metalColor, diamondColor) {
  return productImageUrl(
    getProduct(category, type),
    metalColor ?? previewColor(),
    diamondColor ?? selectedDiamondColorId(),
  );
}

// ── Metal price fetch ─────────────────────────────────────────────────────

async function loadMetalPrices() {
  const pricePanel = document.getElementById("shop-price-panel");
  pricePanel?.classList.add("is-loading-prices");
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
    if (data.chinToGrams != null) chinToGrams = data.chinToGrams;
    if (data.taxRate != null) taxRate = data.taxRate;
    if (data.ringSizeMin != null) ringSizeMin = data.ringSizeMin;
    if (data.ringSizeMax != null) ringSizeMax = data.ringSizeMax;
    ringSizeReference = data.ringSizeReference || {};
    if (data.diamondOptions) {
      diamondOptions = { ...diamondOptions, ...data.diamondOptions };
    }
    pricesLoaded = true;
    populateRingSizeSelect();
    renderRingSizeGuide();
    updateSummary();
    const initialData = window.cartEditData || window.editData || window.prefillData;
    if (initialData?.ringSize) {
      setRingSizeActive(initialData.ringSize);
    }
  } catch (err) {
    pricesLoaded = false;
    updateSummary();
  } finally {
    pricePanel?.classList.remove("is-loading-prices");
  }
}

/** Swaps the static per-gram estimate for the live BOT scrape once it's back;
 * re-renders the summary so an already-selected config picks up the real rate. */
async function loadLiveGoldRates() {
  try {
    const { res, data } = await shopApiFetch('/api/bot-gold');
    if (!res.ok || !data?.alloyRates) return;
    window.ShopPricingLocal?.setLiveGoldRates?.(data.alloyRates);
    Object.assign(pricePerGram, data.alloyRates);
    updateSummary();
  } catch (err) {
    console.error('failed to load live gold rates', err);
  }
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
      const waxFactor = window.ShopPricingLocal?.WAX_TO_METAL_CHIN?.[gold] ?? 1;
      const perChin = rate * chinToGrams;
      const metalChin = waxFactor * Number(waxChin);
      const metal = metalChin * perChin;
      estimates.push(diamond + metal * (1 + taxRate) + laborFeeTwd);
    });
  });
  return estimates.length ? Math.min(...estimates) : null;
}

function filteredProductsForCurrentCategory() {
  const query = (document.getElementById('catalog-search-input')?.value || '').trim().toLowerCase();
  const metal = document.getElementById('catalog-metal-filter')?.value || '';
  const priceBand = document.getElementById('catalog-price-filter')?.value || '';
  return productsFor(state.category).filter(product => {
    const names = `${product.nameZh || ''} ${product.nameEn || ''}`.toLowerCase();
    if (query && !names.includes(query)) return false;
    const golds = product.golds || [];
    if (metal && golds.length && !golds.includes(metal)) return false;
    if (priceBand) {
      const price = estimatedProductPrice(product);
      if (price == null) return false;
      if (priceBand === 'under30000' && price >= 30000) return false;
      if (priceBand === '30000to80000' && (price < 30000 || price > 80000)) return false;
      if (priceBand === 'over80000' && price <= 80000) return false;
    }
    return true;
  });
}

function renderTypeCards() {
  const grid = document.getElementById("type-grid");
  if (!grid) return;
  grid.innerHTML = "";
  const products = filteredProductsForCurrentCategory();
  products.forEach(product => {
    const styleId = String(product.id);
    const card = document.createElement("button");
    card.type = "button";
    card.className = "type-card";
    card.dataset.type = styleId;
    if (state.type === styleId) card.classList.add("active");

    const img = document.createElement("img");
    const imgSrc = styleGridImageUrl(product);
    img.src = imgSrc;
    img.alt = productName(product);
    img.loading = "lazy";
    window.ShopAssets?.attachImageFallback(img, window.ShopAssets.styleThumb(productAssetId(product) || styleId));

    const name = document.createElement("span");
    name.className = "type-name";
    name.textContent = productName(product);

    card.appendChild(img);
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
  document.getElementById('catalog-filter-empty')?.classList.toggle('hidden', products.length > 0);
}

function syncVariantChipActiveStates() {
  document.querySelectorAll('.carat-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.carat === state.carat));
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
  if (!needsColorSelection(gold, product)) return materialColor(gold);
  const colors = availableColorsForGold(gold, product);
  return colors.includes(color) ? color : (colors[0] || null);
}

function updateColorStep(goldOverride) {
  const product = getSelectedProduct();
  const step = document.getElementById('color-step');
  const row = document.getElementById('color-btn-row');
  if (!step) return;
  const gold = goldOverride ?? state.gold;
  const show = gold && needsColorSelection(gold, product);
  updateColorStepLabel('color-step-label', gold);
  step.classList.toggle('hidden', !show);
  // Chain never picks color — collapse the 2-col slot (visibility:hidden would leave a hole)
  step.classList.toggle('hidden-collapse', !show && isColorLockedChainProduct(product));
  if (!show) {
    if (gold) state.color = enforceMetalColor(gold, state.color, product);
    if (row) row.innerHTML = '';
    return;
  }
  step.classList.remove('hidden-collapse');
  state.color = enforceMetalColor(gold, state.color, product);
  renderColorButtons('color-btn-row', gold, product, state.color, selectColor);
}

function isCaratHiddenForShop(carat) {
  const value = parseFloat(String(carat));
  const minCarat = diamondOptions.fancyMinCarat || diamondOptions.nonRoundShapeMinCarat || 0.3;
  if (Number.isNaN(value)) return false;
  if (state.diamondKind === 'fancy' && value < minCarat) return true;
  if (state.diamondShape && state.diamondShape !== 'round' && value < minCarat) return true;
  return false;
}

function ensureChainCaratDefault() {
  if (state.category !== 'chain') return;
  const product = getSelectedProduct();
  const carats = product?.carats || [];
  if (!carats.length) return;
  // Chain has no user-facing carat/fen picker — keep one weight for metal pricing
  if (!state.carat || !carats.includes(state.carat)) {
    state.carat = carats[0];
  }
}

function updateCaratButtons() {
  const product = getSelectedProduct();
  const validCarats = product ? product.carats : [];
  const isChain = state.category === 'chain';
  document.getElementById('carat-step')?.classList.toggle('hidden', isChain);
  if (isChain) {
    ensureChainCaratDefault();
    updateDiamondSteps();
    return;
  }
  const row = document.getElementById('carat-btn-row');
  if (!row) return;
  row.innerHTML = '';
  validCarats.forEach((v) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'carat-btn variant-chip';
    btn.dataset.carat = v;
    const n = parseFloat(v);
    btn.textContent = Number.isNaN(n) ? v : `${n.toFixed(2)} ct`;
    const visible = !isCaratHiddenForShop(v);
    btn.style.display = visible ? '' : 'none';
    btn.disabled = !visible;
    btn.classList.toggle('active', v === state.carat);
    btn.addEventListener('click', () => selectCarat(v));
    row.appendChild(btn);
  });
  updateDiamondSteps();
}

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
  return `/static/images/${relativePath}?v=19`;
}

function diamondMatrixImagePath(shapeId, colorId) {
  const shape = shapeId || 'round';
  const color = colorId || 'white';
  return `diamonds/matrix/${shape}-${color}.png`;
}

function diamondMatrixImageUrl(shapeId, colorId) {
  return diamondAssetUrl(diamondMatrixImagePath(shapeId, colorId));
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

function isDiamondShapeChipActive(chipId) {
  const current = state.diamondShape || 'round';
  if (chipId === 'round') return current === 'round';
  if (chipId === 'other') return isNonRoundShape(current);
  return current === chipId;
}

function diamondShapeDisplayMeta(shapeId = state.diamondShape) {
  if (!shapeId || shapeId === 'round') return null;
  return nonRoundMatrixShapes().find((s) => s.id === shapeId)
    || diamondShapeOptions().find((s) => s.id === shapeId)
    || { id: shapeId, labelZh: shapeId, labelEn: shapeId };
}

function diamondShapeOptions() {
  if (isDiamondOnlyCategory()) {
    if (diamondOptions.matrixShapes?.length) return diamondOptions.matrixShapes;
    return [
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
  }
  if (diamondOptions.shapes?.length) return diamondOptions.shapes;
  return [
    { id: 'round', labelZh: '圓形明亮式', labelEn: 'Round' },
    { id: 'other', labelZh: '其它形狀', labelEn: 'Other (+10%)' },
  ];
}

function usesAutoStoneCount(category = state.category) {
  const cats = diamondOptions.stoneCountCategories || ['earring'];
  return cats.includes(category);
}

function usesStoneCountPicker(category = state.category) {
  return category === 'diamond';
}

function defaultStoneCountForCategory(category = state.category) {
  if (category === 'earring') return 2;
  if (category === 'diamond') return 1;
  return diamondOptions.defaultStoneCountByCategory?.[category] || 2;
}

function stoneCountBadgeText() {
  if (usesStoneCountPicker() && state.stoneCount && state.stoneCount > 1) {
    return tr('stone_count_badge').replace('{n}', String(state.stoneCount));
  }
  if (!usesAutoStoneCount() || !state.stoneCount) return null;
  return tr('stone_count_badge').replace('{n}', String(state.stoneCount));
}

function ensureStoneCountDefault() {
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

function diamondColorOptions() {
  if (diamondOptions.diamondColors?.length) return diamondOptions.diamondColors;
  return [
    { id: 'white', kind: 'white', labelZh: '白鑽', labelEn: 'White', swatch: '#e8e8e8', image: 'diamonds/colors/white.png' },
    ...(diamondOptions.fancyColors || []),
  ];
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
  carousel.innerHTML = '';
  const activeId = selectedDiamondColorId();
  diamondColorOptions().forEach(color => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'diamond-carousel-item fancy-color-item';
    btn.dataset.color = color.id;
    btn.classList.toggle('active', activeId === color.id);
    const icon = document.createElement('span');
    icon.className = 'gem-icon';
    const imagePath = color.image || DIAMOND_WHITE_PREVIEW_PATH;
    if (imagePath) {
      const img = document.createElement('img');
      img.src = diamondAssetUrl(imagePath);
      img.alt = diamondMetaLabel(color);
      img.loading = 'lazy';
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
  fancyStep?.classList.toggle('hidden', isChain);
  shapeStep?.classList.toggle('hidden', isChain);
  stoneStep?.classList.toggle('hidden', !isDiamond);
  if (isChain) {
    resetDiamondOptions();
    return;
  }
  renderDiamondColorCarousel();
  renderDiamondShapeButtons();
  renderStoneCountButtons();
  ensureStoneCountDefault();
  updateGirdlePreview();
}

function renderDiamondShapeButtons() {
  const row = document.getElementById('diamond-shape-row');
  if (!row) return;
  const shapes = diamondShapeOptions();
  const useMatrix = isDiamondOnlyCategory();
  row.classList.toggle('variant-chips--matrix-shapes', useMatrix);
  row.innerHTML = '';
  shapes.forEach((shape) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.dataset.shape = shape.id;
    const isActive = isDiamondShapeChipActive(shape.id);
    if (useMatrix) {
      btn.className = `diamond-carousel-item shape-item diamond-shape-btn${isActive ? ' active' : ''}`;
      const icon = document.createElement('span');
      icon.className = 'gem-icon';
      const img = document.createElement('img');
      img.src = diamondMatrixImageUrl(shape.id, selectedDiamondColorId());
      img.alt = diamondMetaLabel(shape);
      img.loading = 'lazy';
      icon.appendChild(img);
      const label = document.createElement('span');
      label.className = 'gem-label';
      label.textContent = diamondMetaLabel(shape);
      btn.appendChild(icon);
      btn.appendChild(label);
    } else {
      btn.className = `variant-chip diamond-shape-btn${isActive ? ' active' : ''}`;
      btn.textContent = diamondMetaLabel(shape);
      if (shape.id === 'round') {
        btn.textContent = shopLang() === 'en' ? 'Round Brilliant' : '圓形明亮式';
      } else if (shape.id === 'other') {
        btn.textContent = shopLang() === 'en' ? 'Other (+10%)' : '其它形狀 +10%';
      }
    }
    btn.addEventListener('click', () => selectDiamondShape(shape.id));
    row.appendChild(btn);
  });
  syncDiamondShapeOtherDropdown();
}

let diamondShapeOtherBound = false;

function bindDiamondShapeOtherSelect() {
  if (diamondShapeOtherBound) return;
  const select = document.getElementById('diamond-shape-other-select');
  if (!select) return;
  diamondShapeOtherBound = true;
  select.addEventListener('change', () => {
    if (select.value) selectDiamondShape(select.value);
  });
}

function syncDiamondShapeOtherDropdown() {
  bindDiamondShapeOtherSelect();
  const wrap = document.getElementById('diamond-shape-other-wrap');
  const select = document.getElementById('diamond-shape-other-select');
  if (!wrap || !select) return;

  if (isDiamondOnlyCategory()) {
    wrap.hidden = true;
    return;
  }

  const options = nonRoundMatrixShapes();
  const show = isNonRoundShape();
  wrap.hidden = !show;
  if (!show) return;

  select.innerHTML = '';
  options.forEach((shape) => {
    const opt = document.createElement('option');
    opt.value = shape.id;
    opt.textContent = diamondMetaLabel(shape);
    select.appendChild(opt);
  });
  const next = options.some((s) => s.id === state.diamondShape)
    ? state.diamondShape
    : (options[0]?.id || '');
  if (next) select.value = next;
}

function selectDiamondShape(shapeId) {
  if (shapeId === 'other') {
    if (!isNonRoundShape()) {
      state.diamondShape = nonRoundMatrixShapes()[0]?.id || 'oval';
    }
  } else {
    state.diamondShape = shapeId || 'round';
  }
  if (state.carat && isCaratHiddenForShop(state.carat)) {
    state.carat = null;
  }
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

function selectDiamondColor(colorId) {
  const meta = diamondColorOptions().find(c => c.id === colorId);
  if (!meta) return;
  if (meta.kind === 'white' || colorId === 'white') {
    state.diamondKind = 'white';
    state.fancyColor = null;
  } else {
    state.diamondKind = 'fancy';
    state.fancyColor = colorId;
    if (state.carat && isCaratHiddenForShop(state.carat)) {
      state.carat = null;
      document.querySelectorAll('.carat-btn').forEach(b => b.classList.remove('active'));
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
    chainLength: state.chainLength,
    diamondKind: state.diamondKind,
    fancyColor: state.fancyColor,
    stoneCount: state.stoneCount,
    diamondShape: state.diamondShape,
  };
}

async function fetchQuote() {
  const compute = window.ShopPricingLocal?.computeOrderPricing;
  if (compute && (shopUsesLocalPricing() || !shopUsesApi())) {
    return compute(buildQuotePayload(), catalog);
  }
  const id = ++quoteRequestId;
  try {
    const quotePath = window.shopConfig?.preview ? '/api/quote?preview=1' : '/api/quote';
    const { res, data } = await shopApiFetch(quotePath, {
      method: 'POST',
      body: buildQuotePayload(),
    });
    if (!res.ok) return null;
    return id === quoteRequestId ? data : null;
  } catch (err) {
    console.error('quote fetch failed', err);
    return null;
  }
}

function scheduleQuoteRefresh() {
  clearTimeout(quoteTimer);
  quoteTimer = setTimeout(() => { refreshQuotePrices(); }, 120);
}

async function refreshQuotePrices() {
  const pricePanel = document.getElementById('shop-price-panel');
  pricePanel?.classList.add('is-loading-prices');
  const quote = await fetchQuote();
  pricePanel?.classList.remove('is-loading-prices');
  const diamondRow = document.getElementById('sum-diamond-row');
  const chainRow = document.getElementById('sum-chain-row');
  const totalEl = document.getElementById('sum-total');
  const mobileTotal = document.getElementById('sum-total-mobile');
  const hint = document.getElementById('price-hint');

    if (!quote || !quote.ready) {
    if (quote && quote.error && window.showToast) {
      window.showToast(tr('price_unavailable'), 'error');
    } else if (isReadyToSubmit() && window.showToast) {
      window.showToast(tr('price_unavailable'), 'error');
    }
    if (diamondRow) diamondRow.style.display = state.category === 'chain' ? 'none' : '';
    chainRow?.classList.add('hidden');
    document.getElementById('sum-diamond-price').textContent = state.carat ? '-' : '0';
    document.getElementById('sum-metalwork-price').textContent = '-';
    const chainPriceEl = document.getElementById('sum-chain-price');
    if (chainPriceEl) chainPriceEl.textContent = '-';
    if (totalEl) totalEl.textContent = '—';
    if (mobileTotal) mobileTotal.textContent = '—';
    updatePriceHint(null);
    updateCtaState(null);
    return;
  }

  if (quote.manualOverride) {
    if (diamondRow) diamondRow.style.display = 'none';
    chainRow?.classList.add('hidden');
    document.getElementById('sum-metalwork-price').textContent = '—';
  } else {
    if (diamondRow) diamondRow.style.display = state.category === 'chain' ? 'none' : '';
    if (quote.diamondPrice != null) {
      document.getElementById('sum-diamond-price').textContent = Math.round(quote.diamondPrice).toLocaleString();
    }
    const metalworkRow = document.getElementById('sum-metalwork-price')?.closest('.summary-row');
    if (isDiamondOnlyCategory()) {
      metalworkRow?.classList.add('hidden');
      document.getElementById('sum-metalwork-price').textContent = '0';
    } else {
      metalworkRow?.classList.remove('hidden');
      const metalwork = quote.metalworkPrice != null
        ? quote.metalworkPrice
        : (quote.taijinPrice != null && quote.laborPrice != null ? quote.taijinPrice + quote.laborPrice : null);
      if (metalwork != null) {
        document.getElementById('sum-metalwork-price').textContent = Math.round(metalwork).toLocaleString();
      }
    }
    const showChain = state.category === 'pendant' && state.includeChain && quote.chainPrice != null;
    chainRow?.classList.toggle('hidden', !showChain);
    if (showChain) {
      document.getElementById('sum-chain-price').textContent = Math.round(quote.chainPrice).toLocaleString();
    }
  }

  const total = quote.total;
  if (total != null && window.animateCountUp) {
    if (totalEl) window.animateCountUp(totalEl, Math.round(total));
    if (mobileTotal) window.animateCountUp(mobileTotal, Math.round(total));
  } else {
    const totalStr = total != null ? Math.round(total).toLocaleString() : '—';
    if (totalEl) totalEl.textContent = totalStr;
    if (mobileTotal) mobileTotal.textContent = totalStr;
  }
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

function updateEngravingSteps() {
  const bandStep = document.getElementById('engraving-band-step');
  const girdleStep = document.getElementById('engraving-girdle-step');
  const hasBand = state.category === 'ring';
  const hasGirdle = state.category !== 'chain';
  bandStep?.classList.toggle('hidden', !hasBand);
  girdleStep?.classList.toggle('hidden', !hasGirdle);
  if (!hasBand) state.engravingBand = '';
  if (!hasGirdle) state.engravingGirdle = '';
  const bandInput = document.getElementById('engraving-band-input');
  if (bandInput) bandInput.value = state.engravingBand;
  const allowChinese = caratAllowsChineseEngraving();
  const girdleCtrl = ensureGirdleEngrave();
  if (girdleCtrl) {
    girdleCtrl.setAllowChinese(allowChinese);
    girdleCtrl.setValue(state.engravingGirdle || '');
    girdleCtrl.setPreviewShapeAndColor(state.diamondShape || 'round', selectedDiamondColorId() || 'white');
  }
  const hint = document.getElementById('shop-girdle-engrave-hint');
  if (hint) {
    const key = allowChinese ? 'engraving_girdle_hint_cjk' : 'engraving_girdle_hint';
    hint.setAttribute('data-i18n', key);
    hint.textContent = tr(key);
  }
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
    renderLengthSelect('chain-length-select', CHAIN_LENGTH_OPTIONS_CM, state.lengthCm, 'chain_length_placeholder');
  } else if (isBracelet) {
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

function updateChainOptions() {
  const pendantStep = document.getElementById('pendant-chain-step');
  const pendantGuideStep = document.getElementById('pendant-chain-guide-step');
  const isPendant = state.category === 'pendant';
  pendantStep?.classList.toggle('hidden', !isPendant);
  pendantGuideStep?.classList.toggle('hidden', !isPendant || !state.includeChain);
  updateLengthStep();

  if (!isPendant) {
    state.includeChain = false;
    state.chainProductId = null;
    return;
  }

  document.querySelectorAll('.pendant-chain-toggle').forEach(btn =>
    btn.classList.toggle('active', String(state.includeChain) === btn.dataset.includeChain));
  const options = document.getElementById('pendant-chain-options');
  options?.classList.toggle('hidden', !state.includeChain);
  if (!state.includeChain) return;

  const chains = productsFor('chain');
  const chainIds = chains.map(p => String(p.id));
  if (!chainIds.includes(String(state.chainProductId))) {
    state.chainProductId = defaultChainProductId();
    state.chainGold = null;
    state.chainColor = null;
  }

  const chainProduct = getProduct('chain', state.chainProductId);
  const chainGolds = productGolds('chain', chainProduct);
  if (state.chainGold && chainGolds.length && !chainGolds.includes(state.chainGold)) {
    state.chainGold = null;
    state.chainColor = null;
  }
  if (!state.chainGold && chainGolds.length) {
    state.chainGold = chainGolds[0];
  }
  // Attached chain is NOT a color-locked SKU — never use enforceMetalColor(chainProduct)
  // (that always returns chain-A/B/C defaultColor and wipes the swatch).
  state.chainColor = attachedChainColor(state.chainGold, state.chainColor || state.color);
  renderMetalButtons('pendant-chain-metal-row', chainGolds, state.chainGold, gold => {
    state.chainGold = gold;
    state.chainColor = attachedChainColor(gold, state.chainColor || state.color);
    updateChainOptions();
    updateSummary();
    updateLargeImage('chain');
  });

  const chainColorStep = document.getElementById('pendant-chain-color-step');
  const chainColorRow = document.getElementById('pendant-chain-color-row');
  // NOTE: intentionally not using needsColorSelection()/enforceMetalColor() here — those
  // treat any "chain-" product as color-locked (correct for the standalone chain-only
  // product page, where color is picked via SKU). Here the pendant's attached chain has
  // no SKU switcher, only this swatch, so it must stay selectable like a normal metal.
  const showChainColor = !!(state.chainGold && GOLD_COLOR_METALS.includes(state.chainGold));
  chainColorStep?.classList.toggle('hidden', !showChainColor);
  updateColorStepLabel('pendant-chain-color-label', state.chainGold);
  if (!showChainColor) {
    if (state.chainGold) {
      state.chainColor = attachedChainColor(state.chainGold, state.chainColor || state.color);
    }
    if (chainColorRow) chainColorRow.innerHTML = '';
  } else {
    state.chainColor = attachedChainColor(state.chainGold, state.chainColor || state.color);
    renderColorButtons('pendant-chain-color-row', state.chainGold, chainProduct, state.chainColor, color => {
      const colors = availableColorsForGold(state.chainGold);
      if (!colors.includes(color)) return;
      // Chain color is independent of pendant color (mixed-metal combos allowed).
      state.chainColor = color;
      document.querySelectorAll('#pendant-chain-color-row .color-btn').forEach(b =>
        b.classList.toggle('active', b.dataset.color === color));
      updateSummary();
      updateLargeImage('chain');
    });
  }
  if (!state.chainLength) {
    state.chainLength = CHAIN_LENGTH_OPTIONS_CM[0];
  }
  renderLengthSelect('pendant-chain-length-select', CHAIN_LENGTH_OPTIONS_CM, state.chainLength, 'chain_length_placeholder');
}

function currentProductImages() {
  const product = getSelectedProduct();
  if (!product || usesPendantCompositePreview()) return [];
  if (isDiamondOnlyCategory()) {
    return [diamondMatrixImageUrl(state.diamondShape, selectedDiamondColorId())];
  }
  return productImagesForColor(product, previewColor(), selectedDiamondColorId());
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
  return productImagesForColor(product, previewColor(), selectedDiamondColorId(), opts)[0]
    || productImageUrl(product, previewColor(), selectedDiamondColorId(), opts);
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

  // Catalog product.images (e.g. diamond-loose white.png) must not override matrix previews.
  if (isDiamondOnlyCategory()) {
    previewRoot?.classList.remove('is-pendant-only');
    const nextSrc = images[productImageIndex]
      || diamondMatrixImageUrl(state.diamondShape, selectedDiamondColorId());
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

  // pendantPreviewLayers already resolved the correct shop-product URL (incl. combo /
  // pendant-only). Prefer that; only use productImageResolve for fallback chain.
  let primarySrc = preview.composite ? '' : (preview.src || images[productImageIndex] || imageUrl(state.category, state.type) || '');
  let fallbacks = [];
  const pendantOnly = !!preview.pendantOnly;
  previewRoot?.classList.toggle('is-pendant-only', pendantOnly && !!primarySrc);
  if (img) {
    img.style.visibility = '';
    const imageOpts = pendantPreviewImageOpts();
    if (product && window.ShopAssets?.productImageResolve && !preview.composite) {
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
      if (preview.src) primarySrc = preview.src;
    }
    img.onerror = null;
    if (fallbacks.length && window.ShopAssets?.attachImageFallbackChain) {
      window.ShopAssets.attachImageFallbackChain(img, fallbacks);
    } else if (usesPendantCompositePreview() && product) {
      const fullFallback = productPreviewFallbackSrc(product);
      if (fullFallback && fullFallback !== primarySrc) {
        img.onerror = () => {
          img.onerror = null;
          showSingleProductPreview(img, previewRoot, fullFallback, false);
        };
      }
    }
    // Force browser to apply new metal asset even when cached aggressively.
    const nextSrc = primarySrc || '';
    if (img.getAttribute('src') === nextSrc && nextSrc) {
      img.removeAttribute('src');
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
  // Category
  document.getElementById("sum-cat").textContent =
    state.category ? tr('cat_' + state.category) : '-';

  // Style
  const selectedProduct = getSelectedProduct();
  document.getElementById("sum-type").textContent =
    selectedProduct ? productName(selectedProduct) : '-';

  document.getElementById("sum-material").textContent =
    isDiamondOnlyCategory()
      ? tr('sum_loose_diamond')
      : (state.gold ? materialLabel(state.gold, state.color) : '-');

  // Carat — hidden for chain-only (no diamond / no fen picker)
  const caratRow = document.getElementById('sum-carat-row');
  if (state.category === 'chain') {
    if (caratRow) caratRow.style.display = 'none';
  } else {
    if (caratRow) caratRow.style.display = '';
    const caratBase = state.carat
      ? (state.carat === '3fen' ? tr('chain_3fen')
        : state.carat === '4fen' ? tr('chain_4fen')
          : state.carat + 'ct')
      : '-';
    const badge = stoneCountBadgeText();
    const caratDisplay = badge && state.carat && state.carat !== '3fen' && state.carat !== '4fen'
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
    ? baseChin * (state.lengthCm / CHAIN_REFERENCE_LENGTH_CM)
    : baseChin !== null && state.category === 'bracelet' && state.lengthCm
      ? baseChin * (state.lengthCm / BRACELET_REFERENCE_LENGTH_CM)
      : baseChin;

  scheduleQuoteRefresh();

  updateCtaState(null);
  updateBreadcrumb();
  updateConfigChips();
  updateProductHeader();
}

function clearRingSizeSelection() {
  state.ringSize = null;
  state.engravingBand = '';
  state.engravingGirdle = '';
  state.lengthCm = null;
  state.includeChain = false;
  state.chainProductId = null;
  state.chainGold = null;
  state.chainColor = null;
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
  if (current != null) sel.value = String(current);
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

function selectCategory(cat) {
  state.category = cat;
  state.type = null;
  state.gold = null;
  state.color = null;
  state.carat = null;
  state.ringSize = null;
  state.engravingBand = '';
  state.engravingGirdle = '';
  state.lengthCm = null;
  state.includeChain = false;
  state.chainProductId = null;
  state.chainGold = null;
  state.chainColor = null;
  state.chainLength = null;

  document.querySelectorAll(".cat-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.cat === cat));

  const metalFilter = document.getElementById('catalog-metal-filter');
  if (metalFilter) {
    metalFilter.hidden = cat === 'diamond';
    if (cat === 'diamond') metalFilter.value = '';
  }

  renderTypeCards();
  const titleEl = document.getElementById("shop-category-title");
  if (titleEl) titleEl.textContent = tr('cat_' + cat);

  document.querySelectorAll(".carat-btn, #metal-btn-row .metal-btn, #color-btn-row .color-btn").forEach(b => b.classList.remove("active"));
  clearRingSizeSelection();
  updateMetalButtons();
  updateCaratButtons();
  updateChainOptions();
  updateDiamondWizardChrome();

  if (cat === 'diamond') {
    enterDiamondLooseProduct();
    return;
  }

  setShopView('styles');
  updateSummary();
}

function selectType(typeId) {
  state.type = typeId;
  state.carat = null;
  state.gold = null;
  const product = getSelectedProduct();
  state.color = null;
  state.ringSize = null;
  state.engravingBand = '';
  state.engravingGirdle = '';
  resetDiamondOptions();

  document.querySelectorAll(".type-card").forEach(c =>
    c.classList.toggle("active", c.dataset.type === typeId));

  updateCaratButtons();
  updateMetalButtons();
  document.querySelectorAll(".carat-btn, #metal-btn-row .metal-btn, #color-btn-row .color-btn").forEach(b => b.classList.remove("active"));
  clearRingSizeSelection();

  productImageIndex = 0;
  updateLargeImage();
  updateRingSizeStep();
  updateEngravingSteps();
  updateDiamondSteps();
  updateChainOptions();
  setShopView('product', { skipScroll: true });
  updateSummary();
}

function selectMetal(gold) {
  const product = getSelectedProduct();
  if (product && gold && !product.golds.includes(gold)) return;
  state.gold = gold;
  state.color = enforceMetalColor(gold, state.color, product);
  renderMetalButtons('metal-btn-row', productGolds(state.category, product), gold, selectMetal);
  updateColorStep(gold);
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
  state.carat = carat;

  document.querySelectorAll(".carat-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.carat === carat));

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

document.querySelectorAll(".carat-btn").forEach(btn =>
  btn.addEventListener("click", () => selectCarat(btn.dataset.carat)));

document.getElementById('ring-size-select')?.addEventListener('change', (e) =>
  selectRingSize(e.target.value));

document.getElementById('chain-length-select')?.addEventListener('change', (e) => {
  const v = e.target.value;
  state.lengthCm = v ? Number(v) : null;
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

function updateGirdlePreview() {
  const ctrl = ensureGirdleEngrave();
  const shapeId = state.diamondShape || 'round';
  const colorId = selectedDiamondColorId() || 'white';
  if (ctrl?.setPreviewShapeAndColor) {
    ctrl.setPreviewShapeAndColor(shapeId, colorId);
  } else if (ctrl?.setPreviewColor) {
    ctrl.setPreviewColor(colorId);
  }
}

let girdleEngraveCtrl = null;
function ensureGirdleEngrave() {
  if (girdleEngraveCtrl) return girdleEngraveCtrl;
  const input = document.getElementById('shop-girdle-engrave-input');
  if (!input || !window.GirdleEngrave) return null;
  girdleEngraveCtrl = window.GirdleEngrave.init({
    input,
    countEl: document.getElementById('shop-girdle-engrave-count'),
    previewEl: document.getElementById('shop-girdle-engrave-preview'),
    emblemsRoot: document.getElementById('engraving-girdle-step'),
    previewShape: state.diamondShape || 'round',
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
ensureGirdleEngrave();
document.querySelectorAll('.pendant-chain-toggle').forEach(btn =>
  btn.addEventListener('click', () => {
    state.includeChain = btn.dataset.includeChain === 'true';
    if (state.includeChain && !state.chainLength) {
      state.chainLength = CHAIN_LENGTH_OPTIONS_CM[0];
    }
    if (state.includeChain && !state.chainColor) {
      // First time 含鍊 only — seed from pendant; later picks stay independent.
      state.chainColor = attachedChainColor(state.chainGold || state.gold, previewColor());
    } else if (!state.includeChain) {
      // 僅墜子: drop chain metal so preview can't leak combo paths.
      state.chainColor = null;
    }
    productImageIndex = 0;
    updateChainOptions();
    updateSummary();
    // Force pendant-only vs with-chain asset refresh (never keep prior combo src)
    updateLargeImage(state.includeChain ? 'chain' : 'pendant');
  }));

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
  state.category = null;
  state.type = null;
  state.gold = null;
  state.color = null;
  state.carat = null;
  state.ringSize = null;
  state.engravingBand = '';
  state.engravingGirdle = '';
  state.lengthCm = null;
  state.includeChain = false;
  state.chainProductId = null;
  state.chainGold = null;
  state.chainColor = null;
  state.chainLength = null;
  document.querySelectorAll('.cat-btn, .carat-btn, #metal-btn-row .metal-btn, #color-btn-row .color-btn').forEach(b => b.classList.remove('active'));
  clearRingSizeSelection();
  updateChainOptions();
  setShopView('catalog');
  updateSummary();
});

document.getElementById('back-to-styles')?.addEventListener('click', () => {
  if (!state.category) return;
  if (isDiamondOnlyCategory()) {
    document.getElementById('back-to-catalog')?.click();
    return;
  }
  setShopView('styles');
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
  return layers.src || productImageUrl(product, previewColor(), selectedDiamondColorId(), pendantPreviewImageOpts()) || '';
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
  const submitColor = effectiveColor();
  const payload = {
    category: state.category,
    type:     state.type,
    gold:     state.gold,
    color:    submitColor || state.color,
    carat:    state.carat,
    ringSize: state.ringSize,
    engravingBand: state.engravingBand,
    engravingGirdle: state.engravingGirdle,
    lengthCm: state.lengthCm,
    includeChain: state.includeChain,
    chainProductId: state.chainProductId,
    chainGold: state.chainGold,
    chainColor: state.chainColor,
    chainLength: state.chainLength,
    diamondKind: state.diamondKind,
    fancyColor: state.fancyColor,
    stoneCount: state.stoneCount,
    diamondShape: state.diamondShape,
  };
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
  const pricing = window.ShopPricingLocal?.computeOrderPricing?.(buildQuotePayload(), catalog);
  if (pricing?.ready && pricing.total != null) {
    payload.clientPricing = {
      total: pricing.total,
      diamondPrice: pricing.diamondPrice,
      taijinPrice: pricing.taijinPrice,
      laborPrice: pricing.laborPrice,
      metalworkPrice: pricing.metalworkPrice,
      chainPrice: pricing.chainPrice,
      weightGrams: pricing.weightGrams,
      goldRatePerGram: pricing.goldRatePerGram,
      priceSource: 'client',
    };
  }
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
  const pricing = window.ShopPricingLocal?.computeOrderPricing?.(buildQuotePayload(), catalog);
  const lines = [
    '【品項訂製諮詢】',
    `品項：${state.category ? tr('cat_' + state.category) : '-'}`,
    `款式：${productName(product) || '-'}`,
    `金屬：${state.gold || '-'}`,
  ];
  if (state.color) lines.push(`成色：${tr('color_' + state.color) || state.color}`);
  if (state.carat && state.category !== 'chain') lines.push(`克拉：${state.carat}`);
  if (state.ringSize) lines.push(`戒圍：${state.ringSize}`);
  if (state.lengthCm) lines.push(`長度：${state.lengthCm} cm`);
  if (pricing?.total != null) lines.push(`試算參考價：NT$ ${Math.round(pricing.total).toLocaleString()}`);
  if (state.engravingBand) lines.push(`戒台刻字：${state.engravingBand}`);
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
  window.location.href = window.shopConfig?.contactUrl || '../../contact.html';
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

function validateBeforeSubmit(toast) {
  if (!state.category) { toast(tr('alert_pick_category')); return false; }
  if (!state.type)     { toast(tr('alert_pick_type'));     return false; }
  if (!isDiamondOnlyCategory()) {
    if (!state.gold) { toast(tr('alert_pick_gold')); return false; }
    const submitColor = effectiveColor();
    if (!submitColor) {
      const product = getSelectedProduct();
      toast(needsColorSelection(state.gold, product) ? tr('alert_pick_color') : tr('alert_pick_material'));
      return false;
    }
  }

  if (!state.carat) { toast(tr('alert_pick_carat')); return false; }

  if (state.category === 'ring' && !state.ringSize) {
    toast(tr('alert_pick_ring_size')); return false;
  }

  if (state.category === 'chain' && !state.lengthCm) {
    toast(tr('alert_pick_chain_length')); return false;
  }

  if (state.category === 'bracelet' && !state.lengthCm) {
    toast(tr('alert_pick_bracelet_length')); return false;
  }

  if (state.category !== 'chain' && state.diamondKind === 'fancy' && !state.fancyColor) {
    toast(tr('step_diamond_color')); return false;
  }

  if (state.category === 'pendant' && state.includeChain
    && (!state.chainProductId || !state.chainGold || !state.chainColor || !state.chainLength)) {
    toast(tr('alert_pick_chain_length')); return false;
  }

  if (state.category === 'chain' && state.gold === '9k') {
    const product = getSelectedProduct();
    if (product && product.defaultColor !== 'white') {
      toast(tr('alert_chain_9k_white_only')); return false;
    }
  }
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
  if (isGuestShop || shopIsLoggedIn === false) {
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
        const base = window.shopConfig?.checkoutUrl || '/checkout.html';
        window.location.href = base + '?items=' + encodeURIComponent(items);
        return;
      }
      window.location.href = window.shopConfig?.cartUrl || '/cart.html';
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
  if (isDiamondOnlyCategory()) {
    if (!validateBeforeSubmit(toast)) return;
    try {
      sessionStorage.setItem('shopInquiryDraft', buildInquirySummaryLines().join('\n'));
    } catch (_) { /* ignore */ }
    window.open('https://lin.ee/ktVBtmx', '_blank', 'noopener');
    return;
  }
  if (!shopUsesApi()) {
    openContactForOrder();
    return;
  }
  if (!validateBeforeSubmit(toast)) return;
  if (isGuestShop || shopIsLoggedIn === false) {
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
    const checkoutUrl = window.shopConfig?.checkoutUrl || '/checkout.html';
    window.location.href = checkoutUrl + '?item=' + encodeURIComponent(itemId);
  } catch (err) {
    console.error(err);
    resetButtons();
    toast(tr('generic_error'));
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

(function setupMobilePricePanel() {
  const details = document.getElementById('price-breakdown-details');
  const toggle = document.getElementById('mobile-price-toggle');
  const panel = document.getElementById('shop-price-panel');

  function isMobileShop() {
    return window.matchMedia('(max-width: 900px)').matches;
  }

  const isWizard = !!document.querySelector('.shop-page.shop-wizard');

  function syncDetailsOpen() {
    if (!details) return;
    if (!isMobileShop() || isWizard) {
      details.open = true;
      panel?.classList.remove('is-mobile-open');
      return;
    }
    if (!details.dataset.userOpened) details.open = false;
  }

  syncDetailsOpen();
  window.addEventListener('resize', syncDetailsOpen);

  toggle?.addEventListener('click', () => {
    if (!panel || !details) return;
    const willOpen = !panel.classList.contains('is-mobile-open');
    panel.classList.toggle('is-mobile-open', willOpen);
    details.dataset.userOpened = '1';
    details.open = willOpen;
    toggle.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
    if (willOpen) {
      panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  });
})();

['catalog-search-input', 'catalog-metal-filter', 'catalog-price-filter'].forEach(id => {
  const element = document.getElementById(id);
  element?.addEventListener(element.tagName === 'INPUT' ? 'input' : 'change', renderTypeCards);
});
function clearCatalogFilters() {
  const search = document.getElementById('catalog-search-input');
  const metal = document.getElementById('catalog-metal-filter');
  const price = document.getElementById('catalog-price-filter');
  if (search) search.value = '';
  if (metal) metal.value = '';
  if (price) price.value = '';
  renderTypeCards();
}
document.getElementById('catalog-filter-clear')?.addEventListener('click', clearCatalogFilters);
document.getElementById('catalog-filter-empty-clear')?.addEventListener('click', clearCatalogFilters);

document.addEventListener('langchange', () => {
  populateRingSizeSelect();
  updateMetalButtons();
  updateColorStep();
  updateChainOptions();
  renderCatalogTiles();
  renderDiamondShapeButtons();
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
    engravingGirdle: o.engraving_girdle || '',
    diamondKind: o.diamond_kind || 'white',
    fancyColor: o.fancy_color,
    stoneCount: o.stone_count,
    diamondShape: o.diamond_shape || 'round',
    includeChain: !!o.include_chain,
    chainGold: o.chain_gold,
    chainColor: o.chain_color,
  };
  if (o.category === 'chain') cfg.lengthCm = o.chain_length_cm;
  else cfg.chainLength = o.chain_length_cm;
  if (o.product_name) cfg.summaryZh = o.product_name;
  return cfg;
}

function restoreShopConfig(cfg) {
  if (!cfg?.category || !cfg?.type) return;

  const typeId = String(cfg.type);
  state.category = cfg.category;
  state.type = typeId;

  document.querySelectorAll('.cat-btn').forEach((btn) =>
    btn.classList.toggle('active', btn.dataset.cat === cfg.category));

  const titleEl = document.getElementById('shop-category-title');
  if (titleEl) titleEl.textContent = tr('cat_' + cfg.category);

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
  state.engravingGirdle = cfg.engravingGirdle || '';
  state.lengthCm = cfg.lengthCm != null ? cfg.lengthCm : null;
  state.includeChain = !!cfg.includeChain;
  state.chainProductId = cfg.chainProductId || null;
  state.chainGold = cfg.chainGold || null;
  state.chainColor = cfg.chainColor || null;
  state.chainLength = cfg.chainLength != null ? cfg.chainLength : null;
  state.diamondKind = cfg.diamondKind || 'white';
  state.fancyColor = cfg.fancyColor || null;
  state.stoneCount = cfg.stoneCount || null;
  ensureStoneCountDefault();
  state.diamondShape = cfg.diamondShape || 'round';

  if (cfg.ringSize != null && cfg.ringSize !== '') {
    setRingSizeActive(cfg.ringSize);
  }

  updateRingSizeStep();
  updateDiamondSteps();
  updateEngravingSteps();
  updateChainOptions();
  updateLengthStep();
  syncVariantChipActiveStates();
  productImageIndex = 0;
  updateLargeImage();
  setShopView('product', { skipScroll: true });
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
  if (isGuestShop || shopIsLoggedIn === false) {
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
  if (isGuestShop || shopIsLoggedIn === false) {
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
  loadLiveGoldRates();
  refreshShopLoginState();
  updateDiamondWizardChrome();
}

function applyInitialShopState() {
  const prefillData = window.cartEditData || window.editData || window.prefillData || takeShopResumeSnapshot();
  if (prefillData) {
    restoreShopConfig(prefillData);
  } else {
    setShopView('catalog');
    updateWizardGuide();
  }

  const urlCategory = new URLSearchParams(window.location.search).get('category');
  const urlType = new URLSearchParams(window.location.search).get('type')
    || new URLSearchParams(window.location.search).get('product')
    || new URLSearchParams(window.location.search).get('series');
  if (urlCategory && productsFor(urlCategory).length && !prefillData) {
    requestAnimationFrame(() => {
      document.querySelector(`.cat-btn[data-cat="${urlCategory}"]`)?.click();
      if (urlType && urlCategory !== 'diamond') {
        setTimeout(() => {
          const typeId = urlType.startsWith('diamond-') || urlCategory !== 'diamond'
            ? urlType
            : `diamond-${urlType}`;
          document.querySelector(`.type-card[data-type="${typeId}"]`)?.click();
        }, 60);
      }
    });
  }

  const previewProduct = new URLSearchParams(window.location.search).get('product');
  if (window.shopConfig?.preview && previewProduct && urlCategory && !prefillData && !urlType) {
    setTimeout(() => {
      document.querySelector(`.type-card[data-type="${previewProduct}"]`)?.click();
    }, 50);
  }
}

async function init() {
  const bootPromise = bootShopCore();

  if (window.ensureShopTermsAccepted) {
    const termsOk = await window.ensureShopTermsAccepted();
    if (!termsOk) return;
  }

  await bootPromise;
  applyInitialShopState();
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
