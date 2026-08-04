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
            and (not url.startswith("/static/") or static_url_exists(url))
        ):
            images_by_color.setdefault(image["color"], []).append(url)
    return images_by_color


def _first_thumb_url(
    images_by_color: dict[str, list[str]],
    *,
    default_color: str | None = None,
) -> str | None:
    """Prefer default metal + white diamond for lite style-grid thumbs."""
    metal = (default_color or "white").strip().lower() or "white"
    # Exact slots first (metal-diamond[-chain]); legacy single key = metal.
    for key in (f"{metal}-white", metal, f"{metal}-white-white"):
        urls = images_by_color.get(key)
        if urls:
            return urls[0]
    # Any white-diamond slot (skip *-yellow / *-blue / *-pink fancy stones).
    for key, urls in images_by_color.items():
        if not urls:
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
    golds = _sort_golds({v["gold"] for v in variants})
    carats = _sort_carats({_variant_carat_key(v["carat"]) for v in variants})
    images_by_color = _usable_images_by_color(images)
    return {
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
        "colors": sorted(images_by_color.keys()),
        "thumbUrl": _first_thumb_url(images_by_color, default_color=product.get("default_color")),
        "draft": not product["is_published"],
    }


def build_catalog_product(product: dict, variants: list[dict], images: list[dict]) -> dict:
    golds = _sort_golds({v["gold"] for v in variants})
    carats = _sort_carats({_variant_carat_key(v["carat"]) for v in variants})

    weights: dict[str, dict[str, float]] = {}
    manual_prices: dict[str, dict[str, float]] = {}
    side_stone_prices: dict[str, dict[str, float]] = {}
    side_stone_carats: dict[str, dict[str, float]] = {}
    for variant in variants:
        gold = variant["gold"]
        carat = _variant_carat_key(variant["carat"])
        weights.setdefault(gold, {})[carat] = float(variant["weight_chin"])
        if variant.get("manual_price_twd") is not None:
            manual_prices.setdefault(gold, {})[carat] = float(variant["manual_price_twd"])
        if variant.get("side_stone_price_twd") is not None:
            side_stone_prices.setdefault(gold, {})[carat] = float(variant["side_stone_price_twd"])
        if variant.get("side_stone_carat") is not None:
            side_stone_carats.setdefault(gold, {})[carat] = float(variant["side_stone_carat"])

    style_key = legacy_style_key(product, images)
    images_by_color = _usable_images_by_color(images)

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
    for product in products:
        product_id = product["id"]
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
