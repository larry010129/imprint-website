"""Auth helpers — signed-JWT session cookie, login/register lockout, invite
codes. Ported from backend/lib/auth.js, lib/rateLimit.js and lib/invites.js
so this FastAPI app can serve /api/auth/* itself (see app/database.py).
"""

from __future__ import annotations

import hmac
import os
import re
import secrets
import socket
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Request, Response

from config.settings import settings
from app.database import get_connection

COOKIE_NAME = "imprint_session"
PRE2FA_COOKIE_NAME = "imprint_pre2fa"
PWRESET_COOKIE_NAME = "imprint_pwreset"
SESSION_DAYS = 30
PRE2FA_MINUTES = 5
PWRESET_MINUTES = 10

LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300
REGISTER_MAX_ATTEMPTS = 10
REGISTER_LOCKOUT_SECONDS = 600
TOTP_VERIFY_MAX_ATTEMPTS = 5
TOTP_VERIFY_LOCKOUT_SECONDS = 900

_DOMAIN_LABEL_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
_DNS_LOOKUP_SECONDS = 3.0

EMAIL_FORMAT_ERROR = "請輸入有效的 Email 格式"
EMAIL_DOMAIN_ERROR = "此 Email 網域不存在或無法接收郵件，請確認網址是否正確"


def is_valid_email(email: str) -> bool:
    """Format check: local@domain.tld with sane labels — not deliverability."""
    if not email or len(email) > 254:
        return False
    if any(c.isspace() for c in email):
        return False
    if email.count("@") != 1:
        return False

    local, domain = email.rsplit("@", 1)
    if not local or not domain or len(local) > 64:
        return False
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    if domain.startswith(".") or domain.endswith(".") or ".." in domain:
        return False
    if "." not in domain:
        return False

    tld = domain.rsplit(".", 1)[-1]
    if len(tld) < 2:
        return False
    if tld.isalpha():
        pass
    elif tld.startswith("xn--") and len(tld) > 4:
        pass
    else:
        return False

    for label in domain.split("."):
        if not label or len(label) > 63:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
        if _DOMAIN_LABEL_RE.match(label):
            continue
        if label.startswith("xn--"):
            continue
        return False
    return True


def email_domain_resolves(domain: str) -> bool:
    """Light deliverability: domain must resolve (A/AAAA). No MX/SMTP required."""
    if not domain:
        return False
    prev_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(_DNS_LOOKUP_SECONDS)
        socket.getaddrinfo(domain, None, type=socket.SOCK_STREAM)
        return True
    except (OSError, socket.gaierror, socket.timeout):
        return False
    finally:
        socket.setdefaulttimeout(prev_timeout)


def validate_register_email(email: str, *, check_domain: bool = True) -> str | None:
    """Returns a user-facing error message, or None if the email is acceptable."""
    if not is_valid_email(email):
        return EMAIL_FORMAT_ERROR
    if check_domain and not email_domain_resolves(email.rsplit("@", 1)[1]):
        return EMAIL_DOMAIN_ERROR
    return None


def _jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not set")
    return secret


# ── passwords ────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ── Google Sign-In (Google Identity Services) ───────────────────────────────

