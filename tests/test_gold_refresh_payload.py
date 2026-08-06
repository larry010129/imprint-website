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


_SCHEDULE_ZH = (
    "伺服器約每 30 分鐘更新牌價；本頁開啟時約每 25 秒重新讀取。無法取得時沿用最近一次牌價。"
)
_SCHEDULE_EN = (
    "Server refreshes quotes about every 30 minutes; "
    "this page re-reads about every 25 seconds while open. "
    "The last known quote is kept if a fetch fails."
)


def test_gold_price_js_refresh_posts_public_bot_gold_refresh() -> None:
    """Browser refresh POSTs /api/bot-gold/refresh (public), not secret /api/gold-refresh."""
    js = (_ROOT / "public" / "js" / "gold-price.js").read_text(encoding="utf-8")
    assert "REFRESH_URL = '/api/bot-gold/refresh'" in js
    assert "method: 'POST'" in js
    assert "fetch(REFRESH_URL" in js
    # Must not POST the GHA secret endpoint from the browser button.
    assert "REFRESH_URL = '/api/gold-refresh'" not in js
    assert "POLL_MS = 25 * 1000" in js
    assert "visibilityState" in js
    assert "fetchGoldQuote()" in js
    # Soft poll is GET (fetchGoldQuote → fetchLiveQuote), not POST refresh.
    soft_start = js.index("function softPoll")
    soft_end = js.index("function stopPoll", soft_start)
    soft_block = js[soft_start:soft_end]
    assert "fetchGoldQuote()" in soft_block
    assert "refreshGoldQuote" not in soft_block
    assert "REFRESH_URL" not in soft_block
    assert "fetch(API_URL" in js
    assert "gold-price.js?v=24" in (
        _ROOT / "content" / "site" / "templates" / "pages" / "gold-price.html"
    ).read_text(encoding="utf-8")
    assert "gold-price.js?v=24" in (
        _ROOT / "content" / "site" / "page-registry.json"
    ).read_text(encoding="utf-8")


def test_shop_js_live_gold_poll_get_and_cache_bust() -> None:
    shop = (_ROOT / "public" / "js" / "shop.js").read_text(encoding="utf-8")
    assert "GOLD_POLL_MS = 25 * 1000" in shop
    assert "shopApiFetch('/api/bot-gold')" in shop
    assert "setLiveGoldRates" in shop
    assert "initLiveGoldPoll" in shop
    assert "visibilityState" in shop
    assert "shop.js?v=142" in (
        _ROOT / "content" / "site" / "templates" / "pages" / "shop" / "calculator.html"
    ).read_text(encoding="utf-8")
    assert "shop.js?v=142" in (
        _ROOT / "content" / "site" / "page-registry.json"
    ).read_text(encoding="utf-8")


def test_gold_schedule_copy_zh_en_aligned() -> None:
    gold_html = (
        _ROOT / "content" / "site" / "templates" / "pages" / "gold-price.html"
    ).read_text(encoding="utf-8")
    body = (_ROOT / "content" / "site" / "bodies" / "gold-price_html.html").read_text(
        encoding="utf-8"
    )
    i18n = (_ROOT / "public" / "js" / "shop-i18n.js").read_text(encoding="utf-8")
    assert _SCHEDULE_ZH in gold_html
    assert _SCHEDULE_ZH in body
    assert _SCHEDULE_ZH in i18n
    assert _SCHEDULE_EN in i18n


def test_lifespan_starts_and_cancels_gold_scrape_task() -> None:
    init_src = (_ROOT / "app" / "__init__.py").read_text(encoding="utf-8")
    assert "gold_scrape_loop" in init_src
    assert 'name="imprint-gold-scrape"' in init_src
    assert "gold_task.cancel()" in init_src


def test_get_bot_gold_skips_scrape_when_cache_present() -> None:
    api = (_ROOT / "app" / "controllers" / "api_controller.py").read_text(encoding="utf-8")
    assert 'async def bot_gold()' in api
    start = api.index("async def bot_gold()")
    end = api.index("async def bot_gold_refresh", start)
    body = api[start:end]
    assert "_gold_cache_row()" in body
    assert 'xau_per_gram") or 0) > 0' in body
    assert "return _bot_gold_from_row(row)" in body
    # Scrape only on empty/invalid cache bootstrap.
    assert body.index("return _bot_gold_from_row(row)") < body.index(
        "scrape_and_persist_gold"
    )


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
