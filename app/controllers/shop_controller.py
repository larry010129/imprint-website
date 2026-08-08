"""Shop cart + checkout for the FastAPI app."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from psycopg.types.json import Jsonb

from app.auth import get_user_id
from app.catalog import resolve_product_id
from app.coupons import apply_discount_split, record_redemptions, validate_coupon
from app.database import get_connection, get_transaction
from app.image_urls import config_image_url
from app.orders import (
    attach_order_display,
    attach_order_relations,
    cart_details_from_config,
    pack_order_config,
)
from app.pricing import (
    _as_line_quantity,
    cart_line_quantity_max,
    compute_order_pricing,
    get_product_variant,
    normalize_gold,
)
from app.tw_address import validate_tw_shipping_parts as _validate_tw_shipping_parts

router = APIRouter(tags=["shop"])


def cart_needs_collection_bottle(items: list[dict[str, Any]]) -> bool:
    """True when any line needs a DNA/collection bottle (all non-chain custom orders)."""
    for item in items:
        config = _cart_item_config(item)
        cat = str(config.get("category") or item.get("category") or "").strip().lower()
        if cat and cat != "chain":
            return True
    return False


def _err(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


def _user_id(request: Request) -> str:
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not signed in")
    return user_id


def _summary(config: dict[str, Any]) -> str:
    if config.get("summaryZh"):
        return str(config["summaryZh"])
    category = config.get("category") or ""
    style = config.get("type") or ""
    return f"{category} {style}".strip() or "訂製品項"


def _pricing(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("clientPricing")
    return raw if isinstance(raw, dict) else {}


def _validate_config(body: dict[str, Any]) -> str | None:
    # ponytail: required-field only; upgrade = port choice/engraving/length checks
    # from retired backend/lib/validation.js when bad CMS/cart payloads show up.
    for key in ("category", "type", "carat"):
        if not body.get(key):
            return f"缺少欄位：{key}"
    if body.get("category") != "diamond" and not body.get("gold"):
        return "缺少欄位：gold"
    return None


def _validate_product_variant(cur, body: dict[str, Any], *, require_published: bool = True) -> str | None:
    """Reject gold/carat combos that are not in the product's 款式選項."""
    category = str(body.get("category") or "")
    if category == "diamond":
        return None
    gold = body.get("gold")
    carat = body.get("carat")
    if not gold or carat is None or carat == "":
        return None
    product_ref = str(body.get("type") or body.get("productId") or "")
    variant = get_product_variant(
        cur,
        category=category,
        product_id=product_ref,
        gold=normalize_gold(str(gold)),
        carat=str(carat),
        require_published=require_published,
    )
    if not variant:
        return "所選金屬或克拉不在此商品款式選項中"
    return None


CART_UNAVAILABLE_REASON = "商品已下架或規格已變更"
CART_UNAVAILABLE_CHECKOUT_MSG = "請先移除無法購買品項"


