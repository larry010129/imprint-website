"""Shop stills map to shop-media/site-images. No live Storage required."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.storage import (
    encode_unicode_filename_stem,
    site_image_object_path,
    site_image_public_url,
)


STORAGE_ORIGIN = "https://abc123.supabase.co"
PUBLIC_PREFIX = f"{STORAGE_ORIGIN}/storage/v1/object/public/shop-media/site-images"


@pytest.fixture
def storage_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", STORAGE_ORIGIN)
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "shop-media")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)


def test_ascii_diamond_path_maps_to_site_images(storage_env):
    rel = "diamonds/matrix/round-white.png"
    assert site_image_object_path(rel) == f"site-images/{rel}"
    assert site_image_object_path(f"/static/images/{rel}") == f"site-images/{rel}"
    assert site_image_public_url(rel) == f"{PUBLIC_PREFIX}/{rel}"


def test_chinese_shop_product_leaf_uses_u_encode(storage_env):
    local = "/static/images/shop-product/gold/墜飾A_gold.png"
    leaf = f"{encode_unicode_filename_stem('墜飾A_gold')}.png"
    assert leaf.startswith("u-")
    assert site_image_object_path(local) == f"site-images/shop-product/gold/{leaf}"
    assert site_image_public_url(local) == (
        f"{PUBLIC_PREFIX}/shop-product/gold/{leaf}"
    )
    # Folder segments stay ASCII; only the leaf is encoded.
    assert "/gold/" in site_image_object_path(local)


def test_dotdot_rejected_in_mapping(storage_env):
    assert site_image_object_path("diamonds/../hero/x.jpg") is None
    assert site_image_object_path("/static/images/shop-product/gold/../../x.png") is None
    assert site_image_public_url("diamonds/foo/../../../etc/passwd") is None


def test_missing_supabase_url_keeps_disk_paths(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "")
    assert site_image_public_url("diamonds/matrix/round-white.png") is None


@pytest.fixture
def redirect_client(storage_env):
    from app.controllers.web_controller import mount_static

    app = FastAPI()
    mount_static(app)
    with TestClient(app) as client:
        yield client


def test_redirect_ascii_diamond(redirect_client):
    resp = redirect_client.get(
        "/static/images/diamonds/matrix/round-white.png?v=24",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == (
        f"{PUBLIC_PREFIX}/diamonds/matrix/round-white.png?v=24"
    )


def test_redirect_chinese_shop_product_leaf(redirect_client):
    leaf = f"{encode_unicode_filename_stem('墜飾A_gold')}.png"
    resp = redirect_client.get(
        "/static/images/shop-product/gold/墜飾A_gold.png",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == (
        f"{PUBLIC_PREFIX}/shop-product/gold/{leaf}"
    )


def test_redirect_rejects_dotdot(redirect_client):
    escaped = redirect_client.get(
        "/static/images/diamonds/%2e%2e/hero/x.jpg",
        follow_redirects=False,
    )
    location = escaped.headers.get("location", "")
    assert ".." not in location
    if escaped.status_code == 302:
        assert "/site-images/diamonds/" in location
        assert "/hero/" not in location
    else:
        assert escaped.status_code in (400, 404)
