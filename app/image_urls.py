"""Resolve product image paths stored in DB to browser URLs."""

from __future__ import annotations

import re
from typing import Any

_STYLE_ID = re.compile(r"^([a-z]+)-([A-C])$", re.I)
_STYLE_FROM_PATH = re.compile(r"(?:^|/)([a-z]+)-([A-C])\.(?:svg|png|jpe?g|webp)", re.I)
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
_VALID_CATEGORIES = frozenset({"pendant", "ring", "earring", "bracelet", "chain"})

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
    "pendant": "墜子/項墜A.jpg",
    "ring": "戒指/戒指A.jpg",
    "earring": "耳飾/耳飾A.jpg",
    "bracelet": "手鍊/手鍊A.jpg",
    "chain": "鍊條/斗圓鍊.jpg",
}

_STYLE_THUMB = {
    "pendant-A": "墜子/項墜A.jpg",
    "pendant-B": "墜子/項墜B.jpg",
    "pendant-C": "墜子/項墜C.jpg",
    "ring-A": "戒指/戒指A.jpg",
    "ring-B": "戒指/戒指B.jpg",
    "ring-C": "戒指/戒指C.jpg",
    "earring-A": "耳飾/耳飾A.jpg",
    "bracelet-A": "手鍊/手鍊A.jpg",
    "bracelet-B": "手鍊/手鍊B.jpg",
    "bracelet-C": "手鍊/手鍊C.jpg",
    "chain-A": "鍊條/斗圓鍊.jpg",
    "chain-B": "鍊條/斗圓鍊K玫瑰_0.jpg",
    "chain-C": "鍊條/斗圓鍊K黃_0.jpg",
}


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


def _join_shop_path(relative: str) -> str:
    return _IMAGE_ROOT + relative.lstrip("/")


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


def shop_style_png_url(category: str | None, style_letter: str, color: str | None) -> str:
    cat = (category or "").strip().lower()
    style = (style_letter or "").strip().upper()
    if cat not in _VALID_CATEGORIES or style not in "ABC":
        return ""

    resolved = _resolve_color(color)
    color_dir = _COLOR_DIR[resolved]
    suffix = _COLOR_SUFFIX[resolved]

    if cat == "chain":
        basename = _CHAIN_BASENAME.get(style)
        if not basename:
            return ""
        override_key = f"{color_dir}|{basename}|{suffix}"
        if override_key in _FILE_OVERRIDES:
            return _join_shop_path(f"{color_dir}/{_FILE_OVERRIDES[override_key]}")
        return _join_shop_path(f"{color_dir}/{basename}_{suffix}.png")

    zh = _CATEGORY_ZH.get(cat)
    if not zh:
        return ""
    return _join_shop_path(f"{color_dir}/{zh}{style}_{suffix}.png")


def shop_product_image_url(style_key: str | None, color: str | None, *, default_color: str | None = None) -> str:
    if not style_key:
        return ""
    match = _STYLE_ID.match(style_key)
    if not match:
        return shop_style_thumb_url(style_key)

    category = match.group(1).lower()
    style = match.group(2).upper()
    resolved = _resolve_color(color or default_color)
    png = shop_style_png_url(category, style, resolved)
    return png or shop_style_thumb_url(style_key)


def shop_style_thumb_url(style_key: str | None) -> str:
    if not style_key:
        return ""
    rel = _STYLE_THUMB.get(style_key)
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
) -> str:
    """Best product photo for a shop/cart config — DB upload first, then shop-product renders."""
    from app.catalog import legacy_style_key, resolve_product_id

    cat = (category or config.get("category") or "").strip().lower()
    type_ref = style_type or config.get("type")
    color = config.get("color") or "white"

    pid = product_id
    if not pid and type_ref and cat:
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
    elif pid and not product_row:
        cur.execute("select id, category, sort_order from products where id = %s", (pid,))
        product_row = cur.fetchone()

    db_url = ""
    style_key = style_key_from_refs(cat, str(type_ref) if type_ref else None)
    if image_rows:
        match = next((row for row in image_rows if row.get("color") == color), None)
        if not match:
            match = image_rows[0]
        if match:
            db_url = resolve_product_image_url(match.get("file_path"))
            if db_url and _is_raster_url(db_url):
                return db_url
            style_key = style_key or style_key_from_path(match.get("file_path"))

    if not style_key and product_row:
        style_key = legacy_style_key(product_row, image_rows or [])

    if style_key:
        real = shop_product_image_url(style_key, color, default_color=color)
        if real:
            return real

    if db_url:
        return db_url

    thumb = shop_category_thumb_url(cat)
    return thumb


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
    assert shop_style_thumb_url("ring-A") == "/static/images/shop-product/戒指/戒指A.jpg"
    assert resolve_product_image_url("images/products/white/pendant-A.png") == "/static/images/products/white/pendant-A.png"
    assert style_key_from_refs("ring", "A") == "ring-A"
    assert not order_style_image_url("ring", "A").endswith(".svg")

