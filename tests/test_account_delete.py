"""Account delete: member self-serve + admin account-action."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

os.environ.setdefault("STARTUP_SEED_MODE", "off")
os.environ.setdefault("JWT_SECRET", os.environ.get("JWT_SECRET") or "test-jwt-secret-for-account-delete")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def _create_user(*, admin: bool = False) -> tuple[str, str]:
    from app.auth import hash_password
    from app.database import get_connection

    email = f"del-acct-{uuid.uuid4().hex[:10]}@example.com"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into users (email, password_hash, email_verified, is_active)
            values (%s, %s, true, true)
            returning id
            """,
            (email, hash_password("password123")),
        )
        user_id = str(cur.fetchone()["id"])
        cur.execute(
            "insert into profiles (id, full_name) values (%s, %s) on conflict do nothing",
            (user_id, "刪除測試"),
        )
        if admin:
            cur.execute(
                "insert into staff_admins (user_id) values (%s) on conflict do nothing",
                (user_id,),
            )
    return user_id, email


def _session_cookies(user_id: str) -> dict[str, str]:
    from app.auth import COOKIE_NAME, sign_session
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select token_version from users where id = %s", (user_id,))
        row = cur.fetchone() or {}
    token = sign_session(user_id, int(row.get("token_version") or 0))
    return {COOKIE_NAME: token}


def _user_exists(user_id: str) -> bool:
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from users where id = %s", (user_id,))
        return cur.fetchone() is not None


def _cleanup(user_id: str) -> None:
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("delete from staff_admins where user_id = %s", (user_id,))
        cur.execute("delete from users where id = %s", (user_id,))


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_account_delete_unauthenticated_rejects(client):
    resp = client.post(
        "/htmx/account/delete",
        headers={"HX-Request": "true"},
        data={"confirmEmail": "nobody@example.com"},
    )
    assert resp.status_code == 401
    assert "請先登入" in resp.text
    assert not resp.headers.get("HX-Redirect")


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_account_delete_happy_path_clears_session(client):
    from app.auth import COOKIE_NAME

    user_id, email = _create_user()
    try:
        cookies = _session_cookies(user_id)
        resp = client.post(
            "/htmx/account/delete",
            headers={"HX-Request": "true"},
            data={"confirmEmail": email},
            cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.headers.get("HX-Redirect") == "/"
        assert not _user_exists(user_id)
        # Session cookie cleared (deleted or emptied).
        cleared = resp.cookies.get(COOKIE_NAME)
        assert cleared in (None, "")
    finally:
        if _user_exists(user_id):
            _cleanup(user_id)


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_account_delete_wrong_email_keeps_user(client):
    user_id, email = _create_user()
    try:
        resp = client.post(
            "/htmx/account/delete",
            headers={"HX-Request": "true"},
            data={"confirmEmail": "wrong-" + email},
            cookies=_session_cookies(user_id),
        )
        assert resp.status_code == 400
        assert "Email 不符" in resp.text
        assert _user_exists(user_id)
    finally:
        _cleanup(user_id)


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_admin_account_delete_happy_path(client):
    admin_id, _admin_email = _create_user(admin=True)
    target_id, target_email = _create_user()
    try:
        resp = client.post(
            "/api/admin/account-action",
            json={"id": target_id, "action": "delete", "confirmEmail": target_email},
            cookies=_session_cookies(admin_id),
        )
        assert resp.status_code == 200
        assert resp.json().get("ok") is True
        assert not _user_exists(target_id)
    finally:
        if _user_exists(target_id):
            _cleanup(target_id)
        _cleanup(admin_id)


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_admin_account_delete_non_admin_rejected(client):
    member_id, _member_email = _create_user()
    target_id, target_email = _create_user()
    try:
        resp = client.post(
            "/api/admin/account-action",
            json={"id": target_id, "action": "delete", "confirmEmail": target_email},
            cookies=_session_cookies(member_id),
        )
        assert resp.status_code == 403
        assert _user_exists(target_id)
    finally:
        _cleanup(target_id)
        _cleanup(member_id)
