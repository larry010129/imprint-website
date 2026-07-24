"""Auth routes — /api/auth/* (same-origin session cookies, Supabase Postgres)."""

from __future__ import annotations

import hashlib
import logging
import math
import secrets
from datetime import datetime, timedelta, timezone

import psycopg
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.auth import (
    LOGIN_LOCKOUT_SECONDS,
    LOGIN_MAX_ATTEMPTS,
    REGISTER_LOCKOUT_SECONDS,
    REGISTER_MAX_ATTEMPTS,
    bump_token_version,
    check_login_lockout,
    check_register_lockout,
    clear_session_cookie,
    consume_invite_code,
    enforce_rate_limit,
    get_user_id,
    hash_password,
    is_admin,
    log_admin_action,
    record_failure,
    record_success,
    set_session_cookie,
    sign_session,
    validate_invite_code,
    verify_password,
)
from app.database import get_connection
from app.profile_schema import fetch_profile
from config.settings import settings

RESET_TOKEN_TTL_HOURS = 1


def _hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)


def _err(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


@router.post("/signup")
async def signup(request: Request, response: Response) -> JSONResponse:
    body = await request.json()
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    full_name = (body.get("fullName") or "").strip()
    phone = (body.get("phone") or "").strip()
    store_name = (body.get("storeName") or "").strip() or None
    invite_code = body.get("inviteCode")

    if not email or not password or not full_name or not phone:
        return _err(400, "請完整填寫所有欄位")
    if len(password) < 8:
        return _err(400, "密碼至少需要 8 碼")

    normalized_email = email.lower()

    lockout_key, locked = check_register_lockout(request)
    if locked:
        return _err(429, f"註冊失敗次數過多，請 {math.ceil(REGISTER_LOCKOUT_SECONDS / 60)} 分鐘後再試")

    invite_error = validate_invite_code(invite_code)
    if invite_error:
        record_failure(lockout_key, REGISTER_MAX_ATTEMPTS, REGISTER_LOCKOUT_SECONDS)
        return _err(400, invite_error)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from users where email = %s", (normalized_email,))
        if cur.fetchone():
            record_failure(lockout_key, REGISTER_MAX_ATTEMPTS, REGISTER_LOCKOUT_SECONDS)
            return _err(409, "此 Email 已被註冊")

        password_hash = hash_password(password)
        try:
            cur.execute(
                """
                insert into users (email, password_hash, email_verified)
                values (%s, %s, true)
                returning id, email
                """,
                (normalized_email, password_hash),
            )
            user = cur.fetchone()
            cur.execute(
                "insert into profiles (id, full_name, phone, store_name) values (%s, %s, %s, %s)",
                (user["id"], full_name, phone, store_name),
            )
        except psycopg.errors.UniqueViolation:
            # Two concurrent signups for the same email raced past the SELECT
            # check above; the DB's unique constraint is the real guard.
            record_failure(lockout_key, REGISTER_MAX_ATTEMPTS, REGISTER_LOCKOUT_SECONDS)
            return _err(409, "此 Email 已被註冊")

    grants = consume_invite_code(invite_code, user["id"])
    if grants["grants_admin"]:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "insert into staff_admins (user_id) values (%s) on conflict do nothing",
                (user["id"],),
            )
        log_admin_action(user["email"], "invite_granted_admin", {"userId": user["id"]})
    elif grants["grants_partner"]:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("update profiles set is_partner = true where id = %s", (user["id"],))

    # Unlike login, a successful signup still counts against the per-IP
    # register throttle (not cleared via record_success) — otherwise an
    # attacker using unique emails could mass-create accounts forever, since
    # every attempt would reset the counter back to zero right after it.
    record_failure(lockout_key, REGISTER_MAX_ATTEMPTS, REGISTER_LOCKOUT_SECONDS)

    token = sign_session(str(user["id"]))
    result = JSONResponse(content={"ok": True, "user": {"id": str(user["id"]), "email": user["email"]}})
    set_session_cookie(result, token, request)
    return result


@router.post("/login")
async def login(request: Request) -> JSONResponse:
    body = await request.json()
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    if not email or not password:
        return _err(400, "請輸入 Email 與密碼")

    normalized_email = email.lower()
    lockout_key, locked = check_login_lockout(request, normalized_email)
    if locked:
        return _err(429, f"登入失敗次數過多，請 {math.ceil(LOGIN_LOCKOUT_SECONDS / 60)} 分鐘後再試")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select id, email, password_hash, token_version, is_active from users where email = %s",
            (normalized_email,),
        )
        user = cur.fetchone()

    if not user or not verify_password(password, user["password_hash"]):
        record_failure(lockout_key, LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECONDS)
        return _err(401, "Email 或密碼不正確")

    if not user["is_active"]:
        return _err(403, "此帳號已被停用，請聯絡客服。 (This account has been deactivated.)")

    record_success(lockout_key)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("update users set last_login_at = now() where id = %s", (user["id"],))

    remember = body.get("remember", True)
    if isinstance(remember, str):
        remember = remember.strip().lower() not in ("0", "false", "no")

    token = sign_session(str(user["id"]), user["token_version"])
    result = JSONResponse(content={"ok": True, "user": {"id": str(user["id"]), "email": user["email"]}})
    set_session_cookie(result, token, request, remember=remember)
    return result


