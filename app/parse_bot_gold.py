"""Parse Bank of Taiwan (BOT) 黃金條塊 sell price from HTML."""

from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup, Tag

GOLD_BAR_ANCHOR = "黃金條塊"
BAR_DERIVED_GRAM_MIN = 3500
BAR_DERIVED_GRAM_MAX = 5500

WEIGHT_HEADER_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"1\s*公斤"), 1000),
    (re.compile(r"500\s*公克"), 500),
    (re.compile(r"250\s*公克"), 250),
    (re.compile(r"100\s*公克"), 100),
]


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


def cell_amount(cell: Tag | None) -> float | None:
    if cell is None:
        return None
    return parse_twd_amount(text_of(cell))


def grams_from_header_text(text: str | None) -> int | None:
    normalized = re.sub(r"\s+", "", text or "")
    for pattern, grams in WEIGHT_HEADER_PATTERNS:
        if pattern.search(text or "") or pattern.search(normalized):
            return grams
    return None


def is_bar_derived_gram_price(amount: float | None) -> bool:
    return amount is not None and BAR_DERIVED_GRAM_MIN <= amount <= BAR_DERIVED_GRAM_MAX


def parse_bot_datetime(stamp: str | None) -> list[int] | None:
    if not stamp:
        return None
    match = re.search(r"(\d{4})/(\d{2})/(\d{2})\s+(\d{2}):(\d{2})", stamp)
    if not match:
        return None
    return [int(match.group(i)) for i in range(1, 6)]


def extract_page_stamp(soup: BeautifulSoup) -> str | None:
    body = soup.find("body")
    text = text_of(body)
    for pattern in (
        r"掛牌時間[：:]\s*(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})",
        r"牌價時間[：:]\s*(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})",
    ):
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    time_span = soup.select_one("span.time")
    if time_span:
        match = re.search(r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})", text_of(time_span))
        if match:
            return match.group(1)

    time_cell = soup.select_one('td[data-table="牌價時間"]')
    if time_cell:
        match = re.search(r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})", text_of(time_cell))
        if match:
            return match.group(1)
    return None


def extract_stamp_from_row(row: Tag) -> str | None:
    time_cell = row.select_one('td[data-table*="牌價時間"]')
    if time_cell:
        match = re.search(r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})", text_of(time_cell))
        if match:
            return match.group(1)
    match = re.search(r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})", text_of(row))
    return match.group(1) if match else None


def weight_columns_from_table(table: Tag) -> dict[int, int]:
    for row in table.find_all("tr"):
        cols: dict[int, int] = {}
        for idx, cell in enumerate(row.find_all(["td", "th"])):
            grams = grams_from_header_text(text_of(cell))
            if grams is not None:
                cols[idx] = grams
        if cols:
            return cols
    return {}


PREFERRED_GRAM_ORDER = (100, 250, 500, 1000)


def per_gram_from_bar_sell_row(row: Tag, weight_cols: dict[int, int]) -> float | None:
    cells = row.find_all(["td", "th"])
    candidates: dict[int, float] = {}
    for idx, grams in weight_cols.items():
        if idx >= len(cells):
            continue
        amount = cell_amount(cells[idx])
        if amount is None or amount < 10000:
            continue
        per_gram = amount / grams
        if is_bar_derived_gram_price(per_gram):
            candidates[grams] = per_gram
    for grams in PREFERRED_GRAM_ORDER:
        if grams in candidates:
            return candidates[grams]
    return None


def is_gold_bar_table(soup: BeautifulSoup, table: Tag) -> bool:
    for td in table.find_all("td"):
        if text_of(td) == GOLD_BAR_ANCHOR:
            return True
    summary = table.get("summary") or table.get("title") or ""
    if GOLD_BAR_ANCHOR in summary and "存摺" not in summary:
        return True
    return any(label in summary for label in ("黃金條塊歷史牌價", "黃金條塊牌價", "黃金條塊表格"))


def find_gold_bar_anchor(soup: BeautifulSoup) -> Tag | None:
    for td in soup.find_all("td"):
        if text_of(td) == GOLD_BAR_ANCHOR:
            return td
    return None


def quotes_from_live_gold_bar_block(soup: BeautifulSoup, page_stamp: str | None) -> list[tuple[float, str | None]]:
    anchor = find_gold_bar_anchor(soup)
    if anchor is None:
        return []
    table = anchor.find_parent("table")
    if table is None:
        return []

    weight_cols = weight_columns_from_table(table)
    if not weight_cols:
        return []

    anchor_row = anchor.find_parent("tr")
    quotes: list[tuple[float, str | None]] = []
    started = anchor_row is None

    for row in table.find_all("tr"):
        if row is anchor_row:
            started = True
        elif not started:
            continue

        row_text = text_of(row)
        if "轉換" in row_text:
            continue
        if "本行賣出" not in row_text and not row.select_one('td[data-table="本行賣出"]'):
            continue

        per_gram = per_gram_from_bar_sell_row(row, weight_cols)
        if per_gram is not None:
            quotes.append((per_gram, page_stamp or extract_page_stamp(soup)))
            break
    return quotes


def quotes_from_history_tables(soup: BeautifulSoup) -> list[tuple[float, str | None]]:
    quotes: list[tuple[float, str | None]] = []
    for table in soup.find_all("table"):
        summary = table.get("summary") or table.get("title") or ""
        if not is_gold_bar_table(soup, table):
            continue
        if "黃金存摺" in summary and "黃金條塊" not in summary:
            continue

        weight_cols = weight_columns_from_table(table)
        if not weight_cols:
            continue

        for row in table.find_all("tr"):
            row_text = text_of(row)
            if "轉換" in row_text:
                continue
            stamp = extract_stamp_from_row(row)
            per_gram = per_gram_from_bar_sell_row(row, weight_cols)
            if per_gram is None:
                continue
            if "本行賣出" in row_text or stamp:
                quotes.append((per_gram, stamp))
    return quotes


def compare_key(a: list[int], b: list[int]) -> int:
    for left, right in zip(a, b):
        if left != right:
            return left - right
    return 0


def pick_latest_quote(quotes: Iterable[tuple[float, str | None]]) -> tuple[float, str | None] | None:
    best: tuple[float, str | None] | None = None
    best_key: list[int] | None = None
    for sell, stamp in quotes:
        key = parse_bot_datetime(stamp) or [0, 0, 0, 0, 0]
        if best is None or compare_key(key, best_key or [0, 0, 0, 0, 0]) >= 0:
            best = (sell, stamp)
            best_key = key
    return best


def find_gold_bar_prices(html: str) -> dict[str, float | str | None] | None:
    soup = BeautifulSoup(html, "html.parser")
    page_stamp = extract_page_stamp(soup)
    quotes = [
        *quotes_from_live_gold_bar_block(soup, page_stamp),
        *quotes_from_history_tables(soup),
    ]
    if not quotes:
        return None

    picked = pick_latest_quote(quotes)
    if picked is None:
        return None
    sell, stamp_raw = picked
    return {"perGram": sell, "stamp": stamp_raw or page_stamp}


def is_bot_challenge(html: str | None) -> bool:
    if not html or len(html) < 10000:
        return True
    lowered = html.lower()
    return "challenge validation" in lowered or "<title>challenge" in lowered
