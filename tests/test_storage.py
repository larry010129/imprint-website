"""Supabase Storage helper and upload endpoint tests."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.admin_products import (
    delete_product_image_urls_if_unreferenced,
    normalize_product_image_url,
    save_product_children,
)
from app.catalog import build_catalog_product
from app.controllers.admin_controller import (
    _storage_upload,
    banner_upload,
    page_image_upload,
    product_upload,
)
from app.controllers.admin_controller import (
    testimonial_upload as admin_testimonial_upload,
)
from app.controllers.cms_admin_controller import cms_media_upload
from app.storage import (
    StorageNotConfiguredError,
    StorageUploadError,
    delete_by_url,
    english_label_for_folder,
    is_flat_page_image_object_key,
    is_flat_product_object_key,
    is_nested_page_image_object_key,
    is_nested_product_object_key,
    is_pending_product_object_key,
    is_supabase_storage_url,
    local_upload_to_object_key,
    metal_color_from_slot,
    page_image_folder_from_object_key,
    page_image_object_key,
    page_image_upload_relative_path,
    pending_product_object_key,
    prefer_category_scoped_product_url,
    product_category_from_object_key,
    product_folder_from_object_key,
    product_folder_segment,
    product_object_key,
    product_upload_relative_path,
    promote_pending_product_url,
    sanitize_product_name_slug,
    short_product_id_segment,
    storage_safe_folder_segment,
    storage_error_sentence,
    upload_bytes,
)

SUPABASE_URL = "https://abc123.supabase.co"
PUBLIC_PRODUCT = (
    f"{SUPABASE_URL}/storage/v1/object/public/shop-media/products/abc.webp"
)
PUBLIC_PAGE_IMAGE = (
    f"{SUPABASE_URL}/storage/v1/object/public/shop-media/page-images/hero.webp"
)
PUBLIC_BANNER = (
    f"{SUPABASE_URL}/storage/v1/object/public/shop-media/banners/banner.webp"
)
PUBLIC_TESTIMONIAL = (
    f"{SUPABASE_URL}/storage/v1/object/public/shop-media/testimonials/face.webp"
)
PUBLIC_CMS_MEDIA = (
    f"{SUPABASE_URL}/storage/v1/object/public/shop-media/cms-media/block.webp"
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
    assert local_upload_to_object_key("/static/uploads/page-images/c.jpg") == (
        "page-images",
        "c.jpg",
    )
    assert local_upload_to_object_key("/static/uploads/banners/d.webp") == (
        "banners",
        "d.webp",
    )
    assert local_upload_to_object_key("/static/uploads/testimonials/e.png") == (
        "testimonials",
        "e.png",
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
    webp = _pillow_image_bytes("WEBP", quality=80)
    with patch("app.storage.upload_image", return_value=PUBLIC_PRODUCT) as mocked:
        url, err = _storage_upload("products", "abc.webp", webp, ".webp")
    assert url == PUBLIC_PRODUCT
    assert err is None
    mocked.assert_called_once()
    args, kwargs = mocked.call_args
    assert args[0] == "products"
    assert args[1] == "abc.webp"
    assert args[2] == webp  # pass-through
    assert args[3] == ".webp"
    assert kwargs.get("upsert") is True


def test_storage_upload_converts_png_body_and_ext():
    png = _pillow_image_bytes("PNG")
    with patch("app.storage.upload_image", return_value=PUBLIC_PRODUCT) as mocked:
        url, err = _storage_upload("products", "nest/abc.png", png, ".png")
    assert url == PUBLIC_PRODUCT
    assert err is None
    args, kwargs = mocked.call_args
    assert args[1] == "nest/abc.webp"
    assert args[3] == ".webp"
    assert args[2][:4] == b"RIFF" and args[2][8:12] == b"WEBP"
    assert len(args[2]) <= 500 * 1024
    assert kwargs.get("upsert") is True


def test_storage_upload_convert_failure_returns_err():
    bad = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    url, err = _storage_upload("products", "broken.png", bad, ".png")
    assert url is None
    assert err


def test_storage_upload_helper_not_configured():
    webp = _pillow_image_bytes("WEBP")
    with patch(
        "app.storage.upload_image",
        side_effect=StorageNotConfiguredError("missing env"),
    ):
        url, err = _storage_upload("products", "abc.webp", webp, ".webp")
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


def _pillow_image_bytes(
    fmt: str = "PNG",
    size: tuple[int, int] = (32, 32),
    color: tuple[int, int, int] = (10, 20, 200),
    **save_kw,
) -> bytes:
    from PIL import Image

    img = Image.new("RGB", size, color)
    buf = BytesIO()
    img.save(buf, format=fmt, **save_kw)
    return buf.getvalue()


def _image_upload(
    name: str = "photo.png",
    *,
    fmt: str | None = None,
    content_type: str | None = None,
    data: bytes | None = None,
) -> UploadFile:
    suffix = Path(name).suffix.lower()
    if fmt is None:
        fmt = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP", ".gif": "GIF"}.get(
            suffix, "PNG"
        )
    if data is None:
        save_kw = {"quality": 85} if fmt in {"JPEG", "WEBP"} else {}
        data = _pillow_image_bytes(fmt, **save_kw)
    if content_type is None:
        content_type = {
            "PNG": "image/png",
            "JPEG": "image/jpeg",
            "WEBP": "image/webp",
            "GIF": "image/gif",
        }.get(fmt, "application/octet-stream")
    return UploadFile(
        filename=name,
        file=BytesIO(data),
        headers=Headers({"content-type": content_type}),
    )


def _png_upload(name: str = "photo.png") -> UploadFile:
    return _image_upload(name)


def test_metal_color_from_slot():
    assert metal_color_from_slot("white-pink") == "white"
    assert metal_color_from_slot("yellow") == "yellow"
    assert metal_color_from_slot("rose-blue-white") == "rose"
    assert metal_color_from_slot("platinum") is None
    assert metal_color_from_slot(None) is None


def test_sanitize_product_name_slug():
    assert sanitize_product_name_slug("四爪項墜") == ""
    assert sanitize_product_name_slug("Hello World") == "hello-world"
    assert sanitize_product_name_slug("a/b\\c") == "a-b-c"
    assert sanitize_product_name_slug("  foo---bar__baz  ") == "foo-bar-baz"
    assert sanitize_product_name_slug("foo_bar") == "foo_bar"
    assert sanitize_product_name_slug("") == ""
    assert sanitize_product_name_slug("_pending") == ""
    long = "a" * 100
    assert len(sanitize_product_name_slug(long)) == 80
    assert sanitize_product_name_slug("Teardrop Solitaire Necklace") == (
        "teardrop-solitaire-necklace"
    )


def test_product_folder_segment_fallback_and_collision():
    """Folder from name_en slug; empty/CJK → short product id (no zh→en)."""
    pid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert short_product_id_segment(pid) == "a1b2c3d4"
    assert product_folder_segment("", pid) == "a1b2c3d4"
    assert product_folder_segment("Hello-World", pid) == "hello-world"
    # Chinese-only / empty name_en → id fallback (name_zh ignored).
    assert sanitize_product_name_slug("四爪") == ""
    assert storage_safe_folder_segment("四爪") == ""
    assert product_folder_segment("四爪", pid) == "a1b2c3d4"
    assert product_folder_segment(None, pid) == "a1b2c3d4"
    assert product_folder_segment(None, pid, name_zh="水滴單鑽項鍊") == "a1b2c3d4"
    assert product_folder_segment(None, pid, name_zh="未知商品名") == "a1b2c3d4"
    # English name → lowercase ASCII slug; collision appends -{first8}.
    pendant = product_folder_segment("Teardrop Solitaire Necklace", pid)
    assert pendant == "teardrop-solitaire-necklace"
    assert product_folder_segment("Four Prong", pid, collide=True) == (
        "four-prong-a1b2c3d4"
    )
    # Latin chars in mixed string kept; CJK stripped.
    mixed = product_folder_segment("Gabriel四爪", pid)
    assert mixed == "gabriel"
    assert english_label_for_folder(None, "四爪單鑽項鍊") == ""
    assert english_label_for_folder("Four Claw Solitaire Necklace") == (
        "Four Claw Solitaire Necklace"
    )
    assert product_folder_segment(None, pid, name_zh="四爪單鑽項鍊") == "a1b2c3d4"


def test_prefer_category_scoped_product_url_rewrites_untyped_nested():
    base = "https://abc.supabase.co/storage/v1/object/public/shop-media"
    untyped = f"{base}/products/imprint-necklace/white/a605.png"
    typed = f"{base}/products/pendant/imprint-necklace/white/a605.png"
    assert prefer_category_scoped_product_url(untyped, "pendant") == typed
    assert prefer_category_scoped_product_url(typed, "pendant") == typed
    assert prefer_category_scoped_product_url(untyped, None) == untyped
    assert prefer_category_scoped_product_url(
        f"{base}/products/_pending/white/a.png", "pendant"
    ) == f"{base}/products/_pending/white/a.png"


def test_product_object_key_nested():
    folder = storage_safe_folder_segment("Four Prong Pendant")
    assert folder == "four-prong-pendant"
    assert product_object_key(folder, "white", "c3d4.webp") == (
        f"products/{folder}/white/c3d4.webp"
    )
    assert product_object_key(
        "four-prong-solitaire-necklace", "white", "x.png", category="pendant"
    ) == "products/pendant/four-prong-solitaire-necklace/white/x.png"
    assert product_object_key("a1b2", "yellow", "x.png") == "products/a1b2/yellow/x.png"
    assert product_object_key("a1b2", None, "x.png") == "products/a1b2/x.png"
    typed = "products/pendant/four-prong-solitaire-necklace/white/x.png"
    assert product_folder_from_object_key(typed) == "four-prong-solitaire-necklace"
    assert product_category_from_object_key(typed) == "pendant"
    assert product_folder_from_object_key(
        "products/four-prong-solitaire-necklace/white/x.png"
    ) == "four-prong-solitaire-necklace"
    with pytest.raises(StorageUploadError):
        product_object_key("../x", "white", "a.webp")
    with pytest.raises(StorageUploadError):
        product_object_key("a1b2", "green", "a.webp")
    with pytest.raises(StorageUploadError):
        product_object_key("_pending", "white", "a.webp")


def test_pending_product_object_key():
    assert pending_product_object_key("white", "abc.webp") == (
        "products/_pending/white/abc.webp"
    )
    assert pending_product_object_key(None, "abc.webp") == "products/_pending/abc.webp"
    assert pending_product_object_key("white", "abc.webp", category="pendant") == (
        "products/_pending/pendant/white/abc.webp"
    )


def test_page_image_upload_relative_path_maps_tabs():
    assert page_image_upload_relative_path("a.webp", page_key="/") == "home/a.webp"
    assert (
        page_image_upload_relative_path("b.webp", page_key="/about")
        == "brand-story/b.webp"
    )
    assert (
        page_image_upload_relative_path("c.webp", page_key="/series")
        == "series-overview/c.webp"
    )
    assert (
        page_image_upload_relative_path("d.webp", page_key="/series/pet/")
        == "pet-diamond/d.webp"
    )
    assert (
        page_image_upload_relative_path("e.webp", page_key="/series/pet")
        == "pet-diamond/e.webp"
    )
    assert (
        page_image_upload_relative_path("f.webp", page_key="/series/first-love/")
        == "moon-diamond/f.webp"
    )
    assert (
        page_image_upload_relative_path("g.webp", page_key="/series/love/")
        == "wedding-diamond/g.webp"
    )
    assert (
        page_image_upload_relative_path("h.webp", page_key="/series/family/")
        == "family-diamond/h.webp"
    )
    assert (
        page_image_upload_relative_path("i.webp", page_key="/series/heirloom/")
        == "life-diamond/i.webp"
    )
    assert (
        page_image_upload_relative_path("j.webp", page_key="/what-is-dna-diamond")
        == "dna-diamond/j.webp"
    )
    assert page_image_upload_relative_path("k.webp") == "_pending/k.webp"
    assert (
        page_image_upload_relative_path("m.webp", page_key="/stories")
        == "stories/m.webp"
    )


def test_page_image_object_key_helpers():
    assert page_image_object_key("home", "x.webp") == "page-images/home/x.webp"
    assert is_flat_page_image_object_key("page-images/abc.webp")
    assert not is_flat_page_image_object_key("page-images/home/abc.webp")
    assert is_nested_page_image_object_key("page-images/home/abc.webp")
    assert page_image_folder_from_object_key("page-images/home/abc.webp") == "home"
    assert page_image_folder_from_object_key("page-images/abc.webp") is None


def test_product_upload_relative_path():
    assert product_upload_relative_path(
        "f.webp", folder="ring-abc", color_slot="yellow-blue"
    ) == "ring-abc/yellow/f.webp"
    assert product_upload_relative_path(
        "f.webp", folder="ring-abc", color_slot="yellow-blue", category="ring"
    ) == "ring/ring-abc/yellow/f.webp"
    assert product_upload_relative_path(
        "f.webp", folder=None, color_slot="rose", category="pendant"
    ) == "_pending/pendant/rose/f.webp"
    assert product_upload_relative_path(
        "f.webp", folder=None, color_slot="rose"
    ) == "_pending/rose/f.webp"
    assert product_upload_relative_path("f.webp") == "_pending/f.webp"


def test_flat_and_nested_key_detectors():
    assert is_flat_product_object_key("products/abc.webp")
    assert not is_flat_product_object_key("products/_pending/abc.webp")
    assert not is_flat_product_object_key("products/pid/white/abc.webp")
    assert is_nested_product_object_key("products/pid/white/abc.webp")
    assert is_nested_product_object_key("products/pid/abc.webp")
    assert is_nested_product_object_key(
        "products/pendant/four-prong-solitaire-necklace/white/abc.webp"
    )
    assert not is_nested_product_object_key("products/abc.webp")
    assert is_pending_product_object_key("products/_pending/white/x.webp")
    assert is_pending_product_object_key("products/_pending/x.webp")
    assert is_pending_product_object_key("products/_pending/pendant/white/x.webp")


def test_promote_pending_product_url(monkeypatch):
    pending = (
        f"{SUPABASE_URL}/storage/v1/object/public/shop-media/"
        "products/_pending/white/abc.webp"
    )
    dest_url = (
        f"{SUPABASE_URL}/storage/v1/object/public/shop-media/"
        "products/ring-abc/white/abc.webp"
    )

    def fake_move(src: str, dst: str) -> str:
        assert src == "products/_pending/white/abc.webp"
        assert dst == "products/ring-abc/white/abc.webp"
        return dest_url

    monkeypatch.setattr("app.storage.move_object", fake_move)
    assert promote_pending_product_url(pending, "ring-abc", "white") == dest_url
    assert promote_pending_product_url(PUBLIC_PRODUCT, "ring-abc", "white") == PUBLIC_PRODUCT


def test_promote_pending_product_url_with_category(monkeypatch):
    pending = (
        f"{SUPABASE_URL}/storage/v1/object/public/shop-media/"
        "products/_pending/pendant/white/abc.webp"
    )
    dest_url = (
        f"{SUPABASE_URL}/storage/v1/object/public/shop-media/"
        "products/pendant/four-prong/white/abc.webp"
    )

    def fake_move(src: str, dst: str) -> str:
        assert src == "products/_pending/pendant/white/abc.webp"
        assert dst == "products/pendant/four-prong/white/abc.webp"
        return dest_url

    monkeypatch.setattr("app.storage.move_object", fake_move)
    assert (
        promote_pending_product_url(
            pending, "four-prong", "white", category="pendant"
        )
        == dest_url
    )


def test_save_product_children_promotes_pending_urls(monkeypatch):
    pending = (
        f"{SUPABASE_URL}/storage/v1/object/public/shop-media/"
        "products/_pending/yellow/abc.webp"
    )
    folder = "test-product"
    promoted = (
        f"{SUPABASE_URL}/storage/v1/object/public/shop-media/"
        f"products/{folder}/yellow/abc.webp"
    )
    monkeypatch.setattr(
        "app.admin_products.resolve_product_folder",
        lambda *_a, **_k: folder,
    )
    monkeypatch.setattr(
        "app.admin_products.align_product_images_to_folder",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "app.admin_products.promote_pending_product_url",
        lambda url, folder, metal, **kwargs: promoted if "/_pending/" in url else url,
    )
    monkeypatch.setattr(
        "app.admin_products.delete_product_image_urls_if_unreferenced",
        lambda *_a, **_k: 0,
    )
    cleaned = {
        "category": "ring",
        "nameZh": "測試商品",
        "nameEn": "Test Product",
        "variants": [],
        "lengthWeights": None,
        "chainType": None,
        "images": [{"color": "yellow-pink", "url": pending}],
    }
    cur = MagicMock()
    cur.fetchall.return_value = []
    save_product_children(cur, "prod-9", cleaned)
    assert cleaned["images"][0]["url"] == promoted
    insert_calls = [
        c
        for c in cur.execute.call_args_list
        if c.args and "insert into product_images" in str(c.args[0]).lower()
    ]
    assert insert_calls
    assert insert_calls[0].args[1][2] == promoted


def _product_url(key: str) -> str:
    return f"{SUPABASE_URL}/storage/v1/object/public/shop-media/{key}"


def test_delete_product_image_urls_unreferenced_calls_delete(monkeypatch):
    url = _product_url("products/prod-1/white/a.webp")
    deleted: list[str] = []
    monkeypatch.setattr(
        "app.admin_products.delete_by_url",
        lambda u: deleted.append(u) or True,
    )
    cur = MagicMock()
    cur.fetchone.return_value = None
    assert delete_product_image_urls_if_unreferenced(cur, [url, url]) == 1
    assert deleted == [url]


def test_delete_product_image_urls_keeps_referenced(monkeypatch):
    url = _product_url("products/prod-1/white/a.webp")
    monkeypatch.setattr(
        "app.admin_products.delete_by_url",
        lambda _u: (_ for _ in ()).throw(AssertionError("must not delete")),
    )
    cur = MagicMock()
    cur.fetchone.return_value = {"ok": 1}
    assert delete_product_image_urls_if_unreferenced(cur, [url]) == 0


def test_delete_product_image_urls_shared_then_last_ref(monkeypatch):
    """Duplicate shares URL: keep while any row refs; delete when last gone."""
    url = _product_url("products/prod-1/white/shared.webp")
    deleted: list[str] = []
    monkeypatch.setattr(
        "app.admin_products.delete_by_url",
        lambda u: deleted.append(u) or True,
    )
    cur = MagicMock()
    # First product delete: other product still references → keep.
    cur.fetchone.return_value = {"ok": 1}
    assert delete_product_image_urls_if_unreferenced(cur, [url]) == 0
    assert deleted == []
    # Last reference gone → Storage delete.
    cur.fetchone.return_value = None
    assert delete_product_image_urls_if_unreferenced(cur, [url]) == 1
    assert deleted == [url]


def test_delete_product_image_urls_skips_non_products(monkeypatch):
    page = PUBLIC_PAGE_IMAGE
    local = "/static/uploads/products/x.png"
    monkeypatch.setattr(
        "app.admin_products.delete_by_url",
        lambda _u: (_ for _ in ()).throw(AssertionError("must not delete")),
    )
    cur = MagicMock()
    assert delete_product_image_urls_if_unreferenced(cur, [page, local, ""]) == 0
    cur.execute.assert_not_called()


def test_save_product_children_deletes_dropped_unreferenced(monkeypatch):
    old = _product_url("products/prod-1/white/old.webp")
    kept = _product_url("products/prod-1/white/kept.webp")
    dropped: list[str] = []

    monkeypatch.setattr(
        "app.admin_products.resolve_product_folder",
        lambda *_a, **_k: "prod-1",
    )
    monkeypatch.setattr(
        "app.admin_products.align_product_images_to_folder",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "app.admin_products.promote_pending_product_url",
        lambda url, folder, metal, **kwargs: url,
    )

    def fake_unref(cur, urls):
        dropped.extend(sorted(urls))
        return len(urls)

    monkeypatch.setattr(
        "app.admin_products.delete_product_image_urls_if_unreferenced",
        fake_unref,
    )
    cleaned = {
        "category": "ring",
        "nameZh": "prod-1",
        "variants": [],
        "lengthWeights": None,
        "chainType": None,
        "images": [{"color": "white", "url": kept}],
    }
    cur = MagicMock()
    cur.fetchall.return_value = [{"file_path": old}, {"file_path": kept}]
    save_product_children(cur, "prod-1", cleaned)
    assert dropped == [old]


def test_align_product_images_to_folder_moves_unshared(monkeypatch):
    from app.admin_products import align_product_images_to_folder

    old = _product_url("products/old-name/white/a.webp")
    new = _product_url("products/new-name/white/a.webp")
    moved: list[tuple] = []

    def fake_reloc(url, old_f, new_f, *, shared=False, category=None):
        moved.append((url, old_f, new_f, shared, category))
        return new

    monkeypatch.setattr("app.admin_products.relocate_product_object_url", fake_reloc)
    cur = MagicMock()
    cur.fetchone.return_value = None  # not shared
    images = [{"color": "white", "url": old}]
    align_product_images_to_folder(cur, "pid", "new-name", images)
    assert images[0]["url"] == new
    assert moved == [(old, "old-name", "new-name", False, None)]


def test_resolve_product_folder_collision():
    from app.admin_products import resolve_product_folder

    pid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    other = "ffffffff-1111-2222-3333-444444444444"
    cur = MagicMock()
    cur.fetchall.return_value = [
        {"id": other, "name_en": "Same Name", "name_zh": None}
    ]
    expected = product_folder_segment("Same Name", pid, collide=True)
    assert resolve_product_folder(cur, pid, "Same Name") == expected
    assert expected == "same-name-aaaaaaaa"


def test_resolve_product_folder_empty_name_en_uses_short_id():
    from app.admin_products import resolve_product_folder

    pid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    cur = MagicMock()
    cur.fetchall.return_value = []
    assert resolve_product_folder(cur, pid, None) == "aaaaaaaa"
    assert resolve_product_folder(cur, pid, "") == "aaaaaaaa"
    # name_zh ignored — no Google/auto translate.
    assert resolve_product_folder(cur, pid, None, "四爪項墜") == "aaaaaaaa"
    assert resolve_product_folder(cur, pid, "四爪項墜") == "aaaaaaaa"


def _load_purge_module():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / (
        "scripts/purge_unused_supabase_product_images.py"
    )
    spec = importlib.util.spec_from_file_location("purge_unused_product_images", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_orphan_product_keys_skips_referenced():
    purge_mod = _load_purge_module()
    referenced = {"products/pid/white/a.webp"}
    storage = [
        "products/pid/white/a.webp",
        "products/ok.png",
        "products/pid/yellow/b.webp",
        "page-images/hero.webp",
    ]
    assert purge_mod.orphan_product_keys(storage, referenced) == [
        "products/ok.png",
        "products/pid/yellow/b.webp",
    ]


def test_purge_unused_deletes_only_orphans(monkeypatch):
    purge_mod = _load_purge_module()
    storage = [
        "products/pid/white/keep.webp",
        "products/orphan.png",
    ]
    deleted: list[str] = []

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return self

        def execute(self, *_a, **_k):
            return None

        def fetchall(self):
            return [
                {
                    "file_path": (
                        f"{SUPABASE_URL}/storage/v1/object/public/shop-media/"
                        "products/pid/white/keep.webp"
                    ),
                    "previous_file_path": None,
                }
            ]

    monkeypatch.setattr(purge_mod, "get_connection", lambda: _Conn())
    monkeypatch.setattr(purge_mod, "list_product_object_keys", lambda: storage)
    monkeypatch.setattr(
        purge_mod,
        "delete_by_url",
        lambda u: deleted.append(u) or True,
    )
    monkeypatch.setattr(
        purge_mod,
        "public_url_for_object",
        lambda key: f"{SUPABASE_URL}/storage/v1/object/public/shop-media/{key}",
    )

    deleted_n, kept, total = purge_mod.purge_unused_product_images(dry_run=False)
    assert deleted_n == 1
    assert kept == 1
    assert total == 2
    assert deleted == [
        f"{SUPABASE_URL}/storage/v1/object/public/shop-media/products/orphan.png"
    ]
    assert "keep.webp" not in "".join(deleted)


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

    resp = asyncio.run(
        product_upload(MagicMock(), file=_png_upload(), product_id=None, color=None)
    )
    assert PUBLIC_PRODUCT in resp.body.decode()


def test_product_upload_uses_nested_metal_path(monkeypatch):
    import asyncio

    monkeypatch.setattr(
        "app.controllers.admin_controller._require_admin",
        lambda _req: "admin-user",
    )
    calls: list[tuple] = []

    def fake_upload_image(kind: str, name: str, data: bytes, ext: str, upsert: bool = False):
        calls.append((kind, name, data, ext, upsert))
        return (
            f"{SUPABASE_URL}/storage/v1/object/public/shop-media/"
            f"products/{name}"
        )

    monkeypatch.setattr("app.storage.upload_image", fake_upload_image)
    monkeypatch.setattr(
        "app.controllers.admin_controller.append_product_image",
        lambda *_a, **_k: {"id": "img1", "product_id": "prod-1", "color": "white-pink"},
    )
    folder = "four-prong-pendant"
    monkeypatch.setattr(
        "app.controllers.admin_controller.resolve_product_folder",
        lambda *_a, **_k: folder,
    )

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return self

        def execute(self, *_a, **_k):
            return None

        def fetchone(self):
            return {"name_zh": "四爪項墜"}

    monkeypatch.setattr(
        "app.controllers.admin_controller.get_connection",
        lambda: _Conn(),
    )
    monkeypatch.setattr(
        "app.controllers.admin_controller.get_transaction",
        lambda: _Conn(),
    )

    resp = asyncio.run(
        product_upload(
            MagicMock(),
            file=_png_upload(),
            product_id="prod-1",
            color="white-pink",
        )
    )
    assert resp.status_code == 200
    assert calls and calls[0][0] == "products"
    assert calls[0][1].startswith(f"{folder}/white/")
    assert calls[0][1].endswith("photo.webp")
    assert calls[0][3] == ".webp"
    assert calls[0][2][:4] == b"RIFF" and calls[0][2][8:12] == b"WEBP"
    assert calls[0][4] is True


def test_product_upload_pending_without_product_id(monkeypatch):
    import asyncio

    monkeypatch.setattr(
        "app.controllers.admin_controller._require_admin",
        lambda _req: "admin-user",
    )
    calls: list[str] = []

    def fake_upload(kind: str, name: str, data: bytes, ext: str):
        calls.append(name)
        return PUBLIC_PRODUCT, None

    monkeypatch.setattr(
        "app.controllers.admin_controller._storage_upload",
        fake_upload,
    )

    resp = asyncio.run(
        product_upload(
            MagicMock(),
            file=_png_upload(),
            product_id=None,
            color="yellow",
        )
    )
    assert resp.status_code == 200
    assert calls[0].startswith("_pending/yellow/")


def test_page_image_upload_returns_storage_url(monkeypatch):
    import asyncio

    monkeypatch.setattr(
        "app.controllers.admin_controller._require_admin",
        lambda _req: "admin-user",
    )
    kinds: list[str] = []
    names: list[str] = []

    def fake_upload(kind: str, name: str, data: bytes, ext: str):
        kinds.append(kind)
        names.append(name)
        return PUBLIC_PAGE_IMAGE, None

    monkeypatch.setattr(
        "app.controllers.admin_controller._storage_upload",
        fake_upload,
    )
    monkeypatch.setattr(
        "app.controllers.web_controller.clear_page_image_cache",
        lambda: None,
    )

    resp = asyncio.run(
        page_image_upload(
            MagicMock(), file=_png_upload("hero-shot.png"), page_key="/about"
        )
    )
    assert resp.status_code == 200
    assert PUBLIC_PAGE_IMAGE in resp.body.decode()
    assert kinds == ["page-images"]
    # Storage key is ASCII-safe and unique; ensure_webp runs inside real _storage_upload.
    assert len(names) == 1
    assert re.fullmatch(r"brand-story/image-[0-9a-f]{32}\.png", names[0])


def test_page_image_upload_fails_when_storage_missing(monkeypatch):
    import asyncio

    monkeypatch.setattr(
        "app.controllers.admin_controller._require_admin",
        lambda _req: "admin-user",
    )
    monkeypatch.setattr(
        "app.controllers.admin_controller._storage_upload",
        lambda *_a, **_k: (None, "Supabase Storage 未設定：請設定 SUPABASE_URL"),
    )

    resp = asyncio.run(page_image_upload(MagicMock(), file=_png_upload()))
    assert resp.status_code == 503
    assert "圖片上傳失敗" in resp.body.decode()
    assert "/static/uploads/" not in resp.body.decode()


def test_banner_and_testimonial_upload_use_storage(monkeypatch):
    import asyncio

    monkeypatch.setattr(
        "app.controllers.admin_controller._require_admin",
        lambda _req: "admin-user",
    )
    mapping = {
        "banners": PUBLIC_BANNER,
        "testimonials": PUBLIC_TESTIMONIAL,
    }

    def fake_upload(kind: str, name: str, data: bytes, ext: str):
        return mapping[kind], None

    monkeypatch.setattr(
        "app.controllers.admin_controller._storage_upload",
        fake_upload,
    )

    banner_resp = asyncio.run(banner_upload(MagicMock(), file=_png_upload()))
    testimonial_resp = asyncio.run(
        admin_testimonial_upload(MagicMock(), file=_png_upload())
    )
    assert PUBLIC_BANNER in banner_resp.body.decode()
    assert PUBLIC_TESTIMONIAL in testimonial_resp.body.decode()


def test_cms_media_upload_returns_storage_url(monkeypatch):
    import asyncio

    monkeypatch.setattr(
        "app.controllers.cms_admin_controller._require_admin",
        lambda _req: "admin-user",
    )
    kinds: list[str] = []

    def fake_upload(kind: str, name: str, data: bytes, ext: str):
        kinds.append(kind)
        return PUBLIC_CMS_MEDIA, None

    monkeypatch.setattr(
        "app.controllers.cms_admin_controller._storage_upload",
        fake_upload,
    )
    monkeypatch.setattr(
        "app.controllers.cms_admin_controller._actor_email",
        lambda _uid: "admin@example.com",
    )
    monkeypatch.setattr(
        "app.controllers.cms_admin_controller.log_admin_action",
        lambda *_a, **_k: None,
    )

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return self

    monkeypatch.setattr(
        "app.controllers.cms_admin_controller.get_connection",
        lambda: _Conn(),
    )
    monkeypatch.setattr(
        "app.controllers.cms_admin_controller._ensure_all",
        lambda _cur: None,
    )
    monkeypatch.setattr(
        "app.cms_media.create_media",
        lambda _cur, url, filename: {"id": "m1", "url": url, "filename": filename},
    )

    resp = asyncio.run(cms_media_upload(MagicMock(), file=_png_upload()))
    assert resp.status_code == 200
    body = resp.body.decode()
    assert PUBLIC_CMS_MEDIA in body
    assert kinds == ["cms-media"]


def test_product_upload_rejects_gif(monkeypatch):
    import asyncio

    monkeypatch.setattr(
        "app.controllers.admin_controller._require_admin",
        lambda _req: "admin-user",
    )
    with patch("app.storage.upload_image") as mocked:
        resp = asyncio.run(
            product_upload(
                MagicMock(),
                file=_image_upload("anim.gif", fmt="GIF", content_type="image/gif"),
                product_id=None,
                color=None,
            )
        )
    assert resp.status_code == 400
    assert "僅支援 JPG / PNG / WEBP" in resp.body.decode()
    mocked.assert_not_called()


def test_product_upload_rejects_wrong_mime(monkeypatch):
    import asyncio

    monkeypatch.setattr(
        "app.controllers.admin_controller._require_admin",
        lambda _req: "admin-user",
    )
    with patch("app.storage.upload_image") as mocked:
        resp = asyncio.run(
            product_upload(
                MagicMock(),
                file=_image_upload(
                    "photo.png",
                    fmt="PNG",
                    content_type="image/gif",
                ),
                product_id=None,
                color=None,
            )
        )
    assert resp.status_code == 400
    assert "僅支援 JPG / PNG / WEBP" in resp.body.decode()
    mocked.assert_not_called()


def test_product_upload_convert_failure_returns_400(monkeypatch):
    import asyncio

    monkeypatch.setattr(
        "app.controllers.admin_controller._require_admin",
        lambda _req: "admin-user",
    )
    bad = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    with patch("app.storage.upload_image") as mocked:
        resp = asyncio.run(
            product_upload(
                MagicMock(),
                file=_image_upload(
                    "broken.png",
                    content_type="image/png",
                    data=bad,
                ),
                product_id=None,
                color=None,
            )
        )
    assert resp.status_code == 400
    assert b"error" in resp.body
    mocked.assert_not_called()


def test_storage_errors_are_one_sentence():
    invalid = storage_error_sentence(
        'Storage upload failed (400): {"statusCode":"400","error":"InvalidKey"}'
    )
    generic = storage_error_sentence("Storage upload failed (503): upstream unavailable\ntrace")
    assert invalid == "圖片上傳失敗：檔名或儲存路徑包含不支援的字元，請重新上傳。"
    assert generic == "圖片上傳失敗：儲存服務拒絕了這次上傳，請稍後再試。"
    assert "{" not in invalid and "\n" not in generic
