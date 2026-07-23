"""API routes — JSON endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.auth import enforce_rate_limit, get_user_id, is_admin
from app.bot_gold import FALLBACK_XAG, FALLBACK_XPT, fetch_bot_gold_quote
from app.catalog import build_catalog_response, fetch_catalog_rows, load_product_children
from app.orders import attach_order_display, attach_order_relations, hydrate_order
from app.database import get_connection, get_transaction
from app.pricing import compute_order_pricing
from app.pricing_overrides import load_overrides, save_overrides
from app.schemas.gold_quote import GoldQuote

import json

log = logging.getLogger(__name__)

router = APIRouter(tags=["api"])


def _err(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


@router.post("/contact")
async def submit_contact(request: Request) -> dict:
    if not enforce_rate_limit(request, action="contact", limit=5, window_seconds=600):
        return _err(429, "提交過於頻繁，請稍後再試")

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
    if not enforce_rate_limit(request, action="quote", limit=10, window_seconds=600):
        return _err(429, "提交過於頻繁，請稍後再試")

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


@router.get("/testimonials")
async def public_testimonials() -> dict:
    from app.content import fetch_published_testimonials

    with get_connection() as conn, conn.cursor() as cur:
        return {"testimonials": fetch_published_testimonials(cur)}


@router.get("/faq")
async def public_faq() -> dict:
    from app.content import fetch_faq_public

    with get_connection() as conn, conn.cursor() as cur:
        return fetch_faq_public(cur)


@router.get("/banners")
async def public_banners() -> dict:
    from app.content import fetch_published_banners

    with get_connection() as conn, conn.cursor() as cur:
        return {"banners": fetch_published_banners(cur)}


# ── pricing overrides (public read for the configurator, admin write) ───────

@router.get("/pricing")
async def get_pricing() -> dict:
    with get_connection() as conn, conn.cursor() as cur:
        return {"overrides": load_overrides(cur)}


@router.post("/pricing")
async def post_pricing(request: Request) -> JSONResponse:
    user_id = get_user_id(request)
    if not user_id or not is_admin(user_id):
        raise HTTPException(status_code=403, detail="admin access required")
    body = await request.json()
    if not isinstance(body, dict):
        return _err(400, "invalid body")
    if body.get("reset"):
        overrides: dict = {}
    else:
        overrides = body.get("overrides")
        if not isinstance(overrides, dict):
            return _err(400, "overrides 必須是物件")
    with get_transaction() as conn, conn.cursor() as cur:
        saved = save_overrides(cur, overrides)
    return JSONResponse(content={"ok": True, "overrides": saved})


# ── shop price feed + live quote ────────────────────────────────────────────

@router.get("/prices")
async def shop_prices() -> dict:
    """Server-authoritative pricing constants for the configurator (with admin
    overrides applied). Ring-size/diamond-option tables stay client-side; this
    only supplies the money-critical numbers so the browser never guesses."""
    from app.pricing import (
        CHIN_TO_GRAMS,
        LABOR_FEE_TWD,
        METAL_SYMBOL,
        PURITY_MULTIPLIER,
        TAX_RATE,
        _effective_tables,
        get_metal_prices,
    )

    with get_connection() as conn, conn.cursor() as cur:
        overrides = load_overrides(cur)
        metal = get_metal_prices(cur)
    per_gram = {
        gold: metal[METAL_SYMBOL[gold]] * PURITY_MULTIPLIER[gold]
        for gold in PURITY_MULTIPLIER
    }
    eff = _effective_tables(overrides)
    ov_tax = overrides.get("taxRate")
    return {
        "perGram": per_gram,
        "diamond": eff["white"],
        "diamondFancy": eff["fancy"],
        "laborFeeTwd": LABOR_FEE_TWD,
        "chinToGrams": CHIN_TO_GRAMS,
        "taxRate": ov_tax if isinstance(ov_tax, (int, float)) else TAX_RATE,
    }


@router.post("/quote")
async def shop_quote(request: Request, preview: int = Query(0)) -> dict:
    body = await request.json()
    if not isinstance(body, dict):
        return _err(400, "invalid body")
    require_published = True
    if preview:
        user_id = get_user_id(request)
        if user_id and is_admin(user_id):
            require_published = False
    with get_connection() as conn, conn.cursor() as cur:
        pricing = compute_order_pricing(cur, body, require_published=require_published)
    return {"pricing": pricing, **pricing}


# ── live gold price (reads gold_price_cache; refresh re-scrapes BOT) ─────────

@router.get("/gold-price")
async def gold_price() -> dict:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select * from gold_price_cache where id = 1")
        row = cur.fetchone()
    if not row:
        return {"price": None}
    fetched = row.get("fetched_at")
    return {
        "price": {
            "xau_per_gram": float(row["xau_per_gram"]),
            "xpt_per_gram": float(row["xpt_per_gram"]),
            "xag_per_gram": float(row["xag_per_gram"]),
            "bot_posted_at": row.get("bot_posted_at"),
            "fetched_at": fetched.isoformat() if hasattr(fetched, "isoformat") else fetched,
        }
    }


@router.post("/gold-refresh")
async def gold_refresh() -> dict:
    """Re-scrape the BOT gold quote and persist it. fetch_bot_gold_quote caches
    successful fetches for a few minutes, so this can't hammer the upstream."""
    try:
        payload = await fetch_bot_gold_quote()
    except Exception as err:  # noqa: BLE001
        log.exception("gold-refresh fetch failed")
        raise HTTPException(status_code=502, detail="金價暫時無法取得，請稍後再試") from err
    quote = payload.get("quote") or {}
    xau = float(quote.get("sell") or 0)
    if xau <= 0:
        raise HTTPException(status_code=502, detail="金價資料無效")
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into gold_price_cache (id, xau_per_gram, xpt_per_gram, xag_per_gram, bot_posted_at, source, fetched_at)
            values (1, %s, %s, %s, %s, 'bot', now())
            on conflict (id) do update set
              xau_per_gram = excluded.xau_per_gram,
              bot_posted_at = excluded.bot_posted_at,
              fetched_at = now()
            """,
            (xau, FALLBACK_XPT, FALLBACK_XAG, quote.get("bot_posted_at")),
        )
    return {"ok": True, "xau_per_gram": xau, "bot_posted_at": quote.get("bot_posted_at")}


# ── favorites (saved configurations, per signed-in user) ────────────────────

@router.get("/favorites")
async def get_favorites(request: Request) -> dict:
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not signed in")
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select * from favorite_items where user_id = %s order by created_at desc",
            (user_id,),
        )
        rows = cur.fetchall()
    for row in rows:
        if row.get("id") is not None:
            row["id"] = str(row["id"])
        created = row.get("created_at")
        if hasattr(created, "isoformat"):
            row["created_at"] = created.isoformat()
    return {"favorites": rows}


@router.post("/favorites")
async def add_favorite(request: Request) -> JSONResponse:
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not signed in")
    body = await request.json()
    if not isinstance(body, dict):
        return _err(400, "invalid body")
    category = str(body.get("category") or "").strip()
    style_type = str(body.get("type") or body.get("style_type") or "").strip()
    if not category or not style_type:
        return _err(400, "缺少商品類別")
    summary = str(body.get("summaryZh") or body.get("summary_zh") or "").strip() or None
    config_json = json.loads(json.dumps(body, default=str))
    from app.orders import is_uuid

    product_id = body.get("type") if is_uuid(body.get("type")) else None
    from psycopg.types.json import Jsonb

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into favorite_items (user_id, product_id, category, style_type, config_json, summary_zh)
            values (%s, %s, %s, %s, %s, %s)
            returning id
            """,
            (user_id, product_id, category, style_type, Jsonb(config_json), summary),
        )
        row = cur.fetchone()
    return JSONResponse(content={"ok": True, "id": str(row["id"])})


@router.delete("/favorites")
async def delete_favorite(request: Request) -> dict:
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not signed in")
    fav_id = request.query_params.get("id")
    if not fav_id:
        return _err(400, "missing id")
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "delete from favorite_items where id = %s and user_id = %s",
            (fav_id, user_id),
        )
    return {"ok": True}
