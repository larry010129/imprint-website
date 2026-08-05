"""Admin product validation and persistence helpers."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import unquote

from psycopg.types.json import Jsonb

from app.chain_catalog import (
    DEFAULT_NECKLACE_TYPE,
    VALID_NECKLACE_TYPES,
    necklace_type_length_weights,
)
from app.image_urls import (
    _is_raster_url,
    resolve_product_image_url,
    static_url_exists,
)
from app.pricing_overrides import canonical_carat
from app.storage import (
    delete_by_url,
    is_pending_product_object_key,
    is_supabase_storage_url,
    metal_color_from_slot,
    object_path_from_public_url,
    product_folder_from_object_key,
    product_folder_segment,
    promote_pending_product_url,
    relocate_product_object_url,
)

VALID_CATEGORIES = {"pendant", "ring", "earring", "bracelet", "chain"}

VALID_CARATS = {
    "0.1", "0.2", "0.3", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0",
    "1.5", "2.0", "3.0",
}
VALID_CARATS_CHAIN = {"1.0mm", "1.5mm", "2.0mm", "2.5mm", "3.0mm"}
VALID_CHAIN_LENGTHS_CM = {36, 41, 46, 51, 61, 76, 80}
VALID_GOLDS = {"9k", "14k", "18k", "pt950", "s925"}
VALID_COLORS = {"white", "yellow", "rose"}
IMAGE_COLOR_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
PRODUCT_NAME_MAX = 150
PRODUCT_DESC_MAX = 2000
_BROWSER_LOCAL_URL_RE = re.compile(r"^(?:blob:|data:)", re.I)
_DEAD_CATALOG_PLACEHOLDER_RE = re.compile(
    r"(?:\.svg(?:$|\?))|/images/shop/styles/",
    re.I,
)
# Letter-SKU stock renders under shop-product/ — never treat as admin-uploaded photos.
_AUTO_STOCK_PRODUCT_IMAGE_RE = re.compile(
    r"(?:^|/|\\)(?:static/)?images/shop-product(?:/|\\|$)",
    re.I,
)

CATEGORY_LABELS = {
    "pendant": "項墜",
    "ring": "戒指",
    "earring": "耳環",
    "bracelet": "手鍊",
    "chain": "鏈條",
}

# Idempotent schema ensure — migrations may lag local/prod DBs.
_PRODUCT_SELL_MODE_COLUMNS = (
    ("allows_pendant_only", "boolean not null default true"),
    ("allows_with_chain", "boolean not null default true"),
    ("allows_fancy_shapes", "boolean not null default true"),
)


def ensure_product_sell_mode_columns(cur) -> None:
    """Add pendant sell-mode columns if missing (see migration 20260730140000)."""
    for name, col_type in _PRODUCT_SELL_MODE_COLUMNS:
        cur.execute(f"alter table products add column if not exists {name} {col_type}")


def ensure_product_length_weights_column(cur) -> None:
    """Add chain length wax table column if missing (migration 20260731120000)."""
    cur.execute("alter table products add column if not exists length_weights jsonb")


def ensure_product_chain_type_column(cur) -> None:
    """Add necklace pricing type column if missing (migration 20260731130000)."""
    cur.execute("alter table products add column if not exists chain_type text")


def ensure_product_side_stone_total_column(cur) -> None:
    """Add fixed 配鑽價錢 total column if missing (migration 20260804160000)."""
    cur.execute(
        "alter table product_variants "
        "add column if not exists side_stone_total_twd numeric"
    )


def as_jsonb(value: Any) -> Jsonb | None:
    """Wrap dict/list for jsonb params. Bare dict → ProgrammingError in psycopg3."""
    if value is None:
        return None
    if isinstance(value, Jsonb):
        return value
    if isinstance(value, (dict, list)):
        return Jsonb(value)
    return None


def _parse_length_weights(raw: Any, *, errors: list[str]) -> dict[str, dict[str, float]] | None:
    if raw in (None, "", {}):
        return None
    if not isinstance(raw, dict):
        errors.append("invalid chain length weights")
        return None
    cleaned: dict[str, dict[str, float]] = {}
    for thickness, lengths in raw.items():
        thick = str(thickness or "").strip()
        if thick not in VALID_CARATS_CHAIN:
            errors.append(f"invalid chain thickness in length weights: {thick or '(empty)'}")
            continue
        if not isinstance(lengths, dict):
            errors.append(f"invalid length map for {thick}")
            continue
        row: dict[str, float] = {}
        for length_key, wax_val in lengths.items():
            try:
                length_cm = int(length_key)
                wax = float(wax_val)
            except (TypeError, ValueError):
                errors.append(f"invalid length/wax for {thick}")
                continue
            if length_cm not in VALID_CHAIN_LENGTHS_CM:
                errors.append(f"unsupported chain length cm: {length_cm}")
                continue
            if wax <= 0:
                errors.append(f"invalid wax weight for {thick} {length_cm}cm")
                continue
            row[str(length_cm)] = wax
        if row:
            cleaned[thick] = row
    return cleaned or None


def _sync_chain_variant_reference_weights(
    variants: list[dict], length_weights: dict[str, dict[str, float]] | None
) -> None:
    """Keep variant weight_chin aligned with 46cm wax when length table is present."""
    if not length_weights:
        return
    for variant in variants:
        ref = length_weights.get(variant["carat"], {}).get("46")
        if ref is not None:
            variant["weightChin"] = ref


def valid_image_color(color: str) -> bool:
    if color in VALID_COLORS:
        return True
    return bool(IMAGE_COLOR_RE.match(color))


def is_browser_local_image_url(url: str | None) -> bool:
    """blob:/data: URLs are tab-local and must never be persisted to SQL."""
    return bool(url and _BROWSER_LOCAL_URL_RE.match(str(url).strip()))


def is_dead_catalog_placeholder(url: str | None) -> bool:
    """Seed SVG /styles paths 404 — not real uploads."""
    if not url:
        return False
    path = unquote(str(url).strip().split("?", 1)[0])
    return bool(_DEAD_CATALOG_PLACEHOLDER_RE.search(path))


def is_auto_stock_product_image(url: str | None) -> bool:
    """Bundled letter-SKU PNGs under shop-product/ — never admin product photos."""
    if not url:
        return False
    path = unquote(str(url).strip().split("?", 1)[0]).replace("\\", "/")
    return bool(_AUTO_STOCK_PRODUCT_IMAGE_RE.search(path))


def is_pending_product_image(url: str | None) -> bool:
    """Autosave temp Storage paths — never serve in shop catalog or persist on publish."""
    if not url:
        return False
    raw = str(url).strip()
    if not raw:
        return False
    resolved = resolve_product_image_url(raw) or raw
    path = unquote(resolved.split("?", 1)[0]).replace("\\", "/")
    if "/_pending/" in path or path.endswith("/_pending"):
        return True
    if resolved.startswith(("http://", "https://")):
        obj = object_path_from_public_url(resolved)
        return bool(obj and is_pending_product_object_key(obj))
    return False


def normalize_product_image_url(url: str | None, color: str | None = None) -> str | None:
    """Return a persistable server URL, or None if the value must be dropped.

    ``_pending`` Storage paths are allowed here so admin save/autosave can persist
    draft uploads; ``save_product_children`` promotes them to the final folder.
    Shop catalog still filters pending via ``is_pending_product_image``.
    """
    del color  # slot color is metadata only; never infer shop-product letter PNGs.
    raw = str(url or "").strip()
    if not raw or is_browser_local_image_url(raw):
        return None
    resolved = resolve_product_image_url(raw) or raw
    if (
        is_dead_catalog_placeholder(resolved)
        or is_dead_catalog_placeholder(raw)
        or is_auto_stock_product_image(resolved)
        or is_auto_stock_product_image(raw)
    ):
        return None
    if not _is_raster_url(resolved):
        return None
    if resolved.startswith(("http://", "https://")):
        return resolved if is_supabase_storage_url(resolved) else None
    if resolved.startswith("/static/") and not static_url_exists(resolved):
        return None
    return resolved


def purge_auto_stock_product_images(cur) -> int:
    """Delete invented shop-product letter rows from product_images. Returns rows removed."""
    cur.execute(
        """
        delete from product_images
        where file_path ilike '%/shop-product/%'
           or file_path ilike '%\\shop-product\\%'
           or file_path ilike 'images/shop-product/%'
        """
    )
    return int(cur.rowcount or 0)


def image_covers_default_color(image_color: str, default_color: str) -> bool:
    """defaultColor is metal-only; slots may be metal, metal-diamond, or metal-diamond-chain."""
    key = (image_color or "").strip().lower()
    default = (default_color or "").strip().lower()
    if not key or default not in VALID_COLORS:
        return False
    if key == default:
        return True
    return key.startswith(default + "-")


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

    name_en = str(body.get("nameEn") or body.get("name_en") or "").strip()
    if not name_en:
        errors.append("nameEn is required")
        cleaned["nameEn"] = None
    elif len(name_en) > PRODUCT_NAME_MAX:
        errors.append(f"nameEn must be at most {PRODUCT_NAME_MAX} characters")
        cleaned["nameEn"] = name_en[:PRODUCT_NAME_MAX]
    else:
        cleaned["nameEn"] = name_en

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

    cleaned["allowsEngraving"] = bool(body.get("allowsEngraving", True))
    cleaned["allowsFancyShapes"] = bool(body.get("allowsFancyShapes", True))

    # Pendant sell modes (不含鍊賣 / 含鍊賣). Non-pendant rows keep both true.
    if category == "pendant":
        allows_pendant_only = bool(body.get("allowsPendantOnly", True))
        allows_with_chain = bool(body.get("allowsWithChain", True))
        if not allows_pendant_only and not allows_with_chain:
            errors.append("pendant must select 不含鍊賣 or 含鍊賣")
        cleaned["allowsPendantOnly"] = allows_pendant_only
        cleaned["allowsWithChain"] = allows_with_chain
    else:
        cleaned["allowsPendantOnly"] = True
        cleaned["allowsWithChain"] = True

    valid_carats = VALID_CARATS_CHAIN if category == "chain" else VALID_CARATS
    variants: list[dict] = []
    seen_keys: set[str] = set()
    for variant in body.get("variants") or []:
        gold = str(variant.get("gold") or "").strip()
        carat = str(variant.get("carat") or "").strip()
        # Align padded keys (0.10) with shop/catalog canonical form (0.1).
        if category != "chain":
            carat = canonical_carat(carat) or carat
        if gold not in VALID_GOLDS:
            errors.append(f"invalid variant metal: {gold or '(empty)'}")
            continue
        if carat not in valid_carats:
            errors.append(f"invalid variant carat: {carat or '(empty)'}")
            continue
        # Chain wax lives in length_weights grid; variant weightChin is synced from 46cm.
        raw_weight = variant.get("weightChin")
        if category == "chain" and raw_weight in (None, ""):
            weight_chin = 0.0
        else:
            try:
                weight_chin = float(raw_weight)
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
        side_stone_price = None
        if variant.get("sideStonePriceTwd") not in (None, ""):
            try:
                side_stone_price = float(variant.get("sideStonePriceTwd"))
            except (TypeError, ValueError):
                errors.append(f"invalid side stone price for {gold}/{carat}")
                continue
            if side_stone_price < 0:
                errors.append(f"invalid side stone price for {gold}/{carat}")
                continue
        side_stone_carat = None
        if variant.get("sideStoneCarat") not in (None, ""):
            try:
                side_stone_carat = float(variant.get("sideStoneCarat"))
            except (TypeError, ValueError):
                errors.append(f"invalid side stone carat for {gold}/{carat}")
                continue
            if side_stone_carat < 0:
                errors.append(f"invalid side stone carat for {gold}/{carat}")
                continue
        side_stone_total = None
        if variant.get("sideStoneTotalTwd") not in (None, ""):
            try:
                side_stone_total = float(variant.get("sideStoneTotalTwd"))
            except (TypeError, ValueError):
                errors.append(f"invalid side stone total for {gold}/{carat}")
                continue
            if side_stone_total < 0:
                errors.append(f"invalid side stone total for {gold}/{carat}")
                continue
        key = f"{gold}:{carat}"
        if key in seen_keys:
            errors.append(f"duplicate variant: {gold} / {carat}")
            continue
        seen_keys.add(key)
        variants.append(
            {
                "gold": gold,
                "carat": carat,
                "weightChin": weight_chin,
                "manualPriceTwd": manual_price,
                "sideStonePriceTwd": side_stone_price,
                "sideStoneCarat": side_stone_carat,
                "sideStoneTotalTwd": side_stone_total,
            }
        )

    if not variants and is_published:
        errors.append("at least one variant is required")
    cleaned["variants"] = variants

    chain_type = None
    length_weights = None
    if category == "chain":
        raw_type = str(body.get("chainType") or body.get("chain_type") or "").strip()
        if raw_type:
            if raw_type not in VALID_NECKLACE_TYPES:
                errors.append(f"invalid chain type: {raw_type}")
            else:
                chain_type = raw_type
        elif is_published:
            chain_type = DEFAULT_NECKLACE_TYPE
        cleaned["chainType"] = chain_type

        length_weights = _parse_length_weights(body.get("lengthWeights"), errors=errors)
        # Empty admin grid → Excel/type standard table (抖圓鏈 etc.). No per-SKU edit needed.
        if not length_weights and chain_type:
            length_weights = necklace_type_length_weights(chain_type)
        _sync_chain_variant_reference_weights(variants, length_weights)
        if is_published and variants:
            if not chain_type:
                errors.append("chain type is required")
            for variant in variants:
                if float(variant.get("weightChin") or 0) <= 0:
                    errors.append(
                        f"chain thickness missing 46cm wax in 長度蠟重: {variant['carat']}"
                    )
    else:
        cleaned["chainType"] = None
    cleaned["lengthWeights"] = length_weights

    images: list[dict] = []
    for img in body.get("images") or []:
        if not img or not img.get("url"):
            continue
        color = str(img.get("color") or "").strip().lower()
        if not valid_image_color(color):
            errors.append(f"invalid image option: {color or '(empty)'}")
            continue
        url = normalize_product_image_url(img.get("url"), color)
        if not url:
            # Drop blob:/data:/dead SVG quietly; publish gate still requires real images.
            continue
        images.append({"color": color, "url": url})
    final_colors = {img["color"] for img in images}
    if not final_colors:
        if is_published:
            errors.append("at least one product image is required")
    elif is_published and cleaned.get("defaultColor"):
        default = cleaned["defaultColor"]
        if not any(image_covers_default_color(c, default) for c in final_colors):
            errors.append("default color must have at least one image")
    cleaned["images"] = images

    if errors:
        return None, _format_product_errors(errors)
    return cleaned, None


def _format_product_errors(errors: list[str]) -> str:
    zh = {
        "invalid category": "品項無效",
        "nameZh is required": "請填寫中文名稱",
        "nameEn is required": "請填寫英文名稱（資料用）",
        "invalid defaultColor": "預設顏色無效",
        "pendant must select 不含鍊賣 or 含鍊賣": "項墜請選擇「不含鍊賣」或「含鍊賣」",
        "pendant must allow 不含鍊賣 and/or 含鍊賣": "項墜請選擇「不含鍊賣」或「含鍊賣」",
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
            parts.append("款式選項：克拉／厚度無效")
            continue
        if err.startswith("invalid weight for"):
            parts.append("款式選項：蠟重無效")
            continue
        if err.startswith("invalid manual price for"):
            parts.append("款式選項：手動定價無效")
            continue
        if err.startswith("invalid side stone price for"):
            parts.append("款式選項：一克拉價格無效")
            continue
        if err.startswith("invalid side stone carat for"):
            parts.append("款式選項：配鑽克拉無效")
            continue
        if err.startswith("invalid side stone total for"):
            parts.append("款式選項：配鑽價錢無效")
            continue
        if err.startswith("duplicate variant"):
            parts.append("款式選項重複：" + err.split(": ", 1)[-1])
            continue
        if err.startswith("invalid chain type"):
            parts.append("項鍊類型無效")
            continue
        if err == "chain type is required":
            parts.append("請選擇項鍊類型")
            continue
        if err.startswith("invalid chain thickness in length weights"):
            parts.append("長度蠟重：厚度無效")
            continue
        if err.startswith("invalid length map for"):
            parts.append("長度蠟重：長度資料格式無效")
            continue
        if err.startswith("invalid length/wax for"):
            parts.append("長度蠟重：長度或蠟重無效")
            continue
        if err.startswith("unsupported chain length cm"):
            parts.append("長度蠟重：不支援的長度（cm）")
            continue
        if err.startswith("invalid wax weight for"):
            parts.append("長度蠟重：蠟重無效")
            continue
        if err.startswith("chain length weights required for thickness"):
            parts.append("請填寫鏈條各厚度的長度蠟重：" + err.split(": ", 1)[-1])
            continue
        if err.startswith("chain thickness missing 46cm wax in 長度蠟重"):
            parts.append("長度蠟重：請填寫該厚度的 46cm 蠟重（或重填標準表）：" + err.split(": ", 1)[-1])
            continue
        if err.startswith("invalid chain length weights"):
            parts.append("長度蠟重資料無效")
            continue
        if err.startswith("invalid image option"):
            parts.append("圖片選項代碼無效")
            continue
        if err.startswith("image URL must be a server path"):
            parts.append("圖片必須經伺服器上傳後儲存，不可使用瀏覽器暫存網址")
            continue
        parts.append(err)
    return "；".join(parts)


def append_product_image(cur, product_id: str, color: str, file_path: str) -> dict | None:
    """Insert one image row for an existing product (upload-time SQL persist)."""
    color_key = str(color or "").strip().lower()
    path = normalize_product_image_url(file_path, color_key)
    if not path or not valid_image_color(color_key):
        return None
    cur.execute("select id from products where id = %s", (product_id,))
    if not cur.fetchone():
        return None
    cur.execute(
        "select coalesce(max(sort_order), -1) + 1 as next_sort from product_images where product_id = %s",
        (product_id,),
    )
    next_sort = int((cur.fetchone() or {}).get("next_sort") or 0)
    cur.execute(
        """
        insert into product_images (product_id, color, file_path, sort_order)
        values (%s, %s, %s, %s)
        returning id, product_id, color, file_path, sort_order
        """,
        (product_id, color_key, path, next_sort),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def serialize_product_row(row: dict) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    if out.get("created_by_id") is not None:
        out["created_by_id"] = str(out["created_by_id"])
    lw = out.pop("length_weights", None)
    if lw is not None:
        out["lengthWeights"] = lw
    ct = out.pop("chain_type", None)
    if ct is not None:
        out["chainType"] = ct
    for key, value in out.items():
        if isinstance(value, datetime):
            out[key] = value.isoformat()
    return out


def _is_products_storage_url(url: str | None) -> bool:
    """True when URL is a Supabase Storage object under products/."""
    if not url or not is_supabase_storage_url(url):
        return False
    obj = object_path_from_public_url(url)
    return bool(obj and obj.startswith("products/"))




def resolve_product_folder(
    cur,
    product_id: str,
    name_en: str | None,
    name_zh: str | None = None,
) -> str:
    """Storage folder: name_en slug, else short id (name_zh unused)."""
    pid = str(product_id).strip()
    mine = product_folder_segment(name_en, pid, name_zh=name_zh, collide=False)
    cur.execute("select id, name_en, name_zh from products where id <> %s", (pid,))
    collide = False
    for row in cur.fetchall() or []:
        other = product_folder_segment(
            row.get("name_en"),
            str(row["id"]),
            name_zh=row.get("name_zh"),
            collide=False,
        )
        if other == mine:
            collide = True
            break
    return product_folder_segment(
        name_en, pid, name_zh=name_zh, collide=collide
    )


def _url_shared_with_other_products(cur, url: str, product_id: str) -> bool:
    cur.execute(
        """
        select 1 from product_images
        where file_path = %s and product_id <> %s
        limit 1
        """,
        (url, product_id),
    )
    return cur.fetchone() is not None


def align_product_images_to_folder(
    cur,
    product_id: str,
    folder: str,
    images: list[dict],
    *,
    category: str | None = None,
) -> None:
    """Move/copy nested product objects into `folder` (rename / legacy id paths)."""
    if not folder:
        return
    for image in images:
        url = str(image.get("url") or "").strip()
        if not url:
            continue
        obj = object_path_from_public_url(url)
        current = product_folder_from_object_key(obj) if obj else None
        if not current or current == folder:
            continue
        shared = _url_shared_with_other_products(cur, url, product_id)
        new_url = relocate_product_object_url(
            url, current, folder, category=category, shared=shared
        )
        if new_url != url:
            image["url"] = new_url


def delete_product_image_urls_if_unreferenced(cur, urls) -> int:
    """Delete Storage objects when no product_images row still references them.

    Only Supabase URLs under products/. Dedupes. Best-effort: Storage failures
    do not raise. Returns how many delete_by_url calls reported success.
    """
    candidates: list[str] = []
    seen: set[str] = set()
    for raw in urls or []:
        url = str(raw or "").strip()
        if not url or url in seen or not _is_products_storage_url(url):
            continue
        seen.add(url)
        candidates.append(url)

    deleted = 0
    for url in candidates:
        cur.execute(
            "select 1 from product_images where file_path = %s limit 1",
            (url,),
        )
        if cur.fetchone():
            continue
        try:
            if delete_by_url(url):
                deleted += 1
        except Exception:
            continue
    return deleted


def save_product_children(cur, product_id: str, cleaned: dict) -> None:
    ensure_product_side_stone_total_column(cur)
    cur.execute("delete from product_variants where product_id = %s", (product_id,))
    for variant in cleaned["variants"]:
        cur.execute(
            """
            insert into product_variants (
                product_id, gold, carat, weight_chin, manual_price_twd,
                side_stone_price_twd, side_stone_carat, side_stone_total_twd
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                product_id,
                variant["gold"],
                variant["carat"],
                variant["weightChin"],
                variant["manualPriceTwd"],
                variant.get("sideStonePriceTwd"),
                variant.get("sideStoneCarat"),
                variant.get("sideStoneTotalTwd"),
            ),
        )

    cur.execute(
        "update products set length_weights = %s, chain_type = %s where id = %s",
        (
            as_jsonb(cleaned.get("lengthWeights")),
            cleaned.get("chainType"),
            product_id,
        ),
    )

    folder = resolve_product_folder(
        cur,
        product_id,
        cleaned.get("nameEn"),
        cleaned.get("nameZh"),
    )
    category = cleaned.get("category")
    align_product_images_to_folder(
        cur, product_id, folder, cleaned.get("images") or [], category=category
    )

    cur.execute(
        "select file_path from product_images where product_id = %s",
        (product_id,),
    )
    previous_urls = {
        str(row["file_path"]).strip()
        for row in cur.fetchall()
        if row.get("file_path")
    }

    cur.execute("delete from product_images where product_id = %s", (product_id,))
    for sort_order, image in enumerate(cleaned["images"]):
        url = image["url"]
        metal = metal_color_from_slot(image.get("color"))
        url = promote_pending_product_url(url, folder, metal, category=category)
        image["url"] = url
        cur.execute(
            """
            insert into product_images (product_id, color, file_path, sort_order)
            values (%s, %s, %s, %s)
            """,
            (product_id, image["color"], url, sort_order),
        )

    new_urls = {str(img["url"]).strip() for img in cleaned["images"] if img.get("url")}
    delete_product_image_urls_if_unreferenced(cur, previous_urls - new_urls)


def publish_readiness(cur, product: dict) -> tuple[bool, str | None]:
    product_id = product["id"]
    cur.execute("select count(*) as c from product_variants where product_id = %s", (product_id,))
    if int(cur.fetchone()["c"]) == 0:
        return False, "請先新增至少一個款式選項"
    cur.execute("select count(*) as c from product_images where product_id = %s", (product_id,))
    if int(cur.fetchone()["c"]) == 0:
        return False, "請先上傳至少一張商品照片"
    cur.execute(
        "select color from product_images where product_id = %s",
        (product_id,),
    )
    default = product["default_color"]
    if not any(image_covers_default_color(row["color"], default) for row in cur.fetchall()):
        return False, "預設顏色必須至少有一張商品照片"
    return True, None


def first_published_at_value(existing: dict | None, is_published: bool) -> datetime | None:
    if existing and existing.get("first_published_at"):
        return existing["first_published_at"]
    if is_published:
        return datetime.now(timezone.utc)
    return None
