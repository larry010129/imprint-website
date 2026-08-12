"""Home banner per-role text colors (eyebrow / title / lead)."""

from app.content import serialize_banner
from app.controllers.admin_controller import _parse_banner_fields


def test_parse_banner_fields_accepts_three_role_colors():
    fields, err = _parse_banner_fields(
        {
            "title": "測試標題",
            "imageUrl": "/static/x.webp",
            "eyebrowColor": "mint",
            "titleColor": "ink",
            "leadColor": "#8eedf0",
            "align": "right",
        }
    )
    assert err is None
    assert fields["eyebrow_color"] == "mint"
    assert fields["title_color"] == "ink"
    assert fields["lead_color"] == "#8eedf0"
    # Legacy tone tracks title color for older readers.
    assert fields["tone"] == "ink"
    assert fields["align"] == "right"


def test_parse_banner_fields_falls_back_single_tone_to_all_roles():
    fields, err = _parse_banner_fields(
        {
            "title": "測試標題",
            "imageUrl": "/static/x.webp",
            "tone": "cream",
        }
    )
    assert err is None
    assert fields["eyebrow_color"] == "cream"
    assert fields["title_color"] == "cream"
    assert fields["lead_color"] == "cream"
    assert fields["tone"] == "cream"


def test_banner_image_urls_are_cache_busted_and_stripped_on_save():
    """Admin thumb must refresh after a replace; the buster must never persist."""
    from datetime import datetime, timezone

    stamp = datetime(2025, 8, 12, 3, 12, 44, tzinfo=timezone.utc)
    out = serialize_banner(
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "title": "t",
            "image_url": "/static/images/hero/a.jpg",
            "image_url_mobile": "/static/images/hero/a-mobile.jpg",
            "image_webp": "/static/images/hero/a.webp",
            "updated_at": stamp,
        }
    )
    assert out["image_url"] == "/static/images/hero/a.jpg?v=1754968364"
    assert out["image_url_mobile"] == "/static/images/hero/a-mobile.jpg?v=1754968364"
    assert out["image_webp"] == "/static/images/hero/a.webp?v=1754968364"

    fields, err = _parse_banner_fields(
        {
            "title": "t",
            "imageUrl": out["image_url"],
            "imageUrlMobile": out["image_url_mobile"],
            "imageWebp": out["image_webp"],
        }
    )
    assert err is None
    assert fields["image_url"] == "/static/images/hero/a.jpg"
    assert fields["image_url_mobile"] == "/static/images/hero/a-mobile.jpg"
    assert fields["image_webp"] == "/static/images/hero/a.webp"


def test_serialize_banner_fills_missing_role_colors_from_tone():
    out = serialize_banner(
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "title": "t",
            "tone": "teal",
            "is_published": True,
            "sort_order": 1,
        }
    )
    assert out["eyebrow_color"] == "teal"
    assert out["title_color"] == "teal"
    assert out["lead_color"] == "teal"
