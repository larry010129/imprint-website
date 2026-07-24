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


def validate_product_fields(body: dict | None, *, valid_categories: set[str] | None = None) -> tuple[dict | None, str | None]:
    """A draft (isPublished=False) only needs a valid category — name, variants,
    and images can all be filled in later. Publishing still requires all of them."""
    errors: list[str] = []
    cleaned: dict = {}
    body = body or {}
    allowed_categories = valid_categories or VALID_CATEGORIES

    is_published = bool(body.get("isPublished"))
    cleaned["isPublished"] = is_published

    category = str(body.get("category") or "").strip()
    if category not in allowed_categories:
        errors.append("invalid category")
    else:
        cleaned["category"] = category

    name_zh = str(body.get("nameZh") or "").strip()
    if not name_zh:
        if is_published:
            errors.append("nameZh is required")
        cleaned["nameZh"] = "未命名商品（草稿）"
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

    if not variants and is_published:
        errors.append("at least one variant is required")
    cleaned["variants"] = variants

    images: list[dict] = []
    for img in body.get("images") or []:
        if not img or not img.get("url"):
            continue
        color = str(img.get("color") or "").strip().lower()
        if not valid_image_color(color):
            errors.append(f"invalid image option: {color or '(empty)'}")
            continue
        images.append({"color": color, "url": img["url"]})
    final_colors = {img["color"] for img in images}
    if not final_colors:
        if is_published:
            errors.append("at least one product image is required")
    elif is_published and cleaned.get("defaultColor") and cleaned["defaultColor"] not in final_colors:
        errors.append("default color must have at least one image")
    cleaned["images"] = images

    if errors:
        return None, _format_product_errors(errors)
    return cleaned, None


def _format_product_errors(errors: list[str]) -> str:
    zh = {
        "invalid category": "品項無效",
        "nameZh is required": "請填寫中文名稱",
        "invalid defaultColor": "預設顏色無效",
        "at least one variant is required": "請至少新增一個款式選項（金屬／克拉／蠟重）",
        "at least one product image is required": "請至少上傳一張商品照片",
        "default color must have at least one image": "預設顏色必須至少有一張商品照片",
    }
    parts: list[str] = []
    for err in errors:
        if err in zh:
            parts.append(zh[err])
            continue
        if err.startswith("nameZh must be at most"):
            parts.append("中文名稱過長")
            continue
        if err.startswith("nameEn must be at most"):
            parts.append("英文名稱過長")
            continue
        if err.startswith("description must be at most"):
            parts.append("描述文字過長")
            continue
        if err.startswith("invalid variant metal"):
            parts.append("款式選項：金屬成色無效")
            continue
        if err.startswith("invalid variant carat"):
            parts.append("款式選項：克拉／分數無效")
            continue
        if err.startswith("invalid weight for"):
            parts.append("款式選項：蠟重無效")
            continue
        if err.startswith("invalid manual price for"):
            parts.append("款式選項：手動定價無效")
            continue
        if err.startswith("duplicate variant"):
            parts.append("款式選項重複：" + err.split(": ", 1)[-1])
            continue
        if err.startswith("invalid image option"):
            parts.append("圖片選項代碼無效")
            continue
        parts.append(err)
    return "；".join(parts)


def serialize_product_row(row: dict) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    if out.get("created_by_id") is not None:
        out["created_by_id"] = str(out["created_by_id"])
    for key, value in out.items():
        if isinstance(value, datetime):
            out[key] = value.isoformat()
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
