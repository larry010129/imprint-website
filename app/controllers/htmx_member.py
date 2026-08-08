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
from app.tw_address import STREET_ERROR, valid_tw_street

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
    preferred_slot = str(form.get("preferred_slot") or "").strip()
    if preferred_slot:
        message = f"{message}\n\n【希望預約時段】{preferred_slot}"
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
            (name, phone, email, message, "/contact"),
        )
    try:
        from app.mail import notify_contact_message

        notify_contact_message(
            name=name, phone=phone, email=email, message=message, source_page="/contact"
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
    from app.orders import track_order_public_row

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
        rows = [track_order_public_row(dict(order))] if order else []
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


# Shopee-like history tabs → order.status codes (Imprint pipeline).
# No return/refund tab — custom DNA orders rarely allow returns.
HISTORY_TAB_STATUSES: dict[str, frozenset[str]] = {
    "unpaid": frozenset({"received", "order_confirming"}),
    "to_ship": frozenset(
        {"deposit_confirmed", "dna_lab", "in_production", "quality_check"}
    ),
    "to_receive": frozenset({"shipped"}),
    "completed": frozenset({"completed"}),
    "cancelled": frozenset({"cancelled", "canceled"}),
}


def _order_status_code(order: dict) -> str:
    return (order.get("status") or "").strip().lower()


def _orders_for_tab(orders: list, tab: str) -> list:
    statuses = HISTORY_TAB_STATUSES.get(tab)
    if statuses is None:
        return list(orders)
    if not statuses:
        return []
    return [o for o in orders if _order_status_code(o) in statuses]


def _empty_history_context(*, guest: bool) -> dict:
    return {
        "orders": [],
        "unpaid_orders": [],
        "to_ship_orders": [],
        "to_receive_orders": [],
        "completed_orders": [],
        "cancelled_orders": [],
        "guest": guest,
    }


def _history_list_context(user_id: str) -> dict:
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
    return {
        "orders": orders,
        "unpaid_orders": _orders_for_tab(orders, "unpaid"),
        "to_ship_orders": _orders_for_tab(orders, "to_ship"),
        "to_receive_orders": _orders_for_tab(orders, "to_receive"),
        "completed_orders": _orders_for_tab(orders, "completed"),
        "cancelled_orders": _orders_for_tab(orders, "cancelled"),
        "guest": False,
    }


@router.get("/history", response_class=HTMLResponse)
async def history_partial(request: Request) -> HTMLResponse:
    user_id = get_user_id(request)
    if not user_id:
        return html(
            request,
            "history_list.html",
            _empty_history_context(guest=True),
        )
    return html(request, "history_list.html", _history_list_context(user_id))


@router.post("/history/confirm-receipt", response_class=HTMLResponse)
async def history_confirm_receipt(request: Request) -> HTMLResponse:
    """Member marks shipped delivery order as received → completed."""
    user_id = get_user_id(request)
    if not user_id:
        return html(
            request,
            "history_list.html",
            _empty_history_context(guest=True),
            401,
        )
    if not enforce_rate_limit(request, action="confirm-receipt", limit=20, window_seconds=600):
        ctx = _history_list_context(user_id)
        ctx["flash_ok"] = False
        ctx["flash_message"] = "操作過於頻繁，請稍後再試"
        return html(request, "history_list.html", ctx, 429)

    from datetime import datetime, timezone

    from psycopg.types.json import Jsonb

    from app.orders import merge_status_timestamps

    form = await request.form()
    order_id = str(form.get("order_id") or "").strip()
    if not order_id:
        ctx = _history_list_context(user_id)
        ctx["flash_ok"] = False
        ctx["flash_message"] = "缺少訂單編號"
        return html(request, "history_list.html", ctx, 400)

    flash_ok = False
    flash_message = ""
    status_code = 200
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select o.id, o.status, o.status_timestamps, f.fulfillment_method
            from orders o
            left join order_fulfillment f on f.order_id = o.id
            where o.id = %s and o.user_id = %s
            """,
            (order_id, user_id),
        )
        order = cur.fetchone()
        if not order:
            flash_ok = False
            flash_message = "找不到訂單"
            status_code = 404
        else:
            status = (order.get("status") or "").strip().lower()
            method = (order.get("fulfillment_method") or "").strip().lower()
            # Delivery only: pickup uses 可取貨 + schedule, not confirm-receipt.
            if status != "shipped" or method != "delivery":
                flash_ok = False
                flash_message = "此訂單目前無法確認收到商品"
                status_code = 400
            else:
                now = datetime.now(timezone.utc)
                stamps = merge_status_timestamps(
                    order.get("status_timestamps"),
                    status,
                    "completed",
                    now,
                )
                cur.execute(
                    """
                    update orders
                    set status = 'completed',
                        status_timestamps = %s,
                        updated_at = now()
                    where id = %s and user_id = %s and status = 'shipped'
                    """,
                    (Jsonb(stamps), order_id, user_id),
                )
                if cur.rowcount == 0:
                    flash_ok = False
                    flash_message = "此訂單目前無法確認收到商品"
                    status_code = 400
                else:
                    flash_ok = True
                    flash_message = "已確認收到商品，訂單已完成（可於已完成查看）"
                    status_code = 200

    ctx = _history_list_context(user_id)
    ctx["flash_ok"] = flash_ok
    ctx["flash_message"] = flash_message
    if flash_ok:
        # Land on 已完成 after confirm-receipt.
        ctx["active_tab"] = "completed"
    return html(request, "history_list.html", ctx, status_code)


@router.post("/history/pickup-schedule", response_class=HTMLResponse)
async def history_pickup_schedule(request: Request) -> HTMLResponse:
    """Persist preferred store-pickup datetime for a ready-for-pickup order."""
    user_id = get_user_id(request)
    if not user_id:
        return html(
            request,
            "pickup_schedule.html",
            {"ok": False, "message": "請先登入", "order": None},
            401,
        )
    if not enforce_rate_limit(request, action="pickup-schedule", limit=20, window_seconds=600):
        return html(
            request,
            "pickup_schedule.html",
            {"ok": False, "message": "操作過於頻繁，請稍後再試", "order": None},
            429,
        )

    from app.orders import (
        attach_order_display,
        enrich_member_order,
        is_ready_for_pickup,
        parse_pickup_preferred_at,
    )

    form = await request.form()
    order_id = str(form.get("order_id") or "").strip()
    raw_preferred = str(form.get("pickup_preferred_at") or "").strip()
    pickup_date = str(form.get("pickup_date") or "").strip()
    pickup_slot = str(form.get("pickup_slot") or "").strip()
    if not raw_preferred and pickup_date and pickup_slot:
        raw_preferred = f"{pickup_date}T{pickup_slot}"
    schedule_target = str(form.get("schedule_target") or "").strip()
    if schedule_target and (
        not schedule_target.startswith("pickup-schedule-")
        or any(ch in schedule_target for ch in ('"', "'", "<", ">", " ", "\n", "\r"))
    ):
        schedule_target = ""

    def _pickup_ctx(ok: bool, message: str, order_row=None) -> dict:
        return {
            "ok": ok,
            "message": message,
            "order": order_row,
            "schedule_target": schedule_target,
        }

    if not order_id:
        return html(request, "pickup_schedule.html", _pickup_ctx(False, "缺少訂單編號"), 400)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select * from orders where id = %s and user_id = %s",
            (order_id, user_id),
        )
        order = cur.fetchone()
        if not order:
            return html(request, "pickup_schedule.html", _pickup_ctx(False, "找不到訂單"), 404)
        order = dict(order)
        attach_order_display(cur, [order])
        enrich_member_order(order)
        if not is_ready_for_pickup(order):
            return html(
                request,
                "pickup_schedule.html",
                _pickup_ctx(
                    False,
                    "此訂單目前不可預約取貨（需為門市自取且狀態為已出貨）",
                    order,
                ),
                400,
            )

        try:
            preferred_at = parse_pickup_preferred_at(raw_preferred)
        except ValueError as exc:
            return html(
                request,
                "pickup_schedule.html",
                _pickup_ctx(False, str(exc), order),
                400,
            )

        cur.execute(
            """
            update order_fulfillment
            set pickup_preferred_at = %s
            where order_id = %s
            """,
            (preferred_at, order_id),
        )
        if cur.rowcount == 0:
            cur.execute(
                """
                insert into order_fulfillment (order_id, fulfillment_method, pickup_preferred_at)
                values (%s, 'pickup', %s)
                on conflict (order_id) do update
                set pickup_preferred_at = excluded.pickup_preferred_at
                """,
                (order_id, preferred_at),
            )
        order["pickup_preferred_at"] = preferred_at
        enrich_member_order(order)

    return html(
        request,
        "pickup_schedule.html",
        _pickup_ctx(True, "已儲存希望取貨時間", order),
    )


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

    def _profile_error(message: str, *, status: int = 400):
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
                "error": message,
                "onboarding": onboarding,
            },
            status,
        )

    if onboarding and not profile_fields_complete(draft):
        return _profile_error("請完整填寫姓名、電話與寄送地址。")
    if shipping_address and not valid_tw_street(shipping_address):
        return _profile_error(STREET_ERROR)

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
        return hx_redirect("/account")

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
