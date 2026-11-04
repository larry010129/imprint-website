"""Tests for GET /api/admin/notify-summary and X-Admin-Background sliding skip."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from unittest.mock import MagicMock

# Ensure repo root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi import Request
from fastapi.responses import Response

import app.controllers.admin_controller as ac
from app.auth import SessionClaims, session_needs_slide


class _FakeCursor:
    def __init__(self, fetchone_val=None, fetchall_val=None, execute_fn=None):
        self.fetchone_val = fetchone_val
        self.fetchall_val = fetchall_val or []
        self.execute_fn = execute_fn
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))
        if self.execute_fn:
            res = self.execute_fn(sql, params)
            if res is not None:
                if isinstance(res, dict):
                    self.fetchone_val = res
                elif isinstance(res, list):
                    self.fetchall_val = res

    def fetchone(self):
        return self.fetchone_val

    def fetchall(self):
        return self.fetchall_val

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeConn:
    def __init__(self, cur):
        self._cur = cur

    def cursor(self):
        return self._cur

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_notify_summary_requires_admin(monkeypatch):
    """Admin-only: raises HTTPException(401) or 403 when _require_admin rejects."""
    called = []

    def _mock_require(req):
        called.append(req)
        raise ac.HTTPException(status_code=401, detail="not signed in")

    monkeypatch.setattr(ac, "_require_admin", _mock_require)

    req = MagicMock(spec=Request)
    with pytest.raises(ac.HTTPException) as exc_info:
        ac.notify_summary_get(req)
    assert exc_info.value.status_code == 401
    assert len(called) == 1


def test_notify_summary_counts_and_pending_filtering(monkeypatch):
    """Pending counts and pending-only item rows match the contract."""
    monkeypatch.setattr(ac, "_require_admin", lambda req: "admin-uuid-1")

    counts_row = {
        "pending_messages": 3,
        "pending_quotes": 5,
        "pending_orders": 2,
    }

    msgs = [
        {"id": "msg-1", "name": "Alice", "created_at": datetime(2026, 11, 4, 10, 0, 0, tzinfo=timezone.utc)},
    ]
    quotes = [
        {"id": "quote-1", "name": "Bob", "created_at": datetime(2026, 11, 4, 11, 0, 0, tzinfo=timezone.utc)},
    ]
    orders = [
        {"id": "ord-1", "order_number": "ORD-101", "customer_name": "Carol", "created_at": datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc)},
    ]

    def _exec(sql, params):
        s = sql.lower()
        if "from contact_messages" in s and "order by created_at desc" in s:
            return msgs
        if "from quote_requests" in s and "order by created_at desc" in s:
            return quotes
        if "from orders o" in s and "order by o.created_at desc" in s:
            return orders
        if "select count(*)::int" in s or "as pending_messages" in s:
            return counts_row
        return None

    cur = _FakeCursor(execute_fn=_exec)
    monkeypatch.setattr(ac, "get_connection", lambda: _FakeConn(cur))

    req = MagicMock(spec=Request)
    res = ac.notify_summary_get(req)

    assert "counts" in res
    assert res["counts"]["messages"] == 3
    assert res["counts"]["quotes"] == 5
    assert res["counts"]["orders"] == 2
    assert res["counts"]["total"] == 10

    assert len(res["items"]) == 3
    # Newest first: ord-1 (12:00) > quote-1 (11:00) > msg-1 (10:00)
    assert res["items"][0]["type"] == "order"
    assert res["items"][0]["id"] == "ord-1"
    assert res["items"][0]["order_number"] == "ORD-101"
    assert res["items"][0]["name"] == "Carol"

    assert res["items"][1]["type"] == "quote"
    assert res["items"][1]["id"] == "quote-1"
    assert res["items"][1]["order_number"] is None
    assert res["items"][1]["name"] == "Bob"

    assert res["items"][2]["type"] == "message"
    assert res["items"][2]["id"] == "msg-1"
    assert res["items"][2]["order_number"] is None
    assert res["items"][2]["name"] == "Alice"


def test_notify_summary_capped_at_8_items_and_ordered(monkeypatch):
    """Items list is capped at 8 and strictly ordered newest-first across types."""
    monkeypatch.setattr(ac, "_require_admin", lambda req: "admin-uuid-1")

    base_time = datetime(2026, 11, 4, 8, 0, 0, tzinfo=timezone.utc)
    msgs = [
        {"id": f"m{i}", "name": f"Msg{i}", "created_at": base_time + timedelta(hours=i * 3)}
        for i in range(5)
    ]
    quotes = [
        {"id": f"q{i}", "name": f"Quote{i}", "created_at": base_time + timedelta(hours=i * 3 + 1)}
        for i in range(5)
    ]
    orders = [
        {"id": f"o{i}", "order_number": f"ORD-{i}", "customer_name": f"Ord{i}", "created_at": base_time + timedelta(hours=i * 3 + 2)}
        for i in range(5)
    ]

    def _exec(sql, params):
        s = sql.lower()
        if "from contact_messages" in s and "order by created_at desc" in s:
            return msgs
        if "from quote_requests" in s and "order by created_at desc" in s:
            return quotes
        if "from orders o" in s and "order by o.created_at desc" in s:
            return orders
        return {"pending_messages": 5, "pending_quotes": 5, "pending_orders": 5}

    cur = _FakeCursor(execute_fn=_exec)
    monkeypatch.setattr(ac, "get_connection", lambda: _FakeConn(cur))

    req = MagicMock(spec=Request)
    res = ac.notify_summary_get(req)

    assert len(res["items"]) == 8
    times = [item["created_at"] for item in res["items"]]
    assert times == sorted(times, reverse=True)
    assert res["items"][0]["id"] == "o4"
    assert res["items"][0]["type"] == "order"


def test_notify_summary_has_no_pii_fields(monkeypatch):
    """Items contain type, id, order_number, name, created_at ONLY (no phones, emails, message content)."""
    monkeypatch.setattr(ac, "_require_admin", lambda req: "admin-uuid-1")

    msgs = [{"id": "m1", "name": "Secret Guy", "created_at": datetime.now(timezone.utc)}]
    quotes = [{"id": "q1", "name": "Quote Guy", "created_at": datetime.now(timezone.utc)}]
    orders = [{"id": "o1", "order_number": "ORD-1", "customer_name": "Order Guy", "created_at": datetime.now(timezone.utc)}]

    def _exec(sql, params):
        s = sql.lower()
        if "from contact_messages" in s and "order by created_at desc" in s:
            return msgs
        if "from quote_requests" in s and "order by created_at desc" in s:
            return quotes
        if "from orders o" in s and "order by o.created_at desc" in s:
            return orders
        return {"pending_messages": 1, "pending_quotes": 1, "pending_orders": 1}

    cur = _FakeCursor(execute_fn=_exec)
    monkeypatch.setattr(ac, "get_connection", lambda: _FakeConn(cur))

    req = MagicMock(spec=Request)
    res = ac.notify_summary_get(req)

    allowed_keys = {"type", "id", "order_number", "name", "created_at"}
    for item in res["items"]:
        keys = set(item.keys())
        assert keys == allowed_keys, f"Extra or missing keys in item: {keys}"
        assert "phone" not in keys
        assert "email" not in keys
        assert "message" not in keys
        assert "content" not in keys
        assert "body" not in keys


def test_no_token_reissue_when_background_header_set():
    """When X-Admin-Background: 1 is present, session_needs_slide returns False."""
    now = datetime.now(timezone.utc)
    # ADMIN_IDLE_MINUTES is 720 (12 hours). Idle/2 is 6 hours (360 mins).
    # Setting elapsed to 7 hours (> 6 hours) triggers sliding.
    claims = SessionClaims(
        user_id="admin-1",
        token_version=1,
        iat=now - timedelta(hours=7),
        exp=now + timedelta(hours=14),
        role="admin",
        remember=False,
    )

    # 1. Normal request -> needs slide
    normal_req = MagicMock(spec=Request)
    normal_req.headers = {}
    assert session_needs_slide(claims, request=normal_req) is True

    # None request -> backward compatible fallback
    assert session_needs_slide(claims, request=None) is True
    assert session_needs_slide(claims) is True

    # 2. Background header request -> skips slide
    bg_req = MagicMock(spec=Request)
    bg_req.headers = {"x-admin-background": "1"}
    assert session_needs_slide(claims, request=bg_req) is False

    # Header with different value -> still slides
    other_req = MagicMock(spec=Request)
    other_req.headers = {"x-admin-background": "0"}
    assert session_needs_slide(claims, request=other_req) is True
