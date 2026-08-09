#!/usr/bin/env python3
"""Copy public table data from Neon (SOURCE) into Supabase (DATABASE_URL).

Usage:
  set NEON_DATABASE_URL=...   # or place DSN in scripts/_neon_dsn.tmp
  python scripts/migrate_neon_to_supabase.py [--dry-run]

Does not drop Supabase data: uses INSERT ... ON CONFLICT DO NOTHING by PK
when a primary key exists; otherwise skips empty-target-only full copy for
tables without PK if target already has rows.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(__file__).resolve().parent / "_neon_dsn.tmp"

load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))
from app.database import require_database_url  # noqa: E402

# Parent → child order for FK safety (parents first).
TABLE_ORDER = [
    "users",
    "profiles",
    "staff_admins",
    "password_reset_tokens",
    "login_lockouts",
    "invite_codes",
    "product_categories",
    "products",
    "product_variants",
    "product_images",
    "pricing_settings",
    "gold_price_cache",
    "membership_settings",
    "coupons",
    "orders",
    "order_contacts",
    "order_fulfillment",
    "order_items",
    "coupon_redemptions",
    "cart_items",
    "favorite_items",
    "user_notifications",
    "contact_messages",
    "quote_requests",
    "audit_log",
    "testimonials",
    "faq_categories",
    "faq_items",
    "home_banners",
    "page_images",
    "page_copy_slots",
    "cms_pages",
    "cms_page_sections",
    "cms_media",
    "journal_posts",
    "admin_plugins",
]


def _source_dsn() -> str:
    env = (os.environ.get("NEON_DATABASE_URL") or "").strip()
    if env:
        return env
    if TMP.exists():
        text = TMP.read_text(encoding="utf-8").strip()
        for line in text.splitlines():
            line = line.strip()
            if "ep-autumn-hill" in line and "postgresql://" in line:
                return line
        if text.startswith("postgresql://"):
            return text.splitlines()[0].strip()
    raise SystemExit("Set NEON_DATABASE_URL or scripts/_neon_dsn.tmp with Neon URI")


def _pk_cols(cur, table: str) -> list[str]:
    cur.execute(
        """
        select a.attname
        from pg_index i
        join pg_attribute a on a.attrelid = i.indrelid and a.attnum = any(i.indkey)
        where i.indrelid = %s::regclass and i.indisprimary
        order by array_position(i.indkey, a.attnum)
        """,
        (f"public.{table}",),
    )
    return [r["attname"] for r in cur.fetchall()]


def _cols(cur, table: str) -> list[str]:
    cur.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema = 'public' and table_name = %s
        order by ordinal_position
        """,
        (table,),
    )
    return [r["column_name"] for r in cur.fetchall()]


def _count(cur, table: str) -> int:
    cur.execute(f'select count(*) as c from public."{table}"')
    return int(cur.fetchone()["c"])


def _adapt(value):
    if isinstance(value, (dict, list)):
        return Jsonb(value)
    return value


def copy_table(src, dst, table: str, dry_run: bool) -> tuple[int, int, str]:
    with src.cursor(row_factory=dict_row) as sc, dst.cursor(row_factory=dict_row) as dc:
        if table not in _list_tables(sc) or table not in _list_tables(dc):
            return 0, 0, "missing"
        cols = [c for c in _cols(sc, table) if c in set(_cols(dc, table))]
        if not cols:
            return 0, 0, "no-common-cols"
        sc.execute(f'select count(*) as c from public."{table}"')
        src_n = int(sc.fetchone()["c"])
        if src_n == 0:
            return 0, _count(dc, table), "empty-source"
        pk = [c for c in _pk_cols(dc, table) if c in cols]
        col_sql = ", ".join(f'"{c}"' for c in cols)
        sc.execute(f'select {col_sql} from public."{table}"')
        rows = sc.fetchall()
        if dry_run:
            return len(rows), _count(dc, table), "dry-run"
        inserted = 0
        placeholders = ", ".join(f"%({c})s" for c in cols)
        if pk:
            conflict = ", ".join(f'"{c}"' for c in pk)
            sql = (
                f'insert into public."{table}" ({col_sql}) values ({placeholders}) '
                f"on conflict ({conflict}) do nothing"
            )
        else:
            if _count(dc, table) > 0:
                return 0, _count(dc, table), "skip-no-pk-target-nonempty"
            sql = f'insert into public."{table}" ({col_sql}) values ({placeholders})'
        for row in rows:
            payload = {c: _adapt(row[c]) for c in cols}
            dc.execute("savepoint mig_row")
            try:
                dc.execute(sql, payload)
                inserted += max(dc.rowcount, 0)
                dc.execute("release savepoint mig_row")
            except Exception:
                # Unique email / slug collisions across different PKs — skip row.
                dc.execute("rollback to savepoint mig_row")
                continue
        dst.commit()
        return inserted, _count(dc, table), "ok"


def _list_tables(cur) -> set[str]:
    cur.execute(
        """
        select tablename from pg_tables
        where schemaname = 'public' order by tablename
        """
    )
    return {r["tablename"] for r in cur.fetchall()}


def ensure_style_key(dst) -> None:
    """Schema gap that blocked apply_schema.py on Supabase."""
    with dst.cursor() as cur:
        cur.execute(
            "alter table products add column if not exists style_key text"
        )
        cur.execute(
            """
            create unique index if not exists products_style_key_uidx
              on products (style_key) where style_key is not null
            """
        )
    dst.commit()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    src_dsn = _source_dsn()
    dst_dsn = require_database_url()
    if "neon.tech" in dst_dsn:
        raise SystemExit("DATABASE_URL is still Neon — point .env at Supabase first")
    if "neon.tech" not in src_dsn:
        raise SystemExit("Source DSN is not Neon")

    print("Source: Neon")
    print("Target: Supabase")
    print("Mode:", "dry-run" if args.dry_run else "apply")

    with (
        psycopg.connect(src_dsn, connect_timeout=30, row_factory=dict_row) as src,
        psycopg.connect(dst_dsn, connect_timeout=30, row_factory=dict_row) as dst,
    ):
        if not args.dry_run:
            ensure_style_key(dst)
            with dst.cursor() as cur:
                # Bypass FK checks while bulk-loading Neon → Supabase.
                cur.execute("set session_replication_role = replica")
            dst.commit()
        with src.cursor(row_factory=dict_row) as sc:
            src_tables = _list_tables(sc)
        with dst.cursor(row_factory=dict_row) as dc:
            dst_tables = _list_tables(dc)
        skip_legacy = {
            "schema_migrations",
            "alembic_version",
            "cart_item",
            "favorite_item",
            "invite_code",
            "product",
            "product_image",
            "product_variant",
            "user",
            "user_notification",
            "submission",
            "memorial_diamond_style_tombstones",
        }
        ordered = [t for t in TABLE_ORDER if t in src_tables and t in dst_tables]
        extras = sorted((src_tables & dst_tables) - set(TABLE_ORDER) - skip_legacy)
        ordered.extend(extras)

        for table in ordered:
            try:
                inserted, dest_n, status = copy_table(src, dst, table, args.dry_run)
            except Exception as exc:
                print(f"{table}: ERROR {exc}")
                dst.rollback()
                if not args.dry_run:
                    with dst.cursor() as cur:
                        cur.execute("set session_replication_role = replica")
                    dst.commit()
                continue
            print(f"{table}: {status} inserted={inserted} dest_total={dest_n}")

        if not args.dry_run:
            with dst.cursor() as cur:
                cur.execute("set session_replication_role = origin")
            dst.commit()

    print("Done.")


if __name__ == "__main__":
    main()
