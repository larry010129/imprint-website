from app.cms_copy_slots import apply_page_copy_slots, copy_slot_specs, parse_copy_slot_payload


def test_copy_slot_specs_exclude_shop_jewelry():
    for spec in copy_slot_specs():
        assert not spec["page_key"].startswith("/shop/")
        assert not spec["page_key"].startswith("/jewelry/")
        assert spec["page_key"] != "/price"
    signature = [
        spec for spec in copy_slot_specs() if spec["page_key"] == "/series/signature/"
    ]
    assert {spec["slot_key"] for spec in signature} >= {
        "hero-title",
        "hero-lead",
        "cta-calculator",
    }


def test_apply_text_and_button_slots():
    html = (
        '<h1 data-cms-text="hero-title">Old</h1>'
        '<a data-cms-button="cta-calculator" href="/x">Old CTA</a>'
    )
    rows = [
        {
            "slot_key": "hero-title",
            "kind": "text",
            "text_value": "NEW TITLE",
            "default_text": "Old",
            "is_published": True,
        },
        {
            "slot_key": "cta-calculator",
            "kind": "button",
            "text_value": "Start calc",
            "href": "/shop/calculator/",
            "default_text": "Old CTA",
            "default_href": "/x",
            "is_published": True,
        },
    ]
    out = apply_page_copy_slots(html, "/about", rows)
    assert "NEW TITLE" in out
    assert 'href="/shop/calculator/"' in out
    assert "Start calc" in out


def test_apply_text_keeps_markup_when_copy_matches():
    html = '<h1 data-cms-text="hero-title">把最深的情感，<em>銘印成永恆</em></h1>'
    rows = [
        {
            "slot_key": "hero-title",
            "kind": "text",
            "text_value": "把最深的情感，銘印成永恆",
            "default_text": "把最深的情感，銘印成永恆",
            "is_published": True,
        }
    ]
    out = apply_page_copy_slots(html, "/", rows)
    assert "<em>銘印成永恆</em>" in out


def test_copy_slots_escape_text_and_reject_script_links():
    html = '<h1 data-cms-text="hero-title">Old</h1>'
    rows = [
        {
            "slot_key": "hero-title",
            "kind": "text",
            "text_value": "<script>alert(1)</script>",
            "default_text": "Old",
            "is_published": True,
        }
    ]
    out = apply_page_copy_slots(html, "/about", rows)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    fields, err = parse_copy_slot_payload(
        {
            "pageKey": "/about",
            "slotKey": "cta-calculator",
            "href": "javascript:alert(1)",
        }
    )
    assert fields is None
    assert "連結格式" in err
