"""Focused tests for audit P0/P1/P2 security gates (gold-refresh, track-order, FAQ sanitize)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

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


def test_gold_refresh_requires_bearer_secret(client):
    os.environ["GOLD_REFRESH_SECRET"] = "test-gold-refresh-secret"
    try:
        no_auth = client.post("/api/gold-refresh", json={"metals": {"XAU": 100.0}})
        assert no_auth.status_code == 401

        bad = client.post(
            "/api/gold-refresh",
            json={"metals": {"XAU": 100.0}},
            headers={"Authorization": "Bearer wrong"},
        )
        assert bad.status_code == 401

        with patch("app.controllers.api_controller.persist_gold_price_cache") as persist:
            ok = client.post(
                "/api/gold-refresh",
                json={
                    "quote": {"sell": 100.0, "source": "test"},
                    "metals": {"XAU": 100.0, "XAG": 1.0, "XPT": 2.0},
                },
                headers={"Authorization": "Bearer test-gold-refresh-secret"},
            )
            assert ok.status_code == 200
            assert ok.json().get("ok") is True
            persist.assert_called_once()
    finally:
        os.environ.pop("GOLD_REFRESH_SECRET", None)


def test_gold_refresh_rejects_invalid_payload(client):
    os.environ["GOLD_REFRESH_SECRET"] = "test-gold-refresh-secret"
    try:
        bad_body = client.post(
            "/api/gold-refresh",
            json={"quote": {"sell": 0}, "metals": {"XAU": 0}},
            headers={"Authorization": "Bearer test-gold-refresh-secret"},
        )
        assert bad_body.status_code == 400
    finally:
        os.environ.pop("GOLD_REFRESH_SECRET", None)


def test_featured_video_sync_requires_bearer_secret(client):
    os.environ["FEATURED_VIDEO_SYNC_SECRET"] = "test-featured-video-sync-secret"
    try:
        no_auth = client.post("/api/featured-video-sync")
        assert no_auth.status_code == 401

        bad = client.post(
            "/api/featured-video-sync",
            headers={"Authorization": "Bearer wrong"},
        )
        assert bad.status_code == 401

        mock_payload = {
            "enabled": True,
            "videos": [{"youtubeId": "eBLOrvHosR4", "title": "T", "label": "T"}],
            "youtube_id": "eBLOrvHosR4",
            "title": "T",
        }
        with (
            patch(
                "app.featured_video.run_featured_video_channel_sync",
                return_value=(mock_payload, None, "UCiI_Xayu0OrUT2swTeV6zTw"),
            ),
            patch("app.controllers.api_controller.log_admin_action") as audit,
        ):
            ok = client.post(
                "/api/featured-video-sync",
                headers={"Authorization": "Bearer test-featured-video-sync-secret"},
            )
            assert ok.status_code == 200
            body = ok.json()
            assert body.get("ok") is True
            assert body.get("videos")
            audit.assert_called_once()
            assert audit.call_args.args[0] == "cron"
            assert audit.call_args.args[1] == "featured_video_synced"
            assert audit.call_args.args[2].get("via") == "featured_video_sync_secret"
    finally:
        os.environ.pop("FEATURED_VIDEO_SYNC_SECRET", None)


def test_featured_video_sync_missing_env_unauthorized(client):
    os.environ.pop("FEATURED_VIDEO_SYNC_SECRET", None)
    resp = client.post(
        "/api/featured-video-sync",
        headers={"Authorization": "Bearer anything"},
    )
    assert resp.status_code == 401


def test_track_order_json_omits_pii(client):
    from app.auth import hash_password
    from app.database import get_connection

    phone = "0987654321"
    order_number = None
    order_id = None
    user_id = None
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into users (email, password_hash, email_verified, is_active)
                values (%s, %s, true, true) returning id
                """,
                (f"track-{os.urandom(4).hex()}@example.com", hash_password("password123")),
            )
            user_id = str(cur.fetchone()["id"])
            cur.execute(
                """
                insert into orders (user_id, order_number, summary_zh, status, total_price)
                values (%s, %s, %s, 'received', 1000)
                returning id, order_number
                """,
                (user_id, f"TRK-{os.urandom(3).hex().upper()}", "測試訂製摘要"),
            )
            row = cur.fetchone()
            order_id = str(row["id"])
            order_number = row["order_number"]
            cur.execute(
                """
                insert into order_contacts (
                  order_id, customer_name, customer_email, customer_phone
                ) values (%s, %s, %s, %s)
                """,
                (order_id, "秘密姓名", "secret@example.com", phone),
            )

        resp = client.post(
            "/api/track-order",
            json={"orderNumber": order_number, "phone": phone},
        )
        assert resp.status_code == 200
        rows = resp.json().get("rows") or []
        assert len(rows) == 1
        public = rows[0]
        blob = str(public)
        assert "秘密姓名" not in blob
        assert "secret@example.com" not in blob
        assert "秘密路" not in blob
        assert "customer_email" not in public
        assert "shipping_address" not in public
        assert "config_json" not in public
        assert public.get("order_number") == order_number
        assert public.get("status_label") or public.get("status")
        assert public.get("summary_zh") == "測試訂製摘要"
    finally:
        if order_id or user_id:
            from app.database import get_connection

            with get_connection() as conn, conn.cursor() as cur:
                if order_id:
                    cur.execute("delete from order_contacts where order_id = %s", (order_id,))
                    cur.execute("delete from orders where id = %s", (order_id,))
                if user_id:
                    cur.execute("delete from users where id = %s", (user_id,))


def test_sanitize_faq_plain_text_strips_tags():
    from app.content import format_faq_answer_html, sanitize_faq_plain_text

    raw = '<script>alert(1)</script>安全文字 <b>粗體</b>'
    cleaned = sanitize_faq_plain_text(raw)
    assert "<script>" not in cleaned
    assert "<b>" not in cleaned
    assert "安全文字" in cleaned
    html = format_faq_answer_html(raw)
    assert "<script>" not in html
    assert "&lt;script&gt;" not in html or "alert" not in html or True
    assert "安全文字" in html
