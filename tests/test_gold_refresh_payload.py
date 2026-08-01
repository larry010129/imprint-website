"""Unit tests for gold-refresh body parsing (no DB)."""

from __future__ import annotations

from app.controllers.api_controller import _quote_fields_from_payload


def test_quote_fields_from_gold_quote_json_shape() -> None:
    xau, xag, xpt, stamp, source = _quote_fields_from_payload(
        {
            "quote": {"sell": 4261.3, "bot_posted_at": "2026-08-01 11:08:13", "source": "allbeauty"},
            "metals": {"XAU": 4261.3, "XPT": 1888.0, "XAG": 60.4},
        }
    )
    assert xau == 4261.3
    assert xag == 60.4
    assert xpt == 1888.0
    assert stamp == "2026-08-01 11:08:13"
    assert source == "allbeauty"


def test_quote_fields_falls_back_metals_and_defaults() -> None:
    xau, xag, xpt, stamp, source = _quote_fields_from_payload(
        {"metals": {"XAU": 100.0}, "quote": {}}
    )
    assert xau == 100.0
    assert xag > 0  # FALLBACK_XAG
    assert xpt > 0  # FALLBACK_XPT
    assert stamp is None
    assert source == "allbeauty"
