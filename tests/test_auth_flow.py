"""Partner invite, reCAPTCHA register gate, and first-login onboarding gates."""

from __future__ import annotations

import os
import secrets
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

os.environ.setdefault("STARTUP_SEED_MODE", "off")
os.environ.setdefault("JWT_SECRET", os.environ.get("JWT_SECRET") or "test-jwt-secret-for-auth-flow")
os.environ.setdefault("RECAPTCHA_SECRET_KEY", "test-recaptcha-secret")
os.environ.setdefault("RECAPTCHA_SITE_KEY", "test-recaptcha-site-key")


@pytest.fixture(autouse=True)
def _clear_register_lockouts():
    if not os.environ.get("DATABASE_URL"):
        yield
        return
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("delete from login_lockouts where lockout_key like 'register:%'")
    yield


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def _unique_email(prefix: str = "flow") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def _register_form(**overrides):
    data = {
        "fullName": "測試會員",
        "phone": "0912345678",
        "email": _unique_email(),
        "password": "password123",
        "passwordConfirm": "password123",
        "acceptTerms": "1",
        "g-recaptcha-response": "test-token",
    }
    data.update(overrides)
    return data


# ── reCAPTCHA unit ─────────────────────────────────────────────────────────


def test_verify_recaptcha_fail_closed_without_secret(monkeypatch):
    from app.captcha import verify_recaptcha

    monkeypatch.delenv("RECAPTCHA_SECRET_KEY", raising=False)
    assert verify_recaptcha("any-token") is False


def test_verify_recaptcha_rejects_empty_token(monkeypatch):
    from app.captcha import verify_recaptcha

    monkeypatch.setenv("RECAPTCHA_SECRET_KEY", "secret")
    assert verify_recaptcha("") is False
    assert verify_recaptcha(None) is False


@patch("app.captcha.httpx.Client")
def test_verify_recaptcha_true_on_siteverify_success(mock_client_cls, monkeypatch):
    from app.captcha import verify_recaptcha

    monkeypatch.setenv("RECAPTCHA_SECRET_KEY", "secret")
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"success": True}
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    assert verify_recaptcha("ok-token", remote_ip="1.2.3.4") is True
    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == "https://www.google.com/recaptcha/api/siteverify"
    assert kwargs["data"]["response"] == "ok-token"
    assert kwargs["data"]["remoteip"] == "1.2.3.4"


@patch("app.captcha.httpx.Client")
def test_verify_recaptcha_false_on_siteverify_failure(mock_client_cls, monkeypatch):
    from app.captcha import verify_recaptcha

    monkeypatch.setenv("RECAPTCHA_SECRET_KEY", "secret")
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"success": False}
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    assert verify_recaptcha("bad-token") is False


def test_captcha_endpoint_removed(client):
    resp = client.get("/api/auth/captcha")
    assert resp.status_code == 404


def test_validate_partner_invite_rejects_empty():
    from app.auth import validate_partner_invite_code

    err = validate_partner_invite_code("")
    assert err is not None
    assert "邀請碼" in err


@patch("app.auth._lookup_active_invite", return_value=(None, "邀請碼無效或已過期。 (Invalid or expired invite code.)"))
def test_validate_partner_invite_rejects_missing(_mock):
    from app.auth import validate_partner_invite_code

    err = validate_partner_invite_code("NOPE123")
    assert err is not None
    assert "無效" in err


@patch(
    "app.auth._lookup_active_invite",
    return_value=({"grants_partner": False, "grants_admin": False}, None),
)
def test_validate_partner_invite_rejects_non_partner_grant(_mock):
    from app.auth import validate_partner_invite_code

    err = validate_partner_invite_code("MEMBERONLY")
    assert err is not None


@patch(
    "app.auth._lookup_active_invite",
    return_value=({"grants_partner": True, "grants_admin": False}, None),
)
def test_validate_partner_invite_accepts_partner_grant(_mock):
    from app.auth import validate_partner_invite_code

    assert validate_partner_invite_code("PARTNER1") is None


def test_onboarding_helpers():
    from app.onboarding import (
        has_onboard_later_cookie,
        is_onboarding_complete,
        profile_fields_complete,
    )

    assert profile_fields_complete(None) is False
    assert profile_fields_complete({"full_name": "A", "phone": "1"}) is False
    assert (
        profile_fields_complete(
            {
                "full_name": "A",
                "phone": "0912",
                "shipping_postal": "106",
                "shipping_city": "台北市",
                "shipping_address": "信義路一段",
            }
        )
        is True
    )
    assert is_onboarding_complete({}) is False
    assert is_onboarding_complete({"onboarding_completed_at": "2026-01-01"}) is True
    # Fields filled + null timestamp = complete (no redirect / not needs onboarding)
    filled = {
        "full_name": "A",
        "phone": "0912",
        "shipping_postal": "106",
        "shipping_city": "台北市",
        "shipping_address": "信義路一段",
        "onboarding_completed_at": None,
    }
    assert is_onboarding_complete(filled) is True
    assert profile_fields_complete(filled) is True

    class _Req:
        def __init__(self, cookies):
            self.cookies = cookies

    assert has_onboard_later_cookie(_Req({})) is False
    assert has_onboard_later_cookie(_Req({"imprint_onboard_later": "1"})) is True


