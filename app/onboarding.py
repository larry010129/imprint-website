"""First-login profile onboarding — soft prompt when address fields incomplete."""

from __future__ import annotations

from fastapi import Request

from app.auth import is_admin
from app.database import get_connection
from app.profile_schema import fetch_profile

ONBOARDING_URL = "/profile.html?onboarding=1"
ONBOARD_LATER_COOKIE = "imprint_onboard_later"
ONBOARD_LATER_MAX_AGE = 60 * 60 * 24  # 24h
REQUIRED_PROFILE_FIELDS = (
    "full_name",
    "phone",
    "shipping_postal",
    "shipping_city",
    "shipping_address",
)


def profile_fields_complete(profile: dict | None) -> bool:
    if not profile:
        return False
    for key in REQUIRED_PROFILE_FIELDS:
        if not str(profile.get(key) or "").strip():
            return False
    return True


def is_onboarding_complete(profile: dict | None) -> bool:
    if not profile:
        return False
    if profile.get("onboarding_completed_at"):
        return True
    # Legacy members: fields filled before onboarding_completed_at existed.
    return profile_fields_complete(profile)


def needs_member_onboarding(user_id: str | None) -> bool:
    """True when a shop member still needs profile fields (staff admins skipped)."""
    if not user_id:
        return False
    if is_admin(user_id):
        return False
    with get_connection() as conn, conn.cursor() as cur:
        profile = fetch_profile(cur, user_id)
        if not is_onboarding_complete(profile):
            return True
        # Auto-stamp when required fields present but timestamp still null.
        mark_onboarding_complete_if_ready(cur, user_id, profile)
        return False


def has_onboard_later_cookie(request: Request) -> bool:
    val = (request.cookies.get(ONBOARD_LATER_COOKIE) or "").strip().lower()
    return val in ("1", "true", "yes")


def should_show_onboarding_prompt(request: Request, user_id: str | None) -> bool:
    """Soft popup when incomplete and member has not dismissed for this period."""
    if has_onboard_later_cookie(request):
        return False
    return needs_member_onboarding(user_id)


def mark_onboarding_complete_if_ready(cur, user_id: str, profile: dict | None = None) -> bool:
    """Set onboarding_completed_at when required fields present. Returns True if complete."""
    row = profile if profile is not None else fetch_profile(cur, user_id)
    if not profile_fields_complete(row):
        return False
    if row and row.get("onboarding_completed_at"):
        return True
    cur.execute(
        """
        update profiles
        set onboarding_completed_at = coalesce(onboarding_completed_at, now())
        where id = %s
        """,
        (user_id,),
    )
    return True
