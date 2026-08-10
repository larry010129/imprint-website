"""Member order cancel — preset dropdown fills textarea; gate before deposit_confirmed."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")

WRONG = "\u4e0b\u932f\u8a02\u55ae"  # 下錯訂單
OTHER = "\u5176\u4ed6"  # 其他
BLOCK_MSG = "\u8a02\u91d1\u5df2\u78ba\u8a8d\u5f8c\u7121\u6cd5\u53d6\u6d88"  # 訂金已確認後無法取消
CANCELLED_MSG = "\u8a02\u55ae\u5df2\u53d6\u6d88"  # 訂單已取消
REASON_MSG = "\u53d6\u6d88\u539f\u56e0"  # 取消原因
CHANGE_ITEM = (
    "\u60f3\u66f4\u6539\u5546\u54c1\uff08\u9700\u91cd\u65b0\u4e0b\u55ae\uff09"
)  # 想更改商品（需重新下單）
EDIT_ORDER = "\u4fee\u6539\u8a02\u55ae"  # 修改訂單


class _Cur:
    def __init__(self, *, fetchone_item=None, fetchall_rows=None, rowcount=1):
        self.item = fetchone_item
        self.rows = list(fetchall_rows or [])
        self.rowcount = rowcount
        self.executed: list[tuple] = []
        self._pending_fetchall = None

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        sql_l = (sql or "").lower()
        if "group by lower(status)" in sql_l:
            self._pending_fetchall = []
            return
        if "count(*)" in sql_l and "from orders" in sql_l:
            self.item = {"n": 0}
            return
        if "from orders" in sql_l and "select *" in sql_l and "where user_id" in sql_l:
            self._pending_fetchall = []
            return

    def fetchone(self):
        return self.item

    def fetchall(self):
        if self._pending_fetchall is not None:
            rows = self._pending_fetchall
            self._pending_fetchall = None
            return rows
        return self.rows


class _CursorCtx:
    def __init__(self, cur: _Cur):
        self.cur = cur

    def __enter__(self):
        return self.cur

    def __exit__(self, *a):
        return False


class _Conn:
    def __init__(self, cur: _Cur):
        self._cur = cur

    def cursor(self):
        return _CursorCtx(self._cur)


class _ConnOuter:
    def __init__(self, cur: _Cur):
        self._cur = cur

    def __enter__(self):
        return _Conn(self._cur)

    def __exit__(self, *a):
        return False


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    return TestClient(create_app())


def _fake_history(tab=None):
    return {
        "orders": [],
        "active_tab": tab or "all",
        "all_count": 0,
        "unpaid_count": 0,
        "to_ship_count": 0,
        "to_receive_count": 0,
        "completed_count": 0,
        "cancelled_count": 0,
        "page": 1,
        "page_size": 20,
        "total": 0,
        "has_more": False,
        "guest": False,
    }


def test_can_member_cancel_status_gate():
    from app.orders import (
        MEMBER_CANCELABLE_STATUSES,
        can_member_cancel_order,
        enrich_member_order,
        resolve_member_cancel_reason,
    )

    assert MEMBER_CANCELABLE_STATUSES == frozenset({"received", "order_confirming"})
    assert can_member_cancel_order("received") is True
    assert can_member_cancel_order("order_confirming") is True
    assert can_member_cancel_order("deposit_confirmed") is False
    assert can_member_cancel_order("dna_lab") is False
    assert can_member_cancel_order("cancelled") is False

    early = enrich_member_order({"status": "order_confirming", "config_json": {}})
    late = enrich_member_order({"status": "deposit_confirmed", "config_json": {}})
    assert early["can_cancel"] is True
    assert late["can_cancel"] is False

    assert resolve_member_cancel_reason(WRONG, WRONG) == WRONG
    assert resolve_member_cancel_reason(WRONG, "") is None
    assert resolve_member_cancel_reason(OTHER, " note ") == "note"
    assert resolve_member_cancel_reason(OTHER, "") is None
    assert resolve_member_cancel_reason("not-a-preset", "x") is None


def test_history_cancel_received_ok(client, monkeypatch):
    from app.controllers import htmx_member as hm

    cur = _Cur(
        fetchone_item={
            "id": "ord-1",
            "user_id": "user-1",
            "order_number": "IM-2001",
            "status": "received",
            "summary_zh": "test",
        },
        rowcount=1,
    )
    monkeypatch.setattr(hm, "get_user_id", lambda _req: "user-1")
    monkeypatch.setattr(hm, "enforce_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr(hm, "get_connection", lambda: _ConnOuter(cur))
    monkeypatch.setattr(
        hm,
        "_history_context_from_request",
        lambda *_a, **k: _fake_history(k.get("tab") or "cancelled"),
    )

    resp = client.post(
        "/htmx/history/cancel",
        data={
            "order_id": "ord-1",
            "cancel_preset": WRONG,
            "cancel_reason": WRONG,
        },
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    assert CANCELLED_MSG in resp.text
    params = next(p for sql, p in cur.executed if p and "update orders" in sql.lower())
    assert params[0] == WRONG


def test_history_cancel_order_confirming_ok(client, monkeypatch):
    from app.controllers import htmx_member as hm

    cur = _Cur(
        fetchone_item={
            "id": "ord-2",
            "user_id": "user-1",
            "order_number": "IM-2002",
            "status": "order_confirming",
            "summary_zh": "test",
        },
        rowcount=1,
    )
    monkeypatch.setattr(hm, "get_user_id", lambda _req: "user-1")
    monkeypatch.setattr(hm, "enforce_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr(hm, "get_connection", lambda: _ConnOuter(cur))
    monkeypatch.setattr(
        hm,
        "_history_context_from_request",
        lambda *_a, **k: _fake_history(k.get("tab") or "cancelled"),
    )

    resp = client.post(
        "/htmx/history/cancel",
        data={
            "order_id": "ord-2",
            "cancel_preset": OTHER,
            "cancel_reason": "schedule",
        },
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    assert CANCELLED_MSG in resp.text
    params = next(p for sql, p in cur.executed if p and "update orders" in sql.lower())
    assert params[0] == "schedule"


def test_history_cancel_deposit_confirmed_blocked(client, monkeypatch):
    from app.controllers import htmx_member as hm

    cur = _Cur(
        fetchone_item={
            "id": "ord-3",
            "user_id": "user-1",
            "order_number": "IM-2003",
            "status": "deposit_confirmed",
            "summary_zh": "test",
        },
        rowcount=0,
    )
    monkeypatch.setattr(hm, "get_user_id", lambda _req: "user-1")
    monkeypatch.setattr(hm, "enforce_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr(hm, "get_connection", lambda: _ConnOuter(cur))
    monkeypatch.setattr(
        hm,
        "_history_context_from_request",
        lambda *_a, **k: _fake_history(k.get("tab") or "to_ship"),
    )

    resp = client.post(
        "/htmx/history/cancel",
        data={
            "order_id": "ord-3",
            "cancel_preset": WRONG,
            "cancel_reason": WRONG,
        },
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 400
    assert BLOCK_MSG in resp.text
    assert not any("update orders" in sql.lower() for sql, _ in cur.executed)


def test_history_cancel_requires_reason(client, monkeypatch):
    from app.controllers import htmx_member as hm

    monkeypatch.setattr(hm, "get_user_id", lambda _req: "user-1")
    monkeypatch.setattr(hm, "enforce_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr(
        hm, "_history_context_from_request", lambda *_a, **k: _fake_history()
    )

    resp = client.post(
        "/htmx/history/cancel",
        data={
            "order_id": "ord-1",
            "cancel_preset": OTHER,
            "cancel_reason": "",
        },
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 400
    assert REASON_MSG in resp.text


def test_history_template_has_cancel_controls():
    root = Path(__file__).resolve().parents[1]
    rows = (
        root / "content/site/templates/partials/htmx/history_order_rows.html"
    ).read_text(encoding="utf-8")
    page = (root / "content/site/templates/pages/history.html").read_text(
        encoding="utf-8"
    )
    js = (root / "public/js/order-detail.js").read_text(encoding="utf-8")
    assert "member-order-cancel-btn" in rows
    assert "order.can_cancel" in rows
    assert EDIT_ORDER not in rows
    assert 'href="/shop/calculator/"' in rows
    assert 'id="member-order-cancel-dialog"' in page
    assert 'name="cancel_preset"' in page
    assert 'name="cancel_reason"' in page
    assert "取消原因說明" in page
    assert 'hidden' not in page.split('id="member-cancel-reason"')[1].split("</textarea>")[0]
    assert "password" not in page.lower()
    assert CHANGE_ITEM in page
    assert "applyCancelPreset" in js
    assert "syncCancelNoteVisibility" not in js