@router.post("/logout")
async def logout(request: Request) -> JSONResponse:
    user_id = get_user_id(request)
    if user_id:
        bump_token_version(user_id)
    result = JSONResponse(content={"ok": True})
    clear_session_cookie(result, request)
    return result


@router.post("/request-password-reset")
async def request_password_reset(request: Request) -> JSONResponse:
    # Always returns ok — never reveal whether an email is registered. Throttled
    # per-IP so it can't be used to blast reset emails at someone's inbox.
    if not enforce_rate_limit(request, action="pwreset", limit=5, window_seconds=900):
        return _err(429, "請求過於頻繁，請稍後再試")

    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    generic = JSONResponse(content={"ok": True})
    if not email:
        return generic

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id, email from users where email = %s and is_active = true", (email,))
        user = cur.fetchone()

    if not user:
        return generic  # same response as success — no account enumeration

    raw_token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_TTL_HOURS)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "insert into password_reset_tokens (token, user_id, expires_at) values (%s, %s, %s)",
            (_hash_reset_token(raw_token), user["id"], expires),
        )

    reset_url = f"{settings.public_base_url}/reset-password.html?token={raw_token}"
    try:
        from app.mail import send_email

        send_email(
            to=user["email"],
            subject="銘印鑽石｜重設密碼",
            text=(
                "您好，\n\n我們收到您重設密碼的請求。請於 1 小時內點擊以下連結設定新密碼：\n\n"
                f"{reset_url}\n\n若您沒有提出此請求，請忽略這封信，您的密碼不會變更。\n\n銘印鑽石 IMPRINT DIAMOND"
            ),
        )
    except Exception:
        log.exception("password reset email failed")

    return generic


@router.post("/reset-password")
async def reset_password(request: Request) -> JSONResponse:
    body = await request.json()
    token = (body.get("token") or "").strip()
    new_password = body.get("newPassword") or body.get("password") or ""
    if not token or not new_password:
        return _err(400, "缺少驗證碼或新密碼")
    if len(new_password) < 8:
        return _err(400, "密碼至少需要 8 碼")

    token_hash = _hash_reset_token(token)
    now = datetime.now(timezone.utc)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select token, user_id, expires_at, used_at from password_reset_tokens where token = %s",
            (token_hash,),
        )
        row = cur.fetchone()
        if not row or row["used_at"] is not None or row["expires_at"] < now:
            return _err(400, "重設連結無效或已過期，請重新申請")

        cur.execute(
            "update users set password_hash = %s where id = %s",
            (hash_password(new_password), row["user_id"]),
        )
        cur.execute(
            "update password_reset_tokens set used_at = now() where token = %s",
            (token_hash,),
        )

    # Invalidate every existing session for this user (the reset may be because
    # an attacker had access) — they must sign in again with the new password.
    bump_token_version(row["user_id"])
    return JSONResponse(content={"ok": True})


@router.get("/session")
async def session(request: Request) -> JSONResponse:
    user_id = get_user_id(request)
    if not user_id:
        return JSONResponse(content={"user": None})

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id, email from users where id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            return JSONResponse(content={"user": None})

        profile = fetch_profile(cur, user_id)

    return JSONResponse(
        content={
            "user": {"id": str(user["id"]), "email": user["email"]},
            "profile": profile,
            "isAdmin": is_admin(user_id),
        }
    )


@router.patch("/profile")
async def update_profile(request: Request) -> JSONResponse:
    user_id = get_user_id(request)
    if not user_id:
        return _err(401, "請先登入")

    body = await request.json()
    if not isinstance(body, dict):
        body = {}

    full_name = str(body.get("fullName") or body.get("full_name") or "").strip()
    phone = str(body.get("phone") or "").strip()
    shipping_postal = str(body.get("shippingPostal") or body.get("shipping_postal") or "").strip()
    shipping_city = str(body.get("shippingCity") or body.get("shipping_city") or "").strip()
    shipping_address = str(body.get("shippingAddress") or body.get("shipping_address") or "").strip()
    if not full_name:
        return _err(400, "請填寫姓名")
    if not phone:
        return _err(400, "請填寫聯絡電話")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into profiles (id, full_name, phone, shipping_postal, shipping_city, shipping_address)
            values (%s, %s, %s, %s, %s, %s)
            on conflict (id) do update set
              full_name = excluded.full_name,
              phone = excluded.phone,
              shipping_postal = excluded.shipping_postal,
              shipping_city = excluded.shipping_city,
              shipping_address = excluded.shipping_address
            returning full_name, phone, store_name, is_partner,
                      shipping_postal, shipping_city, shipping_address
            """,
            (user_id, full_name, phone, shipping_postal or None, shipping_city or None, shipping_address or None),
        )
        profile = cur.fetchone()

    return JSONResponse(content={"ok": True, "profile": profile})
