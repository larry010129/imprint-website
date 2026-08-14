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
from app.diamond_shapes import is_allowed_shape_id
from app.memorial_diamonds import (
    VALID_DIAMOND_COLORS,
    normalize_style_key,
    style_key_from_name_en,
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

VALID_CATEGORIES = {"diamond", "pendant", "ring", "earring", "bracelet", "chain"}

# Positive integer floor only — no hard upper ceiling on ring sizes.
RING_SIZE_MIN = 1
# Soft UX default when maxSize omitted (not a validation ceiling).
RING_SIZE_DEFAULT_MAX = 18
RING_SIZE_MAX = RING_SIZE_DEFAULT_MAX  # alias: omitted-max default only

VALID_CARATS = {
    "0.1", "0.2", "0.3", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0",
    "1.5", "2.0", "3.0",
}
CHAIN_THICKNESS_RE = re.compile(r"^(?:0|[1-9]\d{0,2})(?:\.\d{1,4})?mm$", re.I)


def _is_valid_chain_thickness(value: str) -> bool:
    if not CHAIN_THICKNESS_RE.fullmatch(value):
        return False
    try:
        return float(value[:-2]) > 0
    except ValueError:
        return False
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
    "diamond": "紀念鑽石",
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


def ensure_product_ear_clasp_price_column(cur) -> None:
    """Add earring-only 耳扣價錢 column if missing (migration 20260806120000)."""
    cur.execute(
        "alter table product_variants "
        "add column if not exists ear_clasp_price_twd numeric"
    )


# Alias kept for older call sites that used ear_cuff naming.
ensure_product_ear_cuff_price_column = ensure_product_ear_clasp_price_column


def ensure_product_variant_addon_price_column(cur) -> None:
    """Add per-row 品項加價 column if missing (migration 20260806150000)."""
    cur.execute(
        "alter table product_variants "
        "add column if not exists addon_price_twd numeric"
    )


def ensure_product_style_key_column(cur) -> None:
    """Add products.style_key if missing (memorial diamond shop linking)."""
    from app.memorial_diamonds import ensure_product_style_key_column as _ensure

    _ensure(cur)


def ensure_product_ring_size_config_column(cur) -> None:
    """Add products.ring_size_config jsonb if missing (migration 20260806180000)."""
    cur.execute("alter table products add column if not exists ring_size_config jsonb")


def ensure_product_images_previous_column(cur) -> None:
    """Add product_images.previous_file_path if missing (migration 20260809140000)."""
    cur.execute(
        "alter table product_images "
        "add column if not exists previous_file_path text"
    )
    ensure_product_images_updated_at_column(cur)


def ensure_product_images_updated_at_column(cur) -> None:
    """Add product_images.updated_at if missing (migration 20260812140000)."""
    cur.execute(
        "alter table product_images "
        "add column if not exists updated_at timestamptz not null default now()"
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


def _parse_ring_size_int(raw: Any) -> int | None:
    """Parse positive integer ring size (>= 1); None if empty/invalid."""
    if raw in (None, ""):
        return None
    try:
        size = int(round(float(raw)))
    except (TypeError, ValueError):
        return None
    if size < RING_SIZE_MIN:
        return None
    return size


def _parse_ring_size_config(raw: Any, *, errors: list[str]) -> dict[str, Any] | None:
    """Normalize ringSizeConfig: minSize, maxSize, chargeAfter, pricePerSizeTwd."""
    if raw in (None, "", {}):
        return None
    if not isinstance(raw, dict):
        errors.append("invalid ring size config")
        return None

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

    has_any = any(
        v not in (None, "") for v in (min_raw, max_raw, price_raw, charge_raw)
    )
    if not has_any:
        return None

    min_size: int | None = None
    if min_raw not in (None, ""):
        min_size = _parse_ring_size_int(min_raw)
        if min_size is None:
            errors.append("invalid ring min size")
    elif max_raw not in (None, "") or price_raw not in (None, "") or charge_raw not in (
        None,
        "",
    ):
        errors.append("invalid ring min size")

    max_size: int | None = None
    if max_raw not in (None, ""):
        max_size = _parse_ring_size_int(max_raw)
        if max_size is None:
            errors.append("invalid ring max size")
    elif min_size is not None:
        max_size = RING_SIZE_DEFAULT_MAX

    if min_size is not None and max_size is not None and min_size > max_size:
        errors.append("ring min size exceeds max size")

    charge_after: int | None = None
    if charge_raw not in (None, ""):
        charge_after = _parse_ring_size_int(charge_raw)
        if charge_after is None:
            errors.append("invalid ring charge after")
        elif min_size is not None and max_size is not None:
            if charge_after < min_size or charge_after > max_size:
                errors.append("ring charge after out of range")
    elif min_size is not None:
        charge_after = min_size

    price = 0.0
    if price_raw not in (None, ""):
        try:
            price = float(price_raw)
        except (TypeError, ValueError):
            errors.append("invalid ring price per size")
            price = 0.0
        else:
            if price < 0:
                errors.append("invalid ring price per size")

    if min_size is None:
        return None
    resolved_max = max_size if max_size is not None else RING_SIZE_DEFAULT_MAX
    resolved_charge = charge_after if charge_after is not None else min_size
    return {
        "minSize": min_size,
        "maxSize": resolved_max,
        "chargeAfter": resolved_charge,
        "pricePerSizeTwd": price,
        "startSize": min_size,
    }


def should_skip_published_autosave_write(autosave: Any, is_published: Any) -> bool:
    """Autosave on a live row must not write a draft-validated payload."""
    return bool(autosave) and bool(is_published)


def _parse_length_weights(raw: Any, *, errors: list[str]) -> dict[str, dict[str, float]] | None:
    # empty / {} / all-zero → unset (NULL). Non-empty table is exclusive override.
    if raw in (None, ""):
        return None
    if not isinstance(raw, dict):
        errors.append("invalid chain length weights")
        return None
    if raw == {}:
        return None
    cleaned: dict[str, dict[str, float]] = {}
    for thickness, lengths in raw.items():
        thick = str(thickness or "").strip()
        if not _is_valid_chain_thickness(thick):
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


def image_covers_default_color(
    image_color: str,
    default_color: str,
    *,
    category: str | None = None,
) -> bool:
    """defaultColor is metal-only for jewelry; diamond uses diamond-color keys."""
    key = (image_color or "").strip().lower()
    default = (default_color or "").strip().lower()
    if not key or not default:
        return False
    if category == "diamond":
        # Product = gem color; image slots are shapes (round, oval, asscher, …).
        if default not in VALID_DIAMOND_COLORS:
            return False
        return is_allowed_shape_id(key)
    if default not in VALID_COLORS:
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
    if category == "diamond":
        if default_color not in VALID_DIAMOND_COLORS:
            errors.append("invalid defaultColor")
        else:
            cleaned["defaultColor"] = default_color
    elif default_color not in VALID_COLORS:
        errors.append("invalid defaultColor")
    else:
        cleaned["defaultColor"] = default_color

    # Memorial diamond: no metal engraving UI; fancy shapes stay on (shop calculator).
    if category == "diamond":
        cleaned["allowsEngraving"] = False
        cleaned["allowsFancyShapes"] = bool(body.get("allowsFancyShapes", True))
    else:
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

    raw_style_key = body.get("styleKey") if body.get("styleKey") is not None else body.get("style_key")
    style_key = normalize_style_key(str(raw_style_key) if raw_style_key not in (None, "") else "")
    if category == "diamond":
        if raw_style_key not in (None, "") and style_key is None:
            errors.append("invalid styleKey")
        elif style_key is None:
            style_key = style_key_from_name_en(cleaned.get("nameEn"))
        cleaned["styleKey"] = style_key
    else:
        cleaned["styleKey"] = None

    # Memorial diamond: name + shape images only — no metal/price variants.
    # product_images.color stores shape id (round/marquise/…); product is the gem color.
    if category == "diamond":
        cleaned["variants"] = []
        cleaned["chainType"] = None
        cleaned["lengthWeights"] = None
        cleaned["ringSizeConfig"] = None
        images: list[dict] = []
        for img in body.get("images") or []:
            if not img or not img.get("url"):
                continue
            shape = str(img.get("color") or "").strip().lower()
            if not is_allowed_shape_id(shape):
                errors.append(f"invalid image option: {shape or '(empty)'}")
                continue
            url = normalize_product_image_url(img.get("url"), shape)
            if not url:
                continue
            prev = _optional_previous_image_url(img)
            entry = {"color": shape, "url": url}
            if prev:
                entry["previousFilePath"] = prev
            images.append(entry)
        final_shapes = {img["color"] for img in images}
        if not final_shapes:
            if is_published:
                errors.append("at least one product image is required")
        elif is_published and cleaned.get("defaultColor"):
            if not any(
                image_covers_default_color(s, cleaned["defaultColor"], category="diamond")
                for s in final_shapes
            ):
                errors.append("default color must have at least one image")
        cleaned["images"] = images
        if errors:
            return None, _format_product_errors(errors)
        return cleaned, None

    valid_carats = VALID_CARATS
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
        valid_thickness = (
            _is_valid_chain_thickness(carat)
            if category == "chain"
            else carat in valid_carats
        )
        if not valid_thickness:
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
        raw_manual = variant.get("manualPriceTwd")
        if raw_manual in (None, ""):
            raw_manual = variant.get("manual_price_twd")
        if raw_manual not in (None, ""):
            try:
                manual_price = float(raw_manual)
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
        ear_clasp_price = None
        raw_ear_clasp = variant.get("earClaspPriceTwd")
        if raw_ear_clasp in (None, ""):
            raw_ear_clasp = variant.get("earCuffPriceTwd")
        if category == "earring" and raw_ear_clasp not in (None, ""):
            try:
                ear_clasp_price = float(raw_ear_clasp)
            except (TypeError, ValueError):
                errors.append(f"invalid ear clasp price for {gold}/{carat}")
                continue
            if ear_clasp_price < 0:
                errors.append(f"invalid ear clasp price for {gold}/{carat}")
                continue
        addon_price = None
        raw_addon = variant.get("addonPriceTwd")
        if raw_addon in (None, ""):
            raw_addon = variant.get("addon_price_twd")
        if raw_addon not in (None, ""):
            try:
                addon_price = float(raw_addon)
            except (TypeError, ValueError):
                errors.append(f"invalid addon price for {gold}/{carat}")
                continue
            if addon_price < 0:
                errors.append(f"invalid addon price for {gold}/{carat}")
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
                "addonPriceTwd": addon_price,
                "earClaspPriceTwd": ear_clasp_price,
                # Alias for older admin clients still posting earCuffPriceTwd.
                "earCuffPriceTwd": ear_clasp_price,
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
        # Empty admin grid persists NULL; catalog/pricing fall back to type table.
        # Sync 46cm variant wax from the override or the type table — do not
        # copy the Excel snapshot into lengthWeights (that would become an override).
        sync_table = length_weights
        if sync_table is None and chain_type:
            sync_table = necklace_type_length_weights(chain_type)
        _sync_chain_variant_reference_weights(variants, sync_table)
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

    ring_size_config = None
    ring_size_provided = False
    if category == "ring":
        if "ringSizeConfig" in body or "ring_size_config" in body:
            ring_size_provided = True
            raw_rsc = body.get("ringSizeConfig")
            if raw_rsc is None:
                raw_rsc = body.get("ring_size_config")
            ring_size_config = _parse_ring_size_config(raw_rsc, errors=errors)
    cleaned["ringSizeConfig"] = ring_size_config
    cleaned["ringSizeConfigProvided"] = ring_size_provided

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
        prev = _optional_previous_image_url(img)
        entry = {"color": color, "url": url}
        if prev:
            entry["previousFilePath"] = prev
        images.append(entry)
    final_colors = {img["color"] for img in images}
    if not final_colors:
        if is_published:
            errors.append("at least one product image is required")
    elif is_published and cleaned.get("defaultColor"):
        default = cleaned["defaultColor"]
        if not any(
            image_covers_default_color(c, default, category=category)
            for c in final_colors
        ):
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
        "invalid styleKey": "款式代碼無效（須為 diamond-…）",
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
        if err.startswith("invalid ear cuff price for") or err.startswith(
            "invalid ear clasp price for"
        ):
            parts.append("款式選項：耳扣價錢無效")
            continue
        if err.startswith("invalid addon price for"):
            parts.append("款式選項：品項加價無效")
            continue
        if err == "invalid ring size config":
            parts.append("戒圍設定無效")
            continue
        if err == "invalid ring min size" or err == "invalid ring start size":
            parts.append("最小戒圍無效（須為 ≥ 1 的整數）")
            continue
        if err == "invalid ring max size":
            parts.append("最大戒圍無效（須為 ≥ 1 的整數）")
            continue
        if err == "ring min size exceeds max size":
            parts.append("最小戒圍不可大於最大戒圍")
            continue
        if err == "invalid ring charge after":
            parts.append("從多少之後開始加價無效（須為 ≥ 1 的整數）")
            continue
        if err == "ring charge after out of range":
            parts.append("從多少之後開始加價須在最小與最大之間")
            continue
        if err == "invalid ring price per size":
            parts.append("加多少無效（須 ≥ 0）")
            continue
        if err == "invalid ring size" or err == "invalid ring size row":
            parts.append("戒圍尺寸無效（須為 ≥ 1 的整數）")
            continue
        if err.startswith("duplicate ring size"):
            parts.append("戒圍尺寸重複：" + err.split(": ", 1)[-1])
            continue
        if err.startswith("invalid ring size addon for"):
            parts.append("戒圍品項加價無效")
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


def _optional_previous_image_url(img: dict) -> str | None:
    raw = img.get("previousFilePath")
    if raw is None:
        raw = img.get("previous_file_path")
    if not raw:
        return None
    path = normalize_product_image_url(raw, str(img.get("color") or "").strip().lower())
    return path or None


def serialize_product_image(row: dict | None) -> dict | None:
    """Admin/list image row — iso timestamps so client can bust thumbs with ?v=."""
    if not row:
        return None
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    if out.get("product_id") is not None:
        out["product_id"] = str(out["product_id"])
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    return out


def append_product_image(cur, product_id: str, color: str, file_path: str) -> dict | None:
    """Insert one image row for an existing product (upload-time SQL persist)."""
    ensure_product_images_previous_column(cur)
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
        returning id, product_id, color, file_path, sort_order, previous_file_path, updated_at
        """,
        (product_id, color_key, path, next_sort),
    )
    row = cur.fetchone()
    return serialize_product_image(row) if row else None


def replace_product_image(cur, image_id: str, new_url: str) -> tuple[dict | None, str | None]:
    """Swap file_path; keep one-deep previous. Drops older previous from Storage when unreferenced."""
    ensure_product_images_previous_column(cur)
    path = normalize_product_image_url(new_url, "")
    if not path:
        return None, "圖片網址無效"
    cur.execute(
        "select id, file_path, previous_file_path from product_images where id = %s",
        (image_id,),
    )
    row = cur.fetchone()
    if not row:
        return None, "找不到圖片"
    old_current = str(row.get("file_path") or "").strip()
    old_prev = str(row.get("previous_file_path") or "").strip()
    # Same Storage key (upsert overwrite): no separate previous object to keep.
    next_prev = old_current if old_current and old_current != path else None
    cur.execute(
        """
        update product_images
        set file_path = %s, previous_file_path = %s, updated_at = now()
        where id = %s
        returning id, product_id, color, file_path, sort_order, previous_file_path, updated_at
        """,
        (path, next_prev, image_id),
    )
    updated = cur.fetchone()
    if old_prev and old_prev != path and old_prev != next_prev:
        delete_product_image_urls_if_unreferenced(cur, [old_prev])
    return (serialize_product_image(updated) if updated else None), None


def restore_product_image(cur, image_id: str) -> tuple[dict | None, str | None]:
    """Put previous_file_path back as current; GC discarded current when unreferenced."""
    ensure_product_images_previous_column(cur)
    cur.execute(
        "select id, file_path, previous_file_path from product_images where id = %s",
        (image_id,),
    )
    row = cur.fetchone()
    if not row:
        return None, "找不到圖片"
    prev = str(row.get("previous_file_path") or "").strip()
    if not prev:
        return None, "沒有可還原的圖片"
    current = str(row.get("file_path") or "").strip()
    cur.execute(
        """
        update product_images
        set file_path = %s, previous_file_path = null, updated_at = now()
        where id = %s
        returning id, product_id, color, file_path, sort_order, previous_file_path, updated_at
        """,
        (prev, image_id),
    )
    updated = cur.fetchone()
    if current and current != prev:
        delete_product_image_urls_if_unreferenced(cur, [current])
    return (serialize_product_image(updated) if updated else None), None


_VARIANT_NUMERIC_KEYS = (
    "weight_chin",
    "manual_price_twd",
    "side_stone_price_twd",
    "side_stone_carat",
    "side_stone_total_twd",
    "addon_price_twd",
    "ear_clasp_price_twd",
    "ear_cuff_price_twd",
)


def normalize_variant_row_for_admin(variant: dict) -> dict:
    """JSON-safe variant row for admin editor (Decimal → float + camel aliases)."""
    out = dict(variant)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    if out.get("product_id") is not None:
        out["product_id"] = str(out["product_id"])
    for key in _VARIANT_NUMERIC_KEYS:
        if key not in out or out[key] is None:
            continue
        try:
            out[key] = float(out[key])
        except (TypeError, ValueError):
            continue
    # Missing/null fixed 配鑽 total is OK — admin UI falls back to formula.
    out.setdefault("side_stone_total_twd", None)
    out.setdefault("addon_price_twd", None)
    out.setdefault("ear_clasp_price_twd", None)
    # Camel aliases so editor load works if a client only reads camelCase.
    if out.get("manual_price_twd") is not None:
        out["manualPriceTwd"] = out["manual_price_twd"]
    if out.get("addon_price_twd") is not None:
        out["addonPriceTwd"] = out["addon_price_twd"]
    if out.get("ear_clasp_price_twd") is not None:
        out["earClaspPriceTwd"] = out["ear_clasp_price_twd"]
    return out


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
    rsc = out.pop("ring_size_config", None)
    if rsc is not None:
        out["ringSizeConfig"] = rsc
    if out.get("style_key") is not None:
        out["styleKey"] = out["style_key"]
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
    ensure_product_images_previous_column(cur)
    cur.execute(
        """
        select 1 from product_images
        where (file_path = %s or previous_file_path = %s)
          and product_id <> %s
        limit 1
        """,
        (url, url, product_id),
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

    Live refs: file_path and previous_file_path. Only Supabase URLs under
    products/. Dedupes. Best-effort: Storage failures do not raise. Returns how
    many delete_by_url calls reported success.
    """
    candidates: list[str] = []
    seen: set[str] = set()
    for raw in urls or []:
        url = str(raw or "").strip()
        if not url or url in seen or not _is_products_storage_url(url):
            continue
        seen.add(url)
        candidates.append(url)

    if not candidates:
        return 0

    ensure_product_images_previous_column(cur)
    deleted = 0
    for url in candidates:
        cur.execute(
            """
            select 1 from product_images
            where file_path = %s or previous_file_path = %s
            limit 1
            """,
            (url, url),
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
    ensure_product_ear_clasp_price_column(cur)
    ensure_product_variant_addon_price_column(cur)
    ensure_product_ring_size_config_column(cur)
    cur.execute("delete from product_variants where product_id = %s", (product_id,))
    for variant in cleaned["variants"]:
        ear_clasp = variant.get("earClaspPriceTwd")
        if ear_clasp is None:
            ear_clasp = variant.get("earCuffPriceTwd")
        cur.execute(
            """
            insert into product_variants (
                product_id, gold, carat, weight_chin, manual_price_twd,
                side_stone_price_twd, side_stone_carat, side_stone_total_twd,
                addon_price_twd, ear_clasp_price_twd
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                variant.get("addonPriceTwd"),
                ear_clasp,
            ),
        )

    cur.execute(
        """
        update products set length_weights = %s, chain_type = %s,
            ring_size_config = %s
        where id = %s
        """,
        (
            as_jsonb(cleaned.get("lengthWeights") or None),
            cleaned.get("chainType"),
            as_jsonb(cleaned.get("ringSizeConfig")),
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

    ensure_product_images_previous_column(cur)
    cur.execute(
        "select file_path, previous_file_path from product_images where product_id = %s",
        (product_id,),
    )
    previous_urls: set[str] = set()
    for row in cur.fetchall():
        for key in ("file_path", "previous_file_path"):
            value = str(row.get(key) or "").strip()
            if value:
                previous_urls.add(value)

    cur.execute("delete from product_images where product_id = %s", (product_id,))
    for sort_order, image in enumerate(cleaned["images"]):
        url = image["url"]
        metal = metal_color_from_slot(image.get("color"))
        url = promote_pending_product_url(url, folder, metal, category=category)
        image["url"] = url
        prev = image.get("previousFilePath") or image.get("previous_file_path")
        prev_url = None
        if prev:
            prev_url = promote_pending_product_url(
                str(prev), folder, metal, category=category
            )
            image["previousFilePath"] = prev_url
        cur.execute(
            """
            insert into product_images (
                product_id, color, file_path, sort_order, previous_file_path, updated_at
            )
            values (%s, %s, %s, %s, %s, now())
            """,
            (product_id, image["color"], url, sort_order, prev_url),
        )

    new_urls: set[str] = set()
    for img in cleaned["images"]:
        if img.get("url"):
            new_urls.add(str(img["url"]).strip())
        prev = img.get("previousFilePath") or img.get("previous_file_path")
        if prev:
            new_urls.add(str(prev).strip())
    delete_product_image_urls_if_unreferenced(cur, previous_urls - new_urls)


def publish_readiness(cur, product: dict) -> tuple[bool, str | None]:
    product_id = product["id"]
    category = str(product.get("category") or "").strip()
    # Memorial diamond: images only (no metal / price variants).
    if category != "diamond":
        cur.execute(
            "select count(*) as c from product_variants where product_id = %s",
            (product_id,),
        )
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
    if not any(
        image_covers_default_color(row["color"], default, category=category)
        for row in cur.fetchall()
    ):
        return False, "預設顏色必須至少有一張商品照片"
    return True, None


def first_published_at_value(existing: dict | None, is_published: bool) -> datetime | None:
    if existing and existing.get("first_published_at"):
        return existing["first_published_at"]
    if is_published:
        return datetime.now(timezone.utc)
    return None
