"""Girdle emblem PNGs must not paint outside the engraving step (file-level)."""
import re
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
    assert "shop.css?v=6.65" in extra


def test_girdle_input_tokens_have_horizontal_gap():
    css = SHOP_CSS.read_text(encoding="utf-8")
    extra = CALC.read_text(encoding="utf-8").split("{% block extra_css %}", 1)[1].split("{% endblock %}", 1)[0]
    shop_input = css.split(".shop-fit .shop-girdle-engrave .cfg-engrave-input {", 1)[1].split("}", 1)[0]
    extra_input = extra.split(".shop-fit .shop-girdle-engrave .cfg-engrave-input {", 1)[1].split("}", 1)[0]
    shop_token = css.split(
        ".shop-fit .shop-girdle-engrave .cfg-engrave-input .cfg-emblem-token {", 1
    )[1].split("}", 1)[0]
    extra_token = extra.split(
        ".shop-fit .shop-girdle-engrave .cfg-engrave-input .cfg-emblem-token {", 1
    )[1].split("}", 1)[0]
    assert "gap: 4px" in shop_input
    assert "gap: 4px" in extra_input
    assert "margin-inline: 2px" in shop_token
    assert "margin-inline: 2px" in extra_token
    assert "overflow: visible" in shop_token
    assert "overflow: visible" in extra_token


def test_girdle_preview_tokens_have_horizontal_gap():
    css = SHOP_CSS.read_text(encoding="utf-8")
    extra = CALC.read_text(encoding="utf-8").split("{% block extra_css %}", 1)[1].split("{% endblock %}", 1)[0]
    shop_text = css.split(
        ".shop-fit .shop-girdle-engrave .cfg-engrave-preview-text {", 1
    )[1].split("}", 1)[0]
    extra_text = extra.split(
        ".shop-fit .shop-girdle-engrave .cfg-engrave-preview-text {", 1
    )[1].split("}", 1)[0]
    shop_token = css.split(
        ".shop-fit .shop-girdle-engrave .cfg-engrave-preview-text .cfg-emblem-token {", 1
    )[1].split("}", 1)[0]
    extra_token = extra.split(
        ".shop-fit .shop-girdle-engrave .cfg-engrave-preview-text .cfg-emblem-token {", 1
    )[1].split("}", 1)[0]
    assert "display: flex" in shop_text
    assert "display: flex" in extra_text
    assert "gap: 4px" in shop_text
    assert "gap: 4px" in extra_text
    assert "position: absolute" in shop_text
    assert "position: absolute" in extra_text
    assert "margin-inline" not in shop_token
    assert "margin-inline" not in extra_token
    assert "width: 18px" in shop_token
    assert "width: 18px" in extra_token


def test_emblem_imgs_have_intrinsic_size_fallback():
    src = GIRDLE_JS.read_text(encoding="utf-8")
    assert 'width="18" height="18"' in src
    shop = SHOP_JS.read_text(encoding="utf-8")
    assert "girdle-engrave.js?v=31" in shop
    hidden_clear = shop.split("function updateEngravingSteps()", 1)[1].split("function closeAllShopDropdowns", 1)[0]
    assert "shop-girdle-engrave-preview" in hidden_clear
    assert "preview.innerHTML = ''" in hidden_clear


def test_girdle_typed_text_is_not_alnum_gated():
    src = GIRDLE_JS.read_text(encoding="utf-8")
    assert "CHARSET_BASE" not in src
    assert "CHARSET_CJK" not in src
    assert "allowedCharRe" not in src
    assert "disallowedCharsRe" not in src
    assert "A-Za-z0-9" not in src
    assert "CONTROL_OR_BREAK" in src
    assert "setAllowChinese: function (flag)" in src
    assert "sanitizeTextNodes(input, false)" in src
    assert "stripCjk" in src
    shop = SHOP_JS.read_text(encoding="utf-8")
    assert "girdle-engrave.js?v=31" in shop
    registry = (ROOT / "content" / "site" / "page-registry.json").read_text(encoding="utf-8")
    assert "girdle-engrave.js?v=31" in registry


def test_girdle_cjk_only_when_allow_chinese():
    src = GIRDLE_JS.read_text(encoding="utf-8")
    assert "var allowChinese = !!opts.allowChinese" in src
    assert "if (!allowChinese) clean = stripCjk(clean)" in src
    assert "if (!allowChinese && CJK_CHAR.test(e.key))" in src
    # Punctuation / Latin stay outside the CJK strip class.
    cjk = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF]")
    kept = "LOVE / 2024 .@$#!%&*()_-+=[]{};:'\",.<>?"
    assert cjk.sub("", kept) == kept
    assert cjk.sub("", "愛.@$永遠") == ".@$"


def test_girdle_keeps_special_symbols():
    src = GIRDLE_JS.read_text(encoding="utf-8")
    assert (
        "CONTROL_OR_BREAK = /[\\u0000-\\u0008\\u000B\\u000C\\u000E-\\u001F\\u007F-\\u009F\\r\\n\\t]/g"
        in src
    )
    # Same class as CONTROL_OR_BREAK — controls/line-breaks only, not punctuation.
    control_or_break = re.compile(r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F\r\n\t]")
    kept = "LOVE / 2024 .@$#!%&*()_-+=[]{};:'\",.<>?"
    assert control_or_break.sub("", kept) == kept
    assert control_or_break.sub("", "愛.@$") == "愛.@$"


def test_girdle_placeholder_allows_punctuation_example():
    calc = CALC.read_text(encoding="utf-8")
    start = calc.find('id="shop-girdle-engrave-input"')
    assert start >= 0
    tag = calc[max(0, start - 80) : calc.find(">", start) + 1]
    assert 'data-placeholder="e.g. LOVE / 2024 / initials"' in tag
    assert "maxlength" not in tag.lower()
