"""Database connection — Supabase Postgres via psycopg + ConnectionPool.

Small process-local pool reuses TCP/TLS sessions. Keep max_size low so this stays
compatible with Supabase **Session pooler** (port 5432) and Direct connections.
Do not point DATABASE_URL at Transaction pooler (6543) for this long-lived app.

See docs/SUPABASE.md.
"""

from __future__ import annotations

import atexit
import logging
import os
import threading
from contextlib import contextmanager
from collections.abc import Iterator
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

log = logging.getLogger(__name__)

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})
# Direct: db.<ref>.supabase.co ; Session/Transaction: *.pooler.supabase.com
_SUPABASE_HOST_MARKERS = (".supabase.co", ".pooler.supabase.com")

_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


def _is_supabase_postgres_host(host: str) -> bool:
    h = (host or "").lower().rstrip(".")
    if not h:
        return False
    return any(h == m.lstrip(".") or h.endswith(m) for m in _SUPABASE_HOST_MARKERS)


def require_database_url() -> str:
    """Return DATABASE_URL or raise. Supabase Postgres only — no Neon / SQLite."""
    dsn = (os.environ.get("DATABASE_URL") or "").strip()
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL is not set — configure Supabase Postgres "
            "(Project Settings → Database → Connection string). "
            "This app does not use local SQLite or in-memory stores."
        )
    parsed = urlparse(dsn)
    scheme = parsed.scheme.lower()
    if scheme.startswith("sqlite") or scheme in {"file", ""}:
        raise RuntimeError(
            f"DATABASE_URL scheme {scheme!r} is not supported — use postgresql:// "
            "(or postgres://) for Supabase Postgres."
        )
    if not scheme.startswith("postgres"):
        raise RuntimeError(
            f"DATABASE_URL must be postgres/postgresql, got scheme {scheme!r}"
        )
    host = (parsed.hostname or "").lower()
    if "neon.tech" in host:
        # Temporary: allow boot on legacy Neon URI until DATABASE_URL is
        # switched to Supabase. Prefer fixing .env over keeping this path.
        log.warning(
            "DATABASE_URL points at Neon (neon.tech). This app targets "
            "Supabase Postgres only. Paste a Session pooler or Direct URI "
            "into .env DATABASE_URL, then restart. Project erobemoojyptyxvnyvuf "
            "(ap-northeast-1):\n"
            "  Session: postgresql://postgres.erobemoojyptyxvnyvuf:"
            "[PASSWORD]@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres\n"
            "  Direct:  postgresql://postgres:[PASSWORD]@"
            "db.erobemoojyptyxvnyvuf.supabase.co:5432/postgres\n"
            "Dashboard → Project Settings → Database → Connection string "
            "(Session, port 5432). See .env.example and docs/SUPABASE.md."
        )
        return dsn
    if not _is_supabase_postgres_host(host):
        raise RuntimeError(
            f"DATABASE_URL host {host!r} is not Supabase Postgres. "
            "Use db.[PROJECT_REF].supabase.co (Direct) or "
            "aws-0-[REGION].pooler.supabase.com (Session, port 5432)."
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


def _pool_sizes() -> tuple[int, int]:
    """min/max connections. Cap max for Session pooler headroom across workers."""
    try:
        min_size = max(1, int(os.environ.get("DB_POOL_MIN", "1")))
    except ValueError:
        min_size = 1
    try:
        max_size = max(min_size, int(os.environ.get("DB_POOL_MAX", "4")))
    except ValueError:
        max_size = max(min_size, 4)
    return min_size, max_size


def _reset_conn(conn: psycopg.Connection) -> None:
    """Return connections to a clean autocommit state for the next checkout."""
    if conn.closed:
        return
    try:
        if not conn.autocommit:
            conn.rollback()
            conn.autocommit = True
    except Exception:
        log.debug("pool reset failed; connection will be discarded", exc_info=True)
        raise


def _ensure_pool() -> ConnectionPool:
    global _pool
    if _pool is not None and not _pool.closed:
        return _pool
    with _pool_lock:
        if _pool is not None and not _pool.closed:
            return _pool
        dsn = require_database_url()
        min_size, max_size = _pool_sizes()
        _pool = ConnectionPool(
            conninfo=dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row, "autocommit": True},
            check=ConnectionPool.check_connection,
            reset=_reset_conn,
            open=True,
            # Recycle before idle Session-pooler timeouts bite.
            max_lifetime=1800.0,
            max_idle=300.0,
            name="imprint",
        )
        return _pool


def close_pool() -> None:
    """Close the process pool (app shutdown / tests)."""
    global _pool
    with _pool_lock:
        pool = _pool
        _pool = None
    if pool is not None and not pool.closed:
        pool.close()


atexit.register(close_pool)


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Checkout a pooled autocommit connection."""
    with _ensure_pool().connection() as conn:
        if not conn.autocommit:
            conn.autocommit = True
        yield conn


@contextmanager
def get_transaction() -> Iterator[psycopg.Connection]:
    """Like get_connection, but for call sites that issue several dependent
    writes that must all succeed or all fail together (e.g. checkout inserting
    N orders then clearing the cart, or admin product saves that replace
    variants/images). autocommit is off, so `with get_transaction() as conn:`
    commits once on clean exit and rolls back everything on an exception."""
    with _ensure_pool().connection() as conn:
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                log.debug("transaction rollback failed", exc_info=True)
            raise
        finally:
            try:
                if not conn.closed:
                    conn.autocommit = True
            except Exception:
                pass
