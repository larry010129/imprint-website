"""Forgot-password email send (shop mailer) + both reset paths."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")

from app.mail import DEFAULT_FROM, PASSWORD_RESET_SUBJECT, send_password_reset_email


@pytest.fixture(autouse=True)
def _clear_pwreset_rate_limits():
    if not os.environ.get("DATABASE_URL"):
        yield
        return
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("delete from login_lockouts where lockout_key like 'pwreset:%'")
    yield


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def test_password_reset_email_uses_shop_html_and_token_link(monkeypatch):
    captured: dict = {}

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=12):
        captured["url"] = req.full_url
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        captured["auth"] = req.get_header("Authorization")
        return _Resp()

    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.delenv("RESET_EMAIL_FROM", raising=False)
    monkeypatch.delenv("EMAIL_FROM", raising=False)
    monkeypatch.setattr("app.mail.urllib.request.urlopen", fake_urlopen)

    ok = send_password_reset_email(
        to="member@example.com",
        reset_url="https://www.imprintdiamond.com/reset-password?token=abc123",
    )
    assert ok is True
    payload = captured["payload"]
    assert payload["subject"] == PASSWORD_RESET_SUBJECT
    assert payload["from"] == DEFAULT_FROM
    assert payload["to"] == ["member@example.com"]
    assert "reset-password?token=abc123" in payload["text"]
    assert "reset-password?token=abc123" in payload["html"]
    assert "<a href=" in payload["html"]
    assert 'referrerpolicy="no-referrer"' in payload["html"]
    assert 'rel="noreferrer"' in payload["html"]
    assert "Resend" not in payload["text"]
    assert "Resend" not in payload["html"]
    assert "Supabase" not in payload["text"]
    assert captured["auth"] == "Bearer re_test_key"


def test_password_reset_email_skips_without_api_key(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "")
    called = {"n": 0}

    def boom(*_a, **_k):
        called["n"] += 1
        raise AssertionError("must not call Resend without key")

    monkeypatch.setattr("app.mail.urllib.request.urlopen", boom)
    assert send_password_reset_email(to="a@b.com", reset_url="https://x/reset-password?token=t") is False
    assert called["n"] == 0


def test_forgot_password_page_does_not_name_resend():
    html = (
        Path(__file__).resolve().parents[1]
        / "content"
        / "site"
        / "templates"
        / "pages"
        / "forgot-password.html"
    ).read_text(encoding="utf-8")
    assert "Resend" not in html
    assert "resend" not in html.lower()
    assert "可用信件重設，也可以使用驗證碼。" in html
    assert "寄出重設信件" in html
    assert "Authenticator 的 6 位數或備用碼" in html
    assert "請開啟主旨為「重設銘印鑽石帳戶密碼」的信件" in html
    assert "Authenticator 6 位數或備用碼" not in html
    assert "寄送重設信件" not in html
    assert "寄出重設連結" not in html
    assert "用信件重設，或使用驗證碼。兩種方式都可以。" not in html
    assert "輸入註冊信箱，選擇重設方式。" not in html
    assert "totp-banner" not in html
    assert "fp-steps" not in html
    assert 'hx-post="/htmx/auth/request-reset"' in html
    assert "data-fp-use-totp" in html
    assert "login-button--outline" in html
    assert "auth_divider('或')" in html
    assert '<p class="auth-divider">或使用</p>' not in html
    assert '<a href="#" data-fp-use-totp>已啟用 Authenticator？使用驗證碼</a>' in html
    assert 'data-fp-step="inbox"' in html
    assert 'hx-post="/htmx/auth/forgot-password-verify"' in html
    assert "totp_enabled" not in html
    assert "totpEnabled" not in html


def test_forgot_password_email_path_is_not_gated_on_totp():
    """Both first-screen actions stay live. Email send must not check totp_enabled."""
    root = Path(__file__).resolve().parents[1]
    page = (root / "content" / "site" / "templates" / "pages" / "forgot-password.html").read_text(
        encoding="utf-8"
    )
    js = (root / "public" / "js" / "forgot-password.js").read_text(encoding="utf-8")
    htmx = (root / "app" / "controllers" / "htmx_auth.py").read_text(encoding="utf-8")
    api = (root / "app" / "controllers" / "auth_controller.py").read_text(encoding="utf-8")
    assert "寄出重設信件" in page
    assert "使用驗證碼" in page
    assert "login-button--outline" in page
    assert "totp_enabled" not in js
    assert "totpEnabled" not in js
    reset_fn = htmx.split("async def auth_request_reset", 1)[1].split("async def ", 1)[0]
    assert "totp_enabled" not in reset_fn
    json_fn = api.split("async def request_password_reset", 1)[1].split("async def ", 1)[0]
    assert "totp_enabled" not in json_fn


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_htmx_request_reset_unknown_email_is_generic(client):
    with patch("app.mail.send_password_reset_email") as send:
        resp = client.post(
            "/htmx/auth/request-reset",
            headers={"HX-Request": "true"},
            data={"email": f"missing-{uuid.uuid4().hex[:8]}@example.com"},
        )
    assert resp.status_code == 200
    assert "若此 Email 已註冊" in resp.text
    assert resp.headers.get("HX-Trigger") == "fp-email-sent"
    send.assert_not_called()


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_htmx_request_reset_known_email_sends_token_link(client):
    from app.auth import hash_password
    from app.database import get_connection

    email = f"reset-mail-{uuid.uuid4().hex[:10]}@example.com"
    user_id = None
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into users (email, password_hash, email_verified)
                values (%s, %s, true) returning id
                """,
                (email, hash_password("password123")),
            )
            user_id = str(cur.fetchone()["id"])

        with patch("app.mail.send_password_reset_email", return_value=True) as send:
            resp = client.post(
                "/htmx/auth/request-reset",
                headers={"HX-Request": "true"},
                data={"email": email},
            )
        assert resp.status_code == 200
        assert "若此 Email 已註冊" in resp.text
        send.assert_called_once()
        kwargs = send.call_args.kwargs
        assert kwargs["to"] == email
        assert "/reset-password?token=" in kwargs["reset_url"]
    finally:
        if user_id:
            with get_connection() as conn, conn.cursor() as cur:
                cur.execute("delete from password_reset_tokens where user_id = %s", (user_id,))
                cur.execute("delete from users where id = %s", (user_id,))


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_htmx_request_reset_sends_when_totp_enabled(client):
    from app.auth import hash_password
    from app.database import get_connection
    from app.totp import generate_secret

    email = f"reset-totp-{uuid.uuid4().hex[:10]}@example.com"
    user_id = None
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into users (email, password_hash, email_verified, totp_secret, totp_enabled)
                values (%s, %s, true, %s, true) returning id
                """,
                (email, hash_password("password123"), generate_secret()),
            )
            user_id = str(cur.fetchone()["id"])

        with patch("app.mail.send_password_reset_email", return_value=True) as send:
            resp = client.post(
                "/htmx/auth/request-reset",
                headers={"HX-Request": "true"},
                data={"email": email},
            )
        assert resp.status_code == 200
        assert "若此 Email 已註冊" in resp.text
        send.assert_called_once()
        assert send.call_args.kwargs["to"] == email
    finally:
        if user_id:
            with get_connection() as conn, conn.cursor() as cur:
                cur.execute("delete from password_reset_tokens where user_id = %s", (user_id,))
                cur.execute("delete from users where id = %s", (user_id,))


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_json_request_reset_unknown_email_is_generic(client):
    with patch("app.mail.send_password_reset_email") as send:
        resp = client.post(
            "/api/auth/request-password-reset",
            json={"email": f"missing-{uuid.uuid4().hex[:8]}@example.com"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    send.assert_not_called()


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_reset_password_page_sends_no_referrer(client):
    resp = client.get("/reset-password?token=leak-me")
    assert resp.status_code == 200
    assert resp.headers.get("referrer-policy") == "no-referrer"
    assert '<meta name="referrer" content="no-referrer">' in resp.text
    login = client.get("/login")
    assert login.status_code == 200
    assert login.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def _insert_reset_user(*, totp_enabled: bool = False, admin: bool = False) -> tuple[str, str]:
    from app.auth import hash_password
    from app.database import get_connection
    from app.totp import generate_secret

    email = f"reset-mail-{uuid.uuid4().hex[:10]}@example.com"
    secret = generate_secret() if totp_enabled else None
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into users (email, password_hash, email_verified, totp_secret, totp_enabled)
            values (%s, %s, true, %s, %s)
            returning id
            """,
            (email, hash_password("password123"), secret, totp_enabled),
        )
        user_id = str(cur.fetchone()["id"])
        if admin:
            cur.execute(
                "insert into staff_admins (user_id) values (%s) on conflict do nothing",
                (user_id,),
            )
    return user_id, email


