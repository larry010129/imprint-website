from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from psycopg.errors import UndefinedTable

from app import i18n_admin, i18n_store
from app.controllers import translations_admin_controller as controller
from app.i18n import load_catalog, translate_html
from main import app

HASH = "a" * 64
SAVE = {"sourceHash": HASH, "lang": "en", "translated": "New Arrival"}


class Cursor:
    def __init__(self, rows=(), error=None):
        self.rows, self.error, self.calls = list(rows), error, []

    def execute(self, query, params=None):
        if self.error:
            raise self.error
        self.calls.append((query, params))

    def fetchone(self):
        if "count(*)" in self.calls[-1][0]:
            return {"total": len(self.rows)}
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def use_cursor(monkeypatch, cursor):
    class Connection:
        def cursor(self):
            return cursor

    @contextmanager
    def connect():
        yield Connection()

    monkeypatch.setattr(controller, "get_connection", connect)


@pytest.fixture
def as_admin(monkeypatch):
    logged = []
    monkeypatch.setattr(controller, "require_admin", lambda _request: "admin-id")
    monkeypatch.setattr(controller, "_actor_email", lambda _id: "admin@example.test")
    monkeypatch.setattr(controller, "log_admin_action", lambda *args: logged.append(args))
    monkeypatch.setattr(i18n_store, "request_sync", lambda *_a, **_k: None)
    return logged


def stored_row(**changes):
    row = {"source_hash": HASH, "lang": "en", "source": "新品上市",
           "translated": "New Arrival", "edited_at": None}
    return {**row, **changes}


@pytest.mark.parametrize("method, url", [
    ("get", "/api/admin/translations"), ("post", "/api/admin/translation-update"),
])
def test_signed_out_visitors_are_rejected(method, url):
    response = getattr(TestClient(app), method)(url)
    assert response.status_code in {401, 403}


def test_list_shows_only_current_text_not_overridden_by_site_files(monkeypatch):
    monkeypatch.setattr(
        i18n_store, "collect_public_texts",
        lambda _cur: {"新品上市": ["新品上市"], "首頁": ["首頁"]},
    )
    monkeypatch.setattr(i18n_admin, "load_entries", lambda _lang: {"首頁": "Home"})
    cur = Cursor([stored_row()])
    total, rows = i18n_admin.list_translations(
        cur, language="en", search="50%_off", limit=20, offset=40
    )
    assert total == 1 and rows[0]["edited"] is False
    query, params = cur.calls[-1]
    assert params[0] == "en" and params[1] == [i18n_store._hash("新品上市")]
    # typed % and _ are searched for literally, and never join the SQL text
    assert params[2] == "%50\\%\\_off%" and "50" not in query
    assert params[-2:] == [20, 40]


@pytest.mark.parametrize("change", [
    {"lang": "fr"}, {"translated": "   "}, {"translated": None},
    {"sourceHash": "1 or 1=1"}, {"translated": "x" * 100_001},
])
def test_bad_save_requests_are_refused(monkeypatch, as_admin, change):
    cur = Cursor([stored_row()])
    use_cursor(monkeypatch, cur)
    response = TestClient(app).post("/api/admin/translation-update", json={**SAVE, **change})
    assert response.status_code == 400
    assert cur.calls == [] and as_admin == []


def test_save_marks_the_row_edited_and_keeps_line_breaks(monkeypatch, as_admin):
    cur = Cursor([stored_row(translated="One\nTwo", edited_at="2026-11-26")])
    use_cursor(monkeypatch, cur)
    forgotten = []
    monkeypatch.setattr(i18n_store, "forget", forgotten.append)
    response = TestClient(app).post(
        "/api/admin/translation-update", json={**SAVE, "translated": " One\r\nTwo "}
    )
    assert response.status_code == 200 and response.json()["item"]["edited"] is True
    query, params = cur.calls[0]
    assert "edited_at = now()" in query and params == ("One\nTwo", HASH, "en")
    assert forgotten == ["en"] and as_admin[0][1] == "translation_updated"


def test_saving_an_unknown_row_is_not_found(monkeypatch, as_admin):
    use_cursor(monkeypatch, Cursor())
    response = TestClient(app).post("/api/admin/translation-update", json=SAVE)
    assert response.status_code == 404 and as_admin == []


def test_missing_table_is_reported_not_crashed(monkeypatch, as_admin):
    use_cursor(monkeypatch, Cursor(error=UndefinedTable("i18n_translations")))
    client = TestClient(app)
    listed = client.get("/api/admin/translations?lang=ja")
    assert listed.status_code == 200 and listed.json()["ready"] is False
    saved = client.post("/api/admin/translation-update", json=SAVE)
    assert saved.status_code == 503


def test_unknown_list_language_is_refused(as_admin):
    assert TestClient(app).get("/api/admin/translations?lang=fr").status_code == 400


def test_a_saved_correction_reaches_visitor_pages(monkeypatch):
    stored = {"source": "僅供測試的新消息", "translated": "Machine words"}
    cur = Cursor([stored])

    class Connection:
        def cursor(self):
            return cur

    @contextmanager
    def connect():
        yield Connection()

    # No Google key: saved translations must show anyway.
    monkeypatch.delenv("GOOGLE_TRANSLATE_API_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused.invalid/test")
    monkeypatch.setattr("app.database.get_connection", connect)
    monkeypatch.setattr(i18n_store, "_cache", {})
    try:
        assert load_catalog("en").get("僅供測試的新消息") == "Machine words"
        stored["translated"] = "Corrected words"
        assert load_catalog("en").get("僅供測試的新消息") == "Machine words"  # cached
        i18n_store.forget("en")
        out, _ = translate_html("<p>僅供測試的新消息</p>", load_catalog("en"))
        assert "Corrected words" in out
    finally:
        monkeypatch.setenv("DATABASE_URL", "")
        load_catalog("en")  # rebuild without the fake row


def test_the_app_serves_the_tab_script():
    response = TestClient(app).get("/js/admin-translations.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_tab_never_reaches_the_content_bootstrap():
    script = open("public/js/admin-content.js", encoding="utf-8").read()
    assert "if (tab === 'translations') return;" in script
    for page in ("admin.html", "admin1.html"):
        html = open(page, encoding="utf-8").read()
        assert html.index("admin-translations.js") < html.index("admin-content.js")
