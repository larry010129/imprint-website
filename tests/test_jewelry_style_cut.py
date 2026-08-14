"""Retired jewelry style PDPs 301 to /shop/calculator/; hubs stay as shells."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from config.routes import ALL_PAGES, JEWELRY_STYLE_REDIRECTS

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
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def test_sixteen_style_redirects_defined():
    assert len(JEWELRY_STYLE_REDIRECTS) == 16
    assert all(target == "/shop/calculator/" for target in JEWELRY_STYLE_REDIRECTS.values())
    live = {page.route for page in ALL_PAGES}
    assert live.isdisjoint(JEWELRY_STYLE_REDIRECTS)


@pytest.mark.parametrize("path", sorted(JEWELRY_STYLE_REDIRECTS))
def test_style_pdp_301_to_calculator(client, path: str):
    resp = client.get(path, follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["location"] == "/shop/calculator/"


def test_style_pdp_301_keeps_query(client):
    resp = client.get(
        "/jewelry/rings/classic-solitaire/?utm=1",
        follow_redirects=False,
    )
    assert resp.status_code == 301
    assert resp.headers["location"] == "/shop/calculator/?utm=1"


@pytest.mark.parametrize("path", HUBS)
def test_hub_shell_no_style_cards(client, path: str):
    resp = client.get(path)
    assert resp.status_code == 200
    html = resp.text
    assert "shop-grid" not in html
    assert "shop-price" not in html
    assert "即時試算" not in html
    assert "查看客製選項" not in html
    assert 'href="/shop/calculator/"' in html
    assert "id=\"cfgForm\"" not in html
    assert "id=\"configurator\"" not in html
    for slug in JEWELRY_STYLE_REDIRECTS:
        assert slug not in html
    assert "earring-" not in html
    assert "bracelet-" not in html
    assert "category-earring" not in html
    assert "category-bracelet" not in html
    assert "necklace-halo-pendant" not in html
    assert "necklace-bar" not in html
    assert "necklace-double-layer" not in html


def test_jewelry_index_and_calculator_stay(client):
    assert client.get("/jewelry/").status_code == 200
    assert client.get("/shop/calculator/").status_code == 200


def test_sitemap_and_registry_drop_style_slugs():
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    registry = json.loads((ROOT / "content" / "site" / "page-registry.json").read_text(encoding="utf-8"))
    routes = {entry["route"] for entry in registry}
    for slug in JEWELRY_STYLE_REDIRECTS:
        assert slug not in sitemap
        assert f"https://www.imprintdiamond.com{slug}" not in sitemap
        assert slug not in routes
    for hub in HUBS:
        assert f"https://www.imprintdiamond.com{hub}" in sitemap
        assert hub in routes
