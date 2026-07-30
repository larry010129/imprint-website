from app.cms_boundary import (
    assert_content_page_key,
    is_reserved_cms_slug,
    is_reserved_page_key,
    validate_cms_slug,
)
from app.cms_pages import (
    DEFAULT_PROPS,
    SECTION_TYPES,
    parse_section_payload,
    serialize_section,
)


def test_reserved_cms_slugs_blocked():
    assert is_reserved_cms_slug("shop")
    assert is_reserved_cms_slug("calculator")
    assert is_reserved_cms_slug("cart")
    assert is_reserved_cms_slug("api")
    assert is_reserved_cms_slug("price")
    assert validate_cms_slug("shop")[0] is None
    slug, err = validate_cms_slug("brand-story")
    assert slug == "brand-story"
    assert err is None


def test_reserved_page_keys_block_shop_jewelry_price():
    assert is_reserved_page_key("/shop/calculator/")
    assert is_reserved_page_key("/jewelry/rings/")
    assert is_reserved_page_key("/price.html")
    assert assert_content_page_key("/about.html")[1] is None
    assert assert_content_page_key("/shop/x/")[0] is None
    assert assert_content_page_key("/SHOP/calculator/")[0] is None
    assert assert_content_page_key("\\shop\\calculator\\")[0] is None
    assert assert_content_page_key("/%73hop/calculator/")[0] is None
    assert assert_content_page_key("/marketing/../shop/calculator/")[0] is None
    assert assert_content_page_key("//shop/calculator/")[0] is None


def test_section_types_and_layout_variants():
    assert "hero" in SECTION_TYPES
    assert "freeform" in SECTION_TYPES
    assert "calculator_embed" not in SECTION_TYPES
    assert DEFAULT_PROPS["image_text"]["layout"] == "stack"
    assert DEFAULT_PROPS["rich_text"]["title"]
    assert DEFAULT_PROPS["rich_text"]["body"]
    fields, err = parse_section_payload({"type": "image_text", "props": {}})
    assert err is None
    assert fields["props"]["layout"] == "stack"
    assert fields["props"]["title"]
    fields, err = parse_section_payload({"type": "rich_text", "props": {}})
    assert err is None
    assert fields["props"]["title"]
    assert fields["props"]["body"]
    fields, err = parse_section_payload(
        {"type": "image_text", "props": {**DEFAULT_PROPS["image_text"], "layout": "right"}}
    )
    assert err is None
    assert fields["props"]["layout"] == "right"
    fields, err = parse_section_payload({"type": "rich_text", "props": {"title": "a", "body": "b", "columns": 3}})
    assert err is None
    assert fields["props"]["columns"] == 3
    fields, err = parse_section_payload({"type": "calculator_embed"})
    assert fields is None


def test_freeform_block_layout_props():
    fields, err = parse_section_payload({"type": "freeform", "props": {}})
    assert err is None
    assert fields["props"]["height"] == 480
    assert isinstance(fields["props"]["blocks"], list)
    assert fields["props"]["blocks"][0]["kind"] == "heading"
    assert fields["props"]["blocks_mobile"] == []
    fields, err = parse_section_payload(
        {
            "type": "freeform",
            "props": {
                "height": 600,
                "blocks": [
                    {
                        "id": "b1",
                        "kind": "text",
                        "x": 12.5,
                        "y": 20,
                        "w": 40,
                        "h": 15,
                        "z": 1,
                        "text": "Hello",
                    }
                ],
            },
        }
    )
    assert err is None
    assert fields["props"]["height"] == 600
    assert fields["props"]["blocks"][0]["x"] == 12.5
    assert fields["props"]["blocks"][0]["text"] == "Hello"
    fields, err = parse_section_payload(
        {
            "type": "freeform",
            "props": {
                "blocks": [{"id": "b1", "kind": "button", "text": "Go", "href": "javascript:alert(1)"}]
            },
        }
    )
    assert fields is None
    assert "連結格式" in err


