"""Public product catalog — format matches shop.js expectations."""

from __future__ import annotations

import re

CATEGORY_DISPLAY_ORDER = ["diamond", "pendant", "ring", "earring", "bracelet", "chain"]
METAL_DISPLAY_ORDER = ["9k", "14k", "18k", "pt950", "s925"]

_STYLE_FROM_PATH = re.compile(r"(?:^|/)([a-z]+)-([A-C])\.(?:svg|png|jpe?g)", re.I)


def _canonical_gold_key(gold: object) -> str:
    """Shop/pricing metal key — silver925/S925 → s925, pt → pt950."""
    from app.pricing import normalize_gold

    return normalize_gold(gold)


def _sort_golds(golds: set[str]) -> list[str]:
    order = {g: i for i, g in enumerate(METAL_DISPLAY_ORDER)}
    return sorted(golds, key=lambda g: order.get(g, 99))


from app.admin_products import (
    image_covers_default_color,
    is_auto_stock_product_image,
    is_dead_catalog_placeholder,
    is_pending_product_image,
)
from app.chain_catalog import DEFAULT_NECKLACE_TYPE, necklace_type_length_weights
from app.image_urls import (
    _is_raster_url,
    is_uuid,
    resolve_product_image_url,
    static_url_exists,
)
from app.memorial_diamonds import DIAMOND_CARATS, normalize_style_key
from app.pricing_overrides import canonical_carat


def _variant_carat_key(raw: object) -> str:
    """Normalize variant carat keys so 0.10 / 0.1 / Decimal meet as '0.1'.

    Chain thicknesses (1.0mm) stay as stored strings.
    """
    text = str(raw or "").strip()
    if not text:
        return text
    if text.lower().endswith("mm"):
        return text
    return canonical_carat(text) or text


def _sort_carats(carats: set[str]) -> list[str]:
    """Numeric order so 0.1 < 0.2 < 0.3 (not lexicographic string quirks)."""

    def sort_key(carat: str) -> tuple[int, float | str]:
        try:
            return (0, float(carat))
        except (TypeError, ValueError):
            return (1, str(carat))

    return sorted(carats, key=sort_key)


def style_key_from_images(images: list[dict]) -> str | None:
    """Read pendant-A / ring-B from real upload paths only (not shop-product stock)."""
    for image in images:
        path = (image.get("file_path") or "").replace("\\", "/")
        if is_auto_stock_product_image(path) or is_dead_catalog_placeholder(path):
            continue
        match = _STYLE_FROM_PATH.search(path)
        if match:
            return f"{match.group(1).lower()}-{match.group(2).upper()}"
    return None


_LEGACY_STYLE_RE = re.compile(r"^(pendant|ring|earring|bracelet|chain)-([A-C])$", re.I)


def resolve_product_id(
    cur,
    *,
    category: str,
    type_ref: str,
    require_published: bool = True,
) -> str | None:
    """Map API UUID or bundled style key (ring-A / diamond-*) to products.id."""
    if not type_ref or not category:
        return None
    ref = str(type_ref).strip()
    if is_uuid(ref):
        return ref

    cat = category.strip().lower()
    memorial_key = normalize_style_key(ref)
    if cat == "diamond" and memorial_key:
        sql = "select id from products where category = %s and style_key = %s"
        params: list = [cat, memorial_key]
        if require_published:
            sql += " and is_published = true"
        cur.execute(sql, params)
        row = cur.fetchone()
        return str(row["id"]) if row else None

    match = _LEGACY_STYLE_RE.match(ref)
    if match:
        letter_cat = match.group(1).lower()
        letter = match.group(2).upper()
        if letter_cat != cat:
            return None
        sort_order = ord(letter) - ord("A")
        sql = "select id from products where category = %s and sort_order = %s"
        params = [letter_cat, sort_order]
        if require_published:
            sql += " and is_published = true"
        cur.execute(sql, params)
        row = cur.fetchone()
        return str(row["id"]) if row else None

    return None


def legacy_style_key(product: dict, images: list[dict] | None = None) -> str | None:
    """Prefer products.style_key; else letter SKU from uploaded image paths."""
    stored = product.get("style_key") or product.get("styleKey")
    if stored:
        key = str(stored).strip()
        if key:
            return key
    if images:
        return style_key_from_images(images)
    return None


