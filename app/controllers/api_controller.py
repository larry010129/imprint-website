"""API routes — JSON endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.auth import get_user_id, is_admin
from app.bot_gold import fetch_bot_gold_quote
from app.catalog import build_catalog_response, fetch_catalog_rows, load_product_children
from app.orders import attach_order_display, attach_order_relations, hydrate_order
from app.database import get_connection
from app.schemas.gold_quote import GoldQuote

log = logging.getLogger(__name__)

router = APIRouter(tags=["api"])


def _err(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


@router.post("/contact")
async def submit_contact(request: Request) -> dict:
    body = await request.json()
    if not isinstance(body, dict):
        return _err(400, "invalid body")

    name = str(body.get("name") or "").strip()
    phone = str(body.get("phone") or "").strip()
    message = str(body.get("message") or "").strip()
    if not name or not phone or not message:
        return _err(400, "請填寫姓名、電話與您的需求")
    email = str(body.get("email") or "").strip() or None
    source_page = str(body.get("sourcePage") or "").strip() or None

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into contact_messages (name, phone, email, message, source_page)
            values (%s, %s, %s, %s, %s)
            """,
            (name, phone, email, message, source_page),
        )

    # Best-effort staff email — never fail the form if mail fails.
    try:
        from app.mail import notify_contact_message

        notify_contact_message(
            name=name,
            phone=phone,
            email=email,
            message=message,
            source_page=source_page,
        )
    except Exception:
        log.exception("contact notify email failed")

    return {"ok": True}


@router.post("/quote-request")
async def submit_quote_request(request: Request) -> dict:
    body = await request.json()
    if not isinstance(body, dict):
        return _err(400, "invalid body")

    name = str(body.get("name") or "").strip()
    phone = str(body.get("phone") or "").strip()
    if not name or not phone:
        return _err(400, "請填寫姓名與電話")
    email = str(body.get("email") or "").strip() or None
    series = str(body.get("series") or "").strip() or None
    product_type = str(body.get("productType") or "").strip() or None
    carat = str(body.get("carat") or "").strip() or None
    color = str(body.get("color") or "").strip() or None
    shape = str(body.get("shape") or "").strip() or None
    metal = str(body.get("metal") or "").strip() or None

    quantity_raw = body.get("quantity")
    quantity = int(quantity_raw) if isinstance(quantity_raw, (int, float)) and quantity_raw else 1
    price_raw = body.get("estimatedPrice")
    estimated_price = float(price_raw) if isinstance(price_raw, (int, float)) else None

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into quote_requests
              (name, phone, email, series, product_type, carat, color, shape, metal, quantity, estimated_price)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (name, phone, email, series, product_type, carat, color, shape, metal, quantity, estimated_price),
        )
    return {"ok": True}


@router.get("/bot-gold", response_model=GoldQuote)
async def bot_gold() -> JSONResponse:
    try:
        payload = await fetch_bot_gold_quote()
    except Exception as err:  # noqa: BLE001
        log.exception("bot-gold quote fetch failed")
        raise HTTPException(status_code=502, detail="金價暫時無法取得，請稍後再試") from err
    return JSONResponse(
        content=GoldQuote.model_validate(payload).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@router.post("/track-order")
async def track_order(request: Request) -> dict:
    body = await request.json()
    if not isinstance(body, dict):
        return _err(400, "invalid body")

    order_number = str(body.get("orderNumber") or "").strip()
    phone = str(body.get("phone") or "").strip()
    if not order_number or not phone:
        return _err(400, "請輸入訂單編號與電話")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select o.*
            from orders o
            join order_contacts oc on oc.order_id = o.id
            where o.order_number = %s and oc.customer_phone = %s
            limit 1
            """,
            (order_number, phone),
        )
        order = cur.fetchone()
        if not order:
            return {"rows": []}
        attach_order_relations(cur, [order])
        hydrate_order(order)
    return {"rows": [order]}


@router.get("/orders")
async def my_orders(request: Request) -> dict:
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not signed in")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select *
            from orders
            where user_id = %s
            order by created_at desc
            """,
            (user_id,),
        )
        orders = cur.fetchall()
        attach_order_display(cur, orders)
    return {"orders": orders}


@router.get("/catalog")
async def catalog(
    request: Request,
    category: str | None = Query(None),
    preview: int = Query(0),
) -> dict:
    include_drafts = False
    if preview:
        user_id = get_user_id(request)
        if user_id and is_admin(user_id):
            include_drafts = True

    with get_connection() as conn, conn.cursor() as cur:
        products = fetch_catalog_rows(cur, category=category, include_drafts=include_drafts)
        product_ids = [row["id"] for row in products]
        variants_by_product, images_by_product = load_product_children(cur, product_ids)
    return build_catalog_response(products, variants_by_product, images_by_product)
