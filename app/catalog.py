"""Public product catalog — format matches shop.js expectations."""

from __future__ import annotations

CATEGORY_DISPLAY_ORDER = ["pendant", "ring", "earring", "bracelet", "chain"]
METAL_DISPLAY_ORDER = ["9k", "14k", "18k", "pt950", "s925"]


def _sort_golds(golds: set[str]) -> list[str]:
    order = {g: i for i, g in enumerate(METAL_DISPLAY_ORDER)}
    return sorted(golds, key=lambda g: order.get(g, 99))


from app.image_urls import resolve_product_image_url


def build_catalog_product(product: dict, variants: list[dict], images: list[dict]) -> dict:
    golds = _sort_golds({v["gold"] for v in variants})
    carats = sorted({v["carat"] for v in variants})

    weights: dict[str, dict[str, float]] = {}
    manual_prices: dict[str, dict[str, float]] = {}
    for variant in variants:
        gold = variant["gold"]
        carat = variant["carat"]
        weights.setdefault(gold, {})[carat] = float(variant["weight_chin"])
        if variant.get("manual_price_twd") is not None:
            manual_prices.setdefault(gold, {})[carat] = float(variant["manual_price_twd"])

    images_by_color: dict[str, list[str]] = {}
    for image in images:
        images_by_color.setdefault(image["color"], []).append(resolve_product_image_url(image["file_path"]))

    return {
        "id": str(product["id"]),
        "nameZh": product["name_zh"],
        "nameEn": product["name_en"],
        "descriptionZh": product["description_zh"],
        "descriptionEn": product["description_en"],
        "defaultColor": product["default_color"],
        "golds": golds,
        "carats": carats,
        "colors": sorted(images_by_color.keys()),
        "images": images_by_color,
        "weights": weights,
        "manualPrices": manual_prices,
        "draft": not product["is_published"],
    }


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


def build_catalog_response(products: list[dict], variants_by_product: dict, images_by_product: dict) -> dict:
    if not products:
        return {"categories": {}, "categoryOrder": []}

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
    category_order = [c for c in CATEGORY_DISPLAY_ORDER if c in present]
    category_order.extend(c for c in present if c not in CATEGORY_DISPLAY_ORDER)
    return {"categories": categories, "categoryOrder": category_order}


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