def _diamond_carats_or_default(carats: list[str]) -> list[str]:
    return carats if carats else list(DIAMOND_CARATS)


def _usable_images_by_color(images: list[dict]) -> dict[str, list[str]]:
    images_by_color: dict[str, list[str]] = {}
    for image in images:
        raw = image.get("file_path")
        if is_auto_stock_product_image(raw):
            continue
        url = resolve_product_image_url(raw)
        if (
            url
            and _is_raster_url(url)
            and not is_dead_catalog_placeholder(url)
            and not is_auto_stock_product_image(url)
            and not is_pending_product_image(url)
            and (not url.startswith("/static/") or static_url_exists(url))
        ):
            images_by_color.setdefault(image["color"], []).append(url)
    return images_by_color


def _image_slot_order(images: list[dict]) -> list[str]:
    """Admin 圖片選項 block order — first DB sort_order row per color key."""
    order: list[str] = []
    seen: set[str] = set()
    for image in images:
        color = str(image.get("color") or "white").strip()
        if not color or color in seen:
            continue
        seen.add(color)
        order.append(color)
    return order


def _catalog_slot_colors(
    images: list[dict],
    images_by_color: dict[str, list[str]],
) -> list[str]:
    """Slot keys in admin save order; extras appended in map insertion order."""
    ordered = [color for color in _image_slot_order(images) if color in images_by_color]
    for key in images_by_color:
        if key not in ordered:
            ordered.append(key)
    return ordered


def _default_color_slot_keys(metal: str, category: str | None = None) -> list[str]:
    """Preferred slot keys for 預設顏色 — white diamond first, then fancy on same metal."""
    metal = (metal or "white").strip().lower() or "white"
    if (category or "").strip().lower() == "chain":
        return [f"{metal}-white", metal]
    keys = [f"{metal}-white"]
    for diamond in ("yellow", "blue", "pink"):
        keys.append(f"{metal}-{diamond}")
    return keys


def _first_thumb_url(
    images_by_color: dict[str, list[str]],
    *,
    images: list[dict] | None = None,
    default_color: str | None = None,
    category: str | None = None,
) -> str | None:
    """預設顏色 slot first; then admin block order; then any usable upload."""
    metal = (default_color or "white").strip().lower() or "white"
    tried: set[str] = set()

    def pick(key: str) -> str | None:
        if not key or key in tried:
            return None
        tried.add(key)
        urls = images_by_color.get(key)
        if urls:
            return urls[0]
        return None

    if (category or "").strip().lower() == "diamond":
        # Color product: image slots are shapes — prefer round thumb.
        for key in ("round", metal):
            url = pick(key)
            if url:
                return url
        for key in images_by_color:
            if key not in tried and image_covers_default_color(
                key, metal, category="diamond"
            ):
                url = pick(key)
                if url:
                    return url
    for key in _default_color_slot_keys(metal, category):
        url = pick(key)
        if url:
            return url
    for key in images_by_color:
        if key not in tried and image_covers_default_color(
            key, metal, category=category
        ):
            url = pick(key)
            if url:
                return url

    if images:
        for color in _image_slot_order(images):
            url = pick(color)
            if url:
                return url

    for key, urls in images_by_color.items():
        if not urls or key in tried:
            continue
        parts = str(key).split("-")
        if len(parts) == 1 or parts[1] == "white":
            return urls[0]
    for urls in images_by_color.values():
        if urls:
            return urls[0]
    return None


def _product_sort_order(product: dict) -> int | None:
    raw = product.get("sort_order")
    try:
        order = int(raw)
    except (TypeError, ValueError):
        return None
    return order