def _cart_item_config(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize cart row config; fill category/type from row columns when missing."""
    raw = item.get("config_json") or {}
    config = dict(raw) if isinstance(raw, dict) else {}
    if not config.get("category") and item.get("category"):
        config["category"] = item["category"]
    if not config.get("type") and item.get("style_type"):
        config["type"] = item["style_type"]
    return config


def _mark_cart_available(item: dict[str, Any], available: bool, reason: str = "") -> dict[str, Any]:
    item["available"] = available
    item["unavailableReason"] = reason
    return item


def annotate_cart_item(cur, item: dict[str, Any]) -> dict[str, Any]:
    """Mark cart line available/unavailable without rewriting stored price."""
    config = _cart_item_config(item)
    category = str(config.get("category") or "")
    cfg_err = _validate_config(config)
    if cfg_err:
        return _mark_cart_available(item, False, cfg_err)
    # Diamond memorial: required fields only — no product-row / publish gate.
    if category == "diamond":
        pricing = compute_order_pricing(cur, config, require_published=False)
        if pricing.get("ready") and pricing.get("compareAtTotal"):
            item["compare_at_total"] = pricing["compareAtTotal"]
        return _mark_cart_available(item, True)
    if _validate_product_variant(cur, config, require_published=True):
        return _mark_cart_available(item, False, CART_UNAVAILABLE_REASON)
    pricing = compute_order_pricing(cur, config, require_published=True)
    if not pricing.get("ready"):
        return _mark_cart_available(item, False, CART_UNAVAILABLE_REASON)
    if pricing.get("compareAtTotal"):
        item["compare_at_total"] = pricing["compareAtTotal"]
    return _mark_cart_available(item, True)


def _strip_disallowed_engraving(cur, body: dict[str, Any]) -> None:
    """Clear band/metal engraving when product disallows 可刻字.

    腰圍刻字 (girdle) is always available for DNA diamond products and is never
    gated by allows_engraving. Clear girdle only for chain (no diamond).
    """
    category = str(body.get("category") or "").strip()
    if category == "chain":
        body["engravingGirdle"] = ""
    # Rings use band engraving only — drop metal-body remark if client sends it.
    if category == "ring":
        body["engravingRemark"] = ""

    if not body.get("engravingBand") and not body.get("engravingRemark"):
        return
    product_id = resolve_product_id(
        cur,
        category=category,
        type_ref=str(body.get("type") or body.get("productId") or ""),
        require_published=False,
    )
    if not product_id:
        return
    cur.execute("select allows_engraving from products where id = %s", (product_id,))
    row = cur.fetchone()
    if row and row.get("allows_engraving") is False:
        body["engravingBand"] = ""
        body["engravingRemark"] = ""


def _strip_disallowed_fancy_shape(cur, body: dict[str, Any]) -> None:
    shape = str(body.get("diamondShape") or "round").strip() or "round"
    if shape == "round":
        return
    product_id = resolve_product_id(
        cur,
        category=str(body.get("category") or ""),
        type_ref=str(body.get("type") or body.get("productId") or ""),
        require_published=False,
    )
    if not product_id:
        return
    cur.execute("select allows_fancy_shapes from products where id = %s", (product_id,))
    row = cur.fetchone()
    if row and row.get("allows_fancy_shapes") is False:
        body["diamondShape"] = "round"


def _clamp_pendant_chain_sell_mode(cur, body: dict[str, Any]) -> str | None:
    """Enforce per-product 僅墜子 / 含鍊賣 flags for pendant orders."""
    if str(body.get("category") or "") != "pendant":
        return None
    product_id = resolve_product_id(
        cur,
        category="pendant",
        type_ref=str(body.get("type") or body.get("productId") or ""),
        require_published=False,
    )
    if not product_id:
        return None
    cur.execute(
        "select allows_pendant_only, allows_with_chain from products where id = %s",
        (product_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    allows_only = row.get("allows_pendant_only", True) is not False
    allows_chain = row.get("allows_with_chain", True) is not False
    include_chain = bool(body.get("includeChain"))
    if include_chain and not allows_chain:
        return "此商品僅販售墜子，無法搭配鏈條"
    if (not include_chain) and not allows_only:
        return "此商品僅販售含鍊款式，請選擇鏈條長度"
    return None


def _profile(cur, user_id: str) -> dict[str, Any] | None:
    cur.execute(
        """
        select p.full_name, p.phone, u.email
        from profiles p
        join users u on u.id = p.id
        where p.id = %s
        """,
        (user_id,),
    )
    return cur.fetchone()


def _validate_customer(
    body: dict[str, Any],
    profile: dict[str, Any] | None,
    *,
    require_collection_bottle: bool = False,
) -> tuple[dict[str, Any], str | None]:
    name = str(body.get("customerName") or (profile or {}).get("full_name") or "").strip()
    phone = str(body.get("customerPhone") or (profile or {}).get("phone") or "").strip()
    email = str(body.get("customerEmail") or (profile or {}).get("email") or "").strip() or None
    method = str(body.get("fulfillmentMethod") or "pickup").strip()
    if method not in ("pickup", "delivery"):
        method = "pickup"
    address = str(body.get("shippingAddress") or "").strip() or None
    city = str(body.get("shippingCity") or "").strip() or None
    postal = str(body.get("shippingPostal") or "").strip() or None
    bottle_address = str(body.get("collectionBottleAddress") or "").strip() or None
    bottle_city = str(body.get("collectionBottleCity") or "").strip() or None
    bottle_postal = str(body.get("collectionBottlePostal") or "").strip() or None
    note = str(body.get("orderNote") or "").strip() or None
    if note and len(note) > 100:
        return {}, "備註最多 100 字"

    if not name:
        return {}, "請填寫收件人姓名"
    if not phone:
        return {}, "請填寫聯絡電話"
    if method == "delivery":
        city, postal, address, addr_err = _validate_tw_shipping_parts(
            address, city, postal, empty_msg="請填寫完整的收件地址"
        )
        if addr_err:
            return {}, addr_err

    if require_collection_bottle:
        bottle_city, bottle_postal, bottle_address, bottle_err = _validate_tw_shipping_parts(
            bottle_address,
            bottle_city,
            bottle_postal,
            empty_msg="請填寫完整的收集瓶寄送地址",
        )
        if bottle_err:
            return {}, bottle_err
    else:
        bottle_address = bottle_city = bottle_postal = None

    return {
        "name": name,
        "phone": phone,
        "email": email,
        "fulfillmentMethod": method,
        "shippingAddress": address,
        "shippingCity": city,
        "shippingPostal": postal,
        "collectionBottleAddress": bottle_address,
        "collectionBottleCity": bottle_city,
        "collectionBottlePostal": bottle_postal,
        "orderNote": note,
    }, None


def _insert_order(
    cur,
    user_id: str,
    customer: dict[str, Any],
    config: dict[str, Any],
    *,
    coupon_code: str | None = None,
    discount_amount: float = 0,
) -> dict[str, Any]:
    cfg, pricing, product_id, summary, total = pack_order_config(config)
    cfg["clientPricing"] = pricing
    config_payload = json.loads(json.dumps(cfg, default=str))
    subtotal = float(total or 0)
    discount = max(0.0, float(discount_amount or 0))
    if discount > subtotal:
        discount = subtotal
    final_total = subtotal - discount

    cur.execute(
        """
        insert into orders (
          user_id, summary_zh, total_price, status,
          coupon_code, discount_amount, subtotal_before_discount,
          status_timestamps
        )
        values (
          %s, %s, %s, 'received', %s, %s, %s,
          jsonb_build_object('received', now())
        )
        returning id, order_number
        """,
        (
            user_id,
            summary,
            final_total,
            coupon_code,
            discount,
            subtotal,
        ),
    )
    row = cur.fetchone()
    oid = row["id"]
    cur.execute(
        """
        insert into order_contacts (order_id, customer_name, customer_phone, customer_email)
        values (%s, %s, %s, %s)
        """,
        (oid, customer["name"], customer["phone"], customer["email"]),
    )
    cur.execute(
        """
        insert into order_fulfillment (
          order_id, fulfillment_method, shipping_address, shipping_city, shipping_postal,
          order_note, collection_bottle_address, collection_bottle_city, collection_bottle_postal
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            oid,
            customer["fulfillmentMethod"],
            customer["shippingAddress"],
            customer["shippingCity"],
            customer["shippingPostal"],
            customer["orderNote"],
            customer.get("collectionBottleAddress"),
            customer.get("collectionBottleCity"),
            customer.get("collectionBottlePostal"),
        ),
    )
    cur.execute(
        """
        insert into order_items (order_id, product_id, config_json, pricing_json, summary_zh)
        values (%s, %s, %s, %s, %s)
        """,
        (oid, product_id, Jsonb(config_payload), Jsonb(pricing), summary),
    )
    return {
        "order_id": oid,
        "order_number": row["order_number"],
        "order_subtotal": subtotal,
        "discount_amount": discount,
        "order_total": final_total,
    }


