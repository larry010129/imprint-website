"""Auth helpers — signed-JWT session cookie, login/register lockout, invite
codes. Ported from backend/lib/auth.js, lib/rateLimit.js and lib/invites.js
so this FastAPI app can serve /api/auth/* itself (see app/database.py).
"""

from __future__ import annotations

import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Request, Response

from app.config import settings
from app.database import get_connection

COOKIE_NAME = "imprint_session"
SESSION_DAYS = 30

LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300
REGISTER_MAX_ATTEMPTS = 10
REGISTER_LOCKOUT_SECONDS = 600


def _jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not set")
    return secret


# ── passwords ────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ── session cookie ───────────────────────────────────────────────────────

def sign_session(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)}
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def verify_session_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        path="/",
        httponly=True,
        secure=settings.is_render,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


def get_user_id(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return verify_session_token(token)


def is_admin(user_id: str | None) -> bool:
    if not user_id:
        return False
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select user_id from staff_admins where user_id = %s", (user_id,))
        return cur.fetchone() is not None


# ── login/register lockout (state lives in login_lockouts, not memory —
# this app runs across multiple gunicorn worker processes) ─────────────────

def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_locked_out(key: str) -> bool:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select fail_count, locked_until from login_lockouts where lockout_key = %s",
            (key,),
        )
        row = cur.fetchone()
    if not row:
        return False
    return bool(
        row["fail_count"] >= 1
        and row["locked_until"]
        and row["locked_until"] > datetime.now(timezone.utc)
    )


def record_failure(key: str, max_attempts: int, lockout_seconds: int) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select fail_count from login_lockouts where lockout_key = %s", (key,))
        row = cur.fetchone()
        fail_count = (row["fail_count"] if row else 0) + 1
        locked_until = (
            datetime.now(timezone.utc) + timedelta(seconds=lockout_seconds)
            if fail_count >= max_attempts
            else None
        )
        cur.execute(
            """
            insert into login_lockouts (lockout_key, fail_count, locked_until, updated_at)
            values (%s, %s, %s, now())
            on conflict (lockout_key) do update set
              fail_count = excluded.fail_count,
              locked_until = excluded.locked_until,
              updated_at = now()
            """,
            (key, fail_count, locked_until),
        )


def record_success(key: str) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("delete from login_lockouts where lockout_key = %s", (key,))


def check_login_lockout(request: Request, email: str) -> tuple[str, bool]:
    key = f"login:{email.lower()}:{client_ip(request)}"
    return key, _is_locked_out(key)


def check_register_lockout(request: Request) -> tuple[str, bool]:
    key = f"register:{client_ip(request)}"
    return key, _is_locked_out(key)


# ── invite codes (register.html doesn't collect one yet — this is a no-op
# unless REQUIRE_INVITE_CODE / REGISTRATION_INVITE_CODE are set) ───────────

def _invite_required() -> bool:
    if os.environ.get("REQUIRE_INVITE_CODE", "").strip().lower() in ("1", "true", "yes"):
        return True
    return bool(os.environ.get("REGISTRATION_INVITE_CODE", "").strip())


def validate_invite_code(code: str | None) -> str | None:
    """Returns an error message, or None if the code is acceptable (or not required)."""
    if not _invite_required():
        return None

    code = (code or "").strip()
    if not code:
        return "請輸入邀請碼。 (Invite code is required.)"

    env_code = os.environ.get("REGISTRATION_INVITE_CODE", "").strip()
    if env_code and hmac.compare_digest(code, env_code):
        return None

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select * from invite_codes where code = %s", (code,))
        invite = cur.fetchone()

    invalid = "邀請碼無效或已過期。 (Invalid or expired invite code.)"
    if not invite or not invite["is_active"]:
        return invalid
    if invite["expires_at"] and invite["expires_at"] < datetime.now(timezone.utc):
        return invalid
    if invite["max_uses"] is not None and invite["use_count"] >= invite["max_uses"]:
        return "邀請碼已達使用上限。 (Invite code has reached its use limit.)"
    return None


def consume_invite_code(code: str | None, user_id: str) -> dict[str, bool]:
    """Marks a DB-backed invite code as used. Returns role flags granted by the code."""
    empty = {"grants_admin": False, "grants_partner": False}
    code = (code or "").strip()
    env_code = os.environ.get("REGISTRATION_INVITE_CODE", "").strip()
    if env_code and hmac.compare_digest(code, env_code):
        return empty
    if not code:
        return empty

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select * from invite_codes where code = %s", (code,))
        invite = cur.fetchone()
        if not invite:
            return empty

        new_use_count = (invite["use_count"] or 0) + 1
        still_active = (
            new_use_count < invite["max_uses"] if invite["max_uses"] is not None else invite["is_active"]
        )
        cur.execute(
            """
            update invite_codes set use_count = %s, used_by_id = %s, used_at = now(), is_active = %s
            where id = %s
            """,
            (new_use_count, user_id, still_active, invite["id"]),
        )
        grants_admin = bool(invite["grants_admin"])
        grants_partner = bool(invite.get("grants_partner")) or (not grants_admin)
        return {"grants_admin": grants_admin, "grants_partner": grants_partner}


def generate_invite_code() -> str:
    return secrets.token_urlsafe(9)[:12].upper()


# ── audit log ────────────────────────────────────────────────────────────

def log_admin_action(actor_email: str | None, action: str, detail: dict | None = None) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "insert into audit_log (actor_email, action, detail) values (%s, %s, %s)",
            (actor_email, action, psycopg_json(detail or {})),
        )


def psycopg_json(value: dict):
    import json

    from psycopg.types.json import Jsonb

    return Jsonb(json.loads(json.dumps(value, default=str)))
