"""Unit tests for Google People profile parsing."""

from app.google_people import merge_into_profile, parse_address, parse_phone


def test_parse_phone_prefers_mobile():
    people = {
        "phoneNumbers": [
            {"value": "02-12345678", "type": "work"},
            {"value": "0912-345-678", "type": "mobile"},
        ]
    }
    assert parse_phone(people) == "0912345678"


def test_parse_phone_normalizes_886():
    people = {"phoneNumbers": [{"value": "+886 912 345 678", "type": "mobile"}]}
    assert parse_phone(people) == "0912345678"


def test_parse_address_home():
    people = {
        "addresses": [
            {
                "type": "home",
                "postalCode": "106",
                "locality": "台北市",
                "administrativeArea": "大安區",
                "streetAddress": "信義路一段1號",
            }
        ]
    }
    addr = parse_address(people)
    assert addr["shipping_postal"] == "106"
    assert "台北市" in (addr["shipping_city"] or "")
    assert addr["shipping_address"] == "信義路一段1號"


def test_merge_only_empty_fields():
    existing = {"phone": "0911111111", "shipping_postal": None}
    updates = merge_into_profile(existing, "0922222222", {"shipping_postal": "100", "shipping_city": "台北", "shipping_address": "路"})
    assert "phone" not in updates
    assert updates["shipping_postal"] == "100"
