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


def test_home_defers_htmx_gtag_and_extras(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # No eager htmx script tag; injector string still present for nav hx-*.
    assert '<script src="/static/js/htmx.min.js" defer>' not in html
    assert "HTMX_FALLBACK_MS = 12000" in html
    assert "/static/js/htmx.min.js" in html

    assert "GTM-KD4FZ458" in html
    assert "G-J5QPK34V89" not in html
    assert "gtagMinDelayMs" not in html
    assert "gtag/js" not in html

    assert "HOME_EXTRAS_MS = 10000" in html
    assert "home-wall.js?v=4" in html
    assert "home-banners.js?v=14" in html

    assert "main.js?v=2.9" in html
    assert "ringflip.js" not in html

    # Botpress stays click-only (no static inject script tag).
    assert "loadImprintChat" in html
    assert 'src="https://cdn.botpress.cloud' not in html

    assert "FAB_FALLBACK_MS = 12000" in html


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
