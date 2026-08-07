"""Memorial diamond list pricing: price packages + above-0.3 unit×qty×discount."""

import json
import subprocess
from pathlib import Path

from app.pricing import (
    COLORED_MULTI_DIAMOND_PRICE,
    COLORED_SINGLE_DIAMOND_PRICE,
    DIAMOND_PRICE,
    WHITE_MULTI_DIAMOND_PRICE,
    compute_diamond_list_price,
)


ROOT = Path(__file__).resolve().parents[1]


def test_memorial_white_single_and_multi_use_price_html_packages():
    unit = DIAMOND_PRICE["0.3"]
    assert compute_diamond_list_price("0.3", category="diamond") == unit
    assert compute_diamond_list_price("0.3", category="diamond", stone_count=1) == unit

    for qty, expected in WHITE_MULTI_DIAMOND_PRICE["0.3"].items():
        assert compute_diamond_list_price(
            "0.3", category="diamond", stone_count=qty,
        ) == expected
        assert expected > unit


def test_memorial_multi_above_03_uses_that_carats_unit_not_03_package():
    unit = DIAMOND_PRICE["0.7"]
    qty2 = compute_diamond_list_price("0.7", category="diamond", stone_count=2)
    assert qty2 == round(unit * 2 * 0.85)
    assert qty2 > unit
    # Must not reuse the 0.3 package row for larger carats.
    assert qty2 != WHITE_MULTI_DIAMOND_PRICE["0.3"][2]


def test_non_round_surcharge_applies_to_package_total():
    unit = round(DIAMOND_PRICE["0.3"] * 1.10)
    assert compute_diamond_list_price(
        "0.3", category="diamond", diamond_shape="oval",
    ) == unit
    assert compute_diamond_list_price(
        "0.3", category="diamond", diamond_shape="oval", stone_count=2,
    ) == round(WHITE_MULTI_DIAMOND_PRICE["0.3"][2] * 1.10)


def test_earring_list_price_is_single_unit():
    """Earrings price one stone; pair qty is applied in compute_order_pricing."""
    unit = DIAMOND_PRICE["0.3"]
    assert compute_diamond_list_price("0.3", category="earring") == unit
    assert compute_diamond_list_price(
        "0.3", category="earring", stone_count=2,
    ) == unit


def test_fancy_below_table_falls_back_on_jewelry_not_memorial():
    """Jewelry admin may list 0.1/0.2; memorial fancy below 0.3 is unavailable."""
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
            carat,
            category="diamond",
            diamond_kind="fancy",
            fancy_color="yellow",
        ) is None
    assert compute_diamond_list_price(
        "0.3",
        category="pendant",
        diamond_kind="fancy",
        fancy_color="yellow",
    ) == COLORED_SINGLE_DIAMOND_PRICE["0.3"]
    assert compute_diamond_list_price(
        "0.3",
        category="diamond",
        diamond_kind="fancy",
        fancy_color="yellow",
        stone_count=4,
    ) == COLORED_MULTI_DIAMOND_PRICE["0.3"][4]


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
        "pyFancy03x2": compute_diamond_list_price(
            "0.3", category="diamond", diamond_kind="fancy", fancy_color="yellow",
            stone_count=2,
        ),
    }
    browser_script = """
global.window = {};
require('./public/js/shop-pricing-local.js');
const catalog = {diamond: [{id: 'd1', weights: {}, manualPrices: {}}]};
const base = {category: 'diamond', type: 'd1', carat: '0.3', diamondKind: 'white'};
const p = window.ShopPricingLocal;
const tot = (cfg) => {
  const q = p.computeOrderPricing(cfg, catalog);
  return q.ready ? q.total : null;
};
console.log(JSON.stringify({
  b1: tot(base),
  b2: tot({...base, stoneCount: 2}),
  b07: tot({...base, carat: '0.7', stoneCount: 2}),
  bFancy01: tot({
    ...base, carat: '0.1', diamondKind: 'fancy', fancyColor: 'yellow',
  }),
  bFancy03: tot({
    ...base, carat: '0.3', diamondKind: 'fancy', fancyColor: 'yellow',
  }),
  bFancy03x2: tot({
    ...base, carat: '0.3', diamondKind: 'fancy', fancyColor: 'yellow', stoneCount: 2,
  }),
}));
"""
    browser = json.loads(
        subprocess.run(
            ["node", "-e", browser_script],
            cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout
    )
    assert browser["b1"] == expected["py1"] == 79000
    assert browser["b2"] == expected["py2"] == 142200
    assert browser["b07"] == expected["py07"]
    assert browser["bFancy01"] == expected["pyFancy01"] is None
    assert browser["bFancy03"] == expected["pyFancy03"] == 102000
    assert browser["bFancy03x2"] == expected["pyFancy03x2"] == 173400
