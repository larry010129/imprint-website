"""Memorial diamond list pricing: unit × qty × multi discount (not package tables)."""

import json
import subprocess
from pathlib import Path

from app.pricing import (
    DIAMOND_PRICE,
    MULTI_STONE_ABOVE_03_MULTIPLIER,
    compute_diamond_list_price,
)


ROOT = Path(__file__).resolve().parents[1]


def test_memorial_white_single_and_multi_use_unit_times_qty_discount():
    unit = DIAMOND_PRICE["0.3"]
    assert compute_diamond_list_price("0.3", category="diamond") == unit
    assert compute_diamond_list_price("0.3", category="diamond", stone_count=1) == unit

    for qty, discount in MULTI_STONE_ABOVE_03_MULTIPLIER.items():
        expected = round(unit * qty * discount)
        assert compute_diamond_list_price(
            "0.3", category="diamond", stone_count=qty,
        ) == expected
        # Multi must stay above single unit (package tables used to undercut).
        assert expected > unit


def test_memorial_multi_above_03_uses_that_carats_unit_not_03_package():
    unit = DIAMOND_PRICE["0.7"]
    qty2 = compute_diamond_list_price("0.7", category="diamond", stone_count=2)
    assert qty2 == round(unit * 2 * 0.85)
    assert qty2 > unit


def test_non_round_surcharge_applies_to_unit_before_multi():
    unit = round(DIAMOND_PRICE["0.3"] * 1.10)
    assert compute_diamond_list_price(
        "0.3", category="diamond", diamond_shape="oval",
    ) == unit
    assert compute_diamond_list_price(
        "0.3", category="diamond", diamond_shape="oval", stone_count=2,
    ) == round(unit * 2 * 0.85)


def test_earring_pair_still_two_singles_no_multi_discount():
    unit = DIAMOND_PRICE["0.3"]
    assert compute_diamond_list_price("0.3", category="earring") == unit * 2
    assert compute_diamond_list_price(
        "0.3", category="earring", stone_count=2,
    ) == unit * 2


def test_browser_match_python_memorial_multi():
    """Thin client must match app/pricing.py (authoritative)."""
    expected = {
        "py1": compute_diamond_list_price("0.3", category="diamond"),
        "py2": compute_diamond_list_price("0.3", category="diamond", stone_count=2),
        "py07": compute_diamond_list_price("0.7", category="diamond", stone_count=2),
    }
    browser_script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const catalog = {diamond: [{id: 'd1', weights: {}, manualPrices: {}}]};
const base = {category: 'diamond', type: 'd1', carat: '0.3', diamondKind: 'white'};
const p = window.ShopPricingLocal;
console.log(JSON.stringify({
  b1: p.computeOrderPricing(base, catalog).total,
  b2: p.computeOrderPricing({...base, stoneCount: 2}, catalog).total,
  b07: p.computeOrderPricing({...base, carat: '0.7', stoneCount: 2}, catalog).total,
}));
"""
    browser = json.loads(
        subprocess.run(
            ["node", "-e", browser_script],
            cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout
    )
    assert browser["b1"] == expected["py1"]
    assert browser["b2"] == expected["py2"]
    assert browser["b07"] == expected["py07"]
