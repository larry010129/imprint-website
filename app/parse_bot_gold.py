"""Parse Allbeauty (詮美) mobile gold board HTML → retail metals per-gram.

Source: https://www.allbeauty.com.tw/m/  (`#goldprice` table).

Board row → metal key (售價 column, unit 元/錢)
----------------------------------------------
| Board label   | Metal key | Used?                                      |
| 黃金飾金      | XAU       | Yes — 9k/14k/18k jewelry + chain gold      |
| 白金 Pt950    | XPT       | Yes — pt950 jewelry                        |
| 白銀條塊      | XAG       | Yes — s925 jewelry (fine Ag × 0.925)       |
| 黃金條塊      | —         | No (bar; not jewelry)                      |
| 白金條塊      | —         | No (bar; not jewelry Pt950)                |
| 鈀金條塊      | —         | Unused (no XPD / palladium products)       |

Board quotes are 元/錢 (台錢); convert with CHIN_TO_GRAMS (3.75) → TWD/g
for the rest of the stack. Excel 鍊條價格.xlsx «黃金價» matches 黃金飾金.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.pricing import CHIN_TO_GRAMS

JEWELRY_GOLD_LABEL = "黃金飾金"
# Legacy label kept for table discovery / challenge heuristics only.
BAR_GOLD_LABEL = "黃金條塊"
PLATINUM_LABEL = "白金 Pt950"
SILVER_BAR_LABEL = "白銀條塊"
GOLDPRICE_TABLE_ID = "goldprice"

# Plausible TWD/錢 bands for Taiwan retail boards (guards parse mistakes).
JEWELRY_GOLD_PER_CHIN_MIN = 8000.0
JEWELRY_GOLD_PER_CHIN_MAX = 40000.0
PT950_PER_CHIN_MIN = 2000.0
PT950_PER_CHIN_MAX = 20000.0
SILVER_BAR_PER_CHIN_MIN = 50.0
SILVER_BAR_PER_CHIN_MAX = 2000.0

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
        has_gold = JEWELRY_GOLD_LABEL in blob or BAR_GOLD_LABEL in blob
        if has_gold and ("售價" in blob or "回收價" in blob):
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
    """Parse `#goldprice` rows. Returns perGram (TWD/g) for 黃金飾金 售價."""
    if not html or not html.strip():
        return None
    soup = BeautifulSoup(html, "html.parser")
    table = _find_goldprice_table(soup)
    if table is None:
        return None

    jewelry_chin: float | None = None
    pt_chin: float | None = None
    ag_chin: float | None = None
    for row in table.find_all("tr"):
        if jewelry_chin is None:
            jewelry_chin = _per_chin_in_band(
                _sell_from_named_row(row, JEWELRY_GOLD_LABEL),
                JEWELRY_GOLD_PER_CHIN_MIN,
                JEWELRY_GOLD_PER_CHIN_MAX,
            )
        if pt_chin is None:
            pt_chin = _per_chin_in_band(
                _sell_from_named_row(row, PLATINUM_LABEL),
                PT950_PER_CHIN_MIN,
                PT950_PER_CHIN_MAX,
            )
        if ag_chin is None:
            ag_chin = _per_chin_in_band(
                _sell_from_named_row(row, SILVER_BAR_LABEL),
                SILVER_BAR_PER_CHIN_MIN,
                SILVER_BAR_PER_CHIN_MAX,
            )

    # Broken markup sometimes nests cells without clean <tr>; scan flat tds.
    if jewelry_chin is None or pt_chin is None or ag_chin is None:
        cells = table.find_all(["td", "th"])
        for idx, cell in enumerate(cells):
            label = text_of(cell)
            if idx + 1 >= len(cells):
                break
            nxt = parse_twd_amount(text_of(cells[idx + 1]))
            if jewelry_chin is None and _label_matches(label, JEWELRY_GOLD_LABEL):
                jewelry_chin = _per_chin_in_band(
                    nxt, JEWELRY_GOLD_PER_CHIN_MIN, JEWELRY_GOLD_PER_CHIN_MAX
                )
            elif pt_chin is None and _label_matches(label, PLATINUM_LABEL):
                pt_chin = _per_chin_in_band(
                    nxt, PT950_PER_CHIN_MIN, PT950_PER_CHIN_MAX
                )
            elif ag_chin is None and _label_matches(label, SILVER_BAR_LABEL):
                ag_chin = _per_chin_in_band(
                    nxt, SILVER_BAR_PER_CHIN_MIN, SILVER_BAR_PER_CHIN_MAX
                )

    if jewelry_chin is None:
        return None

    per_gram = jewelry_chin / CHIN_TO_GRAMS
    result: dict[str, Any] = {
        "perGram": per_gram,
        "perChin": jewelry_chin,
        "stamp": _extract_stamp(table, soup),
        "label": JEWELRY_GOLD_LABEL,
        "field": "售價",
    }
    if pt_chin is not None:
        result["xptPerGram"] = pt_chin / CHIN_TO_GRAMS
        result["xptPerChin"] = pt_chin
    if ag_chin is not None:
        result["xagPerGram"] = ag_chin / CHIN_TO_GRAMS
        result["xagPerChin"] = ag_chin
    return result


def find_gold_bar_prices(html: str) -> dict[str, float | str | None] | None:
    """Compat entry used by `app.bot_gold` (Allbeauty 黃金飾金 售價)."""
    parsed = find_allbeauty_retail_prices(html)
    if not parsed:
        return None
    out: dict[str, float | str | None] = {
        "perGram": float(parsed["perGram"]),
        "stamp": parsed.get("stamp"),
    }
    if parsed.get("xptPerGram") is not None:
        out["xptPerGram"] = float(parsed["xptPerGram"])
    if parsed.get("xagPerGram") is not None:
        out["xagPerGram"] = float(parsed["xagPerGram"])
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
    # Need table id or a known gold row label; otherwise treat as unusable.
    has_label = JEWELRY_GOLD_LABEL in html or BAR_GOLD_LABEL in html
    return GOLDPRICE_TABLE_ID not in html and not has_label
