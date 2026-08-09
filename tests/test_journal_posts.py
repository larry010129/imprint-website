"""Journal posts: public published filter + timeline year/month contract."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.content import (
    ensure_journal_posts_schema,
    fetch_published_journal_posts,
    fetch_published_journal_post,
    parse_journal_post_payload,
    serialize_journal_post,
)


def test_ensure_journal_posts_schema_creates_table_and_index():
    statements: list[str] = []

    class FakeCursor:
        def execute(self, query, params=None):
            statements.append(" ".join(query.split()).lower())

    ensure_journal_posts_schema(FakeCursor())
    assert any("create table if not exists journal_posts" in query for query in statements)
    assert any("create index if not exists journal_posts_published_posted_idx" in query for query in statements)


def year_month_from_date(date_str: str) -> dict[str, str]:
    """Mirror Journal.tsx yearMonthFromDate: YYYY-MM-DD -> year + MM."""
    parts = date_str.split("-")
    year = parts[0] if len(parts) > 0 else ""
    month = parts[1] if len(parts) > 1 else ""
    return {"year": year, "month": month}


def test_year_month_from_posted_at_iso():
    assert year_month_from_date("2025-05-12") == {"year": "2025", "month": "05"}
    assert year_month_from_date("2026-02-01") == {"year": "2026", "month": "02"}
    assert year_month_from_date("2024-12-31") == {"year": "2024", "month": "12"}


def test_year_month_from_incomplete_date():
    assert year_month_from_date("2025") == {"year": "2025", "month": ""}
    assert year_month_from_date("") == {"year": "", "month": ""}


def test_parse_journal_post_payload_accepts_yyyy_mm_dd():
    cleaned, error = parse_journal_post_payload(
        {
            "title": "Day one",
            "body": "hello",
            "posted_at": "2026-03-15",
            "is_published": True,
            "is_archived": False,
        }
    )
    assert error is None
    assert cleaned is not None
    assert cleaned["posted_at"] == "2026-03-15"


def test_parse_journal_post_payload_image_url_optional():
    cleaned, error = parse_journal_post_payload(
        {
            "title": "No image",
            "body": "text only",
            "posted_at": "2026-03-15",
            "image_url": "",
            "is_published": True,
        }
    )
    assert error is None
    assert cleaned is not None
    assert cleaned["image_url"] is None

    cleaned2, error2 = parse_journal_post_payload(
        {
            "title": "Keep image",
            "posted_at": "2026-03-15",
            "image_url": "https://example.com/j.webp",
        }
    )
    assert error2 is None
    assert cleaned2 is not None
    assert cleaned2["image_url"] == "https://example.com/j.webp"


def test_parse_journal_post_payload_rejects_bad_date():
    cleaned, error = parse_journal_post_payload(
        {"title": "Bad", "posted_at": "not-a-date"}
    )
    assert cleaned is None
    assert error is not None
    assert "YYYY-MM-DD" in error


def test_parse_journal_post_payload_requires_date():
    cleaned, error = parse_journal_post_payload({"title": "No date", "posted_at": ""})
    assert cleaned is None
    assert error is not None
    assert "日期" in error


def test_serialize_posted_at_feeds_year_month():
    row = {
        "id": uuid4(),
        "title": "Seed",
        "body": "",
        "posted_at": date(2025, 5, 12),
        "image_url": None,
        "is_archived": False,
        "is_published": True,
        "sort_order": 0,
        "created_at": datetime(2025, 5, 12, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 5, 12, tzinfo=timezone.utc),
    }
    out = serialize_journal_post(row)
    assert out["posted_at"] == "2025-05-12"
    assert year_month_from_date(out["posted_at"]) == {"year": "2025", "month": "05"}


def test_fetch_published_journal_posts_sql_filters_unpublished():
    class FakeCursor:
        def __init__(self):
            self.query = ""
            self.params = None
            self._rows: list[dict] = []

        def execute(self, query, params=None):
            self.query = " ".join(query.split())
            self.params = params
            assert "is_published = true" in self.query
            assert "order by posted_at desc" in self.query.lower()
            self._rows = [
                {
                    "id": uuid4(),
                    "title": "Published only",
                    "body": "body",
                    "posted_at": date(2026, 2, 1),
                    "image_url": "/static/j.jpg",
                    "is_archived": True,
                    "is_published": True,
                    "sort_order": 1,
                    "created_at": datetime(2026, 2, 1, tzinfo=timezone.utc),
                    "updated_at": datetime(2026, 2, 1, tzinfo=timezone.utc),
                }
            ]

        def fetchall(self):
            return self._rows

    cur = FakeCursor()
    posts = fetch_published_journal_posts(cur)
    assert "limit" not in cur.query.lower()
    assert len(posts) == 1
    assert posts[0]["title"] == "Published only"
    assert posts[0]["posted_at"] == "2026-02-01"
    assert posts[0]["is_published"] is True
    assert posts[0]["is_archived"] is True
    assert posts[0]["image_url"] == "/static/j.jpg"
    assert isinstance(posts[0]["id"], str)

    cur_page = FakeCursor()
    fetch_published_journal_posts(cur_page, limit=12, offset=24)
    assert "limit %s offset %s" in cur_page.query.lower()
    assert cur_page.params == [12, 24]


def test_fetch_published_journal_post_uses_id_and_published_filter():
    post_id = uuid4()

    class FakeCursor:
        def __init__(self):
            self.query = ""
            self.params = None

        def execute(self, query, params=None):
            self.query = " ".join(query.split()).lower()
            self.params = params

        def fetchone(self):
            return {
                "id": post_id,
                "title": "Details",
                "body": "Full post body",
                "posted_at": date(2026, 4, 2),
                "image_url": None,
                "is_archived": False,
                "is_published": True,
                "sort_order": 0,
            }

    cur = FakeCursor()
    post = fetch_published_journal_post(cur, post_id)
    assert "where id = %s and is_published = true" in cur.query
    assert cur.params == (post_id,)
    assert post["id"] == str(post_id)
    assert post["posted_at"] == "2026-04-02"


def test_journal_listing_keeps_ssr_body_fallback_separate_from_react_mount():
    root = Path(__file__).resolve().parents[1]
    template = (root / "content/site/templates/pages/journal.html").read_text(encoding="utf-8")
    mount = (root / "frontend/src/journal-main.tsx").read_text(encoding="utf-8")
    assert 'data-journal-ssr' in template
    assert 'post.body[:280]' in template
    assert 'data-journal-app' in template
    assert 'querySelectorAll("[data-journal-app]")' in mount
