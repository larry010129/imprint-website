"""Extensionless public URLs + legacy *.html 301 redirects."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")
# Canonical / og:url must use production host in these assertions.
os.environ["PUBLIC_SITE_URL"] = "https://www.imprintdiamond.com"

_CANONICAL_HREF = re.compile(
    r'<link\s+rel="canonical"\s+href="([^"]+)"',
    re.IGNORECASE,
)
_OG_URL = re.compile(
    r'<meta\s+property="og:url"\s+content="([^"]*)"',
    re.IGNORECASE,
)


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.mark.parametrize(
    "path",
    [
        "/about",
        "/faq",
        "/contact",
        "/what-is-dna-diamond",
        "/diamond-4c",
        "/lab-grown-diamond",
        "/diamond-comparison",
        "/journal",
        "/price",
        "/series",
        "/login",
    ],
)
def test_clean_public_url_200(client, path: str):
    resp = client.get(path)
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_journal_ssr_teaser_markup(client):
    resp = client.get("/journal")
    assert resp.status_code == 200
    assert "品牌日誌" in resp.text
    assert 'data-journal-ssr' in resp.text


def test_knowledge_nav_links_present(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert 'href="/diamond-4c"' in resp.text
    assert 'href="/lab-grown-diamond"' in resp.text
    assert 'href="/diamond-comparison"' in resp.text
    assert 'href="/series"' in resp.text
    assert 'href="/jewelry/"' in resp.text
    assert 'href="/jewelry/engagement/"' in resp.text


@pytest.mark.parametrize(
    ("legacy", "clean"),
    [
        ("/about.html", "/about"),
        ("/faq.html", "/faq"),
        ("/contact.html", "/contact"),
        ("/what-is-dna-diamond.html", "/what-is-dna-diamond"),
        ("/price.html", "/price"),
        ("/series.html", "/series"),
        ("/login.html", "/login"),
        ("/shop/quote-sheet.html", "/shop/quote-sheet"),
        ("/share/summary.html", "/share/summary"),
    ],
)
def test_html_url_301_to_clean(client, legacy: str, clean: str):
    resp = client.get(legacy, follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers.get("location") == clean


def test_html_redirect_preserves_query_string(client):
    resp = client.get("/about.html?utm=1&ref=nav", follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers.get("location") == "/about?utm=1&ref=nav"


def test_canonical_omits_html_extension(client):
    resp = client.get("/about")
    assert resp.status_code == 200
    assert 'rel="canonical"' in resp.text
    assert "about.html" not in resp.text.split('rel="canonical"', 1)[1][:200]
    assert 'href="https://www.imprintdiamond.com/about"' in resp.text


def test_about_canonical_is_absolute_https(client):
    resp = client.get("/about")
    assert resp.status_code == 200
    match = _CANONICAL_HREF.search(resp.text)
    assert match is not None
    assert match.group(1) == "https://www.imprintdiamond.com/about"


def test_jewelry_hub_301_to_home(client):
    resp = client.get("/jewelry/", follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers.get("location", "").split("?", 1)[0] == "/"


def test_404_is_noindex_and_omits_homepage_canonical(client):
    resp = client.get("/this-path-does-not-exist-404-test")
    assert resp.status_code == 404
    assert 'content="noindex, nofollow"' in resp.text
    # Soft-canonical to homepage was the bug; omit the tag entirely.
    assert _CANONICAL_HREF.search(resp.text) is None
    assert 'rel="canonical"' not in resp.text


def test_canonical_matches_og_url(client):
    resp = client.get("/about")
    assert resp.status_code == 200
    canonical = _CANONICAL_HREF.search(resp.text)
    og_url = _OG_URL.search(resp.text)
    assert canonical is not None
    assert og_url is not None
    assert canonical.group(1) == og_url.group(1)


@pytest.mark.parametrize(
    ("legacy", "clean"),
    [
        ("/admin.html", "/admin"),
        ("/admin1.html", "/admin"),
        ("/admin1-settings.html", "/admin/settings"),
        ("/admin1-plugins.html", "/admin/plugins"),
    ],
)
def test_admin_legacy_html_301_to_canonical(client, legacy: str, clean: str):
    """Legacy admin shells 301 to clean CMS paths (not served as FileResponse)."""
    resp = client.get(legacy, follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers.get("location") == clean


def test_admin_guest_redirects_to_login_with_next(client):
    """Unauthenticated /admin goes to login with next=/admin."""
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers.get("location") == "/login?next=/admin"


def test_admin1_login_html_redirects_to_login(client):
    resp = client.get("/admin1-login.html", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers.get("location") == "/login?next=/admin"


def test_routes_registry_has_no_html_public_paths():
    from config.routes import ALL_PAGES, STANDALONE_PAGES

    for meta in [*ALL_PAGES, *STANDALONE_PAGES]:
        assert not meta.route.endswith(".html"), meta.route
        assert not meta.canonical_path.endswith(".html"), meta.canonical_path
        for _label, href in meta.breadcrumbs:
            if href:
                assert not href.endswith(".html"), href
