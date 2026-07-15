"""Fetch + parse Bank of Taiwan 黃金條塊牌價 for /api/bot-gold."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from curl_cffi.requests import AsyncSession

from app.parse_bot_gold import find_gold_bar_prices, is_bot_challenge

# BOT only updates this quote a few times a day — re-scraping the live page on
# every /api/bot-gold hit was pure wasted network latency (and risked getting
# rate-limited upstream). Cache successful fetches for this long; failures are
# never cached, so a broken scrape keeps retrying on the next request.
_CACHE_TTL_SECONDS = 300
_cache_lock = asyncio.Lock()
_cached_payload: dict | None = None
_cached_at: float = 0.0

BOT_URLS = (
    "https://rate.bot.com.tw/gold/quote/recent",
    "https://rate.bot.com.tw/gold?Lang=zh-TW",
)

BOT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml",
}

PURITY_MULTIPLIER = {"9k": 0.5, "14k": 0.75, "18k": 0.85, "pt950": 1.1, "s925": 0.925}
METAL_BASE = {"9k": "XAU", "14k": "XAU", "18k": "XAU", "pt950": "XPT", "s925": "XAG"}
FALLBACK_XPT = 1050.0
FALLBACK_XAG = 30.0

TAIPEI = ZoneInfo("Asia/Taipei")


def build_alloy_rates(raw: dict[str, float]) -> dict[str, float]:
    alloy: dict[str, float] = {}
    for gold, multiplier in PURITY_MULTIPLIER.items():
        symbol = METAL_BASE[gold]
        if symbol in raw and raw[symbol] is not None:
            alloy[gold] = raw[symbol] * multiplier
    return alloy


def format_fetched_at(when: datetime) -> str:
    return when.astimezone(TAIPEI).strftime("%Y/%m/%d %H:%M:%S")


def build_payload(parsed: dict[str, float | str | None], source_url: str) -> dict:
    now = datetime.now(timezone.utc)
    per_gram = float(parsed["perGram"])
    raw = {"XAU": per_gram, "XPT": FALLBACK_XPT, "XAG": FALLBACK_XAG}
    return {
        "refreshed": True,
        "quote": {
            "available": True,
            "sell": per_gram,
            "source": "bot",
            "bot_posted_at": parsed.get("stamp"),
            "fetched_at": now.isoformat(),
            "fetched_at_display": format_fetched_at(now),
            "is_stale": False,
            "source_url": source_url,
        },
        "alloyRates": build_alloy_rates(raw),
    }


async def fetch_bot_gold_quote() -> dict:
    """Cached, O(1)-amortized wrapper: only hits the network once per TTL window."""
    global _cached_payload, _cached_at

    now = time.monotonic()
    if _cached_payload is not None and (now - _cached_at) < _CACHE_TTL_SECONDS:
        return _cached_payload

    async with _cache_lock:
        # Another request may have refreshed the cache while we waited on the lock.
        now = time.monotonic()
        if _cached_payload is not None and (now - _cached_at) < _CACHE_TTL_SECONDS:
            return _cached_payload

        payload = await _fetch_bot_gold_quote_live()
        _cached_payload = payload
        _cached_at = now
        return payload


async def _fetch_bot_gold_quote_live() -> dict:
    last_error: Exception | None = None
    async with AsyncSession(impersonate="chrome120") as client:
        for url in BOT_URLS:
            try:
                response = await client.get(url, headers=BOT_HEADERS, timeout=30)
                if response.status_code >= 400:
                    raise RuntimeError(f"HTTP {response.status_code}")
                html = response.text
                if is_bot_challenge(html):
                    raise RuntimeError("BOT challenge")
                parsed = find_gold_bar_prices(html)
                if not parsed:
                    raise RuntimeError("parse failed")
                return build_payload(parsed, url)
            except Exception as err:  # noqa: BLE001 — try next URL
                last_error = err
    raise last_error or RuntimeError("BOT scrape failed")
