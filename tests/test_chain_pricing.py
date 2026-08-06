import json
import subprocess
from pathlib import Path

import pytest

from app.pricing import (
    CHAIN_LABOR_FEE_TWD,
    CHAIN_WAX_WEIGHT_CHIN,
    CHIN_TO_GRAMS,
    PURITY_MULTIPLIER,
    _chain_wax_chin,
    _labor_fee,
    _metal_pre_tax,
    wax_to_metal_chin,
)


ROOT = Path(__file__).resolve().parents[1]


def test_chain_wax_table_has_all_excel_combinations():
    assert set(CHAIN_WAX_WEIGHT_CHIN) == {"1.0mm", "1.5mm", "2.0mm", "2.5mm", "3.0mm"}
    assert all(set(weights) == {36, 41, 46, 51, 61, 76, 80} for weights in CHAIN_WAX_WEIGHT_CHIN.values())
    assert _chain_wax_chin("1.5mm", 46) == 0.033
    assert _chain_wax_chin("3.0mm", 80) == 0.120


def test_excel_o_chain_formula_uses_shijin_per_chin():
    """鍊條價格.xlsx: 臘重×16×(黃金價×0.85)+3000 for 18K; 黃金價 = 飾金 元/錢."""
    wax = _chain_wax_chin("1.0mm", 36)
    assert wax == 0.014
    metal_chin = wax_to_metal_chin(wax, "18k")
    assert metal_chin == pytest.approx(0.224)
    shijin_per_chin = 17130.0  # Excel P18 sample
    gold_prices = {"XAU": shijin_per_chin / CHIN_TO_GRAMS, "XPT": 0.0, "XAG": 0.0}
    pre_tax, per_gram = _metal_pre_tax(gold_prices, "18k", metal_chin)
    assert per_gram == pytest.approx((shijin_per_chin / CHIN_TO_GRAMS) * PURITY_MULTIPLIER["18k"])
    # Excel: 0.014*16*(17130*0.85)+3000
    expected = 0.014 * 16 * (shijin_per_chin * 0.85) + CHAIN_LABOR_FEE_TWD["other"]
    assert pre_tax + CHAIN_LABOR_FEE_TWD["other"] == pytest.approx(expected)
    # s925 labor path
    assert _labor_fee("chain", "s925") == 500
    s925_metal = wax_to_metal_chin(wax, "s925")
    assert s925_metal == pytest.approx(0.154)


def test_standalone_chain_labor_depends_on_metal():
    assert _labor_fee("chain", "s925") == 500
    assert _labor_fee("chain", "18k") == 3000
    assert _labor_fee("chain", "18k", 0) == 3000
    # 品項加價 > 0 replaces base chain labor (including s925 base)
    assert _labor_fee("chain", "18k", 3000) == 3000
    assert _labor_fee("chain", "18k", 4500) == 4500
    assert _labor_fee("chain", "s925", 800) == 800
    assert _labor_fee("pendant", "s925") == 5000
    assert _labor_fee("pendant", "18k", 0) == 5000
    assert _labor_fee("pendant", "18k", 6000) == 6000


def test_category_addon_replaces_base_labor():
    """品項加價 > 0 replaces base; 0 keeps default for every category."""
    assert _labor_fee("earring", "18k") == 5000
    assert _labor_fee("earring", "18k", 0) == 5000
    assert _labor_fee("earring", "18k", 1200) == 1200
    assert _labor_fee("earring", "s925", 800) == 800
    assert _labor_fee("ring", "18k", 1200) == 1200
    assert _labor_fee("bracelet", "18k", 500) == 500
    assert _labor_fee("pendant", "pt950", 1) == 1


def test_python_chain_wax_and_labor_exact():
    assert _chain_wax_chin("1.5mm", 46) == 0.033
    assert _chain_wax_chin("3.0mm", 80) == 0.12
    assert _labor_fee("chain", "s925") == 500
    assert _labor_fee("chain", "18k") == 3000
    assert _labor_fee("chain", "18k", 0) == 3000


