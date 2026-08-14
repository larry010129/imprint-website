"""Admin content bootstrap, slim list DTOs, schema-off-list, short caches."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import app.content as content
from app.content import (
    serialize_banner_list,
    serialize_journal_post_list,
    serialize_page_image_list,
)
from app.content_cache import (
    ADMIN_CONTENT_CACHE_TTL_SECONDS,
    PUBLIC_CONTENT_API_CACHE_TTL_SECONDS,
    clear_admin_content_cache,
    clear_content_api_caches,
    clear_public_content_api_cache,
    content_etag,
    get_admin_content_cache,
    get_public_content_api_cache,
    set_admin_content_cache,
    set_public_content_api_cache,
)
from app.controllers import admin_controller


def test_journal_list_dto_has_preview_not_body():
    row = serialize_journal_post_list(
        {
            "id": "1",
            "title": "Hello",
            "body": "x" * 200,
            "posted_at": "2026-03-15",
            "is_published": True,
            "is_archived": False,
            "sort_order": 0,
            "updated_at": "2026-08-12T01:02:03+00:00",
        }
    )
    assert "body" not in row
    assert row["body_preview"] == "x" * 120
    assert row["title"] == "Hello"
    assert row["updated_at"] == "2026-08-12T01:02:03+00:00"


def test_page_image_list_dto_omits_previous_and_defaults():
    row = serialize_page_image_list(
        {
            "page_key": "/",
            "slot_key": "hero",
            "label": "首頁",
            "slot_label": "主視覺",
            "group_key": "brand",
            "image_url": "/static/a.jpg",
            "image_webp": None,
            "image_alt": "",
            "default_image_url": "/static/default.jpg",
            "default_image_webp": "/static/default.webp",
            "previous_image_url": "/static/old.jpg",
            "previous_image_webp": None,
            "target_w": 100,
            "target_h": 100,
            "sort_order": 0,
            "is_published": True,
            "updated_at": "2026-08-12T01:02:03+00:00",
        }
    )
    assert "previous_image_url" not in row
    assert "previousImageUrl" not in row
    assert "default_image_url" not in row
    assert row.get("display_url")
    assert row["updated_at"] == "2026-08-12T01:02:03+00:00"
    assert row.get("admin_preview_url")


def test_admin_preview_url_ignores_publish_state():
    from app.content import serialize_page_image

    row = serialize_page_image(
        {
            "page_key": "/",
            "slot_key": "hero",
            "label": "首頁",
            "slot_label": "主視覺",
            "group_key": "brand",
            "image_url": "/static/draft.jpg",
            "image_webp": None,
            "image_alt": "",
            "default_image_url": "/static/default.jpg",
            "default_image_webp": None,
            "target_w": 100,
            "target_h": 100,
            "sort_order": 0,
            "is_published": False,
            "updated_at": "2026-08-12T01:02:03+00:00",
        }
    )
    assert "/static/default.jpg" in (row.get("display_url") or "")
    assert "/static/draft.jpg" in (row.get("admin_preview_url") or "")


def test_banner_list_dto_omits_color_blobs():
    row = serialize_banner_list(
        {
            "id": "1",
            "title": "T",
            "eyebrow": "E",
            "lead": "L",
            "image_url": "/static/b.jpg",
            "tone": "white",
            "eyebrow_color": "cream",
            "title_color": "ink",
            "lead_color": "mint",
            "sort_order": 0,
            "is_published": True,
            "updated_at": "2026-08-12T01:02:03+00:00",
        }
    )
    assert row["tone"] == "white"
    assert "eyebrow_color" not in row
    assert "title_color" not in row
    assert "lead_color" not in row
    assert row["updated_at"] == "2026-08-12T01:02:03+00:00"


def test_page_images_schema_once_per_process():
    content._PAGE_IMAGES_SCHEMA_READY = False
    cur = MagicMock()
    with patch.object(content, "_ensure_page_images_schema_impl") as impl:
        content.ensure_page_images_schema(cur)
        content.ensure_page_images_schema(cur)
        assert impl.call_count == 1
        assert content._PAGE_IMAGES_SCHEMA_READY is True
    content._PAGE_IMAGES_SCHEMA_READY = False


def test_testimonial_country_ensure_once_per_process():
    content._TESTIMONIAL_COUNTRY_READY = False
    cur = MagicMock()
    content.ensure_testimonial_country_column(cur)
    content.ensure_testimonial_country_column(cur)
    assert cur.execute.call_count == 1
    assert content._TESTIMONIAL_COUNTRY_READY is True
    content._TESTIMONIAL_COUNTRY_READY = False


def test_admin_list_endpoints_do_not_call_schema_ensure():
    src = open("app/controllers/admin_controller.py", encoding="utf-8").read()
    # Hot list GETs must stay pure SELECT/COUNT (schema at lifespan / once-per-process).
    list_fn = src.split("async def admin_testimonials_list")[1].split(
        "async def admin_testimonials_create"
    )[0]
    assert "ensure_testimonial_country_column" not in list_fn
    page_fn = src.split("async def admin_page_images_list")[1].split(
        "async def admin_page_image_create_options"
    )[0]
    assert "ensure_page_images_schema" not in page_fn


def test_content_bootstrap_route_registered():
    paths = {getattr(r, "path", None) for r in admin_controller.router.routes}
    assert "/admin/content-bootstrap" in paths


def test_build_content_bootstrap_shape():
    cur = MagicMock()
    with (
        patch(
            "app.controllers.admin_controller.get_connection"
        ) as get_conn,
        patch(
            "app.controllers.admin_controller._build_content_tab_active",
            return_value={
                "items": [{"id": "1"}],
                "total": 1,
                "page": 1,
                "page_size": 10,
            },
        ),
        patch(
            "app.content.fetch_page_image_keys",
            return_value=[{"page_key": "/", "label": "首頁"}],
        ),
    ):
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cur
        get_conn.return_value.__enter__.return_value = conn
        payload = admin_controller._build_content_bootstrap(
            tab="banners", page=1, page_size=10, limit=10, offset=0
        )
    assert payload["tab"] == "banners"
    assert payload["active"]["items"] == [{"id": "1"}]
    assert payload["pageImageKeys"] == [{"page_key": "/", "label": "首頁"}]
    assert isinstance(payload["site_pages"], list)
    assert payload["site_pages"]


def test_admin_and_public_cache_ttl_and_clear():
    clear_content_api_caches()
    assert ADMIN_CONTENT_CACHE_TTL_SECONDS == 12.0
    assert PUBLIC_CONTENT_API_CACHE_TTL_SECONDS == 30.0
    set_admin_content_cache(("banners", 1, 10), {"ok": True})
    set_public_content_api_cache("banners", {"banners": []})
    assert get_admin_content_cache(("banners", 1, 10)) == {"ok": True}
    assert get_public_content_api_cache("banners") == {"banners": []}
    clear_admin_content_cache()
    clear_public_content_api_cache()
    assert get_admin_content_cache(("banners", 1, 10)) is None
    assert get_public_content_api_cache("banners") is None


def test_content_etag_stable():
    a = content_etag({"tab": "banners", "active": {"total": 1}})
    b = content_etag({"tab": "banners", "active": {"total": 1}})
    assert a == b
    assert a.startswith('"') and a.endswith('"')


def test_testimonial_replacement_handoff_keeps_latest_uploaded_url():
    admin_js = open("public/js/admin-content.js", encoding="utf-8").read()
    admin_shell = open("admin.html", encoding="utf-8").read()
    admin_shell_legacy = open("admin1.html", encoding="utf-8").read()

    # The upload widget may finish immediately before requestSubmit; the form
    # must still carry the newest successful remote URL, not the old preview.
    assert "function testimonialImageUrl(value)" in admin_js
    assert "if (form) form.dataset.imageUrl = nextUrl" in admin_js
    assert "form.dataset.imageUrl || ''" in admin_js
    assert "/js/admin-content.js?v=50" in admin_shell
    assert "/js/admin-content.js?v=50" in admin_shell_legacy


def test_page_image_save_keys_are_route_and_kebab_not_labels():
    admin_js = open("public/js/admin-content.js", encoding="utf-8").read()
    modal = open("frontend/src/components/admin/PageImageEditModal.tsx", encoding="utf-8").read()
    keys_lib = open("frontend/src/lib/page-image-save-keys.ts", encoding="utf-8").read()

    assert "function pageImageSaveKeys(row)" in admin_js
    assert "pageKey: keys.page_key" in admin_js
    assert "slotKey: keys.slot_key" in admin_js
    assert "function pageImageTabLabel(pageKey, label)" in admin_js
    assert "return '真我鑽石'" in admin_js
    assert "'真我鑽石': '銘印鑽石'" not in admin_js
    assert '"真我鑽石": "銘印鑽石"' not in admin_js
    assert "銘印鑽石｜首頁圖片與內容管理" in admin_js

    assert "pageImageSaveKeys(row)" in modal
    assert "pageKey: keys.pageKey" in modal
    assert "slotKey: keys.slotKey" in modal
    assert "pageKey.startsWith(\"/\")" in keys_lib
    assert "SLOT_RE" in keys_lib


def test_testimonial_replacement_payload_preserves_each_saved_url():
    from app.content import parse_testimonial_payload

    base = {
        "namePart": "王",
        "honorific": "小姐",
        "category": "寵物鑽石",
        "city": "台北市",
        "text": "很感動的見證內容",
        "isPublished": True,
    }
    for url in (
        "https://storage.example/testimonials/a.webp",
        "https://storage.example/testimonials/b.webp",
        "https://storage.example/testimonials/c.webp",
    ):
        cleaned, error = parse_testimonial_payload({**base, "imageUrl": url})
        assert error is None
        assert cleaned["image_url"] == url
