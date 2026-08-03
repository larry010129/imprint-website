"""HTMX cart + checkout partials — reuse shop_controller cart/coupon/checkout."""

from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.auth import get_user_id
from app.controllers.htmx_common import html, hx_redirect, json_error_message, templates
from app.controllers.shop_controller import (
    _cart_checkout_impl,
    fetch_cart_items,
    validate_coupon_body,
)
from app.database import get_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["htmx-shop"])


@router.get("/cart", response_class=HTMLResponse)
async def cart_partial(request: Request) -> HTMLResponse:
    user_id = get_user_id(request)
    if not user_id:
        return html(request, "cart_list.html", {"items": [], "guest": True})
    return html(request, "cart_list.html", {"items": fetch_cart_items(user_id), "guest": False})


@router.post("/cart/delete", response_class=HTMLResponse)
async def cart_delete(request: Request) -> HTMLResponse:
    user_id = get_user_id(request)
    if not user_id:
        return html(request, "cart_list.html", {"items": [], "guest": True}, 401)
    form = await request.form()
    item_id = str(form.get("id") or "").strip()
    if item_id:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "delete from cart_items where id = %s and user_id = %s", (item_id, user_id)
            )
    items = fetch_cart_items(user_id)
    resp = html(request, "cart_list.html", {"items": items, "guest": False})
    badge = templates.get_template("partials/htmx/cart_badge.html").render(
        {"request": request, "count": len(items), "oob": True}
    )
    body = resp.body.decode(resp.charset) + badge
    resp.body = body.encode(resp.charset)
    resp.headers["content-length"] = str(len(resp.body))
    return resp


@router.get("/checkout", response_class=HTMLResponse)
async def checkout_partial(request: Request) -> Response:
    from app.image_urls import is_uuid
    from app.profile_schema import fetch_profile

    raw_ids = (
        request.query_params.get("items") or request.query_params.get("item") or ""
    ).strip()
    user_id = get_user_id(request)
    if not user_id:
        next_path = "/checkout.html"
        if raw_ids:
            next_path = f"/checkout.html?items={raw_ids}"
        return hx_redirect("/login.html?next=" + quote(next_path, safe=""))
    item_ids = [
        s.strip() for s in raw_ids.split(",") if s.strip() and is_uuid(s.strip())
    ]
    if not item_ids:
        return hx_redirect("/cart.html")
    try:
        items = fetch_cart_items(user_id, item_ids)
    except Exception:
        logger.exception("htmx checkout fetch_cart_items failed")
        return hx_redirect("/cart.html")
    if not items:
        return hx_redirect("/cart.html")
    if any(i.get("available") is False for i in items):
        return hx_redirect("/cart.html")
    profile: dict = {}
    try:
        with get_connection() as conn, conn.cursor() as cur:
            profile = dict(fetch_profile(cur, user_id) or {})
            cur.execute("select email from users where id = %s", (user_id,))
            user_row = cur.fetchone() or {}
            profile["email"] = user_row.get("email") or profile.get("email") or ""
    except Exception:
        logger.exception("htmx checkout profile load failed")
        profile = {}
    subtotal = sum(float(i.get("total_price") or 0) for i in items)
    return html(
        request,
        "checkout_panel.html",
        {
            "items": items,
            "item_ids": [str(i["id"]) for i in items],
            "profile": profile,
            "subtotal": subtotal,
            "coupon": None,
            "coupon_error": None,
            "form_error": None,
            "fulfillment": "pickup",
            "order_note": "",
        },
    )


@router.post("/checkout/coupon", response_class=HTMLResponse)
async def checkout_coupon(request: Request) -> HTMLResponse:
    user_id = get_user_id(request)
    if not user_id:
        return html(
            request,
            "checkout_coupon_result.html",
            {"coupon_error": "請先登入", "oob_totals": False},
            401,
        )
    form = await request.form()
    code = str(form.get("couponCode") or "").strip()
    item_ids = [s for s in str(form.get("itemIds") or "").split(",") if s]
    items = fetch_cart_items(user_id, item_ids) if item_ids else []
    subtotal = sum(float(i.get("total_price") or 0) for i in items)
    result = await validate_coupon_body(user_id, {"code": code, "itemIds": item_ids or None})
    if isinstance(result, Response) and getattr(result, "status_code", 200) >= 400:
        return html(
            request,
            "checkout_coupon_result.html",
            {
                "coupon_error": json_error_message(result, "優惠碼無效"),
                "coupon": None,
                "subtotal": subtotal,
                "oob_totals": True,
            },
        )
    return html(
        request,
        "checkout_coupon_result.html",
        {
            "coupon": result,
            "coupon_error": None,
            "subtotal": subtotal,
            "oob_totals": True,
        },
    )


@router.post("/checkout/submit")
async def checkout_submit(request: Request) -> Response:
    user_id = get_user_id(request)
    if not user_id:
        return hx_redirect("/login.html")
    form = await request.form()
    item_ids = [s for s in str(form.get("itemIds") or "").split(",") if s]
    body = {
        "itemIds": item_ids,
        "customerName": str(form.get("customerName") or "").strip(),
        "customerPhone": str(form.get("customerPhone") or "").strip(),
        "customerEmail": str(form.get("customerEmail") or "").strip(),
        "fulfillmentMethod": str(form.get("fulfillmentMethod") or "pickup").strip(),
        "shippingAddress": str(form.get("shippingAddress") or "").strip(),
        "shippingCity": str(form.get("shippingCity") or "").strip(),
        "shippingPostal": str(form.get("shippingPostal") or "").strip(),
        "orderNote": str(form.get("orderNote") or "").strip(),
        "couponCode": str(form.get("couponCode") or "").strip(),
    }
    result = await _cart_checkout_impl(request, body)
    if isinstance(result, Response) and getattr(result, "status_code", 200) >= 400:
        items = fetch_cart_items(user_id, item_ids)
        return html(
            request,
            "checkout_panel.html",
            {
                "items": items,
                "item_ids": item_ids,
                "profile": {
                    "full_name": body["customerName"],
                    "phone": body["customerPhone"],
                    "email": body["customerEmail"],
                    "shipping_address": body["shippingAddress"],
                    "shipping_city": body["shippingCity"],
                    "shipping_postal": body["shippingPostal"],
                },
                "subtotal": sum(float(i.get("total_price") or 0) for i in items),
                "coupon": {"code": body["couponCode"]} if body["couponCode"] else None,
                "coupon_error": None,
                "form_error": json_error_message(result, "訂單建立失敗"),
                "fulfillment": body["fulfillmentMethod"],
                "order_note": body["orderNote"],
            },
            400,
        )
    nums = result.get("orderNumbers") or []
    if len(nums) == 1:
        return hx_redirect(f"/success.html?order={quote(nums[0])}")
    if nums:
        return hx_redirect("/success.html?orders=" + quote(",".join(nums)))
    return hx_redirect("/success.html")
