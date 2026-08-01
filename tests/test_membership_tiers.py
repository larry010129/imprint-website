"""Membership tier resolution — display helpers for HTMX account."""

from __future__ import annotations

from app.membership_config import default_config
from app.membership_tiers import (
    build_account_membership,
    derive_member_display_number,
    format_member_id_groups,
    resolve_tier_id,
)


def test_derive_member_display_number_is_twelve_digits():
    uid = "550e8400-e29b-41d4-a716-446655440000"
    number = derive_member_display_number(uid)
    assert len(number) == 12
    assert number.isdigit()
    assert derive_member_display_number(uid) == number


def test_format_member_id_groups():
    uid = "550e8400-e29b-41d4-a716-446655440000"
    number = derive_member_display_number(uid)
    assert format_member_id_groups(uid) == " ".join(number[i : i + 4] for i in range(0, 12, 4))


def test_resolve_ice_by_default():
    cfg = default_config()
    tier = resolve_tier_id(
        profile={"is_partner": False},
        orders=[],
        invite_count=0,
        is_admin=False,
        config=cfg,
    )
    assert tier == "ice"


def test_admin_gets_imprint_member_track():
    cfg = default_config()
    tier = resolve_tier_id(
        profile={"is_partner": False},
        orders=[],
        invite_count=0,
        is_admin=True,
        config=cfg,
    )
    assert tier == "imprint"


def test_build_account_membership_includes_ladder_data():
    cfg = default_config()
    ctx = build_account_membership(
        profile={"is_partner": False},
        orders=[{"status": "completed", "total_price": 60000, "created_at": "2026-01-15T00:00:00+00:00"}],
        invite_count=0,
        is_admin=False,
        config=cfg,
    )
    assert ctx["enabled"] is True
    assert ctx["tier_id"] in {"ice", "platinum", "rose", "star", "imprint"}
    assert len(ctx["plans"]) == 5
    assert ctx["feature_groups"]
