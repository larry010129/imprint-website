"""Chain/necklace admin length wax weights — save, catalog, and quote wiring."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from app.admin_products import validate_product_fields
from app.pricing import _chain_wax_from_length_weights, _lookup_weight

ROOT = Path(__file__).resolve().parents[1]

ADMIN_CHAIN_LENGTHS = {
    "1.5mm": {"36": 0.099, "46": 0.033, "80": 0.057},
}


def _chain_publish_body(**overrides):
    body = {
        "category": "chain",
        "nameZh": "測試鍊條",
        "defaultColor": "white",
        "isPublished": True,
        "variants": [
            {"gold": "18k", "carat": "1.5mm", "weightChin": 0.018},
        ],
        "lengthWeights": ADMIN_CHAIN_LENGTHS,
        "images": [{"color": "white", "url": "/static/images/shop-product/gold/chain.png"}],
    }
    body.update(overrides)
    return body


def test_validate_chain_length_weights_round_trip():
    body = _chain_publish_body(isPublished=False, images=[])
    cleaned, err = validate_product_fields(body)
    assert err is None
    assert cleaned["lengthWeights"]["1.5mm"]["46"] == 0.033
    assert cleaned["lengthWeights"]["1.5mm"]["36"] == 0.099
    assert cleaned["variants"][0]["weightChin"] == 0.033


def test_validate_chain_publish_uses_excel_type_table_when_length_weights_empty():
    body = _chain_publish_body(lengthWeights=None, chainType="douyuan", images=[])
    body["isPublished"] = False
    cleaned, err = validate_product_fields(body)
    assert err is None
    assert cleaned["lengthWeights"]["1.5mm"]["46"] == 0.033
    assert cleaned["lengthWeights"]["1.0mm"]["36"] == 0.014


def test_chain_wax_from_length_weights_prefers_admin():
    admin = {"1.5mm": {"46": 0.055}}
    assert _chain_wax_from_length_weights(admin, "1.5mm", 46) == 0.055
    assert _chain_wax_from_length_weights(admin, "1.5mm", 36) is None


def test_lookup_weight_chain_uses_admin_length_weights(monkeypatch):
    product_id = "chain-uuid-1"

    def fake_get_product_variant(cur, **kwargs):
        assert kwargs["category"] == "chain"
        return {"weight_chin": 0.018}

    def fake_resolve(cur, **kwargs):
        return product_id

    def fake_length_weights(cur, pid):
        assert pid == product_id
        return ADMIN_CHAIN_LENGTHS

    monkeypatch.setattr("app.pricing.get_product_variant", fake_get_product_variant)
    monkeypatch.setattr("app.pricing.resolve_product_id", fake_resolve)
    monkeypatch.setattr("app.pricing._product_length_weights", fake_length_weights)

    cur = MagicMock()
    looked_up = _lookup_weight(
        cur,
        category="chain",
        product_id=product_id,
        gold="18k",
        carat="1.5mm",
        length_cm=36,
        require_published=True,
    )
    assert looked_up is not None
    _, weight_chin = looked_up
    # 0.099 wax × 16 (18k factor) = 1.584
    assert abs(weight_chin - 1.584) < 1e-6

    looked_up_fallback = _lookup_weight(
        cur,
        category="chain",
        product_id=product_id,
        gold="18k",
        carat="1.5mm",
        length_cm=41,
        require_published=True,
    )
    assert looked_up_fallback is None


def test_browser_quote_prefers_admin_length_weights_over_fallback():
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
pricing.setLiveGoldRates({'18k': 1});
const product = {
  id: 'chain-admin',
  weights: {'18k': {'1.5mm': 0.033}},
  lengthWeights: {'1.5mm': {'36': 0.099, '46': 0.033}},
  manualPrices: {},
};
const catalog = {chain: [product]};
const payload = {category: 'chain', type: 'chain-admin', gold: '18k', carat: '1.5mm', lengthCm: 36};
console.log(JSON.stringify(pricing.computeOrderPricing(payload, catalog)));
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
    # wax 0.099 → metal 1.584 錢; @ live 元/公克=1 → 5.94 元 metal + tax → taijin 6 + labor 2000
    assert quote["taijinPrice"] == 6
    assert quote["total"] == 2006
    assert quote["total"] > 2000


def test_shop_merge_keeps_api_length_weights_only():
    script = """
function structuredClone(v){return JSON.parse(JSON.stringify(v));}
const staticProduct = {
  weights: {'18k': {'1.5mm': 0.033}},
  lengthWeights: {'1.5mm': {'46': 0.018, '36': 0.026}},
};
const product = {
  weights: {'18k': {'1.5mm': 0.033}},
  lengthWeights: {'1.5mm': {'46': 0.033, '36': 0.099}},
};
function mergeProductWeights(product, staticProduct, category) {
  if (category === 'chain') {
    const adminLengths = product.lengthWeights;
    if (adminLengths && Object.keys(adminLengths).length > 0) {
      product.lengthWeights = structuredClone(adminLengths);
    } else {
      product.lengthWeights = {};
    }
  }
}
mergeProductWeights(product, staticProduct, 'chain');
console.log(JSON.stringify(product.lengthWeights));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    merged = json.loads(result.stdout)
    assert merged["1.5mm"]["36"] == 0.099
    assert merged["1.5mm"]["46"] == 0.033
    assert "41" not in merged["1.5mm"]


def test_shop_chain_length_options_use_excel_when_admin_empty():
    """Empty admin lengthWeights → Excel/type lengths (抖圓鏈)."""
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
function necklaceTypeLengthWeights(chainType) {
  return window.ShopPricingLocal.lengthWeightsForChainType(chainType) || {};
}
function effectiveChainLengthWeights(product) {
  const admin = product && product.lengthWeights;
  if (admin && typeof admin === 'object' && Object.keys(admin).length > 0) return admin;
  return necklaceTypeLengthWeights((product && product.chainType) || 'douyuan');
}
function chainLengthOptionsCm(product, thickness) {
  if (!product || !thickness) return [];
  const table = effectiveChainLengthWeights(product)[thickness];
  if (!table || typeof table !== 'object') return [];
  return Object.keys(table)
    .map((k) => parseInt(k, 10))
    .filter((n) => !Number.isNaN(n) && Number(table[String(n)]) > 0)
    .sort((a, b) => a - b);
}
const adminOnly = chainLengthOptionsCm({lengthWeights: {'1.5mm': {'36': 0.099, '46': 0.033}}}, '1.5mm');
const fromExcel = chainLengthOptionsCm({lengthWeights: {}, chainType: 'douyuan'}, '1.5mm');
console.log(JSON.stringify({adminOnly, fromExcel}));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["adminOnly"] == [36, 46]
    assert data["fromExcel"] == [36, 41, 46, 51, 61, 76, 80]


def test_browser_quote_uses_excel_for_unconfigured_length():
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
pricing.setLiveGoldRates({'18k': 1});
const product = {
  id: 'chain-admin',
  chainType: 'douyuan',
  weights: {'18k': {'1.5mm': 0.033}},
  lengthWeights: {},
  manualPrices: {},
};
const catalog = {chain: [product]};
const payload = {category: 'chain', type: 'chain-admin', gold: '18k', carat: '1.5mm', lengthCm: 41};
console.log(JSON.stringify(pricing.computeOrderPricing(payload, catalog)));
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
