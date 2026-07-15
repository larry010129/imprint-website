"""API routes — JSON endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.auth import get_user_id, is_admin
from app.bot_gold import fetch_bot_gold_quote
from app.catalog import build_catalog_response, fetch_catalog_rows, load_product_children
from app.database import get_connection
from app.schemas.gold_quote import GoldQuote

router = APIRouter(tags=["api"])


@router.get("/bot-gold", response_model=GoldQuote)
async def bot_gold() -> JSONResponse:
    try:
        payload = await fetch_bot_gold_quote()
    except Exception as err:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(err)) from err
    return JSONResponse(
        content=GoldQuote.model_validate(payload).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@router.get("/orders")
async def my_orders(request: Request) -> dict:
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not signed in")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select order_number, product_type, series, category, status, status_note,
                   total_price, created_at, updated_at
            from orders
            where user_id = %s
            order by created_at desc
            """,
            (user_id,),
        )
        orders = cur.fetchall()
    for row in orders:
        row["summary"] = row.get("product_type") or row.get("category") or "訂製品項"
        created = row.get("created_at")
        if created is not None:
            row["created_at_display"] = created.strftime("%Y/%m/%d")
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