def _fetch_editable_order(cur, user_id: str, order_id: str | None, order_number: str | None) -> dict | None:
    if order_id:
        cur.execute(
            "select * from orders where id = %s and user_id = %s",
            (order_id, user_id),
        )
    elif order_number:
        cur.execute(
            "select * from orders where order_number = %s and user_id = %s",
            (order_number, user_id),
        )
    else:
        return None
    order = cur.fetchone()
    if order:
        attach_order_relations(cur, [order])
    return order


def _update_order_row(cur, order_id: str, config: dict[str, Any]) -> None:
    cfg, pricing, product_id, summary, total = pack_order_config(config)
    cfg["clientPricing"] = pricing
    config_payload = json.loads(json.dumps(cfg, default=str))

    cur.execute(
        """
        update orders set
          summary_zh = %s,
          total_price = %s,
          updated_at = now()
        where id = %s and status = 'received'
        """,
        (summary, total, order_id),
    )
    cur.execute(
        """
        update order_items set
          product_id = %s,
          config_json = %s,
          pricing_json = %s,
          summary_zh = %s
        where order_id = %s
        """,
        (product_id, Jsonb(config_payload), Jsonb(pricing), summary, order_id),
    )
    if cur.rowcount == 0:
        cur.execute(
            """
            insert into order_items (order_id, product_id, config_json, pricing_json, summary_zh)
            values (%s, %s, %s, %s, %s)
            """,
            (order_id, product_id, Jsonb(config_payload), Jsonb(pricing), summary),
        )