def _delete_reset_user(user_id: str) -> None:
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("delete from password_reset_tokens where user_id = %s", (user_id,))
        cur.execute("delete from staff_admins where user_id = %s", (user_id,))
        cur.execute("delete from users where id = %s", (user_id,))


def _clear_pwreset_ip_keys() -> None:
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            delete from login_lockouts
            where lockout_key like 'pwreset:%'
              and lockout_key not like 'pwreset:acct:%'
            """
        )


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_htmx_request_reset_sends_for_totp_enabled_and_staff(client):
    cases = (
        {"totp_enabled": True, "admin": False},
        {"totp_enabled": True, "admin": True},
    )
    for kwargs in cases:
        user_id, email = _insert_reset_user(**kwargs)
        try:
            with patch("app.mail.send_password_reset_email", return_value=True) as send:
                resp = client.post(
                    "/htmx/auth/request-reset",
                    headers={"HX-Request": "true"},
                    data={"email": email},
                )
            assert resp.status_code == 200
            assert "若此 Email 已註冊" in resp.text
            send.assert_called_once()
            assert send.call_args.kwargs["to"] == email
            from app.database import get_connection

            with get_connection() as conn, conn.cursor() as cur:
                cur.execute("select totp_enabled from users where id = %s", (user_id,))
                assert cur.fetchone()["totp_enabled"] is True
        finally:
            _delete_reset_user(user_id)


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_request_reset_email_subject_rate_limit_is_generic(client):
    user_id, email = _insert_reset_user()
    mixed = f"  {email.upper()}  "
    try:
        with patch("app.mail.send_password_reset_email", return_value=True) as send:
            for _ in range(5):
                resp = client.post(
                    "/htmx/auth/request-reset",
                    headers={"HX-Request": "true"},
                    data={"email": mixed},
                )
                assert resp.status_code == 200
                assert "若此 Email 已註冊" in resp.text
            assert send.call_count == 5
            _clear_pwreset_ip_keys()
            limited = client.post(
                "/htmx/auth/request-reset",
                headers={"HX-Request": "true"},
                data={"email": email},
            )
            assert limited.status_code == 429
            assert "請求過於頻繁" in limited.text
            assert "若此 Email 已註冊" not in limited.text
            assert send.call_count == 5

            json_limited = client.post(
                "/api/auth/request-password-reset",
                json={"email": mixed},
            )
            assert json_limited.status_code == 429
            assert json_limited.json()["error"] == "請求過於頻繁，請稍後再試"
            assert send.call_count == 5
    finally:
        _delete_reset_user(user_id)


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_request_reset_empty_email_omits_subject_key(client):
    from app.database import get_connection

    with patch("app.mail.send_password_reset_email") as send:
        resp = client.post(
            "/htmx/auth/request-reset",
            headers={"HX-Request": "true"},
            data={"email": "   "},
        )
    assert resp.status_code == 400
    assert "請輸入 Email" in resp.text
    send.assert_not_called()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select lockout_key from login_lockouts where lockout_key like 'pwreset:acct:%'"
        )
        assert cur.fetchall() == []


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_totp_verify_path_still_rejects_bad_code(client):
    resp = client.post(
        "/htmx/auth/forgot-password-verify",
        headers={"HX-Request": "true"},
        data={"email": "anyone@example.com", "code": "000000"},
    )
    assert resp.status_code == 401
    assert "Email 或驗證碼不正確" in resp.text or "不正確" in resp.text
