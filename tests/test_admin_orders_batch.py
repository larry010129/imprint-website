"""Admin orders: history-tab list filter + POST /orders-bulk-delete."""

from __future__ import annotations

import inspect
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import HTTPException

from app.controllers import admin_controller as ac
from app.orders import (
    ADMIN_ORDER_BATCH_DELETE_MAX,
    HISTORY_TAB_STATUSES,
    HISTORY_TABS,
    delete_orders_by_ids,
    normalize_history_tab,
    parse_admin_order_ids,
)

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")

ID_A = "11111111-1111-1111-1111-111111111111"
ID_B = "22222222-2222-2222-2222-222222222222"
DELETE_PATH = "/api/admin/orders-bulk-delete"
CANCEL_ALIAS = "/api/admin/order-delete"


class _Cur:
    def __init__(self, *, rows=None, fetchone_item=None, rowcount=0):
        self.rows = list(rows or [])
        self.item = fetchone_item
        self.rowcount = rowcount
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        sql_l = (sql or "").lower()
        if "count(*)" in sql_l:
            self.item = {"n": len(self.rows)}
        if sql_l.strip().startswith("delete from orders"):
            self.rowcount = self._order_delete_count()

    def _order_delete_count(self) -> int:
        return int(self.rowcount)

    def fetchone(self):
        return self.item

    def fetchall(self):
        return list(self.rows)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Conn:
    def __init__(self, cur):
        self._cur = cur

    def cursor(self):
        return self._cur

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _admin_api_client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(ac.router, prefix="/api")
    return TestClient(app)


def _auth_ok(monkeypatch, cur=None):
    monkeypatch.setattr(ac, "_require_admin", lambda _req: "admin-1")
    monkeypatch.setattr(ac, "attach_order_display", lambda *_a, **_k: None)
    monkeypatch.setattr(ac, "log_admin_action", lambda *_a, **_k: None)
    if cur is not None:
        monkeypatch.setattr(ac, "get_connection", lambda: _Conn(cur))
        monkeypatch.setattr(ac, "get_transaction", lambda: _Conn(cur))


def test_history_tabs_shared_with_member_history():
    from app.controllers import htmx_member as hm

    assert hm.HISTORY_TABS == HISTORY_TABS
    assert hm.HISTORY_TAB_STATUSES == HISTORY_TAB_STATUSES
    assert HISTORY_TABS == (
        "all",
        "unpaid",
        "to_ship",
        "to_receive",
        "completed",
        "cancelled",
    )
    assert HISTORY_TAB_STATUSES["unpaid"] == frozenset(
        {"received", "order_confirming"}
    )
    assert HISTORY_TAB_STATUSES["to_ship"] == frozenset(
        {"deposit_confirmed", "dna_lab", "in_production", "quality_check"}
    )
    assert HISTORY_TAB_STATUSES["to_receive"] == frozenset({"shipped"})
    assert HISTORY_TAB_STATUSES["completed"] == frozenset({"completed"})
    assert HISTORY_TAB_STATUSES["cancelled"] == frozenset({"cancelled", "canceled"})
    assert "return" not in HISTORY_TAB_STATUSES
    assert normalize_history_tab("to_receive") == "to_receive"
    assert normalize_history_tab("RETURN") == "all"


def test_batch_cap_is_100():
    assert ADMIN_ORDER_BATCH_DELETE_MAX == 100


def test_parse_admin_order_ids_empty_and_invalid():
    assert parse_admin_order_ids([]) == ([], "empty")
    assert parse_admin_order_ids(None) == ([], "empty")
    assert parse_admin_order_ids("all") == ([], "invalid")
    assert parse_admin_order_ids([1, 2]) == ([], "invalid")
    assert parse_admin_order_ids(["not-a-uuid"]) == ([], "invalid")
    too_many = [str(uuid4()) for _ in range(ADMIN_ORDER_BATCH_DELETE_MAX + 1)]
    assert parse_admin_order_ids(too_many) == ([], "too_many")


