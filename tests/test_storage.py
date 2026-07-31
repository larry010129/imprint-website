"""Supabase Storage helper and upload endpoint tests."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile

from app.admin_products import normalize_product_image_url
from app.catalog import build_catalog_product
from app.controllers.admin_controller import _storage_upload, product_upload
from app.storage import (
    StorageNotConfiguredError,
    StorageUploadError,
    delete_by_url,
    is_supabase_storage_url,
    local_upload_to_object_key,
    upload_bytes,
)

SUPABASE_URL = "https://abc123.supabase.co"
PUBLIC_PRODUCT = (
    f"{SUPABASE_URL}/storage/v1/object/public/shop-media/products/abc.webp"
)


@pytest.fixture(autouse=True)
def _storage_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", SUPABASE_URL)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "shop-media")


def test_is_supabase_storage_url():
    assert is_supabase_storage_url(PUBLIC_PRODUCT)
    assert not is_supabase_storage_url("/static/uploads/products/x.png")
    assert not is_supabase_storage_url("https://evil.example/x.png")


def test_local_upload_to_object_key():
    assert local_upload_to_object_key("/static/uploads/products/a.webp") == (
        "products",
        "a.webp",
    )
    assert local_upload_to_object_key("/static/uploads/cms-media/b.png") == (
        "cms-media",
        "b.png",
    )


def test_upload_bytes_returns_public_url():
    mock_post = MagicMock(status_code=200, text="")
    mock_get = MagicMock(status_code=200, text="", content=b"data")
    mock_client = MagicMock()
    mock_client.post.return_value = mock_post
    mock_client.get.return_value = mock_get
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.storage.httpx.Client", return_value=mock_client):
        url = upload_bytes("products", "abc.webp", b"data", "image/webp")

    assert url.endswith("/shop-media/products/abc.webp")
    assert mock_client.post.called
    posted_url = mock_client.post.call_args.args[0]
    assert posted_url.endswith("/object/shop-media/products/abc.webp")
    headers = mock_client.post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer test-service-role"
    assert headers["apikey"] == "test-service-role"
    assert headers["x-upsert"] == "true"
    assert mock_client.get.called
    assert "/object/authenticated/shop-media/products/abc.webp" in mock_client.get.call_args.args[0]


def test_upload_bytes_raises_on_failure():
    mock_resp = MagicMock(status_code=400, text="bad request")
    mock_client = MagicMock()
    mock_client.post.return_value = mock_resp
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.storage.httpx.Client", return_value=mock_client):
        with pytest.raises(StorageUploadError):
            upload_bytes("products", "x.png", b"x", "image/png")


def test_upload_bytes_raises_when_object_not_readable():
    mock_post = MagicMock(status_code=200, text='{"Key":"shop-media/products/x.png"}')
    mock_get = MagicMock(
        status_code=404,
        text='{"statusCode":"404","error":"not_found","message":"Object not found","code":"NoSuchKey"}',
    )
    mock_client = MagicMock()
    mock_client.post.return_value = mock_post
    mock_client.get.return_value = mock_get
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.storage.httpx.Client", return_value=mock_client):
        with pytest.raises(StorageUploadError, match="not readable"):
            upload_bytes("products", "x.png", b"x", "image/png")


def test_upload_bytes_rejects_empty_object_path():
    with pytest.raises(StorageUploadError, match="empty object path"):
        upload_bytes("products", "", b"x", "image/png")
    with pytest.raises(StorageUploadError, match="empty object path"):
        upload_bytes("", "x.png", b"x", "image/png")
    with pytest.raises(StorageUploadError, match="empty object path"):
        upload_bytes("/", "/", b"x", "image/png")
    with pytest.raises(StorageUploadError, match="empty object path"):
        upload_bytes("products", "..", b"x", "image/png")


def test_service_role_falls_back_to_secret_key(monkeypatch):
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "test-secret-key")
    from config.settings import Settings

    assert Settings().supabase_service_role_key == "test-secret-key"


def test_storage_upload_helper_success():
    with patch("app.storage.upload_image", return_value=PUBLIC_PRODUCT):
        url, err = _storage_upload("products", "abc.webp", b"x", ".webp")
    assert url == PUBLIC_PRODUCT
    assert err is None


def test_storage_upload_helper_not_configured():
    with patch(
        "app.storage.upload_image",
        side_effect=StorageNotConfiguredError("missing env"),
    ):
        url, err = _storage_upload("products", "abc.webp", b"x", ".webp")
    assert url is None
    assert "missing env" in (err or "")


def test_normalize_keeps_supabase_url():
    assert normalize_product_image_url(PUBLIC_PRODUCT, "white-white") == PUBLIC_PRODUCT


def test_normalize_still_drops_shop_product_stock():
    assert (
        normalize_product_image_url(
            "/static/images/shop-product/silver/%E9%A0%85%E5%A2%9CB_silver.png",
            "white-white",
        )
        is None
    )


def test_build_catalog_includes_supabase_url_without_disk_file():
    product = {
        "id": "prod-1",
        "category": "pendant",
        "name_zh": "四爪項墜",
        "name_en": None,
        "description_zh": None,
        "description_en": None,
        "default_color": "white",
        "sort_order": 0,
        "is_published": True,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }
    images = [{"color": "white-white", "file_path": PUBLIC_PRODUCT}]
    entry = build_catalog_product(product, [], images)
    assert PUBLIC_PRODUCT in entry["images"].get("white-white", [])


def test_delete_by_url_calls_storage_api():
    mock_resp = MagicMock(status_code=200)
    mock_client = MagicMock()
    mock_client.delete.return_value = mock_resp
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.storage.httpx.Client", return_value=mock_client):
        assert delete_by_url(PUBLIC_PRODUCT) is True
    assert mock_client.delete.called


def test_product_upload_returns_storage_url(monkeypatch):
    import asyncio

    monkeypatch.setattr(
        "app.controllers.admin_controller._require_admin",
        lambda _req: "admin-user",
    )
    monkeypatch.setattr(
        "app.controllers.admin_controller._storage_upload",
        lambda *_a, **_k: (PUBLIC_PRODUCT, None),
    )

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    upload = UploadFile(filename="photo.png", file=BytesIO(png))
    request = MagicMock()

    resp = asyncio.run(
        product_upload(request, file=upload, product_id=None, color=None)
    )
    body = resp.body.decode()
    assert PUBLIC_PRODUCT in body
