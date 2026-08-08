"""Member confirm-receipt → completed + history completed tab filter."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")


class _Cur:
    def __init__(self, *, fetchone_item=None, fetchall_rows=None, rowcount=1):
        self.item = fetchone_item
        self.rows = fetchall_rows or []
        self.rowcount = rowcount
        self.executed: list[tuple] = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.item

    def fetchall(self):
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


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def _sample_orders():
    return [
        {
            "id": "o1",
            "status": "shipped",
            "fulfillment_method": "pickup",
            "summary_zh": "A",
            "config_json": {},
            "total_price": 100,
        },
        {
            "id": "o2",
            "status": "completed",
            "fulfillment_method": "delivery",
            "summary_zh": "B",
            "config_json": {},
            "total_price": 200,
        },
        {
            "id": "o3",
            "status": "in_production",
            "fulfillment_method": "pickup",
            "summary_zh": "C",
            "config_json": {},
            "total_price": 300,
        },
        {
            "id": "o4",
            "status": "received",
            "fulfillment_method": "delivery",
            "summary_zh": "D",
            "config_json": {},
            "total_price": 400,
        },
        {
            "id": "o5",
            "status": "order_confirming",
            "fulfillment_method": "delivery",
            "summary_zh": "E",
            "config_json": {},
            "total_price": 500,
        },
        {
            "id": "o6",
            "status": "deposit_confirmed",
            "fulfillment_method": "delivery",
            "summary_zh": "F",
            "config_json": {},
            "total_price": 600,
        },
        {
            "id": "o7",
            "status": "cancelled",
            "fulfillment_method": "delivery",
            "summary_zh": "G",
            "config_json": {},
            "total_price": 700,
        },
        {
            "id": "o8",
            "status": "canceled",
            "fulfillment_method": "pickup",
            "summary_zh": "H",
            "config_json": {},
            "total_price": 800,
        },
        {
            "id": "o9",
            "status": "shipped",
            "fulfillment_method": "delivery",
            "summary_zh": "I",
            "config_json": {},
            "total_price": 900,
        },
    ]


def test_history_tab_status_map():
    from app.controllers import htmx_member as hm

    assert hm.HISTORY_TAB_STATUSES["unpaid"] == frozenset(
        {"received", "order_confirming"}
    )
    assert hm.HISTORY_TAB_STATUSES["to_ship"] == frozenset(
        {"deposit_confirmed", "dna_lab", "in_production", "quality_check"}
    )
    assert hm.HISTORY_TAB_STATUSES["to_receive"] == frozenset({"shipped"})
    assert hm.HISTORY_TAB_STATUSES["completed"] == frozenset({"completed"})
    assert hm.HISTORY_TAB_STATUSES["cancelled"] == frozenset(
        {"cancelled", "canceled"}
    )
    assert "return" not in hm.HISTORY_TAB_STATUSES


def test_history_list_context_filters_shopee_tabs(monkeypatch):
    from app.controllers import htmx_member as hm

    orders = _sample_orders()
    cur = _Cur(fetchall_rows=orders)
    monkeypatch.setattr(hm, "get_connection", lambda: _ConnOuter(cur))
    monkeypatch.setattr("app.orders.attach_order_display", lambda _cur, rows: None)

    ctx = hm._history_list_context("user-1")
    assert [o["id"] for o in ctx["unpaid_orders"]] == ["o4", "o5"]
    assert [o["id"] for o in ctx["to_ship_orders"]] == ["o3", "o6"]
    assert [o["id"] for o in ctx["to_receive_orders"]] == ["o1", "o9"]
    assert [o["id"] for o in ctx["completed_orders"]] == ["o2"]
    assert [o["id"] for o in ctx["cancelled_orders"]] == ["o7", "o8"]
    assert "return_orders" not in ctx
    assert ctx["guest"] is False
    assert len(ctx["orders"]) == 9


def test_history_tab_labels_in_template():
    root = Path(__file__).resolve().parents[1]
    html = (
        root
        / "content"
        / "site"
        / "templates"
        / "partials"
        / "htmx"
        / "history_list.html"
    ).read_text(encoding="utf-8")
    for label in (
        "全部",
        "待付款",
        "待出貨",
        "待收貨",
        "已完成",
        "不成立",
    ):
        assert label in html
    assert "退貨/退款" not in html
    assert "history_tab_return" not in html
    assert "history_tab_to_receive" in html
    assert "可取貨商品" not in html
    assert "全部訂單" not in html


def test_confirm_receipt_owner_shipped_delivery_completes(client, monkeypatch):
    from app.controllers import htmx_member as hm

    select_cur = _Cur(
        fetchone_item={
            "id": "ord-1",
            "status": "shipped",
            "fulfillment_method": "delivery",
            "status_timestamps": {"shipped": "2026-08-01T00:00:00+00:00"},
        },
        rowcount=1,
    )

    completed_order = {
        "id": "ord-1",
        "order_number": "IM-1001",
        "status": "completed",
        "status_label": "已完成",
        "fulfillment_method": "delivery",
        "summary_zh": "測試項鍊",
        "display_name": "測試項鍊",
        "total_price": 12000,
        "created_at_display": "2026/08/01",
        "status_steps": [
            {"code": "received", "label": "已收到申請", "state": "complete", "color": "#e0a458", "date": "8/1"},
            {"code": "shipped", "label": "已出貨", "state": "complete", "color": "#9b7fd4", "date": "8/1"},
            {"code": "completed", "label": "已完成", "state": "current", "color": "#4caf7d", "date": "8/9"},
        ],
        "status_cancelled": False,
        "ready_for_pickup": False,
    }

    def fake_history(_user_id):
        return {
            "orders": [completed_order],
            "unpaid_orders": [],
            "to_ship_orders": [],
            "to_receive_orders": [],
            "completed_orders": [completed_order],
            "cancelled_orders": [],
            "guest": False,
        }

    monkeypatch.setattr(hm, "get_user_id", lambda _req: "user-owner")
    monkeypatch.setattr(hm, "enforce_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr(hm, "get_connection", lambda: _ConnOuter(select_cur))
    monkeypatch.setattr(hm, "_history_list_context", fake_history)

    resp = client.post(
        "/htmx/history/confirm-receipt",
        data={"order_id": "ord-1"},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "已確認收到商品，訂單已完成" in body
    assert "全部" in body
    assert "已完成" in body
    assert 'id="history-tab-all"' in body
    assert 'id="history-tab-completed"' in body
    assert 'id="history-tab-to_receive"' in body
    # Success lands on 已完成 tab.
    assert 'data-tab="completed"' in body
    assert (
        'class="member-tab is-active" role="tab"\n    aria-selected="true"\n    data-tab="completed"'
        in body
        or (
            'data-tab="completed" id="history-tab-completed"' in body
            and 'aria-selected="true"' in body
        )
    )
    assert "history-completed-detail-ord-1" in body or "history-detail-ord-1" in body
    assert "order-confirm-receipt" not in body
    assert (
        'data-tab-panel="completed" role="tabpanel" aria-labelledby="history-tab-completed"'
        in body
    )
    assert (
        'data-tab-panel="completed" role="tabpanel" aria-labelledby="history-tab-completed" hidden'
        not in body
    )
    update_sqls = [sql for sql, _ in select_cur.executed if "update orders" in sql.lower()]
    assert update_sqls
    assert "completed" in update_sqls[0].lower()
    assert any(
        params and params[0] is not None
        for sql, params in select_cur.executed
        if params and "update orders" in sql.lower()
    )


def test_confirm_receipt_rejects_wrong_owner(client, monkeypatch):
    from app.controllers import htmx_member as hm

    select_cur = _Cur(fetchone_item=None)

    monkeypatch.setattr(hm, "get_user_id", lambda _req: "user-a")
    monkeypatch.setattr(hm, "enforce_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr(hm, "get_connection", lambda: _ConnOuter(select_cur))
    monkeypatch.setattr(
        hm,
        "_history_list_context",
        lambda _uid: hm._empty_history_context(guest=False),
    )

    resp = client.post(
        "/htmx/history/confirm-receipt",
        data={"order_id": "someone-elses"},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 404
    assert "找不到訂單" in resp.text
    assert not any("update orders" in sql.lower() for sql, _ in select_cur.executed)


def test_confirm_receipt_rejects_non_shipped(client, monkeypatch):
    from app.controllers import htmx_member as hm

    select_cur = _Cur(
        fetchone_item={
            "id": "ord-2",
            "status": "quality_check",
            "fulfillment_method": "delivery",
            "status_timestamps": {},
        }
    )

    monkeypatch.setattr(hm, "get_user_id", lambda _req: "user-owner")
    monkeypatch.setattr(hm, "enforce_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr(hm, "get_connection", lambda: _ConnOuter(select_cur))
    monkeypatch.setattr(
        hm,
        "_history_list_context",
        lambda _uid: hm._empty_history_context(guest=False),
    )

    resp = client.post(
        "/htmx/history/confirm-receipt",
        data={"order_id": "ord-2"},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 400
    assert "無法確認收到商品" in resp.text
    assert not any("update orders" in sql.lower() for sql, _ in select_cur.executed)


def test_confirm_receipt_rejects_pickup_shipped(client, monkeypatch):
    """Pickup (門市自取) must not use confirm-receipt even when shipped."""
    from app.controllers import htmx_member as hm

    select_cur = _Cur(
        fetchone_item={
            "id": "ord-pickup",
            "status": "shipped",
            "fulfillment_method": "pickup",
            "status_timestamps": {"shipped": "2026-08-01T00:00:00+00:00"},
        }
    )

    monkeypatch.setattr(hm, "get_user_id", lambda _req: "user-owner")
    monkeypatch.setattr(hm, "enforce_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr(hm, "get_connection", lambda: _ConnOuter(select_cur))
    monkeypatch.setattr(
        hm,
        "_history_list_context",
        lambda _uid: hm._empty_history_context(guest=False),
    )

    resp = client.post(
        "/htmx/history/confirm-receipt",
        data={"order_id": "ord-pickup"},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 400
    assert "無法確認收到商品" in resp.text
    assert not any("update orders" in sql.lower() for sql, _ in select_cur.executed)


def test_confirm_receipt_guest_unauthorized(client, monkeypatch):
    from app.controllers import htmx_member as hm

    monkeypatch.setattr(hm, "get_user_id", lambda _req: None)
    resp = client.post(
        "/htmx/history/confirm-receipt",
        data={"order_id": "ord-1"},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 401
