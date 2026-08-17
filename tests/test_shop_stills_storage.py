"""Shop stills map to shop-media/site-images. No live Storage required."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.image_urls import (
    resolve_product_image_url,
    rewrite_shop_stills_in_html,
    share_image_url,
    static_url_exists,
)
from app.storage import (
    diamond_media_base,
    encode_unicode_filename_stem,
    rewrite_shop_still_url,
    site_image_object_path,
    site_image_public_url,
    site_images_public_base,
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
    assert diamond_media_base() == ""
    assert site_images_public_base() is None
    assert rewrite_shop_still_url("/static/images/products/category-ring.jpg") == (
        "/static/images/products/category-ring.jpg"
    )


def test_diamond_media_base_is_the_one_site_images_prefix(storage_env):
    assert diamond_media_base() == PUBLIC_PREFIX
    assert not diamond_media_base().endswith("/")
    assert site_images_public_base() == PUBLIC_PREFIX


def test_resolve_product_image_url_rewrites_seed_and_memorial_paths(storage_env):
    assert resolve_product_image_url("/static/images/products/white/pendant-A.png") == (
        f"{PUBLIC_PREFIX}/products/white/pendant-A.png"
    )
    assert resolve_product_image_url(
        "/static/images/diamonds/matrix/round-white.png"
    ) == f"{PUBLIC_PREFIX}/diamonds/matrix/round-white.png"
    leaf = f"{encode_unicode_filename_stem('耳飾A_gold')}.png"
    assert resolve_product_image_url(
        "/static/images/shop-product/gold/耳飾A_gold.png"
    ) == f"{PUBLIC_PREFIX}/shop-product/gold/{leaf}"
    assert resolve_product_image_url("/static/images/hero/keep.jpg") == (
        "/static/images/hero/keep.jpg"
    )


def test_share_image_url_avoids_double_site_prefix(storage_env):
    assert share_image_url("static/images/products/category-ring.jpg") == (
        f"{PUBLIC_PREFIX}/products/category-ring.jpg"
    )
    assert share_image_url("static/images/hero/imprint-diamond-family-memorial.jpg") == (
        "https://www.imprintdiamond.com/static/images/hero/"
        "imprint-diamond-family-memorial.jpg"
    )


def test_html_rewrite_maps_shop_stills_not_host_prefixed_og(storage_env):
    html = (
        '<img src="/static/images/diamonds/colors/blue-320.webp">'
        '<img src="/static/images/shop-product/gold/耳飾A_gold.png">'
        '<meta property="og:image" content="https://www.imprintdiamond.com/'
        'static/images/products/category-ring.jpg">'
    )
    out = rewrite_shop_stills_in_html(html)
    leaf = f"{encode_unicode_filename_stem('耳飾A_gold')}.png"
    assert f'src="{PUBLIC_PREFIX}/diamonds/colors/blue-320.webp"' in out
    assert f'src="{PUBLIC_PREFIX}/shop-product/gold/{leaf}"' in out
    assert (
        'content="https://www.imprintdiamond.com/static/images/products/category-ring.jpg"'
        in out
    )
    assert "imprintdiamond.com/https://" not in out


def test_shop_catalog_data_rewrites_at_runtime():
    src = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "public"
        / "js"
        / "shop-catalog-data.js"
    ).read_text(encoding="utf-8")
    assert "function imprintDiamondMediaBase()" in src
    assert "rewriteShopStillsDeep(global.shopCatalogData)" in src
    assert "/static/images/products/white/pendant-A.png" in src


def test_static_url_exists_treats_shop_stills_as_present(storage_env):
    assert static_url_exists("/static/images/diamonds/matrix/round-white.png")
    assert static_url_exists("/static/images/products/category-ring.jpg")
    assert static_url_exists("/static/images/shop-product/gold/ear.png")


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
