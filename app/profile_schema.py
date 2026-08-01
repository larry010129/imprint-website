"""Profile table helpers — idempotent column ensure + safe reads before migrations run."""

from __future__ import annotations

import psycopg

from app.database import get_connection

_ADDRESS_COLUMNS = (
    ("shipping_postal", "text"),
    ("shipping_city", "text"),
    ("shipping_address", "text"),
)

_MEMBERSHIP_COLUMNS = (
    ("referral_code", "text"),
    ("referred_by", "uuid"),
    ("referred_at", "timestamptz"),
    ("imprint_invited", "boolean not null default false"),
    ("partner_imprint_invited", "boolean not null default false"),
    ("onboarding_completed_at", "timestamptz"),
)


def _backfill_onboarding_completed(cur) -> None:
    """Stamp legacy members who already filled required fields (remote-safe)."""
    cur.execute(
        """
        update profiles
        set onboarding_completed_at = coalesce(
          (select u.created_at from users u where u.id = profiles.id),
          now()
        )
        where onboarding_completed_at is null
          and nullif(btrim(coalesce(full_name, '')), '') is not null
          and nullif(btrim(coalesce(phone, '')), '') is not null
          and nullif(btrim(coalesce(shipping_postal, '')), '') is not null
          and nullif(btrim(coalesce(shipping_city, '')), '') is not null
          and nullif(btrim(coalesce(shipping_address, '')), '') is not null
        """
    )


def ensure_profile_address_columns() -> None:
    with get_connection() as conn, conn.cursor() as cur:
        for name, col_type in _ADDRESS_COLUMNS:
            cur.execute(f"alter table profiles add column if not exists {name} {col_type}")
        for name, col_type in _MEMBERSHIP_COLUMNS:
            cur.execute(f"alter table profiles add column if not exists {name} {col_type}")
        _backfill_onboarding_completed(cur)


def fetch_profile(cur, user_id: str) -> dict | None:
    try:
        cur.execute(
            """
            select full_name, phone, store_name, is_partner,
                   shipping_postal, shipping_city, shipping_address,
                   referral_code, referred_by, referred_at,
                   coalesce(imprint_invited, false) as imprint_invited,
                   coalesce(partner_imprint_invited, false) as partner_imprint_invited,
                   onboarding_completed_at
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
            "referral_code": None,
            "referred_by": None,
            "referred_at": None,
            "imprint_invited": False,
            "partner_imprint_invited": False,
            "onboarding_completed_at": None,
        }
