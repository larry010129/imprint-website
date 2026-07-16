#!/usr/bin/env python3
"""Apply backend/schema.sql to DATABASE_URL (Supabase or any Postgres)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "backend" / "schema.sql"

load_dotenv(ROOT / ".env")


def parse_statements(text: str) -> list[str]:
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("--")]
    body = "\n".join(lines)
    return [s.strip() for s in body.split(";") if s.strip()]


def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("DATABASE_URL is not set")

    statements = parse_statements(SCHEMA.read_text(encoding="utf-8"))
    print(f"Applying {len(statements)} SQL statement(s) to Supabase/Postgres…")

    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            for i, stmt in enumerate(statements, start=1):
                try:
                    cur.execute(stmt)
                except Exception as exc:
                    print(f"Failed on statement {i}: {stmt[:80]}…")
                    raise exc

    print("Schema applied.")


if __name__ == "__main__":
    main()