@router.get("/order")
async def get_my_order(request: Request) -> dict:
    user_id = _user_id(request)
    order_number = (request.query_params.get("orderNumber") or "").strip()
    order_id = (request.query_params.get("id") or "").strip()
    if not order_number and not order_id:
        return _err(400, "missing orderNumber or id")

    with get_connection() as conn, conn.cursor() as cur:
        order = _fetch_editable_order(cur, user_id, order_id or None, order_number or None)
        if not order:
            return _err(404, "not found")
        attach_order_display(cur, [order])
    return {"order": order}


@router.put("/order")
async def update_my_order(request: Request) -> dict:
    user_id = _user_id(request)
    body = await request.json()
    if not isinstance(body, dict):
        return _err(400, "invalid body")

    order_id = str(body.get("orderId") or body.get("id") or "").strip()
    order_number = str(body.get("orderNumber") or "").strip()
    if not order_id and not order_number:
        return _err(400, "missing order id")

    config = {k: v for k, v in body.items() if k not in ("orderId", "id", "orderNumber")}
    err = _validate_config(config)
    if err:
        return _err(400, err)

    with get_transaction() as conn, conn.cursor() as cur:
        order = _fetch_editable_order(cur, user_id, order_id or None, order_number or None)
        if not order:
            return _err(404, "not found")
        if order.get("status") != "received":
            return _err(400, "僅「已收到申請」狀態的訂單可修改")

        chain_err = _clamp_pendant_chain_sell_mode(cur, config)
        if chain_err:
            return _err(400, chain_err)
        _strip_disallowed_engraving(cur, config)
        _strip_disallowed_fancy_shape(cur, config)
        pricing = compute_order_pricing(cur, config)
        if not pricing.get("ready"):
            return _err(400, "無法計算價格，請重新整理後再試")
        config["clientPricing"] = pricing

        _update_order_row(cur, str(order["id"]), config)
        if cur.rowcount == 0:
            return _err(400, "無法更新此訂單")

    return {"ok": True, "orderNumber": order["order_number"]}


def fetch_cart_items(user_id: str, item_ids: list[str] | None = None) -> list[dict]:
    """Shared cart loader for JSON API + HTMX partials."""
    from app.image_urls import is_uuid

    # cart_items.id is uuid — bad strings raise InvalidTextRepresentation (500).
    if item_ids is not None:
        item_ids = [str(i).strip() for i in item_ids if is_uuid(str(i))]
        if not item_ids:
            return []

    with get_connection() as conn, conn.cursor() as cur:
        if item_ids:
            cur.execute(
                "select * from cart_items where user_id = %s and id = any(%s) order by created_at asc",
                (user_id, item_ids),
            )
        else:
            cur.execute(
                "select * from cart_items where user_id = %s order by created_at asc",
                (user_id,),
            )
        items = cur.fetchall()
        for item in items:
            config = _cart_item_config(item)
            item["image_url"] = config_image_url(
                cur,
                config,
                style_type=item.get("style_type"),
                category=item.get("category"),
            )
            annotate_cart_item(cur, item)
            item["details_zh"] = cart_details_from_config(config)
    return items


