"""Reset-password confirm field + leftover forgot-password UI pins."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def _htmx_reset_fn() -> str:
    src = (ROOT / "app" / "controllers" / "htmx_auth.py").read_text(encoding="utf-8")
    return src.split("async def auth_reset_password", 1)[1].split("async def ", 1)[0]


def _json_reset_fn() -> str:
    src = (ROOT / "app" / "controllers" / "auth_controller.py").read_text(encoding="utf-8")
    return src.split("async def reset_password", 1)[1].split("async def ", 1)[0]


def _htmx_verify_fn() -> str:
    src = (ROOT / "app" / "controllers" / "htmx_auth.py").read_text(encoding="utf-8")
    return src.split("async def auth_forgot_password_verify", 1)[1].split("async def ", 1)[0]


def _json_verify_fn() -> str:
    src = (ROOT / "app" / "controllers" / "auth_controller.py").read_text(encoding="utf-8")
    return src.split("async def forgot_password_verify", 1)[1].split("async def ", 1)[0]


def test_reset_password_handlers_require_confirm_and_drop_old_error():
    for src in (_htmx_reset_fn(), _json_reset_fn()):
        assert "passwordConfirm" in src
        assert "請輸入新密碼並再次確認。" in src
        assert "兩次密碼不一致。" in src
        assert "密碼至少需要 8 碼。" in src
        assert "重設連結無效或已過期，請重新申請。" in src
        assert "缺少驗證碼或新密碼" not in src


def test_verify_handlers_split_empty_backup_and_totp():
    for src in (_htmx_verify_fn(), _json_verify_fn()):
        assert "請輸入備用碼" in src
        assert "請輸入完整的 6 位數驗證碼。" in src
        assert src.index("請輸入備用碼") < src.index("請輸入完整的 6 位數驗證碼。")


def test_reset_password_page_is_separate_landing(client):
    resp = client.get("/reset-password?token=leak-me")
    assert resp.status_code == 200
    assert resp.headers.get("referrer-policy") == "no-referrer"
    assert '<meta name="referrer" content="no-referrer">' in resp.text
    assert 'name="passwordConfirm"' in resp.text
    assert "確認新密碼" in resp.text
    assert "reset-password.js?v=1" in resp.text
    assert "auth-shell.js" not in resp.text
    assert "particles-canvas" not in resp.text
    assert "缺少驗證碼或新密碼" not in resp.text


def test_reset_password_js_has_client_checks_and_error_swap():
    src = (ROOT / "public" / "js" / "reset-password.js").read_text(encoding="utf-8")
    assert "請輸入新密碼並再次確認。" in src
    assert "兩次密碼不一致。" in src
    assert "密碼至少需要 8 碼。" in src
    assert "htmx:beforeSwap" in src
    assert "shouldSwap = true" in src
    assert "resetPasswordForm" in src
    assert "#auth-form-msg" in src
    assert "auth-shell" not in src


def test_api_client_reset_password_sends_confirm():
    src = (ROOT / "public" / "js" / "api-client.js").read_text(encoding="utf-8")
    fn = src.split("resetPassword: function", 1)[1].split("verifyPasswordResetTotp", 1)[0]
    assert "passwordConfirm" in fn
    assert "newPassword" in fn


def test_login_mints_forgot_password_anchor():
    css = (ROOT / "public" / "css" / "auth.css").read_text(encoding="utf-8")
    login = (
        ROOT / "content" / "site" / "templates" / "pages" / "login.html"
    ).read_text(encoding="utf-8")
    assert ".login-container .forgot-password a" in css
    assert "color: var(--login-mint-deep)" in css.split(".login-container .forgot-password a", 1)[1].split("}", 1)[0]
    assert 'class="forgot-password"><a href="/forgot-password">忘記密碼？</a>' in login
    assert "auth.css?v=14" in login


def test_forgot_password_first_screen_copy_locked():
    html = (
        ROOT / "content" / "site" / "templates" / "pages" / "forgot-password.html"
    ).read_text(encoding="utf-8")
    assert "<h1>忘記密碼</h1>" in html
    assert "可用信件重設，也可以使用驗證碼。" in html
    assert 'label for="fpEmail">電子郵件' in html
    assert "寄出重設信件" in html
    assert "auth_divider('或')" in html
    assert "使用驗證碼" in html
    assert "Authenticator 的 6 位數或備用碼" in html
    assert "返回登入" in html
    assert "驗證碼 → 新密碼" not in html
    assert "data-fp-home-header" in html
    assert 'class="login-button login-button--outline" data-fp-back="1"' in html


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_htmx_reset_password_empty_fields(client):
    resp = client.post(
        "/htmx/auth/reset-password",
        headers={"HX-Request": "true"},
        data={"token": "abc", "password": "", "passwordConfirm": ""},
    )
    assert resp.status_code == 400
    assert "請輸入新密碼並再次確認。" in resp.text
    assert "缺少驗證碼或新密碼" not in resp.text


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_htmx_reset_password_mismatch(client):
    resp = client.post(
        "/htmx/auth/reset-password",
        headers={"HX-Request": "true"},
        data={"token": "abc", "password": "newpassword123", "passwordConfirm": "otherpass123"},
    )
    assert resp.status_code == 400
    assert "兩次密碼不一致。" in resp.text


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_htmx_reset_password_short(client):
    resp = client.post(
        "/htmx/auth/reset-password",
        headers={"HX-Request": "true"},
        data={"token": "abc", "password": "short", "passwordConfirm": "short"},
    )
    assert resp.status_code == 400
    assert "密碼至少需要 8 碼。" in resp.text


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_htmx_reset_password_missing_token(client):
    resp = client.post(
        "/htmx/auth/reset-password",
        headers={"HX-Request": "true"},
        data={"token": "", "password": "newpassword123", "passwordConfirm": "newpassword123"},
    )
    assert resp.status_code == 400
    assert "重設連結無效或已過期，請重新申請。" in resp.text


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_json_reset_password_validation_messages(client):
    empty = client.post(
        "/api/auth/reset-password",
        json={"token": "abc", "newPassword": "", "passwordConfirm": ""},
    )
    assert empty.status_code == 400
    assert empty.json()["error"] == "請輸入新密碼並再次確認。"

    mismatch = client.post(
        "/api/auth/reset-password",
        json={"token": "abc", "newPassword": "newpassword123", "passwordConfirm": "otherpass123"},
    )
    assert mismatch.status_code == 400
    assert mismatch.json()["error"] == "兩次密碼不一致。"

    short = client.post(
        "/api/auth/reset-password",
        json={"token": "abc", "newPassword": "short", "passwordConfirm": "short"},
    )
    assert short.status_code == 400
    assert short.json()["error"] == "密碼至少需要 8 碼。"

    missing = client.post(
        "/api/auth/reset-password",
        json={"token": "", "newPassword": "newpassword123", "passwordConfirm": "newpassword123"},
    )
    assert missing.status_code == 400
    assert missing.json()["error"] == "重設連結無效或已過期，請重新申請。"


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_htmx_verify_empty_totp_and_backup(client):
    totp = client.post(
        "/htmx/auth/forgot-password-verify",
        headers={"HX-Request": "true"},
        data={"email": "anyone@example.com", "code": ""},
    )
    assert totp.status_code == 400
    assert "請輸入完整的 6 位數驗證碼。" in totp.text
    assert "請輸入備用碼" not in totp.text

    backup = client.post(
        "/htmx/auth/forgot-password-verify",
        headers={"HX-Request": "true"},
        data={"email": "anyone@example.com", "code": "", "backup": "1"},
    )
    assert backup.status_code == 400
    assert "請輸入備用碼" in backup.text
    assert "請輸入完整的 6 位數驗證碼。" not in backup.text


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_json_verify_empty_totp_and_backup(client):
    totp = client.post(
        "/api/auth/forgot-password-verify",
        json={"email": "anyone@example.com", "code": ""},
    )
    assert totp.status_code == 400
    assert totp.json()["error"] == "請輸入完整的 6 位數驗證碼。"

    backup = client.post(
        "/api/auth/forgot-password-verify",
        json={"email": "anyone@example.com", "code": "", "backup": True},
    )
    assert backup.status_code == 400
    assert backup.json()["error"] == "請輸入備用碼"


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_htmx_verify_invalid_backup_is_generic(client):
    resp = client.post(
        "/htmx/auth/forgot-password-verify",
        headers={"HX-Request": "true"},
        data={"email": "anyone@example.com", "code": "ABCD-1234", "backup": "1"},
    )
    assert resp.status_code == 401
    assert "Email 或驗證碼不正確。" in resp.text
    assert "請輸入完整的 6 位數驗證碼。" not in resp.text
