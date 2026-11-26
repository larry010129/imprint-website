"""Auto-translate under a daily character quota, with a pretend Google and table."""

from __future__ import annotations

from contextlib import contextmanager

import pytest

from app import i18n_store, translator_google

LIMIT = 16_000
LANGUAGES = ("en", "ja", "ko")


class FakeGoogle:
    """Counts characters like the quota does and refuses requests over today's limit."""

    def __init__(self):
        self.used = 0
        self.accepted: list[tuple[str, str]] = []  # (language, Chinese sent)
        self.requests = 0

    def post(self, _url, headers, json, timeout):
        self.requests += 1
        cost = sum(len(q) for q in json["q"])
        over = self.used + cost > LIMIT
        if not over:
            self.used += cost
            self.accepted += [(json["target"], q) for q in json["q"]]

        class Reply:
            def raise_for_status(self):
                if over:
                    raise translator_google.requests.HTTPError("quota exceeded")

            def json(self):
                return {"data": {"translations": [
                    {"translatedText": f"T{len(q)}"} for q in json["q"]
                ]}}

        return Reply()


class Table:
    def __init__(self):
        self.rows: dict[tuple[str, str], tuple[str, str]] = {}

    def execute(self, query, params):
        if query.startswith("insert"):
            digest, language, source, target = params
            self.rows.setdefault((digest, language), (source, target))
            return
        wanted = set(params[1]) if len(params) > 1 else None
        self.found = [
            {"source": source, "translated": target}
            for (digest, language), (source, target) in self.rows.items()
            if language == params[0] and (wanted is None or digest in wanted)
        ]

    def fetchall(self):
        return self.found

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def translated(self, language):
        return {s: t for (_d, lang), (s, t) in self.rows.items() if lang == language}


@pytest.fixture
def world(monkeypatch):
    google, table = FakeGoogle(), Table()

    class Connection:
        def cursor(self):
            return table

    @contextmanager
    def connect():
        yield Connection()

    monkeypatch.setenv("GOOGLE_TRANSLATE_API_KEY", "test-key")
    monkeypatch.setattr(translator_google.requests, "post", google.post)
    monkeypatch.setattr("app.database.get_connection", connect)
    monkeypatch.setattr("app.i18n.load_entries", lambda _language: {})
    return google, table


def use_texts(monkeypatch, *values):
    """Public content as collect_public_texts reports it (real implementation)."""
    class Content:
        def __init__(self):
            self.rows = []

        def execute(self, query):
            self.rows = (
                [{"body": value} for value in values]
                if "from journal_posts" in query else []
            )

        def fetchall(self):
            return self.rows

    texts = i18n_store.collect_public_texts(Content())
    monkeypatch.setattr(i18n_store, "collect_public_texts", lambda _cur: texts)
    return texts


def run_days(google, days=30):
    """One sync per day until a day finishes without hitting the limit."""
    saved_each_day = []
    for _day in range(days):
        google.used = 0
        try:
            saved_each_day.append((i18n_store.sync_once(), False))
            return saved_each_day
        except translator_google.TranslationError:
            saved_each_day.append((None, True))
    raise AssertionError("never finished")


def paragraph(number, length):
    head = f"第{number}段"
    return head + "字" * (length - len(head))


def test_limit_loses_nothing_and_nothing_is_sent_twice(monkeypatch, world):
    google, table = world
    values = [paragraph(i, 300) for i in range(60)]  # 54,000 characters in 3 languages
    use_texts(monkeypatch, *values)
    seen = []
    for _day in range(10):
        google.used = 0
        try:
            i18n_store.sync_once()
        except translator_google.TranslationError:
            pass
        # everything Google accepted is saved, even on a day that hit the limit
        assert len(table.rows) == len(google.accepted)
        seen.append(len(table.rows))
        if len(table.rows) == len(values) * 3:
            break
    assert len(table.rows) == len(values) * 3
    assert seen == sorted(set(seen))  # progress every day
    assert len(google.accepted) == len(set(google.accepted))


def test_a_post_bigger_than_the_daily_limit_finishes(monkeypatch, world):
    google, table = world
    body = "\n\n".join(paragraph(i, 500) for i in range(40)) + "\n\n2026 GIA"
    texts = use_texts(monkeypatch, body)
    assert len(body) > 20_000
    days = run_days(google)
    assert len(days) > 1
    for language in LANGUAGES:
        done = table.translated(language)
        whole = done[next(k for k, parts in texts.items() if len(parts) > 1)]
        assert whole.split("\n") == ["T500"] * 40 + ["2026 GIA"]
    # only the 40 Chinese paragraphs were paid for: not the whole post again
    assert sum(len(q) for _lang, q in google.accepted) == 40 * 500 * 3


def test_a_line_over_the_limit_does_not_block_the_rest(monkeypatch, world, caplog):
    google, table = world
    huge = paragraph(0, LIMIT + 1)
    use_texts(monkeypatch, huge, paragraph(1, 100), paragraph(2, 100))
    run_days(google)
    for language in LANGUAGES:
        assert set(table.translated(language)) == {paragraph(1, 100), paragraph(2, 100)}
    assert all(len(q) <= LIMIT for _lang, q in google.accepted)
    assert "stays Chinese" in caplog.text


def test_a_failure_stops_the_run_after_one_refused_request(monkeypatch, world):
    google, _table = world
    use_texts(monkeypatch, paragraph(1, 100))
    google.used = LIMIT
    with pytest.raises(translator_google.TranslationError):
        i18n_store.sync_once()
    assert google.requests == 1


def test_lines_saved_by_another_process_are_not_sent_again(monkeypatch, world):
    google, table = world
    first, second = paragraph(1, 1_500), paragraph(2, 1_500)
    use_texts(monkeypatch, first, second)
    real_post = google.post

    def post_and_race(*args, **kwargs):
        # while the first request runs, another process saves the second line
        table.execute("insert", (i18n_store._hash(second), "en", second, "other"))
        return real_post(*args, **kwargs)

    monkeypatch.setattr(translator_google.requests, "post", post_and_race)
    i18n_store.sync_once()
    assert [q for lang, q in google.accepted if lang == "en"] == [first]


def test_request_cost_includes_brand_name_markup():
    line = "滿月鑽石" * 100
    groups = list(i18n_store._requests([line, line + "。"], "en"))
    assert len(line) < i18n_store._REQUEST_CHARS and len(groups) == 2
