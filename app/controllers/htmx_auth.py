"""HTMX auth form partials — login / register / reset (reuse auth primitives)."""

from __future__ import annotations

import hashlib
import logging
import math
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.auth import (
    LOGIN_LOCKOUT_SECONDS,
    LOGIN_MAX_ATTEMPTS,
    REGISTER_LOCKOUT_SECONDS,
    REGISTER_MAX_ATTEMPTS,
    bump_token_version,
    check_login_lockout,
    check_register_lockout,
    consume_invite_code,
    enforce_rate_limit,
    hash_password,
    log_admin_action,
    record_failure,
    record_success,
    set_session_cookie,
    sign_session,
    validate_invite_code,
    verify_password,
)
from app.controllers.htmx_common import form_bool, html, hx_redirect
from app.database import get_connection
from app.membership_referral import apply_friend_referral, ensure_referral_code
from config.settings import settings

router = APIRouter(tags=["htmx-auth"])
log = logging.getLogger(__name__)


@router.post("/auth/login", response_class=HTMLResponse)
async def auth_login(request: Request) -> Response:
    form = await request.form()
    email = str(form.get("email") or "").strip()
    password = str(form.get("password") or "")
    remember = form_bool(form.get("remember"))
    next_url = str(form.get("next") or "/account.html").strip() or "/account.html"
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/account.html"

    if not email or not password:
        return html(request, "auth_error.html", {"error": "請輸入 Email 與密碼"}, 400)

    normalized = email.lower()
    lockout_key, locked = check_login_lockout(request, normalized)
    if locked:
        mins = math.ceil(LOGIN_LOCKOUT_SECONDS / 60)
        return html(
            request, "auth_error.html", {"error": f"登入失敗次數過多，請 {mins} 分鐘後再試"}, 429
        )

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select id, email, password_hash, token_version, is_active from users where email = %s",
            (normalized,),
        )
        user = cur.fetchone()

    if not user or not verify_password(password, user["password_hash"]):
        record_failure(lockout_key, LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECONDS)
        return html(request, "auth_error.html", {"error": "Email 或密碼不正確"}, 401)
    if not user["is_active"]:
        return html(request, "auth_error.html", {"error": "此帳號已被停用，請聯絡客服。"}, 403)

    record_success(lockout_key)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("update users set last_login_at = now() where id = %s", (user["id"],))

    token = sign_session(str(user["id"]), user["token_version"])
    resp = hx_redirect(next_url)
    set_session_cookie(resp, token, request, remember=remember)
    return resp


@router.post("/auth/register", response_class=HTMLResponse)
async def auth_register(request: Request) -> Response:
    form = await request.form()
    email = str(form.get("email") or "").strip()
    password = str(form.get("password") or "")
    password_confirm = str(form.get("passwordConfirm") or "")
    full_name = str(form.get("fullName") or "").strip()
    phone = str(form.get("phone") or "").strip()
    invite_code = form.get("inviteCode")
    referral_code = str(form.get("referralCode") or "").strip() or None
    accept_terms = form_bool(form.get("acceptTerms"))
    is_partner = form_bool(form.get("isPartner"))

    if not email or not password or not full_name or not phone:
        return html(request, "auth_error.html", {"error": "請完整填寫所有欄位"}, 400)
    if password != password_confirm:
        return html(request, "auth_error.html", {"error": "兩次密碼不一致"}, 400)
    if not accept_terms:
        return html(
            request, "auth_error.html", {"error": "請先閱讀並同意服務條款與隱私權政策"}, 400
        )
    if len(password) < 8:
        return html(request, "auth_error.html", {"error": "密碼至少需要 8 碼"}, 400)

    lockout_key, locked = check_register_lockout(request)
    if locked:
        mins = math.ceil(REGISTER_LOCKOUT_SECONDS / 60)
        return html(
            request, "auth_error.html", {"error": f"註冊失敗次數過多，請 {mins} 分鐘後再試"}, 429
        )

    code_for_validate = invite_code if is_partner else None
    if is_partner:
        invite_error = validate_invite_code(code_for_validate)
        if invite_error:
            record_failure(lockout_key, REGISTER_MAX_ATTEMPTS, REGISTER_LOCKOUT_SECONDS)
            return html(request, "auth_error.html", {"error": invite_error}, 400)

    normalized = email.lower()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from users where email = %s", (normalized,))
        if cur.fetchone():
            record_failure(lockout_key, REGISTER_MAX_ATTEMPTS, REGISTER_LOCKOUT_SECONDS)
            return html(request, "auth_error.html", {"error": "此 Email 已被註冊"}, 409)
        cur.execute(
            """
            insert into users (email, password_hash, email_verified)
            values (%s, %s, true) returning id, email
            """,
            (normalized, hash_password(password)),
        )
        user = cur.fetchone()
        cur.execute(
            "insert into profiles (id, full_name, phone) values (%s, %s, %s)",
            (user["id"], full_name, phone),
        )
        ensure_referral_code(cur, user["id"])
        if referral_code:
            apply_friend_referral(cur, user["id"], referral_code)

    grants = (
        consume_invite_code(code_for_validate, user["id"])
        if is_partner
        else {"grants_admin": False, "grants_partner": False}
    )
    if grants.get("grants_admin"):
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "insert into staff_admins (user_id) values (%s) on conflict do nothing",
                (user["id"],),
            )
        log_admin_action(user["email"], "invite_granted_admin", {"userId": user["id"]})
    elif grants.get("grants_partner"):
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("update profiles set is_partner = true where id = %s", (user["id"],))

    record_failure(lockout_key, REGISTER_MAX_ATTEMPTS, REGISTER_LOCKOUT_SECONDS)
    token = sign_session(str(user["id"]))
    resp = hx_redirect("/account.html")
    set_session_cookie(resp, token, request)
    return resp


