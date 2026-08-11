"""Pendant with admin 款式選項 + attached chain must quote from wax weights."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from app.pricing import compute_order_pricing, get_product_variant, normalize_gold

ROOT = Path(__file__).resolve().parents[1]


def test_normalize_gold_aliases():
    assert normalize_gold("9K") == "9k"
    assert normalize_gold("PT950") == "pt950"
    assert normalize_gold("pt") == "pt950"
    assert normalize_gold("S925") == "s925"


def test_get_product_variant_normalizes_gold(monkeypatch):
    seen_golds: list[str] = []

    def fake_execute(query, params=None):
        if params:
            seen_golds.append(params[2])

    cur = MagicMock()
    cur.execute.side_effect = fake_execute
    cur.fetchone.return_value = {"gold": "9k", "carat": "0.1", "weight_chin": 0.33}

    monkeypatch.setattr(
        "app.pricing.resolve_product_id",
        lambda *a, **k: "prod-1",
    )
    row = get_product_variant(cur, category="pendant", product_id="prod-1", gold="9K", carat="0.1")
    assert row is not None
    assert seen_golds == ["9k"]


def test_compute_order_pricing_pendant_with_chain(monkeypatch):
    pendant_variant = {
        "weight_chin": 0.33,
        "manual_price_twd": None,
        "side_stone_price_twd": None,
        "side_stone_carat": None,
    }
    chain_variant = {"weight_chin": 0.014, "manual_price_twd": None}

    def fake_get_product_variant(cur, **kwargs):
        if kwargs["category"] == "pendant":
            assert kwargs["gold"] == "9k"
            assert kwargs["carat"] == "0.1"
            return pendant_variant
        if kwargs["category"] == "chain":
            assert kwargs["gold"] == "9k"
            return chain_variant
        return None

    def fake_get_metal_prices(cur):
        return {"XAU": 4300.0, "XPT": 1050.0, "XAG": 61.0}

    def fake_load_overrides(cur):
        return {}

    monkeypatch.setattr("app.pricing.get_product_variant", fake_get_product_variant)
    monkeypatch.setattr("app.pricing.get_metal_prices", fake_get_metal_prices)
    monkeypatch.setattr("app.pricing.load_overrides", fake_load_overrides)
    monkeypatch.setattr(
        "app.pricing._product_length_weights",
        lambda cur, pid: {
            "1.0mm": {"36": 0.014},
            "2.5mm": {"36": 0.047},
        } if pid == "chain-uuid" else None,
    )
    monkeypatch.setattr(
        "app.pricing.resolve_product_id",
        lambda cur, **kwargs: kwargs.get("type_ref"),
    )

    cur = MagicMock()
    pricing = compute_order_pricing(
        cur,
        {
            "category": "pendant",
            "type": "pendant-uuid",
            "gold": "9K",
            "carat": "0.1",
            "includeChain": True,
            "chainProductId": "chain-uuid",
            "chainGold": "9k",
            "chainLength": 36,
            "diamondKind": "white",
            "diamondShape": "round",
        },
    )
    assert pricing["ready"] is True
    assert pricing["diamondPrice"] == 24000
    assert pricing["chainPrice"] is not None
    assert pricing["total"] > pricing["diamondPrice"]


def test_compute_order_pricing_pendant_chain_thickness_changes_price(monkeypatch):
    """Attached-chain thickness must feed wax lookup (not hard-coded 1.0mm)."""
    pendant_variant = {
        "weight_chin": 0.33,
        "manual_price_twd": None,
        "side_stone_price_twd": None,
        "side_stone_carat": None,
    }
    chain_variant = {"weight_chin": 0.014, "manual_price_twd": None}
    seen_chain_carats: list[str] = []

    def fake_get_product_variant(cur, **kwargs):
        if kwargs["category"] == "pendant":
            return pendant_variant
        if kwargs["category"] == "chain":
            seen_chain_carats.append(kwargs["carat"])
            return chain_variant
        return None

    monkeypatch.setattr("app.pricing.get_product_variant", fake_get_product_variant)
    monkeypatch.setattr(
        "app.pricing.get_metal_prices",
        lambda cur: {"XAU": 4300.0, "XPT": 1050.0, "XAG": 61.0},
    )
    monkeypatch.setattr("app.pricing.load_overrides", lambda cur: {})
    monkeypatch.setattr(
        "app.pricing._product_length_weights",
        lambda cur, pid: {
            "1.0mm": {"36": 0.014},
            "2.5mm": {"36": 0.047},
        } if pid == "chain-uuid" else None,
    )
    monkeypatch.setattr(
        "app.pricing.resolve_product_id",
        lambda cur, **kwargs: kwargs.get("type_ref"),
    )

    base = {
        "category": "pendant",
        "type": "pendant-uuid",
        "gold": "9k",
        "carat": "0.1",
        "includeChain": True,
        "chainProductId": "chain-uuid",
        "chainGold": "9k",
        "chainLength": 36,
        "diamondKind": "white",
        "diamondShape": "round",
    }
    cur = MagicMock()
    thin = compute_order_pricing(cur, {**base, "chainThickness": "1.0mm"})
    thick = compute_order_pricing(cur, {**base, "chainThickness": "2.5mm"})
    assert thin["ready"] is True
    assert thick["ready"] is True
    assert thin["chainPrice"] is not None
    assert thick["chainPrice"] is not None
    assert thick["chainPrice"] > thin["chainPrice"]
    assert thick["total"] > thin["total"]
    assert seen_chain_carats == ["1.0mm", "2.5mm"]


def test_browser_pendant_admin_variant_with_chain_without_length_weights():
    """Chain SKU without lengthWeights uses Excel/抖圓鏈 type table."""
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
const catalog = {
  pendant: [{
    id: 'p1',
    weights: {'9k': {'0.1': 0.33}},
    manualPrices: {},
  }],
  chain: [{
    id: 'c1',
    weights: {'9k': {'1.0mm': 0.014}},
    manualPrices: {},
  }],
};
const payload = {
  category: 'pendant',
  type: 'p1',
  gold: '9K',
  carat: '0.1',
  includeChain: true,
  chainProductId: 'c1',
  chainGold: '9k',
  chainLength: 36,
  diamondKind: 'white',
  diamondShape: 'round',
};
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
    # Empty lengthWeights → Excel/抖圓鏈 type table (default douyuan).
    assert quote["ready"] is True


def test_browser_pendant_chain_thickness_changes_price():
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
pricing.setLiveGoldRates({'9k': 1});
const catalog = {
  pendant: [{
    id: 'p1',
    weights: {'9k': {'0.1': 0.33}},
    manualPrices: {},
  }],
  chain: [{
    id: 'c1',
    chainType: 'douyuan',
    weights: {'9k': {'1.0mm': 0.014}},
    lengthWeights: {},
    manualPrices: {},
  }],
};
function quote(thickness) {
  return pricing.computeOrderPricing({
    category: 'pendant',
    type: 'p1',
    gold: '9k',
    carat: '0.1',
    includeChain: true,
    chainProductId: 'c1',
    chainGold: '9k',
    chainThickness: thickness,
    chainLength: 36,
    diamondKind: 'white',
    diamondShape: 'round',
  }, catalog);
}
const thin = quote('1.0mm');
const thick = quote('2.5mm');
console.log(JSON.stringify({
  thinReady: thin.ready,
  thickReady: thick.ready,
  thinChain: thin.chainPrice,
  thickChain: thick.chainPrice,
}));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["thinReady"] is True
    assert data["thickReady"] is True
    assert data["thickChain"] > data["thinChain"]


def _manual_pricing_mocks(monkeypatch, pendant_manual=12800):
    pendant_variant = {
        "weight_chin": 0.33,
        "manual_price_twd": pendant_manual,
        "side_stone_price_twd": None,
        "side_stone_carat": None,
    }
    chain_variant = {"weight_chin": 0.014, "manual_price_twd": None}

    def fake_get_product_variant(cur, **kwargs):
        if kwargs["category"] == "pendant":
            return pendant_variant
        if kwargs["category"] == "chain":
            return chain_variant
        return None

    monkeypatch.setattr("app.pricing.get_product_variant", fake_get_product_variant)
    monkeypatch.setattr(
        "app.pricing.get_metal_prices",
        lambda cur: {"XAU": 4300.0, "XPT": 1050.0, "XAG": 61.0},
    )
    monkeypatch.setattr("app.pricing.load_overrides", lambda cur: {})
    monkeypatch.setattr(
        "app.pricing._product_length_weights",
        lambda cur, pid: {"1.0mm": {"36": 0.014}} if pid == "chain-uuid" else None,
    )
    monkeypatch.setattr(
        "app.pricing.resolve_product_id",
        lambda cur, **kwargs: kwargs.get("type_ref"),
    )


def test_compute_order_pricing_manual_pendant_with_chain(monkeypatch):
    """手動定價 pendant sold 含鍊: chain addon stacks on the manual price."""
    _manual_pricing_mocks(monkeypatch)
    cur = MagicMock()
    pricing = compute_order_pricing(
        cur,
        {
            "category": "pendant",
            "type": "pendant-uuid",
            "gold": "9K",
            "carat": "0.1",
            "includeChain": True,
            "chainProductId": "chain-uuid",
            "chainGold": "9k",
            "chainLength": 36,
            "diamondKind": "white",
            "diamondShape": "round",
        },
    )
    assert pricing["ready"] is True
    assert pricing["manualOverride"] is True
    assert pricing["chainPrice"] is not None
    assert pricing["chainPrice"] > 0
    assert pricing["total"] == 12800 + pricing["chainPrice"]


def test_compute_order_pricing_manual_pendant_without_chain(monkeypatch):
    """手動定價 pendant sold 單墜: no chain line, total unchanged."""
    _manual_pricing_mocks(monkeypatch)
    cur = MagicMock()
    pricing = compute_order_pricing(
        cur,
        {
            "category": "pendant",
            "type": "pendant-uuid",
            "gold": "9K",
            "carat": "0.1",
            "includeChain": False,
            "diamondKind": "white",
            "diamondShape": "round",
        },
    )
    assert pricing["ready"] is True
    assert pricing["manualOverride"] is True
    assert pricing["chainPrice"] is None
    assert pricing["total"] == 12800


def test_compute_order_pricing_manual_earring_ignores_chain_flags(monkeypatch):
    """Non-pendant manual items never get a chain addon, even if flags are sent."""
    earring_variant = {
        "weight_chin": 0.2,
        "manual_price_twd": 9900,
        "side_stone_price_twd": None,
        "side_stone_carat": None,
    }
    monkeypatch.setattr(
        "app.pricing.get_product_variant",
        lambda cur, **kwargs: earring_variant if kwargs["category"] == "earring" else None,
    )
    monkeypatch.setattr(
        "app.pricing.get_metal_prices",
        lambda cur: {"XAU": 4300.0, "XPT": 1050.0, "XAG": 61.0},
    )
    monkeypatch.setattr("app.pricing.load_overrides", lambda cur: {})
    monkeypatch.setattr(
        "app.pricing.resolve_product_id",
        lambda cur, **kwargs: kwargs.get("type_ref"),
    )
    cur = MagicMock()
    pricing = compute_order_pricing(
        cur,
        {
            "category": "earring",
            "type": "earring-uuid",
            "gold": "9K",
            "carat": "0.1",
            "includeChain": True,
            "chainProductId": "chain-uuid",
            "chainGold": "9k",
            "chainLength": 36,
            "diamondKind": "white",
            "diamondShape": "round",
        },
    )
    assert pricing["ready"] is True
    assert pricing["manualOverride"] is True
    assert pricing["chainPrice"] is None
    assert pricing["total"] == 9900


def test_browser_manual_pendant_with_chain():
    """Client quote must match server: manual pendant price + chain = total."""
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
const catalog = {
  pendant: [{
    id: 'p1',
    weights: {'9k': {'0.1': 0.33}},
    manualPrices: {'9k': {'0.1': 12800}},
  }],
  chain: [{
    id: 'c1',
    chainType: 'douyuan',
    weights: {'9k': {'1.0mm': 0.014}},
    lengthWeights: {},
    manualPrices: {},
  }],
  ring: [{
    id: 'r1',
    weights: {'9k': {'0.1': 0.5}},
    manualPrices: {'9k': {'0.1': 9900}},
  }],
};
function quote(payload) {
  return pricing.computeOrderPricing(Object.assign({
    gold: '9K',
    carat: '0.1',
    diamondKind: 'white',
    diamondShape: 'round',
  }, payload), catalog);
}
const withChain = quote({
  category: 'pendant', type: 'p1',
  includeChain: true, chainProductId: 'c1', chainGold: '9k', chainLength: 36,
});
const withoutChain = quote({ category: 'pendant', type: 'p1', includeChain: false });
const ringWithChainFlags = quote({
  category: 'ring', type: 'r1',
  includeChain: true, chainProductId: 'c1', chainGold: '9k', chainLength: 36,
});
console.log(JSON.stringify({
  withChain: withChain,
  withoutChain: withoutChain,
  ring: ringWithChainFlags,
}));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    with_chain = data["withChain"]
    assert with_chain["ready"] is True
    assert with_chain["manualOverride"] is True
    assert with_chain["chainPrice"] is not None
    assert with_chain["chainPrice"] > 0
    assert with_chain["total"] == 12800 + with_chain["chainPrice"]

    without_chain = data["withoutChain"]
    assert without_chain["ready"] is True
    assert without_chain["chainPrice"] is None
    assert without_chain["total"] == 12800

    ring = data["ring"]
    assert ring["ready"] is True
    assert ring["chainPrice"] is None
    assert ring["total"] == 9900