def test_freeform_blocks_mobile_and_hardening():
    fields, err = parse_section_payload(
        {
            "type": "freeform",
            "props": {
                "blocks": [
                    {
                        "id": "desk",
                        "kind": "heading",
                        "x": 10,
                        "y": 10,
                        "w": 40,
                        "h": 12,
                        "z": 1,
                        "text": "桌面",
                    }
                ],
                "blocks_mobile": [
                    {
                        "id": "mob",
                        "kind": "heading",
                        "x": 5,
                        "y": 8,
                        "w": 90,
                        "h": 14,
                        "z": 2,
                        "text": "手機",
                    }
                ],
            },
        }
    )
    assert err is None
    assert len(fields["props"]["blocks"]) == 1
    assert fields["props"]["blocks_mobile"][0]["text"] == "手機"
    assert fields["props"]["blocks_mobile"][0]["w"] == 90.0

    # duplicate ids get rewritten; invalid kind rejected; non-list rejected
    fields, err = parse_section_payload(
        {
            "type": "freeform",
            "props": {
                "blocks": [
                    {"id": "same", "kind": "text", "text": "a"},
                    {"id": "same", "kind": "text", "text": "b"},
                ]
            },
        }
    )
    assert err is None
    assert fields["props"]["blocks"][0]["id"] != fields["props"]["blocks"][1]["id"]

    fields, err = parse_section_payload(
        {"type": "freeform", "props": {"blocks": [{"id": "x", "kind": "video"}]}}
    )
    assert fields is None
    assert "kind" in (err or "")

    fields, err = parse_section_payload(
        {"type": "freeform", "props": {"blocks_mobile": "nope"}}
    )
    assert fields is None
    assert "陣列" in (err or "")

    fields, err = parse_section_payload(
        {"type": "freeform", "props": {"height": True, "blocks": []}}
    )
    assert err is None
    assert fields["props"]["height"] == 480

    # clamp / NaN / image block / unsafe mobile href
    fields, err = parse_section_payload(
        {
            "type": "freeform",
            "props": {
                "height": 9999,
                "blocks": [
                    {
                        "id": "img1",
                        "kind": "image",
                        "x": -10,
                        "y": "nan",
                        "w": 200,
                        "h": 1,
                        "z": True,
                        "image_url": "/uploads/a.webp",
                        "image_alt": "alt",
                    }
                ],
                "blocks_mobile": [
                    {
                        "id": "m1",
                        "kind": "button",
                        "text": "X",
                        "href": "javascript:evil()",
                    }
                ],
            },
        }
    )
    assert fields is None
    assert "連結格式" in (err or "")

    fields, err = parse_section_payload(
        {
            "type": "freeform",
            "props": {
                "height": 9999,
                "blocks": [
                    {
                        "id": "img1",
                        "kind": "image",
                        "x": -10,
                        "y": "nan",
                        "w": 200,
                        "h": 1,
                        "image_url": "/uploads/a.webp",
                        "image_alt": "alt",
                    }
                ],
            },
        }
    )
    assert err is None
    assert fields["props"]["height"] == 1400
    block = fields["props"]["blocks"][0]
    assert block["x"] == 0.0
    assert block["y"] == 8.0  # NaN → default
    assert block["w"] == 100.0
    assert block["h"] == 6.0
    assert block["image_url"] == "/uploads/a.webp"
    assert fields["props"]["blocks_mobile"] == []


def test_serialize_section_freeform_ssr_props():
    """Legacy rows without blocks_mobile still serialize Next-ready props."""
    row = {
        "id": "11111111-1111-1111-1111-111111111111",
        "page_id": "22222222-2222-2222-2222-222222222222",
        "sort_order": 0,
        "type": "freeform",
        "is_visible": True,
        "props": {
            "height": 400,
            "blocks": [
                {
                    "id": "b1",
                    "kind": "heading",
                    "x": 8,
                    "y": 8,
                    "w": 40,
                    "h": 12,
                    "z": 1,
                    "text": "Hi",
                }
            ],
        },
    }
    out = serialize_section(row)
    assert out["type"] == "freeform"
    assert out["sort_order"] == 0
    assert isinstance(out["props"]["blocks"], list)
    assert out["props"]["blocks"][0]["text"] == "Hi"
    assert out["props"]["blocks_mobile"] == []
    assert "html" not in out


def test_section_props_reject_unsafe_links_and_unknown_fields():
    fields, err = parse_section_payload(
        {"type": "hero", "props": {"title": "x", "cta_href": "javascript:alert(1)"}}
    )
    assert fields is None
    assert "連結格式" in err
    fields, err = parse_section_payload(
        {"type": "hero", "props": {"title": "x", "calculator_embed": True}}
    )
    assert fields is None
    assert "不支援欄位" in err
