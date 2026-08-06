"""Shop must expose only admin-configured 款式選項, not bundled static full matrices."""

from decimal import Decimal
from pathlib import Path

from app.catalog import build_catalog_product
from app.controllers.shop_controller import _validate_product_variant

ROOT = Path(__file__).resolve().parents[1]


class _VariantCursor:
    def __init__(self, variant=None):
        self.variant = variant
        self.queries: list[str] = []

    def execute(self, query, params=None):
        self.queries.append(" ".join(query.split()))
        return None

    def fetchone(self):
        return self.variant


def test_build_catalog_product_limits_golds_and_carats_to_variants():
    product = {
        "id": "prod-1",
        "category": "ring",
        "name_zh": "Test Ring",
        "name_en": None,
        "description_zh": None,
        "description_en": None,
        "default_color": "white",
        "sort_order": 0,
        "is_published": True,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }
    variants = [
        {"gold": "14k", "carat": "0.3", "weight_chin": 1.2},
        {"gold": "18k", "carat": "0.5", "weight_chin": 1.4},
    ]

    entry = build_catalog_product(product, variants, [])

    assert entry["golds"] == ["14k", "18k"]
    assert entry["carats"] == ["0.3", "0.5"]
    assert set(entry["weights"]["14k"]) == {"0.3"}
    assert set(entry["weights"]["18k"]) == {"0.5"}


def _generic_product(product_id="prod-generic", category="pendant"):
    return {
        "id": product_id,
        "category": category,
        "name_zh": "Generic Test SKU",
        "name_en": None,
        "description_zh": None,
        "description_en": None,
        "default_color": "white",
        "sort_order": 0,
        "is_published": True,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }


def test_build_catalog_carats_include_sub_fancy_min_when_variants_have_them():
    """Shop must expose admin 0.1/0.2 even though fancy list price starts at 0.3."""
    variants = [
        {"gold": "14k", "carat": "0.3", "weight_chin": 0.018},
        {"gold": "14k", "carat": "0.1", "weight_chin": 0.012},
        {"gold": "14k", "carat": "0.2", "weight_chin": 0.015},
        {"gold": "18k", "carat": "0.1", "weight_chin": 0.012},
    ]

    entry = build_catalog_product(_generic_product(), variants, [])

    assert entry["carats"] == ["0.1", "0.2", "0.3"]
    assert set(entry["weights"]["14k"]) == {"0.1", "0.2", "0.3"}
    assert "0.1" in entry["weights"]["18k"]


def test_catalog_keeps_01_when_variants_only_have_01():
    """Regression: admin lists only 0.1 → catalog/shop must not invent 0.3."""
    variants = [
        {"gold": "14k", "carat": "0.1", "weight_chin": 0.012},
        {"gold": "18k", "carat": "0.1", "weight_chin": 0.012},
    ]
    entry = build_catalog_product(_generic_product("prod-01-only"), variants, [])
    assert entry["carats"] == ["0.1"]
    assert "0.3" not in entry["carats"]
    assert set(entry["weights"]["14k"]) == {"0.1"}


def test_catalog_canonicalizes_decimal_and_padded_carat_keys():
    """0.10 / Decimal('0.1') must surface as shop key '0.1', not drop out."""
    variants = [
        {"gold": "14k", "carat": Decimal("0.10"), "weight_chin": 0.012},
        {"gold": "14k", "carat": "0.30", "weight_chin": 0.018},
    ]
    entry = build_catalog_product(_generic_product("prod-decimal"), variants, [])
    assert entry["carats"] == ["0.1", "0.3"]
    assert set(entry["weights"]["14k"]) == {"0.1", "0.3"}


def test_shop_catalog_filters_use_or_within_dimension():
    src = (ROOT / "public" / "js" / "shop.js").read_text(encoding="utf-8")
    assert "function productMatchesPriceBand" in src
    assert "metals.some((m) => golds.includes(m))" in src
    assert "carats.some((c) => productOffersCarat(product, c))" in src
    assert "priceBands.some((band) => productMatchesPriceBand(price, band))" in src
    assert "function catalogCaratsForProduct" in src
    assert "function collectCategoryCarats" in src
    assert "function collectCategoryMetals" in src
    assert "function populateCatalogFilters" in src
    ms = (ROOT / "public" / "js" / "catalog-multi-filter.js").read_text(encoding="utf-8")
    assert "aria-multiselectable" in ms
    assert "upgradeSelect" in ms


