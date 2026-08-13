"""Girdle emblem PNGs must not paint outside the engraving step (file-level)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOP_JS = ROOT / "public" / "js" / "shop.js"
SHOP_CSS = ROOT / "public" / "css" / "shop.css"
GIRDLE_JS = ROOT / "public" / "js" / "girdle-engrave.js"
CALC = ROOT / "content" / "site" / "templates" / "pages" / "shop" / "calculator.html"


def test_config_chips_use_text_not_emblem_html():
    src = SHOP_JS.read_text(encoding="utf-8")
    chips = src.split("function updateConfigChips()", 1)[1].split("function effectiveColor()", 1)[0]
    assert "toDisplayHtml" not in chips
    assert "span.innerHTML" not in chips
    assert "span.textContent = tr('step_engraving_girdle')" in chips


def test_girdle_step_hidden_is_display_none():
    css = SHOP_CSS.read_text(encoding="utf-8")
    hidden = css.split("#engraving-girdle-step.hidden,", 1)[1].split("}", 1)[0]
    assert "display: none" in hidden
    assert ".hidden { display: none !important; }" in css
    extra = CALC.read_text(encoding="utf-8").split("{% block extra_css %}", 1)[1].split("{% endblock %}", 1)[0]
    assert ".hidden { display: none !important; }" in extra


def test_girdle_preview_wrap_clips_overlay():
    css = SHOP_CSS.read_text(encoding="utf-8")
    wrap = css.split(".shop-fit .shop-girdle-engrave .cfg-engrave-preview {", 1)[1].split("}", 1)[0]
    assert "overflow: hidden" in wrap
    assert "position: relative" in wrap
    extra = CALC.read_text(encoding="utf-8").split("{% block extra_css %}", 1)[1].split("{% endblock %}", 1)[0]
    extra_wrap = extra.split(".shop-fit .shop-girdle-engrave .cfg-engrave-preview {", 1)[1].split("}", 1)[0]
    assert "overflow: hidden" in extra_wrap
    assert "shop.css?v=6.54" in extra


def test_emblem_imgs_have_intrinsic_size_fallback():
    src = GIRDLE_JS.read_text(encoding="utf-8")
    assert 'width="18" height="18"' in src
    shop = SHOP_JS.read_text(encoding="utf-8")
    assert "girdle-engrave.js?v=25" in shop
    hidden_clear = shop.split("function updateEngravingSteps()", 1)[1].split("function closeAllShopDropdowns", 1)[0]
    assert "shop-girdle-engrave-preview" in hidden_clear
    assert "preview.innerHTML = ''" in hidden_clear