def build_catalog_product_lite(product: dict, variants: list[dict], images: list[dict]) -> dict:
    """Style-grid payload — option lists + thumb, no weights/images maps."""
    golds = _sort_golds({_canonical_gold_key(v["gold"]) for v in variants})
    carats = _sort_carats({_variant_carat_key(v["carat"]) for v in variants})
    if product.get("category") == "diamond":
        golds = []
        carats = _diamond_carats_or_default(carats)
    images_by_color = _usable_images_by_color(images)
    slot_colors = _catalog_slot_colors(images, images_by_color)
    entry = {
        "id": str(product["id"]),
        "styleKey": legacy_style_key(product, images),
        "category": product.get("category"),
        "sortOrder": _product_sort_order(product),
        "nameZh": product["name_zh"],
        "nameEn": product["name_en"],
        "defaultColor": product["default_color"],
        "allowsEngraving": bool(product.get("allows_engraving", True)),
        "allowsFancyShapes": bool(product.get("allows_fancy_shapes", True)),
        "allowsPendantOnly": bool(product.get("allows_pendant_only", True)),
        "allowsWithChain": bool(product.get("allows_with_chain", True)),
        "golds": golds,
        "carats": carats,
        "colors": slot_colors,
        "imageSlotOrder": _image_slot_order(images),
        "thumbUrl": _first_thumb_url(
            images_by_color,
            images=images,
            default_color=product.get("default_color"),
            category=product.get("category"),
        ),
        "draft": not product["is_published"],
    }
    # Memorial diamond style cards need images even on lite catalog.
    if product.get("category") == "diamond":
        entry["images"] = images_by_color
        entry["descriptionZh"] = product.get("description_zh")
        entry["descriptionEn"] = product.get("description_en")
    return entry


def build_catalog_product(
    product: dict,
    variants: list[dict],
    images: list[dict],
    *,
    category_ring_size_config: dict | None = None,
) -> dict:
    golds = _sort_golds({_canonical_gold_key(v["gold"]) for v in variants})
    carats = _sort_carats({_variant_carat_key(v["carat"]) for v in variants})
    if product.get("category") == "diamond":
        golds = []
        carats = _diamond_carats_or_default(carats)

    weights: dict[str, dict[str, float]] = {}
    manual_prices: dict[str, dict[str, float]] = {}
    side_stone_prices: dict[str, dict[str, float]] = {}
    side_stone_carats: dict[str, dict[str, float]] = {}
    side_stone_totals: dict[str, dict[str, float]] = {}
    ear_clasp_prices: dict[str, dict[str, float]] = {}
    addon_prices: dict[str, dict[str, float]] = {}
    for variant in variants:
        gold = _canonical_gold_key(variant["gold"])
        carat = _variant_carat_key(variant["carat"])
        weights.setdefault(gold, {})[carat] = float(variant["weight_chin"])
        if variant.get("manual_price_twd") is not None:
            manual_prices.setdefault(gold, {})[carat] = float(variant["manual_price_twd"])
        if variant.get("side_stone_price_twd") is not None:
            side_stone_prices.setdefault(gold, {})[carat] = float(variant["side_stone_price_twd"])
        if variant.get("side_stone_carat") is not None:
            side_stone_carats.setdefault(gold, {})[carat] = float(variant["side_stone_carat"])
        if variant.get("side_stone_total_twd") is not None:
            side_stone_totals.setdefault(gold, {})[carat] = float(variant["side_stone_total_twd"])
        addon_raw = variant.get("addon_price_twd")
        if addon_raw is None:
            addon_raw = variant.get("addonPriceTwd")
        # Omit 0 so client falls back to category 品項加價 (same as server).
        if addon_raw is not None and float(addon_raw) > 0:
            addon_prices.setdefault(gold, {})[carat] = float(addon_raw)
        ear_clasp_raw = variant.get("ear_clasp_price_twd")
        if ear_clasp_raw is None:
            ear_clasp_raw = variant.get("ear_cuff_price_twd")
        if ear_clasp_raw is not None:
            ear_clasp_prices.setdefault(gold, {})[carat] = float(ear_clasp_raw)

    style_key = legacy_style_key(product, images)
    images_by_color = _usable_images_by_color(images)
    slot_colors = _catalog_slot_colors(images, images_by_color)

    return {
        "id": str(product["id"]),
        "styleKey": style_key,
        "category": product.get("category"),
        "sortOrder": _product_sort_order(product),
        "nameZh": product["name_zh"],
        "nameEn": product["name_en"],
        "descriptionZh": product["description_zh"],
        "descriptionEn": product["description_en"],
        "defaultColor": product["default_color"],
        "allowsEngraving": bool(product.get("allows_engraving", True)),
        "allowsFancyShapes": bool(product.get("allows_fancy_shapes", True)),
        "allowsPendantOnly": bool(product.get("allows_pendant_only", True)),
        "allowsWithChain": bool(product.get("allows_with_chain", True)),
        "golds": golds,
        "carats": carats,
        "colors": slot_colors,
        "imageSlotOrder": _image_slot_order(images),
        "images": images_by_color,
        "weights": weights,
        "manualPrices": manual_prices,
        "sideStonePrices": side_stone_prices,
        "sideStoneCarats": side_stone_carats,
        "sideStoneTotals": side_stone_totals,
        "addonPrices": addon_prices,
        "earClaspPrices": ear_clasp_prices,
        "lengthWeights": _effective_chain_length_weights(product),
        "chainType": product.get("chain_type") or (
            DEFAULT_NECKLACE_TYPE if product.get("category") == "chain" else None
        ),
        "ringSizeConfig": _ring_size_config_for_catalog(
            product, category_ring_size_config=category_ring_size_config
        ),
        "draft": not product["is_published"],
    }