def test_parse_admin_order_ids_dedupes_valid_uuids():
    ids, err = parse_admin_order_ids([ID_A, ID_A.upper(), ID_B])
    assert err is None
    assert ids == [ID_A, ID_B]


def test_delete_orders_by_ids_children_then_parent_any():
    cur = _Cur(rowcount=2)
    deleted = delete_orders_by_ids(cur, [ID_A, ID_B])
    assert deleted == 2
    sqls = [sql.lower() for sql, _p in cur.executed]
    assert sqls[0].startswith("delete from coupon_redemptions")
    assert sqls[1].startswith("delete from order_items")
    assert sqls[2].startswith("delete from order_contacts")
    assert sqls[3].startswith("delete from order_fulfillment")
    assert "update user_notifications" in sqls[4]
    assert sqls[5].startswith("delete from orders")
    for sql, params in cur.executed:
        assert " = any(%s)" in sql.lower()
        assert params == ([ID_A, ID_B],)


def test_delete_orders_by_ids_empty_is_noop():
    cur = _Cur()
    assert delete_orders_by_ids(cur, []) == 0
    assert cur.executed == []


def test_order_delete_alias_is_still_cancel():
    src = inspect.getsource(ac.order_delete)
    assert "order_cancel" in src
    assert "orders_bulk_delete" not in src
    assert "delete_orders_by_ids" not in inspect.getsource(ac.order_cancel)


def test_bulk_delete_is_post_only():
    src = (ROOT / "app" / "controllers" / "admin_controller.py").read_text(
        encoding="utf-8"
    )
    assert '@router.post("/orders-bulk-delete")' in src
    assert "@router.api_route(\"/orders/delete\"" not in src
    client = _admin_api_client()
    get_resp = client.get(DELETE_PATH)
    assert get_resp.status_code == 405
    del_resp = client.request("DELETE", DELETE_PATH, json={"ids": [ID_A], "confirm": True})
    assert del_resp.status_code == 405


def test_bulk_delete_requires_admin():
    client = _admin_api_client()
    resp = client.post(DELETE_PATH, json={"ids": [ID_A], "confirm": True})
    assert resp.status_code == 401


def test_bulk_delete_forbids_non_admin(monkeypatch):
    def deny(_req):
        raise HTTPException(status_code=403, detail="admin access required")

    monkeypatch.setattr(ac, "_require_admin", deny)
    client = _admin_api_client()
    resp = client.post(DELETE_PATH, json={"ids": [ID_A], "confirm": True})
    assert resp.status_code == 403


def test_bulk_delete_rejects_without_confirm(monkeypatch):
    opened = {"txn": False}

    def boom():
        opened["txn"] = True
        raise AssertionError("missing confirm must not write")

    monkeypatch.setattr(ac, "_require_admin", lambda _req: "admin-1")
    monkeypatch.setattr(ac, "get_transaction", boom)
    monkeypatch.setattr(ac, "log_admin_action", lambda *_a, **_k: None)
    client = _admin_api_client()
    resp = client.post(DELETE_PATH, json={"ids": [ID_A]})
    assert resp.status_code == 400
    assert resp.json()["error"] == "confirm required"
    assert opened["txn"] is False

    resp_false = client.post(DELETE_PATH, json={"ids": [ID_A], "confirm": False})
    assert resp_false.status_code == 400
    assert resp_false.json()["error"] == "confirm required"
    assert opened["txn"] is False


def test_bulk_delete_empty_list_does_not_write(monkeypatch):
    opened = {"txn": False}

    def boom():
        opened["txn"] = True
        raise AssertionError("empty ids must not open a transaction")

    monkeypatch.setattr(ac, "_require_admin", lambda _req: "admin-1")
    monkeypatch.setattr(ac, "get_transaction", boom)
    monkeypatch.setattr(ac, "log_admin_action", lambda *_a, **_k: None)
    client = _admin_api_client()
    resp = client.post(DELETE_PATH, json={"ids": [], "confirm": True})
    assert resp.status_code == 400
    assert resp.json()["error"] == "missing ids"
    assert opened["txn"] is False


