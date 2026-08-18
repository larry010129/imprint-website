"""Girdle engraving: any Latin/punct at any carat; CJK only at 0.3ct+."""

from app.controllers.htmx_shop_wizard import _config_from_form
from app.controllers.shop_controller import _validate_config
from app.orders import (
    GIRDLE_MAX_SLOTS,
    apply_girdle_engraving,
    carat_allows_chinese_engraving,
    cart_details_from_config,
    hydrate_order,
    pack_order_config,
    sanitize_girdle_engraving,
)


def test_carat_allows_chinese_engraving():
    assert carat_allows_chinese_engraving(0.3) is True
    assert carat_allows_chinese_engraving("0.3") is True
    assert carat_allows_chinese_engraving("0.30") is True
    assert carat_allows_chinese_engraving("0.30ct") is True
    assert carat_allows_chinese_engraving("1") is True
    assert carat_allows_chinese_engraving(0.29) is False
    assert carat_allows_chinese_engraving("0.2") is False
    assert carat_allows_chinese_engraving(None) is False
    assert carat_allows_chinese_engraving("") is False
    assert carat_allows_chinese_engraving("3fen") is False


def test_sanitize_cjk_only_at_point_three():
    assert sanitize_girdle_engraving("永遠", "0.3") == "永遠"
    assert sanitize_girdle_engraving("永遠", 0.3) == "永遠"
    assert sanitize_girdle_engraving("永遠", "0.30") == "永遠"
    assert sanitize_girdle_engraving("永遠", carat="0.3") == "永遠"
    assert sanitize_girdle_engraving("永遠", 0.2) == ""
    assert sanitize_girdle_engraving("永遠", "0.2") == ""
    assert sanitize_girdle_engraving("永遠") == ""
    assert sanitize_girdle_engraving("永遠", None) == ""


def test_sanitize_keeps_latin_punct_at_small_carat():
    assert sanitize_girdle_engraving("Love 2026", 0.2) == "Love 2026"
    assert sanitize_girdle_engraving("A.B @ $", 0.2) == "A.B @ $"
    assert sanitize_girdle_engraving("love.@$", 0.2) == "love.@$"
    assert sanitize_girdle_engraving("A@B.$/2024", 0.2) == "A@B.$/2024"


def test_sanitize_keeps_cjk_spaces_punctuation_and_symbols():
    assert sanitize_girdle_engraving("永遠", carat="0.3") == "永遠"
    assert sanitize_girdle_engraving("Love 2026") == "Love 2026"
    assert sanitize_girdle_engraving("A&B · 永遠!", carat="0.3") == "A&B · 永遠!"
    assert sanitize_girdle_engraving("〔雙心〕永遠", carat="0.3") == "〔雙心〕永遠"
    assert sanitize_girdle_engraving("love.@$") == "love.@$"
    assert sanitize_girdle_engraving("A@B.$/2024") == "A@B.$/2024"
    assert sanitize_girdle_engraving("愛.@$", carat="0.3") == "愛.@$"
    assert sanitize_girdle_engraving("永遠.@$", carat="0.2") == ".@$"
    assert sanitize_girdle_engraving("〔雙心〕永遠", allow_chinese=False) == "〔雙心〕"


def test_sanitize_strips_html_controls_and_clips():
    assert sanitize_girdle_engraving("<b>永遠</b>", carat="0.3") == "永遠"
    assert sanitize_girdle_engraving("<script>alert(1)</script>Love") == "alert(1)Love"
    assert sanitize_girdle_engraving("Love\x00 2026\n") == "Love 2026"
    assert sanitize_girdle_engraving("&lt;i&gt;永遠&lt;/i&gt;", carat="0.3") == "永遠"
    assert sanitize_girdle_engraving("x" * 200) == "x" * GIRDLE_MAX_SLOTS


def test_sanitize_clips_to_twelve_slots_keeps_emblems():
    assert sanitize_girdle_engraving("LOVE.@$2024!") == "LOVE.@$2024!"
    assert sanitize_girdle_engraving("LOVE.@$2024!X") == "LOVE.@$2024!"
    six = "〔雙心〕" * 6
    assert sanitize_girdle_engraving(six) == six
    assert sanitize_girdle_engraving("〔雙心〕" * 7) == six
    assert sanitize_girdle_engraving("〔雙心〕ABCDEFGHIJK") == "〔雙心〕ABCDEFGHIJ"
    assert sanitize_girdle_engraving("〔不是圖騰〕LOVE") == "LOVE"


