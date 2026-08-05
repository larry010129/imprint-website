"""Unit tests for gold-refresh body parsing (no DB)."""

from __future__ import annotations

from pathlib import Path

from app.controllers.api_controller import _quote_fields_from_payload

_ROOT = Path(__file__).resolve().parents[1]


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


def test_gold_price_js_refresh_posts_public_bot_gold_refresh() -> None:
    """Browser refresh POSTs /api/bot-gold/refresh (public), not secret /api/gold-refresh."""
    js = (_ROOT / "public" / "js" / "gold-price.js").read_text(encoding="utf-8")
    assert "REFRESH_URL = '/api/bot-gold/refresh'" in js
    assert "method: 'POST'" in js
    assert "fetch(REFRESH_URL" in js
    # Must not POST the GHA secret endpoint from the browser button.
    assert "REFRESH_URL = '/api/gold-refresh'" not in js
    assert "gold-price.js?v=20" in (
        _ROOT / "content" / "site" / "templates" / "pages" / "gold-price.html"
    ).read_text(encoding="utf-8")


def test_fetch_bot_gold_quote_force_bypasses_memory_ttl() -> None:
    import asyncio
    from unittest.mock import AsyncMock, patch

    from app import bot_gold

    bot_gold.invalidate_bot_gold_memory_cache()
    live = AsyncMock(return_value={"quote": {"sell": 1.0}, "metals": {"XAU": 1.0}})
    with patch.object(bot_gold, "_fetch_bot_gold_quote_live", live):
        asyncio.run(bot_gold.fetch_bot_gold_quote(force=False))
        asyncio.run(bot_gold.fetch_bot_gold_quote(force=False))
        assert live.await_count == 1
        asyncio.run(bot_gold.fetch_bot_gold_quote(force=True))
        assert live.await_count == 2
    bot_gold.invalidate_bot_gold_memory_cache()