def _ring_size_config_for_catalog(
    product: dict,
    *,
    category_ring_size_config: dict | None = None,
) -> dict | None:
    """Expose ring min/max/step (or legacy sizes[]) to shop; other categories omit.

    Prefer category-level config; fall back to product ring_size_config (legacy).
    """
    if product.get("category") != "ring":
        return None
    sources: list[dict] = []
    if isinstance(category_ring_size_config, dict):
        sources.append(category_ring_size_config)
    product_raw = product.get("ring_size_config")
    if product_raw is None:
        product_raw = product.get("ringSizeConfig")
    if isinstance(product_raw, dict):
        sources.append(product_raw)
    for raw in sources:
        normalized = _normalize_ring_config_dict(raw)
        if normalized is not None:
            return normalized
    return None


def _normalize_ring_config_dict(raw: dict) -> dict | None:
    has_step = any(
        key in raw
        for key in (
            "pricePerSizeTwd",
            "price_per_size_twd",
            "minSize",
            "min_size",
            "maxSize",
            "max_size",
            "chargeAfter",
            "charge_after",
        )
    )
    if has_step:
        min_raw = raw.get("minSize")
        if min_raw is None:
            min_raw = raw.get("min_size")
        if min_raw is None:
            min_raw = raw.get("startSize")
        if min_raw is None:
            min_raw = raw.get("start_size")
        max_raw = raw.get("maxSize")
        if max_raw is None:
            max_raw = raw.get("max_size")
        price_raw = raw.get("pricePerSizeTwd")
        if price_raw is None:
            price_raw = raw.get("price_per_size_twd")
        charge_raw = raw.get("chargeAfter")
        if charge_raw is None:
            charge_raw = raw.get("charge_after")
        if charge_raw is None:
            charge_raw = raw.get("priceFromSize")
        if charge_raw is None:
            charge_raw = raw.get("price_from_size")
        if charge_raw is None:
            charge_raw = raw.get("baseSize")
        if charge_raw is None:
            charge_raw = raw.get("base_size")
        try:
            min_out = int(round(float(min_raw))) if min_raw not in (None, "") else None
        except (TypeError, ValueError):
            min_out = None
        try:
            max_out = int(round(float(max_raw))) if max_raw not in (None, "") else None
        except (TypeError, ValueError):
            max_out = None
        try:
            price_out = float(price_raw) if price_raw not in (None, "") else 0.0
        except (TypeError, ValueError):
            price_out = 0.0
        try:
            charge_out = (
                int(round(float(charge_raw))) if charge_raw not in (None, "") else min_out
            )
        except (TypeError, ValueError):
            charge_out = min_out
        if min_out is None and max_out is None and price_raw in (None, ""):
            return None
        return {
            "minSize": min_out,
            "maxSize": max_out,
            "chargeAfter": charge_out,
            "pricePerSizeTwd": price_out,
            "startSize": min_out,
        }

    start = raw.get("startSize")
    if start is None:
        start = raw.get("start_size")
    sizes_out: list[dict] = []
    for row in raw.get("sizes") or []:
        if not isinstance(row, dict):
            continue
        try:
            size = int(round(float(row.get("size"))))
            addon_raw = row.get("addonPriceTwd")
            if addon_raw is None:
                addon_raw = row.get("addon_price_twd")
            addon = float(addon_raw or 0)
        except (TypeError, ValueError):
            continue
        sizes_out.append({"size": size, "addonPriceTwd": addon})
    if start is None and not sizes_out:
        return None
    try:
        start_out = int(round(float(start))) if start is not None else None
    except (TypeError, ValueError):
        start_out = None
    return {"startSize": start_out, "sizes": sizes_out}


