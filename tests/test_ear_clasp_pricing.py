"""Earring per-row 耳扣價錢 — admin validate, catalog, quote (folded into 金工)."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from app.admin_products import validate_product_fields
from app.catalog import build_catalog_product
from app.pricing import _ear_clasp_fee, compute_order_pricing


ROOT = Path(__file__).resolve().parents[1]


def _earring_body(**overrides):
    body = {
        "category": "earring",
        "nameZh": "測試耳環",
        "nameEn": "Test Earring",
        "defaultColor": "white",
        "isPublished": False,
        "variants": [
            {
                "gold": "18k",
                "carat": "0.3",
                "weightChin": 0.02,
                "earClaspPriceTwd": 800,
            }
        ],
        "images": [],
    }
    body.update(overrides)
    return body


def test_validate_earring_keeps_ear_clasp_price():
    cleaned, err = validate_product_fields(_earring_body())
    assert err is None
    assert cleaned["variants"][0]["earClaspPriceTwd"] == 800.0


def test_validate_ear_clasp_alias_ear_cuff():
    body = _earring_body()
    body["variants"][0] = {
        "gold": "18k",
        "carat": "0.3",
        "weightChin": 0.02,
        "earCuffPriceTwd": 900,
    }
    cleaned, err = validate_product_fields(body)
    assert err is None
    assert cleaned["variants"][0]["earClaspPriceTwd"] == 900.0


def test_validate_ring_drops_ear_clasp_price():
    body = _earring_body(category="ring")
    cleaned, err = validate_product_fields(body)
    assert err is None
    assert cleaned["variants"][0]["earClaspPriceTwd"] is None


def test_validate_rejects_negative_ear_clasp():
    body = _earring_body()
    body["variants"][0]["earClaspPriceTwd"] = -1
    cleaned, err = validate_product_fields(body)
    assert cleaned is None
    assert "耳扣價錢" in (err or "")


def test_ear_clasp_fee_helper():
    assert _ear_clasp_fee(None) == 0
    assert _ear_clasp_fee({}) == 0
    assert _ear_clasp_fee({"ear_clasp_price_twd": 800}) == 800
    assert _ear_clasp_fee({"ear_cuff_price_twd": 500}) == 500
    assert _ear_clasp_fee({"ear_clasp_price_twd": -10}) == 0


def test_catalog_exposes_ear_clasp_prices():
    product = {
        "id": "p1",
        "category": "earring",
        "name_zh": "耳環",
        "name_en": "Earring",
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
            "ear_clasp_price_twd": 800,
        }
    ]
    out = build_catalog_product(product, variants, [])
    assert out["earClaspPrices"]["18k"]["0.3"] == 800.0


def test_compute_order_pricing_folds_ear_clasp_into_labor(monkeypatch):
    variant = {
        "weight_chin": 0.01,
        "manual_price_twd": None,
        "side_stone_price_twd": None,
        "side_stone_carat": None,
        "side_stone_total_twd": None,
        "ear_clasp_price_twd": 800,
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
    monkeypatch.setattr("app.pricing.category_addon_price", lambda cur, cat: 0)
    monkeypatch.setattr(
        "app.pricing.compute_diamond_list_price",
        lambda *a, **k: 10000,
    )
    cur = MagicMock()
    quote = compute_order_pricing(
        cur,
        {
            "category": "earring",
            "type": "e1",
            "gold": "18k",
            "carat": "0.3",
            "quantity": 1,
        },
    )
    assert quote["ready"] is True
    assert quote["laborPrice"] == 5800  # 5000 base + 800 耳扣
    assert quote["metalworkPrice"] == quote["taijinPrice"] + 5800
    assert quote["total"] == 10000 + quote["taijinPrice"] + 5800


def test_compute_order_pricing_addon_replaces_base_plus_ear_clasp(monkeypatch):
    """品項加價 replaces base labor; 耳扣 still folds in on top."""
    variant = {
        "weight_chin": 0.01,
        "manual_price_twd": None,
        "side_stone_price_twd": None,
        "side_stone_carat": None,
        "side_stone_total_twd": None,
        "ear_clasp_price_twd": 800,
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
    cur = MagicMock()
    quote = compute_order_pricing(
        cur,
        {
            "category": "earring",
            "type": "e1",
            "gold": "18k",
            "carat": "0.3",
            "quantity": 1,
        },
    )
    assert quote["ready"] is True
    assert quote["laborPrice"] == 2800  # 2000 addon (not 5000) + 800 耳扣
    assert quote["metalworkPrice"] == quote["taijinPrice"] + 2800
    assert quote["total"] == 10000 + quote["taijinPrice"] + 2800


def test_browser_ear_clasp_adds_to_labor_and_total():
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
pricing.setLiveGoldRates({'18k': 1});
pricing.setCategoryAddons({ earring: 0 });
const product = {
  id: 'earring-A',
  weights: {'18k': {'0.3': 0.01}},
  manualPrices: {},
  earClaspPrices: {'18k': {'0.3': 800}},
};
const catalog = {earring: [product]};
const base = {category: 'earring', type: 'earring-A', carat: '0.3', gold: '18k', quantity: 1};
const withClasp = pricing.computeOrderPricing(base, catalog);
const noClaspProduct = {
  id: 'earring-A',
  weights: {'18k': {'0.3': 0.01}},
  manualPrices: {},
  earClaspPrices: {},
};
const noClasp = pricing.computeOrderPricing(base, {earring: [noClaspProduct]});
console.log(JSON.stringify({ withClasp, noClasp }));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    out = json.loads(result.stdout)
    assert out["noClasp"]["laborPrice"] == 5000
    assert out["withClasp"]["laborPrice"] == 5800
    assert out["withClasp"]["metalworkPrice"] == out["noClasp"]["metalworkPrice"] + 800
    assert out["withClasp"]["total"] == out["noClasp"]["total"] + 800


def test_browser_addon_replaces_base_plus_ear_clasp():
    """Browser: 品項加價 replaces 5000; 耳扣 still adds."""
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
pricing.setLiveGoldRates({'18k': 1});
pricing.setCategoryAddons({ earring: 2000 });
const product = {
  id: 'earring-A',
  weights: {'18k': {'0.3': 0.01}},
  manualPrices: {},
  earClaspPrices: {'18k': {'0.3': 800}},
};
const catalog = {earring: [product]};
const quote = pricing.computeOrderPricing(
  {category: 'earring', type: 'earring-A', carat: '0.3', gold: '18k', quantity: 1},
  catalog
);
console.log(JSON.stringify(quote));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    quote = json.loads(result.stdout)
    assert quote["laborPrice"] == 2800  # 2000 replace + 800 耳扣
    assert quote["metalworkPrice"] == quote["taijinPrice"] + 2800


def test_browser_ring_ignores_ear_clasp_prices():
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
pricing.setLiveGoldRates({'18k': 1});
const product = {
  id: 'ring-A',
  weights: {'18k': {'0.3': 0.01}},
  manualPrices: {},
  earClaspPrices: {'18k': {'0.3': 800}},
};
const catalog = {ring: [product]};
const quote = pricing.computeOrderPricing(
  {category: 'ring', type: 'ring-A', carat: '0.3', gold: '18k'},
  catalog
);
console.log(JSON.stringify(quote));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    quote = json.loads(result.stdout)
    assert quote["laborPrice"] == 5000
