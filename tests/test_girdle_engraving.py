"""Girdle engraving accepts shop text; only max-len + control/HTML are stripped."""

from app.controllers.htmx_shop_wizard import _config_from_form
from app.controllers.shop_controller import _validate_config
from app.orders import (
    GIRDLE_ENGRAVING_MAX_LEN,
    apply_girdle_engraving,
    cart_details_from_config,
    hydrate_order,
    pack_order_config,
    sanitize_girdle_engraving,
)


def test_sanitize_keeps_cjk_spaces_punctuation():
    assert sanitize_girdle_engraving("永遠") == "永遠"
    assert sanitize_girdle_engraving("Love 2026") == "Love 2026"
    assert sanitize_girdle_engraving("A&B · 永遠!") == "A&B · 永遠!"
    assert sanitize_girdle_engraving("〔雙心〕永遠") == "〔雙心〕永遠"


def test_sanitize_strips_html_controls_and_clips():
    assert sanitize_girdle_engraving("<b>永遠</b>") == "永遠"
    assert sanitize_girdle_engraving("<script>alert(1)</script>Love") == "alert(1)Love"
    assert sanitize_girdle_engraving("Love\x00 2026\n") == "Love 2026"
    assert sanitize_girdle_engraving("&lt;i&gt;永遠&lt;/i&gt;") == "永遠"
    assert sanitize_girdle_engraving("x" * 200) == "x" * GIRDLE_ENGRAVING_MAX_LEN


def test_apply_accepts_snake_and_camel():
    camel = {"engravingGirdle": "永遠"}
    apply_girdle_engraving(camel)
    assert camel["engravingGirdle"] == "永遠"

    snake = {"engraving_girdle": "<b>Love 2026</b>"}
    apply_girdle_engraving(snake)
    assert snake["engravingGirdle"] == "Love 2026"
    assert snake["engraving_girdle"] == "Love 2026"


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

    body["engravingGirdle"] = "<img src=x>永遠"
    assert _validate_config(body) is None
    assert body["engravingGirdle"] == "永遠"


def test_pack_and_hydrate_keep_text_strip_html():
    cfg, *_ = pack_order_config(
        {
            "category": "pendant",
            "type": "four-prong",
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
            }
        }
    )
    assert order["engraving_girdle"] == "x永遠"


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
