"""Profile table helpers — idempotent column ensure + safe reads before migrations run."""

from __future__ import annotations

import psycopg

from app.database import get_connection

_ADDRESS_COLUMNS = (
    ("shipping_postal", "text"),
    ("shipping_city", "text"),
    ("shipping_address", "text"),
)


def ensure_profile_address_columns() -> None:
    with get_connection() as conn, conn.cursor() as cur:
        for name, col_type in _ADDRESS_COLUMNS:
            cur.execute(f"alter table profiles add column if not exists {name} {col_type}")


def fetch_profile(cur, user_id: str) -> dict | None:
    try:
        cur.execute(
            """
            select full_name, phone, store_name, is_partner,
                   shipping_postal, shipping_city, shipping_address
            from profiles where id = %s
            """,
            (user_id,),
        )
        return cur.fetchone()
    except psycopg.errors.UndefinedColumn:
        cur.execute(
            "select full_name, phone, store_name, is_partner from profiles where id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            **row,
            "shipping_postal": None,
            "shipping_city": None,
            "shipping_address": None,
        }
