"""Shared order display fields for member + admin APIs."""

from __future__ import annotations

from app.admin_products import CATEGORY_LABELS
from app.image_urls import is_uuid, order_product_id, order_style_image_url, resolve_product_image_url


def product_display_name(order: dict, products_by_id: dict[str, dict]) -> str:
    pid = order_product_id(order)
    if pid and pid in products_by_id:
        row = products_by_id[pid]
        return row.get("name_zh") or row.get("name_en") or "訂製品項"
    product_type = (order.get("product_type") or "").strip()
    if product_type and not is_uuid(product_type):
        return product_type
    category = order.get("category")
    return CATEGORY_LABELS.get(category, category) or "訂製品項"


def attach_order_display(cur, orders: list[dict]) -> None:
    """Resolve product names, summary labels, thumbnails, and display dates."""
    product_ids: list[str] = []
    for order in orders:
        pid = order_product_id(order)
        if pid:
            product_ids.append(pid)

    products_by_id: dict[str, dict] = {}
    if product_ids:
        cur.execute(
            "select id, name_zh, name_en, category from products where id = any(%s)",
            (list(set(product_ids)),),
        )
        for row in cur.fetchall():
            products_by_id[str(row["id"])] = row

    images_by_product: dict[str, list] = {}
    if product_ids:
        cur.execute(
            "select * from product_images where product_id = any(%s) order by sort_order",
            (list(set(product_ids)),),
        )
        for image in cur.fetchall():
            images_by_product.setdefault(str(image["product_id"]), []).append(image)

    for order in orders:
        if order.get("id") is not None:
            order["id"] = str(order["id"])
        if order.get("product_id") is not None:
            order["product_id"] = str(order["product_id"])

        name = product_display_name(order, products_by_id)
        order["product_name"] = name
        series = order.get("series")
        order["summary"] = f"{series} · {name}" if series else name
        if is_uuid(order.get("product_type")):
            order["product_type"] = name

        url = ""
        pid = order_product_id(order)
        if pid and pid in images_by_product:
            imgs = images_by_product[pid]
            color = order.get("color") or "white"
            match = next((i for i in imgs if i["color"] == color), None)
            if not match and imgs:
                match = imgs[0]
            if match:
                url = resolve_product_image_url(match["file_path"])
        if not url:
            url = order_style_image_url(order.get("category"), order.get("product_type"))
        order["image_url"] = url

        created = order.get("created_at")
        if created is not None:
            order["created_at_display"] = created.strftime("%Y/%m/%d")
