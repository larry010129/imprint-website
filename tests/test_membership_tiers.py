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


# ── card number (卡面編號): 11 digits from the id + 1 Luhn check digit ──────

import json
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from app.membership_tiers import is_valid_member_number, luhn_check_digit

SAMPLE_ID = "550e8400-e29b-41d4-a716-446655440000"


def test_card_number_known_value():
    # Pinned: changing the rule changes every member's printed number.
    assert derive_member_display_number(SAMPLE_ID) == "769814056966"
    assert format_member_id_groups(SAMPLE_ID) == "7698 1405 6966"


def test_card_number_ends_with_a_valid_check_digit():
    for _ in range(200):
        number = derive_member_display_number(str(uuid.uuid4()))
        assert len(number) == 12 and number.isdigit()
        assert is_valid_member_number(number)
        assert luhn_check_digit(number[:11]) == int(number[11])


def test_any_single_wrong_digit_is_rejected():
    number = derive_member_display_number(SAMPLE_ID)
    for position in range(12):
        for digit in "0123456789":
            if digit == number[position]:
                continue
            typo = number[:position] + digit + number[position + 1:]
            assert not is_valid_member_number(typo), typo


def test_swapped_neighbours_are_rejected_except_09_and_90():
    number = derive_member_display_number(SAMPLE_ID)
    for i in range(11):
        if number[i] == number[i + 1]:
            continue
        swapped = number[:i] + number[i + 1] + number[i] + number[i + 2:]
        if {number[i], number[i + 1]} == {"0", "9"}:
            continue
        assert not is_valid_member_number(swapped)


def test_is_valid_member_number_accepts_spacing_and_rejects_bad_shapes():
    number = derive_member_display_number(SAMPLE_ID)
    assert is_valid_member_number(" ".join(number[i:i + 4] for i in range(0, 12, 4)))
    assert is_valid_member_number("-".join(number[i:i + 4] for i in range(0, 12, 4)))
    for bad in ("", "abc", number[:11], number + "0", "1234 5678 90ab"):
        assert not is_valid_member_number(bad)


def test_non_hex_ids_still_get_a_valid_number():
    number = derive_member_display_number("not-a-uuid-at-all")
    assert is_valid_member_number(number)
    assert derive_member_display_number("not-a-uuid-at-all") == number


NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_python_and_admin_javascript_produce_the_same_numbers():
    """The admin screens recalculate the number in JS; it must match the server."""
    ids = [SAMPLE_ID] + [str(uuid.uuid4()) for _ in range(40)]
    source = Path(__file__).resolve().parents[1] / "public" / "js" / "admin-accounts.js"
    script = (
        "global.window = {}; global.document = {};"
        f"eval(require('fs').readFileSync({json.dumps(str(source))}, 'utf8'));"
        f"const ids = {json.dumps(ids)};"
        "console.log(JSON.stringify(ids.map(id => ["
        "window.ImprintMemberId.deriveMemberDisplayNumber(id),"
        "window.ImprintMemberId.formatMemberDisplayGroups(id),"
        "window.ImprintMemberId.isValidMemberNumber(window.ImprintMemberId.deriveMemberDisplayNumber(id)),"
        "window.ImprintMemberId.isValidMemberNumber('000000000001')])));"
    )
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    rows = json.loads(out.stdout)
    for member_id, (number, groups, valid, bogus_valid) in zip(ids, rows):
        assert number == derive_member_display_number(member_id)
        assert groups == format_member_id_groups(member_id)
        assert valid is True
        assert bogus_valid is False
