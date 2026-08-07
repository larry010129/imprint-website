"""Lighthouse efficient-cache-lifetime: static assets need max-age ≥ 30d on Render."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")


@pytest.fixture
def render_client(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def local_client(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("RENDER_SERVICE_ID", raising=False)
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def test_versioned_css_gets_one_year_immutable(render_client):
    resp = render_client.get("/static/css/nav.css", params={"v": "4.12"})
    assert resp.status_code == 200
    assert resp.headers.get("Cache-Control") == "public, max-age=31536000, immutable"


def test_unversioned_static_meets_lighthouse_30d(render_client):
    resp = render_client.get("/static/js/htmx.min.js")
    assert resp.status_code == 200
    cc = resp.headers.get("Cache-Control") or ""
    assert "max-age=2592000" in cc
    assert "no-store" not in cc


def test_favicon_gets_long_cache_on_render(render_client):
    resp = render_client.get("/favicon.svg")
    assert resp.status_code == 200
    cc = resp.headers.get("Cache-Control") or ""
    assert "max-age=2592000" in cc


def test_html_not_long_cached_by_static_middleware(render_client):
    resp = render_client.get("/")
    assert resp.status_code == 200
    cc = (resp.headers.get("Cache-Control") or "").lower()
    assert "max-age=31536000" not in cc
    assert "max-age=2592000" not in cc


def test_local_dev_static_is_no_store(local_client):
    resp = local_client.get("/static/css/nav.css", params={"v": "4.12"})
    assert resp.status_code == 200
    assert resp.headers.get("Cache-Control") == "no-store"
