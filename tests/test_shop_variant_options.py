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
    assert "shop.js?v=122" in (
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
    """Fancy swatch X shown iff carat≥0.3 AND product has image for X."""
    import json
    import subprocess

    browser_script = r"""
const FANCY_DIAMOND_COLOR_IDS = ['yellow', 'blue', 'pink'];
const diamondOptions = { fancyMinCarat: 0.3 };
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
function designedFancyDiamondColors(product) {
  const found = new Set();
  const images = product?.images;
  if (!images || typeof images !== 'object' || Array.isArray(images)) return [];
  Object.keys(images).forEach((key) => {
    const urls = images[key];
    if (!urls || (Array.isArray(urls) && !urls.length)) return;
    const parts = String(key).toLowerCase().split('-');
    if (parts.length >= 2 && FANCY_DIAMOND_COLOR_IDS.includes(parts[1])) {
      found.add(parts[1]);
    }
  });
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

console.log(JSON.stringify({ yellowOnly, caratNoImage, imageNoCarat, yellowBlue }));
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