def test_apply_accepts_snake_and_camel():
    camel = {"carat": "0.3", "engravingGirdle": "永遠"}
    apply_girdle_engraving(camel)
    assert camel["engravingGirdle"] == "永遠"

    snake = {"carat": "0.3", "engraving_girdle": "<b>Love 2026</b>"}
    apply_girdle_engraving(snake)
    assert snake["engravingGirdle"] == "Love 2026"
    assert snake["engraving_girdle"] == "Love 2026"

    below = {"carat": "0.2", "engravingGirdle": "永遠.@$"}
    apply_girdle_engraving(below)
    assert below["engravingGirdle"] == ".@$"

    latin = {"carat": "0.2", "engravingGirdle": "A.B @ $"}
    apply_girdle_engraving(latin)
    assert latin["engravingGirdle"] == "A.B @ $"

    missing = {"engravingGirdle": "永遠"}
    apply_girdle_engraving(missing)
    assert missing["engravingGirdle"] == ""

    alt = {"diamondCarat": "0.30", "engravingGirdle": "永遠"}
    apply_girdle_engraving(alt)
    assert alt["engravingGirdle"] == "永遠"


def test_validate_config_keeps_shop_girdle_text():
    body = {
        "category": "pendant",
        "type": "four-prong",
        "carat": "0.3",
        "gold": "14k",
        "engravingGirdle": "永遠",
    }
    assert _validate_config(body) is None
    assert body["engravingGirdle"] == "永遠"

    body["engravingGirdle"] = "Love 2026"
    assert _validate_config(body) is None
    assert body["engravingGirdle"] == "Love 2026"

    body["engravingGirdle"] = "love.@$"
    assert _validate_config(body) is None
    assert body["engravingGirdle"] == "love.@$"

    body["carat"] = "0.2"
    body["engravingGirdle"] = "永遠.@$"
    assert _validate_config(body) is None
    assert body["engravingGirdle"] == ".@$"

    body["engravingGirdle"] = "Love 2026"
    assert _validate_config(body) is None
    assert body["engravingGirdle"] == "Love 2026"

    body["engravingGirdle"] = "A.B @ $"
    assert _validate_config(body) is None
    assert body["engravingGirdle"] == "A.B @ $"

    body["carat"] = "0.3"
    body["engravingGirdle"] = "<img src=x>永遠"
    assert _validate_config(body) is None
    assert body["engravingGirdle"] == "永遠"


def test_pack_and_hydrate_keep_text_strip_html():
    cfg, *_ = pack_order_config(
        {
            "category": "pendant",
            "type": "four-prong",
            "carat": "0.3",
            "engravingGirdle": "Love 2026",
            "clientPricing": {"total": 1},
        }
    )
    assert cfg["engravingGirdle"] == "Love 2026"

    order = hydrate_order(
        {
            "config_json": {
                "engravingGirdle": "<script>x</script>永遠",
                "category": "pendant",
                "type": "four-prong",
                "carat": "0.3",
            }
        }
    )
    assert order["engraving_girdle"] == "x永遠"

    small = hydrate_order(
        {
            "config_json": {
                "engravingGirdle": "永遠.@$",
                "category": "pendant",
                "type": "four-prong",
                "carat": "0.2",
            }
        }
    )
    assert small["engraving_girdle"] == ".@$"


def test_cart_details_and_htmx_form_keep_girdle_text():
    line = cart_details_from_config(
        {
            "category": "pendant",
            "gold": "14k",
            "color": "white",
            "carat": "0.3",
            "diamondKind": "white",
            "engravingGirdle": "永遠",
        }
    )
    assert "腰圍刻字 永遠" in line

    cfg = _config_from_form(
        {
            "category": "pendant",
            "type": "four-prong",
            "carat": "0.3",
            "gold": "14k",
            "engravingGirdle": "Love 2026",
        }
    )
    assert cfg["engravingGirdle"] == "Love 2026"

    cfg_sym = _config_from_form(
        {
            "category": "pendant",
            "type": "four-prong",
            "carat": "0.2",
            "gold": "14k",
            "engravingGirdle": "love.@$ / 永遠",
        }
    )
    assert cfg_sym["engravingGirdle"] == "love.@$ /"

    cfg_cjk = _config_from_form(
        {
            "category": "pendant",
            "type": "four-prong",
            "carat": "0.3",
            "gold": "14k",
            "engravingGirdle": "love.@$ / 永遠",
        }
    )
    assert cfg_cjk["engravingGirdle"] == "love.@$ / 永遠"
