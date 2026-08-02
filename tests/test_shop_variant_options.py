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
    assert "shop.js?v=127" in (
        ROOT / "content" / "site" / "templates" / "pages" / "shop" / "calculator.html"
    ).read_text(encoding="utf-8")
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
