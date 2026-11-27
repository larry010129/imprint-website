"""Daily TWD exchange rates for the price estimates on /en, /ja and /ko.

Source: fawazahmed0/exchange-api. Free, no key, published as CC0 (public
domain), so the page needs no credit line. It is community-run with no uptime
promise: if it fails or stops updating, the calculator shows NT$ only.
"""

from __future__ import annotations

import json
import logging
import math
import threading
import time
from datetime import date, timedelta
from urllib.request import Request, urlopen

# The second address is the fallback the project's README asks clients to use.
RATES_URLS = (
    "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/twd.json",
    "https://latest.currency-api.pages.dev/v1/currencies/twd.json",
)
CURRENCIES = ("USD", "JPY", "KRW")

_REFRESH_SECONDS = 24 * 60 * 60  # one check per day
_RETRY_SECONDS = 10 * 60
_MAX_AGE_SECONDS = 3 * 24 * 60 * 60  # hide estimates rather than show old rates
_MAX_DATA_AGE = timedelta(days=7)

_log = logging.getLogger(__name__)
_lock = threading.Lock()
_rates: dict[str, float] | None = None
_fetched_at = 0.0
_next_try = 0.0


def parse_rates(payload: object) -> dict[str, float] | None:
    """Return the wanted rates per 1 TWD, or None if wrong or out of date."""
    if not isinstance(payload, dict) or not isinstance(payload.get("twd"), dict):
        return None
    try:
        published = date.fromisoformat(str(payload.get("date")))
    except ValueError:
        return None
    if date.today() - published > _MAX_DATA_AGE:
        return None
    rates = {}
    for code in CURRENCIES:
        value = payload["twd"].get(code.lower())
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            return None
        rates[code] = float(value)
    return rates


def _download(url: str) -> object:
    request = Request(url, headers={"User-Agent": "price-estimate/1.0"})
    with urlopen(request, timeout=6) as response:
        return json.load(response)


def _fetch() -> dict[str, float] | None:
    for url in RATES_URLS:
        try:
            rates = parse_rates(_download(url))
        except (OSError, ValueError) as error:
            _log.warning("Exchange rate fetch failed (%s): %s", url, error)
            continue
        if rates:
            return rates
    return None


def get_rates() -> dict[str, float] | None:
    """Cached rates. Blocking: call from a worker thread."""
    global _rates, _fetched_at, _next_try
    with _lock:
        now = time.monotonic()
        if now >= _next_try:
            fresh = _fetch()
            if fresh:
                _rates, _fetched_at = fresh, now
                _next_try = now + _REFRESH_SECONDS
            else:
                _next_try = now + _RETRY_SECONDS
        if _rates and now - _fetched_at <= _MAX_AGE_SECONDS:
            return dict(_rates)
        return None
