"""Admin API — dashboard, leads, orders."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from psycopg.types.json import Jsonb

from app.account_delete import delete_blocked_reason, hard_delete_user
from app.admin_dashboard import (
    DASHBOARD_ORDER_HARD_LIMIT,
    build_dashboard_csv,
    build_dashboard_payload,
    dashboard_fetch_bounds,
    normalize_range,
)
from app.admin_products import (
    CATEGORY_LABELS,
    append_product_image,
    as_jsonb,
    delete_product_image_urls_if_unreferenced,
    ensure_product_chain_type_column,
    ensure_product_length_weights_column,
    ensure_product_sell_mode_columns,
    ensure_product_side_stone_total_column,
    first_published_at_value,
    is_auto_stock_product_image,
    publish_readiness,
    purge_auto_stock_product_images,
    resolve_product_folder,
    save_product_children,
    serialize_product_row,
    valid_image_color,
    validate_product_fields,
)
from app.chain_catalog import chain_catalog_for_admin
from app.auth import (
    generate_invite_code,
    get_user_id,
    hash_password,
    is_admin,
    log_admin_action,
    require_admin,
)
from app.auth_totp_service import step_up_from_body, verify_step_up_password
from app.catalog import load_product_children
from app.product_categories import category_labels, create_category, delete_category, fetch_categories, update_category_thumb, valid_category_slugs
from config.settings import settings
from app.database import get_connection, get_transaction
from app.orders import (
    attach_order_display,
    attach_order_relations,
    hydrate_order,
    merge_status_timestamps,
)

router = APIRouter(prefix="/admin", tags=["admin"])

ORDER_STATUSES = {
    "received",
    "order_confirming",
    "dna_lab",
    "deposit_confirmed",
    "in_production",
    "quality_check",
    "shipped",
    "completed",
    "cancelled",
}


def _order_summary(order: dict) -> str:
    parts = [order.get("series"), order.get("product_type")]
    summary = " · ".join(part for part in parts if part)
    return summary or order.get("order_number") or "訂單"


def _notify_order_cancelled(cur, order: dict, reason: str) -> None:
    user_id = order.get("user_id")
    if not user_id:
        return
    message = f"您的訂單 {order['order_number']} 已取消：{reason}"
    cur.execute(
        """
        insert into user_notifications (user_id, kind, message, order_id, order_summary)
        values (%s, 'order_cancelled', %s, %s, %s)
        """,
        (user_id, message, order["id"], _order_summary(order)),
    )


def _require_admin(request: Request) -> str:
    return require_admin(request)


def _step_up_response(admin_id: str, body: dict | None) -> JSONResponse | None:
    step = step_up_from_body(admin_id, body)
    if not step:
        return None
    status, message = step
    return JSONResponse(status_code=status, content={"error": message})


def _fetch_orders(
    cur,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    hard_limit: int = DASHBOARD_ORDER_HARD_LIMIT,
) -> list[dict]:
    """Load dashboard orders inside [since, until). Never unbounded full-table."""
    if since is None or until is None:
        raise ValueError("_fetch_orders requires since/until bounds")
    limit = max(1, int(hard_limit))
    cur.execute(
        """
        select id, order_number, summary_zh, total_price, created_at, status
        from orders
        where created_at >= %s and created_at < %s
        order by created_at asc
        limit %s
        """,
        (since, until, limit),
    )
    rows = cur.fetchall()
    attach_order_relations(cur, rows)
    for row in rows:
        hydrate_order(row)
    return rows


def _lead_counts(cur) -> tuple[int, int, int, int]:
    cur.execute("select count(*) as c from contact_messages where status = 'new'")
    new_messages = int(cur.fetchone()["c"])
    cur.execute("select count(*) as c from quote_requests where status = 'pending'")
    pending_quotes = int(cur.fetchone()["c"])
    cur.execute("select count(*) as c from orders where status <> 'completed'")
    active_orders = int(cur.fetchone()["c"])
    cur.execute("select count(*) as c from orders where status = 'completed'")
    completed_orders = int(cur.fetchone()["c"])
    return new_messages, pending_quotes, active_orders, completed_orders


def _attach_order_images(cur, orders: list[dict]) -> None:
    attach_order_display(cur, orders)


def _dashboard_query_params(
    granularity: str | None = None,
    period: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    return normalize_range(
        granularity=granularity,
        period=period,
        start=start,
        end=end,
    )


@router.get("/dashboard")
async def dashboard(
    request: Request,
    granularity: str | None = Query(None),
    period: str | None = Query(None),
    start: str | None = Query(None),
    end: str | None = Query(None),
) -> dict:
    _require_admin(request)
    cfg = _dashboard_query_params(granularity, period, start, end)
    since, until = dashboard_fetch_bounds(cfg)

    with get_connection() as conn, conn.cursor() as cur:
        orders = _fetch_orders(cur, since=since, until=until)
        new_messages, pending_quotes, active_orders, completed_orders = _lead_counts(cur)

    payload = build_dashboard_payload(orders, cfg)
    payload.update(
        {
            "newMessages": new_messages,
            "pendingQuotes": pending_quotes,
            "activeOrders": active_orders,
            "completedOrders": completed_orders,
        }
    )
    return payload


@router.get("/dashboard/export")
async def dashboard_export(
    request: Request,
    granularity: str | None = Query(None),
    period: str | None = Query(None),
    start: str | None = Query(None),
    end: str | None = Query(None),
) -> Response:
    _require_admin(request)
    cfg = _dashboard_query_params(granularity, period, start, end)
    since, until = dashboard_fetch_bounds(cfg)

    with get_connection() as conn, conn.cursor() as cur:
        orders = _fetch_orders(cur, since=since, until=until)

    csv_body, slug = build_dashboard_csv(orders, cfg)
    filename = f"orders-{slug}.csv"
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/leads")
async def leads_get(request: Request) -> dict:
    _require_admin(request)

    def _ser_lead(row: dict) -> dict:
        out = dict(row)
        if out.get("id") is not None:
            out["id"] = str(out["id"])
        created = out.get("created_at")
        if hasattr(created, "isoformat"):
            out["created_at"] = created.isoformat()
        price = out.get("estimated_price")
        if price is not None:
            try:
                out["estimated_price"] = float(price)
            except (TypeError, ValueError):
                pass
        return out

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select * from contact_messages order by created_at desc limit 50")
        messages = [_ser_lead(r) for r in cur.fetchall()]
        cur.execute("select * from quote_requests order by created_at desc limit 50")
        quotes = [_ser_lead(r) for r in cur.fetchall()]
    return {"messages": messages, "quotes": quotes}


@router.post("/leads")
async def leads_mark_done(request: Request) -> JSONResponse:
    _require_admin(request)
    body = await request.json()
    lead_type = body.get("type")
    lead_id = body.get("id")
    if not lead_id or lead_type not in ("message", "quote"):
        return JSONResponse(status_code=400, content={"error": "invalid lead reference"})

    with get_connection() as conn, conn.cursor() as cur:
        if lead_type == "message":
            cur.execute(
                "update contact_messages set status = 'replied' where id = %s",
                (lead_id,),
            )
        else:
            cur.execute(
                "update quote_requests set status = 'contacted' where id = %s",
                (lead_id,),
            )
    return JSONResponse(content={"ok": True})


@router.get("/orders")
async def orders_list(request: Request, q: str | None = Query(None)) -> dict:
    _require_admin(request)
    search = (q or "").strip()

    with get_connection() as conn, conn.cursor() as cur:
        if search:
            like = f"%{search}%"
            cur.execute(
                """
                select distinct o.*
                from orders o
                left join order_items oi on oi.order_id = o.id
                left join order_contacts oc on oc.order_id = o.id
                where o.order_number ilike %s
                   or o.status ilike %s
                   or o.summary_zh ilike %s
                   or oc.customer_name ilike %s
                   or oc.customer_phone ilike %s
                   or oi.summary_zh ilike %s
                order by o.created_at desc
                limit 200
                """,
                (like, like, like, like, like, like),
            )
        else:
            cur.execute("select * from orders order by created_at desc limit 100")
        orders = cur.fetchall()
        attach_order_display(cur, orders)

    return {"orders": orders}


@router.post("/orders")
async def orders_create(request: Request) -> JSONResponse:
    _require_admin(request)
    body = await request.json()
    customer_name = (body.get("customerName") or "").strip()
    customer_phone = (body.get("customerPhone") or "").strip()
    customer_email = (body.get("customerEmail") or "").strip() or None
    series = (body.get("series") or "").strip() or None
    product_type = (body.get("productType") or "").strip() or None

    if not customer_name or not customer_phone:
        return JSONResponse(status_code=400, content={"error": "請填寫客戶姓名與電話"})

    with get_connection() as conn, conn.cursor() as cur:
        config = {
            "series": series,
            "summaryZh": product_type or "訂製品項",
            "type": product_type or "",
        }
        cur.execute(
            """
            insert into orders (summary_zh)
            values (%s)
            returning id, order_number
            """,
            (product_type or series or "訂製品項",),
        )
        order = cur.fetchone()
        cur.execute(
            """
            insert into order_contacts (order_id, customer_name, customer_phone, customer_email)
            values (%s, %s, %s, %s)
            """,
            (order["id"], customer_name, customer_phone, customer_email),
        )
        cur.execute(
            """
            insert into order_items (order_id, config_json, summary_zh)
            values (%s, %s, %s)
            """,
            (order["id"], Jsonb(config), product_type or series or "訂製品項"),
        )
        cur.execute(
            """
            insert into order_fulfillment (order_id, fulfillment_method)
            values (%s, 'pickup')
            """,
            (order["id"],),
        )

    return JSONResponse(content={"orderNumber": order["order_number"]})


@router.post("/order-update")
async def order_update(request: Request) -> JSONResponse:
    _require_admin(request)
    body = await request.json()
    order_id = body.get("id")
    status = body.get("status")
    status_note = (body.get("statusNote") or "").strip() or None

    if not order_id or not status:
        return JSONResponse(status_code=400, content={"error": "missing id/status"})
    if status not in ORDER_STATUSES:
        return JSONResponse(status_code=400, content={"error": "invalid status"})

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select status, status_timestamps from orders where id = %s",
            (order_id,),
        )
        order = cur.fetchone()
        if not order:
            return JSONResponse(status_code=404, content={"error": "order not found"})
        stamps = merge_status_timestamps(
            order.get("status_timestamps"),
            order.get("status"),
            status,
            datetime.now(timezone.utc),
        )
        cur.execute(
            """
            update orders
            set status = %s, status_note = %s, updated_at = now(),
                status_timestamps = %s
            where id = %s
            """,
            (status, status_note, Jsonb(stamps), order_id),
        )

    return JSONResponse(content={"ok": True})


@router.post("/order-cancel")
async def order_cancel(request: Request) -> JSONResponse:
    admin_id = _require_admin(request)
    body = await request.json()
    step_resp = _step_up_response(admin_id, body if isinstance(body, dict) else {})
    if step_resp:
        return step_resp
    order_id = body.get("id")
    reason = (body.get("reason") or "").strip()
    if not order_id or not reason:
        return JSONResponse(status_code=400, content={"error": "請選擇或填寫取消原因"})

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select * from orders where id = %s", (order_id,))
        order = cur.fetchone()
        if not order:
            return JSONResponse(status_code=404, content={"error": "order not found"})
        attach_order_relations(cur, [order])
        hydrate_order(order)
        if order.get("status") == "cancelled":
            return JSONResponse(status_code=400, content={"error": "訂單已取消"})

        cur.execute(
            """
            update orders
            set status = 'cancelled', cancel_reason = %s, status_note = %s, updated_at = now()
            where id = %s
            """,
            (reason, reason, order_id),
        )
        _notify_order_cancelled(cur, order, reason)

    return JSONResponse(content={"ok": True})


@router.post("/order-delete")
async def order_delete(request: Request) -> JSONResponse:
    """Legacy alias — cancels order (requires reason)."""
    return await order_cancel(request)


@router.post("/orders-bulk-update")
async def orders_bulk_update(request: Request) -> JSONResponse:
    admin_id = _require_admin(request)
    body = await request.json()
    step_resp = _step_up_response(admin_id, body if isinstance(body, dict) else {})
    if step_resp:
        return step_resp
    ids = body.get("ids") or []
    status = body.get("status")
    cancel_reason = (body.get("cancelReason") or "").strip() or None

    if not ids or not status:
        return JSONResponse(status_code=400, content={"error": "missing ids/status"})
    if status not in ORDER_STATUSES:
        return JSONResponse(status_code=400, content={"error": "invalid status"})
    if status == "cancelled" and not cancel_reason:
        return JSONResponse(status_code=400, content={"error": "請選擇或填寫取消原因"})

    updated = 0
    with get_transaction() as conn, conn.cursor() as cur:
        for order_id in ids:
            cur.execute("select * from orders where id = %s", (order_id,))
            order = cur.fetchone()
            if not order:
                continue
            attach_order_relations(cur, [order])
            hydrate_order(order)
            if order.get("status") == "cancelled" and status == "cancelled":
                continue
            if status == "cancelled":
                cur.execute(
                    """
                    update orders
                    set status = %s, cancel_reason = %s, status_note = %s, updated_at = now()
                    where id = %s
                    """,
                    (status, cancel_reason, cancel_reason, order_id),
                )
                _notify_order_cancelled(cur, order, cancel_reason or "")
            else:
                stamps = merge_status_timestamps(
                    order.get("status_timestamps"),
                    order.get("status"),
                    status,
                    datetime.now(timezone.utc),
                )
                cur.execute(
                    """
                    update orders
                    set status = %s, updated_at = now(), status_timestamps = %s
                    where id = %s
                    """,
                    (status, Jsonb(stamps), order_id),
                )
            updated += 1

    return JSONResponse(content={"ok": True, "updated": updated})


_ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
_ALLOWED_IMAGE_MIME = {"image/png", "image/jpeg", "image/webp"}
_MAX_IMAGE_BYTES = 1 * 1024 * 1024


def _image_signature_matches(data: bytes, ext: str) -> bool:
    if ext == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if ext == ".webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


def _image_upload_error(file: UploadFile, data: bytes, ext: str) -> str | None:
    """Reject non-image MIME/ext, oversize, or magic-byte mismatch."""
    if ext not in _ALLOWED_IMAGE_EXT:
        return "僅支援 PNG / JPG / JPEG / WEBP"
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct and ct not in _ALLOWED_IMAGE_MIME and ct not in {
        "application/octet-stream",
        "binary/octet-stream",
    }:
        return "僅支援 PNG / JPG / JPEG / WEBP"
    if not data:
        return "empty file"
    if len(data) > _MAX_IMAGE_BYTES:
        return "圖片需小於 1MB"
    if not _image_signature_matches(data, ext):
        return "檔案內容與副檔名不符"
    return None


def _storage_upload(kind: str, name: str, data: bytes, ext: str) -> tuple[str | None, str | None]:
    from app.storage import StorageNotConfiguredError, StorageUploadError, upload_image

    try:
        # Upsert: category thumbs reuse categories/{slug}{ext}; overwrite on re-upload.
        return upload_image(kind, name, data, ext, upsert=True), None
    except StorageNotConfiguredError as exc:
        return None, str(exc)
    except StorageUploadError as exc:
        return None, str(exc)
    except Exception as exc:
        # httpx/network errors must not become opaque HTTP 500 for admin UI.
        msg = str(exc).strip().split("\n", 1)[0][:200]
        return None, msg or "Storage upload failed"


@router.post("/product-upload")
async def product_upload(
    request: Request,
    file: UploadFile = File(...),
    product_id: str | None = Form(None),
    color: str | None = Form(None),
) -> JSONResponse:
    """Upload to Supabase Storage; when product_id+color given, also insert product_images row."""
    _require_admin(request)
    if not file.filename:
        return JSONResponse(status_code=400, content={"error": "missing file"})

    ext = Path(file.filename).suffix.lower()
    data = await file.read()
    err = _image_upload_error(file, data, ext)
    if err:
        return JSONResponse(status_code=400, content={"error": err})

    pid = (product_id or "").strip()
    slot = (color or "").strip().lower()
    if slot and not valid_image_color(slot):
        return JSONResponse(status_code=400, content={"error": "圖片選項代碼無效"})

    from app.storage import product_folder_segment, product_upload_relative_path

    name = f"{uuid.uuid4().hex}{ext}"
    folder = None
    if pid:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select name_en, name_zh from products where id = %s", (pid,)
            )
            prow = cur.fetchone()
            if prow:
                folder = resolve_product_folder(
                    cur, pid, prow.get("name_en"), prow.get("name_zh")
                )
            else:
                folder = product_folder_segment(None, pid)
    rel = product_upload_relative_path(
        name, folder=folder, color_slot=slot or None
    )
    url, upload_err = _storage_upload("products", rel, data, ext)
    if upload_err:
        return JSONResponse(status_code=503, content={"error": upload_err})

    image_row = None
    if pid and slot:
        with get_transaction() as conn, conn.cursor() as cur:
            image_row = append_product_image(cur, pid, slot, url)
        if image_row and image_row.get("id") is not None:
            image_row["id"] = str(image_row["id"])
        if image_row and image_row.get("product_id") is not None:
            image_row["product_id"] = str(image_row["product_id"])

    payload: dict = {"url": url}
    if image_row:
        payload["image"] = image_row
    return JSONResponse(content=payload)


@router.post("/product-category")
async def product_category_create(request: Request) -> JSONResponse:
    _require_admin(request)
    body = await request.json()
    label_zh = body.get("labelZh") or body.get("label_zh") or ""
    label_en = body.get("labelEn") or body.get("label_en")
    with get_transaction() as conn, conn.cursor() as cur:
        category, error = create_category(cur, label_zh=label_zh, label_en=label_en)
    if error:
        return JSONResponse(status_code=400, content={"error": error})
    return JSONResponse(content={"category": category})


@router.delete("/product-category/{slug}")
async def product_category_delete(request: Request, slug: str) -> JSONResponse:
    _require_admin(request)
    with get_transaction() as conn, conn.cursor() as cur:
        ok, error = delete_category(cur, slug)
    if error:
        return JSONResponse(status_code=400, content={"error": error})
    return JSONResponse(content={"ok": ok})


@router.post("/product-category-upload")
async def product_category_upload(
    request: Request,
    file: UploadFile = File(...),
    slug: str = Query(...),
) -> JSONResponse:
    _require_admin(request)
    slug = (slug or "").strip()
    if not slug:
        return JSONResponse(status_code=400, content={"error": "missing slug"})
    if not file.filename:
        return JSONResponse(status_code=400, content={"error": "missing file"})

    ext = Path(file.filename).suffix.lower()
    data = await file.read()
    err = _image_upload_error(file, data, ext)
    if err:
        return JSONResponse(status_code=400, content={"error": err})

    name = f"{slug}{ext}"
    url, upload_err = _storage_upload("categories", name, data, ext)
    if upload_err:
        return JSONResponse(status_code=503, content={"error": upload_err})

    category: dict | None = None
    error: str | None = None
    try:
        with get_transaction() as conn, conn.cursor() as cur:
            category, error = update_category_thumb(cur, slug, url)
    except Exception as exc:
        msg = str(exc).strip().split("\n", 1)[0][:200]
        return JSONResponse(
            status_code=500,
            content={"error": f"更新品項圖失敗：{msg}" if msg else "更新品項圖失敗"},
        )
    if error:
        return JSONResponse(status_code=400, content={"error": error})
    return JSONResponse(content={"url": url, "category": category})


def _products_with_children(cur) -> list[dict]:
    ensure_product_side_stone_total_column(cur)
    cur.execute("select * from products order by sort_order, created_at desc")
    rows = cur.fetchall()
    product_ids = [row["id"] for row in rows]
    variants_by_product, images_by_product = load_product_children(cur, product_ids)
    products: list[dict] = []
    for row in rows:
        pid = row["id"]
        product = serialize_product_row(row)
        product["variants"] = variants_by_product.get(pid, [])
        # Never surface invented shop-product letter SKUs in admin editor.
        product["images"] = [
            image
            for image in images_by_product.get(pid, [])
            if not is_auto_stock_product_image(image.get("file_path"))
        ]
        for variant in product["variants"]:
            if variant.get("id") is not None:
                variant["id"] = str(variant["id"])
            if variant.get("product_id") is not None:
                variant["product_id"] = str(variant["product_id"])
            # Missing/null fixed 配鑽 total is OK — admin UI falls back to formula.
            variant.setdefault("side_stone_total_twd", None)
        for image in product["images"]:
            if image.get("id") is not None:
                image["id"] = str(image["id"])
            if image.get("product_id") is not None:
                image["product_id"] = str(image["product_id"])
        products.append(product)
    return products


@router.get("/products")
async def products_list(request: Request) -> dict:
    _require_admin(request)
    try:
        with get_transaction() as conn, conn.cursor() as cur:
            purge_auto_stock_product_images(cur)
    except Exception:
        pass
    with get_connection() as conn, conn.cursor() as cur:
        products = _products_with_children(cur)
        categories = fetch_categories(cur)
        labels = category_labels(cur)
    return {
        "products": products,
        "categoryLabels": labels or CATEGORY_LABELS,
        "categories": categories,
        "categoryOrder": [row["slug"] for row in categories],
        "chainCatalog": chain_catalog_for_admin(),
    }


@router.post("/products")
async def products_create(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    with get_connection() as conn, conn.cursor() as cur:
        allowed = valid_category_slugs(cur)
    cleaned, error = validate_product_fields(body, valid_categories=allowed)
    if error:
        return JSONResponse(status_code=400, content={"error": error})

    first_published = first_published_at_value(None, cleaned["isPublished"])
    with get_transaction() as conn, conn.cursor() as cur:
        ensure_product_sell_mode_columns(cur)
        ensure_product_length_weights_column(cur)
        ensure_product_chain_type_column(cur)
        ensure_product_side_stone_total_column(cur)
        cur.execute(
            """
            insert into products (
                category, name_zh, name_en, description_zh, description_en,
                default_color, allows_engraving, allows_fancy_shapes,
                allows_pendant_only, allows_with_chain,
                length_weights, chain_type,
                is_published, first_published_at, created_by_id
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning *
            """,
            (
                cleaned["category"],
                cleaned["nameZh"],
                cleaned["nameEn"],
                cleaned["descriptionZh"],
                cleaned["descriptionEn"],
                cleaned["defaultColor"],
                cleaned["allowsEngraving"],
                cleaned["allowsFancyShapes"],
                cleaned["allowsPendantOnly"],
                cleaned["allowsWithChain"],
                as_jsonb(cleaned.get("lengthWeights")),
                cleaned.get("chainType"),
                cleaned["isPublished"],
                first_published,
                user_id,
            ),
        )
        product = serialize_product_row(cur.fetchone())
        save_product_children(cur, product["id"], cleaned)

    return JSONResponse(content={"product": product})


@router.post("/product-update")
async def product_update(request: Request) -> JSONResponse:
    _require_admin(request)
    body = await request.json()
    product_id = body.get("id")
    if not product_id:
        return JSONResponse(status_code=400, content={"error": "missing id"})

    with get_connection() as conn, conn.cursor() as cur:
        allowed = valid_category_slugs(cur)
    cleaned, error = validate_product_fields(body, valid_categories=allowed)
    if error:
        return JSONResponse(status_code=400, content={"error": error})

    with get_transaction() as conn, conn.cursor() as cur:
        ensure_product_sell_mode_columns(cur)
        ensure_product_length_weights_column(cur)
        ensure_product_chain_type_column(cur)
        ensure_product_side_stone_total_column(cur)
        cur.execute(
            "select id, is_published, first_published_at from products where id = %s",
            (product_id,),
        )
        existing = cur.fetchone()
        if not existing:
            return JSONResponse(status_code=404, content={"error": "product not found"})

        first_published = first_published_at_value(existing, cleaned["isPublished"])
        cur.execute(
            """
            update products set
                category = %s, name_zh = %s, name_en = %s, description_zh = %s, description_en = %s,
                default_color = %s, allows_engraving = %s, allows_fancy_shapes = %s,
                allows_pendant_only = %s, allows_with_chain = %s,
                length_weights = %s, chain_type = %s,
                is_published = %s, first_published_at = %s, updated_at = now()
            where id = %s
            returning *
            """,
            (
                cleaned["category"],
                cleaned["nameZh"],
                cleaned["nameEn"],
                cleaned["descriptionZh"],
                cleaned["descriptionEn"],
                cleaned["defaultColor"],
                cleaned["allowsEngraving"],
                cleaned["allowsFancyShapes"],
                cleaned["allowsPendantOnly"],
                cleaned["allowsWithChain"],
                as_jsonb(cleaned.get("lengthWeights")),
                cleaned.get("chainType"),
                cleaned["isPublished"],
                first_published,
                product_id,
            ),
        )
        product = serialize_product_row(cur.fetchone())
        save_product_children(cur, product_id, cleaned)

    return JSONResponse(content={"product": product})


@router.post("/product-action")
async def product_action(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    product_id = body.get("id")
    action = body.get("action")
    if not product_id or action not in {"publish", "unpublish", "delete", "duplicate"}:
        return JSONResponse(status_code=400, content={"error": "invalid id/action"})

    with get_transaction() as conn, conn.cursor() as cur:
        ensure_product_sell_mode_columns(cur)
        ensure_product_length_weights_column(cur)
        ensure_product_side_stone_total_column(cur)
        cur.execute("select * from products where id = %s", (product_id,))
        product = cur.fetchone()
        if not product:
            return JSONResponse(status_code=404, content={"error": "product not found"})

        if action == "publish":
            ready, reason = publish_readiness(cur, product)
            if not ready:
                return JSONResponse(status_code=400, content={"error": reason})
            first_published = product["first_published_at"] or first_published_at_value(None, True)
            cur.execute(
                """
                update products
                set is_published = true, first_published_at = %s, updated_at = now()
                where id = %s
                """,
                (first_published, product_id),
            )
        elif action == "unpublish":
            cur.execute(
                "update products set is_published = false, updated_at = now() where id = %s",
                (product_id,),
            )
        elif action == "delete":
            cur.execute(
                "select file_path from product_images where product_id = %s",
                (product_id,),
            )
            image_urls = [
                str(row["file_path"]).strip()
                for row in cur.fetchall()
                if row.get("file_path")
            ]
            cur.execute("delete from products where id = %s", (product_id,))
            delete_product_image_urls_if_unreferenced(cur, image_urls)
        elif action == "duplicate":
            cur.execute(
                """
                insert into products (
                    category, name_zh, name_en, description_zh, description_en,
                    default_color, allows_engraving, allows_fancy_shapes,
                    allows_pendant_only, allows_with_chain,
                    length_weights, chain_type,
                    is_published, created_by_id
                )
                select
                    category, %s, name_en, description_zh, description_en,
                    default_color, allows_engraving, allows_fancy_shapes,
                    allows_pendant_only, allows_with_chain,
                    length_weights, chain_type,
                    false, %s
                from products where id = %s
                returning *
                """,
                (
                    f"{product['name_zh']} (複製)",
                    user_id,
                    product_id,
                ),
            )
            copy = cur.fetchone()
            copy_id = copy["id"]
            cur.execute(
                """
                insert into product_variants (
                    product_id, gold, carat, weight_chin, manual_price_twd,
                    side_stone_price_twd, side_stone_carat, side_stone_total_twd
                )
                select %s, gold, carat, weight_chin, manual_price_twd,
                    side_stone_price_twd, side_stone_carat, side_stone_total_twd
                from product_variants where product_id = %s
                """,
                (copy_id, product_id),
            )
            cur.execute(
                """
                insert into product_images (product_id, color, file_path, sort_order)
                select %s, color, file_path, sort_order
                from product_images
                where product_id = %s
                  and file_path not ilike '%%/shop-product/%%'
                  and file_path not ilike '%%\\shop-product\\%%'
                  and file_path not ilike 'images/shop-product/%%'
                """,
                (copy_id, product_id),
            )
            return JSONResponse(content={"ok": True, "product": serialize_product_row(copy)})

    return JSONResponse(content={"ok": True})


@router.post("/products-reorder")
async def products_reorder(request: Request) -> JSONResponse:
    _require_admin(request)
    body = await request.json()
    order = body.get("order")
    if not isinstance(order, list):
        return JSONResponse(status_code=400, content={"error": "order must be an array of product ids"})

    with get_connection() as conn, conn.cursor() as cur:
        for index, product_id in enumerate(order):
            cur.execute(
                "update products set sort_order = %s where id = %s",
                (index, product_id),
            )
    return JSONResponse(content={"ok": True})


def _ensure_invite_schema(cur) -> None:
    cur.execute("alter table invite_codes add column if not exists label text")
    cur.execute(
        "alter table invite_codes add column if not exists grants_partner boolean not null default false"
    )
    cur.execute("alter table profiles add column if not exists is_partner boolean not null default false")
    cur.execute(
        "update invite_codes set grants_partner = true where grants_admin = false and grants_partner = false"
    )


def _serialize_invite(row: dict) -> dict:
    out = dict(row)
    for key in ("id", "created_by_id", "used_by_id"):
        if out.get(key) is not None:
            out[key] = str(out[key])
    for key in ("created_at", "expires_at", "used_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    return out


@router.get("/invites")
async def invites_list(request: Request) -> dict:
    _require_admin(request)
    with get_connection() as conn, conn.cursor() as cur:
        _ensure_invite_schema(cur)
        cur.execute(
            """
            select i.*,
                   p.full_name as used_by_name,
                   u.email as used_by_email
            from invite_codes i
            left join users u on u.id = i.used_by_id
            left join profiles p on p.id = i.used_by_id
            order by i.created_at desc
            """
        )
        invites = [_serialize_invite(row) for row in cur.fetchall()]
    return {"invites": invites}


@router.post("/invites")
async def invites_create(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()

    label = str(body.get("label") or body.get("partnerName") or "").strip() or None
    grants_admin = bool(body.get("grantsAdmin"))
    grants_partner = bool(body.get("grantsPartner"))
    expires_in_days = body.get("expiresInDays")

    if grants_admin and grants_partner:
        return JSONResponse(status_code=400, content={"error": "請只選擇一種帳號類型"})
    if not grants_admin and not grants_partner:
        return JSONResponse(status_code=400, content={"error": "請選擇帳號類型：合作廠商或管理員"})

    step_resp = _step_up_response(user_id, body if isinstance(body, dict) else {})
    if step_resp:
        return step_resp

    max_uses = body.get("maxUses")
    if grants_admin:
        max_uses = 1
        grants_partner = False
    elif max_uses not in (None, ""):
        try:
            max_uses = int(max_uses)
        except (TypeError, ValueError):
            return JSONResponse(status_code=400, content={"error": "可使用次數必須為正整數"})
        if max_uses < 1:
            return JSONResponse(status_code=400, content={"error": "可使用次數至少為 1"})
    else:
        max_uses = None

    expires_at = None
    if expires_in_days not in (None, ""):
        try:
            days = int(expires_in_days)
        except (TypeError, ValueError):
            return JSONResponse(status_code=400, content={"error": "有效天數必須為正整數"})
        if days < 1:
            return JSONResponse(status_code=400, content={"error": "有效天數至少為 1"})
        expires_at = datetime.now(timezone.utc) + timedelta(days=days)

    code = generate_invite_code()
    with get_connection() as conn, conn.cursor() as cur:
        _ensure_invite_schema(cur)
        cur.execute(
            """
            insert into invite_codes (code, label, created_by_id, max_uses, grants_admin, grants_partner, expires_at)
            values (%s, %s, %s, %s, %s, %s, %s)
            returning *
            """,
            (code, label, user_id, max_uses, grants_admin, grants_partner, expires_at),
        )
        invite = _serialize_invite(cur.fetchone())

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(
        actor["email"] if actor else None,
        "invite_created",
        {"code": code, "label": label, "grantsAdmin": grants_admin, "grantsPartner": grants_partner, "maxUses": max_uses},
    )
    return JSONResponse(content={"invite": invite})


@router.post("/invite-action")
async def invite_action(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    invite_id = body.get("id")
    action = body.get("action")

    if not invite_id or action not in {"revoke", "delete"}:
        return JSONResponse(status_code=400, content={"error": "invalid id/action"})

    with get_connection() as conn, conn.cursor() as cur:
        if action == "revoke":
            cur.execute(
                "update invite_codes set is_active = false where id = %s returning code",
                (invite_id,),
            )
        else:
            cur.execute("delete from invite_codes where id = %s returning code", (invite_id,))
        row = cur.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "invite not found"})

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(
        actor["email"] if actor else None,
        f"invite_{action}",
        {"inviteId": str(invite_id), "code": row["code"]},
    )
    return JSONResponse(content={"ok": True})


def _serialize_account(row: dict) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    for key in ("created_at", "last_login_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    out["order_count"] = int(out.get("order_count") or 0)
    out["is_admin"] = bool(out.get("is_admin"))
    out["is_partner"] = bool(out.get("is_partner"))
    out["is_active"] = bool(out.get("is_active"))
    out["imprint_invited"] = bool(out.get("imprint_invited"))
    out["partner_imprint_invited"] = bool(out.get("partner_imprint_invited"))
    return out


def _ensure_membership_profile_cols(cur) -> None:
    for stmt in (
        "alter table profiles add column if not exists imprint_invited boolean not null default false",
        "alter table profiles add column if not exists partner_imprint_invited boolean not null default false",
        "alter table profiles add column if not exists referral_code text",
    ):
        cur.execute(stmt)


@router.get("/accounts")
async def accounts_list(request: Request, q: str | None = Query(None)) -> dict:
    _require_admin(request)
    search = (q or "").strip()
    # Card shows short id like "9A68 6CB8 40" — match against UUID without hyphens/spaces.
    compact = re.sub(r"[\s\-]+", "", search)
    with get_connection() as conn, conn.cursor() as cur:
        _ensure_invite_schema(cur)
        _ensure_membership_profile_cols(cur)
        base_sql = """
            select u.id, u.email, u.is_active, u.last_login_at, u.created_at,
                   p.full_name, p.phone, p.store_name, p.referral_code,
                   coalesce(p.is_partner, false) as is_partner,
                   coalesce(p.imprint_invited, false) as imprint_invited,
                   coalesce(p.partner_imprint_invited, false) as partner_imprint_invited,
                   (sa.user_id is not null) as is_admin,
                   (select count(*)::int from orders o where o.user_id = u.id) as order_count
            from users u
            left join profiles p on p.id = u.id
            left join staff_admins sa on sa.user_id = u.id
        """
        if search:
            like = f"%{search}%"
            like_compact = f"%{compact}%"
            cur.execute(
                base_sql
                + """
                where u.email ilike %s
                   or coalesce(p.full_name, '') ilike %s
                   or coalesce(p.phone, '') ilike %s
                   or coalesce(p.store_name, '') ilike %s
                   or coalesce(p.referral_code, '') ilike %s
                   or u.id::text ilike %s
                   or replace(u.id::text, '-', '') ilike %s
                order by u.created_at desc
                limit 100
                """,
                (like, like, like, like, like, like, like_compact),
            )
        else:
            cur.execute(base_sql + " order by u.created_at desc")
        accounts = [_serialize_account(row) for row in cur.fetchall()]
    return {"accounts": accounts}


@router.get("/accounts/{account_id}", response_model=None)
async def account_detail(request: Request, account_id: str):
    _require_admin(request)
    try:
        uid = str(uuid.UUID(str(account_id).strip()))
    except (ValueError, TypeError, AttributeError):
        return JSONResponse(status_code=400, content={"error": "invalid account id"})

    with get_connection() as conn, conn.cursor() as cur:
        _ensure_invite_schema(cur)
        _ensure_membership_profile_cols(cur)
        for stmt in (
            "alter table profiles add column if not exists shipping_postal text",
            "alter table profiles add column if not exists shipping_city text",
            "alter table profiles add column if not exists shipping_address text",
            "alter table profiles add column if not exists referred_by uuid",
            "alter table profiles add column if not exists referred_at timestamptz",
        ):
            cur.execute(stmt)

        cur.execute(
            """
            select u.id, u.email, u.is_active, u.last_login_at, u.created_at,
                   p.full_name, p.phone, p.store_name, p.referral_code,
                   p.shipping_postal, p.shipping_city, p.shipping_address,
                   p.referred_by, p.referred_at,
                   coalesce(p.is_partner, false) as is_partner,
                   coalesce(p.imprint_invited, false) as imprint_invited,
                   coalesce(p.partner_imprint_invited, false) as partner_imprint_invited,
                   (sa.user_id is not null) as is_admin,
                   (select count(*)::int from orders o where o.user_id = u.id) as order_count
            from users u
            left join profiles p on p.id = u.id
            left join staff_admins sa on sa.user_id = u.id
            where u.id = %s
            """,
            (uid,),
        )
        row = cur.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "account not found"})

        account = _serialize_account(row)
        for key in ("referred_at",):
            val = account.get(key)
            if isinstance(val, datetime):
                account[key] = val.isoformat()
        if account.get("referred_by") is not None:
            account["referred_by"] = str(account["referred_by"])

        referred_by_label = None
        if account.get("referred_by"):
            cur.execute(
                """
                select u.email, p.full_name
                from users u
                left join profiles p on p.id = u.id
                where u.id = %s
                """,
                (account["referred_by"],),
            )
            ref = cur.fetchone()
            if ref:
                referred_by_label = (ref.get("full_name") or ref.get("email") or account["referred_by"])

        cur.execute(
            """
            select id, order_number, status, total_price, summary_zh, created_at
            from orders
            where user_id = %s
            order by created_at desc
            limit 12
            """,
            (uid,),
        )
        orders = []
        for o in cur.fetchall():
            item = dict(o)
            if item.get("id") is not None:
                item["id"] = str(item["id"])
            created = item.get("created_at")
            if isinstance(created, datetime):
                item["created_at"] = created.isoformat()
            if item.get("total_price") is not None:
                item["total_price"] = float(item["total_price"])
            orders.append(item)

    account["referred_by_label"] = referred_by_label
    return {"account": account, "orders": orders}


@router.post("/account-action")
async def account_action(request: Request) -> JSONResponse:
    admin_id = _require_admin(request)
    body = await request.json()
    account_id = body.get("id")
    action = body.get("action")

    if not account_id or action not in {
        "toggle-active",
        "clear-lockout",
        "delete",
        "reset-password",
        "set-role",
        "set-imprint-invited",
        "set-partner-imprint-invited",
    }:
        return JSONResponse(status_code=400, content={"error": "invalid id/action"})

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id, email, is_active from users where id = %s", (account_id,))
        user = cur.fetchone()
        if not user:
            return JSONResponse(status_code=404, content={"error": "account not found"})

        if action == "toggle-active":
            step_resp = _step_up_response(str(admin_id), body if isinstance(body, dict) else {})
            if step_resp:
                return step_resp
            cur.execute(
                "update users set is_active = %s where id = %s",
                (not user["is_active"], account_id),
            )
        elif action == "clear-lockout":
            email = (user["email"] or "").lower()
            cur.execute(
                """
                delete from login_lockouts
                where lockout_key = %s or lockout_key like %s
                """,
                (f"login:{email}", f"login:{email}:%"),
            )
        elif action == "delete":
            confirm_email = str(body.get("confirmEmail") or "").strip().lower()
            admin_password = str(body.get("password") or body.get("adminPassword") or "")
            admin_totp = str(body.get("totpCode") or body.get("code") or "").strip()
            if not confirm_email:
                return JSONResponse(status_code=400, content={"error": "請輸入 Email 以確認刪除"})
            if not admin_password:
                return JSONResponse(status_code=400, content={"error": "請輸入您的管理員密碼以確認刪除"})
            step_err = verify_step_up_password(str(admin_id), admin_password, admin_totp or None)
            if step_err:
                return JSONResponse(status_code=401, content={"error": step_err})
            target_email = str(user.get("email") or "").strip().lower()
            if confirm_email != target_email:
                return JSONResponse(status_code=400, content={"error": "Email 不符，請輸入該帳戶的 Email"})
            blocked = delete_blocked_reason(cur, str(account_id))
            if blocked:
                return JSONResponse(status_code=403, content={"error": blocked})
            hard_delete_user(cur, account_id)
        elif action == "reset-password":
            admin_password = str(body.get("password") or body.get("adminPassword") or "")
            admin_totp = str(body.get("totpCode") or body.get("code") or "").strip()
            if not admin_password:
                return JSONResponse(status_code=400, content={"error": "請輸入您的管理員密碼以確認"})
            step_err = verify_step_up_password(str(admin_id), admin_password, admin_totp or None)
            if step_err:
                return JSONResponse(status_code=401, content={"error": step_err})
            new_password = body.get("newPassword") or ""
            if len(str(new_password)) < 8:
                return JSONResponse(status_code=400, content={"error": "密碼至少需要 8 碼"})
            cur.execute(
                "update users set password_hash = %s, token_version = token_version + 1 where id = %s",
                (hash_password(str(new_password)), account_id),
            )
        elif action == "set-role":
            admin_password = str(body.get("password") or body.get("adminPassword") or "")
            admin_totp = str(body.get("totpCode") or body.get("code") or "").strip()
            if not admin_password:
                return JSONResponse(status_code=400, content={"error": "請輸入您的管理員密碼以確認"})
            step_err = verify_step_up_password(str(admin_id), admin_password, admin_totp or None)
            if step_err:
                return JSONResponse(status_code=401, content={"error": step_err})
            role = body.get("role")
            if role not in {"member", "partner", "admin"}:
                return JSONResponse(status_code=400, content={"error": "invalid role"})
            if str(account_id) == str(admin_id) and role != "admin":
                return JSONResponse(status_code=400, content={"error": "無法變更自己的管理員權限"})
            if role == "admin":
                cur.execute(
                    "insert into staff_admins (user_id) values (%s) on conflict do nothing",
                    (account_id,),
                )
                cur.execute(
                    """
                    insert into profiles (id, is_partner) values (%s, false)
                    on conflict (id) do update set is_partner = false
                    """,
                    (account_id,),
                )
            elif role == "partner":
                cur.execute("delete from staff_admins where user_id = %s", (account_id,))
                cur.execute(
                    """
                    insert into profiles (id, is_partner) values (%s, true)
                    on conflict (id) do update set is_partner = true
                    """,
                    (account_id,),
                )
            else:
                cur.execute("delete from staff_admins where user_id = %s", (account_id,))
                cur.execute(
                    """
                    insert into profiles (id, is_partner) values (%s, false)
                    on conflict (id) do update set is_partner = false
                    """,
                    (account_id,),
                )
        elif action == "set-imprint-invited":
            _ensure_membership_profile_cols(cur)
            flag = bool(body.get("value"))
            cur.execute(
                """
                insert into profiles (id, imprint_invited) values (%s, %s)
                on conflict (id) do update set imprint_invited = excluded.imprint_invited
                """,
                (account_id, flag),
            )
        elif action == "set-partner-imprint-invited":
            _ensure_membership_profile_cols(cur)
            flag = bool(body.get("value"))
            cur.execute(
                """
                insert into profiles (id, partner_imprint_invited) values (%s, %s)
                on conflict (id) do update
                set partner_imprint_invited = excluded.partner_imprint_invited
                """,
                (account_id, flag),
            )

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (admin_id,))
        actor = cur.fetchone()
    log_admin_action(
        actor["email"] if actor else None,
        f"account_{action}",
        {"userId": str(account_id), "email": user["email"]},
    )
    return JSONResponse(content={"ok": True})


def _serialize_coupon(row: dict) -> dict:
    out = dict(row)
    for key in ("id", "created_by_id"):
        if out.get(key) is not None:
            out[key] = str(out[key])
    for key in ("created_at", "updated_at", "starts_at", "expires_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    for key in ("discount_value", "min_order_amount"):
        if out.get(key) is not None:
            out[key] = float(out[key])
    for key in ("max_uses", "max_uses_per_user", "used_count"):
        if out.get(key) is not None:
            out[key] = int(out[key])
    if "is_active" in out:
        out["is_active"] = bool(out["is_active"])
    return out


def _parse_optional_int(value, *, field: str, min_value: int = 1):
    if value in (None, ""):
        return None, None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None, JSONResponse(status_code=400, content={"error": f"{field}必須為正整數"})
    if n < min_value:
        return None, JSONResponse(status_code=400, content={"error": f"{field}至少為 {min_value}"})
    return n, None


def _parse_optional_amount(value, *, field: str):
    if value in (None, ""):
        return None, None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None, JSONResponse(status_code=400, content={"error": f"{field}必須為數字"})
    if n < 0:
        return None, JSONResponse(status_code=400, content={"error": f"{field}不可為負數"})
    return n, None


def _parse_optional_datetime(value, *, field: str):
    if value in (None, ""):
        return None, None
    raw = str(value).strip()
    try:
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            dt = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
        else:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None, JSONResponse(status_code=400, content={"error": f"{field}格式無效"})
    return dt, None


def _parse_coupon_fields(body: dict):
    """Validate coupon create/update body. Returns (fields, error_response)."""
    discount_type = str(body.get("discountType") or body.get("discount_type") or "").strip().lower()
    if discount_type not in ("percent", "fixed"):
        return None, JSONResponse(status_code=400, content={"error": "請選擇折扣類型：百分比或固定金額"})

    try:
        discount_value = float(body.get("discountValue") or body.get("discount_value") or 0)
    except (TypeError, ValueError):
        return None, JSONResponse(status_code=400, content={"error": "折扣數值無效"})
    if discount_type == "percent":
        if discount_value < 1 or discount_value > 100:
            return None, JSONResponse(status_code=400, content={"error": "百分比須介於 1–100"})
    elif discount_value < 1:
        return None, JSONResponse(status_code=400, content={"error": "固定金額至少 NT$1"})

    label = str(body.get("label") or "").strip() or None
    min_order, err = _parse_optional_amount(
        body.get("minOrderAmount") or body.get("min_order_amount"), field="最低消費"
    )
    if err:
        return None, err
    max_uses, err = _parse_optional_int(body.get("maxUses") or body.get("max_uses"), field="總使用上限")
    if err:
        return None, err
    max_per_user, err = _parse_optional_int(
        body.get("maxUsesPerUser") or body.get("max_uses_per_user"), field="每人上限"
    )
    if err:
        return None, err
    starts_at, err = _parse_optional_datetime(body.get("startsAt") or body.get("starts_at"), field="開始時間")
    if err:
        return None, err
    expires_at, err = _parse_optional_datetime(body.get("expiresAt") or body.get("expires_at"), field="到期時間")
    if err:
        return None, err
    if starts_at and expires_at and expires_at <= starts_at:
        return None, JSONResponse(status_code=400, content={"error": "到期時間須晚於開始時間"})

    is_active = body.get("isActive")
    if is_active is None:
        is_active = body.get("is_active", True)
    is_active = bool(is_active)

    return {
        "label": label,
        "discount_type": discount_type,
        "discount_value": discount_value,
        "min_order_amount": min_order,
        "max_uses": max_uses,
        "max_uses_per_user": max_per_user,
        "starts_at": starts_at,
        "expires_at": expires_at,
        "is_active": is_active,
    }, None


@router.get("/coupons")
async def coupons_list(request: Request) -> dict:
    _require_admin(request)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select * from coupons order by created_at desc")
        coupons = [_serialize_coupon(row) for row in cur.fetchall()]
    return {"coupons": coupons}


@router.post("/coupons")
async def coupons_create(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    step_resp = _step_up_response(user_id, body)
    if step_resp:
        return step_resp

    from app.coupons import generate_coupon_code, normalize_code

    code_raw = body.get("code")
    if body.get("generate") or not str(code_raw or "").strip():
        code = generate_coupon_code()
    else:
        code = normalize_code(str(code_raw))
    if not code or len(code) < 3:
        return JSONResponse(status_code=400, content={"error": "優惠碼至少 3 個字元"})
    if len(code) > 32:
        return JSONResponse(status_code=400, content={"error": "優惠碼過長"})

    fields, err = _parse_coupon_fields(body)
    if err:
        return err

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from coupons where code = %s", (code,))
        if cur.fetchone():
            return JSONResponse(status_code=400, content={"error": "優惠碼已存在"})
        cur.execute(
            """
            insert into coupons (
              code, label, discount_type, discount_value,
              min_order_amount, max_uses, max_uses_per_user,
              is_active, starts_at, expires_at, created_by_id
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning *
            """,
            (
                code,
                fields["label"],
                fields["discount_type"],
                fields["discount_value"],
                fields["min_order_amount"],
                fields["max_uses"],
                fields["max_uses_per_user"],
                fields["is_active"],
                fields["starts_at"],
                fields["expires_at"],
                user_id,
            ),
        )
        coupon = _serialize_coupon(cur.fetchone())

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(
        actor["email"] if actor else None,
        "coupon_created",
        {
            "code": code,
            "discountType": fields["discount_type"],
            "discountValue": fields["discount_value"],
        },
    )
    return JSONResponse(content={"coupon": coupon})


@router.post("/coupon-update")
async def coupons_update(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    step_resp = _step_up_response(user_id, body)
    if step_resp:
        return step_resp

    from app.coupons import normalize_code

    coupon_id = body.get("id")
    if not coupon_id:
        return JSONResponse(status_code=400, content={"error": "缺少優惠券 id"})

    code = normalize_code(str(body.get("code") or ""))
    if not code or len(code) < 3:
        return JSONResponse(status_code=400, content={"error": "優惠碼至少 3 個字元"})
    if len(code) > 32:
        return JSONResponse(status_code=400, content={"error": "優惠碼過長"})

    fields, err = _parse_coupon_fields(body)
    if err:
        return err

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from coupons where code = %s and id <> %s", (code, coupon_id))
        if cur.fetchone():
            return JSONResponse(status_code=400, content={"error": "優惠碼已存在"})
        cur.execute(
            """
            update coupons set
              code = %s,
              label = %s,
              discount_type = %s,
              discount_value = %s,
              min_order_amount = %s,
              max_uses = %s,
              max_uses_per_user = %s,
              is_active = %s,
              starts_at = %s,
              expires_at = %s,
              updated_at = now()
            where id = %s
            returning *
            """,
            (
                code,
                fields["label"],
                fields["discount_type"],
                fields["discount_value"],
                fields["min_order_amount"],
                fields["max_uses"],
                fields["max_uses_per_user"],
                fields["is_active"],
                fields["starts_at"],
                fields["expires_at"],
                coupon_id,
            ),
        )
        row = cur.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "coupon not found"})
        coupon = _serialize_coupon(row)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(
        actor["email"] if actor else None,
        "coupon_updated",
        {"couponId": str(coupon_id), "code": code},
    )
    return JSONResponse(content={"coupon": coupon})


@router.post("/coupon-action")
async def coupon_action(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    step_resp = _step_up_response(user_id, body)
    if step_resp:
        return step_resp
    coupon_id = body.get("id")
    action = body.get("action")

    if not coupon_id or action not in {"deactivate", "activate", "delete"}:
        return JSONResponse(status_code=400, content={"error": "invalid id/action"})

    with get_connection() as conn, conn.cursor() as cur:
        if action == "deactivate":
            cur.execute(
                "update coupons set is_active = false, updated_at = now() where id = %s returning code",
                (coupon_id,),
            )
        elif action == "activate":
            cur.execute(
                "update coupons set is_active = true, updated_at = now() where id = %s returning code",
                (coupon_id,),
            )
        else:
            cur.execute("delete from coupons where id = %s returning code", (coupon_id,))
        row = cur.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "coupon not found"})

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(
        actor["email"] if actor else None,
        f"coupon_{action}",
        {"couponId": str(coupon_id), "code": row["code"]},
    )
    return JSONResponse(content={"ok": True})


# ── Content CMS: testimonials + FAQ ──────────────────────────────────────────


@router.get("/testimonials")
async def admin_testimonials_list(request: Request) -> dict:
    _require_admin(request)
    from app.content import ensure_testimonial_country_column, fetch_all_testimonials

    with get_connection() as conn, conn.cursor() as cur:
        ensure_testimonial_country_column(cur)
        return {"testimonials": fetch_all_testimonials(cur)}


@router.post("/testimonials")
async def admin_testimonials_create(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}

    from app.content import (
        apply_testimonial_sort_order,
        ensure_testimonial_country_column,
        next_testimonial_sort_order,
        parse_testimonial_payload,
        serialize_testimonial,
    )

    cleaned, error = parse_testimonial_payload(body)
    if error:
        return JSONResponse(status_code=400, content={"error": error})

    explicit_sort = body.get("sortOrder") not in (None, "")
    with get_transaction() as conn, conn.cursor() as cur:
        ensure_testimonial_country_column(cur)
        sort_order = next_testimonial_sort_order(cur)
        cur.execute(
            """
            insert into testimonials (
              name, role, category, city, country, text, image_url, rating, sort_order, is_published
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning *
            """,
            (
                cleaned["name"],
                cleaned["role"],
                cleaned["category"],
                cleaned["city"],
                cleaned.get("country") or "",
                cleaned["text"],
                cleaned["image_url"],
                cleaned["rating"],
                sort_order,
                cleaned["is_published"],
            ),
        )
        row = serialize_testimonial(cur.fetchone())
        if explicit_sort:
            try:
                target = max(0, int(body.get("sortOrder")))
            except (TypeError, ValueError):
                return JSONResponse(status_code=400, content={"error": "排序無效"})
            apply_testimonial_sort_order(cur, row["id"], target)
            cur.execute("select * from testimonials where id = %s", (row["id"],))
            row = serialize_testimonial(cur.fetchone())

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(actor["email"] if actor else None, "testimonial_created", {"id": row["id"]})
    return JSONResponse(content={"testimonial": row})


@router.post("/testimonial-upload")
async def testimonial_upload(request: Request, file: UploadFile = File(...)) -> JSONResponse:
    _require_admin(request)
    if not file.filename:
        return JSONResponse(status_code=400, content={"error": "missing file"})
    ext = Path(file.filename).suffix.lower()
    data = await file.read()
    err = _image_upload_error(file, data, ext)
    if err:
        return JSONResponse(status_code=400, content={"error": err})
    name = f"{uuid.uuid4().hex}{ext}"
    url, upload_err = _storage_upload("testimonials", name, data, ext)
    if upload_err:
        return JSONResponse(status_code=503, content={"error": upload_err})
    return JSONResponse(content={"url": url})


@router.post("/testimonial-update")
async def admin_testimonials_update(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}

    from app.content import (
        apply_testimonial_sort_order,
        ensure_testimonial_country_column,
        parse_testimonial_payload,
        serialize_testimonial,
    )

    tid = body.get("id")
    if not tid:
        return JSONResponse(status_code=400, content={"error": "缺少 id"})
    cleaned, error = parse_testimonial_payload(body)
    if error:
        return JSONResponse(status_code=400, content={"error": error})

    explicit_sort = body.get("sortOrder") not in (None, "")

    with get_transaction() as conn, conn.cursor() as cur:
        ensure_testimonial_country_column(cur)
        cur.execute("select sort_order from testimonials where id = %s", (tid,))
        existing = cur.fetchone()
        if not existing:
            return JSONResponse(status_code=404, content={"error": "找不到見證"})
        sort_order = int(existing["sort_order"])
        cur.execute(
            """
            update testimonials set
              name = %s, role = %s, category = %s, city = %s, country = %s, text = %s,
              image_url = %s, rating = %s, is_published = %s, updated_at = now()
            where id = %s
            returning *
            """,
            (
                cleaned["name"],
                cleaned["role"],
                cleaned["category"],
                cleaned["city"],
                cleaned.get("country") or "",
                cleaned["text"],
                cleaned["image_url"],
                cleaned["rating"],
                cleaned["is_published"],
                tid,
            ),
        )
        row = serialize_testimonial(cur.fetchone())
        if explicit_sort:
            try:
                target = max(0, int(body.get("sortOrder")))
            except (TypeError, ValueError):
                return JSONResponse(status_code=400, content={"error": "排序無效"})
            apply_testimonial_sort_order(cur, str(tid), target)
            cur.execute("select * from testimonials where id = %s", (tid,))
            row = serialize_testimonial(cur.fetchone())

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(actor["email"] if actor else None, "testimonial_updated", {"id": str(tid)})
    return JSONResponse(content={"testimonial": row})


@router.post("/testimonial-reorder")
async def admin_testimonial_reorder(request: Request) -> JSONResponse:
    _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    tid = body.get("id")
    direction = body.get("direction")
    if not tid or direction not in {"up", "down"}:
        return JSONResponse(status_code=400, content={"error": "invalid id/direction"})

    from app.content import move_testimonial

    with get_transaction() as conn, conn.cursor() as cur:
        if not move_testimonial(cur, str(tid), direction):
            return JSONResponse(status_code=400, content={"error": "無法調整排序"})
    return JSONResponse(content={"ok": True})


@router.post("/testimonial-action")
async def admin_testimonial_action(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    tid = body.get("id")
    action = body.get("action")
    if not tid or action not in {"publish", "unpublish", "delete"}:
        return JSONResponse(status_code=400, content={"error": "invalid id/action"})

    with get_connection() as conn, conn.cursor() as cur:
        if action == "publish":
            cur.execute(
                "update testimonials set is_published = true, updated_at = now() where id = %s returning id",
                (tid,),
            )
        elif action == "unpublish":
            cur.execute(
                "update testimonials set is_published = false, updated_at = now() where id = %s returning id",
                (tid,),
            )
        else:
            cur.execute("delete from testimonials where id = %s returning id", (tid,))
        row = cur.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "找不到見證"})
        if action == "delete":
            from app.content import renormalize_testimonial_sort

            renormalize_testimonial_sort(cur)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(
        actor["email"] if actor else None,
        f"testimonial_{action}",
        {"id": str(tid)},
    )
    return JSONResponse(content={"ok": True})


@router.get("/faq-categories")
async def admin_faq_categories(request: Request) -> dict:
    _require_admin(request)
    from app.content import serialize_faq_category

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select * from faq_categories order by sort_order asc, id asc")
        return {"categories": [serialize_faq_category(r) for r in cur.fetchall()]}


@router.get("/faq-items")
async def admin_faq_items_list(request: Request) -> dict:
    _require_admin(request)
    from app.content import fetch_faq_admin

    with get_connection() as conn, conn.cursor() as cur:
        return fetch_faq_admin(cur)


@router.post("/faq-items")
async def admin_faq_items_create(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}

    from app.content import new_faq_id, sanitize_faq_plain_text, serialize_faq_item

    category_id = str(body.get("categoryId") or body.get("category_id") or "").strip()
    question = sanitize_faq_plain_text(str(body.get("question") or ""))
    answer = sanitize_faq_plain_text(str(body.get("answer") or ""))
    if not category_id or not question or not answer:
        return JSONResponse(status_code=400, content={"error": "請填寫分類、問題與回答"})
    item_id = str(body.get("id") or "").strip() or new_faq_id()
    try:
        sort_order = int(body.get("sortOrder") if body.get("sortOrder") not in (None, "") else 0)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"error": "排序無效"})
    is_published = bool(body.get("isPublished") if body.get("isPublished") is not None else True)
    show_in_teaser = bool(body.get("showInTeaser") or body.get("show_in_teaser"))

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from faq_categories where id = %s", (category_id,))
        if not cur.fetchone():
            return JSONResponse(status_code=400, content={"error": "分類不存在"})
        cur.execute("select id from faq_items where id = %s", (item_id,))
        if cur.fetchone():
            return JSONResponse(status_code=400, content={"error": "FAQ id 已存在"})
        cur.execute(
            """
            insert into faq_items (
              id, category_id, question, answer, sort_order, is_published, show_in_teaser
            ) values (%s, %s, %s, %s, %s, %s, %s)
            returning *
            """,
            (item_id, category_id, question, answer, sort_order, is_published, show_in_teaser),
        )
        row = serialize_faq_item(cur.fetchone())

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(actor["email"] if actor else None, "faq_created", {"id": item_id})
    return JSONResponse(content={"item": row})


@router.post("/faq-update")
async def admin_faq_update(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}

    from app.content import sanitize_faq_plain_text, serialize_faq_item

    item_id = str(body.get("id") or "").strip()
    if not item_id:
        return JSONResponse(status_code=400, content={"error": "缺少 id"})
    category_id = str(body.get("categoryId") or body.get("category_id") or "").strip()
    question = sanitize_faq_plain_text(str(body.get("question") or ""))
    answer = sanitize_faq_plain_text(str(body.get("answer") or ""))
    if not category_id or not question or not answer:
        return JSONResponse(status_code=400, content={"error": "請填寫分類、問題與回答"})
    try:
        sort_order = int(body.get("sortOrder") if body.get("sortOrder") not in (None, "") else 0)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"error": "排序無效"})
    is_published = bool(body.get("isPublished") if body.get("isPublished") is not None else True)
    show_in_teaser = bool(body.get("showInTeaser") or body.get("show_in_teaser"))

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from faq_categories where id = %s", (category_id,))
        if not cur.fetchone():
            return JSONResponse(status_code=400, content={"error": "分類不存在"})
        cur.execute(
            """
            update faq_items set
              category_id = %s, question = %s, answer = %s, sort_order = %s,
              is_published = %s, show_in_teaser = %s, updated_at = now()
            where id = %s
            returning *
            """,
            (category_id, question, answer, sort_order, is_published, show_in_teaser, item_id),
        )
        row = cur.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "找不到 FAQ"})
        out = serialize_faq_item(row)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(actor["email"] if actor else None, "faq_updated", {"id": item_id})
    return JSONResponse(content={"item": out})


@router.post("/faq-action")
async def admin_faq_action(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    step_resp = _step_up_response(user_id, body)
    if step_resp:
        return step_resp
    item_id = body.get("id")
    action = body.get("action")
    if not item_id or action not in {"publish", "unpublish", "delete"}:
        return JSONResponse(status_code=400, content={"error": "invalid id/action"})

    with get_connection() as conn, conn.cursor() as cur:
        if action == "publish":
            cur.execute(
                "update faq_items set is_published = true, updated_at = now() where id = %s returning id",
                (item_id,),
            )
        elif action == "unpublish":
            cur.execute(
                "update faq_items set is_published = false, updated_at = now() where id = %s returning id",
                (item_id,),
            )
        else:
            cur.execute("delete from faq_items where id = %s returning id", (item_id,))
        row = cur.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "找不到 FAQ"})

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(actor["email"] if actor else None, f"faq_{action}", {"id": str(item_id)})
    return JSONResponse(content={"ok": True})


# ── Home banners ─────────────────────────────────────────────────────────────


def _parse_banner_fields(body: dict):
    title = str(body.get("title") or "").strip()
    image_url = str(body.get("imageUrl") or body.get("image_url") or "").strip()
    if not title or not image_url:
        return None, JSONResponse(status_code=400, content={"error": "請填寫標題與圖片"})
    try:
        sort_order = int(body.get("sortOrder") if body.get("sortOrder") not in (None, "") else 0)
    except (TypeError, ValueError):
        return None, JSONResponse(status_code=400, content={"error": "排序無效"})
    tone = str(body.get("tone") or "warm").strip() or "warm"
    if tone not in {"warm", "light", "soft"}:
        tone = "warm"
    is_published = bool(body.get("isPublished") if body.get("isPublished") is not None else True)
    return {
        "eyebrow": str(body.get("eyebrow") or "").strip(),
        "title": title,
        "lead": str(body.get("lead") or "").strip(),
        "image_url": image_url,
        "image_url_mobile": str(body.get("imageUrlMobile") or body.get("image_url_mobile") or "").strip(),
        "image_webp": str(body.get("imageWebp") or body.get("image_webp") or "").strip() or None,
        "image_alt": str(body.get("imageAlt") or body.get("image_alt") or "").strip(),
        "cta_primary_label": str(body.get("ctaPrimaryLabel") or body.get("cta_primary_label") or "").strip(),
        "cta_primary_href": str(body.get("ctaPrimaryHref") or body.get("cta_primary_href") or "").strip(),
        "cta_secondary_label": str(body.get("ctaSecondaryLabel") or body.get("cta_secondary_label") or "").strip(),
        "cta_secondary_href": str(body.get("ctaSecondaryHref") or body.get("cta_secondary_href") or "").strip(),
        "tone": tone,
        "sort_order": sort_order,
        "is_published": is_published,
    }, None


@router.get("/banners")
async def admin_banners_list(request: Request) -> dict:
    _require_admin(request)
    from app.content import fetch_all_banners

    with get_connection() as conn, conn.cursor() as cur:
        return {"banners": fetch_all_banners(cur)}


@router.post("/banner-upload")
async def banner_upload(request: Request, file: UploadFile = File(...)) -> JSONResponse:
    _require_admin(request)
    if not file.filename:
        return JSONResponse(status_code=400, content={"error": "missing file"})
    ext = Path(file.filename).suffix.lower()
    data = await file.read()
    err = _image_upload_error(file, data, ext)
    if err:
        return JSONResponse(status_code=400, content={"error": err})
    name = f"{uuid.uuid4().hex}{ext}"
    url, upload_err = _storage_upload("banners", name, data, ext)
    if upload_err:
        return JSONResponse(status_code=503, content={"error": upload_err})
    return JSONResponse(content={"url": url})


@router.post("/banners")
async def admin_banners_create(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    from app.content import serialize_banner

    fields, err = _parse_banner_fields(body)
    if err:
        return err
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into home_banners (
              eyebrow, title, lead, image_url, image_url_mobile, image_webp, image_alt,
              cta_primary_label, cta_primary_href,
              cta_secondary_label, cta_secondary_href,
              tone, sort_order, is_published
            ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            returning *
            """,
            (
                fields["eyebrow"],
                fields["title"],
                fields["lead"],
                fields["image_url"],
                fields["image_url_mobile"],
                fields["image_webp"],
                fields["image_alt"],
                fields["cta_primary_label"],
                fields["cta_primary_href"],
                fields["cta_secondary_label"],
                fields["cta_secondary_href"],
                fields["tone"],
                fields["sort_order"],
                fields["is_published"],
            ),
        )
        row = serialize_banner(cur.fetchone())
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(actor["email"] if actor else None, "banner_created", {"id": row["id"]})
    return JSONResponse(content={"banner": row})


@router.post("/banner-update")
async def admin_banners_update(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    from app.content import serialize_banner

    bid = body.get("id")
    if not bid:
        return JSONResponse(status_code=400, content={"error": "缺少 id"})
    fields, err = _parse_banner_fields(body)
    if err:
        return err
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            update home_banners set
              eyebrow = %s, title = %s, lead = %s, image_url = %s, image_url_mobile = %s,
              image_webp = %s, image_alt = %s, cta_primary_label = %s, cta_primary_href = %s,
              cta_secondary_label = %s, cta_secondary_href = %s,
              tone = %s, sort_order = %s, is_published = %s, updated_at = now()
            where id = %s
            returning *
            """,
            (
                fields["eyebrow"],
                fields["title"],
                fields["lead"],
                fields["image_url"],
                fields["image_url_mobile"],
                fields["image_webp"],
                fields["image_alt"],
                fields["cta_primary_label"],
                fields["cta_primary_href"],
                fields["cta_secondary_label"],
                fields["cta_secondary_href"],
                fields["tone"],
                fields["sort_order"],
                fields["is_published"],
                bid,
            ),
        )
        row = cur.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "找不到 banner"})
        out = serialize_banner(row)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(actor["email"] if actor else None, "banner_updated", {"id": str(bid)})
    return JSONResponse(content={"banner": out})


@router.post("/banner-action")
async def admin_banner_action(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    bid = body.get("id")
    action = body.get("action")
    if not bid or action not in {"publish", "unpublish", "delete"}:
        return JSONResponse(status_code=400, content={"error": "invalid id/action"})
    with get_connection() as conn, conn.cursor() as cur:
        if action == "publish":
            cur.execute(
                "update home_banners set is_published = true, updated_at = now() where id = %s returning id",
                (bid,),
            )
        elif action == "unpublish":
            cur.execute(
                "update home_banners set is_published = false, updated_at = now() where id = %s returning id",
                (bid,),
            )
        else:
            cur.execute("delete from home_banners where id = %s returning id", (bid,))
        row = cur.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "找不到 banner"})
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(actor["email"] if actor else None, f"banner_{action}", {"id": str(bid)})
    return JSONResponse(content={"ok": True})


# ── Content CMS: page image slots ────────────────────────────────────────────


@router.get("/page-images")
async def admin_page_images_list(request: Request) -> dict:
    _require_admin(request)
    from app.content import ensure_page_images_schema, fetch_all_page_images

    with get_connection() as conn, conn.cursor() as cur:
        ensure_page_images_schema(cur)
        return {"pageImages": fetch_all_page_images(cur)}


@router.get("/page-image-create-options")
async def admin_page_image_create_options(request: Request) -> dict:
    _require_admin(request)
    from app.content import ensure_page_images_schema, fetch_missing_page_image_slots

    with get_connection() as conn, conn.cursor() as cur:
        ensure_page_images_schema(cur)
        return {"options": fetch_missing_page_image_slots(cur)}


@router.post("/page-image-create")
async def admin_page_image_create(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    from app.cms_boundary import assert_content_page_key

    page_key, key_err = assert_content_page_key(
        str(body.get("pageKey") or body.get("page_key") or "")
    )
    slot_key = str(body.get("slotKey") or body.get("slot_key") or "").strip()
    if key_err or not slot_key or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", slot_key):
        return JSONResponse(
            status_code=400,
            content={"error": key_err or "invalid page_key/slot_key"},
        )
    from app.content import create_page_image_from_registry, ensure_page_images_schema

    with get_connection() as conn, conn.cursor() as cur:
        ensure_page_images_schema(cur)
        row, err = create_page_image_from_registry(cur, page_key, slot_key)
        if err:
            status = 409 if err == "此區塊已存在" else 404
            return JSONResponse(status_code=status, content={"error": err})
        assert row is not None
    from app.controllers.web_controller import clear_page_image_cache

    clear_page_image_cache()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(
        actor["email"] if actor else None,
        "page_image_created",
        {"page_key": page_key, "slot_key": slot_key},
    )
    return JSONResponse(content={"pageImage": row})


@router.post("/page-image-upload")
async def page_image_upload(request: Request, file: UploadFile = File(...)) -> JSONResponse:
    _require_admin(request)
    if not file.filename:
        return JSONResponse(status_code=400, content={"error": "missing file"})
    ext = Path(file.filename).suffix.lower()
    data = await file.read()
    err = _image_upload_error(file, data, ext)
    if err:
        return JSONResponse(status_code=400, content={"error": err})
    name = f"{uuid.uuid4().hex}{ext}"
    url, upload_err = _storage_upload("page-images", name, data, ext)
    if upload_err:
        return JSONResponse(status_code=503, content={"error": upload_err})
    from app.controllers.web_controller import clear_page_image_cache

    clear_page_image_cache()
    return JSONResponse(content={"url": url})


@router.post("/page-image-update")
async def admin_page_image_update(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    from app.content import parse_page_image_payload, serialize_page_image

    fields, err = parse_page_image_payload(body)
    if err:
        return JSONResponse(status_code=400, content={"error": err})
    assert fields is not None
    page_key = fields["page_key"]
    slot_key = fields["slot_key"]
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select * from page_images where page_key = %s and slot_key = %s",
            (page_key, slot_key),
        )
        existing = cur.fetchone()
        if not existing:
            return JSONResponse(status_code=404, content={"error": "找不到頁面圖片設定"})
        if existing.get("group_key") == "cms-section":
            from app.cms_section_images import update_section_from_page_image

            update_section_from_page_image(
                cur,
                page_key=page_key,
                slot_key=slot_key,
                image_url=fields["image_url"] if fields["is_published"] else "",
                image_alt=fields["image_alt"],
                image_webp=fields.get("image_webp"),
            )
            cur.execute(
                "select * from page_images where page_key = %s and slot_key = %s",
                (page_key, slot_key),
            )
            row = serialize_page_image(cur.fetchone())
        else:
            sets = [
                "image_url = %s",
                "image_alt = %s",
                "is_published = %s",
                "updated_at = now()",
            ]
            params: list = [fields["image_url"], fields["image_alt"], fields["is_published"]]
            if "image_webp" in fields:
                sets.insert(1, "image_webp = %s")
                params.insert(1, fields["image_webp"])
            params.extend((page_key, slot_key))
            cur.execute(
                f"""
                update page_images set {', '.join(sets)}
                where page_key = %s and slot_key = %s
                returning *
                """,
                params,
            )
            row = serialize_page_image(cur.fetchone())
    from app.controllers.web_controller import clear_page_image_cache, clear_site_cms_cache

    clear_page_image_cache()
    clear_site_cms_cache()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(
        actor["email"] if actor else None,
        "page_image_updated",
        {"page_key": page_key, "slot_key": slot_key},
    )
    return JSONResponse(content={"pageImage": row})


@router.post("/page-image-action")
async def admin_page_image_action(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    page_key = str(body.get("pageKey") or body.get("page_key") or body.get("id") or "").strip()
    slot_key = str(body.get("slotKey") or body.get("slot_key") or "").strip()
    action = body.get("action")
    if (
        not page_key
        or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", slot_key)
        or action not in {"publish", "unpublish", "reset"}
    ):
        return JSONResponse(status_code=400, content={"error": "invalid page_key/slot_key/action"})
    from app.content import serialize_page_image

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select * from page_images where page_key = %s and slot_key = %s",
            (page_key, slot_key),
        )
        existing = cur.fetchone()
        if not existing:
            return JSONResponse(status_code=404, content={"error": "找不到頁面圖片設定"})
        if existing.get("group_key") == "cms-section":
            from app.cms_section_images import update_section_from_page_image

            keep_image = action == "publish"
            update_section_from_page_image(
                cur,
                page_key=page_key,
                slot_key=slot_key,
                image_url=existing.get("image_url") if keep_image else "",
                image_alt=existing.get("image_alt") or "",
                image_webp=existing.get("image_webp") if keep_image else None,
            )
            cur.execute(
                "select * from page_images where page_key = %s and slot_key = %s",
                (page_key, slot_key),
            )
        elif action == "publish":
            cur.execute(
                """
                update page_images
                set is_published = true, updated_at = now()
                where page_key = %s and slot_key = %s
                returning *
                """,
                (page_key, slot_key),
            )
        elif action == "unpublish":
            cur.execute(
                """
                update page_images
                set is_published = false, updated_at = now()
                where page_key = %s and slot_key = %s
                returning *
                """,
                (page_key, slot_key),
            )
        else:
            cur.execute(
                """
                update page_images
                set image_url = default_image_url,
                    image_webp = default_image_webp,
                    is_published = true,
                    updated_at = now()
                where page_key = %s and slot_key = %s
                returning *
                """,
                (page_key, slot_key),
            )
        row = cur.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "找不到頁面圖片設定"})
        payload = serialize_page_image(row)
    from app.controllers.web_controller import clear_page_image_cache, clear_site_cms_cache

    clear_page_image_cache()
    clear_site_cms_cache()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        actor = cur.fetchone()
    log_admin_action(
        actor["email"] if actor else None,
        f"page_image_{action}",
        {"page_key": page_key, "slot_key": slot_key},
    )
    return JSONResponse(content={"ok": True, "pageImage": payload})
