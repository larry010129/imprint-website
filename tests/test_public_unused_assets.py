"""Public pages must not ship unused JS/CSS (dead islands, jewelry-only bundles)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")

RETIRED_ISLANDS = (
    "/static/react/faq.js",
    "/static/react/stories.js",
    "/static/react/auth.js",
    "/static/react/checkout.js",
    "/static/react/dna-diamond.js",
    "/static/react/admin-tables.js",
    "/static/react/nav.js",
    "/static/react/footer.js",
)

JEWELRY_ONLY_SCRIPTS = (
    "/static/js/pdgallery.js",
    "/static/js/configurator.js",
    "/static/js/pricing-config.js",
    "/static/js/girdle-engrave.js",
)

SKIP_HOME_CSS_ROUTES = (
    "/",
    "/about",
    "/stories",
    "/journal",
    "/gold-price",
    "/shop/calculator/",
    "/what-is-dna-diamond",
    "/diamond-4c",
    "/lab-grown-diamond",
    "/diamond-comparison",
    "/faq",
    "/contact",
    "/price",
    "/privacy",
    "/terms",
    "/return-policy",
    "/jewelry/rings/classic-solitaire/",
)

KEEP_HOME_CSS_ROUTES = (
    "/series/love/",
    "/jewelry/",
    "/jewelry/rings/",
    "/jewelry/engagement/",
)


@pytest.fixture(scope="module")
def client():
    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def test_jewelry_hub_keeps_ringflip_drops_configurator(client):
    html = client.get("/jewelry/").text
    assert "ringflip.js?v=1" in html
    for src in JEWELRY_ONLY_SCRIPTS:
        assert src not in html, src
    jewelry = (
        ROOT / "content" / "site" / "templates" / "pages" / "jewelry" / "index.html"
    ).read_text(encoding="utf-8")
    assert "ringflip.js?v=1" in jewelry
    for src in JEWELRY_ONLY_SCRIPTS:
        assert src not in jewelry, src


@pytest.mark.parametrize("path", SKIP_HOME_CSS_ROUTES)
def test_public_pages_skip_unused_home_css(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, path
    assert "/static/css/home.css" not in resp.text, path
    assert "GTM-KD4FZ458" in resp.text
    assert "G-J5QPK34V89" not in resp.text
    for island in RETIRED_ISLANDS:
        assert island not in resp.text, f"{path} still loads {island}"


@pytest.mark.parametrize("path", KEEP_HOME_CSS_ROUTES)
def test_jewelry_and_series_detail_keep_home_css(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, path
    assert "/static/css/home.css" in resp.text, path
    for src in JEWELRY_ONLY_SCRIPTS:
        assert src not in resp.text, f"{path} unexpectedly loads {src}"


def test_shop_calculator_unchanged_and_skips_home_css(client):
    html = client.get("/shop/calculator/").text
    assert "/static/css/home.css" not in html
    assert "/static/js/shop.js?v=166" in html
    assert "/static/js/shop-pricing-local.js" in html
    assert "GTM-KD4FZ458" in html
    shop = (ROOT / "public" / "js" / "shop.js").read_text(encoding="utf-8")
    pricing = (ROOT / "public" / "js" / "shop-pricing-local.js").read_text(encoding="utf-8")
    assert "function buildQuotePayload" in shop or "buildQuotePayload" in shop
    assert "ImprintPricing" in pricing or "carat" in pricing


def test_quote_share_keep_gtm_skip_retired_islands(client):
    for path in ("/quote-sheet", "/share/summary"):
        html = client.get(path).text
        assert "GTM-KD4FZ458" in html
        assert "G-J5QPK34V89" not in html
        for island in RETIRED_ISLANDS:
            assert island not in html, f"{path} still loads {island}"


def test_page_registry_has_no_retired_islands_or_jewelry_hub_bundles():
    registry = json.loads(
        (ROOT / "content" / "site" / "page-registry.json").read_text(encoding="utf-8")
    )
    blob = json.dumps(registry, ensure_ascii=False)
    for needle in (
        "react/faq.js",
        "react/stories.js",
        "react/auth.js",
        "react/checkout.js",
        "react/dna-diamond.js",
        "pdgallery.js",
        "configurator.js",
        "G-J5QPK34V89",
    ):
        assert needle not in blob, needle
    jewelry = next(row for row in registry if row["route"] == "/jewelry/")
    srcs = [s.get("src", "") for s in jewelry["extra_scripts"]]
    assert any("ringflip.js" in src for src in srcs)
    assert not (ROOT / "frontend" / "src" / "components" / "Footer4Col.tsx").is_file()
    assert not (ROOT / "public" / "js" / "stories.js").is_file()
    engraving = ROOT / "public" / "images" / "engraving"
    assert (engraving / "cat-paw.png").is_file()
    assert (engraving / "heart.png").is_file()
    layout = (ROOT / "content" / "site" / "templates" / "layouts" / "base.html").read_text(
        encoding="utf-8"
    )
    assert "GTM-KD4FZ458" in layout
    assert "G-J5QPK34V89" not in layout
