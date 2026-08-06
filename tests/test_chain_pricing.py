import json
import subprocess
from pathlib import Path

from app.pricing import CHAIN_WAX_WEIGHT_CHIN, _chain_wax_chin, _labor_fee


ROOT = Path(__file__).resolve().parents[1]


def test_chain_wax_table_has_all_excel_combinations():
    assert set(CHAIN_WAX_WEIGHT_CHIN) == {"1.0mm", "1.5mm", "2.0mm", "2.5mm", "3.0mm"}
    assert all(set(weights) == {36, 41, 46, 51, 61, 76, 80} for weights in CHAIN_WAX_WEIGHT_CHIN.values())
    assert _chain_wax_chin("1.5mm", 46) == 0.033
    assert _chain_wax_chin("3.0mm", 80) == 0.120


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
