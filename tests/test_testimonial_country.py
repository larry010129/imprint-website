"""Testimonial city「其他」+ country free-text."""

from app.content import (
    build_testimonial_role,
    location_label_for_testimonial,
    parse_testimonial_payload,
)


def _base(**overrides):
    body = {
        "namePart": "王",
        "honorific": "小姐",
        "category": "寵物鑽石",
        "city": "台北市",
        "text": "很感動的見證內容",
        "imageUrl": "/static/uploads/testimonials/x.jpg",
        "isPublished": True,
    }
    body.update(overrides)
    return body


def test_location_label_other_uses_country():
    assert location_label_for_testimonial("其他", "日本") == "日本"
    assert location_label_for_testimonial("台北市", "日本") == "台北市"
    assert location_label_for_testimonial("其他", "") == "其他"


def test_role_other_shows_country():
    assert build_testimonial_role("寵物鑽石", "其他", "日本") == "寵物鑽石・日本"
    assert build_testimonial_role("寵物鑽石", "台北市", "日本") == "寵物鑽石・台北市"


def test_parse_other_requires_country():
    cleaned, err = parse_testimonial_payload(_base(city="其他", country=""))
    assert cleaned is None
    assert "國家" in (err or "")


def test_parse_other_persists_country():
    cleaned, err = parse_testimonial_payload(_base(city="其他", country="日本"))
    assert err is None
    assert cleaned["city"] == "其他"
    assert cleaned["country"] == "日本"
    assert cleaned["role"] == "寵物鑽石・日本"


def test_parse_taiwan_city_clears_country():
    cleaned, err = parse_testimonial_payload(_base(city="台中市", country="日本"))
    assert err is None
    assert cleaned["city"] == "台中市"
    assert cleaned["country"] == ""
    assert cleaned["role"] == "寵物鑽石・台中市"
