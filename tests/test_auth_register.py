"""Auth register — email format validation (HTMX + JSON API)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

os.environ.setdefault("STARTUP_SEED_MODE", "off")
os.environ.setdefault("RECAPTCHA_SITE_KEY", "test-recaptcha-site-key")
os.environ.setdefault("RECAPTCHA_SECRET_KEY", "test-recaptcha-secret")


@pytest.fixture(autouse=True)
def _clear_pwreset_rate_limits():
    if not os.environ.get("DATABASE_URL"):
        yield
        return
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("delete from login_lockouts where lockout_key like 'pwreset-totp:%'")
    yield


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def _register_form(**overrides):
    data = {
        "fullName": "測試會員",
        "phone": "0912345678",
        "email": "valid@example.com",
        "password": "password123",
        "passwordConfirm": "password123",
        "acceptTerms": "1",
        "g-recaptcha-response": "test-token",
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    "bad_email",
    [
        "not-an-email",
        "missing-at.com",
        "a@b",
        "a@b.c",
        "a@b.",
        "test@",
        "@x.com",
        "x@ y.com",
        "foo@bar..com",
        ".foo@bar.com",
        "user@domain",
        "user@.com",
    ],
)
def test_is_valid_email_rejects_junk(bad_email):
    from app.auth import is_valid_email

    assert is_valid_email(bad_email) is False


def test_is_valid_email_accepts_well_formed():
    from app.auth import is_valid_email

    assert is_valid_email("member@example.com") is True


@patch("app.auth.email_domain_resolves", return_value=True)
def test_validate_register_email_accepts_when_domain_resolves(_mock_dns):
    from app.auth import validate_register_email

    assert validate_register_email("member@example.com") is None


@patch("app.auth.email_domain_resolves", return_value=False)
def test_validate_register_email_rejects_unresolvable_domain(_mock_dns):
    from app.auth import EMAIL_DOMAIN_ERROR, validate_register_email

    assert validate_register_email("member@example.com") == EMAIL_DOMAIN_ERROR


def test_htmx_register_rejects_invalid_email(client):
    resp = client.post(
        "/htmx/auth/register",
        headers={"HX-Request": "true"},
        data=_register_form(email="not-an-email"),
    )
    assert resp.status_code == 400
    assert "有效的 Email" in resp.text
    assert 'class="form-msg is-err"' in resp.text


@pytest.mark.parametrize("bad_email", ["missing-at.com", "a@b", "a@b.c", "test@", "@x.com", "foo@bar..com"])
def test_api_signup_rejects_invalid_email(client, bad_email):
    resp = client.post(
        "/api/auth/signup",
        json={
            "fullName": "測試會員",
            "phone": "0912345678",
            "email": bad_email,
            "password": "password123",
            "acceptTerms": True,
        },
    )
    assert resp.status_code == 400
    assert resp.json().get("error") == "請輸入有效的 Email 格式"


@patch("app.auth.email_domain_resolves", return_value=False)
def test_api_signup_rejects_unresolvable_domain(_mock_dns, client):
    resp = client.post(
        "/api/auth/signup",
        json={
            "fullName": "測試會員",
            "phone": "0912345678",
            "email": "member@example.com",
            "password": "password123",
            "acceptTerms": True,
        },
    )
    assert resp.status_code == 400
    assert "網域" in resp.json().get("error", "")


@patch("app.auth.email_domain_resolves", return_value=False)
def test_htmx_register_rejects_unresolvable_domain(_mock_dns, client):
    resp = client.post(
        "/htmx/auth/register",
        headers={"HX-Request": "true"},
        data=_register_form(email="member@example.com"),
    )
    assert resp.status_code == 400
    assert "網域" in resp.text
    assert 'class="form-msg is-err"' in resp.text


def test_check_email_rejects_empty(client):
    resp = client.post("/htmx/auth/check-email", data={"email": ""})
    assert resp.status_code == 400
    body = resp.json()
    assert body["ok"] is False
    assert "Email" in body["error"]


@pytest.mark.parametrize("bad_email", ["not-an-email", "a@b", "missing-at.com"])
def test_check_email_rejects_invalid_format(client, bad_email):
    resp = client.post("/htmx/auth/check-email", data={"email": bad_email})
    assert resp.status_code == 400
    body = resp.json()
    assert body["ok"] is False
    assert "Email" in body["error"]


@patch("app.auth.email_domain_resolves", return_value=True)
def test_check_email_accepts_valid_domain(_mock_dns, client):
    resp = client.post("/htmx/auth/check-email", data={"email": "member@example.com"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@patch("app.auth.email_domain_resolves", return_value=False)
def test_check_email_rejects_unresolvable_domain(_mock_dns, client):
    from app.auth import EMAIL_DOMAIN_ERROR

    resp = client.post("/htmx/auth/check-email", data={"email": "member@example.com"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["ok"] is False
    assert body["error"] == EMAIL_DOMAIN_ERROR


def test_register_page_includes_validation_assets(client, monkeypatch):
    monkeypatch.setenv("RECAPTCHA_SITE_KEY", "test-recaptcha-site-key")
    resp = client.get("/register")
    assert resp.status_code == 200
    assert "auth-shell.js?v=8" in resp.text
    assert "auth.css?v=12" in resp.text
    assert 'id="registerForm"' in resp.text
    assert 'hx-post="/htmx/auth/register"' in resp.text
    assert 'name="g-recaptcha-response"' in resp.text
    assert 'data-recaptcha-sitekey="test-recaptcha-site-key"' in resp.text
    assert "www.google.com/recaptcha/api.js?render=test-recaptcha-site-key" in resp.text
    assert 'class="g-recaptcha"' not in resp.text
    assert "onload=__imprintRecaptchaOnload" not in resp.text
    assert "render=explicit" not in resp.text
    assert 'name="captcha"' not in resp.text
    assert "/api/auth/captcha" not in resp.text
    assert "recaptcha-v3-hint" not in resp.text
    assert 'class="recaptcha-disclosure"' in resp.text
    assert "https://policies.google.com/privacy" in resp.text
    assert "https://policies.google.com/terms" in resp.text
    assert "本表單受 reCAPTCHA 保護" in resp.text
    csp = resp.headers.get("content-security-policy", "")
    assert "https://www.google.com" in csp
    assert "https://www.gstatic.com" in csp


def test_register_page_shows_config_message_without_site_key(client, monkeypatch):
    monkeypatch.setenv("RECAPTCHA_SITE_KEY", "")
    resp = client.get("/register")
    assert resp.status_code == 200
    assert "註冊驗證尚未設定" in resp.text
    assert "data-recaptcha-sitekey" not in resp.text
    assert 'name="g-recaptcha-response"' not in resp.text
    assert 'id="registerSubmitBtn"' in resp.text
    assert "disabled" in resp.text





def test_htmx_forgot_password_requires_verification_cookie(client):

    resp = client.post(

        "/htmx/auth/forgot-password",

        headers={"HX-Request": "true"},

        data={"password": "newpassword123", "passwordConfirm": "newpassword123"},

    )

    assert resp.status_code == 401

    assert "驗證已過期" in resp.text

    assert 'class="form-msg is-err"' in resp.text





@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")

def test_htmx_forgot_password_verify_rejects_invalid_email(client):

    resp = client.post(

        "/htmx/auth/forgot-password-verify",

        headers={"HX-Request": "true"},

        data={"email": "not-an-email", "code": "123456"},

    )

    assert resp.status_code == 400

    assert "有效的 Email" in resp.text

    assert 'class="form-msg is-err"' in resp.text





@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")

def test_htmx_forgot_password_verify_rejects_empty_fields(client):

    resp = client.post(

        "/htmx/auth/forgot-password-verify",

        headers={"HX-Request": "true"},

        data={"email": "", "code": ""},

    )

    assert resp.status_code == 400

    assert "請輸入 Email。" in resp.text





@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")

def test_htmx_forgot_password_rejects_short_password(client):

    from app.auth import PWRESET_COOKIE_NAME, sign_pwreset



    user_id = "00000000-0000-0000-0000-000000000001"

    resp = client.post(

        "/htmx/auth/forgot-password",

        headers={"HX-Request": "true"},

        cookies={PWRESET_COOKIE_NAME: sign_pwreset(user_id)},

        data={"password": "short", "passwordConfirm": "short"},

    )

    assert resp.status_code in (400, 401)

    if resp.status_code == 400:

        assert "密碼至少需要 8 碼" in resp.text





@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")

def test_htmx_forgot_password_rejects_password_mismatch(client):

    from app.auth import PWRESET_COOKIE_NAME, sign_pwreset



    user_id = "00000000-0000-0000-0000-000000000001"

    resp = client.post(

        "/htmx/auth/forgot-password",

        headers={"HX-Request": "true"},

        cookies={PWRESET_COOKIE_NAME: sign_pwreset(user_id)},

        data={"password": "newpassword123", "passwordConfirm": "different456"},

    )

    assert resp.status_code in (400, 401)

    if resp.status_code == 400:

        assert "兩次密碼不一致" in resp.text





@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")

def test_htmx_forgot_password_rejects_empty_fields(client):

    from app.auth import PWRESET_COOKIE_NAME, sign_pwreset



    user_id = "00000000-0000-0000-0000-000000000001"

    resp = client.post(

        "/htmx/auth/forgot-password",

        headers={"HX-Request": "true"},

        cookies={PWRESET_COOKIE_NAME: sign_pwreset(user_id)},

        data={"password": "", "passwordConfirm": ""},

    )

    assert resp.status_code in (400, 401)

    if resp.status_code == 400:

        assert "請輸入新密碼" in resp.text


