"""Testimonial city「其他」+ country free-text + series categories."""

from app.content import (
    TESTIMONIAL_CATEGORIES,
    build_testimonial_role,
    location_label_for_testimonial,
    normalize_testimonial_category,
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


def test_categories_match_six_series_nav_order():
    assert TESTIMONIAL_CATEGORIES == (
        "滿月鑽石",
        "寵物鑽石",
        "結髮鑽石",
        "全家福鑽石",
        "生命鑽石",
        "真我鑽石",
    )


def test_legacy_category_map():
    assert normalize_testimonial_category("初生鑽石") == "滿月鑽石"
    assert normalize_testimonial_category("毛髮鑽石") == "真我鑽石"
    assert normalize_testimonial_category("結髮鑽石") == "結髮鑽石"


def test_parse_accepts_legacy_category_labels():
    cleaned, err = parse_testimonial_payload(_base(category="初生鑽石"))
    assert err is None
    assert cleaned["category"] == "滿月鑽石"
    assert cleaned["role"] == "滿月鑽石・台北市"

    cleaned, err = parse_testimonial_payload(_base(category="毛髮鑽石"))
    assert err is None
    assert cleaned["category"] == "真我鑽石"


def test_parse_rejects_unknown_category():
    cleaned, err = parse_testimonial_payload(_base(category="幽靈鑽石"))
    assert cleaned is None
    assert "分類" in (err or "")
