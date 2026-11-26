"""Machine translations of public CMS / database content.

Saved translations are shown whenever a database is configured. New ones are
requested only when GOOGLE_TRANSLATE_API_KEY is set. The table is created only by the
migration in supabase/migrations, never by the app. Only the published, public
columns listed below are ever sent to Google: no orders, accounts,
addresses, customer names or messages. To stay inside the free tier, set a
daily character quota in Google Cloud (the app does not cap spending).

Work is done line by line and saved after every request, so reaching that
quota loses nothing: the next run continues with what is still missing.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from time import monotonic

from app import translator_google

log = logging.getLogger(__name__)

_PUBLIC_QUERIES = (
    "select title, body from journal_posts where is_published",
    "select title from faq_categories",
    "select question, answer from faq_items where is_published",
    "select text, role from testimonials where is_published",
    "select eyebrow, title, lead, image_alt, cta_primary_label, cta_secondary_label"
    " from home_banners where is_published",
    "select image_alt from page_images where is_published",
    "select text_value from page_copy_slots where is_published",
    "select title, meta_description from cms_pages where status = 'published'",
    "select s.props from cms_page_sections s join cms_pages p on p.id = s.page_id"
    " where s.is_visible and p.status = 'published'",
    "select name_zh, description_zh from products where is_published",
    "select label_zh from product_categories",
)
# Section props that hold links, ids or layout settings rather than wording.
_SKIP_PROP_KEYS = frozenset(
    {"id", "href", "cta_href", "cta_secondary_href", "image_url", "kind", "mode",
     "layout", "anchor", "size", "category_id"}
)
_CACHE_SECONDS = 60
# Match the "characters per day" quota set in Google Cloud. A single line
# bigger than this can never be sent, so it is skipped (and stays Chinese).
_DAILY_CHARS = 16_000
# One request, saved before the next: small, so little is left unused or lost.
_REQUEST_CHARS = 2_000
_REQUEST_LINES = 50

_lock = threading.Lock()
_sync_lock = threading.Lock()
_cache: dict[str, tuple[float, int, dict[str, str]]] = {}
_last_sync = float("-inf")
_pending = threading.Event()


def enabled() -> bool:
    return translator_google.is_configured()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load(language: str) -> tuple[int, dict[str, str]]:
    if not os.environ.get("DATABASE_URL", "").strip():
        return 0, {}
    with _lock:
        cached = _cache.get(language)
        if cached and monotonic() - cached[0] < _CACHE_SECONDS:
            return cached[1], cached[2]
    entries = cached[2] if cached else {}
    try:
        from app.database import get_connection

        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select source, translated from i18n_translations where lang = %s",
                (language,),
            )
            entries = {row["source"]: row["translated"] for row in cur.fetchall()}
    except Exception:  # missing table or database down: Chinese stays visible
        log.warning("saved translations unavailable", exc_info=True)
    version = hash(frozenset(entries.items()))
    with _lock:
        _cache[language] = (monotonic(), version, entries)
    return version, entries


def forget(language: str) -> None:
    """Drop the cached copy so the next page view reads the table again."""
    with _lock:
        _cache.pop(language, None)


def saved_version(language: str) -> int:
    return _load(language)[0]


def saved_entries(language: str) -> dict[str, str]:
    return _load(language)[1]


def _strings(value, key: str = ""):
    if isinstance(value, str):
        if key not in _SKIP_PROP_KEYS:
            yield value
    elif isinstance(value, dict):
        for child_key, child in value.items():
            yield from _strings(child, child_key)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child, key)


def _pieces(column: str, text: str):
    """The text nodes a page will show for one stored value."""
    if column == "answer":  # FAQ answers are split around revived links
        from app.content import format_faq_answer_html
        from app.i18n import translate_html

        yield from translate_html(format_faq_answer_html(text), {})[1]
        return
    yield text


def collect_public_texts(cur) -> dict[str, list[str]]:
    """Chinese texts from published public content: {page key: source lines}."""
    from app.i18n import _HAN_RE, normalize_segment

    found: dict[str, list[str]] = {}

    def add(raw: str) -> None:
        key = normalize_segment(raw)
        if not key or not _HAN_RE.search(key):
            return
        lines = [normalize_segment(line) for line in raw.splitlines()]
        found[key] = [line for line in lines if line] or [key]
        # Some layouts show each line as its own paragraph.
        if len(found[key]) > 1:
            for line in found[key]:
                if _HAN_RE.search(line):
                    found.setdefault(line, [line])

    for query in _PUBLIC_QUERIES:
        cur.execute(query)
        for row in cur.fetchall():
            for column, value in row.items():
                if column == "props" and isinstance(value, str):
                    value = json.loads(value)
                for text in _strings(value, "" if column == "props" else column):
                    for piece in _pieces(column, text):
                        add(piece)
    return found


def _requests(lines: list[str], language: str):
    """Group lines, in order, into requests. Lines too big to ever fit are left out."""
    group: list[str] = []
    size = 0
    for line in lines:
        # What Google counts, including the markup that protects brand names.
        cost = len(translator_google.protect_terms(line, language))
        if cost > _DAILY_CHARS:
            log.warning(
                "one line (%s characters) is over the daily limit and stays Chinese", cost
            )
            continue
        if group and (len(group) >= _REQUEST_LINES or size + cost > _REQUEST_CHARS):
            yield group
            group, size = [], 0
        group.append(line)
        size += cost
    if group:
        yield group


def _saved_pairs(language: str, hashes: list[str] | None = None) -> dict[str, str]:
    """Saved {Chinese: translation}, optionally only for the given hashes."""
    from app.database import get_connection

    query = "select source, translated from i18n_translations where lang = %s"
    params: list = [language]
    if hashes is not None:
        query += " and source_hash = any(%s)"
        params.append(hashes)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        return {row["source"]: row["translated"] for row in cur.fetchall()}


def _save(language: str, rows: list[tuple[str, str]]) -> int:
    from app.database import get_connection

    if rows:
        with get_connection() as conn, conn.cursor() as cur:
            for source, target in rows:
                cur.execute(
                    "insert into i18n_translations"
                    " (source_hash, lang, source, translated)"
                    " values (%s, %s, %s, %s)"
                    " on conflict (source_hash, lang) do nothing",
                    (_hash(source), language, source, target),
                )
        with _lock:
            _cache.pop(language, None)
    return len(rows)


def _assemble(
    waiting: dict[str, list[str]], known: dict[str, str]
) -> list[tuple[str, str]]:
    """Build multi-line rows whose lines are all translated; removes them from waiting."""
    from app.i18n import _HAN_RE

    ready = [
        key for key, parts in waiting.items()
        if all(line in known or not _HAN_RE.search(line) for line in parts)
    ]
    # Lines without Chinese are kept as they are and never sent.
    return [
        (key, "\n".join(known.get(line, line) for line in waiting.pop(key)))
        for key in ready
    ]


def _sync_language(language: str, texts: dict[str, list[str]]) -> int:
    from app.i18n import _HAN_RE, load_entries

    committed = load_entries(language)
    stored = _saved_pairs(language)
    known = {**stored, **committed}
    todo = {k: v for k, v in texts.items() if k not in known}
    # Multi-line rows are put together from their lines, which saves quota and
    # lets a post bigger than the daily limit finish over several days.
    waiting = {k: v for k, v in todo.items() if v != [k]}
    lines = list(dict.fromkeys(
        line for parts in todo.values() for line in parts
        if line not in known and _HAN_RE.search(line)
    ))
    saved = _save(language, _assemble(waiting, known))
    for group in _requests(lines, language):
        # Another server process may have saved some of these meanwhile.
        known.update(_saved_pairs(language, [_hash(line) for line in group]))
        group = [line for line in group if line not in known]
        if group:
            # A failure (such as the daily quota) stops here; all earlier work is saved.
            done = translator_google.translate_texts(group, language)
            saved += _save(language, list(zip(group, done)))
            known.update(zip(group, done))
        saved += _save(language, _assemble(waiting, known))
    return saved


def sync_once() -> int:
    """Translate public texts that have no translation yet. Returns rows saved."""
    from app.database import get_connection
    from app.i18n import LOCALES

    with get_connection() as conn, conn.cursor() as cur:
        texts = collect_public_texts(cur)
    return sum(_sync_language(language, texts) for language in LOCALES)


def _worker() -> None:
    try:
        while _pending.is_set():
            _pending.clear()
            try:
                count = sync_once()
                if count:
                    log.info("translated %s public text(s)", count)
            except Exception:  # retried by the next save or visit
                log.warning("translation sync failed; Chinese stays visible", exc_info=True)
    finally:
        _sync_lock.release()


def request_sync(min_interval: float = 0) -> None:
    """Start a background sync; never blocks or fails the current request."""
    global _last_sync
    if not enabled() or monotonic() - _last_sync < min_interval:
        return
    _last_sync = monotonic()
    _pending.set()  # a save during a running sync is picked up afterwards
    if _sync_lock.acquire(blocking=False):
        threading.Thread(target=_worker, name="i18n-sync", daemon=True).start()
