"""Daily TWD exchange rates for the price estimates on /en, /ja and /ko.

Source: ExchangeRate-API with a free key (EXCHANGE_RATE_API_KEY), which needs no
credit link on the page. Without a key there are no rates and no estimates. Do
not switch to the no-key endpoint: its terms require a visible credit link.
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
from urllib.request import Request, urlopen

RATES_URL = "https://v6.exchangerate-api.com/v6/latest/TWD"
CURRENCIES = ("USD", "JPY", "KRW")

_REFRESH_SECONDS = 12 * 60 * 60
_RETRY_SECONDS = 10 * 60
_MAX_AGE_SECONDS = 3 * 24 * 60 * 60  # hide estimates rather than show old rates

_log = logging.getLogger(__name__)
_lock = threading.Lock()
_rates: dict[str, float] | None = None
_fetched_at = 0.0
_next_try = 0.0


def parse_rates(payload: object) -> dict[str, float] | None:
    """Return the wanted rates per 1 TWD, or None if anything looks wrong."""
    if not isinstance(payload, dict) or payload.get("result") != "success":
        return None
    table = payload.get("conversion_rates")
    if payload.get("base_code") != "TWD" or not isinstance(table, dict):
        return None
    rates = {}
    for code in CURRENCIES:
        value = table.get(code)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            return None
        rates[code] = float(value)
    return rates


def _api_key() -> str:
    return os.environ.get("EXCHANGE_RATE_API_KEY", "").strip()


def _download(key: str) -> object:
    # The key goes in a header so it never appears in a logged address.
    headers = {"Authorization": f"Bearer {key}", "User-Agent": "price-estimate/1.0"}
    request = Request(RATES_URL, headers=headers)
    with urlopen(request, timeout=6) as response:
        return json.load(response)


def get_rates() -> dict[str, float] | None:
    """Cached rates. Blocking: call from a worker thread."""
    global _rates, _fetched_at, _next_try
    key = _api_key()
    if not key:
        return None
    with _lock:
        now = time.monotonic()
        if now >= _next_try:
            try:
                fresh = parse_rates(_download(key))
            except (OSError, ValueError) as error:
                _log.warning("Exchange rate fetch failed: %s", error)
                fresh = None
            if fresh:
                _rates, _fetched_at = fresh, now
                _next_try = now + _REFRESH_SECONDS
            else:
                _next_try = now + _RETRY_SECONDS
        if _rates and now - _fetched_at <= _MAX_AGE_SECONDS:
            return dict(_rates)
        return None