def ensure_google_id_column() -> None:
    """Idempotent — same pattern as app.profile_schema.ensure_profile_address_columns.
    Called from the app lifespan so a fresh DB doesn't need a manual migration."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("alter table users add column if not exists google_id text unique")


def verify_google_id_token(credential: str) -> dict | None:
    """Verifies a Google ID token's signature, issuer, audience and expiry —
    never trust the profile data a client sends without this. Returns the
    decoded claims (sub/email/email_verified/name) or None if invalid."""
    client_id = settings.google_client_id
    if not client_id or not credential:
        return None
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    try:
        return google_id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
    except Exception:
        return None


# ── session cookie ───────────────────────────────────────────────────────

def sign_session(user_id: str, token_version: int = 0) -> str:
    payload = {
        "sub": user_id,
        "ver": token_version,
        "exp": datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def verify_session_token(token: str) -> tuple[str, int] | None:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") in ("pre2fa", "pwreset"):
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    return sub, int(payload.get("ver", 0))


def sign_pre2fa(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "purpose": "pre2fa",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=PRE2FA_MINUTES),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def verify_pre2fa(token: str) -> str | None:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != "pre2fa":
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None


def set_pre2fa_cookie(response: Response, token: str, request: Request) -> None:
    response.set_cookie(
        key=PRE2FA_COOKIE_NAME,
        value=token,
        path="/",
        httponly=True,
        secure=_is_secure_request(request),
        samesite="lax",
        max_age=PRE2FA_MINUTES * 60,
    )


def clear_pre2fa_cookie(response: Response, request: Request | None = None) -> None:
    secure = _is_secure_request(request) if request is not None else False
    response.delete_cookie(
        key=PRE2FA_COOKIE_NAME, path="/", httponly=True, secure=secure, samesite="lax"
    )


def get_pre2fa_user_id(request: Request) -> str | None:
    token = request.cookies.get(PRE2FA_COOKIE_NAME)
    if not token:
        return None
    user_id = verify_pre2fa(token)
    if not user_id:
        return None
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select is_active from users where id = %s", (user_id,))
        row = cur.fetchone()
    if not row or not row["is_active"]:
        return None
    return user_id


def sign_pwreset(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "purpose": "pwreset",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=PWRESET_MINUTES),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def verify_pwreset(token: str) -> str | None:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != "pwreset":
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None


def set_pwreset_cookie(response: Response, token: str, request: Request) -> None:
    response.set_cookie(
        key=PWRESET_COOKIE_NAME,
        value=token,
        path="/",
        httponly=True,
        secure=_is_secure_request(request),
        samesite="lax",
        max_age=PWRESET_MINUTES * 60,
    )


def clear_pwreset_cookie(response: Response, request: Request | None = None) -> None:
    secure = _is_secure_request(request) if request is not None else False
    response.delete_cookie(
        key=PWRESET_COOKIE_NAME, path="/", httponly=True, secure=secure, samesite="lax"
    )


def get_pwreset_user_id(request: Request) -> str | None:
    token = request.cookies.get(PWRESET_COOKIE_NAME)
    if not token:
        return None
    user_id = verify_pwreset(token)
    if not user_id:
        return None
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select is_active, totp_enabled from users where id = %s",
            (user_id,),
        )
        row = cur.fetchone()
    if not row or not row["is_active"] or not row.get("totp_enabled"):
        return None
    return user_id


def bump_token_version(user_id: str) -> None:
    """Invalidates every existing session for a user (logout, password reset)."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("update users set token_version = token_version + 1 where id = %s", (user_id,))


def _is_secure_request(request: Request) -> bool:
    """True when the connection is actually HTTPS, not just when RENDER is set —
    so a Secure cookie isn't silently downgraded on any non-Render deployment
    that still terminates TLS. x-forwarded-proto is only trusted behind Render's
    known edge proxy; elsewhere it could be forged by the client."""
    if request.url.scheme == "https":
        return True
    if settings.is_render:
        return request.headers.get("x-forwarded-proto", "").lower() == "https"
    return False


def set_session_cookie(response: Response, token: str, request: Request, *, remember: bool = True) -> None:
    """Set signed JWT session cookie. Persistent (30d) when remember=True, else browser-session only."""
    kwargs: dict = {
        "key": COOKIE_NAME,
        "value": token,
        "path": "/",
        "httponly": True,
        "secure": _is_secure_request(request),
        "samesite": "lax",
    }
    if remember:
        kwargs["max_age"] = SESSION_DAYS * 24 * 60 * 60
    response.set_cookie(**kwargs)


def clear_session_cookie(response: Response, request: Request | None = None) -> None:
    """Delete session cookie — secure/samesite must match set_session_cookie or browsers keep it."""
    secure = _is_secure_request(request) if request is not None else False
    response.delete_cookie(key=COOKIE_NAME, path="/", httponly=True, secure=secure, samesite="lax")


