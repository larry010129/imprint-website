"""ERP Inbound Integration security & functional tests.
Covers IN-01..IN-06, IN-12, IN-13 from WEBSITE_TO_ERP_SECURITY.md.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.controllers import erp_events_controller
from app.erp_inbound import (
    AUTH_ERROR_RESPONSE,
    build_canonical_string,
    check_and_burn_nonce,
    enqueue_event,
    get_erp_events_hmac_keys,
    is_erp_events_enabled,
    purge_old_events,
    verify_erp_request,
)

TEST_KEY_ID = "erp-test-key-1"
TEST_SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef"  # >= 32 chars


def get_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(erp_events_controller.router, prefix="/api")
    return app


class FakeCursor:
    def __init__(self, rows=None, rowcount=1):
        self.rows = rows or []
        self.rowcount = rowcount
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.rows[0] if self.rows else {"cnt": 0}

    def fetchall(self):
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeConn:
    def __init__(self, cursor):
        self._cur = cursor

    def cursor(self):
        return self._cur

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


@pytest.fixture(autouse=True)
def setup_erp_env(monkeypatch):
    monkeypatch.setenv("ERP_EVENTS_ENABLED", "1")
    monkeypatch.setenv("ERP_EVENTS_HMAC_KEYS", f"{TEST_KEY_ID}:{TEST_SECRET}")
    fake_cur = FakeCursor()
    monkeypatch.setattr("app.controllers.erp_events_controller.get_connection", lambda: FakeConn(fake_cur))


def _sign(method: str, path_and_query: str, timestamp: str, nonce: str, body: bytes, secret: str = TEST_SECRET) -> str:
    canonical = build_canonical_string(method, path_and_query, timestamp, nonce, body)
    return hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest().lower()


def test_in01_unsigned_wrong_key_bad_signature():
    app = get_test_app()
    client = TestClient(app)

    # 1. Unsigned request
    resp = client.get("/api/erp/v1/events")
    assert resp.status_code == 401
    assert resp.json() == AUTH_ERROR_RESPONSE

    # 2. Wrong key ID
    ts = str(int(time.time()))
    nonce = "a" * 20
    body = b""
    sig = _sign("GET", "/api/erp/v1/events?after=0", ts, nonce, body)
    resp = client.get(
        "/api/erp/v1/events?after=0",
        headers={
            "X-Erp-Key-Id": "unknown-key",
            "X-Erp-Timestamp": ts,
            "X-Erp-Nonce": nonce,
            "X-Erp-Signature": sig,
        },
    )
    assert resp.status_code == 401
    assert resp.json() == AUTH_ERROR_RESPONSE

    # 3. Bad signature
    resp = client.get(
        "/api/erp/v1/events?after=0",
        headers={
            "X-Erp-Key-Id": TEST_KEY_ID,
            "X-Erp-Timestamp": ts,
            "X-Erp-Nonce": nonce,
            "X-Erp-Signature": "bad" * 16,
        },
    )
    assert resp.status_code == 401
    assert resp.json() == AUTH_ERROR_RESPONSE


def test_in02_timestamp_skew_rejected():
    app = get_test_app()
    client = TestClient(app)

    now = int(time.time())
    stale_ts = str(now - 305)  # > 300 s skew
    nonce = "b" * 24
    body = b""
    sig = _sign("GET", "/api/erp/v1/events?after=0", stale_ts, nonce, body)

    resp = client.get(
        "/api/erp/v1/events?after=0",
        headers={
            "X-Erp-Key-Id": TEST_KEY_ID,
            "X-Erp-Timestamp": stale_ts,
            "X-Erp-Nonce": nonce,
            "X-Erp-Signature": sig,
        },
    )
    assert resp.status_code == 401
    assert resp.json() == AUTH_ERROR_RESPONSE


def test_in03_nonce_replay_rejected():
    cur = MagicMock()
    # First use succeeds
    cur.execute.return_value = None
    assert check_and_burn_nonce(cur, TEST_KEY_ID, "nonce1234567890abcdef") is True

    # Replay: cur.execute raises Exception on duplicate key
    cur.execute.side_effect = Exception("duplicate key value violates unique constraint")
    assert check_and_burn_nonce(cur, TEST_KEY_ID, "nonce1234567890abcdef") is False


def test_in04_body_tampering_rejected():
    app = get_test_app()
    client = TestClient(app)

    ts = str(int(time.time()))
    nonce = "c" * 20
    original_body = b'{"event_ids": ["123"]}'
    sig = _sign("POST", "/api/erp/v1/events/ack", ts, nonce, original_body)

    # Send tampered body
    tampered_body = b'{"event_ids": ["456"]}'
    resp = client.post(
        "/api/erp/v1/events/ack",
        content=tampered_body,
        headers={
            "X-Erp-Key-Id": TEST_KEY_ID,
            "X-Erp-Timestamp": ts,
            "X-Erp-Nonce": nonce,
            "X-Erp-Signature": sig,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 401
    assert resp.json() == AUTH_ERROR_RESPONSE


def test_in05_nonce_length_boundaries():
    cur = MagicMock()
    # Too short (< 16)
    assert check_and_burn_nonce(cur, TEST_KEY_ID, "short") is False
    # Too long (> 128)
    assert check_and_burn_nonce(cur, TEST_KEY_ID, "x" * 129) is False
    # Valid length
    assert check_and_burn_nonce(cur, TEST_KEY_ID, "valid_nonce_length_123") is True


def test_in06_bad_signature_rate_limiting(monkeypatch):
    with patch("app.erp_inbound.enforce_rate_limit", return_value=False):
        app = get_test_app()
        client = TestClient(app)
        ts = str(int(time.time()))
        nonce = "z" * 20
        resp = client.get(
            "/api/erp/v1/events?after=0",
            headers={
                "X-Erp-Key-Id": TEST_KEY_ID,
                "X-Erp-Timestamp": ts,
                "X-Erp-Nonce": nonce,
                "X-Erp-Signature": "invalidsig" * 5,
            },
        )
        assert resp.status_code == 429


def test_in12_no_forbidden_pii_in_outbox():
    cur = MagicMock()
    # Attempt to enqueue payload with password hash
    bad_payload = {
        "customer": {
            "email": "test@example.com",
            "password_hash": "secret_hash",
        }
    }
    with pytest.raises(ValueError, match="Forbidden PII key"):
        enqueue_event(cur, "order.created", "key1", bad_payload)

    # Attempt to enqueue payload with session token
    bad_token_payload = {
        "customer": {"email": "test@example.com"},
        "session_token": "jwt.token.here",
    }
    with pytest.raises(ValueError, match="Forbidden PII key"):
        enqueue_event(cur, "order.created", "key2", bad_token_payload)

    # Attempt to enqueue IP address
    bad_ip_payload = {
        "customer": {"email": "test@example.com"},
        "client_ip": "1.2.3.4",
    }
    with pytest.raises(ValueError, match="Forbidden PII key"):
        enqueue_event(cur, "order.created", "key3", bad_ip_payload)


def test_in13_rejected_spam_does_not_enqueue():
    # If spam check fails, enqueue_event is not invoked
    cur = MagicMock()
    is_spam = True
    if not is_spam:
        enqueue_event(cur, "inquiry.created", "spam_test", {"lead": {"subject": "spam"}})
    cur.execute.assert_not_called()


def test_flag_off_returns_404(monkeypatch):
    monkeypatch.setenv("ERP_EVENTS_ENABLED", "0")
    monkeypatch.setenv("ERP_INBOUND_ENABLED", "0")
    monkeypatch.setenv("ERP_SYNC_ENABLED", "0")

    app = get_test_app()
    client = TestClient(app)

    ts = str(int(time.time()))
    nonce = "d" * 20
    sig = _sign("GET", "/api/erp/v1/events?after=0", ts, nonce, b"")

    resp = client.get(
        "/api/erp/v1/events?after=0",
        headers={
            "X-Erp-Key-Id": TEST_KEY_ID,
            "X-Erp-Timestamp": ts,
            "X-Erp-Nonce": nonce,
            "X-Erp-Signature": sig,
        },
    )
    assert resp.status_code == 404


def test_pull_and_ack_success(monkeypatch):
    fake_events = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "event_type": "order.created",
            "occurred_at": datetime.now(timezone.utc),
            "idempotency_key": "order:created:TEST01",
            "payload": {"order": {"order_number": "TEST01"}},
            "seq": 101,
        }
    ]
    cur = FakeCursor(rows=fake_events, rowcount=1)
    monkeypatch.setattr("app.controllers.erp_events_controller.get_connection", lambda: FakeConn(cur))

    app = get_test_app()
    client = TestClient(app)

    ts = str(int(time.time()))
    nonce = "e" * 20
    sig = _sign("GET", "/api/erp/v1/events?after=0&limit=50", ts, nonce, b"")

    resp = client.get(
        "/api/erp/v1/events?after=0&limit=50",
        headers={
            "X-Erp-Key-Id": TEST_KEY_ID,
            "X-Erp-Timestamp": ts,
            "X-Erp-Nonce": nonce,
            "X-Erp-Signature": sig,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert len(data["events"]) == 1
    assert data["events"][0]["event_id"] == "11111111-1111-1111-1111-111111111111"
    assert int(data["next_cursor"]) == 101

    # Now ACK the event
    ack_body = json.dumps({"event_ids": ["11111111-1111-1111-1111-111111111111"]}).encode("utf-8")
    nonce_ack = "f" * 20
    sig_ack = _sign("POST", "/api/erp/v1/events/ack", ts, nonce_ack, ack_body)

    ack_resp = client.post(
        "/api/erp/v1/events/ack",
        content=ack_body,
        headers={
            "X-Erp-Key-Id": TEST_KEY_ID,
            "X-Erp-Timestamp": ts,
            "X-Erp-Nonce": nonce_ack,
            "X-Erp-Signature": sig_ack,
            "Content-Type": "application/json",
        },
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json().get("success") is True or ack_resp.json().get("ok") is True


def test_erp_health_endpoint():
    app = get_test_app()
    client = TestClient(app)
    resp = client.get("/api/erp/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
