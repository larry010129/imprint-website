"""HTMX auth form partials — login / register / reset (reuse auth primitives)."""

from __future__ import annotations

import hashlib
import logging
import math
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app.auth import (
    LOGIN_LOCKOUT_SECONDS,
    LOGIN_MAX_ATTEMPTS,
    REGISTER_LOCKOUT_SECONDS,
    REGISTER_MAX_ATTEMPTS,
    TOTP_VERIFY_LOCKOUT_SECONDS,
    check_login_lockout,
    check_register_lockout,
    check_totp_verify_lockout,
    clear_pre2fa_cookie,
    clear_pwreset_cookie,
    consume_invite_code,
    enforce_rate_limit,
    get_pre2fa_user_id,
    get_pwreset_user_id,
    hash_password,
    is_valid_email,
    log_admin_action,
    record_failures,
    record_successes,
    set_pwreset_cookie,
    set_session_cookie,
    sign_pwreset,
    sign_session,
    validate_invite_code,
    validate_partner_invite_code,
    validate_register_email,
    verify_password,
)
from app.auth_post_login import apply_post_login_cookies, decide_post_login, safe_next_url
from app.auth_totp_service import (
    PWRESET_GENERIC_ERR,
    complete_password_reset,
    fetch_totp_user,
    verify_second_factor,
    verify_totp_for_pwreset,
)
from app.captcha import recaptcha_error_or_none
from app.controllers.htmx_common import form_bool, html, hx_redirect
from app.database import get_connection, get_transaction
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
    next_url = str(form.get("next") or "/account").strip() or "/account"
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/account"

    if not email or not password:
        return html(request, "auth_error.html", {"error": "請輸入 Email 與密碼"}, 400)

    normalized = email.lower()
    lockout_keys, locked = check_login_lockout(request, normalized)
    if locked:
        mins = math.ceil(LOGIN_LOCKOUT_SECONDS / 60)
        return html(
            request, "auth_error.html", {"error": f"登入失敗次數過多，請 {mins} 分鐘後再試"}, 429
        )

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select id, email, password_hash, token_version, is_active, totp_enabled
            from users where email = %s
            """,
            (normalized,),
        )
        user = cur.fetchone()

    if not user or not verify_password(password, user["password_hash"]):
        record_failures(lockout_keys, LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECONDS)
        return html(request, "auth_error.html", {"error": "Email 或密碼不正確"}, 401)
    if not user["is_active"]:
        return html(request, "auth_error.html", {"error": "此帳號已被停用，請聯絡客服。"}, 403)

    record_successes(lockout_keys)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("update users set last_login_at = now() where id = %s", (user["id"],))

    decision = decide_post_login(
        next_url=next_url,
        user_id=str(user["id"]),
        totp_enabled=bool(user.get("totp_enabled")),
        remember=remember,
    )
    resp = hx_redirect(decision.next_url)
    apply_post_login_cookies(resp, request, user, decision, remember=remember)
    return resp


@router.post("/auth/verify-2fa", response_class=HTMLResponse)
async def auth_verify_2fa(request: Request) -> Response:
    user_id = get_pre2fa_user_id(request)
    if not user_id:
        return html(request, "auth_error.html", {"error": "驗證已過期，請重新登入"}, 401)

    lockout_keys, locked = check_totp_verify_lockout(request, user_id)
    if locked:
        mins = math.ceil(TOTP_VERIFY_LOCKOUT_SECONDS / 60)
        return html(
            request,
            "auth_error.html",
            {"error": f"驗證失敗次數過多，請 {mins} 分鐘後再試"},
            429,
        )

    form = await request.form()
    code = str(form.get("code") or "").strip()
    if not code:
        return html(request, "auth_error.html", {"error": "請輸入驗證碼"}, 400)

    ok, err = verify_second_factor(user_id, code, lockout_key=lockout_keys)
    if not ok:
        return html(request, "auth_error.html", {"error": err or "驗證碼不正確"}, 401)

    user = fetch_totp_user(user_id)
    if not user:
        return html(request, "auth_error.html", {"error": "驗證已過期，請重新登入"}, 401)

    remember = form_bool(form.get("remember"))
    next_url = safe_next_url(str(form.get("next") or "/account"))
    decision = decide_post_login(
        next_url=next_url,
        user_id=user_id,
        totp_enabled=False,
        remember=remember,
    )
    resp = hx_redirect(decision.next_url)
    apply_post_login_cookies(resp, request, user, decision, remember=remember)
    clear_pre2fa_cookie(resp, request)
    return resp


@router.post("/auth/check-email")
async def auth_check_email(request: Request) -> JSONResponse:
    if not enforce_rate_limit(request, action="check-email", limit=10, window_seconds=600):
        return JSONResponse(
            status_code=429, content={"ok": False, "error": "請求過於頻繁，請稍後再試"}
        )
    form = await request.form()
    email = str(form.get("email") or "").strip()
    if not email:
        return JSONResponse(status_code=400, content={"ok": False, "error": "請輸入 Email"})
    email_error = validate_register_email(email)
    if email_error:
        return JSONResponse(status_code=400, content={"ok": False, "error": email_error})
    normalized = email.lower()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from users where email = %s", (normalized,))
        if cur.fetchone():
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "此 Email 已被註冊"},
            )
    return JSONResponse(content={"ok": True})


@router.post("/auth/check-invite")
async def auth_check_invite(request: Request) -> JSONResponse:
    if not enforce_rate_limit(request, action="check-invite", limit=10, window_seconds=600):
        return JSONResponse(
            status_code=429, content={"ok": False, "error": "請求過於頻繁，請稍後再試"}
        )
    form = await request.form()
    invite_code = str(form.get("inviteCode") or "").strip()
    invite_error = validate_partner_invite_code(invite_code)
    if invite_error:
        return JSONResponse(status_code=400, content={"ok": False, "error": invite_error})
    return JSONResponse(content={"ok": True})


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
    recaptcha_token = str(form.get("g-recaptcha-response") or "").strip()

    if not email or not password or not full_name or not phone:
        return html(request, "auth_error.html", {"error": "請完整填寫所有欄位"}, 400)
    email_error = validate_register_email(email)
    if email_error:
        return html(request, "auth_error.html", {"error": email_error}, 400)
    if password != password_confirm:
        return html(request, "auth_error.html", {"error": "兩次密碼不一致"}, 400)
    if not accept_terms:
        return html(
            request, "auth_error.html", {"error": "請先閱讀並同意服務條款與隱私權政策"}, 400
        )
    if len(password) < 8:
        return html(request, "auth_error.html", {"error": "密碼至少需要 8 碼"}, 400)

    lockout_keys, locked = check_register_lockout(request, email)
    if locked:
        mins = math.ceil(REGISTER_LOCKOUT_SECONDS / 60)
        return html(
            request, "auth_error.html", {"error": f"註冊失敗次數過多，請 {mins} 分鐘後再試"}, 429
        )

    captcha_error = recaptcha_error_or_none(request, recaptcha_token)
    if captcha_error:
        record_failures(lockout_keys, REGISTER_MAX_ATTEMPTS, REGISTER_LOCKOUT_SECONDS)
        return html(request, "auth_error.html", {"error": captcha_error}, 400)

    def _register_err(message: str, status: int = 400) -> HTMLResponse:
        record_failures(lockout_keys, REGISTER_MAX_ATTEMPTS, REGISTER_LOCKOUT_SECONDS)
        return html(request, "auth_error.html", {"error": message}, status)

    code_for_validate = str(invite_code or "").strip() or None
    if is_partner:
        invite_error = validate_partner_invite_code(code_for_validate)
        if invite_error:
            return _register_err(invite_error)
    else:
        invite_error = validate_invite_code(code_for_validate)
        if invite_error:
            return _register_err(invite_error)

    normalized = email.lower()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from users where email = %s", (normalized,))
        if cur.fetchone():
            return _register_err("此 Email 已被註冊", 409)
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

    record_failures(lockout_keys, REGISTER_MAX_ATTEMPTS, REGISTER_LOCKOUT_SECONDS)
    admin = bool(grants.get("grants_admin"))
    token = sign_session(str(user["id"]), is_admin=admin, remember=True)
    decision = decide_post_login(next_url="/account", user_id=str(user["id"]))
    resp = hx_redirect(decision.next_url)
    set_session_cookie(resp, token, request, remember=True, is_admin=admin)
    return resp


@router.post("/auth/forgot-password-verify", response_class=HTMLResponse)
async def auth_forgot_password_verify(request: Request) -> Response:
    form = await request.form()
    email = str(form.get("email") or "").strip()
    code = str(form.get("code") or "").strip()
    backup = form_bool(form.get("backup"))
    if not email:
        return html(request, "auth_error.html", {"error": "請輸入 Email。"}, 400)
    if not code:
        empty_code_err = "請輸入備用碼" if backup else "請輸入完整的 6 位數驗證碼。"
        return html(request, "auth_error.html", {"error": empty_code_err}, 400)
    if not is_valid_email(email):
        return html(request, "auth_error.html", {"error": "請輸入有效的 Email 格式。"}, 400)

    normalized = email.lower()
    if not enforce_rate_limit(
        request, action="pwreset-totp", limit=5, window_seconds=900, subject=normalized
    ):
        return html(request, "auth_error.html", {"error": "請求過於頻繁，請稍後再試。"}, 429)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from users where email = %s and is_active = true", (normalized,))
        row = cur.fetchone()
    lockout_keys = None
    if row:
        lockout_keys, locked = check_totp_verify_lockout(request, str(row["id"]))
        if locked:
            return html(
                request,
                "auth_error.html",
                {"error": "驗證失敗次數過多，請稍後再試。"},
                429,
            )

    user_id, err = verify_totp_for_pwreset(email, code, lockout_key=lockout_keys)
    if err:
        return html(request, "auth_error.html", {"error": PWRESET_GENERIC_ERR}, 401)

    resp = html(request, "auth_success.html", {"message": "驗證成功，請設定新密碼。"})
    set_pwreset_cookie(resp, sign_pwreset(user_id), request)
    return resp


@router.post("/auth/forgot-password", response_class=HTMLResponse)
async def auth_forgot_password(request: Request) -> Response:
    if not enforce_rate_limit(request, action="pwreset-totp", limit=5, window_seconds=900):
        return html(request, "auth_error.html", {"error": "請求過於頻繁，請稍後再試。"}, 429)

    user_id = get_pwreset_user_id(request)
    if not user_id:
        return html(
            request,
            "auth_error.html",
            {"error": "驗證已過期，請重新輸入 Email，或改從信件中的連結重設。"},
            401,
        )

    form = await request.form()
    new_password = str(form.get("password") or "")
    password_confirm = str(form.get("passwordConfirm") or "")
    if not new_password or not password_confirm:
        return html(request, "auth_error.html", {"error": "請輸入新密碼並再次確認。"}, 400)
    if new_password != password_confirm:
        return html(request, "auth_error.html", {"error": "兩次密碼不一致。"}, 400)
    if len(new_password) < 8:
        return html(request, "auth_error.html", {"error": "密碼至少需要 8 碼。"}, 400)

    complete_password_reset(user_id, new_password)
    resp = hx_redirect("/login")
    clear_pwreset_cookie(resp, request)
    return resp


@router.post("/auth/request-reset", response_class=HTMLResponse)
async def auth_request_reset(request: Request) -> HTMLResponse:
    # Email reset stays live for every active account, including Authenticator users.
    form = await request.form()
    email = str(form.get("email") or "").strip().lower()
    if not enforce_rate_limit(
        request, action="pwreset", limit=5, window_seconds=900, subject=email or None
    ):
        return html(request, "auth_error.html", {"error": "請求過於頻繁，請稍後再試。"}, 429)
    if not email:
        return html(request, "auth_error.html", {"error": "請輸入 Email。"}, 400)
    if not is_valid_email(email):
        return html(request, "auth_error.html", {"error": "請輸入有效的 Email 格式。"}, 400)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select id, email from users where email = %s and is_active = true", (email,)
        )
        user = cur.fetchone()
    if user:
        if not settings.reset_mail_base_ok():
            log.error("skip password-reset insert+mail: unsafe public_base_url on Render")
        else:
            raw = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            expires = datetime.now(timezone.utc) + timedelta(hours=1)
            with get_transaction() as conn, conn.cursor() as cur:
                cur.execute(
                    "update password_reset_tokens set used_at = now() where user_id = %s and used_at is null",
                    (user["id"],),
                )
                cur.execute(
                    "insert into password_reset_tokens (token, user_id, expires_at) values (%s, %s, %s)",
                    (token_hash, user["id"], expires),
                )
            reset_url = f"{settings.public_base_url}/reset-password?token={raw}"
            try:
                from app.mail import send_password_reset_email

                send_password_reset_email(to=user["email"], reset_url=reset_url)
            except Exception:
                log.exception("htmx password reset email failed")
    resp = html(
        request,
        "auth_success.html",
        {"message": "若此 Email 已註冊，重設連結已寄出。"},
    )
    resp.headers["HX-Trigger"] = "fp-email-sent"
    return resp


@router.post("/auth/reset-password", response_class=HTMLResponse)
async def auth_reset_password(request: Request) -> Response:
    form = await request.form()
    token = str(form.get("token") or "").strip()
    new_password = str(form.get("password") or "")
    password_confirm = str(form.get("passwordConfirm") or "")
    if not new_password or not password_confirm:
        return html(request, "auth_error.html", {"error": "請輸入新密碼並再次確認。"}, 400)
    if new_password != password_confirm:
        return html(request, "auth_error.html", {"error": "兩次密碼不一致。"}, 400)
    if len(new_password) < 8:
        return html(request, "auth_error.html", {"error": "密碼至少需要 8 碼。"}, 400)
    if not token:
        return html(
            request, "auth_error.html", {"error": "重設連結無效或已過期，請重新申請。"}, 400
        )

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    with get_transaction() as conn, conn.cursor() as cur:
        cur.execute(
            "select token, user_id, expires_at, used_at from password_reset_tokens where token = %s",
            (token_hash,),
        )
        row = cur.fetchone()
        if not row or row["used_at"] is not None or row["expires_at"] < now:
            return html(
                request, "auth_error.html", {"error": "重設連結無效或已過期，請重新申請。"}, 400
            )
        cur.execute(
            """
            update users
               set password_hash = %s,
                   token_version = token_version + 1
             where id = %s
            """,
            (hash_password(new_password), row["user_id"]),
        )
        cur.execute(
            "update password_reset_tokens set used_at = now() where user_id = %s and used_at is null",
            (row["user_id"],),
        )
    return hx_redirect("/login")
