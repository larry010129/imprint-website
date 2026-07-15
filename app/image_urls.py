"""Resolve product image paths stored in DB to browser URLs."""

from __future__ import annotations

import re

_STYLE_ID = re.compile(r"^([a-z]+)-([A-C])$", re.I)
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
_VALID_CATEGORIES = frozenset({"pendant", "ring", "earring", "bracelet", "chain"})


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


def category_image_url(category: str | None) -> str:
    cat = (category or "").strip().lower()
    if cat in _VALID_CATEGORIES:
        return f"/static/images/shop/categories/{cat}.svg"
    return ""


def order_style_image_url(category: str | None, style_type: str | None) -> str:
    cat = (category or "").strip().lower()
    if not style_type:
        return category_image_url(cat)

    style = str(style_type).strip()
    if is_uuid(style):
        return category_image_url(cat)
    if len(style) == 1 and style in "ABC" and cat:
        return f"/static/images/shop/styles/{cat}-{style}.svg"

    match = _STYLE_ID.match(style)
    if match:
        return f"/static/images/shop/styles/{match.group(1).lower()}-{match.group(2).upper()}.svg"

    return category_image_url(cat)


def order_product_id(order: dict) -> str | None:
    pid = order.get("product_id")
    if pid:
        return str(pid)
    pt = order.get("product_type")
    if is_uuid(pt):
        return str(pt).strip()
    return None


if __name__ == "__main__":
    assert order_style_image_url("ring", "classic-solitaire") == "/static/images/shop/categories/ring.svg"
    assert order_style_image_url("ring", "A") == "/static/images/shop/styles/ring-A.svg"
    assert resolve_product_image_url("images/products/white/pendant-A.png") == "/static/images/products/white/pendant-A.png"
