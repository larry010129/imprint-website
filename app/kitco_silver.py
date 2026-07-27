"""Fetch Kitco silver spot (USD/oz) and convert to TWD/g for S925 alloy rates."""

from __future__ import annotations

import re

from curl_cffi.requests import AsyncSession

KITCO_SILVER_URL = "https://www.kitco.com/charts/silver"
KITCO_TEXT_URL = "https://www.kitco.com/texten/texten.html"
BOT_XRT_URL = "https://rate.bot.com.tw/xrt?Lang=zh-TW"

# Troy ounce → grams (LBMA / Kitco spot unit)
TROY_OZ_TO_GRAMS = 31.1034768

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8",
    "Accept": "text/html,application/xhtml+xml",
}


def parse_kitco_silver_ask_usd_oz(html: str) -> float | None:
    """Prefer Ask (sell) side — mirrors BOT 本行賣出 usage for gold."""
    patterns = (
        r">Ask</div>\s*<div[^>]*>\s*([0-9]+(?:\.[0-9]+)?)\s*<",
        r">Ask</[^>]*>\s*<[^>]*>\s*([0-9]+(?:\.[0-9]+)?)\s*<",
        r">silver</span><span[^>]*>[0-9.]+</span><span[^>]*>([0-9.]+)</span>",
    )
    for pat in patterns:
        m = re.search(pat, html, re.I | re.S)
        if not m:
            continue
        try:
            value = float(m.group(1))
        except (TypeError, ValueError):
            continue
        if 5.0 <= value <= 500.0:
            return value
    return None


def parse_bot_usd_cash_sell(html: str) -> float | None:
    """台銀美金現金本行賣出 (second cash column after USD)."""
    m = re.search(
        r"USD\).*?rate-content-cash[^>]*>\s*([0-9]+(?:\.[0-9]+)?)\s*</td>\s*"
        r"<td[^>]*rate-content-cash[^>]*>\s*([0-9]+(?:\.[0-9]+)?)",
        html,
        re.I | re.S,
    )
    if not m:
        return None
    try:
        sell = float(m.group(2))
    except (TypeError, ValueError):
        return None
    if 20.0 <= sell <= 50.0:
        return sell
    return None


def usd_oz_to_twd_per_gram(ask_usd_oz: float, usd_twd: float) -> float:
    return (ask_usd_oz * usd_twd) / TROY_OZ_TO_GRAMS


async def fetch_xag_per_gram_twd(client: AsyncSession | None = None) -> float | None:
    """Return fine silver TWD/g from Kitco Ask × BOT USD cash sell, or None on failure."""
    owns_client = client is None
    session = client or AsyncSession(impersonate="chrome120")
    try:
        ask_usd: float | None = None
        for url in (KITCO_SILVER_URL, KITCO_TEXT_URL):
            try:
                response = await session.get(url, headers=HEADERS, timeout=30)
                if response.status_code >= 400:
                    continue
                ask_usd = parse_kitco_silver_ask_usd_oz(response.text)
                if ask_usd:
                    break
            except Exception:  # noqa: BLE001
                continue
        if not ask_usd:
            return None

        try:
            fx_res = await session.get(BOT_XRT_URL, headers=HEADERS, timeout=30)
            if fx_res.status_code >= 400:
                return None
            usd_twd = parse_bot_usd_cash_sell(fx_res.text)
        except Exception:  # noqa: BLE001
            return None
        if not usd_twd:
            return None

        return usd_oz_to_twd_per_gram(ask_usd, usd_twd)
    finally:
        if owns_client:
            await session.close()
