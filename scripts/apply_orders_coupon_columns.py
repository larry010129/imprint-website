"""Apply orders coupon/discount columns if missing (20260722180000_coupons.sql tail)."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.database import get_connection

STATEMENTS = (
    "alter table orders add column if not exists coupon_code text",
    "alter table orders add column if not exists discount_amount numeric not null default 0",
    "alter table orders add column if not exists subtotal_before_discount numeric",
)


def main() -> None:
    with get_connection() as conn, conn.cursor() as cur:
        for stmt in STATEMENTS:
            cur.execute(stmt)
        cur.execute(
            """
            select column_name from information_schema.columns
            where table_schema = 'public' and table_name = 'orders'
              and column_name in ('coupon_code', 'discount_amount', 'subtotal_before_discount')
            order by column_name
            """
        )
        cols = [row["column_name"] for row in cur.fetchall()]
    print("orders discount columns:", ", ".join(cols) or "(none)")


if __name__ == "__main__":
    main()
