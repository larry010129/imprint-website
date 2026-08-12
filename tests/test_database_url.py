"""DATABASE_URL must be Supabase Postgres — Neon / other hosts rejected."""

from __future__ import annotations

import pytest

from app.database import database_target_label, require_database_url


def test_require_database_url_accepts_supabase_direct(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:x@db.erobemoojyptyxvnyvuf.supabase.co:5432/postgres",
    )
    dsn = require_database_url()
    assert "supabase.co" in dsn
    label = database_target_label(dsn)
    assert "neon" not in label
    assert "erobemoojyptyxvnyvuf.supabase.co" in label


def test_require_database_url_accepts_session_pooler(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres.ref:x@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres",
    )
    assert "pooler.supabase.com" in require_database_url()


def test_require_database_url_rejects_neon(monkeypatch):
    neon = (
        "postgresql://user:pass@ep-x-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb"
    )
    monkeypatch.setenv("DATABASE_URL", neon)
    with pytest.raises(RuntimeError, match="Neon"):
        require_database_url()


def test_require_database_url_rejects_non_supabase_host(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:pass@db.example.com:5432/postgres",
    )
    with pytest.raises(RuntimeError, match="not Supabase"):
        require_database_url()


def test_require_database_url_rejects_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="not set"):
        require_database_url()
