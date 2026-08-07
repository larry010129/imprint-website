"""Homepage should not ship sync render-blocking CSS network requests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")
BASE = ROOT / "content" / "site" / "templates" / "layouts" / "base.html"
INDEX = ROOT / "content" / "site" / "templates" / "pages" / "index.html"
NAV_CRITICAL = ROOT / "public" / "css" / "nav-critical.css"
GHIBLI_CRITICAL = ROOT / "public" / "css" / "home-ghibli-critical.css"


def test_home_inlines_nav_and_hero_critical():
    base = BASE.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    assert "inline_css('nav-critical.css')" in base
    assert "inline_css('home-ghibli-critical.css')" in index
    assert NAV_CRITICAL.is_file()
    assert GHIBLI_CRITICAL.is_file()


def test_home_sync_nav_defers_ghibli_remainder():
    """nav.css is sync (InteractiveHoverButton); ghibli remainder still deferred."""
    base = BASE.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    assert 'nav.css?v=' in base
    # Sync all pages — do not defer nav.css (hover CTA needs full rules)
    assert 'href="/static/css/nav.css?v=' in base
    nav_link_idx = base.index('href="/static/css/nav.css?v=')
    nav_snippet = base[nav_link_idx : nav_link_idx + 80]
    assert 'media="print"' not in nav_snippet
    assert "is_home" in base and "nav-critical.css" in base
    assert 'home-ghibli.css?v=' in index and 'media="print"' in index
    # No sync stylesheet link for hero critical on home
    assert 'href="/static/css/home-ghibli-critical.css' not in index


def test_hero_copy_stays_above_media_in_critical():
    """Regression: copy must stack above hc-media (hero stacking bug)."""
    css = GHIBLI_CRITICAL.read_text(encoding="utf-8")
    assert ".page-home .hc-media{" in css
    assert "z-index:0" in css
    assert ".page-home .hc-scrim{" in css
    scrim_pos = css.index(".page-home .hc-scrim{")
    assert "z-index:1" in css[scrim_pos : scrim_pos + 80]
    assert ".gh-hc-copy{" in css or ".page-home .hc-copy," in css
    # copy block declares z-index:2 after media z-index:0
    media_pos = css.index(".page-home .hc-media{")
    copy_pos = css.index(".page-home .hc-copy,")
    assert copy_pos > media_pos
    copy_block = css[copy_pos : copy_pos + 220]
    assert "position:relative" in copy_block
    assert "z-index:2" in copy_block
    assert "display:flex" in copy_block


def test_hc_dot_and_nav_tap_targets_in_critical():
    """WCAG 2.5.8: carousel dots + closed-bar cart/burger ≥44px on first paint."""
    hero = GHIBLI_CRITICAL.read_text(encoding="utf-8")
    nav = NAV_CRITICAL.read_text(encoding="utf-8")
    assert ".page-home .hc-dot{" in hero
    assert "var(--tap-target-min, 44px)" in hero
    assert ".page-home .hc-dot::after{" in hero
    assert ".nav-cart-link{" in nav
    assert "var(--tap-target-min, 44px)" in nav
    assert ".nav-burger{" in nav
    assert "width:44px" in nav or "var(--tap-target-min,44px)" in nav


def test_mobile_hc_copy_keeps_page_home_specificity():
    """Merge-race: mobile padding must beat .page-home .hc-copy desktop rule."""
    css = GHIBLI_CRITICAL.read_text(encoding="utf-8")
    assert css.count(".page-home .hc-copy,\n  .gh-hc-copy{") >= 2 or (
        css.count(".page-home .hc-copy,") >= 3
    )


def test_critical_css_budget():
    """Keep inlined critical CSS small enough to justify inlining over blocking fetch."""
    nav = NAV_CRITICAL.stat().st_size
    hero = GHIBLI_CRITICAL.stat().st_size
    # nav-critical includes InteractiveHoverButton hover (first paint)
    assert nav < 12_000, f"nav-critical too fat: {nav}"
    assert hero < 18_000, f"home-ghibli-critical too fat: {hero}"


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def test_live_home_has_no_sync_critical_css(client):
    text = client.get("/").text
    assert ".nav-inner{" in text
    assert ".gh-hero--carousel" in text
    assert 'href="/static/css/home-ghibli-critical.css' not in text
    assert 'class="nav-ihb"' in text
    assert ".btn-neon" in text
    assert ".nav-ihb:hover" in text or ".nav-ihb:hover," in text
    # nav.css loads sync (not media=print)
    pos = text.find('href="/static/css/nav.css')
    assert pos >= 0
    snippet = text[pos : pos + 100]
    assert 'media="print"' not in snippet, snippet