def set_cart_item_quantity(user_id: str, item_id: str, quantity: Any) -> dict[str, Any]:
    """Set cart line quantity; quantity <= 0 deletes the line. Recalculates total_price."""
    item_id = str(item_id or "").strip()
    if not item_id:
        return {"error": "missing id", "status": 400}
    try:
        raw = int(quantity)
    except (TypeError, ValueError):
        return {"error": "invalid quantity", "status": 400}

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select * from cart_items where id = %s and user_id = %s",
            (item_id, user_id),
        )
        item = cur.fetchone()
        if not item:
            return {"error": "not found", "status": 404}

        if raw <= 0:
            cur.execute(
                "delete from cart_items where id = %s and user_id = %s",
                (item_id, user_id),
            )
            cur.execute(
                "select count(*) as count from cart_items where user_id = %s",
                (user_id,),
            )
            count_row = cur.fetchone()
            return {
                "ok": True,
                "deleted": True,
                "id": item_id,
                "count": count_row["count"] if count_row else 0,
            }

        config = _cart_item_config(item)
        category = str(config.get("category") or item.get("category") or "")
        qty = _as_line_quantity(raw, category=category)
        config["quantity"] = qty
        error = _validate_config(config)
        if error:
            return {"error": error, "status": 400}
        variant_err = _validate_product_variant(cur, config)
        if variant_err:
            return {"error": variant_err, "status": 400}
        chain_err = _clamp_pendant_chain_sell_mode(cur, config)
        if chain_err:
            return {"error": chain_err, "status": 400}
        _strip_disallowed_engraving(cur, config)
        _strip_disallowed_fancy_shape(cur, config)
        pricing = compute_order_pricing(cur, config)
        if not pricing.get("ready"):
            return {"error": "無法計算價格，請重新整理後再試", "status": 400}
        config["clientPricing"] = pricing
        config_json = json.loads(json.dumps(config, default=str))
        summary = _summary(config)
        cur.execute(
            """
            update cart_items set
              category = %s,
              style_type = %s,
              config_json = %s,
              summary_zh = %s,
              total_price = %s
            where id = %s and user_id = %s
            returning *
            """,
            (
                config["category"],
                config["type"],
                Jsonb(config_json),
                summary,
                pricing.get("total"),
                item_id,
                user_id,
            ),
        )
        updated = cur.fetchone()
        cur.execute(
            "select count(*) as count from cart_items where user_id = %s",
            (user_id,),
        )
        count_row = cur.fetchone()
        return {
            "ok": True,
            "deleted": False,
            "item": updated,
            "quantity": qty,
            "max": cart_line_quantity_max(category),
            "count": count_row["count"] if count_row else None,
        }


def _err_from_qty_result(result: dict[str, Any]) -> JSONResponse | None:
    if "error" in result:
        return _err(int(result.get("status") or 400), str(result["error"]))
    return None


@router.get("/cart")
async def get_cart(request: Request) -> dict:
    user_id = _user_id(request)
    return {"items": fetch_cart_items(user_id)}


@router.post("/cart/quantity")
async def cart_quantity(request: Request) -> dict:
    user_id = _user_id(request)
    body = await request.json()
    if not isinstance(body, dict):
        return _err(400, "invalid body")
    result = set_cart_item_quantity(user_id, body.get("id"), body.get("quantity"))
    err = _err_from_qty_result(result)
    if err:
        return err
    return result


@router.post("/cart")
async def add_to_cart(request: Request) -> dict:
    user_id = _user_id(request)
    body = await request.json()
    if not isinstance(body, dict):
        return _err(400, "invalid body")
    error = _validate_config(body)
    if error:
        return _err(400, error)

    summary = _summary(body)

    with get_connection() as conn, conn.cursor() as cur:
        variant_err = _validate_product_variant(cur, body)
        if variant_err:
            return _err(400, variant_err)
        chain_err = _clamp_pendant_chain_sell_mode(cur, body)
        if chain_err:
            return _err(400, chain_err)
        _strip_disallowed_engraving(cur, body)
        _strip_disallowed_fancy_shape(cur, body)
        pricing = compute_order_pricing(cur, body)
        if not pricing.get("ready"):
            return _err(400, "無法計算價格，請重新整理後再試")
        body["clientPricing"] = pricing
        config_json = json.loads(json.dumps(body, default=str))

        cur.execute(
            """
            insert into cart_items (user_id, category, style_type, config_json, summary_zh, total_price)
            values (%s, %s, %s, %s, %s, %s)
            returning *
            """,
            (
                user_id,
                body["category"],
                body["type"],
                Jsonb(config_json),
                summary,
                pricing.get("total"),
            ),
        )
        item = cur.fetchone()
    return {"item": item}


