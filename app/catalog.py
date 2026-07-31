"""Public product catalog — format matches shop.js expectations."""

from __future__ import annotations

import re

CATEGORY_DISPLAY_ORDER = ["pendant", "ring", "earring", "bracelet", "chain"]
METAL_DISPLAY_ORDER = ["9k", "14k", "18k", "pt950", "s925"]

_STYLE_FROM_PATH = re.compile(r"(?:^|/)([a-z]+)-([A-C])\.(?:svg|png|jpe?g)", re.I)


def _sort_golds(golds: set[str]) -> list[str]:
    order = {g: i for i, g in enumerate(METAL_DISPLAY_ORDER)}
    return sorted(golds, key=lambda g: order.get(g, 99))


from app.admin_products import is_auto_stock_product_image, is_dead_catalog_placeholder
from app.chain_catalog import DEFAULT_NECKLACE_TYPE, necklace_type_length_weights
from app.image_urls import (
    _is_raster_url,
    is_uuid,
    resolve_product_image_url,
    static_url_exists,
)


def style_key_from_images(images: list[dict]) -> str | None:
    """Read pendant-A / ring-B from stored image paths (stable when sort_order has gaps)."""
    for image in images:
        path = (image.get("file_path") or "").replace("\\", "/")
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
    """Map API UUID or bundled style key (ring-A) to products.id."""
    if not type_ref or not category:
        return None
    ref = str(type_ref).strip()
    if is_uuid(ref):
        return ref

    match = _LEGACY_STYLE_RE.match(ref)
    if match:
        cat = match.group(1).lower()
        letter = match.group(2).upper()
        if cat != category.strip().lower():
            return None
        sort_order = ord(letter) - ord("A")
        sql = "select id from products where category = %s and sort_order = %s"
        params: list = [cat, sort_order]
        if require_published:
            sql += " and is_published = true"
        cur.execute(sql, params)
        row = cur.fetchone()
        return str(row["id"]) if row else None

    return None


def legacy_style_key(product: dict, images: list[dict] | None = None) -> str | None:
    """Map to shop-product asset ids only when stored image paths contain them."""
    if images:
        return style_key_from_images(images)
    return None


def build_catalog_product(product: dict, variants: list[dict], images: list[dict]) -> dict:
    golds = _sort_golds({v["gold"] for v in variants})
    carats = sorted({v["carat"] for v in variants})

    weights: dict[str, dict[str, float]] = {}
    manual_prices: dict[str, dict[str, float]] = {}
    side_stone_prices: dict[str, dict[str, float]] = {}
    side_stone_carats: dict[str, dict[str, float]] = {}
    for variant in variants:
        gold = variant["gold"]
        carat = variant["carat"]
        weights.setdefault(gold, {})[carat] = float(variant["weight_chin"])
        if variant.get("manual_price_twd") is not None:
            manual_prices.setdefault(gold, {})[carat] = float(variant["manual_price_twd"])
        if variant.get("side_stone_price_twd") is not None:
            side_stone_prices.setdefault(gold, {})[carat] = float(variant["side_stone_price_twd"])
        if variant.get("side_stone_carat") is not None:
            side_stone_carats.setdefault(gold, {})[carat] = float(variant["side_stone_carat"])

    style_key = legacy_style_key(product, images)
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
            and (not url.startswith("/static/") or static_url_exists(url))
        ):
            images_by_color.setdefault(image["color"], []).append(url)

    return {
        "id": str(product["id"]),
        "styleKey": style_key,
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
        "colors": sorted(images_by_color.keys()),
        "images": images_by_color,
        "weights": weights,
        "manualPrices": manual_prices,
        "sideStonePrices": side_stone_prices,
        "sideStoneCarats": side_stone_carats,
        "lengthWeights": _effective_chain_length_weights(product),
        "chainType": product.get("chain_type") or (
            DEFAULT_NECKLACE_TYPE if product.get("category") == "chain" else None
        ),
        "draft": not product["is_published"],
    }


def _effective_chain_length_weights(product: dict) -> dict:
    """Admin overrides win; otherwise Excel/type table (抖圓鏈 etc.)."""
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


def build_catalog_response(
    products: list[dict],
    variants_by_product: dict,
    images_by_product: dict,
    *,
    category_order: list[str] | None = None,
    category_meta: dict[str, dict] | None = None,
) -> dict:
    if not products and not category_meta:
        return {"categories": {}, "categoryOrder": [], "categoryMeta": {}}

    categories: dict[str, list[dict]] = {}
    for product in products:
        product_id = product["id"]
        entry = build_catalog_product(
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
