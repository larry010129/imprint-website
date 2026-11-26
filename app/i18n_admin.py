"""List and correct saved machine translations (the CMS 「翻譯」 tab)."""

from __future__ import annotations

from app import i18n_store
from app.i18n import LOCALES, load_entries

MAX_TRANSLATION_CHARS = 100_000

_COLUMNS = "source_hash, lang, source, translated, edited_at"


def _like(text: str) -> str:
    """A "contains" pattern in which the typed % and _ are ordinary characters."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _public_row(row: dict) -> dict:
    return {
        "sourceHash": row["source_hash"],
        "lang": row["lang"],
        "source": row["source"],
        "translated": row["translated"],
        "edited": row["edited_at"] is not None,
    }


def list_translations(
    cur, *, language: str, search: str, limit: int, offset: int
) -> tuple[int, list[dict]]:
    """Saved translations that pages can still show. Returns (total, rows).

    Left out: rows for Chinese that has since changed or been unpublished, and
    rows whose wording the site's own files override (editing them does nothing).
    """
    committed = load_entries(language)
    shown = [
        i18n_store._hash(key)
        for key in i18n_store.collect_public_texts(cur)
        if key not in committed
    ]
    where = "lang = %s and source_hash = any(%s)"
    params: list = [language, shown]
    if search:
        where += " and (source ilike %s or translated ilike %s)"
        params += [_like(search), _like(search)]
    cur.execute(f"select count(*) as total from i18n_translations where {where}", params)
    total = cur.fetchone()["total"]
    cur.execute(
        f"select {_COLUMNS} from i18n_translations where {where}"
        " order by updated_at desc, source_hash limit %s offset %s",
        [*params, limit, offset],
    )
    return total, [_public_row(row) for row in cur.fetchall()]


def clean_update(body: dict) -> tuple[tuple[str, str, str] | None, str | None]:
    """Validate a save request: ((source_hash, language, text), None) or (None, error)."""
    source_hash = body.get("sourceHash")
    language = body.get("lang")
    text = body.get("translated")
    if language not in LOCALES:
        return None, "不支援的語言"
    if (
        not isinstance(source_hash, str)
        or len(source_hash) != 64
        or any(c not in "0123456789abcdef" for c in source_hash)
    ):
        return None, "找不到這筆翻譯"
    if not isinstance(text, str) or not text.strip():
        return None, "翻譯內容不可空白"
    text = text.replace("\r\n", "\n").strip()
    if len(text) > MAX_TRANSLATION_CHARS or "\x00" in text:
        return None, "翻譯內容太長或含無法儲存的字元"
    return (source_hash, language, text), None


def update_translation(cur, source_hash: str, language: str, text: str) -> dict | None:
    """Save a hand correction. The sync never overwrites an existing row."""
    cur.execute(
        "update i18n_translations"
        " set translated = %s, edited_at = now(), updated_at = now()"
        f" where source_hash = %s and lang = %s returning {_COLUMNS}",
        (text, source_hash, language),
    )
    row = cur.fetchone()
    return _public_row(row) if row else None
