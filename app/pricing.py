"""Server-side authoritative order pricing (source of truth).

Client-submitted prices (`clientPricing`) must never be trusted when writing to
cart_items/orders; this module recomputes the price from the DB catalog + live
gold rate. See shop_controller.add_to_cart, which is the sole write path.

Parity fixture for formula tests: public/js/shop-pricing-local.js (calculator uses server /htmx/shop/quote).
"""

from __future__ import annotations

from typing import Any

from app.admin_products import RING_SIZE_MIN
from app.catalog import resolve_product_id
from app.chain_catalog import DEFAULT_NECKLACE_TYPE, necklace_type_length_weights
from app.pricing_overrides import (
    _merge_multi,
    _merge_table,
    canonical_carat,
    load_overrides,
)
from app.product_categories import category_addon_price, category_ring_size_config

DIAMOND_PRICE = {
    "0.1": 24000, "0.2": 48000, "0.3": 79000, "0.5": 98000,
    "0.6": 113000, "0.7": 133000, "0.8": 159000, "0.9": 200000,
    "1.0": 250000, "1": 250000, "1.5": 380000, "2.0": 700000, "2": 700000,
    "3.0": 990000, "3": 990000,
}

COLORED_SINGLE_DIAMOND_PRICE = {
    "0.3": 102000, "0.5": 127000, "0.6": 147000, "0.7": 172000,
    "0.8": 206000, "0.9": 260000, "1.0": 325000, "1": 325000,
    "1.5": 494000, "2.0": 910000, "2": 910000, "3.0": 1287000, "3": 1287000,
}

WHITE_MULTI_DIAMOND_PRICE = {
    "0.1": {2: 45600, 3: 61200, 4: 81000},
    "0.2": {2: 86400, 3: 122400, 4: 162000},
    "0.3": {2: 142200, 3: 189600, 4: 250000},
}

COLORED_MULTI_DIAMOND_PRICE = {
    "0.3": {2: 173400, 3: 244800, 4: 322300},
}

MULTI_STONE_ABOVE_03_MULTIPLIER = {2: 0.85, 3: 0.80, 4: 0.75}

VALID_FANCY_COLORS = {"yellow", "pink", "blue"}
VALID_STONE_COUNTS = {2, 3, 4}
FANCY_MIN_CARAT = 0.3
NON_ROUND_SHAPE_SURCHARGE = 0.10
# Earring stoneCount no longer auto-doubles; use quantity (1–2) instead.
DEFAULT_STONE_COUNT_BY_CATEGORY = {"ring": 2, "pendant": 2}
STONE_COUNT_CATEGORIES: set[str] = set()
EARRING_QUANTITY_MIN = 1
EARRING_QUANTITY_MAX = 2
# Non-earring cart/order line units (made-to-order; no stock cap).
CART_LINE_QUANTITY_MAX = 99

# 蠟重(錢) × factor → 成品金屬重(錢)
WAX_TO_METAL_CHIN = {
    "9k": 11.5, "14k": 14.0, "18k": 16.0, "s925": 11.0, "pt950": 24.0,
    "999": 11.5, "pt": 24.0, "silver925": 11.0,
}
WAX_REFERENCE_GOLD = "9k"

PURITY_MULTIPLIER = {
    "9k": 0.50, "14k": 0.75, "18k": 0.85, "pt950": 1.10, "s925": 0.925,
    "999": 0.999, "pt": 1.0, "silver925": 0.925,
}
METAL_SYMBOL = {
    "9k": "XAU", "14k": "XAU", "18k": "XAU", "pt950": "XPT", "s925": "XAG",
    "999": "XAU", "pt": "XPT", "silver925": "XAG",
}
# Default flat labor; standalone chains use metal-specific labor below.
LABOR_FEE_TWD = 5000
CHAIN_LABOR_FEE_TWD = {"s925": 500, "other": 3000}
DEFAULT_ATTACHED_CHAIN_THICKNESS = "1.0mm"
CHAIN_WAX_WEIGHT_CHIN = {
    "1.0mm": {36: 0.014, 41: 0.016, 46: 0.018, 51: 0.020, 61: 0.024, 76: 0.030, 80: 0.032},
    "1.5mm": {36: 0.026, 41: 0.030, 46: 0.033, 51: 0.037, 61: 0.043, 76: 0.054, 80: 0.057},
    "2.0mm": {36: 0.040, 41: 0.046, 46: 0.051, 51: 0.056, 61: 0.066, 76: 0.083, 80: 0.087},
    "2.5mm": {36: 0.047, 41: 0.053, 46: 0.059, 51: 0.065, 61: 0.076, 76: 0.095, 80: 0.100},
    "3.0mm": {36: 0.052, 41: 0.060, 46: 0.066, 51: 0.074, 61: 0.086, 76: 0.110, 80: 0.120},
}