def _effective_chain_length_weights(product: dict) -> dict:
    """Admin overrides win; otherwise Excel/type table (O字鍊 etc.)."""
    if product.get("category") != "chain":
        return product.get("length_weights") or {}
    lw = product.get("length_weights")
    if isinstance(lw, dict) and lw:
        return lw
    return necklace_type_length_weights(product.get("chain_type") or DEFAULT_NECKLACE_TYPE)


def fetch_catalog_rows(cur, *, category: str | None = None, include_drafts: bool = False) -> list[dict]:
    if category:
        if include_drafts:
            cur.execute(
                "select * from products where category = %s order by sort_order, created_at",
                (category,),
            )
        else:
            cur.execute(
                "select * from products where is_published = true and category = %s order by sort_order, created_at",
                (category,),
            )
    elif include_drafts:
        cur.execute("select * from products order by sort_order, created_at")
    else:
        cur.execute("select * from products where is_published = true order by sort_order, created_at")
    return cur.fetchall()


def normalize_catalog_detail(detail: str | None) -> str:
    return "full" if str(detail or "").strip().lower() == "full" else "lite"


def build_catalog_response(
    products: list[dict],
    variants_by_product: dict,
    images_by_product: dict,
    *,
    category_order: list[str] | None = None,
    category_meta: dict[str, dict] | None = None,
    detail: str = "lite",
) -> dict:
    if not products and not category_meta:
        return {"categories": {}, "categoryOrder": [], "categoryMeta": {}}

    builder = (
        build_catalog_product
        if normalize_catalog_detail(detail) == "full"
        else build_catalog_product_lite
    )
    categories: dict[str, list[dict]] = {}
    ring_cat_cfg = None
    if category_meta:
        ring_meta = category_meta.get("ring") or {}
        ring_cat_cfg = ring_meta.get("ringSizeConfig") or ring_meta.get("ring_size_config")
        if not isinstance(ring_cat_cfg, dict):
            ring_cat_cfg = None
    for product in products:
        product_id = product["id"]
        if normalize_catalog_detail(detail) == "full":
            entry = builder(
                product,
                variants_by_product.get(product_id, []),
                images_by_product.get(product_id, []),
                category_ring_size_config=ring_cat_cfg,
            )
        else:
            entry = builder(
                product,
                variants_by_product.get(product_id, []),
                images_by_product.get(product_id, []),
            )
        categories.setdefault(product["category"], []).append(entry)

    present = list(categories.keys())
    preferred = category_order or CATEGORY_DISPLAY_ORDER
    category_order_out = [c for c in preferred if c in present]
    category_order_out.extend(c for c in present if c not in category_order_out)
    return {
        "categories": categories,
        "categoryOrder": category_order_out,
        "categoryMeta": category_meta or {},
    }


def fetch_product_row(
    cur,
    product_id: str,
    *,
    include_drafts: bool = False,
) -> dict | None:
    """Load one product by id; unpublished only when include_drafts."""
    if not product_id:
        return None
    cur.execute("select * from products where id = %s", (product_id,))
    row = cur.fetchone()
    if not row:
        return None
    if not row["is_published"] and not include_drafts:
        return None
    return row


def load_product_children(cur, product_ids: list) -> tuple[dict, dict]:
    if not product_ids:
        return {}, {}
    cur.execute("select * from product_variants where product_id = any(%s)", (product_ids,))
    variants = cur.fetchall()
    cur.execute(
        "select * from product_images where product_id = any(%s) order by sort_order",
        (product_ids,),
    )
    images = cur.fetchall()
    variants_by_product: dict = {}
    images_by_product: dict = {}
    for variant in variants:
        variants_by_product.setdefault(variant["product_id"], []).append(variant)
    for image in images:
        images_by_product.setdefault(image["product_id"], []).append(image)
    return variants_by_product, images_by_product
