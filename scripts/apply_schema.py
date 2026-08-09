#!/usr/bin/env python3
"""Apply backend/schema.sql to DATABASE_URL (Supabase Postgres only)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "backend" / "schema.sql"

load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT))
from app.database import database_target_label, require_database_url  # noqa: E402


def parse_statements(text: str) -> list[str]:
    # Strip `--` comments (including trailing inline ones) before splitting on
    # `;` — a `;` inside a comment must not be treated as a statement terminator.
    lines = [re.sub(r"--.*$", "", ln) for ln in text.splitlines()]
    body = "\n".join(lines)
    return [s.strip() for s in body.split(";") if s.strip()]


def main() -> None:
    try:
        dsn = require_database_url()
    except RuntimeError as exc:
        sys.exit(str(exc))

    statements = parse_statements(SCHEMA.read_text(encoding="utf-8"))
    print(
        f"Applying {len(statements)} SQL statement(s) to "
        f"{database_target_label(dsn)}…"
    )

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
