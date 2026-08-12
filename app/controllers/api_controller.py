"""API routes — JSON endpoints."""

from __future__ import annotations

import logging
import os
import secrets

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.auth import (
    enforce_rate_limit,
    get_user_id,
    is_admin,
    log_admin_action,
    require_admin,
)
from app.auth_totp_service import step_up_from_body
from app.bot_gold import build_payload_from_cache
from app.gold_scrape_job import (
    persist_gold_price_cache,
    quote_fields_from_payload,
    scrape_and_persist_gold,
)
from app.catalog import (
    build_catalog_product,
    build_catalog_product_lite,
    build_catalog_response,
    count_catalog_rows,
    fetch_catalog_rows,
    fetch_product_row,
    get_public_catalog_cache,
    list_catalog_category_slugs,
    load_product_children,
    normalize_catalog_detail,
    set_public_catalog_cache,
)
from app.memorial_diamonds import list_tombstoned_style_keys, merge_memorial_diamond_catalog
from app.paging import page_meta, page_response, page_window_from_params, sql_count_total
from app.product_categories import build_category_meta, build_category_meta_from_rows, fetch_categories
from app.orders import (
    attach_order_display,
    attach_order_relations,
    enrich_member_order,
    hydrate_order,
    track_order_public_row,
)
from app.database import get_connection, get_transaction
from app.membership_config import default_config, load_config, save_config
from app.pricing import compute_order_pricing
from app.pricing_overrides import load_overrides, save_overrides
from app.schemas.gold_quote import GoldQuote

import json

log = logging.getLogger(__name__)

router = APIRouter(tags=["api"])

_TRACK_ORDER_PII_KEYS = frozenset(
    {
        "customer_name",
        "customer_email",
        "customer_phone",
        "shipping_name",
        "shipping_phone",
        "shipping_city",
        "shipping_postal",
        "shipping_address",
        "shipping_line",
        "collection_bottle_address",
        "collection_bottle_city",
        "collection_bottle_postal",
        "collection_bottle_line",
        "config_json",
        "pricing_json",
        "email",
        "phone",
        "user_id",
        "contacts",
        "items",
    }
)


