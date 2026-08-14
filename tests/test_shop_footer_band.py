"""Shop footer must be last in-flow content — no white band under the legal bar."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_base_layout_skips_cms_end_stack_on_shop_calculator():
    base = (ROOT / "content/site/templates/layouts/base.html").read_text(encoding="utf-8")
    assert "{% if not is_shop_calculator %}" in base
    gated = base.split("{% if not is_shop_calculator %}", 1)[1].split("{% endif %}", 1)[0]
    assert "cms_anchor = 'end'" in gated
    assert "site_section_stack.html" in gated
    after_main = base.split("</main>", 1)[1]
    assert "site_section_stack.html" not in after_main.split("{% include \"partials/footer.html\" %}", 1)[0]


def test_shop_mobile_bar_padding_lives_on_main_not_body():
    css = (ROOT / "public/css/shop.css").read_text(encoding="utf-8")
    body_rule = css.split("body.shop-mobile-bar {", 1)[1].split("}", 1)[0]
    assert "padding-bottom: 0" in body_rule
    assert "body.shop-mobile-bar > main" in css
    assert "body.shop-mobile-bar {\n    padding-bottom: calc" not in css
    assert "body.shop-mobile-bar {\n  padding-bottom: calc" not in css


def test_shop_wizard_hides_cms_end_stack():
    css = (ROOT / "public/css/shop-wizard.css").read_text(encoding="utf-8")
    rule = css.split(
        '.shop-calculator-page > .cms-site-stack[data-cms-anchor="end"] {', 1
    )[1].split("}", 1)[0]
    assert "display: none" in rule
