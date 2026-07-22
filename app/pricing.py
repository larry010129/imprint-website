"""Server-side authoritative order pricing — ported from backend/lib/pricing.js.

Client-submitted prices (`clientPricing`) must never be trusted when writing to
cart_items/orders; this module recomputes the price from the DB catalog + live
gold rate. See shop_controller.add_to_cart, which is the sole write path.
"""

from __future__ import annotations

from typing import Any

from app.catalog import resolve_product_id

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
DEFAULT_STONE_COUNT_BY_CATEGORY = {"earring": 2, "ring": 2, "pendant": 2}
STONE_COUNT_CATEGORIES = {"earring"}

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
# Universal 金工費 (flat NT$, not taxed). Same for every category.
LABOR_FEE_TWD = 5000

TAX_RATE = 0.05
CHIN_TO_GRAMS = 3.75
CHAIN_REFERENCE_LENGTH_CM = 45
BRACELET_REFERENCE_LENGTH_CM = 18


def _as_stone_count(value: Any) -> int | None:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    return count if count in VALID_STONE_COUNTS else None


def _shape_carat_allowed(carat_num: float, diamond_shape: str | None) -> bool:
    return (diamond_shape or "round") == "round" or carat_num >= FANCY_MIN_CARAT


def _shape_surcharge_rate(diamond_shape: str | None) -> float:
    return NON_ROUND_SHAPE_SURCHARGE if (diamond_shape or "round") != "round" else 0.0


def _multi_stone_tier(carat_key: str, carat_num: float, table: dict) -> str | None:
    if table.get(carat_key) is not None:
        return carat_key
    return "0.3_plus" if carat_num > 0.3 else None


def _resolve_multi_price(table: dict, tier: str, stone_count: int) -> float | None:
    if tier == "0.3_plus":
        row = table.get("0.3") or {}
        multiplier = MULTI_STONE_ABOVE_03_MULTIPLIER.get(stone_count)
        base_row = row.get(stone_count)
        return round(base_row * multiplier) if (base_row is not None and multiplier) else None
    return (table.get(tier) or {}).get(stone_count)


def compute_diamond_list_price(
    carat_key: str | None,
    *,
    diamond_kind: str = "white",
    fancy_color: str | None = None,
    stone_count: Any = None,
    diamond_shape: str = "round",
    category: str | None = None,
) -> float | None:
    if not carat_key or category == "chain":
        return None
    try:
        carat_num = float(carat_key)
    except (TypeError, ValueError):
        return None

    multi_stone = category in STONE_COUNT_CATEGORIES
    if not _shape_carat_allowed(carat_num, diamond_shape):
        return None

    base = None
    if diamond_kind == "white":
        if multi_stone:
            count = _as_stone_count(stone_count) or DEFAULT_STONE_COUNT_BY_CATEGORY.get(category, 2)
            tier = _multi_stone_tier(carat_key, carat_num, WHITE_MULTI_DIAMOND_PRICE)
            base = _resolve_multi_price(WHITE_MULTI_DIAMOND_PRICE, tier, count) if tier else None
        else:
            base = DIAMOND_PRICE.get(carat_key)
    elif diamond_kind == "fancy":
        if fancy_color not in VALID_FANCY_COLORS or carat_num < FANCY_MIN_CARAT:
            return None
        if multi_stone:
            count = _as_stone_count(stone_count) or DEFAULT_STONE_COUNT_BY_CATEGORY.get(category, 2)
            tier = _multi_stone_tier(carat_key, carat_num, COLORED_MULTI_DIAMOND_PRICE)
            base = _resolve_multi_price(COLORED_MULTI_DIAMOND_PRICE, tier, count) if tier else None
        else:
            base = COLORED_SINGLE_DIAMOND_PRICE.get(carat_key)
            if base is None and carat_key == "1.0":
                base = COLORED_SINGLE_DIAMOND_PRICE.get("1")
    else:
        return None

    if base is None:
        return None
    surcharge = _shape_surcharge_rate(diamond_shape)
    return round(base * (1 + surcharge)) if surcharge else base


def get_metal_prices(cur) -> dict[str, float]:
    cur.execute("select xau_per_gram, xpt_per_gram, xag_per_gram from gold_price_cache where id = 1")
    row = cur.fetchone()
    if not row:
        return {"XAU": 4300.0, "XPT": 1050.0, "XAG": 30.0}
    return {
        "XAU": float(row["xau_per_gram"]),
        "XPT": float(row["xpt_per_gram"]),
        "XAG": float(row["xag_per_gram"]),
    }


def _carat_lookup_keys(carat: str) -> list[str]:
    if carat in ("3fen", "4fen"):
        return [carat]
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
    factor = WAX_TO_METAL_CHIN.get(gold)
    if factor is None:
        raise ValueError(f"unknown gold: {gold}")
    return wax_chin * factor


def get_product_variant(
    cur, *, category: str, product_id: str, gold: str, carat: str, require_published: bool = True
) -> dict | None:
    resolved = resolve_product_id(
        cur, category=category, type_ref=product_id, require_published=require_published,
    )
    if not resolved:
        return None
    for carat_key in _carat_lookup_keys(carat):
        if require_published:
            cur.execute(
                """
                select pv.* from product_variants pv
                join products p on p.id = pv.product_id
                where p.id = %s and p.category = %s
                  and pv.gold = %s and pv.carat = %s and p.is_published = true
                """,
                (resolved, category, gold, carat_key),
            )
        else:
            cur.execute(
                """
                select pv.* from product_variants pv
                join products p on p.id = pv.product_id
                where p.id = %s and p.category = %s
                  and pv.gold = %s and pv.carat = %s
                """,
                (resolved, category, gold, carat_key),
            )
        row = cur.fetchone()
        if row:
            return row
    return None