def test_browser_pricing_uses_length_wax_and_chain_labor():
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
pricing.setLiveGoldRates({'18k': 1, s925: 1});
const lengthWeights = {'1.5mm': {'46': 0.033}};
const product = {
  id: 'chain-A',
  weights: {'18k': {'1.5mm': 0.033}, s925: {'1.5mm': 0.033}},
  lengthWeights,
  manualPrices: {},
};
const catalog = {chain: [product]};
const base = {category: 'chain', type: 'chain-A', carat: '1.5mm', lengthCm: 46};
console.log(JSON.stringify([
  pricing.computeOrderPricing({...base, gold: '18k'}, catalog),
  pricing.computeOrderPricing({...base, gold: 's925'}, catalog),
]));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    gold, silver = json.loads(result.stdout)
    assert gold["laborPrice"] == 3000
    assert silver["laborPrice"] == 500
    assert gold["metalworkPrice"] == gold["taijinPrice"] + gold["laborPrice"]
    assert silver["metalworkPrice"] == silver["taijinPrice"] + silver["laborPrice"]
    assert gold["total"] == 3002
    assert silver["total"] == 501


def test_browser_pricing_reads_category_addon():
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
pricing.setLiveGoldRates({'18k': 1, s925: 1});
pricing.setCategoryAddons({ chain: 4500, pendant: 0 });
const lengthWeights = {'1.5mm': {'46': 0.033}};
const product = {
  id: 'chain-A',
  weights: {'18k': {'1.5mm': 0.033}, s925: {'1.5mm': 0.033}},
  lengthWeights,
  manualPrices: {},
};
const catalog = {chain: [product]};
const base = {category: 'chain', type: 'chain-A', carat: '1.5mm', lengthCm: 46};
console.log(JSON.stringify([
  pricing.computeOrderPricing({...base, gold: '18k'}, catalog),
  pricing.computeOrderPricing({...base, gold: 's925'}, catalog),
]));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    gold, silver = json.loads(result.stdout)
    # chain: 4500 replaces base (3000 gold / 500 s925)
    assert gold["laborPrice"] == 4500
    assert silver["laborPrice"] == 4500
    assert gold["metalworkPrice"] == gold["taijinPrice"] + 4500
    assert silver["metalworkPrice"] == silver["taijinPrice"] + 4500
    assert gold["total"] == 4502
    assert silver["total"] == 4501


def test_browser_earring_addon_replaces_base():
    """Shop local pricing: earring 品項加價 replaces default labor."""
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
pricing.setLiveGoldRates({'18k': 1});
pricing.setCategoryAddons({ earring: 1200 });
const product = {
  id: 'earring-A',
  weights: {'18k': {'0.3': 0.01}},
  manualPrices: {},
};
const catalog = {earring: [product]};
const base = {category: 'earring', type: 'earring-A', carat: '0.3', gold: '18k', quantity: 1};
const withAddon = pricing.computeOrderPricing(base, catalog);
pricing.setCategoryAddons({ earring: 0 });
const noAddon = pricing.computeOrderPricing(base, catalog);
console.log(JSON.stringify({ withAddon, noAddon }));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    out = json.loads(result.stdout)
    assert out["noAddon"]["laborPrice"] == 5000
    assert out["withAddon"]["laborPrice"] == 1200
    assert out["withAddon"]["metalworkPrice"] == out["noAddon"]["metalworkPrice"] - 3800
    assert out["withAddon"]["total"] == out["noAddon"]["total"] - 3800


