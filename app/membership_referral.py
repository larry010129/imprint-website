"""Friend referral codes + imprint invite helpers."""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone

_ALPHABET = string.ascii_uppercase + string.digits


def generate_referral_code(cur, *, length: int = 8) -> str:
    for _ in range(24):
        code = "".join(secrets.choice(_ALPHABET) for _ in range(length))
        cur.execute(
            "select 1 from profiles where referral_code = %s limit 1",
            (code,),
        )
        if not cur.fetchone():
            return code
    return secrets.token_hex(6).upper()


def ensure_referral_code(cur, user_id) -> str:
    cur.execute("select referral_code from profiles where id = %s", (user_id,))
    row = cur.fetchone()
    if row and row.get("referral_code"):
        return str(row["referral_code"])
    code = generate_referral_code(cur)
    cur.execute(
        """
        update profiles
        set referral_code = %s
        where id = %s and (referral_code is null or referral_code = '')
        """,
        (code, user_id),
    )
    cur.execute("select referral_code from profiles where id = %s", (user_id,))
    again = cur.fetchone()
    return str((again or {}).get("referral_code") or code)


def resolve_referrer_id(cur, referral_code: str | None):
    code = (referral_code or "").strip().upper()
    if not code:
        return None
    cur.execute(
        "select id from profiles where upper(referral_code) = %s limit 1",
        (code,),
    )
    row = cur.fetchone()
    return row["id"] if row else None


def apply_friend_referral(cur, new_user_id, referral_code: str | None) -> bool:
    referrer_id = resolve_referrer_id(cur, referral_code)
    if not referrer_id or str(referrer_id) == str(new_user_id):
        return False
    cur.execute(
        """
        update profiles
        set referred_by = %s, referred_at = coalesce(referred_at, now())
        where id = %s and referred_by is null
        """,
        (referrer_id, new_user_id),
    )
    return cur.rowcount > 0


def count_invites_since(cur, user_id, since: datetime) -> int:
    cur.execute(
        """
        select count(*)::int as n
        from profiles
        where referred_by = %s
          and referred_at is not null
          and referred_at >= %s
        """,
        (user_id, since),
    )
    row = cur.fetchone()
    return int((row or {}).get("n") or 0)


def rolling_two_year_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now - timedelta(days=730)
