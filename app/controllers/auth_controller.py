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
    verify_google_id_token,
    verify_password,
)
from app.database import get_connection
from app.google_people import (
    fetch_people_profile,
    merge_into_profile,
    parse_address,
    parse_phone,
    verify_access_token,
)
from app.profile_schema import fetch_profile
from config.settings import settings

RESET_TOKEN_TTL_HOURS = 1


def _hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)


def _err(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


def _session_payload(user: dict, profile: dict | None, user_id: str) -> dict:
    phone = (profile or {}).get("phone") if profile else None
    return {
        "user": {"id": str(user["id"]), "email": user["email"]},
        "profile": profile,
        "isAdmin": is_admin(user_id),
        "hasGoogleLinked": bool(user.get("google_id")),
        "profileComplete": bool(str(phone or "").strip()),
    }


def _backfill_google_name(cur, user_id: str, full_name: str) -> None:
    if not full_name:
        return
    cur.execute(
        """
        update profiles set full_name = %s
        where id = %s and coalesce(trim(full_name), '') = ''
        """,
        (full_name, user_id),
    )


@router.post("/signup")
async def signup(request: Request, response: Response) -> JSONResponse:
    body = await request.json()
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    full_name = (body.get("fullName") or "").strip()
    phone = (body.get("phone") or "").strip()
    store_name = (body.get("storeName") or "").strip() or None
    invite_code = body.get("inviteCode")
    accept_terms = body.get("acceptTerms")
    if isinstance(accept_terms, str):
        accept_terms = accept_terms.strip().lower() in ("1", "true", "yes", "on")

    if not email or not password or not full_name or not phone:
        return _err(400, "請完整填寫所有欄位")
    if not accept_terms:
        return _err(400, "請先閱讀並同意服務條款與隱私權政策")
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


@router.post("/google")
async def google_login(request: Request) -> JSONResponse:
    """Sign in / sign up with a Google Identity Services ID token (see
    public/js/google-signin.js). The credential is verified server-side —
    the client-sent profile fields are never trusted directly."""
    body = await request.json()
    credential = (body.get("credential") or "").strip()
    if not credential:
        return _err(400, "缺少 Google 登入憑證")

    idinfo = verify_google_id_token(credential)
    if not idinfo:
        return _err(401, "Google 登入驗證失敗，請再試一次")

    google_sub = idinfo.get("sub")
    email = (idinfo.get("email") or "").strip().lower()
    email_verified = bool(idinfo.get("email_verified"))
    full_name = (idinfo.get("name") or "").strip()
    if not google_sub or not email or not email_verified:
        return _err(401, "無法取得已驗證的 Google 帳號資訊")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select id, email, token_version, is_active from users where google_id = %s",
            (google_sub,),
        )
        user = cur.fetchone()

        if not user:
            # Same email already has a password account — link this Google
            # identity to it instead of creating a duplicate user.
            cur.execute(
                "select id, email, token_version, is_active from users where email = %s",
                (email,),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute("update users set google_id = %s where id = %s", (google_sub, existing["id"]))
                user = existing
                _backfill_google_name(cur, user["id"], full_name)
            else:
                # No password login is possible with this hash — it's a random
                # value the account owner never sees, not a usable credential.
                placeholder_hash = hash_password(secrets.token_urlsafe(32))
                cur.execute(
                    """
                    insert into users (email, password_hash, email_verified, google_id)
                    values (%s, %s, true, %s)
                    returning id, email, token_version, is_active
                    """,
                    (email, placeholder_hash, google_sub),
                )
                user = cur.fetchone()
                cur.execute(
                    "insert into profiles (id, full_name) values (%s, %s) on conflict (id) do nothing",
                    (user["id"], full_name or None),
                )
        else:
            _backfill_google_name(cur, user["id"], full_name)

    if not user["is_active"]:
        return _err(403, "此帳號已被停用，請聯絡客服。 (This account has been deactivated.)")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("update users set last_login_at = now() where id = %s", (user["id"],))

    token = sign_session(str(user["id"]), user["token_version"])
    result = JSONResponse(content={"ok": True, "user": {"id": str(user["id"]), "email": user["email"]}})
    set_session_cookie(result, token, request)
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
        cur.execute("select id, email, google_id from users where id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            return JSONResponse(content={"user": None})

        profile = fetch_profile(cur, user_id)

    return JSONResponse(content=_session_payload(user, profile, user_id))


@router.post("/google-enrich")
async def google_enrich(request: Request) -> JSONResponse:
    """Import phone/address from Google People API after user grants extra OAuth scopes."""
    user_id = get_user_id(request)
    if not user_id:
        return _err(401, "請先登入")

    body = await request.json()
    access_token = (body.get("access_token") or "").strip()
    if not access_token:
        return _err(400, "缺少 Google 授權")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id, email, google_id from users where id = %s", (user_id,))
        user = cur.fetchone()
        if not user or not user.get("google_id"):
            return _err(400, "此帳號未連結 Google，無法匯入")

        if not verify_access_token(
            access_token,
            expected_sub=user["google_id"],
            expected_email=user["email"],
        ):
            return _err(401, "Google 授權無效或已過期，請再試一次")

        people = fetch_people_profile(access_token)
        if not people:
            return _err(502, "無法讀取 Google 帳戶資料，請稍後再試")

        phone = parse_phone(people)
        address = parse_address(people)
        existing = fetch_profile(cur, user_id)
        updates = merge_into_profile(existing, phone, address)

        imported = {
            "phone": bool(updates.get("phone")),
            "address": any(
                updates.get(k) for k in ("shipping_postal", "shipping_city", "shipping_address")
            ),
        }

        if not updates:
            return JSONResponse(
                content={
                    "ok": True,
                    "profile": existing,
                    "imported": imported,
                    "message": "Google 帳戶中沒有可匯入的電話或地址，或您已填寫完成。",
                }
            )

        cur.execute("insert into profiles (id) values (%s) on conflict (id) do nothing", (user_id,))

        set_parts = []
        params: list[str] = []
        for key, val in updates.items():
            set_parts.append(f"{key} = %s")
            params.append(val)
        params.append(user_id)
        cur.execute(
            f"update profiles set {', '.join(set_parts)} where id = %s returning "
            "full_name, phone, store_name, is_partner, "
            "shipping_postal, shipping_city, shipping_address",
            params,
        )
        profile = cur.fetchone()

    return JSONResponse(content={"ok": True, "profile": profile, "imported": imported})


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
