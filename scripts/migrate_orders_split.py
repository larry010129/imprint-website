#!/usr/bin/env python3
"""Apply order normalization migrations (idempotent)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = [
    ROOT / "supabase" / "migrations" / "20260718110000_order_items_split.sql",
    ROOT / "supabase" / "migrations" / "20260718120000_order_contacts_fulfillment.sql",
]

load_dotenv(ROOT / ".env")


def _has_column(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        select 1 from information_schema.columns
        where table_schema = 'public' and table_name = %s and column_name = %s
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("DATABASE_URL is not set")

    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            if _has_column(cur, "orders", "category") or _has_column(cur, "orders", "config_json"):
                cur.execute(MIGRATIONS[0].read_text(encoding="utf-8"))
                print("Applied:", MIGRATIONS[0].name)
            else:
                print("Skip:", MIGRATIONS[0].name, "(already split)")

            if _has_column(cur, "orders", "customer_name"):
                cur.execute(MIGRATIONS[1].read_text(encoding="utf-8"))
                print("Applied:", MIGRATIONS[1].name)
            else:
                cur.execute(
                    MIGRATIONS[1].read_text(encoding="utf-8").split("do $$")[0]
                )
                print("Ensured:", "order_contacts + order_fulfillment tables")

    print("Order normalization complete.")


if __name__ == "__main__":
    main()