TAX_RATE = 0.05
CHIN_TO_GRAMS = 3.75
BRACELET_REFERENCE_LENGTH_CM = 18


def normalize_gold(gold: Any) -> str:
    """Canonical metal key for DB lookups and pricing tables (9K → 9k, PT → pt950)."""
    g = str(gold or "").strip().lower()
    if g in ("pt", "pt950"):
        return "pt950"
    if g in ("silver925", "s925"):
        return "s925"
    if g in ("999",):
        return "999"
    return g


def _as_stone_count(value: Any) -> int | None:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    return count if count in VALID_STONE_COUNTS else None


def _as_earring_quantity(value: Any) -> int:
    """Single-earring units; default 1, max 2 (pair)."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return EARRING_QUANTITY_MIN
    return max(EARRING_QUANTITY_MIN, min(EARRING_QUANTITY_MAX, n))


def _as_line_quantity(value: Any, *, category: str | None = None) -> int:
    """Cart/order line units. Earrings capped at pair; others up to CART_LINE_QUANTITY_MAX."""
    if category == "earring":
        return _as_earring_quantity(value)
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(CART_LINE_QUANTITY_MAX, n))


def cart_line_quantity_max(category: str | None = None) -> int:
    if category == "earring":
        return EARRING_QUANTITY_MAX
    return CART_LINE_QUANTITY_MAX


def _shape_carat_allowed(carat_num: float, diamond_shape: str | None) -> bool:
    return (diamond_shape or "round") == "round" or carat_num >= FANCY_MIN_CARAT


def _effective_tables(overrides: dict[str, Any] | None) -> dict[str, Any]:
    """Overlay admin overrides onto the base diamond tables, canonicalizing carat
    keys so client ('0.10') and server ('0.1') formats align. With no overrides
    this yields the module constants unchanged (checkout math is untouched until
    an admin sets a value).

    Memorial multi: package tables for 0.1/0.2/0.3 (price);
    above 0.3ct uses unit × qty × multi_above_03.
    """
    ov = overrides or {}
    dia = ov.get("diamond") if isinstance(ov.get("diamond"), dict) else {}
    multi_above = {str(k): v for k, v in MULTI_STONE_ABOVE_03_MULTIPLIER.items()}
    ov_above = ov.get("multiStoneAbove03Multiplier")
    if isinstance(ov_above, dict):
        for k, v in ov_above.items():
            if isinstance(v, (int, float)):
                multi_above[str(k)] = v
    return {
        "white": _merge_table(DIAMOND_PRICE, dia.get("white")),
        "fancy": _merge_table(COLORED_SINGLE_DIAMOND_PRICE, dia.get("fancy")),
        "white_multi": _merge_multi(WHITE_MULTI_DIAMOND_PRICE, ov.get("whiteMultiDiamondPrice")),
        "fancy_multi": _merge_multi(COLORED_MULTI_DIAMOND_PRICE, ov.get("coloredMultiDiamondPrice")),
        "multi_above_03": multi_above,
        "surcharge_pct": ov.get("shapeSurchargePct"),
    }


def _shape_surcharge_fraction(
    diamond_shape: str | None, surcharge_pct: Any
) -> float:
    if (diamond_shape or "round") == "round":
        return 0.0
    if isinstance(surcharge_pct, (int, float)):
        return float(surcharge_pct) / 100.0
    return NON_ROUND_SHAPE_SURCHARGE


def _apply_shape_surcharge(amount: float, surcharge: float) -> float:
    return round(amount * (1 + surcharge)) if surcharge else amount


def compute_diamond_compare_at_price(
    carat_key: str | None,
    *,
    diamond_kind: str = "white",
    fancy_color: str | None = None,
    stone_count: Any = None,
    diamond_shape: str = "round",
    category: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> float | None:
    """Pre-discount total (unit × stoneCount) when multi-stone package beats list×qty.

    Memorial diamonds only (`category == \"diamond\"`). Returns None when no discount.
    """
    multi_count = _as_stone_count(stone_count) if category == "diamond" else None
    if not multi_count:
        return None
    unit = compute_diamond_list_price(
        carat_key,
        diamond_kind=diamond_kind,
        fancy_color=fancy_color,
        stone_count=None,
        diamond_shape=diamond_shape,
        category=category,
        overrides=overrides,
    )
    discounted = compute_diamond_list_price(
        carat_key,
        diamond_kind=diamond_kind,
        fancy_color=fancy_color,
        stone_count=stone_count,
        diamond_shape=diamond_shape,
        category=category,
        overrides=overrides,
    )
    if unit is None or discounted is None:
        return None
    compare_at = round(float(unit) * multi_count)
    if compare_at > round(float(discounted)):
        return float(compare_at)
    return None


def memorial_diamond_line_totals(
    carat_key: str | None,
    *,
    diamond_kind: str = "white",
    fancy_color: str | None = None,
    stone_count: Any = None,
    diamond_shape: str = "round",
    line_qty: int = 1,
    overrides: dict[str, Any] | None = None,
) -> tuple[float | None, float | None]:
    """Memorial diamond line sale + optional compare-at (unit×stones).

    - Configured multi stoneCount (2/3/4): package price × line_qty.
    - Single-stone lines: pack line_qty into 4→3→2 packages (same tables),
      remainder at unit list — so cart qty 2/3/4 unlocks the same discount as
      the stone-count picker.
    """
    qty = max(1, int(line_qty or 1))
    common = dict(
        diamond_kind=diamond_kind,
        fancy_color=fancy_color,
        diamond_shape=diamond_shape,
        category="diamond",
        overrides=overrides,
    )
    multi = _as_stone_count(stone_count)
    if multi:
        sale_unit = compute_diamond_list_price(
            carat_key, stone_count=multi, **common
        )
        if sale_unit is None:
            return None, None
        compare_unit = compute_diamond_compare_at_price(
            carat_key, stone_count=multi, **common
        )
        sale = round(float(sale_unit)) * qty
        if compare_unit is None:
            return float(sale), None
        return float(sale), float(round(float(compare_unit)) * qty)

    unit = compute_diamond_list_price(carat_key, stone_count=None, **common)
    if unit is None:
        return None, None
    unit_i = round(float(unit))
    remaining = qty
    sale = 0
    compare = 0
    for pack in (4, 3, 2):
        packs = remaining // pack
        if not packs:
            continue
        pack_price = compute_diamond_list_price(
            carat_key, stone_count=pack, **common
        )
        if pack_price is None:
            sale += unit_i * pack * packs
        else:
            sale += round(float(pack_price)) * packs
        compare += unit_i * pack * packs
        remaining -= pack * packs
    if remaining:
        sale += unit_i * remaining
        compare += unit_i * remaining
    if compare > sale:
        return float(sale), float(compare)
    return float(sale), None


def compute_diamond_list_price(
    carat_key: str | None,
    *,
    diamond_kind: str = "white",
    fancy_color: str | None = None,
    stone_count: Any = None,
    diamond_shape: str = "round",
    category: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> float | None:
    if not carat_key or category == "chain":
        return None
    try:
        carat_num = float(carat_key)
    except (TypeError, ValueError):
        return None

    # Earrings: single-stone list price; pair/qty applied in compute_order_pricing.
    multi_count = _as_stone_count(stone_count) if category == "diamond" else None
    if not _shape_carat_allowed(carat_num, diamond_shape):
        return None

    eff = _effective_tables(overrides)
    ck = canonical_carat(carat_key) or carat_key

    base = None
    if diamond_kind == "white":
        base = eff["white"].get(ck)
    elif diamond_kind == "fancy":
        if fancy_color not in VALID_FANCY_COLORS:
            return None
        # Fancy list starts at 0.3ct; admin jewelry may still offer 0.1/0.2 —
        # fall back to white so shop quote does not blank out.
        base = eff["fancy"].get(ck)
        if base is None and category != "diamond":
            base = eff["white"].get(ck)
    else:
        return None

    surcharge = _shape_surcharge_fraction(diamond_shape, eff["surcharge_pct"])

    if multi_count:
        multi_table = eff["fancy_multi"] if diamond_kind == "fancy" else eff["white_multi"]
        package = (multi_table.get(ck) or {}).get(str(multi_count))
        if package is not None:
            return _apply_shape_surcharge(float(package), surcharge)
        # price: above 0.30ct → 單顆價 × 顆數 × discount
        if carat_num > FANCY_MIN_CARAT and base is not None:
            discount = eff["multi_above_03"].get(str(multi_count))
            if not discount:
                return None
            return _apply_shape_surcharge(
                round(float(base) * multi_count * discount), surcharge
            )
        return None

    if base is None:
        return None
    return _apply_shape_surcharge(float(base), surcharge)


def get_metal_prices(cur) -> dict[str, float]:
    cur.execute("select xau_per_gram, xpt_per_gram, xag_per_gram from gold_price_cache where id = 1")
    row = cur.fetchone()
    if not row:
        return {"XAU": 4300.0, "XPT": 1050.0, "XAG": 61.0}
    return {
        "XAU": float(row["xau_per_gram"]),
        "XPT": float(row["xpt_per_gram"]),
        "XAG": float(row["xag_per_gram"]),
    }


def _carat_lookup_keys(carat: str) -> list[str]:
    keys: list[str] = []
    for key in (carat, str(carat).strip()):
        if key and key not in keys:
            keys.append(key)
    try:
        n = float(carat)
        for alt in (f"{n:.1f}", f"{int(n)}.0", str(int(n)) if n == int(n) else None):
            if alt and alt not in keys:
                keys.append(alt)
    except (TypeError, ValueError):
        pass
    return keys


def wax_to_metal_chin(wax_chin: float, gold: str) -> float:
    factor = WAX_TO_METAL_CHIN.get(normalize_gold(gold))
    if factor is None:
        raise ValueError(f"unknown gold: {gold}")
    return wax_chin * factor


def _chain_wax_chin(carat: str, length_cm: Any) -> float:
    try:
        length = int(length_cm)
    except (TypeError, ValueError):
        raise ValueError("invalid chain length") from None
    wax = CHAIN_WAX_WEIGHT_CHIN.get(carat, {}).get(length)
    if wax is None:
        raise ValueError("unsupported chain thickness or length")
    return wax


def _chain_wax_from_length_weights(
    length_weights: dict | None, carat: str, length_cm: Any
) -> float | None:
    if not length_weights or not isinstance(length_weights, dict):
        return None
    table = length_weights.get(carat)
    if not isinstance(table, dict):
        return None
    try:
        length_key = str(int(length_cm))
    except (TypeError, ValueError):
        return None
    wax = table.get(length_key)
    if wax is None:
        return None
    try:
        value = float(wax)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _product_chain_type(cur, product_id: str) -> str | None:
    cur.execute("select chain_type from products where id = %s", (product_id,))
    row = cur.fetchone()
    if not row:
        return None
    ct = row.get("chain_type")
    return str(ct).strip() if ct else None


def _product_length_weights(cur, product_id: str) -> dict | None:
    cur.execute("select length_weights from products where id = %s", (product_id,))
    row = cur.fetchone()
    if not row:
        return None
    lw = row.get("length_weights")
    return lw if isinstance(lw, dict) and lw else None


def _chain_wax_from_type_catalog(
    chain_type: str | None, carat: str, length_cm: Any
) -> float | None:
    table = necklace_type_length_weights(chain_type)
    return _chain_wax_from_length_weights(table, carat, length_cm)


def _resolve_chain_wax(
    cur,
    *,
    product_id: str,
    carat: str,
    length_cm: Any,
) -> float:
    resolved = resolve_product_id(cur, category="chain", type_ref=product_id, require_published=False)
    pid = resolved or product_id
    lw = _product_length_weights(cur, pid)
    admin_wax = _chain_wax_from_length_weights(lw, carat, length_cm)
    if admin_wax is not None:
        return admin_wax
    chain_type = _product_chain_type(cur, pid) or DEFAULT_NECKLACE_TYPE
    type_wax = _chain_wax_from_type_catalog(chain_type, carat, length_cm)
    if type_wax is not None:
        return type_wax
    raise ValueError("unsupported chain thickness or length")


def _labor_fee(category: str, gold: str, addon_price_twd: int | None = None) -> int:
    """Labor fee = 品項加價 when set, else built-in base (folded into 金工價格).

    Base (when addon is 0 / unset): chain s925=500, chain other=3000,
    else LABOR_FEE 5000. Addon > 0 fully replaces that base (no double).
    Earring 耳扣 is added separately in compute_order_pricing.
    """
    if category == "chain" and gold == "s925":
        base = CHAIN_LABOR_FEE_TWD["s925"]
    elif category == "chain":
        base = CHAIN_LABOR_FEE_TWD["other"]
    else:
        base = LABOR_FEE_TWD
    try:
        addon = int(addon_price_twd) if addon_price_twd is not None else 0
    except (TypeError, ValueError):
        addon = 0
    if addon < 0:
        addon = 0
    return addon if addon > 0 else base


def _variant_addon_price(variant: dict | None) -> int | None:
    """Per-row 品項加價 when set; None means fall back to category addon."""
    if not variant:
        return None
    raw = variant.get("addon_price_twd")
    if raw is None:
        raw = variant.get("addonPriceTwd")
    if raw is None or raw == "":
        return None
    try:
        amount = int(round(float(raw)))
    except (TypeError, ValueError):
        return None
    return max(0, amount)


def _effective_addon_price(cur, category: str, variant: dict | None) -> int:
    """Row addon when > 0; else category 品項加價.

    Explicit 0 is treated as unset so prefilled/force-written zeros do not
    block a later category 品項加價 (labor still uses base when both are 0).
    """
    row_addon = _variant_addon_price(variant)
    if row_addon:
        return row_addon
    return category_addon_price(cur, category)


def _ear_clasp_fee(variant: dict | None) -> int:
    """Per-variant 耳扣價錢 (earring only); folded into labor / 金工價格."""
    if not variant:
        return 0
    raw = variant.get("ear_clasp_price_twd")
    if raw is None:
        raw = variant.get("ear_cuff_price_twd")
    if raw is None:
        return 0
    try:
        amount = int(round(float(raw)))
    except (TypeError, ValueError):
        return 0
    return max(0, amount)


def _normalize_ring_size(ring_size: Any) -> int | None:
    if ring_size in (None, ""):
        return None
    try:
        size = int(round(float(ring_size)))
    except (TypeError, ValueError):
        return None
    if size < RING_SIZE_MIN:
        return None
    return size


def _ring_charge_after_from_config(config: dict) -> int | None:
    """Threshold size: N <= chargeAfter → +0. Defaults to minSize when omitted."""
    charge_raw = config.get("chargeAfter")
    if charge_raw is None:
        charge_raw = config.get("charge_after")
    if charge_raw is None:
        charge_raw = config.get("priceFromSize")
    if charge_raw is None:
        charge_raw = config.get("price_from_size")
    if charge_raw is None:
        charge_raw = config.get("baseSize")
    if charge_raw is None:
        charge_raw = config.get("base_size")
    if charge_raw in (None, ""):
        min_raw = config.get("minSize")
        if min_raw is None:
            min_raw = config.get("min_size")
        if min_raw is None:
            min_raw = config.get("startSize")
        if min_raw is None:
            min_raw = config.get("start_size")
        charge_raw = min_raw
    return _normalize_ring_size(charge_raw)


def ring_size_addon_from_config(config: dict | None, ring_size: Any) -> int:
    """戒圍加價: step formula, else legacy sizes[] lookup. Does not replace labor addon."""
    size = _normalize_ring_size(ring_size)
    if size is None or not isinstance(config, dict):
        return 0

    step_raw = config.get("pricePerSizeTwd")
    if step_raw is None:
        step_raw = config.get("price_per_size_twd")
    if step_raw not in (None, ""):
        charge_after = _ring_charge_after_from_config(config)
        if charge_after is None:
            return 0
        try:
            step = float(step_raw)
        except (TypeError, ValueError):
            return 0
        if step < 0:
            return 0
        if size <= charge_after:
            return 0
        return max(0, int(round((size - charge_after) * step)))

    for row in config.get("sizes") or []:
        if not isinstance(row, dict):
            continue
        row_size = _normalize_ring_size(row.get("size"))
        if row_size != size:
            continue
        raw = row.get("addonPriceTwd")
        if raw is None:
            raw = row.get("addon_price_twd")
        if raw in (None, ""):
            return 0
        try:
            return max(0, int(round(float(raw))))
        except (TypeError, ValueError):
            return 0
    addons = config.get("addons")
    if isinstance(addons, dict):
        raw = addons.get(str(size))
        if raw is None:
            raw = addons.get(size)
        if raw in (None, ""):
            return 0
        try:
            return max(0, int(round(float(raw))))
        except (TypeError, ValueError):
            return 0
    return 0


def _product_ring_size_config(cur, *, category: str, product_id: str, require_published: bool) -> dict | None:
    """Effective ring config: category first, then product legacy ring_size_config."""
    if category == "ring":
        cat_cfg = category_ring_size_config(cur, category)
        if isinstance(cat_cfg, dict):
            return cat_cfg
    resolved = resolve_product_id(
        cur, category=category, type_ref=product_id, require_published=require_published,
    )
    if not resolved:
        return None
    cur.execute(
        "select ring_size_config from products where id = %s and category = %s",
        (resolved, category),
    )
    row = cur.fetchone()
    if not row:
        return None
    cfg = row.get("ring_size_config")
    return cfg if isinstance(cfg, dict) else None


def _gold_lookup_keys(gold: str) -> list[str]:
    """Canonical gold first, then legacy aliases stored in older variant rows."""
    canonical = normalize_gold(gold)
    keys = [canonical]
    if canonical == "s925":
        for alias in ("silver925", "S925"):
            if alias not in keys:
                keys.append(alias)
    elif canonical == "pt950":
        for alias in ("pt", "PT950"):
            if alias not in keys:
                keys.append(alias)
    return keys


def get_product_variant(
    cur, *, category: str, product_id: str, gold: str, carat: str, require_published: bool = True
) -> dict | None:
    resolved = resolve_product_id(
        cur, category=category, type_ref=product_id, require_published=require_published,
    )
    if not resolved:
        return None
    for gold_key in _gold_lookup_keys(gold):
        for carat_key in _carat_lookup_keys(carat):
            if require_published:
                cur.execute(
                    """
                    select pv.* from product_variants pv
                    join products p on p.id = pv.product_id
                    where p.id = %s and p.category = %s
                      and pv.gold = %s and pv.carat = %s and p.is_published = true
                    """,
                    (resolved, category, gold_key, carat_key),
                )
            else:
                cur.execute(
                    """
                    select pv.* from product_variants pv
                    join products p on p.id = pv.product_id
                    where p.id = %s and p.category = %s
                      and pv.gold = %s and pv.carat = %s
                    """,
                    (resolved, category, gold_key, carat_key),
                )
            row = cur.fetchone()
            if row:
                return row
    gold = normalize_gold(gold)
    if category == "chain":
        for gold_key in _gold_lookup_keys(gold):
            sql = """
                select pv.* from product_variants pv
                join products p on p.id = pv.product_id
                where p.id = %s and p.category = 'chain' and pv.gold = %s
            """
            params: list[Any] = [resolved, gold_key]
            if require_published:
                sql += " and p.is_published = true"
            sql += " order by pv.carat limit 1"
            cur.execute(sql, params)
            row = cur.fetchone()
            if row:
                return row
    return None


def _lookup_weight(
    cur, *, category: str, product_id: str, gold: str, carat: str,
    length_cm: Any, require_published: bool,
) -> tuple[dict, float] | None:
    gold = normalize_gold(gold)
    variant = get_product_variant(
        cur, category=category, product_id=product_id, gold=gold, carat=carat,
        require_published=require_published,
    )
    if not variant:
        return None
    resolved = resolve_product_id(
        cur, category=category, type_ref=product_id, require_published=require_published,
    )
    if category == "chain":
        pid = resolved or product_id
        try:
            wax = _resolve_chain_wax(cur, product_id=pid, carat=carat, length_cm=length_cm)
        except ValueError:
            return None
    else:
        wax = float(variant["weight_chin"])
    weight = wax_to_metal_chin(wax, gold)
    if category == "bracelet" and length_cm is not None:
        weight *= float(length_cm) / BRACELET_REFERENCE_LENGTH_CM
    return variant, weight


def _metal_pre_tax(gold_prices: dict, gold: str, weight_chin: float) -> tuple[float, float]:
    """Metal cost pre-tax: 金屬重(台錢) × 成色金價(元/台錢).

    Cache stores 黃金飾金 售價 as 元/公克 (board 元/錢 ÷ CHIN_TO_GRAMS).
    Excel O字鍊: 臘重×factor = 金屬重(錢); × (飾金×成色) + 工費.
    """
    per_gram = gold_prices[METAL_SYMBOL[gold]] * PURITY_MULTIPLIER[gold]
    per_chin = per_gram * CHIN_TO_GRAMS
    return per_chin * weight_chin, per_gram


def _compute_chain_addon(
    cur, gold_prices: dict, *, chain_product_id: str, chain_gold: str,
    chain_length_cm: Any, require_published: bool,
    chain_thickness: str | None = None,
    tax_rate: float = TAX_RATE,
) -> dict | None:
    """Full standalone O字鍊 quote for 搭配鏈條 (metal+tax + labor/addon, or manual)."""
    thickness = (chain_thickness or DEFAULT_ATTACHED_CHAIN_THICKNESS).strip()
    looked_up = _lookup_weight(
        cur, category="chain", product_id=chain_product_id, gold=chain_gold,
        carat=thickness or DEFAULT_ATTACHED_CHAIN_THICKNESS,
        length_cm=chain_length_cm, require_published=require_published,
    )
    if not looked_up:
        return None
    variant, weight_chin = looked_up
    if variant.get("manual_price_twd") is not None:
        return {"chainPrice": float(variant["manual_price_twd"])}
    labor = _labor_fee(
        "chain", chain_gold, _effective_addon_price(cur, "chain", variant)
    )
    pre_tax, _ = _metal_pre_tax(gold_prices, chain_gold, weight_chin)
    return {"chainPrice": round(pre_tax * (1 + tax_rate)) + labor}


def compute_order_pricing(cur, data: dict[str, Any], *, require_published: bool = True) -> dict[str, Any]:
    """Single source of truth for cart/order pricing; never trust data["clientPricing"]."""
    category = data.get("category")
    carat = data.get("carat")
    gold = data.get("gold")
    length_cm = data.get("lengthCm")
    diamond_kind = data.get("diamondKind") or "white"
    fancy_color = data.get("fancyColor")
    stone_count = data.get("stoneCount")
    diamond_shape = data.get("diamondShape") or "round"
    include_chain = data.get("includeChain")
    chain_product_id = data.get("chainProductId")
    chain_gold = data.get("chainGold")
    chain_length = data.get("chainLength")
    chain_thickness = data.get("chainThickness") or DEFAULT_ATTACHED_CHAIN_THICKNESS
    product_id = data.get("type")
    line_qty = _as_line_quantity(data.get("quantity"), category=category)

    if not category or not carat or not product_id:
        return {"ready": False}
    if category in ("chain", "bracelet") and length_cm is None:
        return {"ready": False}

    overrides = load_overrides(cur)

    # Memorial loose diamonds: list price only (no metal / labor).
    # Qty packs into multi-stone tables when stoneCount is not already a package.
    if category == "diamond":
        sale_total, compare_at = memorial_diamond_line_totals(
            carat,
            diamond_kind=diamond_kind,
            fancy_color=fancy_color,
            stone_count=stone_count,
            diamond_shape=diamond_shape,
            line_qty=line_qty,
            overrides=overrides,
        )
        if sale_total is None:
            return {"ready": False}
        out = {
            "ready": True,
            "diamondPrice": sale_total,
            "taijinPrice": 0,
            "laborPrice": 0,
            "metalworkPrice": 0,
            "chainPrice": None,
            "total": round(sale_total),
            "quantity": line_qty,
            "priceSource": "server",
        }
        if compare_at is not None:
            out["compareAtTotal"] = round(compare_at)
        return out

    if not gold:
        return {"ready": False}
    gold = normalize_gold(gold)
    if chain_gold:
        chain_gold = normalize_gold(chain_gold)
    ov_tax = overrides.get("taxRate")
    tax_rate = ov_tax if isinstance(ov_tax, (int, float)) else TAX_RATE

    looked_up = _lookup_weight(
        cur, category=category, product_id=product_id, gold=gold, carat=carat,
        length_cm=length_cm, require_published=require_published,
    )
    if not looked_up:
        return {"ready": False, "error": "product not available"}
    variant, weight_chin = looked_up
    weight_grams = weight_chin * CHIN_TO_GRAMS
    labor_pre_tax = _labor_fee(
        category, gold, _effective_addon_price(cur, category, variant)
    )
    ring_size_addon = 0
    if category == "ring":
        ring_cfg = _product_ring_size_config(
            cur, category=category, product_id=product_id,
            require_published=require_published,
        )
        ring_size_addon = ring_size_addon_from_config(ring_cfg, data.get("ringSize"))

    # 手動定價: fixed unit total for every metal category (incl. standalone chain).
    if variant.get("manual_price_twd") is not None:
        gold_prices = get_metal_prices(cur)
        unit_total = float(variant["manual_price_twd"]) + ring_size_addon
        return {
            "ready": True,
            "total": unit_total * line_qty,
            "manualOverride": True,
            "ringSizePrice": ring_size_addon or None,
            "weightGrams": weight_grams * line_qty,
            "goldRatePerGram": gold_prices[METAL_SYMBOL[gold]] * PURITY_MULTIPLIER[gold],
            "priceSource": "server",
            "quantity": line_qty,
        }

    gold_prices = get_metal_prices(cur)
    taijin_pre_tax, rate_used = _metal_pre_tax(gold_prices, gold, weight_chin)
    taijin_display = round(taijin_pre_tax * (1 + tax_rate))
    # Labor is flat NT$ — not taxed. Tax only on metal.
    # 搭配鏈條 uses full O字鍊 quote (taxed metal + chain labor/addon or manual).
    # Earring per-row 耳扣價錢 folds into labor / 金工價格 (with 品項加價).
    # Ring size 品項加價 stacks on top of category/variant labor addon (not a replace).
    labor_display = labor_pre_tax
    if category == "earring":
        labor_display = labor_pre_tax + _ear_clasp_fee(variant)
    elif category == "ring" and ring_size_addon:
        labor_display = labor_pre_tax + ring_size_addon
    # Diamond list price is tax-inclusive; metal/chain quotes include tax at display time.

    diamond_price = None
    if category != "chain":
        diamond_price = compute_diamond_list_price(
            carat, diamond_kind=diamond_kind, fancy_color=fancy_color,
            stone_count=stone_count, diamond_shape=diamond_shape, category=category,
            overrides=overrides,
        )
        if diamond_price is None:
            return {"ready": False}

    # 配鑽: fixed total wins; else 克拉數 × 一克拉價格 (side_stone_price_twd = ppc)
    side_stone_ppc = None
    if category != "chain" and variant.get("side_stone_price_twd") is not None:
        side_stone_ppc = float(variant["side_stone_price_twd"])
    side_stone_carat = None
    if category != "chain" and variant.get("side_stone_carat") is not None:
        side_stone_carat = float(variant["side_stone_carat"])
    side_stone_price = None
    if category != "chain" and variant.get("side_stone_total_twd") is not None:
        side_stone_price = round(float(variant["side_stone_total_twd"]))
    elif side_stone_ppc is not None and side_stone_carat is not None:
        side_stone_price = round(side_stone_carat * side_stone_ppc)

    if line_qty > 1:
        if diamond_price is not None:
            diamond_price = diamond_price * line_qty
        if side_stone_price is not None:
            side_stone_price = side_stone_price * line_qty
        taijin_display = round(taijin_display * line_qty)
        labor_display = labor_display * line_qty
        weight_grams = weight_grams * line_qty

    total = (diamond_price or 0) + (side_stone_price or 0) + taijin_display + labor_display
    chain_display = None

    if category == "pendant" and include_chain and chain_product_id and chain_gold and chain_length:
        addon = _compute_chain_addon(
            cur, gold_prices, chain_product_id=chain_product_id, chain_gold=chain_gold,
            chain_length_cm=chain_length, require_published=require_published,
            chain_thickness=chain_thickness, tax_rate=tax_rate,
        )
        if not addon:
            return {"ready": False, "error": "invalid chain option"}
        chain_display = round(addon["chainPrice"]) * line_qty
        total += chain_display

    return {
        "ready": True,
        "diamondPrice": diamond_price,
        "sideStonePrice": side_stone_price,
        "sideStoneCarat": side_stone_carat,
        "taijinPrice": taijin_display,
        "laborPrice": labor_display,
        "metalworkPrice": taijin_display + labor_display,
        "ringSizePrice": ring_size_addon or None,
        "chainPrice": chain_display,
        "total": round(total),
        "weightGrams": weight_grams,
        "goldRatePerGram": rate_used,
        "priceSource": "server",
        "manualOverride": False,
        "quantity": line_qty,
    }