def get_user_id(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    decoded = verify_session_token(token)
    if not decoded:
        return None
    user_id, token_version = decoded
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select token_version, is_active from users where id = %s", (user_id,))
        row = cur.fetchone()
    if not row or row["token_version"] != token_version or not row["is_active"]:
        return None
    return user_id


def is_admin(user_id: str | None) -> bool:
    if not user_id:
        return False
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select user_id from staff_admins where user_id = %s", (user_id,))
        return cur.fetchone() is not None


# ── login/register lockout (state lives in login_lockouts, not memory —
# this app runs across multiple gunicorn worker processes) ─────────────────

def client_ip(request: Request) -> str:
    """x-forwarded-for is only trusted behind Render's known edge proxy, which
    sets/overwrites it itself — elsewhere a client could forge it to rotate
    fake IPs and bypass login/register lockout."""
    if settings.is_render:
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


def _as_lockout_keys(keys: str | list[str] | None) -> list[str]:
    if not keys:
        return []
    if isinstance(keys, str):
        return [keys]
    return [k for k in keys if k]


def record_failures(keys: str | list[str] | None, max_attempts: int, lockout_seconds: int) -> None:
    for key in _as_lockout_keys(keys):
        record_failure(key, max_attempts, lockout_seconds)


def record_successes(keys: str | list[str] | None) -> None:
    for key in _as_lockout_keys(keys):
        record_success(key)


def _dual_lockout_keys(account_key: str, ip_key: str) -> tuple[list[str], bool]:
    """Lock if either account-scoped or IP-scoped key is locked."""
    keys = [account_key, ip_key]
    return keys, any(_is_locked_out(k) for k in keys)


def enforce_rate_limit(
    request: Request,
    *,
    action: str,
    limit: int,
    window_seconds: int,
    subject: str | None = None,
) -> bool:
    """Per-IP (and optional subject) throttle for unauthenticated POST endpoints,
    reusing the login_lockouts table so it works across gunicorn workers. Returns
    True if the request is within the allowance, False if it should be rejected.

    Fixed window that resets after `window_seconds` of inactivity: while a client
    keeps hitting the endpoint the counter grows and, once it passes `limit`,
    stays blocked; after it goes quiet for a full window the counter starts over.
    Keys are namespaced by `action`, separate from login:/register: keys.
    When `subject` is set, both IP and subject keys are incremented; either over
    limit rejects."""
    keys = [f"{action}:{client_ip(request)}"]
    if subject:
        keys.append(f"{action}:acct:{subject.strip().lower()}")
    now = datetime.now(timezone.utc)
    allowed = True
    with get_connection() as conn, conn.cursor() as cur:
        for key in keys:
            cur.execute(
                "select fail_count, updated_at from login_lockouts where lockout_key = %s",
                (key,),
            )
            row = cur.fetchone()
            within_window = bool(
                row
                and row["updated_at"]
                and (now - row["updated_at"]).total_seconds() < window_seconds
            )
            count = (row["fail_count"] + 1) if within_window else 1
            locked_until = now + timedelta(seconds=window_seconds) if count > limit else None
            cur.execute(
                """
                insert into login_lockouts (lockout_key, fail_count, locked_until, updated_at)
                values (%s, %s, %s, now())
                on conflict (lockout_key) do update set
                  fail_count = excluded.fail_count,
                  locked_until = excluded.locked_until,
                  updated_at = now()
                """,
                (key, count, locked_until),
            )
            if count > limit:
                allowed = False
    return allowed


def check_login_lockout(request: Request, email: str) -> tuple[list[str], bool]:
    normalized = email.lower()
    return _dual_lockout_keys(
        f"login:{normalized}",
        f"login:{normalized}:{client_ip(request)}",
    )


def check_register_lockout(request: Request, email: str | None = None) -> tuple[list[str], bool]:
    ip_key = f"register:{client_ip(request)}"
    if email:
        return _dual_lockout_keys(f"register:{(email or '').strip().lower()}", ip_key)
    return [ip_key], _is_locked_out(ip_key)


def check_totp_verify_lockout(request: Request, user_id: str) -> tuple[list[str], bool]:
    return _dual_lockout_keys(
        f"2fa:{user_id}",
        f"2fa:{user_id}:{client_ip(request)}",
    )


def same_site_origin(request: Request) -> bool:
    """True when Origin/Referer matches Host, or both headers are absent.

    Cross-site browser POSTs always send Origin; rejecting mismatches is the
    CSRF defense. Missing both is allowed for same-site HTMX / TestClient."""
    host = (request.headers.get("host") or "").strip().lower()
    if not host:
        return True

    origin = (request.headers.get("origin") or "").strip()
    if origin:
        return _url_host_matches(origin, host)

    referer = (request.headers.get("referer") or "").strip()
    if referer:
        return _url_host_matches(referer, host)
    return True


def _url_host_matches(url: str, host: str) -> bool:
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    netloc = (parsed.netloc or "").strip().lower()
    if not netloc:
        return False
    return netloc == host


# ── invite codes (register.html doesn't collect one yet — this is a no-op
# unless REQUIRE_INVITE_CODE / REGISTRATION_INVITE_CODE are set) ───────────

def _invite_required() -> bool:
    if os.environ.get("REQUIRE_INVITE_CODE", "").strip().lower() in ("1", "true", "yes"):
        return True
    return bool(os.environ.get("REGISTRATION_INVITE_CODE", "").strip())


def _lookup_active_invite(code: str) -> tuple[dict | None, str | None]:
    """Fetch invite row; return (invite, error). error set when unusable."""
    invalid = "邀請碼無效或已過期。 (Invalid or expired invite code.)"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select * from invite_codes where code = %s", (code,))
        invite = cur.fetchone()
    if not invite or not invite["is_active"]:
        return None, invalid
    expires_at = invite.get("expires_at")
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return None, invalid
    if invite["max_uses"] is not None and invite["use_count"] >= invite["max_uses"]:
        return None, "邀請碼已達使用上限。 (Invite code has reached its use limit.)"
    return invite, None


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

    _invite, err = _lookup_active_invite(code)
    return err


def validate_partner_invite_code(code: str | None) -> str | None:
    """Partner checkbox path — always requires an active DB invite that grants partner/admin."""
    code = (code or "").strip()
    if not code:
        return "請輸入合作廠商邀請碼。"

    invite, err = _lookup_active_invite(code)
    if err:
        return err
    assert invite is not None
    if not (invite.get("grants_partner") or invite.get("grants_admin")):
        return "邀請碼無效或已過期。 (Invalid or expired invite code.)"
    return None


def consume_invite_code(code: str | None, user_id: str) -> dict[str, bool]:
    """Atomically consume a DB invite. Returns role flags, or empty if unavailable.

    Uses UPDATE…WHERE use_count < max_uses RETURNING so parallel signups cannot
    all grant admin/partner from one single-use code.
    """
    empty = {"grants_admin": False, "grants_partner": False}
    code = (code or "").strip()
    env_code = os.environ.get("REGISTRATION_INVITE_CODE", "").strip()
    if env_code and hmac.compare_digest(code, env_code):
        return empty
    if not code:
        return empty

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            update invite_codes
            set
              use_count = use_count + 1,
              used_by_id = %s,
              used_at = now(),
              is_active = case
                when max_uses is null then is_active
                when use_count + 1 < max_uses then true
                else false
              end
            where code = %s
              and is_active = true
              and (expires_at is null or expires_at > now())
              and (max_uses is null or use_count < max_uses)
            returning grants_admin, grants_partner
            """,
            (user_id, code),
        )
        invite = cur.fetchone()
        if not invite:
            return empty
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