def test_bulk_delete_oversize_rejected(monkeypatch):
    opened = {"txn": False}

    def boom():
        opened["txn"] = True
        raise AssertionError("oversize batch must not write")

    monkeypatch.setattr(ac, "_require_admin", lambda _req: "admin-1")
    monkeypatch.setattr(ac, "get_transaction", boom)
    monkeypatch.setattr(ac, "log_admin_action", lambda *_a, **_k: None)
    client = _admin_api_client()
    ids = [str(uuid4()) for _ in range(ADMIN_ORDER_BATCH_DELETE_MAX + 1)]
    resp = client.post(DELETE_PATH, json={"ids": ids, "confirm": True})
    assert resp.status_code == 400
    assert resp.json()["error"] == "too many ids"
    assert opened["txn"] is False


def test_bulk_delete_only_sent_ids_generic_count(monkeypatch):
    cur = _Cur(rowcount=1, fetchone_item={"email": "admin@example.com"})
    logged = {}

    def capture(email, action, detail=None):
        logged["email"] = email
        logged["action"] = action
        logged["detail"] = detail or {}

    _auth_ok(monkeypatch, cur)
    monkeypatch.setattr(ac, "log_admin_action", capture)
    client = _admin_api_client()
    resp = client.post(
        DELETE_PATH,
        json={"ids": [ID_A, ID_B], "confirm": True, "selectAll": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"ok": True, "deleted": 1}
    assert "missing" not in body
    assert ID_A not in str(body)
    assert ID_B not in str(body)
    delete_orders = [
        (sql, params)
        for sql, params in cur.executed
        if (sql or "").lower().startswith("delete from orders")
    ]
    assert len(delete_orders) == 1
    sql, params = delete_orders[0]
    assert "id = any(%s)" in sql.lower()
    assert params == ([ID_A, ID_B],)
    assert logged["action"] == "orders_bulk_delete"
    assert logged["detail"] == {"deleted": 1, "requested": 2}


def test_orders_list_tab_matches_history_statuses(monkeypatch):
    cur = _Cur(rows=[])
    _auth_ok(monkeypatch, cur)
    client = _admin_api_client()
    resp = client.get("/api/admin/orders", params={"tab": "to_ship"})
    assert resp.status_code == 200
    sqls = " ".join(sql.lower() for sql, _p in cur.executed)
    assert "lower(status) = any" in sqls
    status_lists = [
        params[0]
        for _sql, params in cur.executed
        if params and isinstance(params[0], list)
    ]
    assert status_lists
    assert set(status_lists[0]) == set(HISTORY_TAB_STATUSES["to_ship"])


def test_orders_list_unknown_tab_is_all(monkeypatch):
    cur = _Cur(rows=[])
    _auth_ok(monkeypatch, cur)
    client = _admin_api_client()
    resp = client.get("/api/admin/orders", params={"tab": "return"})
    assert resp.status_code == 200
    sqls = " ".join(sql.lower() for sql, _p in cur.executed)
    assert "lower(status) = any" not in sqls


def test_admin_list_source_reuses_history_tab_helper():
    src = inspect.getsource(ac._admin_tab_statuses) + inspect.getsource(
        ac._fetch_admin_orders
    )
    assert "HISTORY_TAB_STATUSES" in src
    assert "normalize_history_tab" in src


def test_csrf_prefix_covers_admin_bulk_delete():
    src = (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")
    assert '"/api/admin/"' in src
    assert DELETE_PATH.startswith("/api/admin/")
    assert CANCEL_ALIAS.startswith("/api/admin/")
