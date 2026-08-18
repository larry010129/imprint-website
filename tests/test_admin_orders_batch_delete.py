"""Admin /admin/orders toolbar — batch delete is admin-only FE wiring."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH_DELETE = "/api/admin/orders/batch-delete"


def test_admin_orders_toolbar_has_delete_when_rows_selected():
    for name in ("admin.html", "admin1.html"):
        html = (ROOT / name).read_text(encoding="utf-8")
        assert 'id="ordersBulkBar"' in html
        assert 'id="ordersBulkDelete"' in html
        assert ">刪除</button>" in html
        assert "admin-orders.js?v=26" in html
        assert "api-client.js?v=27" in html


def test_admin_orders_js_confirms_then_posts_batch_delete():
    src = (ROOT / "public" / "js" / "admin-orders.js").read_text(encoding="utf-8")
    assert "ordersBulkDelete" in src
    assert "batchDeleteOrders" in src
    assert "確定刪除" in src
    assert "confirm(" in src
    assert "此操作無法復原" in src


def test_api_client_batch_delete_uses_admin_session_post():
    src = (ROOT / "public" / "js" / "api-client.js").read_text(encoding="utf-8")
    assert "batchDeleteOrders" in src
    assert BATCH_DELETE in src
    # Existing cancel alias must not be reused as hard-delete.
    assert "function (id, reason)" in src
    assert "this.cancelOrder" in src


def test_customer_history_has_no_admin_batch_delete():
    history_paths = [
        ROOT / "content/site/templates/pages/history.html",
        ROOT / "content/site/templates/partials/htmx/history_order_rows.html",
        ROOT / "content/site/templates/partials/htmx/history_list.html",
        ROOT / "public/js/mvc/controllers/history-controller.js",
    ]
    for path in history_paths:
        text = path.read_text(encoding="utf-8")
        assert "ordersBulkDelete" not in text
        assert BATCH_DELETE not in text
        assert "batchDeleteOrders" not in text