def test_browser_ring_addon_replaces_base():
    """Non-earring categories: 品項加價 replaces LABOR_FEE when > 0."""
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
pricing.setLiveGoldRates({'18k': 1});
pricing.setCategoryAddons({ ring: 1200 });
const product = {
  id: 'ring-A',
  weights: {'18k': {'0.3': 0.01}},
  manualPrices: {},
};
const catalog = {ring: [product]};
const base = {category: 'ring', type: 'ring-A', carat: '0.3', gold: '18k'};
const withAddon = pricing.computeOrderPricing(base, catalog);
pricing.setCategoryAddons({ ring: 0 });
const noAddon = pricing.computeOrderPricing(base, catalog);
console.log(JSON.stringify({ withAddon, noAddon }));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    out = json.loads(result.stdout)
    assert out["noAddon"]["laborPrice"] == 5000
    assert out["withAddon"]["laborPrice"] == 1200
    assert out["withAddon"]["total"] == out["noAddon"]["total"] - 3800


def test_attached_chain_ignores_chain_addon(monkeypatch):
    """Pendant + includeChain: chainPrice = metal×tax only; chain 品項加價 never folds in."""
    from unittest.mock import MagicMock

    from app.pricing import TAX_RATE, _metal_pre_tax, compute_order_pricing

    pendant = {
        "weight_chin": 0.33,
        "manual_price_twd": None,
        "side_stone_price_twd": None,
        "side_stone_carat": None,
        "side_stone_total_twd": None,
        "addon_price_twd": 1200,
    }
    chain = {
        "weight_chin": 0.014,
        "manual_price_twd": None,
        "addon_price_twd": 4500,
    }
    gold_prices = {"XAU": 4300.0, "XPT": 1050.0, "XAG": 61.0}

    def fake_lookup(cur, **kwargs):
        if kwargs["category"] == "pendant":
            return pendant, 0.33
        if kwargs["category"] == "chain":
            return chain, 0.014
        return None

    monkeypatch.setattr("app.pricing._lookup_weight", fake_lookup)
    monkeypatch.setattr("app.pricing.get_metal_prices", lambda cur: gold_prices)
    monkeypatch.setattr("app.pricing.load_overrides", lambda cur: {})
    monkeypatch.setattr("app.pricing.category_addon_price", lambda cur, cat: 9999 if cat == "chain" else 0)
    monkeypatch.setattr("app.pricing.compute_diamond_list_price", lambda *a, **k: 10000)

    quote = compute_order_pricing(
        MagicMock(),
        {
            "category": "pendant",
            "type": "p1",
            "gold": "18k",
            "carat": "0.3",
            "includeChain": True,
            "chainProductId": "c1",
            "chainGold": "18k",
            "chainLength": 36,
            "chainThickness": "1.0mm",
            "diamondKind": "white",
            "diamondShape": "round",
        },
    )
    metal_pre, _ = _metal_pre_tax(gold_prices, "18k", 0.014)
    expected_chain = round(metal_pre * (1 + TAX_RATE))
    assert quote["ready"] is True
    assert quote["laborPrice"] == 1200  # pendant row addon only
    assert quote["chainPrice"] == expected_chain
    # Chain row 4500 + category 9999 must not appear in labor or chain line
    assert quote["chainPrice"] != expected_chain + 4500
    assert quote["total"] == 10000 + quote["taijinPrice"] + 1200 + expected_chain