@router.post("/auth/request-reset", response_class=HTMLResponse)
async def auth_request_reset(request: Request) -> HTMLResponse:
    if not enforce_rate_limit(request, action="pwreset", limit=5, window_seconds=900):
        return html(request, "auth_error.html", {"error": "請求過於頻繁，請稍後再試"}, 429)
    form = await request.form()
    email = str(form.get("email") or "").strip().lower()
    if email:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select id, email from users where email = %s and is_active = true", (email,)
            )
            user = cur.fetchone()
        if user:
            raw = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            expires = datetime.now(timezone.utc) + timedelta(hours=1)
            with get_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    "insert into password_reset_tokens (token, user_id, expires_at) values (%s, %s, %s)",
                    (token_hash, user["id"], expires),
                )
            reset_url = f"{settings.public_base_url}/reset-password.html?token={raw}"
            try:
                from app.mail import send_email

                send_email(
                    to=user["email"],
                    subject="銘印鑽石｜重設密碼",
                    text=(
                        "您好，\n\n我們收到您重設密碼的請求。請於 1 小時內點擊以下連結設定新密碼：\n\n"
                        f"{reset_url}\n\n若您沒有提出此請求，請忽略這封信。\n\n銘印鑽石 IMPRINT DIAMOND"
                    ),
                )
            except Exception:
                log.exception("htmx password reset email failed")
    return html(
        request,
        "auth_success.html",
        {"message": "若此 Email 已註冊，您將收到重設密碼信件。"},
    )


@router.post("/auth/reset-password", response_class=HTMLResponse)
async def auth_reset_password(request: Request) -> Response:
    form = await request.form()
    token = str(form.get("token") or "").strip()
    new_password = str(form.get("password") or "")
    if not token or not new_password:
        return html(request, "auth_error.html", {"error": "缺少驗證碼或新密碼"}, 400)
    if len(new_password) < 8:
        return html(request, "auth_error.html", {"error": "密碼至少需要 8 碼"}, 400)

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select token, user_id, expires_at, used_at from password_reset_tokens where token = %s",
            (token_hash,),
        )
        row = cur.fetchone()
        if not row or row["used_at"] is not None or row["expires_at"] < now:
            return html(
                request, "auth_error.html", {"error": "重設連結無效或已過期，請重新申請"}, 400
            )
        cur.execute(
            "update users set password_hash = %s where id = %s",
            (hash_password(new_password), row["user_id"]),
        )
        cur.execute(
            "update password_reset_tokens set used_at = %s where token = %s",
            (now, token_hash),
        )
    bump_token_version(str(row["user_id"]))
    return hx_redirect("/login.html")
