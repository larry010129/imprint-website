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
    assert _labor_fee("chain", "18k") == 2000
    assert _labor_fee("pendant", "s925") == 5000


def test_node_pricing_uses_same_exact_chain_wax():
    script = (
        "const p=require('./backend/lib/pricing');"
        "console.log(JSON.stringify([p.chainWaxChin('1.5mm',46),p.chainWaxChin('3.0mm',80),"
        "p.laborFee('chain','s925'),p.laborFee('chain','18k')]));"
    )
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == [0.033, 0.12, 500, 2000]


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
    assert gold["laborPrice"] == 2000
    assert silver["laborPrice"] == 500
    assert gold["total"] == 2002
    assert silver["total"] == 501
