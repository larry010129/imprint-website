"""Checkout confirm notice flashes twice on first paint; mobile bar stays CTA-only."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "public" / "css" / "checkout-page.css"
PANEL = ROOT / "content" / "site" / "templates" / "partials" / "htmx" / "checkout_panel.html"
PAGE = ROOT / "content" / "site" / "templates" / "pages" / "checkout.html"


def test_notice_box_pulses_twice_then_stops():
    css = CSS.read_text(encoding="utf-8")
    rule = css.split(".checkout-notice {", 1)[1].split("}", 1)[0]
    assert "animation: checkout-notice-flash 0.65s ease-in-out 2" in rule
    assert "infinite" not in rule
    assert "@keyframes checkout-notice-flash" in css


def test_notice_flash_skips_when_reduced_motion():
    css = CSS.read_text(encoding="utf-8")
    reduced = css.split("@media (prefers-reduced-motion: reduce) {", 1)[1]
    notice = reduced.split(".checkout-notice {", 1)[1].split("}", 1)[0]
    assert "animation: none" in notice


def test_mobile_bar_stays_cta_only():
    css = CSS.read_text(encoding="utf-8")
    bar = css.split("[data-checkout-root] .checkout-mobile-bar {", 1)[1]
    first_rule = bar.split("}", 1)[0]
    assert "animation" not in first_rule
    panel = PANEL.read_text(encoding="utf-8")
    mobile = panel.split('class="checkout-mobile-bar"', 1)[1]
    assert "checkout-notice" not in mobile
    assert "送出後仍需專人確認" not in mobile


def test_notice_copy_unchanged_and_css_cache_busted():
    panel = PANEL.read_text(encoding="utf-8")
    assert '<div class="checkout-notice" role="status">' in panel
    assert "送出後仍需專人確認" in panel
    assert "線上送出僅代表收到您的訂製申請" in panel
    extra = PAGE.read_text(encoding="utf-8").split("{% block extra_css %}", 1)[1].split(
        "{% endblock %}", 1
    )[0]
    assert "checkout-page.css?v=18" in extra
