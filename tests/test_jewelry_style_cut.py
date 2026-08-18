"""Retired jewelry tree 301s home. Hubs must not stay HTTP 200."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from config.routes import ALL_PAGES, JEWELRY_STYLE_REDIRECTS  # ALL_PAGES still lists hubs; HTTP must 301

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")

ROOT = Path(__file__).resolve().parents[1]
HUBS = (
    "/jewelry/rings/",
    "/jewelry/earrings/",
    "/jewelry/necklaces/",
    "/jewelry/bracelets/",
)


@pytest.fixture(scope="module")
def client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.controllers.web_controller import register_pages

    app = FastAPI()
    register_pages(app)
    with TestClient(app) as c:
        yield c


def test_sixteen_style_redirects_defined():
    assert len(JEWELRY_STYLE_REDIRECTS) == 16
    assert all(target == "/" for target in JEWELRY_STYLE_REDIRECTS.values())
    live = {page.route for page in ALL_PAGES}
    assert live.isdisjoint(JEWELRY_STYLE_REDIRECTS)


@pytest.mark.parametrize("path", sorted(JEWELRY_STYLE_REDIRECTS))
def test_style_pdp_301_to_home(client, path: str):
    resp = client.get(path, follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["location"].split("?", 1)[0] == "/"


def test_style_pdp_301_keeps_query(client):
    resp = client.get(
        "/jewelry/rings/classic-solitaire/?utm=1",
        follow_redirects=False,
    )
    assert resp.status_code == 301
    assert resp.headers["location"].split("?", 1)[0] == "/"


@pytest.mark.parametrize("path", HUBS)
def test_hub_301_to_home(client, path: str):
    resp = client.get(path, follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["location"].split("?", 1)[0] == "/"


def test_jewelry_index_301_calculator_stays(client):
    jewelry = client.get("/jewelry/", follow_redirects=False)
    assert jewelry.status_code == 301
    assert jewelry.headers["location"].split("?", 1)[0] == "/"
    assert client.get("/shop/calculator/").status_code == 200


def test_sitemap_and_registry_drop_style_slugs():
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    for slug in JEWELRY_STYLE_REDIRECTS:
        assert slug not in sitemap
        assert f"https://www.imprintdiamond.com{slug}" not in sitemap
        assert f"https://imprint-diamond.com{slug}" not in sitemap
    for hub in HUBS:
        assert f"https://www.imprintdiamond.com{hub}" not in sitemap
        assert f"https://imprint-diamond.com{hub}" not in sitemap
