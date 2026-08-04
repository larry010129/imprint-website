"""Memorial diamond list pricing: unit × qty × multi discount (not package tables)."""

import json
import subprocess
from pathlib import Path

from app.pricing import (
    COLORED_SINGLE_DIAMOND_PRICE,
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


def test_earring_list_price_is_single_unit():
    """Earrings price one stone; pair qty is applied in compute_order_pricing."""
    unit = DIAMOND_PRICE["0.3"]
    assert compute_diamond_list_price("0.3", category="earring") == unit
    assert compute_diamond_list_price(
        "0.3", category="earring", stone_count=2,
    ) == unit


def test_fancy_below_table_falls_back_to_white_list_price():
    """Admin may list 0.1/0.2 on a product; fancy table starts at 0.3."""
    assert "0.1" not in COLORED_SINGLE_DIAMOND_PRICE
    assert "0.2" not in COLORED_SINGLE_DIAMOND_PRICE
    for carat in ("0.1", "0.2"):
        assert compute_diamond_list_price(
            carat,
            category="pendant",
            diamond_kind="fancy",
            fancy_color="yellow",
        ) == DIAMOND_PRICE[carat]
    assert compute_diamond_list_price(
        "0.3",
        category="pendant",
        diamond_kind="fancy",
        fancy_color="yellow",
    ) == COLORED_SINGLE_DIAMOND_PRICE["0.3"]


def test_shop_carat_options_fancy_filters_below_min_white_keeps_01():
    """Fancy dropdown: admin ∩ ≥0.3. White: full admin list including 0.1/0.2."""
    browser_script = r"""
const state = { category: 'pendant', diamondKind: 'white' };
const diamondOptions = { fancyMinCarat: 0.3 };
function fancyMinCaratValue() {
  const n = Number(diamondOptions.fancyMinCarat || 0.3);
  return Number.isNaN(n) ? 0.3 : n;
}
function caratsForProductGold(product, gold) {
  const byGold = gold ? product.weights?.[gold] : null;
  if (byGold && Object.keys(byGold).length) {
    return Object.keys(byGold).sort((a, b) => parseFloat(a) - parseFloat(b));
  }
  return [...(product.carats || [])];
}
function listAdminProductCaratOptions(product, gold) {
  if (!product) return [];
  const fromGold = gold ? caratsForProductGold(product, gold) : null;
  const raw = (fromGold && fromGold.length) ? fromGold : [...(product.carats || [])];
  return raw.map(String).filter(Boolean);
}
function listProductCaratOptions(product, gold) {
  const options = listAdminProductCaratOptions(product, gold);
  if (state.category === 'chain' || state.diamondKind !== 'fancy') return options;
  const minCarat = fancyMinCaratValue();
  return options.filter((c) => {
    const n = parseFloat(c);
    return !Number.isNaN(n) && n >= minCarat;
  });
}
const product = {
  carats: ['0.1', '0.2', '0.3'],
  weights: { '14k': { '0.1': 1, '0.2': 1, '0.3': 1 } },
};
state.diamondKind = 'white';
const whiteOpts = listProductCaratOptions(product, '14k');
state.diamondKind = 'fancy';
const fancyOpts = listProductCaratOptions(product, '14k');
const bumped = (!fancyOpts.includes('0.1') && fancyOpts[0] === '0.3');
console.log(JSON.stringify({ whiteOpts, fancyOpts, bumped, firstFancy: fancyOpts[0] }));
"""
    out = json.loads(
        subprocess.run(
            ["node", "-e", browser_script],
            cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout
    )
    assert out["whiteOpts"] == ["0.1", "0.2", "0.3"]
    assert out["fancyOpts"] == ["0.3"]
    assert out["bumped"] is True
    assert out["firstFancy"] == "0.3"


def test_fancy_invalid_color_still_rejected():
    assert compute_diamond_list_price(
        "0.3",
        category="pendant",
        diamond_kind="fancy",
        fancy_color="green",
    ) is None


def test_browser_match_python_memorial_multi():
    """Thin client must match app/pricing.py (authoritative)."""
    expected = {
        "py1": compute_diamond_list_price("0.3", category="diamond"),
        "py2": compute_diamond_list_price("0.3", category="diamond", stone_count=2),
        "py07": compute_diamond_list_price("0.7", category="diamond", stone_count=2),
        "pyFancy01": compute_diamond_list_price(
            "0.1", category="diamond", diamond_kind="fancy", fancy_color="yellow",
        ),
        "pyFancy03": compute_diamond_list_price(
            "0.3", category="diamond", diamond_kind="fancy", fancy_color="yellow",
        ),
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
  bFancy01: p.computeOrderPricing({
    ...base, carat: '0.1', diamondKind: 'fancy', fancyColor: 'yellow',
  }, catalog).total,
  bFancy03: p.computeOrderPricing({
    ...base, carat: '0.3', diamondKind: 'fancy', fancyColor: 'yellow',
  }, catalog).total,
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
    assert browser["bFancy01"] == expected["pyFancy01"]
    assert browser["bFancy03"] == expected["pyFancy03"]