def _err(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


def _gold_refresh_authorized(request: Request) -> bool:
    expected = (os.environ.get("GOLD_REFRESH_SECRET") or "").strip()
    if not expected:
        return False
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        return False
    token = auth[7:].strip()
    if not token:
        return False
    return secrets.compare_digest(token, expected)


def _featured_video_sync_authorized(request: Request) -> bool:
    expected = (os.environ.get("FEATURED_VIDEO_SYNC_SECRET") or "").strip()
    if not expected:
        return False
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        return False
    token = auth[7:].strip()
    if not token:
        return False
    return secrets.compare_digest(token, expected)


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


def _gold_cache_row() -> dict | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select * from gold_price_cache where id = 1")
        return cur.fetchone()


def _bot_gold_from_row(row: dict) -> JSONResponse:
    payload = build_payload_from_cache(row)
    return JSONResponse(
        content=GoldQuote.model_validate(payload).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@router.get("/bot-gold", response_model=GoldQuote)
async def bot_gold() -> JSONResponse:
    """Public gold quote — DB ``gold_price_cache`` only (no scrape on poll).

    Empty-cache bootstrap may scrape once under the shared lock, then persist.
    """
    row = _gold_cache_row()
    if row and float(row.get("xau_per_gram") or 0) > 0:
        return _bot_gold_from_row(row)
    try:
        payload = await scrape_and_persist_gold(force=True)
    except Exception as err:  # noqa: BLE001
        log.exception("bot-gold cache empty and live fetch failed")
        raise HTTPException(status_code=502, detail="金價暫時無法取得，請稍後再試") from err
    if payload is None:
        row = _gold_cache_row()
        if row and float(row.get("xau_per_gram") or 0) > 0:
            return _bot_gold_from_row(row)
        raise HTTPException(status_code=502, detail="金價暫時無法取得，請稍後再試")
    return JSONResponse(
        content=GoldQuote.model_validate(payload).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@router.post("/bot-gold/refresh", response_model=GoldQuote)
async def bot_gold_refresh(request: Request) -> JSONResponse:
    """Public button refresh — live scrape + persist. Rate-limited; no Bearer secret.

    Distinct from ``POST /api/gold-refresh`` (GHA-only, Bearer ``GOLD_REFRESH_SECRET``).
    Shared 90s min scrape interval with the lifespan loop.
    """
    if not enforce_rate_limit(request, action="bot-gold-refresh", limit=5, window_seconds=600):
        raise HTTPException(status_code=429, detail="請求過於頻繁，請稍後再試")
    try:
        payload = await scrape_and_persist_gold(force=True)
    except Exception as err:  # noqa: BLE001
        log.exception("bot-gold refresh scrape failed")
        raise HTTPException(status_code=502, detail="金價暫時無法取得，請稍後再試") from err
    if payload is None:
        row = _gold_cache_row()
        if row and float(row.get("xau_per_gram") or 0) > 0:
            return _bot_gold_from_row(row)
        raise HTTPException(status_code=502, detail="金價暫時無法取得，請稍後再試")
    out = dict(payload)
    out["refreshed"] = True
    if isinstance(out.get("quote"), dict):
        out["quote"] = dict(out["quote"])
        out["quote"]["is_stale"] = False
    return JSONResponse(
        content=GoldQuote.model_validate(out).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@router.post("/track-order")
async def track_order(request: Request) -> dict:
    if not enforce_rate_limit(request, action="track-order", limit=10, window_seconds=600):
        return _err(429, "請求過於頻繁，請稍後再試")

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
            select o.order_number, o.status, o.summary_zh, o.created_at, o.updated_at,
                   o.status_timestamps
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
    row = track_order_public_row(dict(order))
    for key in _TRACK_ORDER_PII_KEYS:
        row.pop(key, None)
    return {"rows": [row]}


@router.get("/orders")
def my_orders(request: Request) -> dict:
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not signed in")

    window = page_window_from_params(
        request.query_params, default_page_size=12, max_page_size=100
    )
    with get_connection() as conn, conn.cursor() as cur:
        total = sql_count_total(
            cur,
            "select count(*) as n from orders where user_id = %s",
            (user_id,),
        )
        cur.execute(
            """
            select *
            from orders
            where user_id = %s
            order by created_at desc
            limit %s offset %s
            """,
            (user_id, window.limit, window.offset),
        )
        orders = cur.fetchall()
        attach_order_display(cur, orders)
        for order in orders:
            enrich_member_order(order)
    out = page_response(
        orders,
        page=window.page,
        page_size=window.page_size,
        total=total,
        items_key="orders",
    )
    return out


@router.get("/catalog")
def catalog(
    request: Request,
    category: str | None = Query(None),
    preview: int = Query(0),
    detail: str = Query("lite"),
    page: int | None = Query(None),
    page_size: int | None = Query(None),
) -> JSONResponse:
    include_drafts = False
    if preview:
        user_id = get_user_id(request)
        if user_id and is_admin(user_id):
            include_drafts = True

    detail_mode = normalize_catalog_detail(detail)
    cat = (category or "").strip() or None
    # Always page: category-scoped when set; unscoped still capped (no full dump).
    window = page_window_from_params(
        {"page": page, "page_size": page_size},
    )
    cacheable = detail_mode == "lite" and not include_drafts
    cache_key = (cat or "", window.page, window.page_size)
    if cacheable:
        cached_payload = get_public_catalog_cache(cache_key)
        if cached_payload is not None:
            return JSONResponse(
                content=cached_payload,
                headers={"Cache-Control": "public, max-age=60"},
            )

    diamond_tombstones: set[str] = set()
    available_slugs: list[str] = []
    # Memorial diamond merge needs every DB overlay; page after merge (small set).
    page_sql = cat != "diamond"
    with get_connection() as conn, conn.cursor() as cur:
        total = count_catalog_rows(cur, category=cat, include_drafts=include_drafts)
        products = fetch_catalog_rows(
            cur,
            category=cat,
            include_drafts=include_drafts,
            limit=window.limit if page_sql else None,
            offset=window.offset if page_sql else None,
        )
        # Children only for fetched product IDs (page set, or full diamond set).
        product_ids = [row["id"] for row in products]
        variants_by_product, images_by_product = load_product_children(cur, product_ids)
        category_rows = fetch_categories(cur)
        cat_order = [row["slug"] for row in category_rows]
        cat_meta = build_category_meta_from_rows(category_rows)
        if cat is None:
            available_slugs = list_catalog_category_slugs(
                cur, include_drafts=include_drafts
            )
        if cat in (None, "diamond"):
            diamond_tombstones = list_tombstoned_style_keys(cur)
        diamond_overlay: list[dict] | None = None
        if cat is None:
            # Unscoped boot pages jewelry only — diamond rows are usually not in
            # the page, so the memorial merge would fall back to static matrix
            # images and ignore admin uploads. Fetch the (small) diamond set
            # explicitly so DB overlays always reach the merge.
            diamond_rows = fetch_catalog_rows(
                cur, category="diamond", include_drafts=include_drafts
            )
            d_variants, d_images = load_product_children(
                cur, [row["id"] for row in diamond_rows]
            )
            diamond_builder = (
                build_catalog_product
                if detail_mode == "full"
                else build_catalog_product_lite
            )
            diamond_overlay = [
                diamond_builder(
                    row,
                    d_variants.get(row["id"], []),
                    d_images.get(row["id"], []),
                )
                for row in diamond_rows
            ]
    payload = build_catalog_response(
        products,
        variants_by_product,
        images_by_product,
        category_order=cat_order,
        category_meta=cat_meta,
        detail=detail_mode,
    )
    categories = dict(payload.get("categories") or {})
    # Seed empty lists for nonempty categories missing from this page (boot tiles).
    if cat is None:
        for slug in available_slugs:
            categories.setdefault(slug, [])
        preferred = cat_order or list(categories.keys())
        order = [c for c in preferred if c in categories]
        order.extend(c for c in categories if c not in order)
        payload["categoryOrder"] = order
    # Always expose memorial diamond styles; DB overlays name/image/color.
    if cat in (None, "diamond"):
        merged_diamond = merge_memorial_diamond_catalog(
            diamond_overlay if cat is None else (categories.get("diamond") or []),
            excluded_style_keys=diamond_tombstones,
        )
        if cat == "diamond":
            total = len(merged_diamond)
            start = window.offset
            end = window.offset + window.limit
            categories["diamond"] = merged_diamond[start:end]
        else:
            # Unscoped boot: include full memorial list (small); jewelry stays paged.
            categories["diamond"] = merged_diamond
        order = list(payload.get("categoryOrder") or [])
        if "diamond" not in order:
            order = ["diamond"] + order
        else:
            order = ["diamond"] + [c for c in order if c != "diamond"]
        payload["categoryOrder"] = order
    payload["categories"] = categories
    payload.update(
        page_meta(page=window.page, page_size=window.page_size, total=total)
    )
    headers = {}
    if detail_mode == "lite" and not include_drafts:
        headers["Cache-Control"] = "public, max-age=60"
    encoded_payload = jsonable_encoder(payload)
    if cacheable:
        set_public_catalog_cache(cache_key, encoded_payload)
    return JSONResponse(content=encoded_payload, headers=headers)


@router.get("/catalog/product/{product_id}")
def catalog_product(
    request: Request,
    product_id: str,
    preview: int = Query(0),
) -> dict:
    """Full product payload for configure/quote (weights, images, prices)."""
    include_drafts = False
    if preview:
        user_id = get_user_id(request)
        if user_id and is_admin(user_id):
            include_drafts = True

    with get_connection() as conn, conn.cursor() as cur:
        product = fetch_product_row(cur, product_id, include_drafts=include_drafts)
        if not product:
            raise HTTPException(status_code=404, detail="product not found")
        variants_by_product, images_by_product = load_product_children(cur, [product["id"]])
        cat_meta = build_category_meta(cur)
        ring_meta = cat_meta.get("ring") or {}
        ring_cat_cfg = ring_meta.get("ringSizeConfig")
        if not isinstance(ring_cat_cfg, dict):
            ring_cat_cfg = None

    return {
        "product": build_catalog_product(
            product,
            variants_by_product.get(product["id"], []),
            images_by_product.get(product["id"], []),
            category_ring_size_config=ring_cat_cfg,
        )
    }


TESTIMONIALS_PUBLIC_CAP = 24


@router.get("/testimonials")
def public_testimonials() -> dict:
    """Home wall / public list — hard SQL cap (paging awkward for masonry wall)."""
    from app.content import (
        count_published_testimonials,
        fetch_published_testimonials,
    )
    from app.content_cache import (
        get_public_content_api_cache,
        set_public_content_api_cache,
    )
    from app.paging import page_response

    cached = get_public_content_api_cache("testimonials")
    if cached is not None:
        return cached

    with get_connection() as conn, conn.cursor() as cur:
        items = fetch_published_testimonials(
            cur, limit=TESTIMONIALS_PUBLIC_CAP, offset=0
        )
        total = count_published_testimonials(cur)
    payload = page_response(
        items,
        page=1,
        page_size=TESTIMONIALS_PUBLIC_CAP,
        total=total,
        items_key="testimonials",
    )
    set_public_content_api_cache("testimonials", payload)
    return payload


@router.get("/journal/posts")
def public_journal_posts(request: Request) -> dict:
    from app.content import (
        count_published_journal_posts,
        fetch_published_journal_posts,
    )
    from app.paging import page_response_from_window, page_window_from_params

    win = page_window_from_params(request.query_params, default_page_size=20)
    with get_connection() as conn, conn.cursor() as cur:
        posts = fetch_published_journal_posts(
            cur, limit=win.limit, offset=win.offset
        )
        total = count_published_journal_posts(cur)
    return page_response_from_window(
        posts, win, total=total, items_key="posts"
    )


@router.get("/cms/pages/{slug}")
async def cms_page_public(request: Request, slug: str) -> JSONResponse:
    """Public/admin JSON for Next SSR — page + ordered sections + full props (no HTML)."""
    from app.cms_boundary import is_reserved_cms_slug, normalize_cms_slug
    from app.cms_pages import fetch_public_cms_bundle

    clean = normalize_cms_slug(slug)
    if not clean or is_reserved_cms_slug(clean):
        return _err(404, "Not Found")

    preview = str(request.query_params.get("preview") or "") in {"1", "true", "yes"}
    admin_ok = is_admin(get_user_id(request))
    if preview and not admin_ok:
        return _err(404, "Not Found")

    try:
        with get_connection() as conn, conn.cursor() as cur:
            bundle = fetch_public_cms_bundle(
                cur, clean, visible_only=not preview
            )
    except Exception:
        return _err(404, "Not Found")

    if not bundle or not bundle.get("page"):
        return _err(404, "Not Found")
    page = bundle["page"]
    if page.get("status") != "published" and not (preview and admin_ok):
        return _err(404, "Not Found")

    sections = bundle.get("sections") or page.get("sections") or []
    page_out = dict(page)
    page_out["sections"] = sections
    page_out["cms_path"] = f"/p/{page_out.get('slug') or clean}"
    meta = dict(bundle.get("meta") or {})
    meta["preview"] = bool(preview)
    return JSONResponse(
        content={
            "page": page_out,
            "sections": sections,
            "faq": bundle.get("faq")
            or {"categories": [], "teaser": [], "items": []},
            "testimonials": bundle.get("testimonials") or [],
            "meta": meta,
        }
    )


@router.get("/faq")
def public_faq() -> dict:
    from app.content import fetch_faq_public

    with get_connection() as conn, conn.cursor() as cur:
        return fetch_faq_public(cur)


@router.get("/banners")
def public_banners() -> dict:
    from app.content import fetch_published_banners
    from app.content_cache import (
        get_public_content_api_cache,
        set_public_content_api_cache,
    )

    cached = get_public_content_api_cache("banners")
    if cached is not None:
        return cached

    with get_connection() as conn, conn.cursor() as cur:
        payload = {"banners": fetch_published_banners(cur)}
    set_public_content_api_cache("banners", payload)
    return payload


# ── pricing overrides (public read for the configurator, admin write) ───────

@router.get("/pricing")
def get_pricing() -> dict:
    with get_connection() as conn, conn.cursor() as cur:
        return {"overrides": load_overrides(cur)}


@router.post("/pricing")
async def post_pricing(request: Request) -> JSONResponse:
    user_id = require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        return _err(400, "invalid body")
    step = step_up_from_body(user_id, body)
    if step:
        status, message = step
        return _err(status, message)
    if body.get("reset"):
        overrides: dict = {}
    else:
        overrides = body.get("overrides")
        if not isinstance(overrides, dict):
            return _err(400, "overrides 必須是物件")
    with get_transaction() as conn, conn.cursor() as cur:
        saved = save_overrides(cur, overrides)
    return JSONResponse(content={"ok": True, "overrides": saved})


# ── membership ladder config (public read; admin write) ─────────────────────

@router.get("/membership-config")
def get_membership_config() -> dict:
    try:
        with get_connection() as conn, conn.cursor() as cur:
            return {"config": load_config(cur)}
    except Exception:
        log.exception("membership-config load failed; serving defaults")
        return {"config": default_config()}


@router.get("/admin/membership-config")
def admin_get_membership_config(request: Request) -> dict:
    require_admin(request)
    with get_connection() as conn, conn.cursor() as cur:
        return {"config": load_config(cur)}


@router.post("/admin/membership-config")
async def admin_post_membership_config(request: Request) -> JSONResponse:
    user_id = require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        return _err(400, "invalid body")
    step = step_up_from_body(user_id, body)
    if step:
        status, message = step
        return _err(status, message)
    if body.get("reset"):
        config = default_config()
    else:
        config = body.get("config")
        if not isinstance(config, dict):
            return _err(400, "config 必須是物件")
    try:
        with get_transaction() as conn, conn.cursor() as cur:
            saved = save_config(cur, config)
    except ValueError as exc:
        return _err(400, str(exc))
    return JSONResponse(content={"ok": True, "config": saved})


# ── shop price feed + live quote ────────────────────────────────────────────

@router.get("/prices")
def shop_prices() -> dict:
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

    from app.diamond_shapes import matrix_shapes_payload

    with get_connection() as conn, conn.cursor() as cur:
        overrides = load_overrides(cur)
        metal = get_metal_prices(cur)
        category_addons = {
            row["slug"]: int(row.get("addonPrice") or 0)
            for row in fetch_categories(cur)
        }
        matrix_shapes = matrix_shapes_payload(cur)
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
        "categoryAddonPrices": category_addons,
        "chinToGrams": CHIN_TO_GRAMS,
        "taxRate": ov_tax if isinstance(ov_tax, (int, float)) else TAX_RATE,
        # Shape / cut table for memorial diamond picker (grows with admin cuts).
        "diamondOptions": {"matrixShapes": matrix_shapes},
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
def gold_price() -> dict:
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


# Compat aliases for tests / callers that imported private helpers.
_quote_fields_from_payload = quote_fields_from_payload
_persist_gold_price_cache = persist_gold_price_cache


@router.post("/featured-video-sync")
async def featured_video_sync(request: Request) -> JSONResponse:
    """Optional force sync for ``featured-video.json`` (Bearer secret).

    Primary refresh is lazy TTL on home/about load. Same core as admin sync
    (RSS + embed-page filter → max 6). Requires
    ``Authorization: Bearer $FEATURED_VIDEO_SYNC_SECRET``.
    """
    if not _featured_video_sync_authorized(request):
        raise HTTPException(status_code=401, detail="unauthorized")
    if not enforce_rate_limit(
        request, action="featured-video-sync", limit=30, window_seconds=3600
    ):
        raise HTTPException(status_code=429, detail="請求過於頻繁，請稍後再試")

    from app.featured_video import IMPRINT_CHANNEL_URL, run_featured_video_channel_sync

    payload, error, channel_id = run_featured_video_channel_sync()
    if error or payload is None:
        raise HTTPException(status_code=502, detail=error or "同步失敗")

    log_admin_action(
        "cron",
        "featured_video_synced",
        {
            "count": len(payload.get("videos") or []),
            "channel_id": channel_id,
            "primary": (payload.get("videos") or [{}])[0].get("youtubeId"),
            "via": "featured_video_sync_secret",
        },
    )
    return JSONResponse(
        content={
            "ok": True,
            "channel_url": IMPRINT_CHANNEL_URL,
            **payload,
        }
    )


@router.post("/gold-refresh")
async def gold_refresh(request: Request) -> dict:
    """Persist gold_price_cache.

    Prefer an optional JSON body (same shape as ``data/gold-quote.json``) so
    GitHub Actions can push a quote it already scraped. Empty body keeps the
    legacy live re-scrape path. Requires ``Authorization: Bearer $GOLD_REFRESH_SECRET``.
    """
    if not _gold_refresh_authorized(request):
        raise HTTPException(status_code=401, detail="unauthorized")
    if not enforce_rate_limit(request, action="gold-refresh", limit=30, window_seconds=3600):
        raise HTTPException(status_code=429, detail="請求過於頻繁，請稍後再試")

    body: dict = {}
    try:
        raw = await request.json()
        if isinstance(raw, dict):
            body = raw
    except Exception:  # noqa: BLE001 — empty / non-JSON body = live scrape
        body = {}

    if body.get("quote") or body.get("metals"):
        xau, xag, xpt, stamp, source = quote_fields_from_payload(body)
        if xau <= 0:
            raise HTTPException(status_code=400, detail="金價資料無效")
        persist_gold_price_cache(
            xau=xau, xag=xag, xpt=xpt, bot_posted_at=stamp, source=source
        )
        return {
            "ok": True,
            "xau_per_gram": xau,
            "xag_per_gram": xag,
            "bot_posted_at": stamp,
            "source": source,
        }

    try:
        payload = await scrape_and_persist_gold(force=True)
    except Exception as err:  # noqa: BLE001
        log.exception("gold-refresh fetch failed")
        raise HTTPException(status_code=502, detail="金價暫時無法取得，請稍後再試") from err
    if payload is None:
        row = _gold_cache_row()
        if row and float(row.get("xau_per_gram") or 0) > 0:
            return {
                "ok": True,
                "xau_per_gram": float(row["xau_per_gram"]),
                "xag_per_gram": float(row["xag_per_gram"]),
                "bot_posted_at": row.get("bot_posted_at"),
                "throttled": True,
            }
        raise HTTPException(status_code=502, detail="金價暫時無法取得，請稍後再試")
    xau, xag, xpt, stamp, source = quote_fields_from_payload(payload)
    return {
        "ok": True,
        "xau_per_gram": xau,
        "xag_per_gram": xag,
        "bot_posted_at": stamp,
    }


# ── favorites (saved configurations, per signed-in user) ────────────────────

@router.get("/favorites")
def get_favorites(request: Request) -> dict:
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not signed in")
    window = page_window_from_params(
        request.query_params, default_page_size=20, max_page_size=100
    )
    with get_connection() as conn, conn.cursor() as cur:
        total = sql_count_total(
            cur,
            "select count(*) as n from favorite_items where user_id = %s",
            (user_id,),
        )
        cur.execute(
            """
            select * from favorite_items
            where user_id = %s
            order by created_at desc
            limit %s offset %s
            """,
            (user_id, window.limit, window.offset),
        )
        rows = cur.fetchall()
    for row in rows:
        if row.get("id") is not None:
            row["id"] = str(row["id"])
        created = row.get("created_at")
        if hasattr(created, "isoformat"):
            row["created_at"] = created.isoformat()
    return page_response(
        rows,
        page=window.page,
        page_size=window.page_size,
        total=total,
        items_key="favorites",
    )


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
def delete_favorite(request: Request) -> dict:
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
