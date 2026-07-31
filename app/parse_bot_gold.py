"""Parse Allbeauty (詮美) mobile gold board HTML → retail gold per-gram.

Source: https://www.allbeauty.com.tw/m/  (`#goldprice` table).

Price field choice
------------------
Shop pricing uses **黃金條塊 / 售價** (bar gold sell).

Board quotes are 元/錢 (台錢); convert with CHIN_TO_GRAMS (3.75) → TWD/g
for the rest of the stack.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.pricing import CHIN_TO_GRAMS

BAR_GOLD_LABEL = "黃金條塊"
PLATINUM_LABEL = "白金 Pt950"
GOLDPRICE_TABLE_ID = "goldprice"

# Plausible TWD/錢 bands for Taiwan retail boards (guards parse mistakes).
BAR_GOLD_PER_CHIN_MIN = 8000.0
BAR_GOLD_PER_CHIN_MAX = 40000.0
PT950_PER_CHIN_MIN = 2000.0
PT950_PER_CHIN_MAX = 20000.0

_STAMP_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?")
_AMOUNT_RE = re.compile(r"[\d,]+(?:\.\d+)?")


def text_of(el: Tag | None) -> str:
    if el is None:
        return ""
    return re.sub(r"\s+", " ", el.get_text()).strip()


def parse_twd_amount(text: str | None) -> float | None:
    cleaned = re.sub(r"[^\d,.]", "", text or "")
    if not cleaned:
        return None
    try:
        value = float(cleaned.replace(",", ""))
    except ValueError:
        return None
    return value if value == value else None


def normalize_stamp(raw: str | None) -> str | None:
    if not raw:
        return None
    match = _STAMP_RE.search(raw)
    if not match:
        return None
    y, mo, d, h, mi = (match.group(i) for i in range(1, 6))
    sec = match.group(6) or "00"
    return f"{y}-{mo}-{d} {h}:{mi}:{sec}"


def _label_matches(cell_text: str, label: str) -> bool:
    compact = re.sub(r"\s+", "", cell_text)
    want = re.sub(r"\s+", "", label)
    return compact == want or compact.startswith(want)


def _row_cells(row: Tag) -> list[Tag]:
    return row.find_all(["td", "th"], recursive=False) or row.find_all(["td", "th"])


def _sell_from_named_row(row: Tag, label: str) -> float | None:
    cells = _row_cells(row)
    if len(cells) < 2:
        return None
    if not _label_matches(text_of(cells[0]), label):
        return None
    return parse_twd_amount(text_of(cells[1]))


def _find_goldprice_table(soup: BeautifulSoup) -> Tag | None:
    table = soup.find("table", id=GOLDPRICE_TABLE_ID)
    if table is not None:
        return table
    for candidate in soup.find_all("table"):
        blob = text_of(candidate)
        if BAR_GOLD_LABEL in blob and ("售價" in blob or "回收價" in blob):
            return candidate
    return None


def _extract_stamp(table: Tag, soup: BeautifulSoup) -> str | None:
    for row in table.find_all("tr"):
        stamp = normalize_stamp(text_of(row))
        if stamp:
            return stamp
    return normalize_stamp(text_of(soup.find("body")))


def _per_chin_in_band(amount: float | None, lo: float, hi: float) -> float | None:
    if amount is None or not (lo <= amount <= hi):
        return None
    return amount


def find_allbeauty_retail_prices(html: str) -> dict[str, Any] | None:
    """Parse `#goldprice` rows. Returns perGram (TWD/g) for 黃金條塊 售價."""
    if not html or not html.strip():
        return None
    soup = BeautifulSoup(html, "html.parser")
    table = _find_goldprice_table(soup)
    if table is None:
        return None

    bar_chin: float | None = None
    pt_chin: float | None = None
    for row in table.find_all("tr"):
        if bar_chin is None:
            bar_chin = _per_chin_in_band(
                _sell_from_named_row(row, BAR_GOLD_LABEL),
                BAR_GOLD_PER_CHIN_MIN,
                BAR_GOLD_PER_CHIN_MAX,
            )
        if pt_chin is None:
            pt_chin = _per_chin_in_band(
                _sell_from_named_row(row, PLATINUM_LABEL),
                PT950_PER_CHIN_MIN,
                PT950_PER_CHIN_MAX,
            )

    # Broken markup sometimes nests cells without clean <tr>; scan flat tds.
    if bar_chin is None:
        cells = table.find_all(["td", "th"])
        for idx, cell in enumerate(cells):
            if not _label_matches(text_of(cell), BAR_GOLD_LABEL):
                continue
            if idx + 1 >= len(cells):
                break
            bar_chin = _per_chin_in_band(
                parse_twd_amount(text_of(cells[idx + 1])),
                BAR_GOLD_PER_CHIN_MIN,
                BAR_GOLD_PER_CHIN_MAX,
            )
            break

    if bar_chin is None:
        return None

    per_gram = bar_chin / CHIN_TO_GRAMS
    result: dict[str, Any] = {
        "perGram": per_gram,
        "perChin": bar_chin,
        "stamp": _extract_stamp(table, soup),
        "label": BAR_GOLD_LABEL,
        "field": "售價",
    }
    if pt_chin is not None:
        result["xptPerGram"] = pt_chin / CHIN_TO_GRAMS
        result["xptPerChin"] = pt_chin
    return result


def find_gold_bar_prices(html: str) -> dict[str, float | str | None] | None:
    """Backward-compatible entry used by `app.bot_gold` (Allbeauty 條塊 售價)."""
    parsed = find_allbeauty_retail_prices(html)
    if not parsed:
        return None
    out: dict[str, float | str | None] = {
        "perGram": float(parsed["perGram"]),
        "stamp": parsed.get("stamp"),
    }
    if parsed.get("xptPerGram") is not None:
        out["xptPerGram"] = float(parsed["xptPerGram"])
    return out


def is_bot_challenge(html: str | None) -> bool:
    """True when response looks empty / blocked (not a usable price board)."""
    if not html or len(html.strip()) < 200:
        return True
    lowered = html.lower()
    if "challenge validation" in lowered or "<title>challenge" in lowered:
        return True
    if "captcha" in lowered and "allbeauty" not in lowered:
        return True
    # Need either table id or bar-gold label; otherwise treat as unusable.
    return GOLDPRICE_TABLE_ID not in html and BAR_GOLD_LABEL not in html
