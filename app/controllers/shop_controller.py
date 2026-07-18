"""Shop cart + checkout for the FastAPI app."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from psycopg.types.json import Jsonb

from app.auth import get_user_id
from app.database import get_connection, get_transaction
from app.image_urls import is_uuid
from app.pricing import compute_order_pricing

router = APIRouter(tags=["shop"])


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
    for key in ("category", "type", "gold", "carat"):
        if not body.get(key):
            return f"缺少欄位：{key}"
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


def _validate_customer(body: dict[str, Any], profile: dict[str, Any] | None) -> tuple[dict[str, Any], str | None]:
    name = str(body.get("customerName") or (profile or {}).get("full_name") or "").strip()
    phone = str(body.get("customerPhone") or (profile or {}).get("phone") or "").strip()
    email = str(body.get("customerEmail") or (profile or {}).get("email") or "").strip() or None
    method = str(body.get("fulfillmentMethod") or "pickup").strip()
    if method not in ("pickup", "delivery"):
        method = "pickup"
    address = str(body.get("shippingAddress") or "").strip() or None
    city = str(body.get("shippingCity") or "").strip() or None
    postal = str(body.get("shippingPostal") or "").strip() or None
    note = str(body.get("orderNote") or "").strip() or None

    if not name:
        return {}, "請填寫收件人姓名"
    if not phone:
        return {}, "請填寫聯絡電話"
    if method == "delivery" and not (address and city and postal):
        return {}, "請填寫完整的收件地址"

    return {
        "name": name,
        "phone": phone,
        "email": email,
        "fulfillmentMethod": method,
        "shippingAddress": address,
        "shippingCity": city,
        "shippingPostal": postal,
        "orderNote": note,
    }, None


def _insert_order(cur, user_id: str, customer: dict[str, Any], config: dict[str, Any]) -> str:
    pricing = _pricing(config)
    product_type = config.get("summaryZh") or config.get("type")
    product_id = config.get("type") if is_uuid(config.get("type")) else None

    cur.execute(
        """
        insert into orders (
          user_id, product_id, customer_name, customer_phone, customer_email,
          product_type, category, carat, gold_purity, color,
          diamond_kind, fancy_color, stone_count, diamond_shape,
          weight_grams, ring_size, engraving_band, engraving_girdle,
          include_chain, chain_gold, chain_color, chain_length_cm,
          diamond_price_twd, taijin_price_twd, labor_price_twd, tax_amount_twd,
          total_price, gold_rate_per_gram, price_source,
          fulfillment_method, shipping_address, shipping_city, shipping_postal, order_note,
          status
        ) values (
          %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s,
          %s, %s, %s, %s,
          %s, %s, %s, %s,
          %s, %s, %s, %s,
          %s, %s, %s, %s,
          %s, %s, %s,
          %s, %s, %s, %s, %s,
          'received'
        )
        returning order_number
        """,
        (
            user_id,
            product_id,
            customer["name"],
            customer["phone"],
            customer["email"],
            product_type,
            config.get("category"),
            config.get("carat"),
            config.get("gold"),
            config.get("color"),
            config.get("diamondKind") or "white",
            config.get("fancyColor"),
            config.get("stoneCount"),
            config.get("diamondShape") or "round",
            pricing.get("weightGrams"),
            config.get("ringSize"),
            config.get("engravingBand"),
            config.get("engravingGirdle"),
            bool(config.get("includeChain")),
            config.get("chainGold"),
            config.get("chainColor"),
            config.get("chainLength") if config.get("category") != "chain" else config.get("lengthCm"),
            pricing.get("diamondPrice"),
            pricing.get("taijinPrice"),
            pricing.get("laborPrice"),
            pricing.get("taxAmount"),
            pricing.get("total"),
            pricing.get("goldRatePerGram"),
            pricing.get("priceSource") or "client",
            customer["fulfillmentMethod"],
            customer["shippingAddress"],
            customer["shippingCity"],
            customer["shippingPostal"],
            customer["orderNote"],
        ),
    )
    row = cur.fetchone()
    return row["order_number"]


@router.get("/cart")
async def get_cart(request: Request) -> dict:
    user_id = _user_id(request)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select * from cart_items where user_id = %s order by created_at asc",
            (user_id,),
        )
        items = cur.fetchall()
    return {"items": items}


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


@router.api_route("/cart-item", methods=["GET", "DELETE"])
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

    config = item.get("config_json") or {}
    pricing = _pricing(config)
    breakdown = {
        "diamondPrice": pricing.get("diamondPrice"),
        "taijinPrice": pricing.get("taijinPrice"),
        "laborPrice": pricing.get("laborPrice"),
        "chainPrice": pricing.get("chainPrice"),
        "taxAmount": pricing.get("taxAmount"),
        "total": pricing.get("total") or item.get("total_price"),
    }
    return {"item": item, "breakdown": breakdown, "taxRate": 0.05}


@router.post("/cart-checkout")
async def cart_checkout(request: Request) -> dict:
    user_id = _user_id(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
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
            return _err(400, "cart is empty")
        if item_ids and len(items) != len(set(item_ids)):
            return _err(400, "invalid item selection")

        profile = _profile(cur, user_id)
        customer, customer_err = _validate_customer(body, profile)
        if customer_err:
            return _err(400, customer_err)

        configs: list[dict[str, Any]] = []
        for item in items:
            config = item.get("config_json") or {}
            if not isinstance(config, dict):
                config = {}
            err = _validate_config(config)
            if err:
                return _err(400, err)
            configs.append(config)

    # Validation is done — now write. get_transaction() (autocommit off) makes
    # this all-or-nothing: if inserting order N of M raises, everything commits
    # or nothing does, instead of leaving earlier orders committed with their
    # cart items never cleared (which would duplicate orders on retry).
    with get_transaction() as conn, conn.cursor() as cur:
        order_numbers = [_insert_order(cur, user_id, customer, config) for config in configs]
        checked_out = [str(i["id"]) for i in items]
        cur.execute(
            "delete from cart_items where id = any(%s)",
            (checked_out,),
        )

    return {"ok": True, "orderNumbers": order_numbers}
