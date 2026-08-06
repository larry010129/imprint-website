"""Background Allbeauty gold scrape: shared lock, min interval, lifespan loop."""

from __future__ import annotations

import asyncio
import logging
import os
import time

from app.bot_gold import (
    FALLBACK_XAG,
    FALLBACK_XPT,
    fetch_bot_gold_quote,
    invalidate_bot_gold_memory_cache,
)
from app.database import get_connection

log = logging.getLogger(__name__)

DEFAULT_INTERVAL_SEC = 1800
MIN_SCRAPE_INTERVAL_SEC = 90
_STARTUP_DELAY_SEC = 2.0

_scrape_lock = asyncio.Lock()
_last_scrape_mono: float = 0.0


def scrape_interval_sec() -> int:
    raw = (os.environ.get("GOLD_SCRAPE_INTERVAL_SEC") or str(DEFAULT_INTERVAL_SEC)).strip()
    try:
        return max(int(raw), 1)
    except ValueError:
        log.warning("invalid GOLD_SCRAPE_INTERVAL_SEC=%r; using %s", raw, DEFAULT_INTERVAL_SEC)
        return DEFAULT_INTERVAL_SEC


def scrape_on_startup_enabled() -> bool:
    raw = (os.environ.get("GOLD_SCRAPE_ON_STARTUP") or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def quote_fields_from_payload(payload: dict) -> tuple[float, float, float, str | None, str]:
    """Extract cache columns from fetch_bot_gold_quote / gold-quote.json shape."""
    quote = payload.get("quote") or {}
    metals = payload.get("metals") or {}
    xau = float(quote.get("sell") or metals.get("XAU") or 0)
    xag = float(metals.get("XAG") or FALLBACK_XAG)
    xpt = float(metals.get("XPT") or FALLBACK_XPT)
    source = str(quote.get("source") or "allbeauty")
    stamp = quote.get("bot_posted_at")
    stamp_out = stamp if stamp is None or isinstance(stamp, str) else str(stamp)
    return xau, xag, xpt, stamp_out, source


def persist_gold_price_cache(
    *,
    xau: float,
    xag: float,
    xpt: float,
    bot_posted_at: str | None,
    source: str,
) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into gold_price_cache
              (id, xau_per_gram, xpt_per_gram, xag_per_gram, bot_posted_at, source, fetched_at)
            values (1, %s, %s, %s, %s, %s, now())
            on conflict (id) do update set
              xau_per_gram = excluded.xau_per_gram,
              xpt_per_gram = excluded.xpt_per_gram,
              xag_per_gram = excluded.xag_per_gram,
              bot_posted_at = excluded.bot_posted_at,
              source = excluded.source,
              fetched_at = now()
            """,
            (xau, xpt, xag, bot_posted_at, source),
        )


def _throttle_remaining() -> float:
    if _last_scrape_mono <= 0:
        return 0.0
    elapsed = time.monotonic() - _last_scrape_mono
    return max(0.0, MIN_SCRAPE_INTERVAL_SEC - elapsed)


async def scrape_and_persist_gold(*, force: bool = True) -> dict | None:
    """Live scrape + persist under shared lock. None if within 90s min interval."""
    global _last_scrape_mono
    async with _scrape_lock:
        if _throttle_remaining() > 0:
            log.debug("gold scrape skipped (min interval %ss)", MIN_SCRAPE_INTERVAL_SEC)
            return None
        payload = await fetch_bot_gold_quote(force=force)
        xau, xag, xpt, stamp, source = quote_fields_from_payload(payload)
        if xau <= 0:
            raise RuntimeError("金價資料無效")
        persist_gold_price_cache(
            xau=xau, xag=xag, xpt=xpt, bot_posted_at=stamp, source=source
        )
        invalidate_bot_gold_memory_cache()
        _last_scrape_mono = time.monotonic()
        return payload


async def gold_scrape_loop() -> None:
    """Startup scrape (optional) then every GOLD_SCRAPE_INTERVAL_SEC."""
    interval = scrape_interval_sec()
    if scrape_on_startup_enabled():
        await asyncio.sleep(_STARTUP_DELAY_SEC)
        try:
            await scrape_and_persist_gold(force=True)
            log.info("gold scrape startup ok")
        except Exception:
            log.exception("gold scrape startup failed; keeping last cache row")
    while True:
        await asyncio.sleep(interval)
        try:
            await scrape_and_persist_gold(force=True)
            log.info("gold scrape interval ok (%ss)", interval)
        except Exception:
            log.exception("gold scrape interval failed; keeping last cache row")