def _lookup_weight(
    cur, *, category: str, product_id: str, gold: str, carat: str,
    length_cm: Any, require_published: bool,
) -> tuple[dict, float] | None:
    variant = get_product_variant(
        cur, category=category, product_id=product_id, gold=gold, carat=carat,
        require_published=require_published,
    )
    if not variant:
        return None
    weight = wax_to_metal_chin(float(variant["weight_chin"]), gold)
    if category == "chain" and length_cm is not None:
        weight *= float(length_cm) / CHAIN_REFERENCE_LENGTH_CM
    elif category == "bracelet" and length_cm is not None:
        weight *= float(length_cm) / BRACELET_REFERENCE_LENGTH_CM
    return variant, weight


def _metal_pre_tax(gold_prices: dict, gold: str, weight_chin: float) -> tuple[float, float]:
    """Metal cost pre-tax: 金屬重(台錢) × 成色金價(元/台錢). BOT cache is 元/公克."""
    per_gram = gold_prices[METAL_SYMBOL[gold]] * PURITY_MULTIPLIER[gold]
    per_chin = per_gram * CHIN_TO_GRAMS
    return per_chin * weight_chin, per_gram


def _compute_chain_addon(
    cur, gold_prices: dict, *, chain_product_id: str, chain_gold: str,
    chain_length_cm: Any, require_published: bool,
) -> dict | None:
    looked_up = _lookup_weight(
        cur, category="chain", product_id=chain_product_id, gold=chain_gold, carat="3fen",
        length_cm=chain_length_cm, require_published=require_published,
    )
    if not looked_up:
        return None
    variant, weight_chin = looked_up

    if variant.get("manual_price_twd") is not None:
        pre_tax = float(variant["manual_price_twd"])
    else:
        # 搭配鏈條 = metal only; standalone chain still gets LABOR_FEE_TWD in compute_order_pricing
        amount, _ = _metal_pre_tax(gold_prices, chain_gold, weight_chin)
        pre_tax = amount
    return {"chainPreTax": pre_tax}


def compute_order_pricing(cur, data: dict[str, Any], *, require_published: bool = True) -> dict[str, Any]:
    """The single source of truth for cart/order pricing. Mirrors
    backend/lib/pricing.js computeOrderPricing(); never trust data["clientPricing"]."""
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
    product_id = data.get("type")

    if not category or not carat or not gold or not product_id:
        return {"ready": False}
    if category in ("chain", "bracelet") and length_cm is None:
        return {"ready": False}

    looked_up = _lookup_weight(
        cur, category=category, product_id=product_id, gold=gold, carat=carat,
        length_cm=length_cm, require_published=require_published,
    )
    if not looked_up:
        return {"ready": False, "error": "product not available"}
    variant, weight_chin = looked_up
    weight_grams = weight_chin * CHIN_TO_GRAMS
    labor_pre_tax = LABOR_FEE_TWD

    if variant.get("manual_price_twd") is not None:
        gold_prices = get_metal_prices(cur)
        return {
            "ready": True,
            "total": float(variant["manual_price_twd"]),
            "manualOverride": True,
            "weightGrams": weight_grams,
            "goldRatePerGram": gold_prices[METAL_SYMBOL[gold]] * PURITY_MULTIPLIER[gold],
            "priceSource": "server",
        }

    gold_prices = get_metal_prices(cur)
    taijin_pre_tax, rate_used = _metal_pre_tax(gold_prices, gold, weight_chin)
    taijin_display = round(taijin_pre_tax * (1 + TAX_RATE))
    # Labor is flat NT$ — not taxed. Tax only on metal (and 搭配鏈條 metal).
    labor_display = labor_pre_tax
    # Diamond list price is tax-inclusive; metal/chain quotes include 5% at display time.

    diamond_price = None
    if category != "chain":
        diamond_price = compute_diamond_list_price(
            carat, diamond_kind=diamond_kind, fancy_color=fancy_color,
            stone_count=stone_count, diamond_shape=diamond_shape, category=category,
        )
        if diamond_price is None:
            return {"ready": False}

    total = (diamond_price or 0) + taijin_display + labor_display
    chain_display = None

    if category == "pendant" and include_chain and chain_product_id and chain_gold and chain_length:
        addon = _compute_chain_addon(
            cur, gold_prices, chain_product_id=chain_product_id, chain_gold=chain_gold,
            chain_length_cm=chain_length, require_published=require_published,
        )
        if not addon:
            return {"ready": False, "error": "invalid chain option"}
        chain_display = round(addon["chainPreTax"] * (1 + TAX_RATE))
        total += chain_display

    return {
        "ready": True,
        "diamondPrice": diamond_price,
        "taijinPrice": taijin_display,
        "laborPrice": labor_display,
        "metalworkPrice": taijin_display + labor_display,
        "chainPrice": chain_display,
        "total": round(total),
        "weightGrams": weight_grams,
        "goldRatePerGram": rate_used,
        "priceSource": "server",
        "manualOverride": False,
    }
