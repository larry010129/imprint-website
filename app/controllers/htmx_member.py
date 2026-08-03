"""HTMX member partials — contact, track, favorites, history, notifications, account, profile, stories."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.account_delete import delete_blocked_reason, hard_delete_user
from app.auth import (
    clear_pre2fa_cookie,
    clear_session_cookie,
    enforce_rate_limit,
    get_user_id,
    is_admin,
)
from app.auth_totp_service import verify_step_up_password
from app.controllers.htmx_common import form_bool, html, hx_redirect
from app.database import get_connection
from app.membership_config import load_config
from app.membership_referral import count_invites_since, rolling_two_year_start
from app.membership_tiers import (
    build_account_membership,
    derive_member_display_number,
    format_member_id_groups,
)
from app.onboarding import (
    mark_onboarding_complete_if_ready,
    needs_member_onboarding,
    profile_fields_complete,
    should_show_onboarding_prompt,
)
from app.profile_schema import fetch_profile

router = APIRouter(tags=["htmx-member"])


def _format_member_since(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y/%m/%d")
    text = str(value).strip()
    return text[:10].replace("-", "/") if text else None


def _delete_error(message: str, status: int = 400) -> HTMLResponse:
    return HTMLResponse(
        f'<p class="account-delete-dialog__error" role="alert">{message}</p>',
        status_code=status,
    )


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
    if not enforce_rate_limit(request, action="track-order", limit=10, window_seconds=600):
        return html(
            request, "track_result.html", {"error": "請求過於頻繁，請稍後再試", "rows": []}, 429
        )
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
    from app.orders import attach_order_display, enrich_member_order

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select * from orders where user_id = %s order by created_at desc",
            (user_id,),
        )
        orders = cur.fetchall()
        if orders:
            attach_order_display(cur, orders)
            for order in orders:
                enrich_member_order(order)
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
async def account_partial(request: Request) -> Response:
    user_id = get_user_id(request)
    if not user_id:
        return html(request, "account_panel.html", {"guest": True, "user": None, "profile": None})
    show_onboarding_prompt = should_show_onboarding_prompt(request, user_id)
    admin = is_admin(user_id)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select id, email, google_id, totp_enabled, created_at from users where id = %s",
            (user_id,),
        )
        user = cur.fetchone()
        profile = fetch_profile(cur, user_id) if user else None
        orders: list = []
        invite_count = 0
        membership = None
        if user:
            cur.execute(
                """
                select status, total_price, created_at
                from orders where user_id = %s
                """,
                (user_id,),
            )
            orders = cur.fetchall() or []
            try:
                invite_count = count_invites_since(cur, user_id, rolling_two_year_start())
            except Exception:
                invite_count = 0
            config = load_config(cur)
            membership = build_account_membership(
                profile=profile,
                orders=orders,
                invite_count=invite_count,
                is_admin=admin,
                config=config,
            )
    return html(
        request,
        "account_panel.html",
        {
            "guest": False,
            "user": user,
            "profile": profile,
            "is_admin": admin,
            "totp_enabled": bool(user.get("totp_enabled")) if user else False,
            "membership": membership,
            "member_id_display": format_member_id_groups(str(user["id"])) if user else "",
            "member_id_copy": derive_member_display_number(str(user["id"])) if user else "",
            "member_since": _format_member_since(user.get("created_at")) if user else None,
            "login_type": "Google" if user and user.get("google_id") else "電子郵件",
            "show_onboarding_prompt": show_onboarding_prompt,
        },
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile_partial(request: Request) -> HTMLResponse:
    user_id = get_user_id(request)
    if not user_id:
        return html(request, "profile_form.html", {"guest": True, "onboarding": False})
    onboarding = (
        needs_member_onboarding(user_id)
        or str(request.query_params.get("onboarding") or "").strip() == "1"
    )
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id, email from users where id = %s", (user_id,))
        user = cur.fetchone()
        profile = fetch_profile(cur, user_id)
    return html(
        request,
        "profile_form.html",
        {
            "guest": False,
            "user": user,
            "profile": profile or {},
            "saved": False,
            "error": None,
            "onboarding": onboarding,
        },
    )


@router.post("/profile", response_class=HTMLResponse)
async def profile_save(request: Request) -> Response:
    user_id = get_user_id(request)
    if not user_id:
        return html(request, "profile_form.html", {"guest": True, "onboarding": False}, 401)
    form = await request.form()
    onboarding = (
        needs_member_onboarding(user_id)
        or form_bool(form.get("onboarding"))
        or str(request.query_params.get("onboarding") or "").strip() == "1"
    )
    full_name = str(form.get("fullName") or "").strip()
    phone = str(form.get("phone") or "").strip()
    shipping_postal = str(form.get("shippingPostal") or "").strip() or None
    shipping_city = str(form.get("shippingCity") or "").strip() or None
    shipping_address = str(form.get("shippingAddress") or "").strip() or None

    draft = {
        "full_name": full_name,
        "phone": phone,
        "shipping_postal": shipping_postal,
        "shipping_city": shipping_city,
        "shipping_address": shipping_address,
    }
    if onboarding and not profile_fields_complete(draft):
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select id, email from users where id = %s", (user_id,))
            user = cur.fetchone()
            profile = fetch_profile(cur, user_id) or {}
        merged = {**profile, **draft}
        return html(
            request,
            "profile_form.html",
            {
                "guest": False,
                "user": user,
                "profile": merged,
                "saved": False,
                "error": "請完整填寫姓名、電話與寄送地址。",
                "onboarding": True,
            },
            400,
        )

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
        mark_onboarding_complete_if_ready(cur, user_id, draft)
        cur.execute("select id, email from users where id = %s", (user_id,))
        user = cur.fetchone()
        profile = fetch_profile(cur, user_id)

    if onboarding and profile_fields_complete(profile):
        return hx_redirect("/account.html")

    return html(
        request,
        "profile_form.html",
        {
            "guest": False,
            "user": user,
            "profile": profile or {},
            "saved": True,
            "error": None,
            "onboarding": False,
        },
    )


@router.post("/account/delete")
async def account_delete(request: Request) -> Response:
    """Hard-delete the authenticated user, clear session, redirect home."""
    user_id = get_user_id(request)
    if not user_id:
        return _delete_error("請先登入。", 401)
    if not enforce_rate_limit(request, action="account-delete", limit=5, window_seconds=600):
        return _delete_error("操作過於頻繁，請稍後再試。", 429)

    form = await request.form()
    confirm_email = str(form.get("confirmEmail") or "").strip().lower()
    password = str(form.get("password") or "")
    totp_code = str(form.get("totpCode") or form.get("code") or "").strip()
    if not confirm_email:
        return _delete_error("請輸入 Email 以確認刪除。")
    if not password:
        return _delete_error("請輸入目前密碼以確認刪除。")

    step_err = verify_step_up_password(user_id, password, totp_code or None)
    if step_err:
        return _delete_error(step_err, 401)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id, email from users where id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            return _delete_error("找不到帳戶。", 404)
        if confirm_email != str(user.get("email") or "").strip().lower():
            return _delete_error("Email 不符，請輸入目前帳戶的 Email。")
        blocked = delete_blocked_reason(cur, user_id)
        if blocked:
            return _delete_error(blocked, 403)
        hard_delete_user(cur, user_id)

    resp = hx_redirect("/")
    clear_session_cookie(resp, request)
    clear_pre2fa_cookie(resp, request)
    return resp


@router.get("/account-security", response_class=HTMLResponse)
async def account_security_partial(request: Request) -> HTMLResponse:
    user_id = get_user_id(request)
    if not user_id:
        return html(request, "totp_security_panel.html", {"guest": True})
    admin = is_admin(user_id)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select id, email, totp_enabled from users where id = %s",
            (user_id,),
        )
        user = cur.fetchone()
    return html(
        request,
        "totp_security_panel.html",
        {
            "guest": False,
            "user": user,
            "totp_enabled": bool(user.get("totp_enabled")) if user else False,
            "is_admin": admin,
        },
    )


@router.get("/stories", response_class=HTMLResponse)
async def stories_partial(request: Request) -> HTMLResponse:
    from app.content import fetch_published_testimonials

    with get_connection() as conn, conn.cursor() as cur:
        items = fetch_published_testimonials(cur)
    return html(request, "stories_list.html", {"testimonials": items})
