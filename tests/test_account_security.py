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
            """
        )
    yield


def _unique_email(prefix: str = "sec") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def _create_user(*, email: str | None = None, password: str = "password123", admin: bool = False):
    from app.auth import hash_password
    from app.database import get_connection

    email = email or _unique_email()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into users (email, password_hash, email_verified, is_active)
            values (%s, %s, true, true)
            returning id
            """,
            (email.lower(), hash_password(password)),
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
        login = client.post("/api/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200

        resp = client.post(
            "/api/admin/account-action",
            json={"id": admin_id, "action": "toggle-active"},
            cookies=login.cookies,
            headers={"Origin": "https://evil.example"},
        )
        assert resp.status_code == 403
        assert "來源" in resp.json().get("error", "")
    finally:
        _cleanup_user(admin_id)


def test_admin_reset_password_min_eight(client):
    admin_id, admin_email, admin_password = _create_user(admin=True)
    target_id, _target_email, _ = _create_user()
    try:
        login = client.post(
            "/api/auth/login",
            json={"email": admin_email, "password": admin_password},
        )
        assert login.status_code == 200

        missing_step = client.post(
            "/api/admin/account-action",
            json={"id": target_id, "action": "reset-password", "newPassword": "longpass1"},
            cookies=login.cookies,
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
            },
            cookies=login.cookies,
        )
        assert short.status_code == 400
        assert "8" in short.json().get("error", "")

        ok = client.post(
            "/api/admin/account-action",
            json={
                "id": target_id,
                "action": "reset-password",
                "newPassword": "longpass1",
                "password": admin_password,
            },
            cookies=login.cookies,
        )
        assert ok.status_code == 200
    finally:
        _cleanup_user(target_id)
        _cleanup_user(admin_id)


def test_admin_set_role_requires_step_up(client):
    admin_id, admin_email, admin_password = _create_user(admin=True)
    target_id, _target_email, _ = _create_user()
    try:
        login = client.post(
            "/api/auth/login",
            json={"email": admin_email, "password": admin_password},
        )
        assert login.status_code == 200

        missing = client.post(
            "/api/admin/account-action",
            json={"id": target_id, "action": "set-role", "role": "partner"},
            cookies=login.cookies,
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
            },
            cookies=login.cookies,
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
    admin_id, admin_email, admin_password = _create_user(admin=True)
    target_id, target_email, _ = _create_user()
    try:
        login = client.post(
            "/api/auth/login",
            json={"email": admin_email, "password": admin_password},
        )
        assert login.status_code == 200

        missing = client.post(
            "/api/admin/account-action",
            json={"id": target_id, "action": "delete", "confirmEmail": target_email},
            cookies=login.cookies,
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
            },
            cookies=login.cookies,
        )
        assert ok.status_code == 200
        target_id = None
    finally:
        if target_id:
            _cleanup_user(target_id)
        _cleanup_user(admin_id)
