"""Checkout delivery + collection-bottle address validation — Taiwan postal/city/street."""

import pytest

from app.controllers.shop_controller import (
    _validate_customer,
    cart_needs_collection_bottle,
)
from app.orders import enrich_member_order
from app.tw_address import STREET_ERROR, valid_tw_street


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


def _bottle(**overrides):
    base = {
        "collectionBottleAddress": "信義路五段7號",
        "collectionBottleCity": "台北市",
        "collectionBottlePostal": "110",
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    "address",
    [
        "忠孝東路四段123號",
        "信義路五段7號",
        "中山路100號3樓",
        "文化路二段99巷5弄2號",
        "福德南路43號",
        "復興南路一段390號2樓之1",
        "達邦村1鄰5號",
        "中正路168號B1",
    ],
)
def test_valid_tw_street_samples(address):
    assert valid_tw_street(address) is True


@pytest.mark.parametrize(
    "address",
    [
        "",
        "忠孝路",
        "忠孝東路四段",
        "123 abc",
        "hello world",
        "asdfasdf",
        "aaaaaa",
        "路路路路路路",
        "你好世界測試文",
        "測試測試測試",
        "111111",
        "abcdef路1",
    ],
)
def test_invalid_tw_street_samples(address):
    assert valid_tw_street(address) is False


def test_reject_latin_junk_street():
    customer, err = _validate_customer(
        _body(shippingAddress="123 abc"),
        None,
    )
    assert customer == {}
    assert err == STREET_ERROR


def test_reject_random_chinese_words():
    customer, err = _validate_customer(
        _body(shippingAddress="你好世界測試文"),
        None,
    )
    assert customer == {}
    assert err == STREET_ERROR


def test_reject_repeated_junk_street():
    customer, err = _validate_customer(
        _body(shippingAddress="路路路路路路"),
        None,
    )
    assert customer == {}
    assert err == STREET_ERROR


def test_reject_road_without_number():
    customer, err = _validate_customer(
        _body(shippingAddress="忠孝東路四段"),
        None,
    )
    assert customer == {}
    assert err == STREET_ERROR


def test_reject_short_street():
    customer, err = _validate_customer(
        _body(shippingAddress="忠孝路"),
        None,
    )
    assert customer == {}
    assert err == STREET_ERROR


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


def test_collection_bottle_required_when_flagged():
    customer, err = _validate_customer(
        _body(fulfillmentMethod="pickup"),
        None,
        require_collection_bottle=True,
    )
    assert customer == {}
    assert err == "請填寫完整的收集瓶寄送地址"


def test_collection_bottle_accepts_valid_and_normalizes():
    customer, err = _validate_customer(
        {
            **_body(fulfillmentMethod="pickup"),
            **_bottle(collectionBottleCity="臺北市"),
        },
        None,
        require_collection_bottle=True,
    )
    assert err is None
    assert customer["collectionBottleCity"] == "台北市"
    assert customer["collectionBottlePostal"] == "110"
    assert customer["collectionBottleAddress"] == "信義路五段7號"


def test_collection_bottle_rejects_bad_street():
    customer, err = _validate_customer(
        {
            **_body(fulfillmentMethod="pickup"),
            **_bottle(collectionBottleAddress="123 abc"),
        },
        None,
        require_collection_bottle=True,
    )
    assert customer == {}
    assert err == STREET_ERROR


def test_collection_bottle_rejects_random_words():
    customer, err = _validate_customer(
        {
            **_body(fulfillmentMethod="pickup"),
            **_bottle(collectionBottleAddress="隨便寫幾個字"),
        },
        None,
        require_collection_bottle=True,
    )
    assert customer == {}
    assert err == STREET_ERROR


def test_collection_bottle_optional_when_not_required():
    customer, err = _validate_customer(
        _body(fulfillmentMethod="pickup"),
        None,
        require_collection_bottle=False,
    )
    assert err is None
    assert customer["collectionBottleAddress"] is None


def test_cart_needs_collection_bottle_skips_chain_only():
    assert cart_needs_collection_bottle(
        [{"category": "chain", "config_json": {"category": "chain"}}]
    ) is False
    assert cart_needs_collection_bottle(
        [{"category": "diamond", "config_json": {"category": "diamond"}}]
    ) is True
    assert cart_needs_collection_bottle(
        [
            {"category": "chain", "config_json": {"category": "chain"}},
            {"category": "ring", "config_json": {"category": "ring"}},
        ]
    ) is True


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
            "collection_bottle_city": "新北市",
            "collection_bottle_postal": "241",
            "collection_bottle_address": "福德南路43號",
        }
    )
    assert order["shipping_line"] == "台北市 106 忠孝東路四段123號"
    assert order["collection_bottle_line"] == "新北市 241 福德南路43號"
    assert order["fulfillment_label"] == "宅配到府"