# ── HTMX integration (needs DB) ─────────────────────────────────────────────


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
@patch("app.captcha.verify_recaptcha", return_value=True)
@patch("app.auth.email_domain_resolves", return_value=True)
def test_htmx_register_partner_empty_invite_rejects(_mock_dns, _mock_captcha, client):
    resp = client.post(
        "/htmx/auth/register",
        headers={"HX-Request": "true"},
        data=_register_form(isPartner="1", inviteCode=""),
    )
    assert resp.status_code == 400
    assert "邀請碼" in resp.text


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
@patch("app.captcha.verify_recaptcha", return_value=True)
@patch("app.auth.email_domain_resolves", return_value=True)
def test_htmx_register_partner_bad_invite_rejects_no_user(_mock_dns, _mock_captcha, client):
    from app.database import get_connection

    email = _unique_email("bad-invite")
    resp = client.post(
        "/htmx/auth/register",
        headers={"HX-Request": "true"},
        data=_register_form(
            email=email,
            isPartner="1",
            inviteCode="TOTALLY-INVALID-" + secrets.token_hex(4),
        ),
    )
    assert resp.status_code == 400
    assert "邀請碼" in resp.text
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from users where email = %s", (email,))
        assert cur.fetchone() is None


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
@patch("app.captcha.verify_recaptcha", return_value=True)
@patch("app.auth.email_domain_resolves", return_value=True)
def test_htmx_register_partner_valid_sets_is_partner(_mock_dns, _mock_captcha, client):
    from app.database import get_connection
    from app.profile_schema import ensure_profile_address_columns

    ensure_profile_address_columns()
    code = "P" + secrets.token_hex(4).upper()
    email = _unique_email("partner-ok")
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into invite_codes (code, label, max_uses, grants_admin, grants_partner, is_active)
            values (%s, 'test partner', 5, false, true, true)
            """,
            (code,),
        )

    try:
        resp = client.post(
            "/htmx/auth/register",
            headers={"HX-Request": "true"},
            data=_register_form(
                email=email,
                isPartner="1",
                inviteCode=code,
            ),
        )
        assert resp.status_code == 200
        assert resp.headers.get("HX-Redirect")
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select u.id, coalesce(p.is_partner, false) as is_partner
                from users u left join profiles p on p.id = u.id
                where u.email = %s
                """,
                (email,),
            )
            row = cur.fetchone()
            assert row is not None
            assert row["is_partner"] is True
    finally:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("delete from users where email = %s", (email,))
            cur.execute("delete from invite_codes where code = %s", (code,))


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
@patch("app.captcha.verify_recaptcha", return_value=True)
@patch("app.auth.email_domain_resolves", return_value=True)
def test_htmx_register_non_partner_unchanged(_mock_dns, _mock_captcha, client):
    from app.database import get_connection
    from app.profile_schema import ensure_profile_address_columns

    ensure_profile_address_columns()
    email = _unique_email("member-ok")
    resp = client.post(
        "/htmx/auth/register",
        headers={"HX-Request": "true"},
        data=_register_form(email=email),
    )
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect") == "/account.html"
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select coalesce(p.is_partner, false) as is_partner,
                       p.onboarding_completed_at
                from users u left join profiles p on p.id = u.id
                where u.email = %s
                """,
                (email,),
            )
            row = cur.fetchone()
            assert row is not None
            assert row["is_partner"] is False
            assert row["onboarding_completed_at"] is None
    finally:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("delete from users where email = %s", (email,))


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
@patch("app.captcha.verify_recaptcha", return_value=False)
@patch("app.auth.email_domain_resolves", return_value=True)
def test_htmx_register_wrong_captcha_rejects(_mock_dns, _mock_captcha, client):
    from app.database import get_connection

    email = _unique_email("bad-captcha")
    resp = client.post(
        "/htmx/auth/register",
        headers={"HX-Request": "true"},
        data=_register_form(email=email, **{"g-recaptcha-response": "bad-token"}),
    )
    assert resp.status_code == 400
    assert "請完成驗證" in resp.text
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from users where email = %s", (email,))
        assert cur.fetchone() is None


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
@patch("app.auth.email_domain_resolves", return_value=True)
def test_htmx_register_missing_captcha_rejects(_mock_dns, client):
    from app.database import get_connection

    email = _unique_email("no-captcha")
    data = _register_form(email=email)
    data["g-recaptcha-response"] = ""
    resp = client.post(
        "/htmx/auth/register",
        headers={"HX-Request": "true"},
        data=data,
    )
    assert resp.status_code == 400
    assert "請完成驗證" in resp.text or "驗證尚未設定" in resp.text
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from users where email = %s", (email,))
        assert cur.fetchone() is None


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
@patch("app.captcha.verify_recaptcha", return_value=True)
@patch("app.auth.email_domain_resolves", return_value=True)
def test_htmx_register_right_captcha_ok(_mock_dns, _mock_captcha, client):
    from app.database import get_connection
    from app.profile_schema import ensure_profile_address_columns

    ensure_profile_address_columns()
    email = _unique_email("ok-captcha")
    resp = client.post(
        "/htmx/auth/register",
        headers={"HX-Request": "true"},
        data=_register_form(email=email),
    )
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect")
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select id from users where email = %s", (email,))
            assert cur.fetchone() is not None
    finally:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("delete from users where email = %s", (email,))


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_check_invite_endpoint(client):
    from app.database import get_connection

    code = "C" + secrets.token_hex(4).upper()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into invite_codes (code, label, max_uses, grants_admin, grants_partner, is_active)
            values (%s, 'check', 3, false, true, true)
            """,
            (code,),
        )
    try:
        bad = client.post("/htmx/auth/check-invite", data={"inviteCode": "NOPE"})
        assert bad.status_code == 400
        assert bad.json()["ok"] is False
        good = client.post("/htmx/auth/check-invite", data={"inviteCode": code})
        assert good.status_code == 200
        assert good.json() == {"ok": True}
    finally:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("delete from invite_codes where code = %s", (code,))


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
@patch("app.auth.email_domain_resolves", return_value=True)
def test_login_incomplete_profile_soft_onboarding_prompt(_mock_dns, client):
    from app.auth import hash_password, sign_session
    from app.database import get_connection
    from app.profile_schema import ensure_profile_address_columns

    ensure_profile_address_columns()
    email = _unique_email("onboard")
    password = "password123"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into users (email, password_hash, email_verified)
            values (%s, %s, true) returning id
            """,
            (email, hash_password(password)),
        )
        user = cur.fetchone()
        cur.execute(
            "insert into profiles (id, full_name, phone) values (%s, %s, %s)",
            (user["id"], "未完成", "0911111111"),
        )

    try:
        resp = client.post(
            "/htmx/auth/login",
            headers={"HX-Request": "true"},
            data={"email": email, "password": password, "next": "/account.html"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("HX-Redirect") == "/account.html"

        client.cookies.set("imprint_session", sign_session(str(user["id"])))
        account = client.get("/htmx/account", headers={"HX-Request": "true"})
        assert not account.headers.get("HX-Redirect")
        assert account.status_code == 200
        assert "請完善個人資料" in account.text
        assert "/profile.html?onboarding=1" in account.text
        assert "稍後再說" in account.text

        # Later cookie suppresses the soft prompt for this period
        client.cookies.set("imprint_onboard_later", "1")
        later = client.get("/htmx/account", headers={"HX-Request": "true"})
        assert later.status_code == 200
        assert "請完善個人資料" not in later.text
        client.cookies.delete("imprint_onboard_later")

        save = client.post(
            "/htmx/profile?onboarding=1",
            headers={"HX-Request": "true"},
            data={
                "fullName": "完成會員",
                "phone": "0912345678",
                "shippingPostal": "106",
                "shippingCity": "台北市大安區",
                "shippingAddress": "忠孝東路四段",
                "onboarding": "1",
            },
        )
        assert save.status_code == 200
        assert save.headers.get("HX-Redirect") == "/account.html"

        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select onboarding_completed_at from profiles where id = %s",
                (user["id"],),
            )
            row = cur.fetchone()
            assert row and row["onboarding_completed_at"] is not None

        done = client.get("/htmx/account", headers={"HX-Request": "true"})
        assert done.status_code == 200
        assert "請完善個人資料" not in done.text
    finally:
        client.cookies.clear()
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("delete from users where email = %s", (email,))


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
@patch("app.captcha.verify_recaptcha", return_value=True)
@patch("app.auth.email_domain_resolves", return_value=True)
def test_api_signup_partner_bad_invite(_mock_dns, _mock_captcha, client):
    resp = client.post(
        "/api/auth/signup",
        json={
            "fullName": "測試",
            "phone": "0912345678",
            "email": _unique_email("api-partner"),
            "password": "password123",
            "acceptTerms": True,
            "isPartner": True,
            "inviteCode": "BAD-CODE",
            "g-recaptcha-response": "test-token",
        },
    )
    assert resp.status_code == 400
    assert "邀請碼" in resp.json().get("error", "")
