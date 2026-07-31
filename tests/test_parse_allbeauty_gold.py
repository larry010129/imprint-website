"""Parser tests for Allbeauty mobile `#goldprice` board."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.bot_gold import build_payload
from app.parse_bot_gold import (
    find_allbeauty_retail_prices,
    find_gold_bar_prices,
    is_bot_challenge,
)
from app.pricing import CHIN_TO_GRAMS

FIXTURE = Path(__file__).parent / "fixtures" / "allbeauty_m_goldprice.html"
# Fixture 黃金條塊 售價 (元/錢)
BAR_SELL_PER_CHIN = 15969.0


@pytest.fixture
def sample_html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_find_bar_gold_sell_per_gram(sample_html: str) -> None:
    parsed = find_allbeauty_retail_prices(sample_html)
    assert parsed is not None
    assert parsed["label"] == "黃金條塊"
    assert parsed["field"] == "售價"
    assert parsed["perChin"] == BAR_SELL_PER_CHIN
    assert parsed["perGram"] == pytest.approx(BAR_SELL_PER_CHIN / CHIN_TO_GRAMS)
    assert parsed["stamp"] == "2026-07-31 18:21:11"
    assert parsed["xptPerChin"] == 6990.0
    assert parsed["xptPerGram"] == pytest.approx(6990.0 / CHIN_TO_GRAMS)


def test_compat_entry_find_gold_bar_prices(sample_html: str) -> None:
    parsed = find_gold_bar_prices(sample_html)
    assert parsed is not None
    assert parsed["perGram"] == pytest.approx(BAR_SELL_PER_CHIN / CHIN_TO_GRAMS)
    assert parsed["stamp"] == "2026-07-31 18:21:11"
    assert parsed["xptPerGram"] == pytest.approx(6990.0 / CHIN_TO_GRAMS)


def test_build_payload_uses_allbeauty_source(sample_html: str) -> None:
    parsed = find_gold_bar_prices(sample_html)
    assert parsed is not None
    payload = build_payload(parsed, "https://www.allbeauty.com.tw/m/", xag_per_gram=62.0)
    assert payload["quote"]["source"] == "allbeauty"
    assert payload["quote"]["source_url"] == "https://www.allbeauty.com.tw/m/"
    assert payload["quote"]["sell"] == pytest.approx(BAR_SELL_PER_CHIN / CHIN_TO_GRAMS)
    assert payload["metals"]["XPT"] == pytest.approx(6990.0 / CHIN_TO_GRAMS)
    assert payload["metals"]["XAG"] == 62.0
    assert "18k" in payload["alloyRates"]


def test_rejects_empty_and_challenge_pages() -> None:
    assert is_bot_challenge(None) is True
    assert is_bot_challenge("") is True
    assert is_bot_challenge("<html><body>hi</body></html>") is True
    assert is_bot_challenge("<html><title>Challenge</title></html>") is True


def test_parse_rejects_jewelry_only_missing_bar_row() -> None:
    html = """
    <table id='goldprice'>
      <tr><th>名稱</th><th>售價</th><th>回收價</th></tr>
      <tr><td>黃金飾金</td><td>16,520</td><td>15,320</td></tr>
      <tr><th colspan="3">2026-07-31 18:00:00</th></tr>
    </table>
    """
    assert find_allbeauty_retail_prices(html) is None


def test_parse_flat_broken_markup_without_tr() -> None:
    html = """
    <table id="goldprice">
      <td>黃金條塊</td><td>15,100</td><td>14,900</td>
      <th colspan="3">2026-07-31 12:00:00</th>
    </table>
    """
    parsed = find_allbeauty_retail_prices(html)
    assert parsed is not None
    assert parsed["perChin"] == 15100.0
    assert parsed["label"] == "黃金條塊"
