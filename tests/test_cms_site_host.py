"""Site-route CMS host pages + section → page_images sync helpers."""

from __future__ import annotations

import re
import uuid

from app.cms_pages import (
    DEFAULT_PROPS,
    SECTION_IMAGE_TYPES,
    page_key_for_cms_page,
    parse_section_payload,
    section_page_image_slot_key,
    site_route_to_slug,
    upsert_section_page_image,
)


def test_site_route_to_slug_stable():
    assert site_route_to_slug("/") == "site-home"
    about = site_route_to_slug("/about.html")
    assert about.startswith("site-")
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", about)


def test_image_text_defaults_to_stack_and_cta_has_image():
    assert DEFAULT_PROPS["image_text"]["layout"] == "stack"
    fields, err = parse_section_payload({"type": "image_text", "props": {}})
    assert err is None
    assert fields["props"]["layout"] == "stack"
    assert "cta_band" in SECTION_IMAGE_TYPES
    assert "image_url" in DEFAULT_PROPS["cta_band"]
    fields, err = parse_section_payload(
        {"type": "cta_band", "props": {**DEFAULT_PROPS["cta_band"], "image_url": "/x.jpg"}}
    )
    assert err is None
    assert fields["props"]["image_url"] == "/x.jpg"


def test_section_page_image_slot_key_fits_page_images_regex():
    section_id = str(uuid.uuid4())
    slot = section_page_image_slot_key(section_id)
    assert slot.startswith("cms-section-")
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", slot)


def test_page_key_for_cms_page_prefers_site_route():
    assert page_key_for_cms_page({"site_route": "/", "slug": "site-home"}) == "/"
    assert page_key_for_cms_page({"site_route": None, "slug": "spring"}) == "/p/spring"
    assert page_key_for_cms_page({"slug": "x"}) == "/p/x"


def test_upsert_section_page_image_skips_text_only_types(monkeypatch):
    class FakeCur:
        def execute(self, *args, **kwargs):
            raise AssertionError("should not touch DB for text-only sections")

        def fetchone(self):
            return None

    monkeypatch.setattr("app.content.ensure_page_images_schema", lambda _cur: None)
    result = upsert_section_page_image(
        FakeCur(),
        page_key="/about.html",
        section_id=str(uuid.uuid4()),
        section_type="rich_text",
        image_url="/x.jpg",
    )
    assert result is None


def test_section_partial_renders_for_preview_patch():
    """Admin soft-preview needs section HTML fragments with data-cms-section-id."""
    from app.controllers.web_controller import templates

    section_id = str(uuid.uuid4())
    html = templates.env.get_template("partials/cms/section_hero.html").render(
        {
            "section": {"id": section_id, "type": "hero"},
            "props": {
                "title": "預覽標題",
                "lead": "引言",
                "eyebrow": "",
                "image_url": "",
                "image_alt": "",
                "cta_label": "",
                "cta_href": "",
                "cta_secondary_label": "",
                "cta_secondary_href": "",
            },
            "cms_page": {"title": "頁面", "slug": "x"},
            "cms_inline": True,
            "site_cms_edit": True,
        }
    )
    assert f'data-cms-section-id="{section_id}"' in html
    assert "預覽標題" in html


def test_ensure_site_route_page_rejects_non_editable_route():
    from app.cms_pages import ensure_site_route_page

    class FakeCur:
        def execute(self, *args, **kwargs):
            return None

        def fetchone(self):
            return None

    try:
        ensure_site_route_page(FakeCur(), "/shop/calculator/", "試算")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "不可編輯" in str(exc) or "保留" in str(exc) or "無效" in str(exc)
