"""Public/admin testimonials must read Supabase rows — no local-seed display path."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.content import (
    build_testimonial_role,
    classify_testimonial_image_url,
    normalize_testimonial_image_url,
    remap_legacy_testimonial_categories,
    serialize_testimonial,
    summarize_testimonial_image_urls,
)
from app.seed_content import _seed_faq_testimonials


def test_serialize_normalizes_legacy_category_and_role():
    row = serialize_testimonial(
        {
            "id": "1",
            "name": "簡小姐",
            "role": "毛髮鑽石・新北",
            "category": "毛髮鑽石",
            "city": "新北",
            "country": "",
            "text": "quote",
            "image_url": "",
            "rating": 5,
            "sort_order": 0,
            "is_published": True,
        }
    )
    assert row["category"] == "真我鑽石"
    assert row["role"] == "真我鑽石・新北"
    assert row["text"] == "quote"
    assert row["name"] == "簡小姐"


def test_serialize_keeps_supabase_image_url():
    """CMS Storage URLs must not be rewritten to /static (localhost needs absolute)."""
    supabase = (
        "https://erobemoojyptyxvnyvuf.supabase.co/storage/v1/object/public/"
        "imprint-media/testimonials/testimonial-ring-01.webp"
    )
    row = serialize_testimonial(
        {
            "id": "9",
            "name": "朱小姐",
            "role": "生命鑽石・台北",
            "category": "生命鑽石",
            "city": "台北",
            "country": "",
            "text": "為父親製作",
            "image_url": supabase,
            "rating": 5,
            "sort_order": 4,
            "is_published": True,
        }
    )
    assert row["image_url"] == supabase
    assert row["text"] == "為父親製作"
    assert not str(row["image_url"]).startswith("/static/")


def test_testimonial_image_url_busted_then_stripped_on_save():
    """Wall thumb must refresh after a replace; the buster must never persist."""
    from datetime import datetime, timezone

    from app.content import parse_testimonial_payload

    supabase = (
        "https://proj.supabase.co/storage/v1/object/public/shop-media/testimonials/a.webp"
    )
    row = serialize_testimonial(
        {
            "id": "9",
            "name": "朱小姐",
            "category": "生命鑽石",
            "city": "台北",
            "country": "",
            "text": "為父親製作",
            "image_url": supabase,
            "rating": 5,
            "sort_order": 4,
            "is_published": True,
            "updated_at": datetime(2025, 8, 12, 3, 12, 44, tzinfo=timezone.utc),
        }
    )
    assert row["image_url"] == f"{supabase}?v=1754968364"

    cleaned, err = parse_testimonial_payload(
        {
            "name": "朱",
            "honorific": "小姐",
            "category": "生命鑽石",
            "city": "台北市",
            "text": "為父親製作",
            "imageUrl": row["image_url"],
        }
    )
    assert err is None
    assert cleaned["image_url"] == supabase


def test_normalize_passes_supabase_unchanged():
    url = (
        "https://proj.supabase.co/storage/v1/object/public/"
        "shop-media/testimonials/abcd.webp"
    )
    assert normalize_testimonial_image_url(url) == url
    assert (
        normalize_testimonial_image_url(
            "https://proj.supabase.co/storage/v1/object/public/shop-media/"
            "site-images/testimonials/presets/ring-A.jpg"
        )
        == (
            "https://proj.supabase.co/storage/v1/object/public/shop-media/"
            "site-images/testimonials/presets/ring-A.jpg"
        )
    )


def test_normalize_rewrites_static_images_to_supabase(monkeypatch):
    monkeypatch.setattr(
        "app.content._testimonial_public_storage_url",
        lambda object_path: (
            f"https://proj.supabase.co/storage/v1/object/public/shop-media/{object_path}"
        ),
    )
    assert normalize_testimonial_image_url(
        "/static/images/testimonials/presets/ring-A.webp"
    ) == (
        "https://proj.supabase.co/storage/v1/object/public/shop-media/"
        "site-images/testimonials/presets/ring-A.jpg"
    )
    assert normalize_testimonial_image_url(
        "/static/uploads/testimonials/face.png"
    ) == (
        "https://proj.supabase.co/storage/v1/object/public/shop-media/"
        "testimonials/face.webp"
    )


def test_image_url_classifier_and_summary():
    assert classify_testimonial_image_url(
        "https://x.supabase.co/storage/v1/object/public/b/a.webp"
    ) == "supabase"
    assert classify_testimonial_image_url("/static/images/testimonials/a.webp") == "static"
    assert classify_testimonial_image_url("") == "empty"
    stats = summarize_testimonial_image_urls(
        [
            {"image_url": "https://x.supabase.co/storage/v1/object/public/b/a.webp"},
            {"image_url": "/static/images/testimonials/a.webp"},
            {"image_url": ""},
        ]
    )
    assert stats == {
        "total": 3,
        "supabase": 1,
        "static": 1,
        "empty": 1,
        "other": 0,
    }


def test_remap_legacy_updates_both_labels():
    cur = MagicMock()
    cur.rowcount = 1
    updated = remap_legacy_testimonial_categories(cur)
    assert updated == 2
    assert cur.execute.call_count == 2
    old_labels = [call.args[1][3] for call in cur.execute.call_args_list]
    assert "初生鑽石" in old_labels
    assert "毛髮鑽石" in old_labels


def test_seed_skips_insert_when_testimonials_exist(monkeypatch):
    """Non-empty testimonials table must not pull rows from content-seed.json."""
    calls: list[str] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql, params=None):
            calls.append(" ".join(str(sql).lower().split()))
            self._sql = sql
            self._params = params

        def fetchone(self):
            sql = " ".join(str(self._sql).lower().split())
            if "to_regclass" in sql:
                return {"t": "testimonials", "c": "faq_categories"}
            if "count(*)" in sql and "testimonials" in sql:
                return {"count": 3}
            if "count(*)" in sql and "faq_items" in sql:
                return {"count": 1}
            return {}

        def fetchall(self):
            return []

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr("app.seed_content.get_connection", lambda: FakeConn())
    created = _seed_faq_testimonials()
    assert created == 0
    assert not any("insert into testimonials" in c for c in calls)


def test_role_builder_maps_legacy_hair_label():
    assert build_testimonial_role("毛髮鑽石", "新北") == "真我鑽石・新北"


def test_live_paths_have_no_seed_json_or_ts_array():
    """Display/API/admin must not import content-seed.json or TESTIMONIALS[]."""
    web = Path("app/controllers/web_controller.py").read_text(encoding="utf-8")
    api = Path("app/controllers/api_controller.py").read_text(encoding="utf-8")
    admin = Path("app/controllers/admin_controller.py").read_text(encoding="utf-8")
    home_wall = Path("public/js/home-wall.js").read_text(encoding="utf-8")
    stories_tsx = Path("frontend/src/components/StoriesTestimonials.tsx").read_text(
        encoding="utf-8"
    )
    wall_tsx = Path("frontend/src/components/TestimonialsWall.tsx").read_text(
        encoding="utf-8"
    )
    data_ts = Path("frontend/src/data/testimonials.ts").read_text(encoding="utf-8")
    for src in (web, api, admin, home_wall):
        assert "content-seed.json" not in src
    assert "fetchTestimonialsApi" in stories_tsx
    assert "fetchTestimonialsApi" in wall_tsx
    assert "TESTIMONIALS" not in stories_tsx
    assert "TESTIMONIALS" not in wall_tsx
    assert "export const TESTIMONIALS" not in data_ts
    assert "_load_stories_ssr" in web
    assert "fetch_published_testimonials" in web
    assert "fetch_published_testimonials" in api


def test_stories_ssr_uses_db_only(monkeypatch):
    from app.controllers import web_controller as wc

    payload = [
        {
            "id": "1",
            "name": "沈小姐",
            "text": "from-db",
            "image_url": "https://x.supabase.co/storage/v1/object/public/b/a.webp",
        }
    ]

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr("app.database.get_connection", lambda: FakeConn())
    monkeypatch.setattr(
        "app.content.fetch_published_testimonials",
        lambda cur, limit=None, offset=0: payload,
    )
    assert wc._load_stories_ssr() == payload
    assert wc._load_stories_ssr()[0]["text"] == "from-db"