def test_shop_js_catalog_filter_options_from_product_variants():
    """Carat/metal filter options must union distinct variant values in category."""
    import json
    import subprocess

    browser_script = r"""
const METAL_DISPLAY_ORDER = ['9k', '14k', '18k', 'pt950', 's925'];
function sortGolds(golds) {
  const order = Object.fromEntries(METAL_DISPLAY_ORDER.map((g, i) => [g, i]));
  return [...golds].sort((a, b) => (order[a] ?? 99) - (order[b] ?? 99));
}
function sortCaratValues(values) {
  return [...values].sort((a, b) => {
    const na = parseFloat(a);
    const nb = parseFloat(b);
    if (!Number.isNaN(na) && !Number.isNaN(nb) && na !== nb) return na - nb;
    return String(a).localeCompare(String(b), undefined, { numeric: true });
  });
}
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
function collectCategoryCarats(products) {
  const set = new Set();
  products.forEach((product) => {
    catalogCaratsForProduct(product).forEach((c) => set.add(c));
  });
  return sortCaratValues([...set]);
}
function productGolds(product) {
  const golds = new Set(Object.keys(product.weights || {}));
  (product.golds || []).forEach((g) => {
    if (product.weights?.[g] && Object.keys(product.weights[g]).length) golds.add(g);
  });
  return sortGolds([...golds]);
}
function collectCategoryMetals(products) {
  const set = new Set();
  products.forEach((product) => productGolds(product).forEach((g) => set.add(g)));
  return sortGolds([...set]);
}

const ringProducts = [
  { carats: ['0.3'], weights: { '14k': { '0.3': 1 } } },
  { carats: ['0.5', '0.6'], weights: { '18k': { '0.5': 1, '0.6': 1 } } },
];
const chainProducts = [
  { carats: ['1.5mm'], weights: { '18k': { '1.5mm': 0.03 } } },
  { carats: ['2.0mm', '2.5mm'], weights: { '14k': { '2.0mm': 0.04, '2.5mm': 0.05 } } },
];

console.log(JSON.stringify({
  ringCarats: collectCategoryCarats(ringProducts),
  ringMetals: collectCategoryMetals(ringProducts),
  chainThicknesses: collectCategoryCarats(chainProducts),
  offers06: catalogCaratsForProduct(ringProducts[1]).includes('0.6'),
  weightOnly: catalogCaratsForProduct({ carats: [], weights: { '14k': { '0.1': 1, '0.7': 1 } } }),
}));
"""
    out = json.loads(
        subprocess.run(
            ["node", "-e", browser_script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert out["ringCarats"] == ["0.3", "0.5", "0.6"]
    assert out["ringMetals"] == ["14k", "18k"]
    assert out["chainThicknesses"] == ["1.5mm", "2.0mm", "2.5mm"]
    assert out["offers06"] is True
    assert out["weightOnly"] == ["0.1", "0.7"]


def test_build_catalog_product_includes_extended_carats_for_filters():
    """API catalog must surface 0.5/0.6 so client filters can list them."""
    variants = [
        {"gold": "14k", "carat": "0.3", "weight_chin": 0.018},
        {"gold": "14k", "carat": "0.5", "weight_chin": 0.022},
        {"gold": "18k", "carat": "0.6", "weight_chin": 0.024},
    ]
    entry = build_catalog_product(_generic_product(category="ring"), variants, [])
    assert entry["carats"] == ["0.3", "0.5", "0.6"]


def test_shop_js_fancy_carat_dropdown_intersects_admin_min():
    """Fancy carat <select> = admin ∩ ≥ fancyMin; white keeps full admin list."""
    src = (ROOT / "public" / "js" / "shop.js").read_text(encoding="utf-8")
    assert "function listAdminProductCaratOptions" in src
    assert "function listProductCaratOptions" in src
    assert "function isCaratHiddenForShop" in src
    # Dead isCaratHiddenForShop path must stay unused when building options.
    assert "const visible = isChain || !isCaratHiddenForShop" not in src
    assert "isCaratHiddenForShop(v)" not in src
    assert "if (state.carat && isCaratHiddenForShop(state.carat))" not in src
    # No hard-coded bump to literal 0.3 — bump comes from filtered options[0].
    assert "state.carat = '0.3'" not in src
    assert "state.carat = \"0.3\"" not in src
    # Fancy path filters by diamondKind === 'fancy' and fancyMinCaratValue().
    assert "state.diamondKind !== 'fancy'" in src
    assert "fancyMinCaratValue()" in src
    assert "function isFancyDiamondColorOffered" in src
    assert "function productOffersFancyMinCaratOrAbove" in src
    # Per-color AND gate: carat≥0.3 alone must not unlock all fancy colors.
    assert "if (!productOffersFancyMinCaratOrAbove()) return false;" in src
    assert "if (productOffersFancyMinCaratOrAbove()) return true;" not in src
    # Letter SKUs: bundled shop-product fancy PNGs count (admin 內建, not DB).
    assert "stockFancyDiamondColors" in src
    assert "stockFancyDiamondColors" in (
        ROOT / "public" / "js" / "shop-assets.js"
    ).read_text(encoding="utf-8")
    assert "shop.js?v=143" in (
        ROOT / "content" / "site" / "templates" / "pages" / "shop" / "calculator.html"
    ).read_text(encoding="utf-8")
    assert "shop.js?v=143" in (
        ROOT / "content" / "site" / "page-registry.json"
    ).read_text(encoding="utf-8")
    # Step 2 style grid: admin slot order, then thumb/stock; onerror walks full chain.
    assert "function styleGridImageUrl" in src
    assert "function styleGridImageCandidates" in src
    assert "function orderedCatalogImageUrls" in src
    assert "function catalogImageSlotKeyOrder" in src
    assert "candidates.slice(1)" in src
    assert "attachImageFallbackChain" in src
    assert "catalogImageCrossDiamondFallback" in src
    assert "function firstAnyCatalogImageUrl" in src
    assert "productImageResolve(" in src and "assetId, 'white', 'white', 'white'" in src
    # Lite thumbUrl before letter-stock PNGs when styleKey still maps bracelet-A etc.
    assert "if (product.thumbUrl && isUsableCatalogImageUrl(product.thumbUrl)) return '';" in src
    assert "if (productHasCatalogImages(product)) return '';" in src
    assert (
        "// Full catalog: 預設顏色 slots first; lite uses server thumbUrl (same priority)."
        in src
    )
    assert "shop-assets.js?v=15" in (
        ROOT / "content" / "site" / "templates" / "pages" / "shop" / "calculator.html"
    ).read_text(encoding="utf-8")
    # Fancy preview must not reuse metal-only / white-stone catalog slots.
    assert "that froze preview on" in src
    assert "Catalog miss (common: white slot only)" in src
    assert "catalog-multi-filter.js" in (
        ROOT / "content" / "site" / "templates" / "pages" / "shop" / "calculator.html"
    ).read_text(encoding="utf-8")
    assert "shop-fancy-min-note" in (
        ROOT / "content" / "site" / "templates" / "pages" / "shop" / "calculator.html"
    ).read_text(encoding="utf-8")
    # Notice = product offers fancy (carat≥min AND fancy images). No white/carat hide.
    assert "productOffersFancyMinCaratOrAbove()" in src
    assert "designedFancyDiamondColors(getSelectedProduct()).length > 0" in src
    assert "selectedCaratBelowFancyMin" not in src
    assert "function syncFancyMinCaratNotice" in src
    # API /api/prices omits diamondOptions — must seed UI tables + fallback defs.
    assert "function ensureDiamondOptionTables" in src
    assert "FALLBACK_DIAMOND_COLOR_DEFS" in src


def test_shop_js_fancy_min_notice_when_product_offers_fancy():
    """Red 彩鑽0.3 note: show when product offers fancy; ignore white/carat pick."""
    import json
    import subprocess

    browser_script = r"""
function shouldShow(productOffersFancyMin, fancyImageCount) {
  return productOffersFancyMin && fancyImageCount > 0;
}
console.log(JSON.stringify({
  offersFancy: shouldShow(true, 2),
  whiteStillShow: shouldShow(true, 2),
  highCaratStillShow: shouldShow(true, 1),
  noMinCarat: shouldShow(false, 2),
  noFancyImages: shouldShow(true, 0),
  neither: shouldShow(false, 0),
}));
"""
    out = json.loads(
        subprocess.run(
            ["node", "-e", browser_script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert out["offersFancy"] is True
    assert out["whiteStillShow"] is True
    assert out["highCaratStillShow"] is True
    assert out["noMinCarat"] is False
    assert out["noFancyImages"] is False
    assert out["neither"] is False


def test_shop_js_fancy_color_requires_carat_and_image():
    """Fancy swatch X shown iff carat≥0.3 AND (catalog slot OR letter stock) for X."""
    import json
    import subprocess

    browser_script = r"""
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assetsSrc = fs.readFileSync(path.join('public', 'js', 'shop-assets.js'), 'utf8');
const pricingSrc = fs.readFileSync(path.join('public', 'js', 'shop-pricing-local.js'), 'utf8');
const sandbox = { window: { shopConfig: { imageRoot: '/static/images/shop-product/', useApi: true } }, console };
sandbox.window = sandbox.window;
sandbox.global = sandbox.window;
vm.runInNewContext(assetsSrc, sandbox);
vm.runInNewContext(pricingSrc, sandbox);
const ShopAssets = sandbox.window.ShopAssets;

const FANCY_DIAMOND_COLOR_IDS = ['yellow', 'blue', 'pink'];
let diamondOptions = { diamondColors: [], fancyColors: [], fancyMinCarat: 0.3 };
const state = { category: 'ring' };
let selectedProduct = null;
function getSelectedProduct() { return selectedProduct; }
function fancyMinCaratValue() {
  const n = Number(diamondOptions.fancyMinCarat || 0.3);
  return Number.isNaN(n) ? 0.3 : n;
}
function productConfiguredCarats() {
  return [...(getSelectedProduct()?.carats || [])].map(String);
}
function productOffersFancyMinCaratOrAbove() {
  const minCarat = fancyMinCaratValue();
  return productConfiguredCarats().some((c) => {
    const n = parseFloat(c);
    return !Number.isNaN(n) && n >= minCarat;
  });
}
function productAssetId(product) {
  if (!product) return '';
  if (product.styleKey && /^[a-z]+-[A-C]$/i.test(String(product.styleKey))) {
    return String(product.styleKey);
  }
  const id = String(product.id || '');
  if (/^[a-z]+-[A-C]$/i.test(id)) return id;
  const cat = String(product.category || state.category || '').toLowerCase();
  if (!['pendant', 'ring', 'earring', 'bracelet', 'chain'].includes(cat)) return '';
  const order = Number(product.sortOrder ?? product.sort_order);
  if (!Number.isFinite(order) || order < 0 || order > 2) return '';
  return cat + '-' + String.fromCharCode(65 + order);
}
function addFancyColorsFromSlotKeys(keys, found) {
  if (!keys) return;
  const list = Array.isArray(keys) ? keys : Object.keys(keys);
  list.forEach((key) => {
    const parts = String(key).toLowerCase().split('-');
    if (parts.length >= 2 && FANCY_DIAMOND_COLOR_IDS.includes(parts[1])) {
      found.add(parts[1]);
    }
  });
}
function designedFancyDiamondColors(product) {
  const found = new Set();
  const images = product?.images;
  if (images && typeof images === 'object' && !Array.isArray(images)) {
    Object.keys(images).forEach((key) => {
      const urls = images[key];
      if (!urls || (Array.isArray(urls) && !urls.length)) return;
      addFancyColorsFromSlotKeys([key], found);
    });
  }
  addFancyColorsFromSlotKeys(product?.colors, found);
  const styleKey = productAssetId(product);
  const stock = ShopAssets.stockFancyDiamondColors(styleKey) || [];
  stock.forEach((c) => { if (FANCY_DIAMOND_COLOR_IDS.includes(c)) found.add(c); });
  return FANCY_DIAMOND_COLOR_IDS.filter((c) => found.has(c));
}
function isFancyDiamondColorOffered(colorId) {
  if (!FANCY_DIAMOND_COLOR_IDS.includes(colorId)) return false;
  if (!productOffersFancyMinCaratOrAbove()) return false;
  return designedFancyDiamondColors(getSelectedProduct()).includes(colorId);
}
function offered() {
  return FANCY_DIAMOND_COLOR_IDS.filter(isFancyDiamondColorOffered);
}

const FALLBACK_DIAMOND_COLOR_DEFS = [
  { id: 'white', kind: 'white' },
  { id: 'yellow', kind: 'fancy' },
  { id: 'blue', kind: 'fancy' },
  { id: 'pink', kind: 'fancy' },
];
function ensureDiamondOptionTables() {
  const localOpts = sandbox.window.ShopPricingLocal?.pricesPayload?.()?.diamondOptions;
  if (!localOpts) return false;
  const needColors = !diamondOptions.diamondColors?.length;
  const needFancy = !diamondOptions.fancyColors?.length;
  if (!needColors && !needFancy) return false;
  diamondOptions = {
    ...diamondOptions,
    diamondColors: needColors ? (localOpts.diamondColors || []) : diamondOptions.diamondColors,
    fancyColors: needFancy ? (localOpts.fancyColors || []) : diamondOptions.fancyColors,
  };
  return true;
}
function diamondColorOptions() {
  ensureDiamondOptionTables();
  let all = diamondOptions.diamondColors?.length
    ? diamondOptions.diamondColors
    : [{ id: 'white', kind: 'white' }, ...(diamondOptions.fancyColors || [])];
  const byId = new Map();
  all.forEach((c) => { if (c?.id) byId.set(c.id, c); });
  FALLBACK_DIAMOND_COLOR_DEFS.forEach((def) => {
    if (!byId.has(def.id)) byId.set(def.id, def);
  });
  all = FALLBACK_DIAMOND_COLOR_DEFS.map((def) => byId.get(def.id)).filter(Boolean);
  return all.filter((color) => {
    if (!color || color.id === 'white' || color.kind === 'white') return true;
    return isFancyDiamondColorOffered(color.id);
  }).map((c) => c.id);
}
function noticeShows() {
  return productOffersFancyMinCaratOrAbove()
    && designedFancyDiamondColors(getSelectedProduct()).length > 0;
}

selectedProduct = {
  carats: ['0.1', '0.3'],
  images: { 'yellow-yellow': ['/y.png'] },
};
const yellowOnly = offered();

selectedProduct = {
  carats: ['0.1', '0.3'],
  images: {},
};
const caratNoImage = offered();

selectedProduct = {
  carats: ['0.1', '0.2'],
  images: { 'yellow-yellow': ['/y.png'], 'yellow-blue': ['/b.png'], 'yellow-pink': ['/p.png'] },
};
const imageNoCarat = offered();

selectedProduct = {
  carats: ['0.3'],
  images: { 'yellow-yellow': ['/y.png'], 'yellow-blue': ['/b.png'] },
};
const yellowBlue = offered();

// Letter SKU with only white uploads — stock fancy PNGs unlock 黃/藍/粉.
selectedProduct = {
  id: 'uuid-ring',
  category: 'ring',
  sortOrder: 0,
  carats: ['0.1', '0.3'],
  images: { 'white-white': ['/upload-white.png'] },
};
const stockLetterFancy = offered();

selectedProduct = {
  id: 'earring-A',
  carats: ['0.3'],
  images: { white: ['/e.png'] },
};
const earringStock = offered();

selectedProduct = {
  id: 'bracelet-A',
  carats: ['0.3'],
  images: { 'white-white': ['/b.png'] },
};
const braceletNoStockFancy = offered();

// Lite UUID + 0.3 + stock: carousel must list fancy (not white-only) even when
// diamondOptions left empty by /api/prices (useApi path).
diamondOptions = { diamondColors: [], fancyColors: [], fancyMinCarat: 0.3 };
selectedProduct = {
  id: 'uuid-earring',
  category: 'earring',
  sortOrder: 0,
  carats: ['0.3'],
  colors: ['white-white'],
  // lite omits images
};
const apiModeCarousel = diamondColorOptions();
const apiModeNotice = noticeShows();
const apiModeOffered = offered();

// Notice must not claim fancy when nothing offered.
selectedProduct = {
  id: 'bracelet-A',
  category: 'bracelet',
  sortOrder: 0,
  carats: ['0.3'],
  colors: ['white-white'],
};
const braceletNotice = noticeShows();

console.log(JSON.stringify({
  yellowOnly, caratNoImage, imageNoCarat, yellowBlue,
  stockLetterFancy, earringStock, braceletNoStockFancy,
  stockRing: ShopAssets.stockFancyDiamondColors('ring-A'),
  stockBracelet: ShopAssets.stockFancyDiamondColors('bracelet-A'),
  apiModeCarousel, apiModeNotice, apiModeOffered, braceletNotice,
}));
"""
    out = json.loads(
        subprocess.run(
            ["node", "-e", browser_script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert out["yellowOnly"] == ["yellow"]
    assert out["caratNoImage"] == []
    assert out["imageNoCarat"] == []
    assert out["yellowBlue"] == ["yellow", "blue"]
    assert out["stockRing"] == ["yellow", "blue", "pink"]
    assert out["stockBracelet"] == []
    assert out["stockLetterFancy"] == ["yellow", "blue", "pink"]
    assert out["earringStock"] == ["yellow", "blue", "pink"]
    assert out["braceletNoStockFancy"] == []
    # Regression: stock fancy + 0.3 → carousel lists 黃/藍/粉 (API empty tables).
    assert out["apiModeOffered"] == ["yellow", "blue", "pink"]
    assert out["apiModeCarousel"] == ["white", "yellow", "blue", "pink"]
    assert out["apiModeNotice"] is True
    assert out["braceletNotice"] is False


def test_shop_preview_url_follows_fancy_diamond_color():
    """White-only catalog slot must not pin preview; pink → *_pink.png stock."""
    import json
    import subprocess

    browser_script = r"""
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assetsSrc = fs.readFileSync(path.join('public', 'js', 'shop-assets.js'), 'utf8');
const sandbox = { window: { shopConfig: { imageRoot: '/static/images/shop-product/' } }, console };
sandbox.global = sandbox.window;
vm.runInNewContext(assetsSrc, sandbox);
const ShopAssets = sandbox.window.ShopAssets;

function catalogImagesForKeys(product, keys) {
  if (!product?.images || !keys?.length) return [];
  for (const key of keys) {
    const val = product.images[key];
    const list = Array.isArray(val) ? val : val ? [val] : [];
    if (list.length) return list;
  }
  return [];
}

/** Mirrors shop.js catalogPreviewSrc fancy exact-key behavior. */
function catalogPreviewSrc(product, metal, diamond, chainMetal) {
  if (!product?.images) return '';
  const d = diamond || 'white';
  let keys;
  if (d !== 'white') {
    keys = [];
    if (chainMetal) keys.push(ShopAssets.buildImageSlotKey(metal, d, chainMetal));
    keys.push(ShopAssets.buildImageSlotKey(metal, d));
  } else {
    keys = ShopAssets.imageSlotKeysForLookup(metal, d, chainMetal || null);
  }
  const urls = catalogImagesForKeys(product, keys);
  return urls[0] || '';
}

const product = {
  id: 'uuid-ring',
  category: 'ring',
  sortOrder: 0,
  defaultColor: 'white',
  images: { white: ['/static/uploads/products/ring-white.png'], 'white-white': ['/static/uploads/products/ring-white.png'] },
};
const whiteCatalog = catalogPreviewSrc(product, 'white', 'white', null);
const pinkCatalog = catalogPreviewSrc(product, 'white', 'pink', null);
const pinkStock = ShopAssets.productImage('ring-A', 'white', 'white', 'pink');
const yellowGold = ShopAssets.productImage('ring-A', 'white', 'white', 'yellow');
const earringPinkGold = ShopAssets.productImage('earring-A', 'yellow', 'yellow', 'pink');
const earringYellowResolve = ShopAssets.productImageResolve('earring-A', 'yellow', 'yellow', 'pink');
const earringRoseResolve = ShopAssets.productImageResolve('earring-A', 'rose', 'rose', 'pink');
console.log(JSON.stringify({
  whiteCatalog,
  pinkCatalog,
  pinkStock,
  yellowGold,
  earringPinkGold,
  earringYellowResolve,
  earringRoseResolve,
  lookupWouldHaveReturnedWhite: ShopAssets.imageSlotKeysForLookup('white', 'pink', null),
}));
"""
    out = json.loads(
        subprocess.run(
            ["node", "-e", browser_script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert out["whiteCatalog"] == "/static/uploads/products/ring-white.png"
    # Exact fancy slot missing → empty (do NOT return white upload).
    assert out["pinkCatalog"] == ""
    # Legacy lookup still lists metal-only — proves the trap we avoid.
    assert "white" in out["lookupWouldHaveReturnedWhite"]
    assert "white-pink" in out["lookupWouldHaveReturnedWhite"]
    assert out["pinkStock"].endswith("戒指A_silver_pink.png") or "%E6%88%92%E6%8C%87A_silver_pink.png" in out["pinkStock"]
    assert "_yellow.png" in out["yellowGold"] or out["yellowGold"].endswith("yellow.png")
    assert "耳飾A_gold_pink.png" in out["earringPinkGold"] or "%E8%80%B3%E9%A3%BEA_gold_pink.png" in out["earringPinkGold"]
    # Yellow metal earring: gold fancy primary, gold white fallback — never silver fancy.
    yellow_chain = [out["earringYellowResolve"]["src"], *out["earringYellowResolve"]["fallbacks"]]
    assert any("gold" in u and "pink" in u for u in yellow_chain)
    assert any("gold" in u and "pink" not in u for u in yellow_chain) or any(
        u.endswith("耳飾A_gold.png") or "%E8%80%B3%E9%A3%BEA_gold.png" in u for u in yellow_chain
    )
    assert not any("silver" in u for u in yellow_chain)
    # Rose metal earring keeps rose_gold fancy.
    assert "rose" in out["earringRoseResolve"]["src"]
    assert "pink" in out["earringRoseResolve"]["src"]


def test_shop_js_multi_image_gallery_honors_index():
    """Multi-image slot: main preview must use images[productImageIndex], not catalog [0]."""
    import json
    import subprocess

    src = (ROOT / "public" / "js" / "shop.js").read_text(encoding="utf-8")
    assert "const multiImageGallery = images.length > 1;" in src
    assert "if (preview.src && !multiImageGallery) primarySrc = preview.src;" in src
    assert "&& !multiImageGallery" in src

    browser_script = r"""
function pickPrimarySrc({ multiImageGallery, indexedSrc, previewSrc, keepPrevious, fallbackUrl }) {
  if (multiImageGallery) return indexedSrc;
  return previewSrc || (keepPrevious ? '' : (indexedSrc || fallbackUrl || ''));
}
const img0 = '/static/uploads/products/earring-top.png';
const img1 = '/static/uploads/products/earring-side.png';
console.log(JSON.stringify({
  multiUsesIndex1: pickPrimarySrc({
    multiImageGallery: true,
    indexedSrc: img1,
    previewSrc: img0,
    keepPrevious: false,
    fallbackUrl: '',
  }),
  singleUsesPreview: pickPrimarySrc({
    multiImageGallery: false,
    indexedSrc: img1,
    previewSrc: img0,
    keepPrevious: false,
    fallbackUrl: '',
  }),
}));
"""
    out = json.loads(
        subprocess.run(
            ["node", "-e", browser_script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert out["multiUsesIndex1"] == "/static/uploads/products/earring-side.png"
    assert out["singleUsesPreview"] == "/static/uploads/products/earring-top.png"


def test_shop_js_girdle_not_gated_by_allows_engraving():
    """腰圍刻字 stays visible when allowsEngraving=false (except chain)."""
    src = (ROOT / "public" / "js" / "shop.js").read_text(encoding="utf-8")
    assert "const hasGirdle = state.category !== 'chain';" in src
    assert "const hasGirdle = allows && state.category !== 'chain';" not in src
    # Band/remark still follow allowsEngraving.
    assert "const hasBand = allows && state.category === 'ring';" in src
    assert (
        "const hasRemark = allows && state.category !== 'chain' && state.category !== 'ring' && !isDiamondOnlyCategory();"
        in src
    )


def test_shop_js_merge_preserves_lite_thumb_url():
    """Full product detail omit thumbUrl → keep lite catalog thumb for step-2 grid."""
    import json
    import subprocess

    src = (ROOT / "public" / "js" / "shop.js").read_text(encoding="utf-8")
    assert "function mergeProductIntoCatalog" in src
    assert "!product.thumbUrl && prev?.thumbUrl" in src
    assert "thumbUrl: prev.thumbUrl" in src
    # ensureProductDetail must return merged (not raw full that dropped thumbUrl).
    assert "if (targetCat) return mergeProductIntoCatalog(targetCat, full);" in src

    browser_script = r"""
function isUsableCatalogImageUrl(url) {
  if (!url || typeof url !== 'string') return false;
  const u = url.trim();
  return u.startsWith('/') || /^https?:\/\//i.test(u);
}
function mergeProductIntoCatalog(catalog, category, product) {
  if (!category || !product?.id) return product;
  const list = catalog[category] || (catalog[category] = []);
  const idx = list.findIndex((p) => String(p.id) === String(product.id));
  if (idx >= 0) {
    const prev = list[idx];
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
function styleGridImageUrl(product, isUsable) {
  if (product?.thumbUrl && isUsable(product.thumbUrl)) return product.thumbUrl;
  return '';
}

const catalog = {
  ring: [{ id: 'prod-1', thumbUrl: '/static/uploads/products/lite-thumb.png' }],
};
const full = { id: 'prod-1', weights: { '14k': { '0.3': 1 } }, images: {} };
const merged = mergeProductIntoCatalog(catalog, 'ring', full);
const fullWithThumb = { id: 'prod-1', thumbUrl: '/static/uploads/products/full-thumb.png', weights: {} };
const replaced = mergeProductIntoCatalog(
  { ring: [{ id: 'prod-1', thumbUrl: '/static/uploads/products/lite-thumb.png' }] },
  'ring',
  fullWithThumb,
);
console.log(JSON.stringify({
  preserved: merged.thumbUrl,
  catalogThumb: catalog.ring[0].thumbUrl,
  hasWeights: !!merged.weights,
  preferFullThumb: replaced.thumbUrl,
  gridUsesThumb: styleGridImageUrl(merged, isUsableCatalogImageUrl),
  omitKeepsEmpty: mergeProductIntoCatalog(
    { ring: [{ id: 'prod-2' }] },
    'ring',
    { id: 'prod-2', weights: {} },
  ).thumbUrl || null,
}));
"""
    out = json.loads(
        subprocess.run(
            ["node", "-e", browser_script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert out["preserved"] == "/static/uploads/products/lite-thumb.png"
    assert out["catalogThumb"] == "/static/uploads/products/lite-thumb.png"
    assert out["hasWeights"] is True
    assert out["preferFullThumb"] == "/static/uploads/products/full-thumb.png"
    assert out["gridUsesThumb"] == "/static/uploads/products/lite-thumb.png"
    assert out["omitKeepsEmpty"] is None


def test_shop_js_style_grid_prefers_upload_over_bracelet_stock():
    """Step 2: lite bracelet with styleKey must show admin thumb, not 手鍊A stock PNG."""
    import json
    import subprocess

    browser_script = r"""
function isUsableCatalogImageUrl(url) {
  if (!url) return false;
  const path = String(url).split('?', 1)[0].replace(/\\/g, '/').toLowerCase();
  if (path.endsWith('.svg')) return false;
  if (/\/images\/shop\/styles\//i.test(path)) return false;
  if (/(?:^|\/)(?:static\/)?images\/shop-product(?:\/|$)/.test(path)) return false;
  return true;
}
function productHasCatalogImages(product) {
  if (!product?.images || typeof product.images !== 'object') return false;
  return Object.values(product.images).some((list) => {
    const arr = Array.isArray(list) ? list : list ? [list] : [];
    return arr.some(isUsableCatalogImageUrl);
  });
}
function productAssetId(product) {
  if (!product) return '';
  if (product.thumbUrl && isUsableCatalogImageUrl(product.thumbUrl)) return '';
  if (productHasCatalogImages(product)) return '';
  if (product.styleKey && /^[a-z]+-[A-C]$/i.test(String(product.styleKey))) {
    return String(product.styleKey);
  }
  return '';
}
function styleGridImageUrl(product) {
  if (product?.thumbUrl && isUsableCatalogImageUrl(product.thumbUrl)) return product.thumbUrl;
  const assetId = productAssetId(product);
  if (assetId) return '/static/images/shop-product/silver/手鍊A_silver.png';
  return '';
}
const upload = '/static/uploads/products/bracelet-custom.png';
const product = {
  id: 'uuid-bracelet-1',
  category: 'bracelet',
  styleKey: 'bracelet-A',
  thumbUrl: upload,
  colors: ['white-white'],
};
console.log(JSON.stringify({
  gridSrc: styleGridImageUrl(product),
  assetId: productAssetId(product),
}));
"""
    out = json.loads(
        subprocess.run(
            ["node", "-e", browser_script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert out["gridSrc"] == "/static/uploads/products/bracelet-custom.png"
    assert out["assetId"] == ""


def test_shop_js_catalog_cross_diamond_image_fallback():
    """White↔fancy catalog slots fall back to next upload; preview keeps fancy strict."""
    import json
    import subprocess

    browser_script = r"""
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assetsSrc = fs.readFileSync(path.join('public', 'js', 'shop-assets.js'), 'utf8');
const sandbox = { window: { shopConfig: { imageRoot: '/static/images/shop-product/' } }, console };
sandbox.global = sandbox.window;
vm.runInNewContext(assetsSrc, sandbox);
const ShopAssets = sandbox.window.ShopAssets;

function isUsableCatalogImageUrl(url) {
  if (!url) return false;
  const path = String(url).split('?', 1)[0].replace(/\\/g, '/').toLowerCase();
  if (path.endsWith('.svg')) return false;
  if (/\/images\/shop\/styles\//i.test(path)) return false;
  if (/(?:^|\/)(?:static\/)?images\/shop-product(?:\/|$)/.test(path)) return false;
  return true;
}
function catalogImagesForKeys(product, keys) {
  if (!product?.images || !keys?.length) return [];
  for (const key of keys) {
    const val = product.images[key];
    const list = Array.isArray(val) ? val.filter(isUsableCatalogImageUrl) : (typeof val === 'string' && isUsableCatalogImageUrl(val) ? [val] : []);
    if (list.length) return list;
  }
  return [];
}
function firstAnyCatalogImageUrl(product) {
  if (!product?.images) return '';
  const keyOrder = Array.isArray(product.colors) && product.colors.length ? product.colors : Object.keys(product.images);
  for (const key of keyOrder) {
    const urls = catalogImagesForKeys(product, [key]);
    if (urls.length) return urls[0];
  }
  for (const list of Object.values(product.images)) {
    const normalized = (Array.isArray(list) ? list : list ? [list] : []).filter(isUsableCatalogImageUrl);
    if (normalized.length) return normalized[0];
  }
  return '';
}
function catalogImageCrossDiamondFallback(product, metal, diamond, chainMetal, opts) {
  opts = opts || {};
  if (!product?.images) return '';
  const m = metal || 'white';
  const d = diamond || 'white';
  const chain = chainMetal || null;
  const fancyIds = ['yellow', 'blue', 'pink'];
  if (d === 'white') {
    for (const fd of fancyIds) {
      const keys = ShopAssets.imageSlotKeysForLookup(m, fd, chain);
      const urls = catalogImagesForKeys(product, keys);
      if (urls.length) return urls[0];
    }
  } else if (fancyIds.includes(d) && opts.allowWhiteForFancy !== false) {
    const keys = ShopAssets.imageSlotKeysForLookup(m, 'white', chain);
    const urls = catalogImagesForKeys(product, keys);
    if (urls.length) return urls[0];
  }
  return firstAnyCatalogImageUrl(product);
}
function catalogPreviewSrc(product, metal, diamond, chainMetal) {
  if (!product?.images) return '';
  const d = diamond || 'white';
  let keys;
  if (d !== 'white') {
    keys = [];
    if (chainMetal) keys.push(ShopAssets.buildImageSlotKey(metal, d, chainMetal));
    keys.push(ShopAssets.buildImageSlotKey(metal, d));
  } else {
    keys = ShopAssets.imageSlotKeysForLookup(metal, d, chainMetal || null);
  }
  return catalogImagesForKeys(product, keys)[0] || '';
}
function styleGridImageUrl(product) {
  const whiteKeys = ShopAssets.imageSlotKeysForLookup('white', 'white', null);
  const fromCatalog = catalogImagesForKeys(product, whiteKeys)[0];
  if (fromCatalog) return fromCatalog;
  const crossCatalog = catalogImageCrossDiamondFallback(product, 'white', 'white', null);
  if (crossCatalog) return crossCatalog;
  return '';
}
function productImagesForColor(product, metalColor, diamondColor) {
  const metal = metalColor || 'white';
  const diamond = diamondColor || 'white';
  if (diamond !== 'white') {
    const exactKeys = [ShopAssets.buildImageSlotKey(metal, diamond)];
    const fromExact = catalogImagesForKeys(product, exactKeys);
    if (fromExact.length) return fromExact;
  } else {
    const whiteKeys = ShopAssets.imageSlotKeysForLookup(metal, 'white', null);
    const fromWhite = catalogImagesForKeys(product, whiteKeys);
    if (fromWhite.length) return fromWhite;
    const crossWhite = catalogImageCrossDiamondFallback(product, metal, 'white', null);
    if (crossWhite) return [crossWhite];
  }
  if (diamond !== 'white') {
    const crossFancy = catalogImageCrossDiamondFallback(product, metal, diamond, null);
    if (crossFancy) return [crossFancy];
  }
  return [];
}

const fancyOnly = {
  id: 'uuid-ring-fancy',
  category: 'ring',
  colors: ['white-pink'],
  images: { 'white-pink': ['/static/uploads/products/ring-pink-only.png'] },
};
const whiteOnly = {
  id: 'uuid-ring-white',
  category: 'ring',
  colors: ['white-white'],
  images: { 'white-white': ['/static/uploads/products/ring-white-only.png'] },
};

console.log(JSON.stringify({
  gridFancy: styleGridImageUrl(fancyOnly),
  gridWhite: styleGridImageUrl(whiteOnly),
  previewPinkStrict: catalogPreviewSrc(whiteOnly, 'white', 'pink', null),
  previewPinkLoose: productImagesForColor(whiteOnly, 'white', 'pink')[0] || '',
  previewWhiteFromFancy: productImagesForColor(fancyOnly, 'white', 'white')[0] || '',
}));
"""
    out = json.loads(
        subprocess.run(
            ["node", "-e", browser_script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert out["gridFancy"] == "/static/uploads/products/ring-pink-only.png"
    assert out["gridWhite"] == "/static/uploads/products/ring-white-only.png"
    assert out["previewPinkStrict"] == ""
    assert out["previewPinkLoose"] == "/static/uploads/products/ring-white-only.png"
    assert out["previewWhiteFromFancy"] == "/static/uploads/products/ring-pink-only.png"


def test_shop_js_style_grid_ordered_image_fallback_chain():
    """Step 2 grid walks admin slot order; broken primary advances via fallback chain."""
    import json
    import subprocess

    browser_script = r"""
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assetsSrc = fs.readFileSync(path.join('public', 'js', 'shop-assets.js'), 'utf8');
const sandbox = { window: { shopConfig: { imageRoot: '/static/images/shop-product/' } }, console };
sandbox.global = sandbox.window;
vm.runInNewContext(assetsSrc, sandbox);
const ShopAssets = sandbox.window.ShopAssets;

const IMAGE_SLOT_METALS = ['white', 'yellow', 'rose'];
const IMAGE_SLOT_DIAMONDS = ['white', 'yellow', 'blue', 'pink'];

function isUsableCatalogImageUrl(url) {
  if (!url) return false;
  const p = String(url).split('?', 1)[0].replace(/\\/g, '/').toLowerCase();
  if (p.endsWith('.svg')) return false;
  if (/\/images\/shop\/styles\//i.test(p)) return false;
  if (/(?:^|\/)(?:static\/)?images\/shop-product(?:\/|$)/.test(p)) return false;
  if (/\/products\/_pending\//i.test(p) || /\/_pending\//i.test(p)) return false;
  return true;
}
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
function presetImageSlotKeys(category) {
  const cat = String(category || '').toLowerCase();
  if (cat === 'chain') return IMAGE_SLOT_METALS.map((m) => m + '-white');
  const keys = [];
  for (const metal of IMAGE_SLOT_METALS) {
    for (const diamond of IMAGE_SLOT_DIAMONDS) keys.push(metal + '-' + diamond);
  }
  return keys;
}
function catalogUrlsForImageSlot(product, slotKey) {
  const parts = String(slotKey || '').split('-');
  if (parts.length >= 2 && IMAGE_SLOT_METALS.includes(parts[0]) && IMAGE_SLOT_DIAMONDS.includes(parts[1])) {
    const keys = ShopAssets.imageSlotKeysForLookup(parts[0], parts[1], null);
    return catalogImagesForKeys(product, keys);
  }
  if (IMAGE_SLOT_METALS.includes(slotKey)) {
    return catalogImagesForKeys(product, ShopAssets.imageSlotKeysForLookup(slotKey, 'white', null));
  }
  return catalogImagesForKeys(product, [slotKey]);
}
function defaultColorImageSlotKeys(product) {
  const metal = String(product?.defaultColor || 'white').toLowerCase();
  const cat = String(product?.category || '').toLowerCase();
  if (cat === 'chain') return [metal + '-white', metal];
  const keys = [metal + '-white'];
  for (const diamond of IMAGE_SLOT_DIAMONDS) {
    if (diamond !== 'white') keys.push(metal + '-' + diamond);
  }
  return keys;
}
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
    if (IMAGE_SLOT_METALS.includes(key)) pushKey(key + '-white');
    else pushKey(key);
  }
  return order;
}
function orderedCatalogImageUrls(product) {
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
function styleGridImageCandidates(product) {
  const out = [];
  const seen = new Set();
  const add = (url) => {
    if (!url || seen.has(url)) return;
    seen.add(url);
    out.push(url);
  };
  for (const url of orderedCatalogImageUrls(product)) add(url);
  if (product?.thumbUrl && isUsableCatalogImageUrl(product.thumbUrl)) {
    add(product.thumbUrl);
  }
  return out;
}

const broken = '/static/uploads/products/platinum-white-broken.png';
const goodYellow = '/static/uploads/products/platinum-white-yellow.png';
const goodRose = '/static/uploads/products/rose-white.png';
const product = {
  id: 'uuid-ring-broken',
  category: 'ring',
  imageSlotOrder: ['white-white', 'white-yellow', 'rose-white'],
  colors: ['white-white', 'white-yellow', 'rose-white'],
  images: {
    'white-white': [broken],
    'white-yellow': [goodYellow],
    'rose-white': [goodRose],
  },
  thumbUrl: '/static/uploads/products/thumb-fallback.png',
};

const productRoseFirst = {
  id: 'uuid-ring-rose-first',
  category: 'ring',
  defaultColor: 'white',
  imageSlotOrder: ['rose-white', 'white-yellow', 'white-white'],
  colors: ['rose-white', 'white-yellow', 'white-white'],
  images: {
    'white-white': [broken],
    'white-yellow': [goodYellow],
    'rose-white': [goodRose],
  },
};

const goodWhite = '/static/uploads/products/white-white.png';
const litePendant = {
  id: '408642ff-0000-0000-0000-000000000001',
  category: 'pendant',
  defaultColor: 'white',
  imageSlotOrder: ['rose-white', 'white-white'],
  colors: ['rose-white', 'white-white'],
  thumbUrl: goodWhite,
};

const candidates = styleGridImageCandidates(product);
const roseFirst = styleGridImageCandidates(productRoseFirst);
const litePrimary = styleGridImageCandidates(litePendant)[0];
console.log(JSON.stringify({
  slotOrder: catalogImageSlotKeyOrder(product),
  ordered: orderedCatalogImageUrls(product),
  primary: candidates[0],
  fallbacks: candidates.slice(1),
  roseFirstPrimary: roseFirst[0],
  roseFirstOrder: catalogImageSlotKeyOrder(productRoseFirst),
  litePrimary: litePrimary,
  skipsPending: orderedCatalogImageUrls({
    category: 'ring',
    imageSlotOrder: ['white-yellow'],
    images: { 'white-white': ['/static/products/_pending/x.png'], 'white-yellow': [goodYellow] },
  }),
}));
"""
    out = json.loads(
        subprocess.run(
            ["node", "-e", browser_script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert out["slotOrder"] == ["white-white", "white-yellow", "rose-white"]
    assert out["ordered"] == [
        "/static/uploads/products/platinum-white-broken.png",
        "/static/uploads/products/platinum-white-yellow.png",
        "/static/uploads/products/rose-white.png",
    ]
    assert out["primary"] == "/static/uploads/products/platinum-white-broken.png"
    assert out["fallbacks"] == [
        "/static/uploads/products/platinum-white-yellow.png",
        "/static/uploads/products/rose-white.png",
        "/static/uploads/products/thumb-fallback.png",
    ]
    assert out["roseFirstPrimary"] == "/static/uploads/products/platinum-white-broken.png"
    assert out["roseFirstOrder"] == ["white-white", "white-yellow", "rose-white"]
    assert out["litePrimary"] == "/static/uploads/products/white-white.png"
    assert "/static/uploads/products/platinum-white-yellow.png" in out["ordered"]
    assert out["skipsPending"] == ["/static/uploads/products/platinum-white-yellow.png"]


def test_validate_product_variant_rejects_unconfigured_combo(monkeypatch):
    body = {
        "category": "ring",
        "type": "ring-A",
        "gold": "14k",
        "carat": "0.5",
    }

    def fake_get_product_variant(cur, **kwargs):
        assert kwargs["gold"] == "14k"
        assert kwargs["carat"] == "0.5"
        return None

    monkeypatch.setattr(
        "app.controllers.shop_controller.get_product_variant",
        fake_get_product_variant,
    )
    err = _validate_product_variant(_VariantCursor(), body)
    assert err == "所選金屬或克拉不在此商品款式選項中"


def test_build_catalog_exposes_image_slot_colors_for_metal_filter():
    """Shop 金屬顏色 options are derived from admin image slot keys + defaultColor."""
    product = {
        "id": "prod-color",
        "category": "pendant",
        "name_zh": "Yellow Only",
        "name_en": None,
        "description_zh": None,
        "description_en": None,
        "default_color": "yellow",
        "sort_order": 0,
        "is_published": True,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }
    variants = [{"gold": "14k", "carat": "0.3", "weight_chin": 1.0}]
    images = [
        {
            "color": "yellow-white",
            "file_path": "/static/uploads/products/yellow.png",
        }
    ]

    # Missing file on disk is dropped from images map; colors still come from keys
    # that survive — use empty images list and assert defaultColor is on entry.
    entry = build_catalog_product(product, variants, [])
    assert entry["defaultColor"] == "yellow"

    entry_with = build_catalog_product(
        product,
        variants,
        [{"color": "yellow-white", "file_path": "https://cdn.example/y.png"}],
    )
    assert "yellow-white" in entry_with["colors"]


def test_validate_product_variant_accepts_configured_combo(monkeypatch):
    body = {
        "category": "ring",
        "type": "ring-A",
        "gold": "14k",
        "carat": "0.3",
    }

    def fake_get_product_variant(cur, **kwargs):
        return {"gold": "14k", "carat": "0.3", "weight_chin": 1.0}

    monkeypatch.setattr(
        "app.controllers.shop_controller.get_product_variant",
        fake_get_product_variant,
    )
    assert _validate_product_variant(_VariantCursor(), body) is None
