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
from app.orders import (
    HISTORY_TABS,
    HISTORY_TAB_STATUSES,
    normalize_history_tab as _normalize_history_tab,
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
    email = str(form.get("email") or "").strip()
    preferred_dates = form.getlist("preferred_date")
    preferred_slots = form.getlist("preferred_slot")
    slot_pairs = []
    for raw_date, raw_slot in zip(preferred_dates, preferred_slots):
        date_part = str(raw_date or "").strip()
        slot_part = str(raw_slot or "").strip()
        if date_part or slot_part:
            slot_pairs.append(f"{date_part} {slot_part}".strip())
    if slot_pairs:
        lines = "\n".join(f"{i + 1}. {pair}" for i, pair in enumerate(slot_pairs[:3]))
        message = f"{message}\n\n【希望預約時段】\n{lines}"
    if not name or not phone or not email or not message:
        return html(
            request, "form_msg.html", {"ok": False, "message": "請填寫姓名、電話、Email 與您的需求"}, 400
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


HISTORY_DEFAULT_PAGE_SIZE = 20
FAVORITES_DEFAULT_PAGE_SIZE = 20
ACCOUNT_ORDERS_PAGE_SIZE = 12


@router.get("/favorites", response_class=HTMLResponse)
async def favorites_partial(request: Request) -> HTMLResponse:
    from app.paging import parse_paging_from_mapping, sql_count_total

    user_id = get_user_id(request)
    page, page_size, limit, offset = parse_paging_from_mapping(
        request.query_params, default_page_size=FAVORITES_DEFAULT_PAGE_SIZE
    )
    if not user_id:
        return html(
            request,
            "favorites_list.html",
            {
                "items": [],
                "guest": True,
                "page": page,
                "page_size": page_size,
                "total": 0,
                "has_more": False,
            },
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
            (user_id, limit, offset),
        )
        items = cur.fetchall()
    return html(
        request,
        "favorites_list.html",
        {
            "items": items,
            "guest": False,
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_more": offset + len(items) < total,
        },
    )


def _empty_history_context(*, guest: bool, tab: str = "all") -> dict:
    active = _normalize_history_tab(tab)
    return {
        "orders": [],
        "active_tab": active,
        "all_count": 0,
        "unpaid_count": 0,
        "to_ship_count": 0,
        "to_receive_count": 0,
        "completed_count": 0,
        "cancelled_count": 0,
        "page": 1,
        "page_size": HISTORY_DEFAULT_PAGE_SIZE,
        "total": 0,
        "has_more": False,
        "guest": guest,
    }


def _history_tab_counts(cur, user_id: str) -> dict[str, int]:
    cur.execute(
        """
        select lower(status) as status, count(*)::int as n
        from orders
        where user_id = %s
        group by lower(status)
        """,
        (user_id,),
    )
    by_status = {
        str(row["status"] or "").strip().lower(): int(row["n"] or 0)
        for row in cur.fetchall()
    }
    counts = {tab: 0 for tab in HISTORY_TABS}
    counts["all"] = sum(by_status.values())
    for tab, statuses in HISTORY_TAB_STATUSES.items():
        counts[tab] = sum(by_status.get(s, 0) for s in statuses)
    return counts


def _history_list_context(
    user_id: str,
    *,
    tab: str = "all",
    page=None,
    page_size=None,
) -> dict:
    from app.orders import attach_order_display, enrich_member_order
    from app.paging import parse_paging, sql_count_total

    active_tab = _normalize_history_tab(tab)
    page_i, size_i, limit, offset = parse_paging(
        page, page_size, default_page_size=HISTORY_DEFAULT_PAGE_SIZE
    )
    statuses = HISTORY_TAB_STATUSES.get(active_tab)

    with get_connection() as conn, conn.cursor() as cur:
        counts = _history_tab_counts(cur, user_id)
        if statuses is None:
            total = sql_count_total(
                cur,
                "select count(*) as n from orders where user_id = %s",
                (user_id,),
            )
            cur.execute(
                """
                select * from orders
                where user_id = %s
                order by created_at desc
                limit %s offset %s
                """,
                (user_id, limit, offset),
            )
        else:
            status_list = list(statuses)
            total = sql_count_total(
                cur,
                """
                select count(*) as n from orders
                where user_id = %s and lower(status) = any(%s)
                """,
                (user_id, status_list),
            )
            cur.execute(
                """
                select * from orders
                where user_id = %s and lower(status) = any(%s)
                order by created_at desc
                limit %s offset %s
                """,
                (user_id, status_list, limit, offset),
            )
        orders = cur.fetchall()
        if orders:
            attach_order_display(cur, orders)
            for order in orders:
                enrich_member_order(order)

    return {
        "orders": orders,
        "active_tab": active_tab,
        "all_count": counts["all"],
        "unpaid_count": counts["unpaid"],
        "to_ship_count": counts["to_ship"],
        "to_receive_count": counts["to_receive"],
        "completed_count": counts["completed"],
        "cancelled_count": counts["cancelled"],
        "page": page_i,
        "page_size": size_i,
        "total": total,
        "has_more": offset + len(orders) < total,
        "guest": False,
    }


def _history_context_from_request(
    request: Request, user_id: str, *, tab: str | None = None
) -> dict:
    from app.paging import parse_paging_from_mapping

    qp = request.query_params
    active = _normalize_history_tab(tab if tab is not None else qp.get("tab"))
    page, page_size, _, _ = parse_paging_from_mapping(
        qp, default_page_size=HISTORY_DEFAULT_PAGE_SIZE
    )
    return _history_list_context(
        user_id, tab=active, page=page, page_size=page_size
    )


@router.get("/history", response_class=HTMLResponse)
async def history_partial(request: Request) -> HTMLResponse:
    user_id = get_user_id(request)
    if not user_id:
        return html(
            request,
            "history_list.html",
            _empty_history_context(
                guest=True, tab=request.query_params.get("tab")
            ),
        )
    ctx = _history_context_from_request(request, user_id)
    if str(request.query_params.get("partial") or "").strip().lower() == "rows":
        prefixes = {
            "all": "history-detail-",
            "unpaid": "history-unpaid-detail-",
            "to_ship": "history-toship-detail-",
            "to_receive": "history-toreceive-detail-",
            "completed": "history-completed-detail-",
            "cancelled": "history-cancelled-detail-",
        }
        ctx["detail_prefix"] = prefixes.get(ctx["active_tab"], "history-detail-")
        return html(request, "history_rows_page.html", ctx)
    return html(request, "history_list.html", ctx)


@router.post("/history/cancel", response_class=HTMLResponse)
async def history_cancel_order(request: Request) -> HTMLResponse:
    """Member cancels own order (before 訂金已確認); dropdown fills always-visible note."""
    user_id = get_user_id(request)
    if not user_id:
        return html(
            request,
            "history_list.html",
            _empty_history_context(guest=True),
            401,
        )
    if not enforce_rate_limit(request, action="history-cancel", limit=20, window_seconds=600):
        ctx = _history_context_from_request(request, user_id)
        ctx["flash_ok"] = False
        ctx["flash_message"] = "操作過於頻繁，請稍後再試"
        return html(request, "history_list.html", ctx, 429)

    from app.orders import (
        MEMBER_CANCEL_REASON_PRESETS,
        can_member_cancel_order,
        notify_order_cancelled,
        resolve_member_cancel_reason,
    )

    form = await request.form()
    order_id = str(form.get("order_id") or "").strip()
    # Form: cancel_preset=<select>, cancel_reason=<textarea always visible>
    preset = str(form.get("cancel_preset") or "").strip()
    note = str(form.get("cancel_reason") or form.get("cancel_note") or "").strip()
    # Legacy: select was named cancel_reason; optional cancel_note for 其他
    if not preset:
        legacy = str(form.get("cancel_reason") or "").strip()
        if legacy in MEMBER_CANCEL_REASON_PRESETS:
            preset = legacy
            note = str(form.get("cancel_note") or "").strip()
            if preset != "其他" and not note:
                note = preset
    reason = resolve_member_cancel_reason(preset, note)

    flash_ok = False
    flash_message = ""
    status_code = 200
    if not order_id:
        flash_ok = False
        flash_message = "缺少訂單編號"
        status_code = 400
    elif not reason:
        flash_ok = False
        flash_message = "請選擇取消原因並填寫說明"
        status_code = 400
    else:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select id, user_id, order_number, status, summary_zh
                from orders
                where id = %s and user_id = %s
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
                if status in {"cancelled", "canceled"}:
                    flash_ok = False
                    flash_message = "訂單已取消"
                    status_code = 400
                elif not can_member_cancel_order(status):
                    flash_ok = False
                    flash_message = "訂金已確認後無法取消，如需協助請聯繫客服"
                    status_code = 400
                else:
                    cur.execute(
                        """
                        update orders
                        set status = 'cancelled',
                            cancel_reason = %s,
                            status_note = %s,
                            updated_at = now()
                        where id = %s
                          and user_id = %s
                          and lower(status) in ('received', 'order_confirming')
                        """,
                        (reason, reason, order_id, user_id),
                    )
                    if cur.rowcount == 0:
                        flash_ok = False
                        flash_message = "訂金已確認後無法取消，如需協助請聯繫客服"
                        status_code = 400
                    else:
                        notify_order_cancelled(cur, order, reason)
                        flash_ok = True
                        flash_message = "訂單已取消（可於不成立查看）"
                        status_code = 200

    land_tab = "cancelled" if flash_ok else request.query_params.get("tab")
    ctx = _history_context_from_request(request, user_id, tab=land_tab)
    ctx["flash_ok"] = flash_ok
    ctx["flash_message"] = flash_message
    return html(request, "history_list.html", ctx, status_code)


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
        ctx = _history_context_from_request(request, user_id)
        ctx["flash_ok"] = False
        ctx["flash_message"] = "操作過於頻繁，請稍後再試"
        return html(request, "history_list.html", ctx, 429)

    from datetime import datetime, timezone

    from psycopg.types.json import Jsonb

    from app.orders import merge_status_timestamps

    form = await request.form()
    order_id = str(form.get("order_id") or "").strip()
    if not order_id:
        ctx = _history_context_from_request(request, user_id)
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

    land_tab = "completed" if flash_ok else request.query_params.get("tab")
    ctx = _history_context_from_request(request, user_id, tab=land_tab)
    ctx["flash_ok"] = flash_ok
    ctx["flash_message"] = flash_message
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
            # Lightweight columns for membership stats (not a full order dump).
            # Soft safety cap — tier windows need more than a UI page of 12.
            cur.execute(
                """
                select status, total_price, created_at
                from orders
                where user_id = %s
                order by created_at desc
                limit 2000
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
    from app.content import (
        count_published_testimonials,
        fetch_published_testimonials,
    )
    from app.paging import page_window_from_params

    win = page_window_from_params(
        request.query_params,
        default_page_size=12,
        max_page_size=48,
    )
    with get_connection() as conn, conn.cursor() as cur:
        items = fetch_published_testimonials(
            cur, limit=win.limit, offset=win.offset
        )
        total = count_published_testimonials(cur)
    return html(
        request,
        "stories_list.html",
        {
            "testimonials": items,
            "page": win.page,
            "page_size": win.page_size,
            "total": total,
            "has_more": (win.offset + len(items)) < total,
            "append": win.page > 1,
        },
    )
