"""Admin 諮詢名單 — per-row hard delete wiring (contact_messages / quote_requests)."""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock

import app.controllers.admin_controller as ac

ROOT = Path(__file__).resolve().parents[1]
LEADS_DELETE = "/api/admin/leads-delete"
GOOD_ID = "3f6c1d2e-8a4b-4c7d-9e10-2b5a6c7d8e9f"


class _Cur:
    """Records every SQL statement so the test can assert which table was hit."""

    def __init__(self):
        self.sql = []
        self.rowcount = 1

    def execute(self, sql, params=None):
        self.sql.append((" ".join(sql.split()), params))

    def fetchone(self):
        return {"email": "admin@example.com"}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Conn:
    def __init__(self, cur):
        self._cur = cur

    def cursor(self):
        return self._cur

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _call(monkeypatch, body, cur=None):
    cur = cur or _Cur()
    monkeypatch.setattr(ac, "_require_admin", lambda _req: "admin-1")
    monkeypatch.setattr(ac, "get_transaction", lambda: _Conn(cur))
    monkeypatch.setattr(ac, "log_admin_action", lambda *a, **k: None)
    req = MagicMock()

    async def _json():
        return body

    req.json = _json
    resp = asyncio.run(ac.leads_delete(req))
    return resp, cur


def test_delete_message_targets_contact_messages(monkeypatch):
    resp, cur = _call(monkeypatch, {"type": "message", "id": GOOD_ID})
    assert resp.status_code == 200
    assert json.loads(bytes(resp.body)) == {"ok": True, "deleted": 1}
    delete_sql, params = cur.sql[0]
    assert delete_sql == "delete from contact_messages where id = %s"
    assert params == (GOOD_ID,)


def test_delete_quote_targets_quote_requests(monkeypatch):
    _resp, cur = _call(monkeypatch, {"type": "quote", "id": GOOD_ID})
    delete_sql, _params = cur.sql[0]
    assert delete_sql == "delete from quote_requests where id = %s"


def test_bad_type_is_rejected_without_touching_db(monkeypatch):
    for bad in ("orders", "", None, "users; drop table orders"):
        resp, cur = _call(monkeypatch, {"type": bad, "id": GOOD_ID})
        assert resp.status_code == 400
        assert cur.sql == []


def test_non_uuid_id_is_400_not_500(monkeypatch):
    for bad in ("1 or 1=1", "", None, "not-a-uuid"):
        resp, cur = _call(monkeypatch, {"type": "message", "id": bad})
        assert resp.status_code == 400
        assert cur.sql == []


def test_missing_row_reports_zero_deleted(monkeypatch):
    cur = _Cur()
    cur.rowcount = 0
    resp, _cur = _call(monkeypatch, {"type": "message", "id": GOOD_ID}, cur=cur)
    assert json.loads(bytes(resp.body)) == {"ok": True, "deleted": 0}


def test_backend_endpoint_validates_type_and_uuid():
    src = (ROOT / "app" / "controllers" / "admin_controller.py").read_text(encoding="utf-8")
    block = src.split('@router.post("/leads-delete")')[1].split("def _admin_orders_search_from")[0]
    # Admin gate + audit trail on an irreversible action.
    assert "_require_admin(request)" in block
    assert 'log_admin_action(' in block
    assert '"lead_delete"' in block
    # Table name must come from the validated enum, never from the body.
    assert 'lead_type not in ("message", "quote")' in block
    assert 'table = "contact_messages" if lead_type == "message" else "quote_requests"' in block
    assert 'body.get("table")' not in block
    # Reject non-UUID ids with 400 instead of letting psycopg raise a 500.
    assert "uuid.UUID(" in block
    assert '"invalid lead id"' in block


def test_api_client_exposes_delete_lead():
    src = (ROOT / "public" / "js" / "api-client.js").read_text(encoding="utf-8")
    assert "deleteLead" in src
    assert LEADS_DELETE in src
    # Must not collide with the mark-done POST on /api/admin/leads.
    block = src.split("deleteLead")[1].split("getOrders")[0]
    assert "'/api/admin/leads'" not in block


def test_admin_js_confirms_before_deleting_lead():
    src = (ROOT / "public" / "js" / "admin.js").read_text(encoding="utf-8")
    assert "data-lead-delete" in src
    assert "deleteLead" in src
    assert "confirm(" in src
    assert "此操作無法復原" in src
    # Refresh both the list and the dashboard counter after a delete.
    assert "loadLeads(true, true)" in src
    assert "loadDashboardStats()" in src


def test_admin_pages_ship_bumped_assets():
    for name in ("admin.html", "admin1.html"):
        html = (ROOT / name).read_text(encoding="utf-8")
        assert "api-client.js?v=32" in html
        assert 'data-panel="leads"' in html or "諮詢名單" in html
