"""Admin /admin/orders toolbar — Rex bulk-delete wiring + history tabs."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BULK_DELETE = "/api/admin/orders-bulk-delete"
CANCEL_DELETE = "/api/admin/order-delete"
HISTORY_TABS = ("all", "unpaid", "to_ship", "to_receive", "completed", "cancelled")
HISTORY_LABELS = ("全部", "待付款", "待出貨", "待收貨", "已完成", "不成立")


def test_admin_orders_toolbar_delete_disabled_until_checked():
    for name in ("admin.html", "admin1.html"):
        html = (ROOT / name).read_text(encoding="utf-8")
        assert 'id="ordersBulkBar"' in html
        assert 'id="ordersBulkDelete"' in html
        assert 'id="ordersBulkDelete" disabled' in html
        assert ">刪除</button>" in html
        assert "admin-orders.js?v=27" in html
        assert "api-client.js?v=32" in html


def test_admin_orders_has_history_status_tabs():
    for name in ("admin.html", "admin1.html"):
        html = (ROOT / name).read_text(encoding="utf-8")
        assert 'id="ordersTabs"' in html
        assert 'aria-label="訂單分類"' in html
        for key, label in zip(HISTORY_TABS, HISTORY_LABELS):
            assert 'data-orders-tab="' + key + '"' in html
            assert label in html


def test_admin_orders_js_confirms_then_posts_rex_bulk_delete():
    src = (ROOT / "public" / "js" / "admin-orders.js").read_text(encoding="utf-8")
    assert "ordersBulkDelete" in src
    assert "bulkDeleteOrders" in src
    assert "BULK_DELETE_CAP = 100" in src
    assert "確定刪除" in src
    assert "confirm(" in src
    assert "此操作無法復原" in src
    assert "bulkDelete.disabled = n === 0" in src
    assert "deleteOrder" not in src
    assert CANCEL_DELETE not in src
    assert "/api/admin/orders/batch-delete" not in src
    for key in HISTORY_TABS:
        if key == "all":
            continue
        assert key in src


def test_api_client_bulk_delete_rex_lock():
    src = (ROOT / "public" / "js" / "api-client.js").read_text(encoding="utf-8")
    assert "bulkDeleteOrders" in src
    assert BULK_DELETE in src
    assert "confirm: true" in src
    assert "Path is FINAL" in src
    block = src.split("bulkDeleteOrders")[1].split("getProducts")[0]
    assert "PLACEHOLDER" not in block
    assert "confirm: true" in block
    assert "ids.slice(0, 100)" in src
    assert "missing ids" in src
    # Cancel alias must stay unused by bulk delete.
    assert "function (id, reason)" in src
    assert "this.cancelOrder" in src
    assert src.index("bulkDeleteOrders") > src.index("deleteOrder")
    assert CANCEL_DELETE not in src.split("bulkDeleteOrders")[1].split("getProducts")[0]


def test_customer_history_has_no_admin_bulk_delete():
    history_paths = [
        ROOT / "content/site/templates/pages/history.html",
        ROOT / "content/site/templates/partials/htmx/history_order_rows.html",
        ROOT / "content/site/templates/partials/htmx/history_list.html",
        ROOT / "public/js/mvc/controllers/history-controller.js",
    ]
    for path in history_paths:
        text = path.read_text(encoding="utf-8")
        assert "ordersBulkDelete" not in text
        assert BULK_DELETE not in text
        assert "bulkDeleteOrders" not in text
        assert "data-orders-tab" not in text
