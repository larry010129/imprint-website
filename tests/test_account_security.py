"""Account abuse-path hardening — lockouts, invite race, oracles, delete step-up, CSRF."""

from __future__ import annotations

import os
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

os.environ.setdefault("STARTUP_SEED_MODE", "off")
os.environ.setdefault("JWT_SECRET", os.environ.get("JWT_SECRET") or "test-jwt-secret-security")
os.environ.setdefault("RECAPTCHA_SECRET_KEY", "test-recaptcha-secret")
os.environ.setdefault("RECAPTCHA_SITE_KEY", "test-recaptcha-site-key")

pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture(autouse=True)
def _clear_security_lockouts():
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            delete from login_lockouts
            where lockout_key like 'login:%'
               or lockout_key like 'register:%'
               or lockout_key like '2fa:%'
               or lockout_key like 'check-email:%'
               or lockout_key like 'check-invite:%'
               or lockout_key like 'track-order:%'
               or lockout_key like 'pwreset-totp:%'
               or lockout_key like 'account-delete:%'
               or lockout_key like 'gold-refresh:%'
            """
        )
    yield


def _unique_email(prefix: str = "sec") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def _create_user(
    *,
    email: str | None = None,
    password: str = "password123",
    admin: bool = False,
    totp_enabled: bool | None = None,
):
    from app.auth import hash_password
    from app.database import get_connection
    from app.totp import generate_secret

    email = email or _unique_email()
    # Staff must enroll TOTP before admin APIs work.
    if totp_enabled is None:
        totp_enabled = bool(admin)
    secret = generate_secret() if totp_enabled else None
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into users (email, password_hash, email_verified, is_active, totp_secret, totp_enabled)
            values (%s, %s, true, true, %s, %s)
            returning id
            """,
            (email.lower(), hash_password(password), secret, bool(totp_enabled)),
        )
        user_id = str(cur.fetchone()["id"])
        cur.execute(
            "insert into profiles (id, full_name, phone) values (%s, %s, %s)",
            (user_id, "Security Test", "0912345678"),
        )
        if admin:
            cur.execute(
                "insert into staff_admins (user_id) values (%s) on conflict do nothing",
                (user_id,),
            )
    return user_id, email.lower(), password


def _login_cookies(client, email: str, password: str):
    """Login and complete admin pre2fa when required."""
    import pyotp
    from app.database import get_connection

    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    data = login.json()
    if not data.get("requires2fa"):
        return login.cookies
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select totp_secret from users where email = %s", (email.lower(),))
        secret = cur.fetchone()["totp_secret"]
    code = pyotp.TOTP(secret).now()
    verify = client.post(
        "/api/auth/verify-2fa",
        json={"code": code},
        cookies=login.cookies,
    )
    assert verify.status_code == 200
    return verify.cookies


def _cleanup_user(user_id: str) -> None:
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("delete from staff_admins where user_id = %s", (user_id,))
        cur.execute("delete from profiles where id = %s", (user_id,))
        cur.execute("delete from users where id = %s", (user_id,))


def test_login_lockout_follows_account_across_ips(client):
    from app.auth import LOGIN_LOCKOUT_SECONDS, LOGIN_MAX_ATTEMPTS, check_login_lockout, record_failures

    user_id, email, _password = _create_user()
    try:
        for i in range(LOGIN_MAX_ATTEMPTS):
            fake = MagicMock()
            fake.client = MagicMock(host=f"10.0.0.{i + 1}")
            fake.headers = {}
            keys, locked = check_login_lockout(fake, email)
            assert not locked
            record_failures(keys, LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECONDS)

        other_ip = MagicMock()
        other_ip.client = MagicMock(host="203.0.113.50")
        other_ip.headers = {}
        _keys, locked = check_login_lockout(other_ip, email)
        assert locked is True

        resp = client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrong-password"},
        )
        assert resp.status_code == 429
    finally:
        _cleanup_user(user_id)


