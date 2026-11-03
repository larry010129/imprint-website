"""*.onrender.com page requests 301 to PUBLIC_SITE_URL; API/health stay put."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import create_app
from app.host_redirect import onrender_redirect_location

RENDER_HOST = "imprint-website-kh6x.onrender.com"
PUBLIC = "https://www.imprint-diamond.com"


@pytest.fixture
def public_site(monkeypatch):
    monkeypatch.setenv("PUBLIC_SITE_URL", PUBLIC)
    monkeypatch.delenv("SITE_URL", raising=False)


def test_render_host_page_redirects_with_query(public_site):
    assert (
        onrender_redirect_location(RENDER_HOST, "GET", "/series/pet/", "a=1")
        == f"{PUBLIC}/series/pet/?a=1"
    )
    assert onrender_redirect_location(f"{RENDER_HOST}:443", "HEAD", "/", "") == f"{PUBLIC}/"


@pytest.mark.parametrize("path", ["/health", "/robots.txt", "/api/gold-refresh", "/api/v1/cart"])
def test_render_host_exempt_paths_stay(public_site, path):
    assert onrender_redirect_location(RENDER_HOST, "GET", path, "") is None


def test_render_host_post_is_not_redirected(public_site):
    assert onrender_redirect_location(RENDER_HOST, "POST", "/login", "") is None


@pytest.mark.parametrize("host", ["www.imprint-diamond.com", "imprintdiamond.com", "localhost", "testserver", ""])
def test_other_hosts_never_redirect(public_site, host):
    assert onrender_redirect_location(host, "GET", "/", "") is None


@pytest.mark.parametrize(
    "value",
    ["", "http://www.imprint-diamond.com", f"https://{RENDER_HOST}", "https://other.onrender.com"],
)
def test_no_redirect_without_safe_public_url(monkeypatch, value):
    monkeypatch.setenv("PUBLIC_SITE_URL", value)
    monkeypatch.delenv("SITE_URL", raising=False)
    assert onrender_redirect_location(RENDER_HOST, "GET", "/", "") is None


def test_app_middleware_sends_301(public_site):
    client = TestClient(create_app())
    resp = client.get("/about", headers={"Host": RENDER_HOST}, follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["location"] == f"{PUBLIC}/about"


def test_app_health_on_render_host_stays_200(public_site):
    client = TestClient(create_app())
    resp = client.get("/health", headers={"Host": RENDER_HOST}, follow_redirects=False)
    assert resp.status_code == 200
    assert resp.json()["service"] == "imprint-api"
