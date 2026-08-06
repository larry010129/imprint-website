"""Per-variant 品項加價 — admin validate, catalog, quote (row ?? category)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from app.admin_products import validate_product_fields
from app.catalog import build_catalog_product
from app.pricing import (
    _effective_addon_price,
    _labor_fee,
    _variant_addon_price,
    compute_order_pricing,
)


ROOT = Path(__file__).resolve().parents[1]
ADMIN_PRODUCTS_JS = ROOT / "public" / "js" / "admin-products.js"


def _ring_body(**overrides):
    body = {
        "category": "ring",
        "nameZh": "測試戒指",
        "nameEn": "Test Ring",
        "defaultColor": "white",
        "isPublished": False,
        "variants": [
            {
                "gold": "18k",
                "carat": "0.3",
                "weightChin": 0.02,
                "addonPriceTwd": 3500,
            }
        ],
        "images": [],
    }
    body.update(overrides)
    return body


def test_validate_keeps_variant_addon_price():
    cleaned, err = validate_product_fields(_ring_body())
    assert err is None
    assert cleaned["variants"][0]["addonPriceTwd"] == 3500.0


def test_validate_accepts_snake_case_addon():
    body = _ring_body()
    body["variants"][0] = {
        "gold": "18k",
        "carat": "0.3",
        "weightChin": 0.02,
        "addon_price_twd": 2200,
    }
    cleaned, err = validate_product_fields(body)
    assert err is None
    assert cleaned["variants"][0]["addonPriceTwd"] == 2200.0


def test_validate_null_addon_when_empty():
    body = _ring_body()
    body["variants"][0]["addonPriceTwd"] = None
    cleaned, err = validate_product_fields(body)
    assert err is None
    assert cleaned["variants"][0]["addonPriceTwd"] is None


def test_validate_rejects_negative_addon():
    body = _ring_body()
    body["variants"][0]["addonPriceTwd"] = -1
    cleaned, err = validate_product_fields(body)
    assert cleaned is None
    assert "品項加價" in (err or "")


def test_variant_addon_helpers():
    assert _variant_addon_price(None) is None
    assert _variant_addon_price({}) is None
    assert _variant_addon_price({"addon_price_twd": 3500}) == 3500
    assert _variant_addon_price({"addonPriceTwd": 1200}) == 1200
    assert _variant_addon_price({"addon_price_twd": -5}) == 0
    cur = MagicMock()
    assert _effective_addon_price(cur, "ring", {"addon_price_twd": 3500}) == 3500


def test_effective_addon_falls_back_to_category(monkeypatch):
    monkeypatch.setattr("app.pricing.category_addon_price", lambda cur, cat: 2000)
    cur = MagicMock()
    assert _effective_addon_price(cur, "ring", {}) == 2000
    assert _effective_addon_price(cur, "ring", {"addon_price_twd": None}) == 2000
    assert _labor_fee("ring", "18k", 2000) == 2000
    assert _labor_fee("ring", "18k", 0) == 5000


def test_catalog_exposes_addon_prices():
    product = {
        "id": "p1",
        "category": "ring",
        "name_zh": "戒指",
        "name_en": "Ring",
        "description_zh": "",
        "description_en": "",
        "default_color": "white",
        "is_published": True,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
        "sort_order": 0,
        "chain_type": None,
        "length_weights": None,
    }
    variants = [
        {
            "gold": "18k",
            "carat": "0.3",
            "weight_chin": 0.02,
            "manual_price_twd": None,
            "side_stone_price_twd": None,
            "side_stone_carat": None,
            "side_stone_total_twd": None,
            "addon_price_twd": 3500,
        }
    ]
    out = build_catalog_product(product, variants, [])
    assert out["addonPrices"]["18k"]["0.3"] == 3500.0


def test_quote_uses_variant_addon_over_category(monkeypatch):
    variant = {
        "weight_chin": 0.01,
        "manual_price_twd": None,
        "side_stone_price_twd": None,
        "side_stone_carat": None,
        "side_stone_total_twd": None,
        "addon_price_twd": 3500,
    }
    monkeypatch.setattr(
        "app.pricing._lookup_weight",
        lambda *a, **k: (variant, 0.01),
    )
    monkeypatch.setattr(
        "app.pricing.get_metal_prices",
        lambda cur: {"XAU": 1.0, "XPT": 1.0, "XAG": 1.0},
    )
    monkeypatch.setattr("app.pricing.load_overrides", lambda cur: {})
    monkeypatch.setattr("app.pricing.category_addon_price", lambda cur, cat: 2000)
    monkeypatch.setattr(
        "app.pricing.compute_diamond_list_price",
        lambda *a, **k: 10000,
    )
    quote = compute_order_pricing(
        MagicMock(),
        {"category": "ring", "type": "r1", "gold": "18k", "carat": "0.3"},
    )
    assert quote["ready"] is True
    assert quote["laborPrice"] == 3500  # row wins over category 2000


def test_quote_falls_back_to_category_addon(monkeypatch):
    variant = {
        "weight_chin": 0.01,
        "manual_price_twd": None,
        "side_stone_price_twd": None,
        "side_stone_carat": None,
        "side_stone_total_twd": None,
        "addon_price_twd": None,
    }
    monkeypatch.setattr(
        "app.pricing._lookup_weight",
        lambda *a, **k: (variant, 0.01),
    )
    monkeypatch.setattr(
        "app.pricing.get_metal_prices",
        lambda cur: {"XAU": 1.0, "XPT": 1.0, "XAG": 1.0},
    )
    monkeypatch.setattr("app.pricing.load_overrides", lambda cur: {})
    monkeypatch.setattr("app.pricing.category_addon_price", lambda cur, cat: 2000)
    monkeypatch.setattr(
        "app.pricing.compute_diamond_list_price",
        lambda *a, **k: 10000,
    )
    quote = compute_order_pricing(
        MagicMock(),
        {"category": "ring", "type": "r1", "gold": "18k", "carat": "0.3"},
    )
    assert quote["ready"] is True
    assert quote["laborPrice"] == 2000


def test_browser_variant_addon_overrides_category():
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
pricing.setLiveGoldRates({'18k': 1});
pricing.setCategoryAddons({ ring: 2000 });
const withRow = {
  id: 'ring-A',
  weights: {'18k': {'0.3': 0.01}},
  manualPrices: {},
  addonPrices: {'18k': {'0.3': 3500}},
};
const noRow = {
  id: 'ring-A',
  weights: {'18k': {'0.3': 0.01}},
  manualPrices: {},
  addonPrices: {},
};
const base = {category: 'ring', type: 'ring-A', carat: '0.3', gold: '18k'};
const override = pricing.computeOrderPricing(base, {ring: [withRow]});
const fallback = pricing.computeOrderPricing(base, {ring: [noRow]});
console.log(JSON.stringify({ override, fallback }));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    out = json.loads(result.stdout)
    assert out["override"]["laborPrice"] == 3500
    assert out["fallback"]["laborPrice"] == 2000


def test_admin_js_wires_variant_addon_column():
    src = ADMIN_PRODUCTS_JS.read_text(encoding="utf-8")
    assert "品項加價 (NT$)" in src
    assert "function variantAddonDisplayValue" in src
    assert "name=\"addonPrice\"" in src or "name='addonPrice'" in src
    assert "addonPriceTwd" in src
    assert "categoryAddonValue(category)" in src
