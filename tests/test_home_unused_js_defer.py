"""Homepage unused-JS: large vendors stay out of first paint / PSI window."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")


@pytest.fixture(scope="module")
def client():
    from app import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_home_defers_htmx_gtag_and_extras(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # No eager htmx script tag; injector string still present for nav hx-*.
    assert '<script src="/static/js/htmx.min.js" defer>' not in html
    assert "HTMX_FALLBACK_MS = 12000" in html
    assert "/static/js/htmx.min.js" in html

    assert "GTM-KD4FZ458" in html
    assert "function injectGtm" in html
    assert "GTM_FALLBACK_MS = 12000" in html
    assert "https://www.googletagmanager.com/gtm.js?id=" in html
    assert "G-J5QPK34V89" not in html
    assert "gtagMinDelayMs" not in html
    assert "gtag/js" not in html
    assert "AW-18310006207" not in html

    assert "HOME_WALL_MS = 10000" in html
    assert "home-wall.js?v=4" in html
    assert "home-banners.js?v=13" in html

    assert "main.js?v=2.10" in html
    assert "ringflip.js" not in html

    # Botpress stays click-only (no static inject script tag).
    assert "loadImprintChat" in html
    assert 'src="https://cdn.botpress.cloud' not in html

    assert "FAB_FALLBACK_MS = 12000" in html


PUBLIC_GTM_TEMPLATES = (
    "content/site/templates/layouts/base.html",
    "content/site/templates/layouts/base-auth.html",
    "content/site/templates/pages/shop/quote-sheet.html",
    "content/site/templates/pages/share/summary.html",
)


def _assert_deferred_gtm(html: str) -> None:
    assert "GTM-KD4FZ458" in html
    assert html.count("GTM-KD4FZ458") == 2
    assert "function injectGtm" in html
    assert "GTM_FALLBACK_MS = 12000" in html
    assert "addEventListener('load', scheduleGtm)" in html
    assert "https://www.googletagmanager.com/gtm.js?id=" in html
    assert "https://www.googletagmanager.com/ns.html?id=GTM-KD4FZ458" in html
    assert '<script src="https://www.googletagmanager.com/gtm.js' not in html
    assert "G-J5QPK34V89" not in html
    assert "gtagMinDelayMs" not in html
    assert "gtag/js" not in html
    assert "AW-18310006207" not in html
    assert "GTM-" in html
    assert html.count("GTM-") == html.count("GTM-KD4FZ458")


def test_public_layouts_share_one_deferred_gtm_snippet():
    head = (ROOT / "content/site/templates/partials/gtm-head.html").read_text(
        encoding="utf-8"
    )
    assert "GTM-KD4FZ458" in head
    assert head.count("GTM-") == 1
    assert "function injectGtm" in head
    assert "GTM_FALLBACK_MS = 12000" in head
    assert "G-J5QPK34V89" not in head
    assert "gtag/js" not in head
    assert "AW-18310006207" not in head

    for rel in PUBLIC_GTM_TEMPLATES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert '{% include "partials/gtm-head.html" %}' in text
        assert "ns.html?id=GTM-KD4FZ458" in text
        assert text.count("GTM-KD4FZ458") == 1


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")
def test_home_auth_quote_and_share_defer_gtm(client):
    for path in ("/", "/login", "/quote-sheet", "/share/summary"):
        resp = client.get(path)
        assert resp.status_code == 200, path
        _assert_deferred_gtm(resp.text)


def test_csp_still_omits_ads_collect_hosts():
    from app import HTML_CONTENT_SECURITY_POLICY

    assert "doubleclick.net" not in HTML_CONTENT_SECURITY_POLICY
    assert "googleads" not in HTML_CONTENT_SECURITY_POLICY


def test_ringflip_split_out_of_main():
    main = (ROOT / "public" / "js" / "main.js").read_text(encoding="utf-8")
    assert "getElementById('rfTrack')" not in main
    assert (ROOT / "public" / "js" / "ringflip.js").is_file()
    jewelry = (
        ROOT / "content" / "site" / "templates" / "pages" / "jewelry" / "index.html"
    ).read_text(encoding="utf-8")
    assert "ringflip.js?v=1" in jewelry


def test_shop_third_party_and_quote_work_is_deferred_and_deduplicated():
    botpress = (
        ROOT / "content" / "site" / "templates" / "partials" / "botpress-webchat.html"
    ).read_text(encoding="utf-8")
    tour = (
        ROOT / "content" / "site" / "templates" / "partials" / "shop-tour-react-js.html"
    ).read_text(encoding="utf-8")
    shop = (ROOT / "public" / "js" / "shop.js").read_text(encoding="utf-8")

    assert "scheduleIdlePrefetch" not in botpress
    assert "/static/css/shop-tour.css" not in (
        ROOT / "content" / "site" / "templates" / "partials" / "shop-tour-react-css.html"
    ).read_text(encoding="utf-8")
    assert "import(\"/static/react/shop-tour.js?v=18\")" in tour
    assert "pointerdown" not in tour
    assert "keydown" not in tour
    assert "data-shop-tour-start" in tour
    assert "requestIdleCallback" not in tour
    assert "shopRequestInflight" in shop
    assert "quoteCache" in shop
    assert "activeQuoteController?.abort()" in shop
    assert "JSON.stringify(buildQuotePayload())" in shop
