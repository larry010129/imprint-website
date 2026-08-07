"""手動定價 — admin load/save for all variant categories + chain override."""

from __future__ import annotations

import json
import subprocess
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from app.admin_products import normalize_variant_row_for_admin, validate_product_fields
from app.pricing import compute_order_pricing


ROOT = Path(__file__).resolve().parents[1]
ADMIN_PRODUCTS_JS = ROOT / "public" / "js" / "admin-products.js"
ADMIN_HTML = ROOT / "admin.html"


def _variant_body(category: str, **variant_extra):
    carat = "1.5mm" if category == "chain" else "0.3"
    variant = {
        "gold": "18k",
        "carat": carat,
        "weightChin": 0.02 if category != "chain" else None,
        "manualPriceTwd": 12800,
    }
    variant.update(variant_extra)
    body = {
        "category": category,
        "nameZh": f"測試{category}",
        "nameEn": f"Test {category}",
        "defaultColor": "white",
        "isPublished": False,
        "variants": [variant],
        "images": [],
    }
    if category == "chain":
        body["chainType"] = "douyuan"
        body["lengthWeights"] = {"1.5mm": {"46": 0.033}}
    return body


def test_validate_keeps_manual_price_for_all_variant_categories():
    for category in ("pendant", "ring", "earring", "bracelet", "chain"):
        cleaned, err = validate_product_fields(_variant_body(category))
        assert err is None, category
        assert cleaned["variants"][0]["manualPriceTwd"] == 12800.0, category


def test_validate_accepts_snake_case_manual_price():
    body = _variant_body("ring")
    body["variants"][0] = {
        "gold": "18k",
        "carat": "0.3",
        "weightChin": 0.02,
        "manual_price_twd": 9900,
    }
    cleaned, err = validate_product_fields(body)
    assert err is None
    assert cleaned["variants"][0]["manualPriceTwd"] == 9900.0


def test_normalize_variant_exposes_float_and_camel_manual_price():
    row = normalize_variant_row_for_admin(
        {
            "id": 1,
            "product_id": 2,
            "gold": "18k",
            "carat": "0.3",
            "weight_chin": Decimal("0.0200"),
            "manual_price_twd": Decimal("12800"),
            "addon_price_twd": None,
        }
    )
    assert row["manual_price_twd"] == 12800.0
    assert row["manualPriceTwd"] == 12800.0
    assert isinstance(row["weight_chin"], float)


def test_server_chain_honors_manual_price(monkeypatch):
    monkeypatch.setattr(
        "app.pricing._lookup_weight",
        lambda *a, **k: (
            {"manual_price_twd": 15000, "addon_price_twd": None},
            0.033,
        ),
    )
    monkeypatch.setattr(
        "app.pricing.get_metal_prices",
        lambda cur: {"XAU": 4000.0, "XPT": 0.0, "XAG": 0.0},
    )
    monkeypatch.setattr("app.pricing.load_overrides", lambda cur: {})
    quote = compute_order_pricing(
        MagicMock(),
        {
            "category": "chain",
            "type": "c1",
            "gold": "18k",
            "carat": "1.5mm",
            "lengthCm": 46,
        },
    )
    assert quote["ready"] is True
    assert quote["manualOverride"] is True
    assert quote["total"] == 15000


def test_browser_chain_honors_manual_price():
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
pricing.setLiveGoldRates({'18k': 1});
const product = {
  id: 'chain-A',
  weights: {'18k': {'1.5mm': 0.033}},
  lengthWeights: {'1.5mm': {'46': 0.033}},
  manualPrices: {'18k': {'1.5mm': 15000}},
};
const quote = pricing.computeOrderPricing(
  {category: 'chain', type: 'chain-A', gold: '18k', carat: '1.5mm', lengthCm: 46},
  {chain: [product]}
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
    assert quote["ready"] is True
    assert quote["manualOverride"] is True
    assert quote["total"] == 15000


def test_admin_js_wires_manual_price_for_variant_categories():
    src = ADMIN_PRODUCTS_JS.read_text(encoding="utf-8")
    assert "function variantManualPriceDisplayValue" in src
    assert "手動定價" in src
    assert 'name="price"' in src or "name='price'" in src
    assert "manualPriceTwd" in src
    assert "manual_price_twd" in src
    # Chain head includes 手動定價; jewelry rows share the same input helper.
    assert "category === 'chain'" in src
    assert "variantManualPriceDisplayValue(variant)" in src
    html = ADMIN_HTML.read_text(encoding="utf-8")
    assert "admin-products.js?v=56" in html
