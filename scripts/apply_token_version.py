"""Apply users.token_version if missing (login 500 without it)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.database import get_connection


def main() -> int:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            alter table users
            add column if not exists token_version integer not null default 0
            """
        )
        cur.execute(
            """
            select column_name from information_schema.columns
            where table_schema = 'public' and table_name = 'users'
              and column_name = 'token_version'
            """
        )
        row = cur.fetchone()
    if not row:
        print("FAILED: token_version still missing", file=sys.stderr)
        return 1
    print("OK: users.token_version ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
