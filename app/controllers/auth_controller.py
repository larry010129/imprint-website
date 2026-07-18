"""Auth routes — /api/auth/* (same-origin session cookies, Supabase Postgres)."""

from __future__ import annotations

import math

import psycopg
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.auth import (
    LOGIN_LOCKOUT_SECONDS,
    LOGIN_MAX_ATTEMPTS,
    REGISTER_LOCKOUT_SECONDS,
    REGISTER_MAX_ATTEMPTS,
    check_login_lockout,
    check_register_lockout,
    clear_session_cookie,
    consume_invite_code,
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

router = APIRouter(prefix="/auth", tags=["auth"])


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
    if len(password) < 6:
        return _err(400, "密碼至少需要 6 碼")

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
            "select id, email, password_hash from users where email = %s",
            (normalized_email,),
        )
        user = cur.fetchone()

    if not user or not verify_password(password, user["password_hash"]):
        record_failure(lockout_key, LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECONDS)
        return _err(401, "Email 或密碼不正確")

    record_success(lockout_key)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("update users set last_login_at = now() where id = %s", (user["id"],))

    token = sign_session(str(user["id"]))
    result = JSONResponse(content={"ok": True, "user": {"id": str(user["id"]), "email": user["email"]}})
    set_session_cookie(result, token, request)
    return result


@router.post("/logout")
async def logout() -> JSONResponse:
    result = JSONResponse(content={"ok": True})
    clear_session_cookie(result)
    return result


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

        cur.execute("select full_name, phone from profiles where id = %s", (user_id,))
        profile = cur.fetchone()

    return JSONResponse(
        content={
            "user": {"id": str(user["id"]), "email": user["email"]},
            "profile": profile,
            "isAdmin": is_admin(user_id),
        }
    )
