"""List/detail catalog split — lite payload, full detail, product endpoint."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import load_dotenv

from app.catalog import (
    build_catalog_product,
    build_catalog_product_lite,
    build_catalog_response,
    normalize_catalog_detail,
)

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")

SUPABASE_PRODUCT = (
    "https://abc123.supabase.co/storage/v1/object/public/shop-media/products/x.webp"
)


def _product_row(product_id="prod-scale-1", category="ring", published=True):
    return {
        "id": product_id,
        "category": category,
        "name_zh": "測試戒",
        "name_en": "Test Ring",
        "description_zh": "說明",
        "description_en": "Desc",
        "default_color": "white",
        "sort_order": 0,
        "is_published": published,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }


def _variants():
    return [
        {"gold": "14k", "carat": "0.3", "weight_chin": 1.2},
        {"gold": "18k", "carat": "0.5", "weight_chin": 1.4},
    ]


def _images():
    return [{"color": "white-white", "file_path": SUPABASE_PRODUCT}]


def test_normalize_catalog_detail_defaults_lite():
    assert normalize_catalog_detail(None) == "lite"
    assert normalize_catalog_detail("") == "lite"
    assert normalize_catalog_detail("LITE") == "lite"
    assert normalize_catalog_detail("full") == "full"
    assert normalize_catalog_detail("FULL") == "full"


def test_build_catalog_product_lite_omits_heavy_maps():
    entry = build_catalog_product_lite(_product_row(), _variants(), _images())

    assert entry["id"] == "prod-scale-1"
    assert entry["nameZh"] == "測試戒"
    assert entry["golds"] == ["14k", "18k"]
    assert entry["carats"] == ["0.3", "0.5"]
    assert "white-white" in entry["colors"]
    assert entry["thumbUrl"] == SUPABASE_PRODUCT
    assert "weights" not in entry
    assert "images" not in entry
    assert "manualPrices" not in entry
    assert "lengthWeights" not in entry
    assert entry["allowsEngraving"] is True
    assert entry["draft"] is False


def test_build_catalog_product_full_keeps_previous_shape():
    entry = build_catalog_product(_product_row(), _variants(), _images())

    assert entry["weights"]["14k"]["0.3"] == 1.2
    assert SUPABASE_PRODUCT in entry["images"]["white-white"]
    assert entry["descriptionZh"] == "說明"
    assert "manualPrices" in entry
    assert "lengthWeights" in entry


def test_build_catalog_response_detail_modes():
    products = [_product_row()]
    variants = {products[0]["id"]: _variants()}
    images = {products[0]["id"]: _images()}

    lite = build_catalog_response(products, variants, images, detail="lite")
    full = build_catalog_response(products, variants, images, detail="full")

    lite_prod = lite["categories"]["ring"][0]
    full_prod = full["categories"]["ring"][0]

    assert "weights" not in lite_prod
    assert lite_prod["thumbUrl"] == SUPABASE_PRODUCT
    assert full_prod["weights"]["18k"]["0.5"] == 1.4
    assert "thumbUrl" not in full_prod


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def test_api_catalog_default_is_lite(client):
    resp = client.get("/api/catalog")
    assert resp.status_code == 200
    assert "public, max-age=60" in (resp.headers.get("Cache-Control") or "")
    data = resp.json()
    assert "categories" in data
    for products in (data.get("categories") or {}).values():
        for product in products:
            assert "weights" not in product
            assert "images" not in product
            assert "golds" in product
            assert "carats" in product
            assert "thumbUrl" in product


def test_api_catalog_detail_full_has_weights(client):
    resp = client.get("/api/catalog", params={"detail": "full"})
    assert resp.status_code == 200
    # Full / preview responses should not advertise the short lite cache.
    assert "max-age=60" not in (resp.headers.get("Cache-Control") or "")
    data = resp.json()
    jewelry = [
        p
        for products in (data.get("categories") or {}).values()
        for p in products
        if p.get("golds")
    ]
    if not jewelry:
        pytest.skip("no published jewelry products in DB")
    sample = jewelry[0]
    assert "weights" in sample
    assert "images" in sample


def test_api_catalog_product_detail_200_and_404(client):
    listing = client.get("/api/catalog", params={"detail": "full"})
    assert listing.status_code == 200
    jewelry = [
        p
        for products in (listing.json().get("categories") or {}).values()
        for p in products
        if p.get("golds")
    ]
    if not jewelry:
        pytest.skip("no published jewelry products in DB")

    product_id = jewelry[0]["id"]
    detail = client.get(f"/api/catalog/product/{product_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["product"]["id"] == product_id
    assert "weights" in body["product"]
    assert "images" in body["product"]

    missing = client.get(f"/api/catalog/product/{uuid4()}")
    assert missing.status_code == 404