def test_atomic_invite_consume_only_one_admin(client):
    from app.auth import consume_invite_code, hash_password
    from app.database import get_connection

    code = "A" + secrets.token_hex(5).upper()
    user_ids: list[str] = []
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into invite_codes (code, label, max_uses, grants_admin, grants_partner, is_active)
            values (%s, 'race', 1, true, false, true)
            """,
            (code,),
        )
        for i in range(3):
            email = _unique_email(f"inv{i}")
            cur.execute(
                """
                insert into users (email, password_hash, email_verified)
                values (%s, %s, true) returning id
                """,
                (email, hash_password("password123")),
            )
            user_ids.append(str(cur.fetchone()["id"]))

    try:
        results = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(consume_invite_code, code, uid) for uid in user_ids]
            for fut in as_completed(futures):
                results.append(fut.result())

        admin_grants = sum(1 for r in results if r.get("grants_admin"))
        assert admin_grants == 1

        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select use_count, is_active from invite_codes where code = %s", (code,))
            row = cur.fetchone()
            assert row["use_count"] == 1
            assert row["is_active"] is False
    finally:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("delete from invite_codes where code = %s", (code,))
            for uid in user_ids:
                cur.execute("delete from users where id = %s", (uid,))


@patch("app.auth.email_domain_resolves", return_value=True)
def test_check_email_rate_limited(_mock_dns, client):
    from app.database import get_connection

    for _ in range(10):
        resp = client.post("/htmx/auth/check-email", data={"email": "member@example.com"})
        assert resp.status_code in (200, 400)

    limited = client.post("/htmx/auth/check-email", data={"email": "member@example.com"})
    assert limited.status_code == 429

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("delete from login_lockouts where lockout_key like 'check-email:%'")


def test_track_order_rate_limited(client):
    from app.database import get_connection

    for _ in range(10):
        resp = client.post(
            "/api/track-order",
            json={"orderNumber": "ID999999", "phone": "0900000000"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"rows": []}

    limited = client.post(
        "/api/track-order",
        json={"orderNumber": "ID999999", "phone": "0900000000"},
    )
    assert limited.status_code == 429

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("delete from login_lockouts where lockout_key like 'track-order:%'")


def test_account_delete_requires_password(client):
    from app.auth import sign_session
    from app.auth import COOKIE_NAME

    user_id, email, password = _create_user()
    try:
        cookies = {COOKIE_NAME: sign_session(user_id)}
        missing = client.post(
            "/htmx/account/delete",
            headers={"HX-Request": "true"},
            data={"confirmEmail": email},
            cookies=cookies,
        )
        assert missing.status_code == 400
        assert "密碼" in missing.text

        wrong = client.post(
            "/htmx/account/delete",
            headers={"HX-Request": "true"},
            data={"confirmEmail": email, "password": "wrong-pass"},
            cookies=cookies,
        )
        assert wrong.status_code == 401

        ok = client.post(
            "/htmx/account/delete",
            headers={"HX-Request": "true"},
            data={"confirmEmail": email, "password": password},
            cookies=cookies,
        )
        assert ok.status_code == 200
        assert ok.headers.get("HX-Redirect") == "/"
        user_id = None
    finally:
        if user_id:
            _cleanup_user(user_id)


def test_csrf_rejects_cross_site_origin_on_admin_post(client):
    admin_id, email, password = _create_user(admin=True)
    try:
        cookies = _login_cookies(client, email, password)

        resp = client.post(
            "/api/admin/account-action",
            json={"id": admin_id, "action": "toggle-active"},
            cookies=cookies,
            headers={"Origin": "https://evil.example"},
        )
        assert resp.status_code == 403
        assert "來源" in resp.json().get("error", "")
    finally:
        _cleanup_user(admin_id)


def test_csrf_rejects_cross_site_origin_on_pricing_post(client):
    admin_id, email, password = _create_user(admin=True)
    try:
        cookies = _login_cookies(client, email, password)
        resp = client.post(
            "/api/pricing",
            json={"overrides": {}},
            cookies=cookies,
            headers={"Origin": "https://evil.example"},
        )
        assert resp.status_code == 403
        assert "來源" in resp.json().get("error", "")
    finally:
        _cleanup_user(admin_id)


def test_admin_reset_password_min_eight(client):
    import pyotp
    from app.database import get_connection

    admin_id, admin_email, admin_password = _create_user(admin=True)
    target_id, _target_email, _ = _create_user()
    try:
        cookies = _login_cookies(client, admin_email, admin_password)
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select totp_secret from users where id = %s", (admin_id,))
            secret = cur.fetchone()["totp_secret"]
        totp = pyotp.TOTP(secret).now()

        missing_step = client.post(
            "/api/admin/account-action",
            json={"id": target_id, "action": "reset-password", "newPassword": "longpass1"},
            cookies=cookies,
        )
        assert missing_step.status_code == 400
        assert "密碼" in missing_step.json().get("error", "")

        short = client.post(
            "/api/admin/account-action",
            json={
                "id": target_id,
                "action": "reset-password",
                "newPassword": "short1",
                "password": admin_password,
                "totpCode": totp,
            },
            cookies=cookies,
        )
        assert short.status_code == 400
        assert "8" in short.json().get("error", "")

        totp = pyotp.TOTP(secret).now()
        ok = client.post(
            "/api/admin/account-action",
            json={
                "id": target_id,
                "action": "reset-password",
                "newPassword": "longpass1",
                "password": admin_password,
                "totpCode": totp,
            },
            cookies=cookies,
        )
        assert ok.status_code == 200
    finally:
        _cleanup_user(target_id)
        _cleanup_user(admin_id)


def test_admin_set_role_requires_step_up(client):
    import pyotp
    from app.database import get_connection

    admin_id, admin_email, admin_password = _create_user(admin=True)
    target_id, _target_email, _ = _create_user()
    try:
        cookies = _login_cookies(client, admin_email, admin_password)
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select totp_secret from users where id = %s", (admin_id,))
            secret = cur.fetchone()["totp_secret"]

        missing = client.post(
            "/api/admin/account-action",
            json={"id": target_id, "action": "set-role", "role": "partner"},
            cookies=cookies,
        )
        assert missing.status_code == 400
        assert "密碼" in missing.json().get("error", "")

        ok = client.post(
            "/api/admin/account-action",
            json={
                "id": target_id,
                "action": "set-role",
                "role": "partner",
                "password": admin_password,
                "totpCode": pyotp.TOTP(secret).now(),
            },
            cookies=cookies,
        )
        assert ok.status_code == 200
    finally:
        _cleanup_user(target_id)
        _cleanup_user(admin_id)


def test_csrf_rejects_cross_site_origin_on_cart_post(client):
    user_id, email, password = _create_user()
    try:
        login = client.post("/api/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200

        resp = client.post(
            "/api/cart",
            json={"category": "ring", "type": "ring-A", "gold": "14k", "carat": "0.3"},
            cookies=login.cookies,
            headers={"Origin": "https://evil.example"},
        )
        assert resp.status_code == 403
        assert "來源" in resp.json().get("error", "")
    finally:
        _cleanup_user(user_id)


def test_admin_delete_requires_password(client):
    import pyotp
    from app.database import get_connection

    admin_id, admin_email, admin_password = _create_user(admin=True)
    target_id, target_email, _ = _create_user()
    try:
        cookies = _login_cookies(client, admin_email, admin_password)
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select totp_secret from users where id = %s", (admin_id,))
            secret = cur.fetchone()["totp_secret"]

        missing = client.post(
            "/api/admin/account-action",
            json={"id": target_id, "action": "delete", "confirmEmail": target_email},
            cookies=cookies,
        )
        assert missing.status_code == 400
        assert "密碼" in missing.json().get("error", "")

        ok = client.post(
            "/api/admin/account-action",
            json={
                "id": target_id,
                "action": "delete",
                "confirmEmail": target_email,
                "password": admin_password,
                "totpCode": pyotp.TOTP(secret).now(),
            },
            cookies=cookies,
        )
        assert ok.status_code == 200
        target_id = None
    finally:
        if target_id:
            _cleanup_user(target_id)
        _cleanup_user(admin_id)


def test_csrf_rejects_cross_site_origin_on_favorites_post(client):
    user_id, email, password = _create_user()
    try:
        login = client.post("/api/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200

        resp = client.post(
            "/api/favorites",
            json={"category": "ring", "type": "ring-A"},
            cookies=login.cookies,
            headers={"Origin": "https://evil.example"},
        )
        assert resp.status_code == 403
        assert "來源" in resp.json().get("error", "")
    finally:
        _cleanup_user(user_id)


def test_csrf_rejects_cross_site_origin_on_notifications_post(client):
    user_id, email, password = _create_user()
    try:
        login = client.post("/api/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200

        resp = client.post(
            "/api/notifications/mark-read",
            json={"id": str(uuid.uuid4())},
            cookies=login.cookies,
            headers={"Origin": "https://evil.example"},
        )
        assert resp.status_code == 403
        assert "來源" in resp.json().get("error", "")
    finally:
        _cleanup_user(user_id)


def _encode_session_payload(payload: dict) -> str:
    import jwt

    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


def test_session_absolute_expired_rejects():
    from datetime import datetime, timedelta, timezone

    from app.auth import verify_session_claims

    now = datetime.now(timezone.utc)
    token = _encode_session_payload(
        {
            "sub": str(uuid.uuid4()),
            "ver": 0,
            "iat": now - timedelta(days=2),
            "exp": now - timedelta(minutes=1),
            "role": "member",
            "rem": True,
        }
    )
    assert verify_session_claims(token) is None


def test_session_idle_expired_rejects_even_if_exp_future():
    from datetime import datetime, timedelta, timezone

    from app.auth import SESSION_IDLE_MINUTES, verify_session_claims

    now = datetime.now(timezone.utc)
    token = _encode_session_payload(
        {
            "sub": str(uuid.uuid4()),
            "ver": 0,
            "iat": now - timedelta(minutes=SESSION_IDLE_MINUTES + 1),
            "exp": now + timedelta(days=7),
            "role": "member",
            "rem": True,
        }
    )
    assert verify_session_claims(token) is None


def test_admin_session_has_shorter_absolute_exp_than_member():
    import jwt
    from datetime import datetime, timezone

    from app.auth import ADMIN_SESSION_HOURS, SESSION_DAYS, sign_session

    member = sign_session(str(uuid.uuid4()), is_admin=False, remember=True)
    admin = sign_session(str(uuid.uuid4()), is_admin=True, remember=True)
    secret = os.environ["JWT_SECRET"]
    m = jwt.decode(member, secret, algorithms=["HS256"])
    a = jwt.decode(admin, secret, algorithms=["HS256"])
    assert a["role"] == "admin"
    assert m["role"] == "member"
    assert (a["exp"] - a["iat"]) <= ADMIN_SESSION_HOURS * 3600 + 5
    assert (m["exp"] - m["iat"]) >= (SESSION_DAYS * 24 * 3600) - 5
    assert (a["exp"] - a["iat"]) < (m["exp"] - m["iat"])


def test_remember_false_jwt_exp_at_most_24h():
    from datetime import timedelta

    from app.auth import REMEMBER_FALSE_MAX_HOURS, sign_session, verify_session_claims

    claims = verify_session_claims(sign_session(str(uuid.uuid4()), remember=False))
    assert claims is not None
    assert claims.exp - claims.iat <= timedelta(hours=REMEMBER_FALSE_MAX_HOURS, seconds=5)


def test_session_slide_updates_iat_keeps_absolute_exp():
    from datetime import datetime, timedelta, timezone

    from app.auth import (
        SESSION_DAYS,
        SESSION_IDLE_MINUTES,
        SessionClaims,
        reissue_session_token,
        session_needs_slide,
    )

    now = datetime.now(timezone.utc)
    # Slide triggers after half idle; age past that while absolute exp still valid.
    age = timedelta(minutes=SESSION_IDLE_MINUTES / 2 + 60)
    exp = now + timedelta(days=max(1, SESSION_DAYS - 1))
    claims = SessionClaims(
        user_id=str(uuid.uuid4()),
        token_version=0,
        role="member",
        iat=now - age,
        exp=exp,
        remember=True,
    )
    assert session_needs_slide(claims)
    slid = reissue_session_token(claims)
    from app.auth import verify_session_claims

    refreshed = verify_session_claims(slid)
    assert refreshed is not None
    assert refreshed.exp == exp.replace(microsecond=0) or abs(
        (refreshed.exp - exp).total_seconds()
    ) < 2
    assert refreshed.iat > claims.iat


def test_session_touch_middleware_slides_cookie(client):
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch

    from app.auth import COOKIE_NAME, verify_session_claims

    user_id, _email, _password = _create_user()
    try:
        now = datetime.now(timezone.utc)
        with patch("app.auth.SESSION_IDLE_MINUTES", 2):
            token = _encode_session_payload(
                {
                    "sub": user_id,
                    "ver": 0,
                    "iat": now - timedelta(seconds=70),
                    "exp": now + timedelta(days=7),
                    "role": "member",
                    "rem": True,
                }
            )
            before = verify_session_claims(token)
            assert before is not None
            resp = client.get("/api/auth/session", cookies={COOKIE_NAME: token})
            assert resp.status_code == 200
            assert resp.json().get("user") is not None
            set_cookie = resp.headers.get("set-cookie") or ""
            assert COOKIE_NAME in set_cookie
            # Extract new token value from Set-Cookie
            part = [p for p in set_cookie.split(";") if p.strip().startswith(f"{COOKIE_NAME}=")][0]
            new_token = part.split("=", 1)[1].strip()
            after = verify_session_claims(new_token)
            assert after is not None
            assert after.iat > before.iat
            assert abs((after.exp - before.exp).total_seconds()) < 2
    finally:
        _cleanup_user(user_id)


def test_admin_login_issues_admin_role_cookie(client):
    import jwt

    from app.auth import ADMIN_SESSION_HOURS, COOKIE_NAME

    admin_id, email, password = _create_user(admin=True)
    try:
        cookies = _login_cookies(client, email, password)
        token = cookies.get(COOKIE_NAME)
        assert token
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
        assert payload["role"] == "admin"
        assert (payload["exp"] - payload["iat"]) <= ADMIN_SESSION_HOURS * 3600 + 5
    finally:
        _cleanup_user(admin_id)
