"""Parser tests for Allbeauty mobile `#goldprice` board."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.bot_gold import ALLBEAUTY_URLS, build_payload
from app.parse_bot_gold import (
    find_allbeauty_retail_prices,
    find_gold_bar_prices,
    is_bot_challenge,
)
from app.pricing import CHIN_TO_GRAMS

FIXTURE = Path(__file__).parent / "fixtures" / "allbeauty_m_goldprice.html"
# Fixture board 售價 (元/錢) — jewelry rows drive XAU / XPT / XAG
JEWELRY_SELL_PER_CHIN = 17200.0
PT950_SELL_PER_CHIN = 7430.0
SILVER_BAR_SELL_PER_CHIN = 266.94
BAR_GOLD_SELL_PER_CHIN = 16623.0
BAR_PT_SELL_PER_CHIN = 7260.0
PRIMARY_SCRAPE_URL = "https://www.allbeauty.com.tw/m/"


@pytest.fixture
def sample_html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_primary_scrape_url_is_allbeauty_mobile() -> None:
    assert ALLBEAUTY_URLS[0] == PRIMARY_SCRAPE_URL
    assert all("/GoldPrice/" not in u for u in ALLBEAUTY_URLS)


def test_find_jewelry_gold_sell_per_gram(sample_html: str) -> None:
    parsed = find_allbeauty_retail_prices(sample_html)
    assert parsed is not None
    assert parsed["label"] == "黃金飾金"
    assert parsed["field"] == "售價"
    assert parsed["perChin"] == JEWELRY_SELL_PER_CHIN
    assert parsed["perChin"] != BAR_GOLD_SELL_PER_CHIN
    assert parsed["perGram"] == pytest.approx(JEWELRY_SELL_PER_CHIN / CHIN_TO_GRAMS)
    assert parsed["stamp"] == "2026-07-31 18:21:11"
    assert parsed["xptPerChin"] == PT950_SELL_PER_CHIN
    assert parsed["xptPerChin"] != BAR_PT_SELL_PER_CHIN
    assert parsed["xptPerGram"] == pytest.approx(PT950_SELL_PER_CHIN / CHIN_TO_GRAMS)
    assert parsed["xagPerChin"] == SILVER_BAR_SELL_PER_CHIN
    assert parsed["xagPerGram"] == pytest.approx(SILVER_BAR_SELL_PER_CHIN / CHIN_TO_GRAMS)


def test_compat_entry_find_gold_bar_prices(sample_html: str) -> None:
    parsed = find_gold_bar_prices(sample_html)
    assert parsed is not None
    assert parsed["perGram"] == pytest.approx(JEWELRY_SELL_PER_CHIN / CHIN_TO_GRAMS)
    assert parsed["stamp"] == "2026-07-31 18:21:11"
    assert parsed["xptPerGram"] == pytest.approx(PT950_SELL_PER_CHIN / CHIN_TO_GRAMS)
    assert parsed["xagPerGram"] == pytest.approx(SILVER_BAR_SELL_PER_CHIN / CHIN_TO_GRAMS)


def test_build_payload_uses_allbeauty_source(sample_html: str) -> None:
    parsed = find_gold_bar_prices(sample_html)
    assert parsed is not None
    payload = build_payload(parsed, PRIMARY_SCRAPE_URL)
    assert payload["quote"]["source"] == "allbeauty"
    assert payload["quote"]["source_url"] == PRIMARY_SCRAPE_URL
    assert payload["quote"]["sell"] == pytest.approx(JEWELRY_SELL_PER_CHIN / CHIN_TO_GRAMS)
    assert payload["quote"]["sellPerChin"] == pytest.approx(JEWELRY_SELL_PER_CHIN)
    assert payload["metals"]["XPT"] == pytest.approx(PT950_SELL_PER_CHIN / CHIN_TO_GRAMS)
    assert payload["metals"]["XAG"] == pytest.approx(SILVER_BAR_SELL_PER_CHIN / CHIN_TO_GRAMS)
    assert payload["alloyRates"]["s925"] == pytest.approx(
        (SILVER_BAR_SELL_PER_CHIN / CHIN_TO_GRAMS) * 0.925
    )
    assert "18k" in payload["alloyRates"]
    assert "pt950" in payload["alloyRates"]


def test_build_payload_xag_override_still_honored(sample_html: str) -> None:
    parsed = find_gold_bar_prices(sample_html)
    assert parsed is not None
    payload = build_payload(parsed, PRIMARY_SCRAPE_URL, xag_per_gram=62.0)
    assert payload["metals"]["XAG"] == 62.0
    assert payload["alloyRates"]["s925"] == pytest.approx(62.0 * 0.925)


def test_rejects_empty_and_challenge_pages() -> None:
    assert is_bot_challenge(None) is True
    assert is_bot_challenge("") is True
    assert is_bot_challenge("<html><body>hi</body></html>") is True
    assert is_bot_challenge("<html><title>Challenge</title></html>") is True


def test_parse_rejects_bar_only_missing_jewelry_row() -> None:
    html = """
    <table id='goldprice'>
      <tr><th>名稱</th><th>售價</th><th>回收價</th></tr>
      <tr><td>黃金條塊</td><td>16,623</td><td>16,373</td></tr>
      <tr><th colspan="3">2026-07-31 18:00:00</th></tr>
    </table>
    """
    assert find_allbeauty_retail_prices(html) is None


def test_parse_accepts_jewelry_only_row() -> None:
    html = """
    <table id='goldprice'>
      <tr><th>名稱</th><th>售價</th><th>回收價</th></tr>
      <tr><td>黃金飾金</td><td>17,200</td><td>16,000</td></tr>
      <tr><th colspan="3">2026-07-31 18:00:00</th></tr>
    </table>
    """
    parsed = find_allbeauty_retail_prices(html)
    assert parsed is not None
    assert parsed["label"] == "黃金飾金"
    assert parsed["perChin"] == 17200.0


def test_parse_flat_broken_markup_without_tr() -> None:
    html = """
    <table id="goldprice">
      <td>白銀條塊</td><td>266.94</td><td>221.00</td>
      <td>黃金飾金</td><td>17,200</td><td>16,000</td>
      <td>白金 Pt950</td><td>7,430</td><td>5,840</td>
      <th colspan="3">2026-07-31 12:00:00</th>
    </table>
    """
    parsed = find_allbeauty_retail_prices(html)
    assert parsed is not None
    assert parsed["perChin"] == 17200.0
    assert parsed["xptPerChin"] == 7430.0
    assert parsed["xagPerChin"] == 266.94
    assert parsed["label"] == "黃金飾金"


def test_parse_rejects_silver_out_of_band() -> None:
    html = """
    <table id='goldprice'>
      <tr><th>名稱</th><th>售價</th><th>回收價</th></tr>
      <tr><td>黃金飾金</td><td>17,200</td><td>16,000</td></tr>
      <tr><td>白銀條塊</td><td>5</td><td>4</td></tr>
      <tr><th colspan="3">2026-07-31 18:00:00</th></tr>
    </table>
    """
    parsed = find_allbeauty_retail_prices(html)
    assert parsed is not None
    assert "xagPerChin" not in parsed
