"""Database connection — Supabase Postgres via psycopg.

A fresh connection per call, not a pool: this app runs as a single Render
free-tier instance with light traffic, so pool lifecycle management (and its
failure modes across gunicorn workers) isn't worth the complexity yet. Revisit
if/when that stops being true.

Use Supabase **Direct connection** or **Session pooler** (port 5432) in
DATABASE_URL for this long-lived FastAPI process. See docs/SUPABASE.md.
"""

from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row


def get_connection() -> psycopg.Connection:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set (Supabase Postgres connection string)")
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=True)
