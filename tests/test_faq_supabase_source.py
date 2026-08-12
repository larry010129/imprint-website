"""Public FAQ SSR must read Supabase rows — no content-seed.json live path."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.controllers import web_controller as wc


def test_web_controller_has_no_faq_seed_fallback():
    src = Path("app/controllers/web_controller.py").read_text(encoding="utf-8")
    assert "faq_public_from_seed" not in src
    assert "content-seed.json" not in src


def test_load_faq_public_returns_db_payload(monkeypatch):
    payload = {
        "categories": [{"id": "general", "title": "一般", "items": []}],
        "teaser": [],
        "items": [{"id": "q1"}],
    }

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
    monkeypatch.setattr("app.content.fetch_faq_public", lambda cur: payload)
    assert wc._load_faq_public() == payload


def test_load_faq_public_empty_db_stays_empty(monkeypatch):
    empty = {"categories": [], "teaser": [], "items": []}

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

    seed = MagicMock(return_value={"categories": [{"id": "seed"}]})
    monkeypatch.setattr("app.database.get_connection", lambda: FakeConn())
    monkeypatch.setattr("app.content.fetch_faq_public", lambda cur: empty)
    monkeypatch.setattr("app.content.faq_public_from_seed", seed)
    assert wc._load_faq_public() == empty
    seed.assert_not_called()


def test_load_faq_public_db_error_fail_closed(monkeypatch):
    seed = MagicMock(return_value={"categories": [{"id": "seed"}]})

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr("app.database.get_connection", boom)
    monkeypatch.setattr("app.content.faq_public_from_seed", seed)
    assert wc._load_faq_public() == {"categories": [], "teaser": [], "items": []}
    seed.assert_not_called()


def test_cms_kv_migration_matches_runtime_ddl():
    migration = Path("supabase/migrations/20260812130000_cms_kv.sql").read_text(
        encoding="utf-8"
    )
    schema = Path("backend/schema.sql").read_text(encoding="utf-8")
    for text in (migration, schema):
        assert "create table if not exists cms_kv" in text
        assert "key text primary key" in text
        assert "value jsonb not null" in text
        assert "updated_at timestamptz not null default now()" in text
