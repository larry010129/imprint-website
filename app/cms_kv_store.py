"""Shared CMS key/value store in Postgres.

Replaces per-environment JSON files (app/data/*.json, content/admin/*.json)
for CMS-edited payloads so an edit made on ANY environment is visible on
EVERY environment — the DB is the single shared store.

Semantics:
- Reads: DB first; when no row exists yet, one-time import from the legacy
  local JSON file (so committed seed data and pre-migration edits are kept).
  If the DB is unreachable, reads fall back to the legacy file with a loud
  error log (degraded mode — never used for writes).
- Writes: DB only. Failures raise — an admin save must never silently land
  in a local file that other environments cannot see.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

log = logging.getLogger(__name__)

_schema_lock = threading.Lock()
_schema_ready = False


def ensure_cms_kv_schema(cur=None) -> None:
    """Create the cms_kv table. Pass an open cursor or let it open one."""
    global _schema_ready
    ddl = (
        """
        create table if not exists cms_kv (
          key text primary key,
          value jsonb not null,
          updated_at timestamptz not null default now()
        )
        """
    )
    if cur is not None:
        cur.execute(ddl)
        _schema_ready = True
        return
    with _schema_lock:
        from app.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as c:
                c.execute(ddl)
        _schema_ready = True


def _ensure_schema_once() -> None:
    if _schema_ready:
        return
    ensure_cms_kv_schema()


def kv_get(key: str) -> dict[str, Any] | None:
    """Return the stored payload for key, or None when absent. Raises on DB errors."""
    from app.database import get_connection

    _ensure_schema_once()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("select value from cms_kv where key = %s", (key,))
            row = cur.fetchone()
    if not row:
        return None
    value = row.get("value") if isinstance(row, dict) else row[0]
    return value if isinstance(value, dict) else None


def kv_set(key: str, value: dict[str, Any]) -> None:
    """Upsert payload. Raises on DB errors so admin saves fail loudly."""
    from psycopg.types.json import Jsonb

    from app.database import get_connection

    _ensure_schema_once()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into cms_kv (key, value, updated_at)
                values (%s, %s, now())
                on conflict (key) do update set value = excluded.value,
                  updated_at = now()
                """,
                (key, Jsonb(value)),
            )


def kv_get_or_import_file(
    key: str,
    legacy_loader: Callable[[], dict[str, Any] | None],
) -> dict[str, Any] | None:
    """DB value, importing the legacy local file into the DB on first read.

    legacy_loader returns the file payload (or None when no usable file).
    Import failures do not hide the legacy data — it is still returned.
    """
    try:
        stored = kv_get(key)
    except Exception:
        log.error(
            "cms_kv read failed for key=%s; falling back to legacy local file "
            "(this environment cannot see edits made elsewhere until the DB "
            "is reachable)",
            key,
            exc_info=True,
        )
        return legacy_loader()
    if stored is not None:
        return stored
    legacy = legacy_loader()
    if legacy is None:
        return None
    try:
        kv_set(key, legacy)
        log.info("cms_kv imported legacy local file into DB key=%s", key)
    except Exception:
        log.error(
            "cms_kv import of legacy file failed for key=%s; serving legacy "
            "data but edits will NOT sync until the DB is reachable",
            key,
            exc_info=True,
        )
    return legacy
