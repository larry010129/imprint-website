"""Admin product validation and persistence helpers."""

from __future__ import annotations

import re
from datetime import datetime, timezone

VALID_CATEGORIES = {"pendant", "ring", "earring", "bracelet", "chain"}
VALID_CARATS = {"0.1", "0.2", "0.3", "0.5", "1.0"}
VALID_CARATS_CHAIN = {"3fen", "4fen"}
VALID_GOLDS = {"9k", "14k", "18k", "pt950", "s925"}
VALID_COLORS = {"white", "yellow", "rose"}
IMAGE_COLOR_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
PRODUCT_NAME_MAX = 150
PRODUCT_DESC_MAX = 2000

CATEGORY_LABELS = {
    "pendant": "項墜",
    "ring": "戒指",
    "earring": "耳環",
    "bracelet": "手鍊",
    "chain": "鏈條",
}


def valid_image_color(color: str) -> bool:
    if color in VALID_COLORS:
        return True
    return bool(IMAGE_COLOR_RE.match(color))


def validate_product_fields(body: dict | None) -> tuple[dict | None, str | None]:
    errors: list[str] = []
    cleaned: dict = {}
    body = body or {}

    category = str(body.get("category") or "").strip()
    if category not in VALID_CATEGORIES:
        errors.append("invalid category")
    else:
        cleaned["category"] = category

    name_zh = str(body.get("nameZh") or "").strip()
    if not name_zh:
        errors.append("nameZh is required")
    elif len(name_zh) > PRODUCT_NAME_MAX:
        errors.append(f"nameZh must be at most {PRODUCT_NAME_MAX} characters")
    else:
        cleaned["nameZh"] = name_zh

    name_en = str(body.get("nameEn") or "").strip()
    if len(name_en) > PRODUCT_NAME_MAX:
        errors.append(f"nameEn must be at most {PRODUCT_NAME_MAX} characters")
    cleaned["nameEn"] = name_en[:PRODUCT_NAME_MAX] or None

    desc_zh = str(body.get("descriptionZh") or "").strip()
    desc_en = str(body.get("descriptionEn") or "").strip()
    if len(desc_zh) > PRODUCT_DESC_MAX or len(desc_en) > PRODUCT_DESC_MAX:
        errors.append(f"description must be at most {PRODUCT_DESC_MAX} characters")
    cleaned["descriptionZh"] = desc_zh or None
    cleaned["descriptionEn"] = desc_en or None

    default_color = str(body.get("defaultColor") or "white").strip()
    if default_color not in VALID_COLORS:
        errors.append("invalid defaultColor")
    else:
        cleaned["defaultColor"] = default_color

    cleaned["isPublished"] = bool(body.get("isPublished"))

    valid_carats = VALID_CARATS_CHAIN if category == "chain" else VALID_CARATS
    variants: list[dict] = []
    seen_keys: set[str] = set()
    for variant in body.get("variants") or []:
        gold = str(variant.get("gold") or "").strip()
        carat = str(variant.get("carat") or "").strip()
        if gold not in VALID_GOLDS:
            errors.append(f"invalid variant metal: {gold or '(empty)'}")
            continue
        if carat not in valid_carats:
            errors.append(f"invalid variant carat: {carat or '(empty)'}")
            continue
        try:
            weight_chin = float(variant.get("weightChin"))
        except (TypeError, ValueError):
            errors.append(f"invalid weight for {gold}/{carat}")
            continue
        if weight_chin <= 0:
            errors.append(f"invalid weight for {gold}/{carat}")
            continue
        manual_price = None
        if variant.get("manualPriceTwd") not in (None, ""):
            try:
                manual_price = float(variant.get("manualPriceTwd"))
            except (TypeError, ValueError):
                errors.append(f"invalid manual price for {gold}/{carat}")
                continue
            if manual_price < 0:
                errors.append(f"invalid manual price for {gold}/{carat}")
                continue
        key = f"{gold}:{carat}"
        if key in seen_keys:
            errors.append(f"duplicate variant: {gold} / {carat}")
            continue
        seen_keys.add(key)
        variants.append(
            {"gold": gold, "carat": carat, "weightChin": weight_chin, "manualPriceTwd": manual_price}
        )

    if not variants:
        errors.append("at least one variant is required")
    cleaned["variants"] = variants

    images: list[dict] = []
    seen_colors: set[str] = set()
    for img in body.get("images") or []:
        if not img or not img.get("url"):
            continue
        color = str(img.get("color") or "").strip().lower()
        if not valid_image_color(color):
            errors.append(f"invalid image option: {color or '(empty)'}")
            continue
        if color in seen_colors:
            errors.append(f"duplicate image option: {color}")
            continue
        seen_colors.add(color)
        images.append({"color": color, "url": img["url"]})
    final_colors = {img["color"] for img in images}
    if not final_colors:
        errors.append("at least one product image is required")
    elif cleaned.get("defaultColor") and cleaned["defaultColor"] not in final_colors:
        errors.append("default color must have at least one image")
    cleaned["images"] = images

    if errors:
        return None, "; ".join(errors)
    return cleaned, None


def serialize_product_row(row: dict) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    if out.get("created_by_id") is not None:
        out["created_by_id"] = str(out["created_by_id"])
    return out


def save_product_children(cur, product_id: str, cleaned: dict) -> None:
    cur.execute("delete from product_variants where product_id = %s", (product_id,))
    for variant in cleaned["variants"]:
        cur.execute(
            """
            insert into product_variants (product_id, gold, carat, weight_chin, manual_price_twd)
            values (%s, %s, %s, %s, %s)
            """,
            (
                product_id,
                variant["gold"],
                variant["carat"],
                variant["weightChin"],
                variant["manualPriceTwd"],
            ),
        )

    cur.execute("delete from product_images where product_id = %s", (product_id,))
    for sort_order, image in enumerate(cleaned["images"]):
        cur.execute(
            """
            insert into product_images (product_id, color, file_path, sort_order)
            values (%s, %s, %s, %s)
            """,
            (product_id, image["color"], image["url"], sort_order),
        )


def publish_readiness(cur, product: dict) -> tuple[bool, str | None]:
    product_id = product["id"]
    cur.execute("select count(*) as c from product_variants where product_id = %s", (product_id,))
    if int(cur.fetchone()["c"]) == 0:
        return False, "請先新增至少一個款式選項"
    cur.execute("select count(*) as c from product_images where product_id = %s", (product_id,))
    if int(cur.fetchone()["c"]) == 0:
        return False, "請先上傳至少一張商品照片"
    cur.execute(
        "select 1 from product_images where product_id = %s and color = %s limit 1",
        (product_id, product["default_color"]),
    )
    if not cur.fetchone():
        return False, "預設顏色必須至少有一張商品照片"
    return True, None


def first_published_at_value(existing: dict | None, is_published: bool) -> datetime | None:
    if existing and existing.get("first_published_at"):
        return existing["first_published_at"]
    if is_published:
        return datetime.now(timezone.utc)
    return None
