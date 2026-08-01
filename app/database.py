"""Database connection — Supabase/Neon Postgres via psycopg.

A fresh connection per call, not a pool: this app runs as a single Render
free-tier instance with light traffic, so pool lifecycle management (and its
failure modes across gunicorn workers) isn't worth the complexity yet. Revisit
if/when that stops being true.

Use Supabase **Direct connection** or **Session pooler** (port 5432) in
DATABASE_URL for this long-lived FastAPI process. See docs/SUPABASE.md.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})


def require_database_url() -> str:
    """Return DATABASE_URL or raise. No SQLite / file / silent local fallback."""
    dsn = (os.environ.get("DATABASE_URL") or "").strip()
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL is not set — configure Postgres (Neon/Supabase). "
            "This app does not use local SQLite or in-memory stores."
        )
    scheme = urlparse(dsn).scheme.lower()
    if scheme.startswith("sqlite") or scheme in {"file", ""}:
        raise RuntimeError(
            f"DATABASE_URL scheme {scheme!r} is not supported — use postgresql:// "
            "(or postgres://) for remote Postgres."
        )
    if not scheme.startswith("postgres"):
        raise RuntimeError(
            f"DATABASE_URL must be postgres/postgresql, got scheme {scheme!r}"
        )
    return dsn


def database_target_label(dsn: str | None = None) -> str:
    """Safe host/db label for logs (never includes password)."""
    raw = dsn if dsn is not None else (os.environ.get("DATABASE_URL") or "")
    try:
        u = urlparse(raw)
    except Exception:
        return "(unparseable DATABASE_URL)"
    host = (u.hostname or "?").lower()
    db = (u.path or "/").lstrip("/") or "?"
    port = f":{u.port}" if u.port else ""
    tag = "local" if host in _LOCAL_HOSTS else "remote"
    return f"{tag} postgres {host}{port}/{db}"


def get_connection() -> psycopg.Connection:
    dsn = require_database_url()
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=True)


def get_transaction() -> psycopg.Connection:
    """Like get_connection, but for call sites that issue several dependent
    writes that must all succeed or all fail together (e.g. checkout inserting
    N orders then clearing the cart, or admin product saves that replace
    variants/images). autocommit is off, so `with get_transaction() as conn:`
    commits once on clean exit and rolls back everything on an exception."""
    dsn = require_database_url()
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=False)