@router.api_route("/cart-item", methods=["GET", "PUT", "DELETE"])
async def cart_item(request: Request) -> dict:
    user_id = _user_id(request)
    item_id = request.query_params.get("id")
    if not item_id:
        return _err(400, "missing id")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select * from cart_items where id = %s and user_id = %s",
            (item_id, user_id),
        )
        item = cur.fetchone()
        if not item:
            return _err(404, "not found")

        if request.method == "DELETE":
            cur.execute("delete from cart_items where id = %s and user_id = %s", (item_id, user_id))
            return {"ok": True}

        if request.method == "PUT":
            body = await request.json()
            if not isinstance(body, dict):
                return _err(400, "invalid body")
            error = _validate_config(body)
            if error:
                return _err(400, error)
            variant_err = _validate_product_variant(cur, body)
            if variant_err:
                return _err(400, variant_err)
            chain_err = _clamp_pendant_chain_sell_mode(cur, body)
            if chain_err:
                return _err(400, chain_err)
            _strip_disallowed_engraving(cur, body)
            _strip_disallowed_fancy_shape(cur, body)
            pricing = compute_order_pricing(cur, body)
            if not pricing.get("ready"):
                return _err(400, "無法計算價格，請重新整理後再試")
            body["clientPricing"] = pricing
            config_json = json.loads(json.dumps(body, default=str))
            summary = _summary(body)
            cur.execute(
                """
                update cart_items set
                  category = %s,
                  style_type = %s,
                  config_json = %s,
                  summary_zh = %s,
                  total_price = %s
                where id = %s and user_id = %s
                returning *
                """,
                (
                    body["category"],
                    body["type"],
                    Jsonb(config_json),
                    summary,
                    pricing.get("total"),
                    item_id,
                    user_id,
                ),
            )
            updated = cur.fetchone()
            cur.execute(
                "select count(*) as count from cart_items where user_id = %s",
                (user_id,),
            )
            count_row = cur.fetchone()
            return {"item": updated, "count": count_row["count"] if count_row else None}

        config = item.get("config_json") or {}
        pricing = _pricing(config)
        breakdown = {
            "diamondPrice": pricing.get("diamondPrice"),
            "taijinPrice": pricing.get("taijinPrice"),
            "laborPrice": pricing.get("laborPrice"),
            "metalworkPrice": pricing.get("metalworkPrice"),
            "chainPrice": pricing.get("chainPrice"),
            "total": pricing.get("total") or item.get("total_price"),
        }
        item["image_url"] = config_image_url(
            cur,
            config,
            style_type=item.get("style_type"),
            category=item.get("category"),
        )
        annotate_cart_item(cur, item)
        return {"item": item, "breakdown": breakdown}


@router.post("/coupon/validate")
async def coupon_validate(request: Request) -> dict:
    user_id = _user_id(request)
    body = await request.json()
    return await validate_coupon_body(user_id, body if isinstance(body, dict) else {})


async def validate_coupon_body(user_id: str, body: dict[str, Any]) -> dict:
    """Shared coupon validate for JSON API + HTMX (no duplicate pricing SQL)."""
    code = body.get("code") or body.get("couponCode") or ""
    item_ids = body.get("itemIds")

    with get_connection() as conn, conn.cursor() as cur:
        if item_ids:
            cur.execute(
                "select * from cart_items where user_id = %s and id = any(%s) order by created_at asc",
                (user_id, item_ids),
            )
        else:
            cur.execute(
                "select * from cart_items where user_id = %s order by created_at asc",
                (user_id,),
            )
        items = cur.fetchall()
        if not items:
            return _err(400, "購物車是空的")
        if item_ids and len(items) != len(set(item_ids)):
            return _err(400, "無效的商品選取")

        subtotal = 0.0
        for item in items:
            config = _cart_item_config(item)
            pricing = compute_order_pricing(cur, config, require_published=True)
            if not pricing.get("ready"):
                return _err(400, CART_UNAVAILABLE_CHECKOUT_MSG)
            subtotal += float(pricing.get("total") or 0)

        result, err = validate_coupon(cur, code=str(code), user_id=user_id, subtotal=subtotal)
        if err:
            return _err(400, err)
        assert result is not None
        return {
            "ok": True,
            "code": result["code"],
            "label": result.get("label"),
            "discountType": result["discountType"],
            "discountValue": result["discountValue"],
            "discountAmount": result["discountAmount"],
            "subtotal": result["subtotal"],
            "total": result["total"],
        }


def _request_is_shop_preview(request: Request, body: dict[str, Any] | None = None) -> bool:
    from app.controllers.htmx_common import form_bool, is_shop_preview

    if is_shop_preview(request):
        return True
    if body is not None and form_bool(body.get("preview")):
        return True
    return False


