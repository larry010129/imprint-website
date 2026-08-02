"""Cart lines become unavailable when product unpublished; checkout rejects them."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.responses import JSONResponse

from app.controllers.shop_controller import (
    CART_UNAVAILABLE_CHECKOUT_MSG,
    CART_UNAVAILABLE_REASON,
    annotate_cart_item,
    fetch_cart_items,
)


def _ring_item(**overrides):
    base = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "user-1",
        "category": "ring",
        "style_type": "ring-A",
        "summary_zh": "測試戒指",
        "total_price": 12000,
        "config_json": {
            "category": "ring",
            "type": "ring-A",
            "gold": "14k",
            "carat": "0.3",
            "clientPricing": {"total": 12000, "ready": True},
        },
    }
    base.update(overrides)
    return base


class _Cur:
    def __init__(self, rows=None, item=None):
        self.rows = rows or []
        self.item = item
        self.deleted: list = []

    def execute(self, query, params=None):
        q = " ".join(query.split()).lower()
        if q.startswith("delete"):
            self.deleted.append(params)
        return None

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.item


# Match `with get_connection() as conn, conn.cursor() as cur`
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


def test_annotate_published_item_available(monkeypatch):
    monkeypatch.setattr(
        "app.controllers.shop_controller.get_product_variant",
        lambda cur, **kwargs: {"gold": "14k", "carat": "0.3", "weight_chin": 1.0},
    )
    monkeypatch.setattr(
        "app.controllers.shop_controller.compute_order_pricing",
        lambda cur, data, **kwargs: {"ready": True, "total": 12000},
    )
    item = annotate_cart_item(MagicMock(), _ring_item())
    assert item["available"] is True
    assert item["unavailableReason"] == ""


def test_annotate_unpublished_marks_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.controllers.shop_controller.get_product_variant",
        lambda cur, **kwargs: None,
    )
    item = annotate_cart_item(MagicMock(), _ring_item())
    assert item["available"] is False
    assert item["unavailableReason"] == CART_UNAVAILABLE_REASON


def test_annotate_pricing_not_ready_marks_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.controllers.shop_controller.get_product_variant",
        lambda cur, **kwargs: {"gold": "14k", "carat": "0.3", "weight_chin": 1.0},
    )
    monkeypatch.setattr(
        "app.controllers.shop_controller.compute_order_pricing",
        lambda cur, data, **kwargs: {"ready": False, "error": "product not available"},
    )
    item = annotate_cart_item(MagicMock(), _ring_item())
    assert item["available"] is False
    assert item["unavailableReason"] == CART_UNAVAILABLE_REASON


def test_annotate_diamond_missing_fields_unavailable():
    item = annotate_cart_item(
        MagicMock(),
        {
            "id": "d1",
            "category": "diamond",
            "style_type": "memorial",
            "config_json": {"category": "diamond", "type": "memorial"},
        },
    )
    assert item["available"] is False
    assert "carat" in item["unavailableReason"]


def test_annotate_diamond_complete_available_without_product_gate(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("diamond must not hit product pricing gate")

    monkeypatch.setattr("app.controllers.shop_controller.compute_order_pricing", boom)
    monkeypatch.setattr("app.controllers.shop_controller.get_product_variant", boom)
    item = annotate_cart_item(
        MagicMock(),
        {
            "id": "d2",
            "category": "diamond",
            "style_type": "memorial",
            "config_json": {"category": "diamond", "type": "memorial", "carat": "0.3"},
        },
    )
    assert item["available"] is True


def test_fetch_cart_items_annotates_after_unpublish(monkeypatch):
    rows = [_ring_item()]
    cur = _Cur(rows=rows)
    monkeypatch.setattr(
        "app.controllers.shop_controller.get_connection",
        lambda: _ConnOuter(cur),
    )
    monkeypatch.setattr(
        "app.controllers.shop_controller.config_image_url",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "app.controllers.shop_controller.get_product_variant",
        lambda cur, **kwargs: None,
    )
    items = fetch_cart_items("user-1")
    assert len(items) == 1
    assert items[0]["available"] is False
    assert items[0]["unavailableReason"] == CART_UNAVAILABLE_REASON


def test_checkout_rejects_unavailable_item(monkeypatch):
    from app.controllers import shop_controller as sc

    item = _ring_item()
    cur = _Cur(rows=[item])
    monkeypatch.setattr(sc, "get_connection", lambda: _ConnOuter(cur))
    monkeypatch.setattr(sc, "_request_is_shop_preview", lambda *a, **k: False)
    monkeypatch.setattr(sc, "_user_id", lambda request: "user-1")
    monkeypatch.setattr(sc, "get_product_variant", lambda cur, **kwargs: None)

    request = SimpleNamespace(cookies={}, headers={}, query_params={})
    result = asyncio.run(
        sc._cart_checkout_impl(
            request,
            {
                "itemIds": [item["id"]],
                "customerName": "A",
                "customerPhone": "0912",
            },
        )
    )
    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    payload = json.loads(result.body)
    assert payload["error"] == CART_UNAVAILABLE_CHECKOUT_MSG


def test_delete_cart_item_works_when_unavailable(monkeypatch):
    """DELETE still removes unavailable rows — no availability gate."""
    from app.controllers import shop_controller as sc

    item = _ring_item()
    cur = _Cur(item=item)
    monkeypatch.setattr(sc, "get_connection", lambda: _ConnOuter(cur))
    monkeypatch.setattr(sc, "_user_id", lambda request: "user-1")

    request = SimpleNamespace(
        method="DELETE",
        query_params={"id": item["id"]},
    )
    result = asyncio.run(sc.cart_item(request))
    assert result == {"ok": True}
    assert cur.deleted
    assert cur.deleted[0][0] == item["id"]