def test_attached_chain_price_stable_when_chain_addon_changes(monkeypatch):
    """Changing chain 品項加價 must not change pendant+chain quote."""
    from unittest.mock import MagicMock

    from app.pricing import compute_order_pricing

    pendant = {
        "weight_chin": 0.33,
        "manual_price_twd": None,
        "side_stone_price_twd": None,
        "side_stone_carat": None,
        "side_stone_total_twd": None,
        "addon_price_twd": None,
    }
    chain = {
        "weight_chin": 0.014,
        "manual_price_twd": None,
        "addon_price_twd": None,
    }
    gold_prices = {"XAU": 4300.0, "XPT": 1050.0, "XAG": 61.0}
    chain_addon = {"value": 0}

    def fake_lookup(cur, **kwargs):
        if kwargs["category"] == "pendant":
            return pendant, 0.33
        if kwargs["category"] == "chain":
            return {**chain, "addon_price_twd": chain_addon["value"] or None}, 0.014
        return None

    monkeypatch.setattr("app.pricing._lookup_weight", fake_lookup)
    monkeypatch.setattr("app.pricing.get_metal_prices", lambda cur: gold_prices)
    monkeypatch.setattr("app.pricing.load_overrides", lambda cur: {})
    monkeypatch.setattr(
        "app.pricing.category_addon_price",
        lambda cur, cat: chain_addon["value"] if cat == "chain" else 0,
    )
    monkeypatch.setattr("app.pricing.compute_diamond_list_price", lambda *a, **k: 10000)

    payload = {
        "category": "pendant",
        "type": "p1",
        "gold": "18k",
        "carat": "0.3",
        "includeChain": True,
        "chainProductId": "c1",
        "chainGold": "18k",
        "chainLength": 36,
        "chainThickness": "1.0mm",
        "diamondKind": "white",
        "diamondShape": "round",
    }
    cur = MagicMock()
    chain_addon["value"] = 0
    q0 = compute_order_pricing(cur, payload)
    chain_addon["value"] = 4500
    q1 = compute_order_pricing(cur, payload)
    assert q0["ready"] and q1["ready"]
    assert q0["chainPrice"] == q1["chainPrice"]
    assert q0["laborPrice"] == q1["laborPrice"] == 5000
    assert q0["total"] == q1["total"]


def test_browser_attached_chain_ignores_chain_addon():
    """Client parity: includeChain chainPrice ignores chain category/row 品項加價."""
    script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const pricing = window.ShopPricingLocal;
pricing.setLiveGoldRates({'18k': 4300});
const pendant = {
  id: 'p1',
  weights: {'18k': {'0.3': 0.33}},
  manualPrices: {},
  addonPrices: {'18k': {'0.3': 1200}},
};
const chainHi = {
  id: 'c1',
  weights: {'18k': {'1.0mm': 0.014}},
  lengthWeights: {'1.0mm': {'36': 0.014}},
  manualPrices: {},
  addonPrices: {'18k': {'1.0mm': 4500}},
};
const chainLo = {
  id: 'c1',
  weights: {'18k': {'1.0mm': 0.014}},
  lengthWeights: {'1.0mm': {'36': 0.014}},
  manualPrices: {},
  addonPrices: {},
};
const base = {
  category: 'pendant', type: 'p1', gold: '18k', carat: '0.3',
  includeChain: true, chainProductId: 'c1', chainGold: '18k',
  chainLength: 36, chainThickness: '1.0mm',
  diamondKind: 'white', diamondShape: 'round',
};
pricing.setCategoryAddons({ chain: 9999, pendant: 0 });
const withAddon = pricing.computeOrderPricing(base, {pendant: [pendant], chain: [chainHi]});
pricing.setCategoryAddons({ chain: 0, pendant: 0 });
const noAddon = pricing.computeOrderPricing(base, {pendant: [pendant], chain: [chainLo]});
pricing.setCategoryAddons({ chain: 4500 });
const alone = pricing.computeOrderPricing(
  {category: 'chain', type: 'c1', gold: '18k', carat: '1.0mm', lengthCm: 36},
  {chain: [chainHi]}
);
console.log(JSON.stringify({ withAddon, noAddon, alone }));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    out = json.loads(result.stdout)
    assert out["withAddon"]["ready"] is True
    assert out["noAddon"]["ready"] is True
    assert out["withAddon"]["laborPrice"] == 1200
    assert out["noAddon"]["laborPrice"] == 1200
    assert out["withAddon"]["chainPrice"] == out["noAddon"]["chainPrice"]
    assert out["withAddon"]["total"] == out["noAddon"]["total"]
    # Standalone chain still takes row/category 品項加價
    assert out["alone"]["laborPrice"] == 4500
