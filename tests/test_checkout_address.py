"""Checkout delivery address validation — Taiwan postal/city/street."""

from app.controllers.shop_controller import _validate_customer
from app.orders import enrich_member_order


def _body(**overrides):
    base = {
        "customerName": "王小明",
        "customerPhone": "0912345678",
        "fulfillmentMethod": "delivery",
        "shippingAddress": "忠孝東路四段123號",
        "shippingCity": "台北市",
        "shippingPostal": "106",
    }
    base.update(overrides)
    return base


def test_reject_latin_junk_street():
    customer, err = _validate_customer(
        _body(shippingAddress="123 abc"),
        None,
    )
    assert customer == {}
    assert err == "請填寫有效中文地址（含路街巷弄號）"


def test_reject_short_street():
    customer, err = _validate_customer(
        _body(shippingAddress="忠孝路"),
        None,
    )
    assert customer == {}
    assert err == "請填寫有效中文地址（含路街巷弄號）"


def test_reject_bad_postal():
    customer, err = _validate_customer(
        _body(shippingPostal="10"),
        None,
    )
    assert customer == {}
    assert err == "請填寫有效郵遞區號"


def test_reject_unknown_city():
    customer, err = _validate_customer(
        _body(shippingCity="火星市"),
        None,
    )
    assert customer == {}
    assert err == "請選擇有效縣市"


def test_accept_valid_delivery_and_normalize_city():
    customer, err = _validate_customer(
        _body(
            shippingCity="臺北市",
            shippingPostal="10617",
            shippingAddress="信義路五段7號",
        ),
        None,
    )
    assert err is None
    assert customer["shippingCity"] == "台北市"
    assert customer["shippingPostal"] == "10617"
    assert customer["shippingAddress"] == "信義路五段7號"
    assert customer["fulfillmentMethod"] == "delivery"


def test_pickup_skips_address_rules():
    customer, err = _validate_customer(
        {
            "customerName": "王小明",
            "customerPhone": "0912345678",
            "fulfillmentMethod": "pickup",
        },
        None,
    )
    assert err is None
    assert customer["fulfillmentMethod"] == "pickup"


def test_enrich_member_order_shipping_line():
    order = enrich_member_order(
        {
            "status": "received",
            "summary_zh": "測試戒指",
            "config_json": {"category": "ring", "gold": "14k", "color": "white"},
            "fulfillment_method": "delivery",
            "shipping_city": "台北市",
            "shipping_postal": "106",
            "shipping_address": "忠孝東路四段123號",
        }
    )
    assert order["shipping_line"] == "台北市 106 忠孝東路四段123號"
    assert order["fulfillment_label"] == "宅配到府"
