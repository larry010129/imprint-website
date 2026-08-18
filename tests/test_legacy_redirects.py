"""Cutover 301s: old /imprint Google URLs + retired /jewelry tree."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from app.legacy_redirects import DNA_SHOP_IDS, lookup_legacy_redirect

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")


@pytest.fixture(scope="module")
def client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.controllers.web_controller import register_pages

    app = FastAPI()
    register_pages(app)
    with TestClient(app) as c:
        yield c


def _location_path(location: str) -> str:
    return (location or "").split("?", 1)[0]


@pytest.mark.parametrize(
    ("path", "dest"),
    [
        ("/imprint", "/"),
        ("/imprint/", "/"),
        ("/imprint/index", "/"),
        ("/imprint/index.php", "/"),
        ("/imprint/shop", "/series"),
        ("/imprint/shop/", "/series"),
        ("/imprint/jewelry", "/"),
        ("/imprint/jewelry/", "/"),
        ("/imprint/first-love", "/series/first-love/"),
        ("/imprint/pet", "/series/pet/"),
        ("/imprint/love", "/series/love/"),
        ("/imprint/family", "/series/family/"),
        ("/imprint/heirloom", "/series/heirloom/"),
        ("/imprint/shop/18", "/series/first-love/"),
        ("/imprint/shop/8", "/series/pet/"),
        ("/imprint/shop/11", "/series/love/"),
        ("/imprint/shop/19", "/series/family/"),
        ("/imprint/shop/20", "/series/heirloom/"),
        ("/jewelry", "/"),
        ("/jewelry/", "/"),
        ("/jewelry/engagement/", "/"),
        ("/jewelry/rings/", "/"),
        ("/jewelry/necklaces/", "/"),
        ("/jewelry/earrings/", "/"),
        ("/jewelry/bracelets/", "/"),
        ("/jewelry/foo", "/"),
        ("/jewelry/rings/classic-solitaire/", "/"),
    ],
)
def test_legacy_paths_301(client, path: str, dest: str):
    resp = client.get(path, follow_redirects=False)
    assert resp.status_code == 301, path
    assert _location_path(resp.headers.get("location", "")) == dest


def test_imprint_index_query_301_to_home(client):
    resp = client.get("/imprint/index?srsltid=x", follow_redirects=False)
    assert resp.status_code == 301
    assert _location_path(resp.headers.get("location", "")) == "/"


def test_imprint_shop_does_not_go_to_jewelry(client):
    resp = client.get("/imprint/shop", follow_redirects=False)
    assert resp.status_code == 301
    location = resp.headers.get("location", "")
    assert _location_path(location) == "/series"
    assert "/jewelry" not in location


def test_series_hub_stays_200(client):
    resp = client.get("/series", follow_redirects=False)
    assert resp.status_code == 200


def test_unknown_path_is_http_404(client):
    resp = client.get("/this-path-does-not-exist-404-test", follow_redirects=False)
    assert resp.status_code == 404


def test_unknown_imprint_path_is_http_404(client):
    resp = client.get("/imprint/no-such-legacy-page", follow_redirects=False)
    assert resp.status_code == 404


def test_unknown_shop_id_is_http_404(client):
    resp = client.get("/imprint/shop/99", follow_redirects=False)
    assert resp.status_code == 404


def test_dna_shop_id_map_covers_five_series():
    assert DNA_SHOP_IDS == {
        "8": "/series/pet/",
        "11": "/series/love/",
        "18": "/series/first-love/",
        "19": "/series/family/",
        "20": "/series/heirloom/",
    }
    assert lookup_legacy_redirect("/imprint/shop/18") == "/series/first-love/"
    assert lookup_legacy_redirect("/jewelry/anything") == "/"
    assert lookup_legacy_redirect("/imprint/shop") == "/series"
    assert lookup_legacy_redirect("/imprint/missing") is None
