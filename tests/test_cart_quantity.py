"""Cart line quantity update + pricing clamps."""

from __future__ import annotations

from app.controllers.shop_controller import set_cart_item_quantity
from app.pricing import (
    CART_LINE_QUANTITY_MAX,
    DIAMOND_PRICE,
    EARRING_QUANTITY_MAX,
    WHITE_MULTI_DIAMOND_PRICE,
    _as_line_quantity,
    cart_line_quantity_max,
    memorial_diamond_line_totals,
)


def test_as_line_quantity_earring_pair_cap():
    assert _as_line_quantity(1, category="earring") == 1
    assert _as_line_quantity(2, category="earring") == 2
    assert _as_line_quantity(9, category="earring") == EARRING_QUANTITY_MAX
    assert _as_line_quantity(0, category="earring") == 1
    assert _as_line_quantity("nope", category="earring") == 1


def test_as_line_quantity_general_max():
    assert _as_line_quantity(1, category="ring") == 1
    assert _as_line_quantity(3, category="pendant") == 3
    assert _as_line_quantity(500, category="ring") == CART_LINE_QUANTITY_MAX
    assert cart_line_quantity_max("earring") == EARRING_QUANTITY_MAX
    assert cart_line_quantity_max("ring") == CART_LINE_QUANTITY_MAX


class _Cur:
    def __init__(self, item=None):
        self.item = item
        self.deleted: list = []
        self.updated: list = []
        self._count = 1

    def execute(self, query, params=None):
        q = " ".join(query.split()).lower()
        if q.startswith("delete"):
            self.deleted.append(params)
            self.item = None
            self._count = 0
        elif q.startswith("update"):
            self.updated.append(params)
            cfg = params[2]
            total = params[4]
            self.item = {
                **(self.item or {}),
                "category": params[0],
                "style_type": params[1],
                "config_json": cfg,
                "summary_zh": params[3],
                "total_price": total,
            }
        elif "count(*)" in q:
            self._count_row = {"count": self._count}
        return None

    def fetchone(self):
        if getattr(self, "_count_row", None) is not None:
            row = self._count_row
            self._count_row = None
            return row
        return self.item


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


def _ring_item():
    return {
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
            "quantity": 1,
            "clientPricing": {"total": 12000, "ready": True},
        },
    }


def test_set_cart_item_quantity_deletes_at_zero(monkeypatch):
    cur = _Cur(_ring_item())
    monkeypatch.setattr(
        "app.controllers.shop_controller.get_connection",
        lambda: _ConnOuter(cur),
    )
    result = set_cart_item_quantity("user-1", _ring_item()["id"], 0)
    assert result["ok"] is True
    assert result["deleted"] is True
    assert cur.deleted


def test_set_cart_item_quantity_updates_and_reprices(monkeypatch):
    cur = _Cur(_ring_item())
    monkeypatch.setattr(
        "app.controllers.shop_controller.get_connection",
        lambda: _ConnOuter(cur),
    )
    monkeypatch.setattr(
        "app.controllers.shop_controller._validate_product_variant",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "app.controllers.shop_controller._clamp_pendant_chain_sell_mode",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "app.controllers.shop_controller._strip_disallowed_engraving",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "app.controllers.shop_controller._strip_disallowed_fancy_shape",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "app.controllers.shop_controller.compute_order_pricing",
        lambda cur, config, **k: {
            "ready": True,
            "total": 24000,
            "quantity": 2,
        },
    )
    result = set_cart_item_quantity("user-1", _ring_item()["id"], 2)
    assert result["ok"] is True
    assert result["deleted"] is False
    assert result["quantity"] == 2
    assert result["item"]["total_price"] == 24000
    assert cur.updated
    cfg = cur.updated[0][2]
    if hasattr(cfg, "obj"):
        cfg = cfg.obj
    assert cfg["quantity"] == 2


def test_set_cart_item_quantity_invalid(monkeypatch):
    cur = _Cur(_ring_item())
    monkeypatch.setattr(
        "app.controllers.shop_controller.get_connection",
        lambda: _ConnOuter(cur),
    )
    result = set_cart_item_quantity("user-1", _ring_item()["id"], "x")
    assert result["error"] == "invalid quantity"
    assert result["status"] == 400


def _diamond_item():
    return {
        "id": "22222222-2222-2222-2222-222222222222",
        "user_id": "user-1",
        "category": "diamond",
        "style_type": "diamond-A",
        "summary_zh": "測試紀念鑽",
        "total_price": DIAMOND_PRICE["0.3"],
        "config_json": {
            "category": "diamond",
            "type": "diamond-A",
            "carat": "0.3",
            "diamondKind": "white",
            "quantity": 1,
            "clientPricing": {"total": DIAMOND_PRICE["0.3"], "ready": True},
        },
    }


def test_set_cart_item_quantity_applies_memorial_package_discount(monkeypatch):
    """qty 1→2 on single memorial diamond unlocks 2-stone package + compareAt."""
    cur = _Cur(_diamond_item())
    monkeypatch.setattr(
        "app.controllers.shop_controller.get_connection",
        lambda: _ConnOuter(cur),
    )
    monkeypatch.setattr(
        "app.controllers.shop_controller._validate_product_variant",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "app.controllers.shop_controller._clamp_pendant_chain_sell_mode",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "app.controllers.shop_controller._strip_disallowed_engraving",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "app.controllers.shop_controller._strip_disallowed_fancy_shape",
        lambda *a, **k: None,
    )
    monkeypatch.setattr("app.pricing.load_overrides", lambda cur: {})
    expected_sale, expected_compare = memorial_diamond_line_totals("0.3", line_qty=2)
    result = set_cart_item_quantity("user-1", _diamond_item()["id"], 2)
    assert result["ok"] is True
    assert result["quantity"] == 2
    assert expected_sale == WHITE_MULTI_DIAMOND_PRICE["0.3"][2]
    assert expected_compare == DIAMOND_PRICE["0.3"] * 2
    assert result["item"]["total_price"] == expected_sale
    cfg = cur.updated[0][2]
    if hasattr(cfg, "obj"):
        cfg = cfg.obj
    assert cfg["quantity"] == 2
    assert cfg["clientPricing"]["total"] == expected_sale
    assert cfg["clientPricing"]["compareAtTotal"] == expected_compare
