"""Taiwan postal / street address structure helpers (no geocoding)."""

from __future__ import annotations

import re
from collections import Counter

from app.content import TAIWAN_CITIES

POSTAL_RE = re.compile(r"^\d{3}(\d{2})?$")
# Common TW street / locality markers in the detail line (city/district via selects).
STREET_MARKER_RE = re.compile(r"路|街|巷|弄|段|號|樓|室|大道|村|鄉|鎮|里|鄰|道")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
DIGIT_RE = re.compile(r"\d")
LATIN_RE = re.compile(r"[A-Za-z]")
REPEAT_RUN_RE = re.compile(r"(.)\1{3,}")

SHIPPING_CITIES = frozenset(c for c in TAIWAN_CITIES if c != "其他")

STREET_ERROR = (
    "請填寫有效街道地址（含路／街／巷／弄／號等）"
    " / Please enter a valid street address with road markers and a number"
)


def normalize_tw_city(city: str) -> str:
    return (city or "").strip().replace("臺", "台")


def valid_tw_postal(postal: str) -> bool:
    return bool(POSTAL_RE.fullmatch(postal or ""))


def valid_tw_city(city: str) -> bool:
    return normalize_tw_city(city) in SHIPPING_CITIES


def _is_repeated_junk(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    if len(compact) < 4:
        return False
    if REPEAT_RUN_RE.search(compact):
        return True
    most = Counter(compact).most_common(1)[0][1]
    return most * 2 >= len(compact)


def valid_tw_street(address: str) -> bool:
    """Practical TW detail-line structure — not a geocode guarantee."""
    text = (address or "").strip()
    if len(text) < 6:
        return False
    if _is_repeated_junk(text):
        return False
    if not CJK_RE.search(text):
        return False
    if not STREET_MARKER_RE.search(text):
        return False
    if not (DIGIT_RE.search(text) or "號" in text):
        return False
    letters = LATIN_RE.findall(text)
    cjk = CJK_RE.findall(text)
    if letters and len(letters) > len(cjk):
        return False
    return True


def validate_tw_shipping_parts(
    address: str | None,
    city: str | None,
    postal: str | None,
    *,
    empty_msg: str,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Return (city, postal, address, error). city normalized on success."""
    if not (address and city and postal):
        return None, None, None, empty_msg
    city_n = normalize_tw_city(city)
    if not valid_tw_postal(postal):
        return None, None, None, "請填寫有效郵遞區號"
    if not valid_tw_city(city_n):
        return None, None, None, "請選擇有效縣市"
    if not valid_tw_street(address):
        return None, None, None, STREET_ERROR
    return city_n, postal, address, None
