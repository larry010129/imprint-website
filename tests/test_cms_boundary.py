from app.cms_boundary import (
    assert_content_page_key,
    is_reserved_cms_slug,
    is_reserved_page_key,
    validate_cms_slug,
)
from app.cms_pages import DEFAULT_PROPS, SECTION_TYPES, parse_section_payload


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
    assert "calculator_embed" not in SECTION_TYPES
    assert DEFAULT_PROPS["image_text"]["layout"] == "stack"
    fields, err = parse_section_payload({"type": "image_text", "props": {}})
    assert err is None
    assert fields["props"]["layout"] == "stack"
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
