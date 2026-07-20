"""Resolve product image paths stored in DB to browser URLs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote

_STYLE_ID = re.compile(r"^([a-z]+)-([A-C])$", re.I)
_STYLE_FROM_PATH = re.compile(r"(?:^|/)([a-z]+)-([A-C])\.(?:svg|png|jpe?g|webp)", re.I)
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
_VALID_CATEGORIES = frozenset({"pendant", "ring", "earring", "bracelet", "chain"})
_DIAMOND_COLORS = frozenset({"white", "yellow", "blue", "pink"})

_IMAGE_ROOT = "/static/images/shop-product/"

_CATEGORY_ZH = {
    "pendant": "項墜",
    "ring": "戒指",
    "earring": "耳飾",
    "bracelet": "手鍊",
}

_COLOR_DIR = {"white": "silver", "yellow": "gold", "rose": "rose_gold"}
_COLOR_SUFFIX = {"white": "silver", "yellow": "gold", "rose": "rose"}

_CHAIN_BASENAME = {
    "A": "斗圓鍊",
    "B": "斗圓鍊K玫瑰",
    "C": "斗圓鍊K黃",
}

_FILE_OVERRIDES = {
    "rose_gold|斗圓鍊K玫瑰|rose": "斗圓鍊K玫瑰_silver2.png",
}

_CATEGORY_THUMB = {
    "pendant": "thumbs/pendant/A.jpg",
    "ring": "thumbs/ring/A.jpg",
    "earring": "thumbs/earring/A.jpg",
    "bracelet": "thumbs/bracelet/A.jpg",
    "chain": "thumbs/chain/A.jpg",
}


def _style_thumb_rel(style_key: str) -> str:
    match = _STYLE_ID.match(style_key)
    if not match:
        return ""
    category = match.group(1).lower()
    style = match.group(2).upper()
    if category not in _VALID_CATEGORIES or style not in "ABC":
        return ""
    return f"thumbs/{category}/{style}.jpg"


def is_uuid(value: str | None) -> bool:
    return bool(value and _UUID.match(str(value).strip()))


def resolve_product_image_url(file_path: str | None) -> str:
    if not file_path:
        return ""
    path = file_path.strip()
    if path.startswith(("http://", "https://")):
        return path
    if path.startswith("/static/"):
        return path
    if path.startswith("/"):
        return path

    if path.startswith("images/shop/"):
        return f"/static/{path}"
    if path.startswith("static/"):
        return f"/{path}"
    if path.startswith("images/"):
        return f"/static/{path}"
    return f"/{path}"


def _is_raster_url(url: str) -> bool:
    return bool(url) and not url.lower().split("?", 1)[0].endswith(".svg")


def _resolve_color(color: str | None) -> str:
    c = (color or "white").strip().lower()
    return c if c in _COLOR_DIR else "white"


def _resolve_diamond(diamond: str | None) -> str:
    d = (diamond or "white").strip().lower()
    return d if d in _DIAMOND_COLORS else "white"


def config_diamond_color(config: dict[str, Any] | None) -> str:
    """Diamond color id for shop-product filenames (white|yellow|blue|pink)."""
    if not config:
        return "white"
    cat = (config.get("category") or "").strip().lower()
    if cat == "chain":
        return "white"
    dc = config.get("diamondColor")
    if isinstance(dc, str) and dc.strip().lower() in _DIAMOND_COLORS:
        return dc.strip().lower()
    if config.get("diamondKind") == "white":
        return "white"
    fancy = config.get("fancyColor")
    if isinstance(fancy, str) and fancy.strip().lower() in _DIAMOND_COLORS:
        return fancy.strip().lower()
    return "white"


def _join_shop_path(relative: str) -> str:
    return _IMAGE_ROOT + relative.lstrip("/")


_SHOP_ASSET_EXISTS_CACHE: dict[str, bool] = {}


def _shop_asset_exists(url: str) -> bool:
    if not url.startswith("/static/"):
        return False
    cached = _SHOP_ASSET_EXISTS_CACHE.get(url)
    if cached is not None:
        return cached
    from config.settings import settings

    rel = unquote(url[len("/static/") :])
    exists = (settings.static_dir / Path(rel)).is_file()
    _SHOP_ASSET_EXISTS_CACHE[url] = exists
    return exists


def style_key_from_path(path: str | None) -> str | None:
    if not path:
        return None
    match = _STYLE_FROM_PATH.search(str(path).replace("\\", "/"))
    if not match:
        return None
    return f"{match.group(1).lower()}-{match.group(2).upper()}"


def style_key_from_refs(category: str | None, type_ref: str | None) -> str | None:
    cat = (category or "").strip().lower()
    ref = str(type_ref or "").strip()
    if not ref or is_uuid(ref):
        return None
    if len(ref) == 1 and ref in "ABC" and cat:
        return f"{cat}-{ref}"
    match = _STYLE_ID.match(ref)
    if match:
        return f"{match.group(1).lower()}-{match.group(2).upper()}"
    return None


def shop_style_png_url(
    category: str | None,
    style_letter: str,
    color: str | None,
    diamond_color: str | None = None,
    *,
    chain_color: str | None = None,
) -> str:
    cat = (category or "").strip().lower()
    style = (style_letter or "").strip().upper()
    if cat not in _VALID_CATEGORIES or style not in "ABC":
        return ""

    resolved = _resolve_color(color)
    color_dir = _COLOR_DIR[resolved]
    suffix = _COLOR_SUFFIX[resolved]
    diamond = _resolve_diamond(diamond_color)
    diamond_suffix = f"_{diamond}" if diamond != "white" else ""

    if cat == "chain":
        basename = _CHAIN_BASENAME.get(style)
        if not basename:
            return ""
        override_key = f"{color_dir}|{basename}|{suffix}"
        if override_key in _FILE_OVERRIDES:
            return _join_shop_path(f"{color_dir}/{_FILE_OVERRIDES[override_key]}")
        return _join_shop_path(f"{color_dir}/{basename}_{suffix}{diamond_suffix}.png")

    zh = _CATEGORY_ZH.get(cat)
    if not zh:
        return ""

    if chain_color:
        chain_resolved = _resolve_color(chain_color)
        if chain_resolved != resolved:
            chain_suffix = _COLOR_SUFFIX[chain_resolved]
            return _join_shop_path(
                f"{color_dir}/{zh}{style}_{suffix}_chain_{chain_suffix}{diamond_suffix}.png"
            )

    return _join_shop_path(f"{color_dir}/{zh}{style}_{suffix}{diamond_suffix}.png")


def shop_product_image_url(
    style_key: str | None,
    color: str | None,
    *,
    default_color: str | None = None,
    diamond_color: str | None = None,
    chain_color: str | None = None,
) -> str:
    if not style_key:
        return ""
    match = _STYLE_ID.match(style_key)
    if not match:
        return shop_style_thumb_url(style_key)

    category = match.group(1).lower()
    style = match.group(2).upper()
    resolved = _resolve_color(color or default_color)
    png = shop_style_png_url(
        category,
        style,
        resolved,
        diamond_color,
        chain_color=chain_color,
    )
    if png and (diamond_color in (None, "", "white") or _shop_asset_exists(png)):
        return png
    if png and _resolve_diamond(diamond_color) != "white":
        # Fancy stone render missing — fall back to white-stone metal match
        white = shop_style_png_url(category, style, resolved, "white", chain_color=chain_color)
        if white:
            return white
    return png or shop_style_thumb_url(style_key)


def shop_style_thumb_url(style_key: str | None) -> str:
    if not style_key:
        return ""
    rel = _style_thumb_rel(style_key)
    if rel:
        return _join_shop_path(rel)
    match = _STYLE_ID.match(style_key)
    if match:
        png = shop_style_png_url(match.group(1).lower(), match.group(2).upper(), "white")
        if png:
            return png
    return ""


def shop_category_thumb_url(category: str | None) -> str:
    cat = (category or "").strip().lower()
    rel = _CATEGORY_THUMB.get(cat)
    return _join_shop_path(rel) if rel else ""


def category_image_url(category: str | None) -> str:
    """Real category preview (jpg/png), not legacy SVG placeholders."""
    return shop_category_thumb_url(category)


def order_style_image_url(category: str | None, style_type: str | None) -> str:
    """Legacy name — resolves to shop-product photos when possible."""
    style_key = style_key_from_refs(category, style_type)
    if style_key:
        url = shop_product_image_url(style_key, "white")
        if url:
            return url
    return shop_category_thumb_url(category)


def config_image_url(
    cur,
    config: dict[str, Any],
    *,
    style_type: str | None = None,
    category: str | None = None,
    product_id: str | None = None,
    images: list[dict] | None = None,
    products_by_id: dict[str, dict] | None = None,
) -> str:
    """Best product photo for a shop/cart config — matches metal + diamond selection."""
    from app.catalog import legacy_style_key, resolve_product_id

    cat = (category or config.get("category") or "").strip().lower()
    # Prefer real style/uuid from config.type over display names passed as style_type
    cfg_type = config.get("type")
    type_ref = cfg_type or style_type
    if style_type and cfg_type:
        style_as_key = style_key_from_refs(cat, str(style_type)) or (
            str(style_type) if is_uuid(str(style_type)) else None
        )
        if not style_as_key:
            type_ref = cfg_type
    color = _resolve_color(config.get("color") or "white")
    diamond = config_diamond_color(config)
    chain_color = config.get("chainColor") if config.get("includeChain") else None

    pid = product_id
    if not pid and type_ref and cat:
        # Only resolve when type_ref looks like uuid / ring-A — skip display names
        if is_uuid(str(type_ref)) or style_key_from_refs(cat, str(type_ref)):
            pid = resolve_product_id(cur, category=cat, type_ref=str(type_ref), require_published=False)

    product_row: dict | None = None
    image_rows = images
    if pid and image_rows is None:
        cur.execute("select id, category, sort_order from products where id = %s", (pid,))
        product_row = cur.fetchone()
        cur.execute(
            "select color, file_path from product_images where product_id = %s order by sort_order",
            (pid,),
        )
        image_rows = cur.fetchall()
    elif pid and products_by_id and str(pid) in products_by_id:
        product_row = products_by_id[str(pid)]

    def _db_url_for(*slot_keys: str) -> str:
        if not image_rows:
            return ""
        by_color = {row.get("color"): row for row in image_rows if row.get("color")}
        for key in slot_keys:
            row = by_color.get(key)
            if not row:
                continue
            url = resolve_product_image_url(row.get("file_path"))
            if url and _is_raster_url(url):
                return url
        return ""

    db_url = ""
    style_key = style_key_from_refs(cat, str(type_ref) if type_ref else None)

    # Exact metal-diamond DB upload (admin slot key e.g. white-pink)
    if diamond != "white":
        exact = _db_url_for(f"{color}-{diamond}")
        if exact:
            return exact

    # Shop-product render with diamond color (and pendant+chain combo when set)
    if not style_key and product_row:
        style_key = legacy_style_key(product_row, image_rows or [])
    elif not style_key and pid and not product_row:
        # Last resort only — avoid N+1 when batch products_by_id already provided
        cur.execute("select id, category, sort_order from products where id = %s", (pid,))
        product_row = cur.fetchone()
        if product_row:
            style_key = legacy_style_key(product_row, image_rows or [])
    if not style_key and image_rows:
        style_key = style_key_from_path(image_rows[0].get("file_path"))

    if style_key and diamond != "white":
        real = shop_product_image_url(
            style_key,
            color,
            default_color=color,
            diamond_color=diamond,
            chain_color=chain_color,
        )
        if real and _shop_asset_exists(real):
            return real

    # Legacy metal-only DB upload / white-stone slot
    db_url = _db_url_for(color, f"{color}-white")
    if db_url and diamond == "white":
        return db_url
    if not db_url and image_rows:
        first = resolve_product_image_url(image_rows[0].get("file_path"))
        if first and _is_raster_url(first):
            db_url = first
            if diamond == "white":
                return db_url
            style_key = style_key or style_key_from_path(image_rows[0].get("file_path"))

    if style_key:
        real = shop_product_image_url(
            style_key,
            color,
            default_color=color,
            diamond_color=diamond,
            chain_color=chain_color,
        )
        if real:
            return real

    if db_url:
        return db_url

    return shop_category_thumb_url(cat)


def order_product_id(order: dict) -> str | None:
    pid = order.get("product_id")
    if pid:
        return str(pid)
    pt = order.get("product_type")
    if is_uuid(pt):
        return str(pt).strip()
    return None


if __name__ == "__main__":
    assert shop_product_image_url("ring-A", "white") == "/static/images/shop-product/silver/戒指A_silver.png"
    assert (
        shop_product_image_url("ring-A", "white", diamond_color="pink")
        == "/static/images/shop-product/silver/戒指A_silver_pink.png"
    )
    assert config_diamond_color({"diamondKind": "fancy", "fancyColor": "pink"}) == "pink"
    assert shop_style_thumb_url("ring-A") == "/static/images/shop-product/thumbs/ring/A.jpg"
    assert resolve_product_image_url("images/products/white/pendant-A.png") == "/static/images/products/white/pendant-A.png"
    assert style_key_from_refs("ring", "A") == "ring-A"
    assert not order_style_image_url("ring", "A").endswith(".svg")

