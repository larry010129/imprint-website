"""Unit tests for cart/checkout details_zh lines."""

from app.orders import cart_details_from_config


def test_cart_details_pendant_with_chain_and_engraving():
    line = cart_details_from_config(
        {
            "category": "pendant",
            "gold": "14k",
            "color": "white",
            "carat": "0.3",
            "diamondKind": "white",
            "includeChain": True,
            "chainGold": "14k",
            "chainColor": "white",
            "chainLength": 46,
            "engravingGirdle": "LOVE",
        }
    )
    assert "14K白金" in line
    assert "0.3ct" in line
    assert "白鑽" in line
    assert "鍊長 46 cm" in line
    assert "搭配鍊條 14K白金" in line
    assert "腰圍刻字 LOVE" in line


def test_cart_details_fancy_ring():
    line = cart_details_from_config(
        {
            "category": "ring",
            "gold": "18k",
            "color": "rose",
            "carat": "0.5",
            "diamondKind": "fancy",
            "fancyColor": "pink",
            "ringSize": 12,
            "engravingBand": "A&B",
        }
    )
    assert line == "18K玫瑰金 · 0.5ct · 彩鑽（粉） · 戒圍 12 · 戒圈刻字 A&B"


def test_cart_details_empty_config():
    assert cart_details_from_config({}) == ""
    assert cart_details_from_config(None) == ""


def test_cart_details_pendant_ignores_ring_size():
    line = cart_details_from_config(
        {
            "category": "pendant",
            "gold": "14k",
            "color": "white",
            "carat": "0.3",
            "diamondKind": "white",
            "ringSize": 12,
            "chainLength": 46,
        }
    )
    assert "戒圍" not in line
    assert "鍊長 46 cm" in line
