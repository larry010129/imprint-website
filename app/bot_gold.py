"""Fetch + parse Allbeauty mobile gold board for /api/bot-gold.

Metals
------
- XAU: Allbeauty **黃金飾金** 售價 (元/錢 ÷ CHIN_TO_GRAMS → TWD/g)
- XPT: Allbeauty **白金 Pt950** 售價 (same conversion)
- XAG: Allbeauty **白銀條塊** 售價 (same conversion; S925 = XAG × 0.925)

API path `/api/bot-gold` kept for clients; upstream is no longer Bank of Taiwan.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from curl_cffi.requests import AsyncSession

from app.parse_bot_gold import find_gold_bar_prices, is_bot_challenge
from app.pricing import CHIN_TO_GRAMS, PURITY_MULTIPLIER as _PURITY_ALL

# In-process scrape TTL (refresh / lifespan). GET /api/bot-gold reads DB only.
_CACHE_TTL_SECONDS = 300
_cache_lock = asyncio.Lock()
_cached_payload: dict | None = None
_cached_at: float = 0.0

ALLBEAUTY_URLS = (
    "https://www.allbeauty.com.tw/m/",
)

SOURCE_NAME = "allbeauty"

BOT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml",
}

# Shop alloys only (aliases 999/pt/silver925 stay in app.pricing for orders).
PURITY_MULTIPLIER = {k: _PURITY_ALL[k] for k in ("9k", "14k", "18k", "pt950", "s925")}
METAL_BASE = {"9k": "XAU", "14k": "XAU", "18k": "XAU", "pt950": "XPT", "s925": "XAG"}
FALLBACK_XPT = 1050.0
# Fine silver TWD/g fallback when 白銀條塊 row missing from board HTML
FALLBACK_XAG = 61.0

TAIPEI = ZoneInfo("Asia/Taipei")

# Legacy alias — older imports / docs may still say BOT_URLS.
BOT_URLS = ALLBEAUTY_URLS


def build_alloy_rates_per_chin(alloy_per_gram: dict[str, float]) -> dict[str, float]:
    return {gold: rate * CHIN_TO_GRAMS for gold, rate in alloy_per_gram.items()}


def build_alloy_rates(raw: dict[str, float]) -> dict[str, float]:
    alloy: dict[str, float] = {}
    for gold, multiplier in PURITY_MULTIPLIER.items():
        symbol = METAL_BASE[gold]
        if symbol in raw and raw[symbol] is not None:
            alloy[gold] = raw[symbol] * multiplier
    return alloy


def format_fetched_at(when: datetime) -> str:
    return when.astimezone(TAIPEI).strftime("%Y/%m/%d %H:%M:%S")


def build_payload_from_cache(row: dict) -> dict:
    """Build public GoldQuote JSON from ``gold_price_cache`` (orders + display source)."""
    now = datetime.now(timezone.utc)
    xau = float(row["xau_per_gram"])
    xpt = float(row["xpt_per_gram"])
    xag = float(row["xag_per_gram"])
    raw = {"XAU": xau, "XPT": xpt, "XAG": xag}
    alloy_rates = build_alloy_rates(raw)
    fetched = row.get("fetched_at")
    if fetched is not None and hasattr(fetched, "astimezone"):
        fetched_dt = fetched if fetched.tzinfo else fetched.replace(tzinfo=timezone.utc)
    else:
        fetched_dt = now
    age_hours = (now - fetched_dt.astimezone(timezone.utc)).total_seconds() / 3600.0
    fetched_display = format_fetched_at(fetched_dt)
    return {
        "refreshed": False,
        "quote": {
            "available": True,
            "sell": xau,
            "sellPerChin": xau * CHIN_TO_GRAMS,
            "source": "cached",
            "bot_posted_at": row.get("bot_posted_at"),
            "fetched_at": fetched_dt.isoformat(),
            "fetched_at_display": fetched_display,
            "is_stale": age_hours > 24,
            "source_url": "",
        },
        "alloyRates": alloy_rates,
        "alloyRatesPerChin": build_alloy_rates_per_chin(alloy_rates),
        "metals": raw,
    }


def _positive_metal(raw: object | None, fallback: float) -> float:
    try:
        value = float(raw) if raw is not None else 0.0
    except (TypeError, ValueError):
        return fallback
    return value if value > 0 else fallback


def build_payload(
    parsed: dict[str, float | str | None],
    source_url: str,
    *,
    xag_per_gram: float | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    per_gram = float(parsed["perGram"])
    xpt = _positive_metal(parsed.get("xptPerGram"), FALLBACK_XPT)
    # Prefer explicit override (tests); else board 白銀條塊; else FALLBACK_XAG.
    if xag_per_gram is not None and xag_per_gram > 0:
        xag = float(xag_per_gram)
    else:
        xag = _positive_metal(parsed.get("xagPerGram"), FALLBACK_XAG)
    raw = {"XAU": per_gram, "XPT": xpt, "XAG": xag}
    alloy_rates = build_alloy_rates(raw)
    return {
        "refreshed": True,
        "quote": {
            "available": True,
            "sell": per_gram,
            "sellPerChin": per_gram * CHIN_TO_GRAMS,
            "source": SOURCE_NAME,
            "bot_posted_at": parsed.get("stamp"),
            "fetched_at": now.isoformat(),
            "fetched_at_display": format_fetched_at(now),
            "is_stale": False,
            "source_url": source_url,
        },
        "alloyRates": alloy_rates,
        "alloyRatesPerChin": build_alloy_rates_per_chin(alloy_rates),
        "metals": {"XAU": per_gram, "XPT": xpt, "XAG": xag},
    }


def invalidate_bot_gold_memory_cache() -> None:
    """Drop in-process scrape cache (e.g. after a forced browser refresh)."""
    global _cached_payload, _cached_at
    _cached_payload = None
    _cached_at = 0.0


async def fetch_bot_gold_quote(*, force: bool = False) -> dict:
    """Cached wrapper: network once per TTL unless ``force`` (button refresh)."""
    global _cached_payload, _cached_at

    if not force:
        now = time.monotonic()
        if _cached_payload is not None and (now - _cached_at) < _CACHE_TTL_SECONDS:
            return _cached_payload

    async with _cache_lock:
        if not force:
            now = time.monotonic()
            if _cached_payload is not None and (now - _cached_at) < _CACHE_TTL_SECONDS:
                return _cached_payload

        payload = await _fetch_bot_gold_quote_live()
        _cached_payload = payload
        _cached_at = time.monotonic()
        return payload


async def _fetch_bot_gold_quote_live() -> dict:
    last_error: Exception | None = None
    # 18s each attempt — Allbeauty is often slow; fail before blocking admin work.
    request_timeout = 18
    async with AsyncSession(impersonate="chrome120") as client:
        for url in ALLBEAUTY_URLS:
            try:
                response = await client.get(
                    url, headers=BOT_HEADERS, timeout=request_timeout
                )
                if response.status_code >= 400:
                    raise RuntimeError(f"HTTP {response.status_code}")
                html = response.text
                if is_bot_challenge(html):
                    raise RuntimeError("scrape challenge / empty board")
                parsed = find_gold_bar_prices(html)
                if not parsed:
                    raise RuntimeError("parse failed")
                return build_payload(parsed, url)
            except Exception as err:  # noqa: BLE001 — try next URL
                last_error = err
    raise last_error or RuntimeError("Allbeauty gold scrape failed")
