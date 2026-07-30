"""HTMX member partials — contact, track, favorites, history, notifications, account, profile, stories."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.auth import enforce_rate_limit, get_user_id, is_admin
from app.controllers.htmx_common import html
from app.database import get_connection
from app.profile_schema import fetch_profile

router = APIRouter(tags=["htmx-member"])


@router.post("/contact", response_class=HTMLResponse)
async def contact_submit(request: Request) -> HTMLResponse:
    if not enforce_rate_limit(request, action="contact", limit=5, window_seconds=600):
        return html(request, "form_msg.html", {"ok": False, "message": "提交過於頻繁，請稍後再試"}, 429)
    form = await request.form()
    name = str(form.get("name") or "").strip()
    phone = str(form.get("phone") or "").strip()
    message = str(form.get("message") or "").strip()
    email = str(form.get("email") or "").strip() or None
    if not name or not phone or not message:
        return html(
            request, "form_msg.html", {"ok": False, "message": "請填寫姓名、電話與您的需求"}, 400
        )
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into contact_messages (name, phone, email, message, source_page)
            values (%s, %s, %s, %s, %s)
            """,
            (name, phone, email, message, "/contact.html"),
        )
    try:
        from app.mail import notify_contact_message

        notify_contact_message(
            name=name, phone=phone, email=email, message=message, source_page="/contact.html"
        )
    except Exception:
        pass
    return html(request, "form_msg.html", {"ok": True, "message": "已收到您的留言，顧問將盡快聯繫。"})


@router.post("/track-order", response_class=HTMLResponse)
async def track_order_partial(request: Request) -> HTMLResponse:
    form = await request.form()
    order_number = str(form.get("orderNumber") or "").strip()
    phone = str(form.get("phone") or "").strip()
    if not order_number or not phone:
        return html(
            request, "track_result.html", {"error": "請輸入訂單編號與電話", "rows": []}, 400
        )
    from app.orders import attach_order_relations, hydrate_order

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select o.* from orders o
            join order_contacts oc on oc.order_id = o.id
            where o.order_number = %s and oc.customer_phone = %s
            limit 1
            """,
            (order_number, phone),
        )
        order = cur.fetchone()
        rows = []
        if order:
            attach_order_relations(cur, [order])
            hydrate_order(order)
            rows = [order]
    return html(request, "track_result.html", {"error": None, "rows": rows})


@router.get("/favorites", response_class=HTMLResponse)
async def favorites_partial(request: Request) -> HTMLResponse:
    user_id = get_user_id(request)
    if not user_id:
        return html(request, "favorites_list.html", {"items": [], "guest": True})
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select * from favorite_items where user_id = %s order by created_at desc",
            (user_id,),
        )
        items = cur.fetchall()
    return html(request, "favorites_list.html", {"items": items, "guest": False})


@router.get("/history", response_class=HTMLResponse)
async def history_partial(request: Request) -> HTMLResponse:
    user_id = get_user_id(request)
    if not user_id:
        return html(request, "history_list.html", {"orders": [], "guest": True})
    from app.orders import attach_order_relations, hydrate_order

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select * from orders where user_id = %s order by created_at desc",
            (user_id,),
        )
        orders = cur.fetchall()
        if orders:
            attach_order_relations(cur, orders)
            for order in orders:
                hydrate_order(order)
    return html(request, "history_list.html", {"orders": orders, "guest": False})


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_partial(request: Request) -> HTMLResponse:
    user_id = get_user_id(request)
    if not user_id:
        return html(request, "notifications_list.html", {"groups": [], "guest": True})
    from app.controllers.notifications_controller import notifications_recent

    data = await notifications_recent(request)
    return html(
        request, "notifications_list.html", {"groups": data.get("groups") or [], "guest": False}
    )


@router.get("/account", response_class=HTMLResponse)
async def account_partial(request: Request) -> HTMLResponse:
    user_id = get_user_id(request)
    if not user_id:
        return html(request, "account_panel.html", {"guest": True, "user": None, "profile": None})
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id, email, google_id from users where id = %s", (user_id,))
        user = cur.fetchone()
        profile = fetch_profile(cur, user_id) if user else None
    return html(
        request,
        "account_panel.html",
        {"guest": False, "user": user, "profile": profile, "is_admin": is_admin(user_id)},
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile_partial(request: Request) -> HTMLResponse:
    user_id = get_user_id(request)
    if not user_id:
        return html(request, "profile_form.html", {"guest": True})
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id, email from users where id = %s", (user_id,))
        user = cur.fetchone()
        profile = fetch_profile(cur, user_id)
    return html(
        request,
        "profile_form.html",
        {"guest": False, "user": user, "profile": profile or {}, "saved": False, "error": None},
    )


@router.post("/profile", response_class=HTMLResponse)
async def profile_save(request: Request) -> HTMLResponse:
    user_id = get_user_id(request)
    if not user_id:
        return html(request, "profile_form.html", {"guest": True}, 401)
    form = await request.form()
    full_name = str(form.get("fullName") or "").strip()
    phone = str(form.get("phone") or "").strip()
    shipping_postal = str(form.get("shippingPostal") or "").strip() or None
    shipping_city = str(form.get("shippingCity") or "").strip() or None
    shipping_address = str(form.get("shippingAddress") or "").strip() or None
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("insert into profiles (id) values (%s) on conflict (id) do nothing", (user_id,))
        cur.execute(
            """
            update profiles set
              full_name = %s, phone = %s,
              shipping_postal = %s, shipping_city = %s, shipping_address = %s
            where id = %s
            """,
            (
                full_name or None,
                phone or None,
                shipping_postal,
                shipping_city,
                shipping_address,
                user_id,
            ),
        )
        cur.execute("select id, email from users where id = %s", (user_id,))
        user = cur.fetchone()
        profile = fetch_profile(cur, user_id)
    return html(
        request,
        "profile_form.html",
        {"guest": False, "user": user, "profile": profile or {}, "saved": True, "error": None},
    )


@router.get("/stories", response_class=HTMLResponse)
async def stories_partial(request: Request) -> HTMLResponse:
    from app.content import fetch_published_testimonials

    with get_connection() as conn, conn.cursor() as cur:
        items = fetch_published_testimonials(cur)
    return html(request, "stories_list.html", {"testimonials": items})