@router.post("/cart-checkout")
async def cart_checkout(request: Request) -> dict:
    import logging

    logger = logging.getLogger(__name__)
    try:
        return await _cart_checkout_impl(request)
    except HTTPException:
        raise
    except Exception:
        logger.exception("cart_checkout failed")
        return _err(500, "訂單建立失敗，請稍後再試或聯絡客服")


async def _cart_checkout_impl(request: Request, body: dict[str, Any] | None = None) -> dict:
    if body is None:
        raw = await request.json()
        body = raw if isinstance(raw, dict) else {}
    # Preview gate before auth — never create real orders from admin product preview.
    if _request_is_shop_preview(request, body):
        return _err(403, "預覽模式無法送出真實訂單")
    user_id = _user_id(request)
    item_ids = body.get("itemIds")
    coupon_code_raw = body.get("couponCode") or body.get("code") or ""

    with get_connection() as conn, conn.cursor() as cur:
        if item_ids:
            cur.execute(
                "select * from cart_items where user_id = %s and id = any(%s) order by created_at asc",
                (user_id, item_ids),
            )
        else:
            cur.execute(
                "select * from cart_items where user_id = %s order by created_at asc",
                (user_id,),
            )
        items = cur.fetchall()

        if not items:
            return _err(400, "cart is empty")
        if item_ids and len(items) != len(set(item_ids)):
            return _err(400, "invalid item selection")

        for item in items:
            annotate_cart_item(cur, item)
            if not item.get("available"):
                return _err(400, CART_UNAVAILABLE_CHECKOUT_MSG)

        profile = _profile(cur, user_id)
        need_bottle = cart_needs_collection_bottle(items)
        customer, customer_err = _validate_customer(
            body, profile, require_collection_bottle=need_bottle
        )
        if customer_err:
            return _err(400, customer_err)

        configs: list[dict[str, Any]] = []
        item_totals: list[float] = []
        for item in items:
            config = _cart_item_config(item)
            err = _validate_config(config)
            if err:
                return _err(400, err)
            chain_err = _clamp_pendant_chain_sell_mode(cur, config)
            if chain_err:
                return _err(400, chain_err)
            # Server reprice — never trust stored clientPricing / total_price.
            pricing = compute_order_pricing(cur, config, require_published=True)
            if not pricing.get("ready"):
                return _err(400, CART_UNAVAILABLE_CHECKOUT_MSG)
            config["clientPricing"] = pricing
            configs.append(config)
            item_totals.append(float(pricing.get("total") or 0))

    # Validation is done — now write. get_transaction() (autocommit off) makes
    # this all-or-nothing: if inserting order N of M raises, everything commits
    # or nothing does, instead of leaving earlier orders committed with their
    # cart items never cleared (which would duplicate orders on retry).
    # Coupon is re-validated inside the write transaction to avoid race on caps.
    with get_transaction() as conn, conn.cursor() as cur:
        coupon_result = None
        discount_shares = [0] * len(configs)
        if str(coupon_code_raw).strip():
            subtotal = sum(item_totals)
            coupon_result, coupon_err = validate_coupon(
                cur, code=str(coupon_code_raw), user_id=user_id, subtotal=subtotal, lock=True
            )
            if coupon_err:
                return _err(400, coupon_err)
            assert coupon_result is not None
            discount_shares = apply_discount_split(item_totals, int(coupon_result["discountAmount"]))

        order_numbers: list[str] = []
        redemption_rows: list[dict[str, Any]] = []
        coupon_code = coupon_result["code"] if coupon_result else None
        for i, config in enumerate(configs):
            inserted = _insert_order(
                cur,
                user_id,
                customer,
                config,
                coupon_code=coupon_code,
                discount_amount=float(discount_shares[i]),
            )
            order_numbers.append(inserted["order_number"])
            if coupon_result:
                redemption_rows.append(inserted)
        if coupon_result and redemption_rows:
            record_redemptions(
                cur,
                coupon_id=coupon_result["coupon"]["id"],
                user_id=user_id,
                code=coupon_result["code"],
                order_rows=redemption_rows,
            )
        checked_out = [str(i["id"]) for i in items]
        cur.execute(
            "delete from cart_items where id = any(%s)",
            (checked_out,),
        )

    return {"ok": True, "orderNumbers": order_numbers}
