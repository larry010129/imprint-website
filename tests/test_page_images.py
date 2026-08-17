from collections import Counter
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.content import (
    apply_page_image_replace_stack,
    create_page_image_from_registry,
    delete_page_image_urls_if_unreferenced,
    effective_page_image_url,
    ensure_page_image_row,
    get_page_image_row,
    parse_page_image_payload,
    reset_page_image_row,
    restore_page_image_row,
    serialize_page_image,
)
from app.controllers import web_controller
from app.page_image_slots import (
    PAGE_IMAGE_STORAGE_FOLDERS,
    apply_page_image_slots,
    build_page_image_seed,
    page_image_slot_specs,
    page_image_storage_folder,
    paired_series_slot,
    paired_series_slots,
    sync_paired_series_image,
)

_SUPABASE = "https://abc123.supabase.co"


def _page_url(key: str) -> str:
    return f"{_SUPABASE}/storage/v1/object/public/shop-media/{key}"


@pytest.fixture
def _page_storage_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", _SUPABASE)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "shop-media")


def test_effective_url_falls_back_to_default():
    row = {
        "image_url": "",
        "default_image_url": "/static/a.jpg",
        "is_published": True,
    }
    assert effective_page_image_url(row) == "/static/a.jpg"


def test_base_layout_unregisters_service_worker():
    from pathlib import Path

    html = (
        Path(__file__).resolve().parents[1] / "content/site/templates/layouts/base.html"
    ).read_text(encoding="utf-8")
    assert "serviceWorker" in html
    assert "unregister" in html
    assert "navigator.serviceWorker.register" not in html


def test_home_slot_rewrite_does_not_touch_carousel_duplicate():
    html = (
        '<img src="/static/images/hero/imprint-diamond-family-memorial.jpg">'
        '<img data-cms-slot="poem-visual" '
        'src="/static/images/hero/imprint-diamond-family-memorial.jpg">'
    )
    row = {
        "slot_key": "poem-visual",
        "image_url": "/static/new.jpg",
        "default_image_url": "/static/images/hero/imprint-diamond-family-memorial.jpg",
        "is_published": True,
    }
    out = apply_page_image_slots(html, "/", [row])
    assert out.count("/static/new.jpg") == 1
    assert out.count("/static/images/hero/imprint-diamond-family-memorial.jpg") == 1


def test_home_prefers_local_sky_over_supabase():
    html = (
        '<picture><source srcset="/static/images/ghibli/hero-sky.webp" type="image/webp">'
        '<img data-cms-slot="hero-sky" src="/static/images/ghibli/hero-sky.jpg" '
        'loading="lazy" fetchpriority="low"></picture>'
    )
    row = {
        "slot_key": "hero-sky",
        "display_url": "https://xxx.supabase.co/storage/v1/object/public/cms/hero-sky.png",
        "display_webp": "https://xxx.supabase.co/storage/v1/object/public/cms/hero-sky.webp",
        "is_published": True,
    }
    out = apply_page_image_slots(html, "/", [row])
    assert "/static/images/ghibli/hero-sky.webp" in out
    assert "/static/images/ghibli/hero-sky.jpg" in out
    assert "supabase.co" not in out
    assert 'fetchpriority="low"' in out
    assert 'loading="lazy"' in out


def test_home_series_slot_does_not_remap_remote_to_local_srcset():
    html = (
        '<picture><source type="image/webp" '
        'srcset="/static/images/hero/imprint-diamond-family-portrait-jewelry-800w.webp 800w">'
        '<img data-cms-slot="series-family" '
        'src="/static/images/hero/imprint-diamond-family-portrait-jewelry-800w.webp"></picture>'
    )
    remote = (
        "https://xxx.supabase.co/storage/v1/object/public/cms/"
        "imprint-diamond-family-portrait-jewelry.jpg"
    )
    remote_webp = (
        "https://xxx.supabase.co/storage/v1/object/public/cms/"
        "imprint-diamond-family-portrait-jewelry.webp"
    )
    row = {
        "slot_key": "series-family",
        "display_url": remote,
        "display_webp": remote_webp,
        "is_published": True,
    }
    out = apply_page_image_slots(html, "/", [row])
    assert remote in out
    assert "/static/images/hero/imprint-diamond-family-portrait-jewelry-800w.webp" not in out
    assert "/static/images/hero/imprint-diamond-family-portrait-jewelry-1200w.webp" not in out


def test_home_series_custom_upload_replaces_stale_local_srcset():
    """Admin custom crop must win — stale local srcset must not keep PC hero bytes."""
    html = (
        '<picture><source type="image/webp" '
        'srcset="/static/images/hero/imprint-diamond-wedding-couple-ring-800w.webp 800w, '
        '/static/images/hero/imprint-diamond-wedding-couple-ring-1200w.webp 1200w" '
        'sizes="(max-width:640px) 92vw, 320px">'
        '<img data-cms-slot="series-signature" '
        'src="/static/images/hero/imprint-diamond-wedding-couple-ring-800w.webp" '
        'srcset="/static/images/hero/imprint-diamond-wedding-couple-ring-800w.webp 800w, '
        '/static/images/hero/imprint-diamond-wedding-couple-ring-1200w.webp 1200w" '
        'sizes="(max-width:640px) 92vw, 320px" alt="銘印鑽石"></picture>'
    )
    custom = "https://xxx.supabase.co/storage/v1/object/public/shop-media/page-images/home/1786367609718.webp"
    row = {
        "slot_key": "series-signature",
        "display_url": custom,
        "display_webp": custom,
        "is_published": True,
    }
    out = apply_page_image_slots(html, "/", [row])
    assert custom in out
    assert "imprint-diamond-wedding-couple-ring" not in out
    assert f'src="{custom}"' in out
    assert f'srcset="{custom}"' in out
    assert "<source" not in out.lower()


def test_home_series_love_custom_upload_drops_wedding_couple_srcset():
    html = (
        '<picture><source type="image/webp" '
        'srcset="/static/images/hero/imprint-diamond-wedding-couple-ring-800w.webp 800w, '
        '/static/images/hero/imprint-diamond-wedding-couple-ring-1200w.webp 1200w">'
        '<img data-cms-slot="series-love" '
        'src="/static/images/hero/imprint-diamond-wedding-couple-ring-800w.webp" '
        'srcset="/static/images/hero/imprint-diamond-wedding-couple-ring-800w.webp 800w"></picture>'
    )
    custom = (
        "https://xxx.supabase.co/storage/v1/object/public/shop-media/"
        "page-images/home/image-love-swap.webp"
    )
    stamp = datetime(2026, 8, 17, 6, 0, 0, tzinfo=timezone.utc)
    row = {
        "slot_key": "series-love",
        "display_url": custom,
        "display_webp": (
            "https://xxx.supabase.co/storage/v1/object/public/shop-media/"
            "site-images/hero/imprint-diamond-wedding-couple-ring.webp"
        ),
        "updated_at": stamp,
        "is_published": True,
    }
    out = apply_page_image_slots(html, "/", [row])
    assert f"{custom}?v=1786946400" in out
    assert "imprint-diamond-wedding-couple-ring" not in out
    assert "<source" not in out.lower()


def test_series_overview_custom_upload_does_not_keep_local_srcset():
    html = (
        '<picture><source srcset="/static/images/hero/imprint-diamond-pet-memorial-cat.webp">'
        '<img src="/static/images/hero/imprint-diamond-pet-memorial-cat.jpg" '
        'data-cms-slot="pet"></picture>'
    )
    custom = (
        "https://xxx.supabase.co/storage/v1/object/public/shop-media/"
        "page-images/series-overview/pet-new.webp"
    )
    row = {
        "slot_key": "pet",
        "display_url": custom,
        "display_webp": custom,
        "is_published": True,
    }
    out = apply_page_image_slots(html, "/series", [row])
    assert custom in out
    assert "imprint-diamond-pet-memorial-cat" not in out
    assert "-400w.webp" not in out
    assert "/static/images/hero/" not in out


def _overview_couple_html() -> str:
    couple = (
        "/static/images/hero/imprint-diamond-wedding-couple-ring.webp"
    )
    couple_srcset = (
        f"{couple} 2400w, "
        "/static/images/hero/imprint-diamond-wedding-couple-ring-800w.webp 800w"
    )
    return (
        '<picture><source type="image/webp" '
        f'srcset="{couple_srcset}">'
        f'<img data-cms-slot="love" src="{couple}" '
        f'srcset="{couple_srcset}" alt="結髮鑽石"></picture>'
        '<picture><source type="image/webp" '
        f'srcset="{couple_srcset}">'
        f'<img data-cms-slot="signature" src="{couple}" '
        f'srcset="{couple_srcset}" alt="真我鑽石 detail"></picture>'
        '<picture><source type="image/webp" '
        f'srcset="{couple_srcset}">'
        f'<img data-cms-slot="signature" src="{couple}" '
        f'srcset="{couple_srcset}" alt="真我鑽石 quick"></picture>'
    )


def _mock_series_hero(monkeypatch, hero_url: str, stamp, series_key: str = "signature"):
    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def cursor(self):
            return self

    monkeypatch.setattr("app.database.get_connection", lambda: _Conn())
    monkeypatch.setattr(
        "app.content.fetch_page_image",
        lambda *_a, **_k: {
            "image_url": hero_url,
            "image_webp": hero_url,
            "default_image_url": (
                "/static/images/hero/imprint-diamond-wedding-couple-ring.jpg"
            ),
            "is_published": True,
            "updated_at": stamp,
        }
        if _a[1] == f"/series/{series_key}/"
        else None,
    )


def test_series_overview_signature_uses_custom_hero_not_wedding_couple(monkeypatch):
    """ /series 真我 must follow /series/signature/ 主視覺, not the couple file. """
    custom = (
        "https://xxx.supabase.co/storage/v1/object/public/shop-media/"
        "page-images/signature-diamond/image-122d47ff150e4a70a2f5e9a8bbd328fb.webp"
    )
    leftover = (
        "https://xxx.supabase.co/storage/v1/object/public/shop-media/"
        "page-images/series-overview/imprint-diamond-wedding-couple-ring.webp"
    )
    stamp = datetime(2026, 8, 17, 6, 28, 58, tzinfo=timezone.utc)
    later = datetime(2026, 8, 17, 7, 28, 58, tzinfo=timezone.utc)
    _mock_series_hero(monkeypatch, custom, stamp)
    row = {
        "slot_key": "signature",
        "display_url": leftover,
        "display_webp": leftover,
        "updated_at": stamp,
        "is_published": True,
    }
    out = apply_page_image_slots(_overview_couple_html(), "/series", [row])
    assert f"{custom}?v=1786948138" in out
    assert 'alt="真我鑽石 detail"' in out
    assert 'alt="真我鑽石 quick"' in out
    signature_blocks = [
        block
        for block in out.split("<picture>")
        if 'data-cms-slot="signature"' in block
    ]
    assert len(signature_blocks) == 2
    for block in signature_blocks:
        assert f"{custom}?v=1786948138" in block
        assert "imprint-diamond-wedding-couple-ring" not in block
        assert "<source" not in block.lower()
    love_block = next(
        block for block in out.split("<picture>") if 'data-cms-slot="love"' in block
    )
    assert "imprint-diamond-wedding-couple-ring" in love_block
    assert custom not in love_block

    _mock_series_hero(monkeypatch, custom, later)
    out_later = apply_page_image_slots(
        _overview_couple_html(),
        "/series",
        [{**row, "updated_at": later}],
    )
    assert f"{custom}?v=1786951738" in out_later
    assert f"{custom}?v=1786948138" not in out_later


def test_series_overview_other_series_follow_custom_hero(monkeypatch):
    custom = (
        "https://xxx.supabase.co/storage/v1/object/public/shop-media/"
        "page-images/pet-diamond/pet-hero-swap.webp"
    )
    stamp = datetime(2026, 8, 17, 6, 0, 0, tzinfo=timezone.utc)
    _mock_series_hero(monkeypatch, custom, stamp, series_key="pet")
    stock_srcset = (
        "/static/images/hero/imprint-diamond-pet-memorial-cat-800w.webp 800w, "
        "/static/images/hero/imprint-diamond-pet-memorial-cat.webp 2400w"
    )
    html = (
        f'<picture><source type="image/webp" srcset="{stock_srcset}">'
        '<img data-cms-slot="pet" '
        'src="/static/images/hero/imprint-diamond-pet-memorial-cat.jpg" '
        f'srcset="{stock_srcset}"></picture>'
        f'<picture><source type="image/webp" srcset="{stock_srcset}">'
        '<img data-cms-slot="pet" '
        'src="/static/images/hero/imprint-diamond-pet-memorial-cat.jpg" '
        f'srcset="{stock_srcset}"></picture>'
    )
    row = {
        "slot_key": "pet",
        "display_url": (
            "https://xxx.supabase.co/storage/v1/object/public/shop-media/"
            "page-images/series-overview/imprint-diamond-pet-memorial-cat.webp"
        ),
        "display_webp": (
            "https://xxx.supabase.co/storage/v1/object/public/shop-media/"
            "page-images/series-overview/imprint-diamond-pet-memorial-cat.webp"
        ),
        "is_published": True,
    }
    out = apply_page_image_slots(html, "/series", [row])
    assert f"{custom}?v=1786946400" in out
    assert out.count(f"{custom}?v=1786946400") >= 2
    assert "imprint-diamond-pet-memorial-cat" not in out
    assert "<source" not in out.lower()


def test_series_overview_template_marks_both_images_per_series():
    from pathlib import Path

    html = (
        Path(__file__).resolve().parents[1]
        / "content/site/templates/pages/series.html"
    ).read_text(encoding="utf-8")
    for key in ("first-love", "pet", "love", "family", "heirloom", "signature"):
        assert html.count(f'data-cms-slot="{key}"') == 2


def test_series_overview_indexes_pair_detail_and_quick():
    specs = [spec for spec in page_image_slot_specs() if spec.page_key == "/series"]
    assert [spec.slot_key for spec in specs] == [
        "first-love",
        "pet",
        "love",
        "family",
        "heirloom",
        "signature",
    ]
    for index, spec in enumerate(specs):
        assert spec.image_indexes == (index, index + 6)
        assert spec.indexed is True


def test_paired_series_slots_include_overview_and_home():
    assert paired_series_slots("/series/signature/", "hero") == (
        ("/", "series-signature"),
        ("/series", "signature"),
    )
    assert paired_series_slots("/series/signature", "hero") == (
        ("/", "series-signature"),
        ("/series", "signature"),
    )
    assert paired_series_slots("/series", "signature") == (
        ("/series/signature/", "hero"),
    )
    assert paired_series_slots("/", "series-signature") == (
        ("/series/signature/", "hero"),
    )
    assert paired_series_slot("/series", "signature") == (
        "/series/signature/",
        "hero",
    )
    assert paired_series_slot("/about", "cinema") is None


def test_sync_paired_series_image_updates_overview_and_home():
    updates: list[tuple] = []

    class _Cur:
        def execute(self, _sql, params=None):
            updates.append(params)

    sync_paired_series_image(
        _Cur(),
        "/series/signature/",
        "hero",
        "https://example.test/new.webp",
        "https://example.test/new.webp",
    )
    assert updates == [
        (
            "https://example.test/new.webp",
            "https://example.test/new.webp",
            "/",
            "series-signature",
        ),
        (
            "https://example.test/new.webp",
            "https://example.test/new.webp",
            "/series",
            "signature",
        ),
    ]
    updates.clear()
    sync_paired_series_image(
        _Cur(),
        "/series",
        "pet",
        "https://example.test/pet.webp",
        None,
    )
    assert updates == [
        (
            "https://example.test/pet.webp",
            None,
            "/series/pet/",
            "hero",
        )
    ]


def test_stock_remote_series_hero_does_not_override_custom_home_card(monkeypatch):
    stock = (
        "https://xxx.supabase.co/storage/v1/object/public/shop-media/"
        "site-images/hero/imprint-diamond-newborn-baby-necklace.jpg"
    )
    custom = (
        "https://xxx.supabase.co/storage/v1/object/public/shop-media/"
        "page-images/home/moon-swap.webp"
    )

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def cursor(self):
            return self

    monkeypatch.setattr("app.database.get_connection", lambda: _Conn())
    monkeypatch.setattr(
        "app.content.fetch_page_image",
        lambda *_a, **_k: {
            "image_url": stock,
            "image_webp": stock.replace(".jpg", ".webp"),
            "default_image_url": "/static/images/hero/imprint-diamond-newborn-baby-necklace.jpg",
            "is_published": True,
            "updated_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        },
    )
    html = (
        '<img data-cms-slot="series-first-love" '
        'src="/static/images/hero/imprint-diamond-newborn-baby-necklace-800w.webp" '
        'srcset="/static/images/hero/imprint-diamond-newborn-baby-necklace-800w.webp 800w">'
    )
    out = apply_page_image_slots(
        html,
        "/",
        [
            {
                "slot_key": "series-first-love",
                "display_url": custom,
                "display_webp": custom,
                "is_published": True,
            }
        ],
    )
    assert custom in out
    assert "imprint-diamond-newborn-baby-necklace" not in out


def test_home_dna_cta_prefers_local_webp():
    html = '<img data-cms-slot="dna-cta-diamond" src="/static/images/diamonds/colors/blue.webp">'
    row = {
        "slot_key": "dna-cta-diamond",
        "display_url": "https://xxx.supabase.co/storage/v1/object/public/cms/colors/blue.png",
        "display_webp": "",
        "is_published": True,
    }
    out = apply_page_image_slots(html, "/", [row])
    assert 'src="/static/images/diamonds/colors/blue-320.webp"' in out
    assert "cms/colors/blue" not in out


def test_home_dna_cta_rewrites_to_diamond_media_base(monkeypatch):
    from app.image_urls import rewrite_shop_stills_in_html

    monkeypatch.setenv("SUPABASE_URL", "https://abc123.supabase.co")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "shop-media")
    html = '<img data-cms-slot="dna-cta-diamond" src="/static/images/diamonds/colors/blue.webp">'
    row = {
        "slot_key": "dna-cta-diamond",
        "display_url": "https://xxx.supabase.co/storage/v1/object/public/cms/colors/blue.png",
        "display_webp": "",
        "is_published": True,
    }
    out = rewrite_shop_stills_in_html(apply_page_image_slots(html, "/", [row]))
    assert (
        'src="https://abc123.supabase.co/storage/v1/object/public/shop-media/'
        'site-images/diamonds/colors/blue-320.webp"'
    ) in out
    assert "cms/colors/blue" not in out


def test_page_image_storage_folders_cover_admin_tabs():
    """Every 頁面圖片 tab page_key maps to a stable English folder."""
    page_keys = {spec.page_key for spec in page_image_slot_specs()}
    assert page_keys == set(PAGE_IMAGE_STORAGE_FOLDERS)
    assert PAGE_IMAGE_STORAGE_FOLDERS["/"] == "home"
    assert PAGE_IMAGE_STORAGE_FOLDERS["/about"] == "brand-story"
    assert PAGE_IMAGE_STORAGE_FOLDERS["/journal"] == "journal"
    assert PAGE_IMAGE_STORAGE_FOLDERS["/series"] == "series-overview"
    assert PAGE_IMAGE_STORAGE_FOLDERS["/series/first-love/"] == "moon-diamond"
    assert PAGE_IMAGE_STORAGE_FOLDERS["/series/pet/"] == "pet-diamond"
    assert PAGE_IMAGE_STORAGE_FOLDERS["/series/love/"] == "wedding-diamond"
    assert PAGE_IMAGE_STORAGE_FOLDERS["/series/family/"] == "family-diamond"
    assert PAGE_IMAGE_STORAGE_FOLDERS["/series/heirloom/"] == "life-diamond"
    assert PAGE_IMAGE_STORAGE_FOLDERS["/series/signature/"] == "signature-diamond"
    assert PAGE_IMAGE_STORAGE_FOLDERS["/what-is-dna-diamond"] == "dna-diamond"
    assert PAGE_IMAGE_STORAGE_FOLDERS["/privacy"] == "privacy"
    assert PAGE_IMAGE_STORAGE_FOLDERS["/return-policy"] == "return-policy"
    assert page_image_storage_folder(None) == "_pending"
    assert page_image_storage_folder("/series/pet") == "pet-diamond"
    assert page_image_storage_folder("/series/signature/") == "signature-diamond"
    assert page_image_storage_folder("/privacy") == "privacy"
    assert page_image_storage_folder("/return-policy") == "return-policy"


def test_inventory_excludes_empty_calculator_and_jewelry_slots():
    rows = build_page_image_seed()
    counts = Counter(row["page_key"] for row in rows)
    by_slot = {row["slot_key"]: row for row in rows if row["page_key"] == "/what-is-dna-diamond"}
    assert len(rows) == 52
    assert len(counts) == 13
    assert counts["/journal"] == 1
    assert counts["/about"] == 3
    assert counts["/what-is-dna-diamond"] == 14
    assert counts["/series/signature/"] == 2
    assert counts["/privacy"] == 1
    assert counts["/return-policy"] == 1
    assert "/shop/calculator/" not in counts
    assert not any(key.startswith("/jewelry") for key in counts)
    assert "intro" in by_slot
    assert by_slot["intro"]["default_image_url"] == (
        "/static/images/dna-process/what-is-dna-diamond-hero.png"
    )
    assert "lab-photo" in by_slot
    assert by_slot["lab-photo"]["slot_label"] == "在地實驗室（主文區）"
    assert by_slot["lab-photo"]["default_image_url"] == ""
    assert "usp-lab-photo" in by_slot
    assert by_slot["usp-lab-photo"]["slot_label"] == "四大保障・在地實驗室"
    assert by_slot["usp-lab-photo"]["default_image_url"] == ""
    empty_slots = {"lab-photo", "usp-lab-photo", "hero"}
    assert all(row["default_image_url"] or row["slot_key"] in empty_slots for row in rows)
    assert all(not str(row["default_image_url"]).startswith("{{") for row in rows)


def test_signature_series_page_label_is_true_self_not_brand():
    """Admin 頁面圖片 / series-overview use 真我鑽石; brand 銘印鑽石 stays elsewhere."""
    specs = page_image_slot_specs()
    signature = [spec for spec in specs if spec.page_key == "/series/signature/"]
    assert signature
    assert all(spec.page_label == "真我鑽石" for spec in signature)
    overview = next(spec for spec in specs if spec.page_key == "/series" and spec.slot_key == "signature")
    assert overview.slot_label == "系列・真我鑽石"
    home = next(spec for spec in specs if spec.page_key == "/" and spec.slot_key == "series-signature")
    assert home.slot_label == "系列卡・真我鑽石"
    assert all(spec.page_label != "銘印鑽石" for spec in signature)
    about = next(spec for spec in specs if spec.page_key == "/about" and spec.slot_key == "cinema")
    assert "銘印鑽石" in about.image_alt


def test_legal_pages_with_hero_binding_have_empty_slots():
    rows = {row["page_key"]: row for row in build_page_image_seed() if row["page_key"] in {"/privacy", "/return-policy"}}
    assert rows["/privacy"]["slot_key"] == "hero"
    assert rows["/privacy"]["label"] == "隱私權政策"
    assert rows["/privacy"]["slot_label"] == "頁首圖片"
    assert rows["/privacy"]["default_image_url"] == ""
    assert rows["/return-policy"]["slot_key"] == "hero"
    assert rows["/return-policy"]["label"] == "退換貨政策"
    assert rows["/return-policy"]["default_image_url"] == ""


def test_copy_pages_without_content_images_have_no_slots():
    """Audit: text-only / chrome-only 內容 pages must not invent 頁面圖片 slots."""
    page_keys = {spec.page_key for spec in page_image_slot_specs()}
    for route in (
        "/diamond-4c",
        "/lab-grown-diamond",
        "/diamond-comparison",
        "/contact",
        "/faq",
        "/stories",
        "/terms",
    ):
        assert route not in page_keys


def test_payload_requires_valid_slot_key():
    fields, error = parse_page_image_payload({"pageKey": "/", "imageUrl": "/x.jpg"})
    assert fields is None
    assert error == "缺少 slot_key"
    fields, error = parse_page_image_payload(
        {"pageKey": "/", "slotKey": "poem-visual", "imageUrl": "/x.jpg"}
    )
    assert error is None
    assert fields and fields["slot_key"] == "poem-visual"


def test_create_page_image_from_registry_inserts_missing_slot():
    from app.content import create_page_image_from_registry, fetch_missing_page_image_slots

    class FakeCursor:
        def __init__(self):
            self.rows = {}
            self.last = None

        def execute(self, query, params=None):
            self.last = query
            if "select page_key, slot_key from page_images" in query:
                self._fetchall = [{"page_key": k, "slot_key": s} for (k, s) in self.rows]
            elif "select * from page_images where" in query or (
                "select page_key from page_images where" in query
            ):
                pk, sk = params
                self._fetchone = self.rows.get((pk, sk)) or (
                    {"page_key": pk} if (pk, sk) in self.rows else None
                )
            elif query.strip().startswith("insert into page_images"):
                pk, sk = params[0], params[1]
                row = {
                    "page_key": pk,
                    "slot_key": sk,
                    "label": params[2],
                    "slot_label": params[3],
                    "group_key": params[4],
                    "image_url": params[5],
                    "image_webp": params[6],
                    "image_alt": params[7],
                    "default_image_url": params[8],
                    "default_image_webp": params[9],
                    "target_w": params[10],
                    "target_h": params[11],
                    "sort_order": params[12],
                    "is_published": True,
                }
                self.rows[(pk, sk)] = row
                self._fetchone = row

        def fetchall(self):
            return getattr(self, "_fetchall", [])

        def fetchone(self):
            return getattr(self, "_fetchone", None)

    cur = FakeCursor()
    cur.rows[("/about", "cinema")] = {"page_key": "/about", "slot_key": "cinema"}
    missing = fetch_missing_page_image_slots(cur)
    assert missing
    assert all(item["page_key"] != "/shop/calculator/" for item in missing)

    target = next(item for item in missing if item["page_key"] == "/about")
    created, error = create_page_image_from_registry(cur, target["page_key"], target["slot_key"])
    assert error is None
    assert created and created["slot_key"] == target["slot_key"]

    again, dup_error = create_page_image_from_registry(cur, target["page_key"], target["slot_key"])
    assert again is None
    assert dup_error == "此區塊已存在"


def test_signature_tab_label_is_true_self_not_brand():
    specs = [s for s in page_image_slot_specs() if s.page_key == "/series/signature/"]
    assert {s.slot_key for s in specs} == {"hero", "intro"}
    assert all(s.page_label == "真我鑽石" for s in specs)
    assert all(s.allow_empty for s in specs)
    assert all(s.slot_label in {"主視覺", "介紹圖"} for s in specs)


def test_payload_normalizes_signature_trailing_slash():
    """Admin save sends /series/signature/; normpath drops the slash."""
    fields, error = parse_page_image_payload(
        {
            "pageKey": "/series/signature/",
            "slotKey": "hero",
            "imageUrl": "/static/new.jpg",
        }
    )
    assert error is None
    assert fields
    assert fields["page_key"] == "/series/signature"
    assert fields["slot_key"] == "hero"


def test_get_page_image_row_resolves_slash_alias():
    """DB/registry key is /series/signature/; UPDATE looks up /series/signature."""

    class FakeCursor:
        def __init__(self):
            self.rows = {}
            self.queries = []

        def execute(self, query, params=None):
            self.queries.append((query, params))
            if "select * from page_images where" in query:
                pk, sk = params
                self._fetchone = self.rows.get((pk, sk))
            else:
                self._fetchone = None

        def fetchone(self):
            return getattr(self, "_fetchone", None)

    cur = FakeCursor()
    stored = {
        "page_key": "/series/signature/",
        "slot_key": "hero",
        "label": "真我鑽石",
        "slot_label": "主視覺",
        "image_url": "/static/old.jpg",
    }
    cur.rows[("/series/signature/", "hero")] = stored
    row = get_page_image_row(cur, "/series/signature", "hero")
    assert row is stored
    assert row["page_key"] == "/series/signature/"
    assert get_page_image_row(cur, "/series/signature/", "hero") is stored
    assert get_page_image_row(cur, "/series/signature.html", "hero") is stored


def test_ensure_page_image_row_upserts_unseeded_signature_hero():
    """Valid 主視覺 in registry must insert, not 404, when the row was never seeded."""

    class FakeCursor:
        def __init__(self):
            self.rows = {}
            self.last = None

        def execute(self, query, params=None):
            self.last = query
            if "select * from page_images where" in query:
                pk, sk = params
                self._fetchone = self.rows.get((pk, sk))
            elif query.strip().startswith("insert into page_images"):
                pk, sk = params[0], params[1]
                row = {
                    "page_key": pk,
                    "slot_key": sk,
                    "label": params[2],
                    "slot_label": params[3],
                    "group_key": params[4],
                    "image_url": params[5],
                    "image_webp": params[6],
                    "image_alt": params[7],
                    "default_image_url": params[8],
                    "default_image_webp": params[9],
                    "target_w": params[10],
                    "target_h": params[11],
                    "sort_order": params[12],
                    "is_published": True,
                }
                self.rows[(pk, sk)] = row
                self._fetchone = row
            else:
                self._fetchone = None

        def fetchone(self):
            return getattr(self, "_fetchone", None)

    cur = FakeCursor()
    row, err = ensure_page_image_row(cur, "/series/signature", "hero")
    assert err is None
    assert row is not None
    assert row["page_key"] == "/series/signature/"
    assert row["slot_key"] == "hero"
    assert row["slot_label"] == "主視覺"
    assert row["label"] == "真我鑽石"

    created, dup = create_page_image_from_registry(cur, "/series/signature/", "hero")
    assert created is None
    assert dup == "此區塊已存在"

    again, again_err = ensure_page_image_row(cur, "/series/signature/", "hero")
    assert again_err is None
    assert again["page_key"] == "/series/signature/"


def test_dna_template_marks_cms_slots():
    from pathlib import Path

    html = (
        Path(__file__).resolve().parents[1]
        / "content/site/templates/pages/what-is-dna-diamond.html"
    ).read_text(encoding="utf-8")
    for slot in (
        "intro",
        "process-sample",
        "process-growth",
        "process-cutting",
        "process-certificate",
        "process-jewelry",
        "process-memorial-box",
        "sample-quantity",
        "lab-photo",
        "assurance-certificate",
        "usp-lab-photo",
        "usp-certificate",
        "usp-memorial-box",
        "usp-jewelry-making",
    ):
        assert f'data-cms-slot="{slot}"' in html or f"dna_img('{slot}'" in html
    assert "/static/images/dna-process/what-is-dna-diamond-hero.png" in html
    assert "/static/images/dna-process/collect-bottle.png" in html


def test_dna_slot_rewrite_updates_marked_process_image():
    html = (
        '<img data-cms-slot="process-sample" '
        'src="/static/images/dna-process/collect-bottle.png">'
    )
    row = {
        "slot_key": "process-sample",
        "image_url": "/static/uploads/cms/dna-sample.png",
        "default_image_url": "/static/images/dna-process/collect-bottle.png",
        "is_published": True,
    }
    out = apply_page_image_slots(html, "/what-is-dna-diamond", [row])
    assert "/static/uploads/cms/dna-sample.png" in out
    assert "collect-bottle.png" not in out


def test_page_image_loader_reuses_per_route_cache(monkeypatch):
    calls = []

    class Resource:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def cursor(self):
            return self

    rows = [
            {"page_key": "/series/pet/", "slot_key": "hero"},
            {"page_key": "/series/pet/", "slot_key": "intro"},
            {"page_key": "/series/love/", "slot_key": "hero"},
            {"page_key": "/what-is-dna-diamond", "slot_key": "intro"},
            {"page_key": "/what-is-dna-diamond", "slot_key": "process-sample"},
    ]

    def fetch_page_images(_cur, route):
        calls.append(route)
        return [row for row in rows if row["page_key"] == route]

    monkeypatch.setattr(web_controller, "monotonic", lambda: 120)
    monkeypatch.setattr("app.database.get_connection", Resource)
    monkeypatch.setattr("app.content.fetch_page_images", fetch_page_images)
    web_controller.clear_page_image_cache()
    assert len(web_controller._load_page_images("/series/pet/")) == 2
    assert web_controller._load_page_image("/series/pet/")["slot_key"] == "hero"
    assert web_controller._load_page_image("/series/love/")["slot_key"] == "hero"
    assert web_controller._load_page_image("/what-is-dna-diamond")["slot_key"] == "intro"
    assert calls == ["/series/pet/", "/series/love/", "/what-is-dna-diamond"]
    web_controller.clear_page_image_cache()


def test_shop_calculator_context_skips_page_images_and_catalog_ssr(monkeypatch):
    """Shop HTML must not pay page_images aliases or per-category catalog SSR."""
    from starlette.requests import Request

    from config.routes import PAGE_PRIVACY, SHOP_CALCULATOR

    image_calls: list[str] = []
    catalog_calls: list[str] = []

    def fake_page_images(route):
        image_calls.append(route)
        return [{"slot_key": "hero", "display_url": "/x.jpg", "display_webp": None}]

    def boom_catalog(*_a, **_k):
        catalog_calls.append("fetch_catalog_rows")
        raise AssertionError("shop HTML must not fetch catalog rows")

    def boom_categories(*_a, **_k):
        catalog_calls.append("fetch_categories")
        raise AssertionError("shop HTML must not fetch categories")

    monkeypatch.setattr(web_controller, "_load_page_images", fake_page_images)
    monkeypatch.setattr(web_controller, "_load_page_copy_slots", lambda _route: [])
    monkeypatch.setattr("app.catalog.fetch_catalog_rows", boom_catalog)
    monkeypatch.setattr("app.product_categories.fetch_categories", boom_categories)

    request = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/shop/calculator/",
            "raw_path": b"/shop/calculator/",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 0),
            "server": ("127.0.0.1", 8080),
        }
    )
    shop_ctx = web_controller._context(request, SHOP_CALCULATOR)
    assert shop_ctx["shop_catalog_ssr"] == []
    assert shop_ctx["page_images"] == []
    assert shop_ctx["page_image"] is None
    assert image_calls == []
    assert catalog_calls == []

    privacy_ctx = web_controller._context(request, PAGE_PRIVACY)
    assert image_calls == ["/privacy"]
    assert privacy_ctx["page_images"][0]["slot_key"] == "hero"


def test_delete_page_image_urls_unreferenced_calls_delete(
    monkeypatch, _page_storage_env
):
    url = _page_url("page-images/about/a.webp")
    deleted: list[str] = []
    monkeypatch.setattr(
        "app.storage.delete_by_url",
        lambda u: deleted.append(u) or True,
    )
    monkeypatch.setattr(
        "app.content.ensure_page_images_previous_columns",
        lambda _cur: None,
    )
    cur = MagicMock()
    cur.fetchone.return_value = None
    assert delete_page_image_urls_if_unreferenced(cur, [url, url]) == 1
    assert deleted == [url]


def test_delete_page_image_urls_keeps_referenced(monkeypatch, _page_storage_env):
    url = _page_url("page-images/about/a.webp")
    monkeypatch.setattr(
        "app.storage.delete_by_url",
        lambda _u: (_ for _ in ()).throw(AssertionError("must not delete")),
    )
    monkeypatch.setattr(
        "app.content.ensure_page_images_previous_columns",
        lambda _cur: None,
    )
    cur = MagicMock()
    cur.fetchone.return_value = {"ok": 1}
    assert delete_page_image_urls_if_unreferenced(cur, [url]) == 0


def test_delete_page_image_urls_shared_then_last_ref(monkeypatch, _page_storage_env):
    """Shared URL: keep while any row refs; delete when last gone."""
    url = _page_url("page-images/about/shared.webp")
    deleted: list[str] = []
    monkeypatch.setattr(
        "app.storage.delete_by_url",
        lambda u: deleted.append(u) or True,
    )
    monkeypatch.setattr(
        "app.content.ensure_page_images_previous_columns",
        lambda _cur: None,
    )
    cur = MagicMock()
    cur.fetchone.return_value = {"ok": 1}
    assert delete_page_image_urls_if_unreferenced(cur, [url]) == 0
    assert deleted == []
    cur.fetchone.return_value = None
    assert delete_page_image_urls_if_unreferenced(cur, [url]) == 1
    assert deleted == [url]


def test_delete_page_image_urls_skips_non_page_images(monkeypatch, _page_storage_env):
    product = _page_url("products/prod-1/white/a.webp")
    local = "/static/uploads/page-images/x.png"
    keep = _page_url("page-images/about/.keep")
    monkeypatch.setattr(
        "app.storage.delete_by_url",
        lambda _u: (_ for _ in ()).throw(AssertionError("must not delete")),
    )
    monkeypatch.setattr(
        "app.content.ensure_page_images_previous_columns",
        lambda _cur: None,
    )
    cur = MagicMock()
    assert delete_page_image_urls_if_unreferenced(cur, [product, local, keep, ""]) == 0
    cur.execute.assert_not_called()


def test_delete_page_image_urls_keeps_default_and_previous_refs(
    monkeypatch, _page_storage_env
):
    """SQL must check image_*, default_*, and previous_* columns."""
    url = _page_url("page-images/about/kept.webp")
    monkeypatch.setattr(
        "app.storage.delete_by_url",
        lambda _u: (_ for _ in ()).throw(AssertionError("must not delete")),
    )
    monkeypatch.setattr(
        "app.content.ensure_page_images_previous_columns",
        lambda _cur: None,
    )
    cur = MagicMock()
    cur.fetchone.return_value = {"ok": 1}
    assert delete_page_image_urls_if_unreferenced(cur, [url]) == 0
    sql = str(cur.execute.call_args.args[0]).lower()
    for col in (
        "image_url",
        "image_webp",
        "default_image_url",
        "default_image_webp",
        "previous_image_url",
        "previous_image_webp",
    ):
        assert col in sql


def _base_row(**overrides):
    row = {
        "page_key": "/about",
        "slot_key": "cinema",
        "image_url": "",
        "image_webp": None,
        "image_alt": "",
        "is_published": True,
        "default_image_url": "/static/images/about/default.jpg",
        "default_image_webp": "/static/images/about/default.webp",
        "previous_image_url": None,
        "previous_image_webp": None,
    }
    row.update(overrides)
    return row


class _StackCur:
    """Minimal cursor stub for replace/restore/reset stack helpers."""

    def __init__(self, state: dict):
        self.state = state
        self._sql = ""
        self._params = None
        self._ref = False

    def execute(self, sql, params=None):
        sql_l = str(sql).lower()
        self._sql = sql_l
        self._params = params
        if "update page_images" in sql_l and "previous_image_url = %s" in sql_l:
            # replace stack advance
            (
                self.state["image_url"],
                self.state["image_webp"],
                self.state["image_alt"],
                self.state["is_published"],
                self.state["previous_image_url"],
                self.state["previous_image_webp"],
            ) = params[:6]
        elif "update page_images" in sql_l and "previous_image_url = null" in sql_l:
            if "image_url = default_image_url" in sql_l:
                self.state["image_url"] = self.state["default_image_url"]
                self.state["image_webp"] = self.state["default_image_webp"]
                self.state["previous_image_url"] = None
                self.state["previous_image_webp"] = None
                self.state["is_published"] = True
            elif "image_url = %s" in sql_l and "previous_image_url = null" in sql_l:
                # restore
                self.state["image_url"] = params[0]
                self.state["image_webp"] = params[1]
                self.state["previous_image_url"] = None
                self.state["previous_image_webp"] = None
        elif "update page_images" in sql_l and "image_alt = %s" in sql_l:
            if "image_webp = %s" in sql_l and "previous_image" not in sql_l:
                self.state["image_webp"] = params[0]
                self.state["image_alt"] = params[1]
                self.state["is_published"] = params[2]
            else:
                self.state["image_alt"] = params[0]
                self.state["is_published"] = params[1]
        if "select 1 from page_images" in sql_l:
            url = params[0]
            self._ref = url in {
                self.state.get("image_url"),
                self.state.get("image_webp"),
                self.state.get("default_image_url"),
                self.state.get("default_image_webp"),
                self.state.get("previous_image_url"),
                self.state.get("previous_image_webp"),
            }

    def fetchone(self):
        if "select 1 from page_images" in self._sql:
            return {"ok": 1} if self._ref else None
        if "update page_images" in self._sql:
            return dict(self.state)
        return None


def test_replace_a_to_b_keeps_previous_not_deleted(monkeypatch, _page_storage_env):
    a = _page_url("page-images/about/a.webp")
    b = _page_url("page-images/about/b.webp")
    deleted: list[str] = []
    monkeypatch.setattr(
        "app.storage.delete_by_url",
        lambda u: deleted.append(u) or True,
    )
    monkeypatch.setattr(
        "app.content.ensure_page_images_previous_columns",
        lambda _cur: None,
    )
    state = _base_row(image_url=a, image_webp=a)
    cur = _StackCur(state)
    row = apply_page_image_replace_stack(
        cur,
        dict(state),
        new_url=b,
        new_webp=b,
        image_alt="",
        is_published=True,
        webp_provided=True,
    )
    assert row["image_url"] == b
    assert row["previous_image_url"] == a
    assert deleted == []


def test_replace_b_to_c_drops_a(monkeypatch, _page_storage_env):
    a = _page_url("page-images/about/a.webp")
    b = _page_url("page-images/about/b.webp")
    c = _page_url("page-images/about/c.webp")
    deleted: list[str] = []
    monkeypatch.setattr(
        "app.storage.delete_by_url",
        lambda u: deleted.append(u) or True,
    )
    monkeypatch.setattr(
        "app.content.ensure_page_images_previous_columns",
        lambda _cur: None,
    )
    state = _base_row(
        image_url=b,
        image_webp=b,
        previous_image_url=a,
        previous_image_webp=a,
    )
    cur = _StackCur(state)
    row = apply_page_image_replace_stack(
        cur,
        dict(state),
        new_url=c,
        new_webp=c,
        image_alt="",
        is_published=True,
        webp_provided=True,
    )
    assert row["image_url"] == c
    assert row["previous_image_url"] == b
    assert deleted == [a]


def test_restore_swaps_and_gc_current(monkeypatch, _page_storage_env):
    b = _page_url("page-images/about/b.webp")
    c = _page_url("page-images/about/c.webp")
    deleted: list[str] = []
    monkeypatch.setattr(
        "app.storage.delete_by_url",
        lambda u: deleted.append(u) or True,
    )
    monkeypatch.setattr(
        "app.content.ensure_page_images_previous_columns",
        lambda _cur: None,
    )
    state = _base_row(
        image_url=c,
        image_webp=c,
        previous_image_url=b,
        previous_image_webp=b,
    )
    cur = _StackCur(state)
    row, err = restore_page_image_row(cur, dict(state))
    assert err is None
    assert row["image_url"] == b
    assert row["previous_image_url"] is None
    assert deleted == [c]


def test_reset_gc_custom_never_defaults(monkeypatch, _page_storage_env):
    custom = _page_url("page-images/about/custom.webp")
    prev = _page_url("page-images/about/prev.webp")
    default_url = "/static/images/about/default.jpg"
    default_webp = "/static/images/about/default.webp"
    deleted: list[str] = []
    monkeypatch.setattr(
        "app.storage.delete_by_url",
        lambda u: deleted.append(u) or True,
    )
    monkeypatch.setattr(
        "app.content.ensure_page_images_previous_columns",
        lambda _cur: None,
    )
    state = _base_row(
        image_url=custom,
        image_webp=custom,
        previous_image_url=prev,
        previous_image_webp=prev,
        default_image_url=default_url,
        default_image_webp=default_webp,
    )
    cur = _StackCur(state)
    row = reset_page_image_row(cur, dict(state))
    assert row["image_url"] == default_url
    assert row["image_webp"] == default_webp
    assert row["previous_image_url"] is None
    assert set(deleted) == {custom, prev}
    assert default_url not in deleted
    assert default_webp not in deleted


def test_replace_does_not_stash_default_as_previous(monkeypatch, _page_storage_env):
    default_url = "/static/images/about/default.jpg"
    b = _page_url("page-images/about/b.webp")
    deleted: list[str] = []
    monkeypatch.setattr(
        "app.storage.delete_by_url",
        lambda u: deleted.append(u) or True,
    )
    monkeypatch.setattr(
        "app.content.ensure_page_images_previous_columns",
        lambda _cur: None,
    )
    state = _base_row(image_url=default_url, image_webp=None)
    cur = _StackCur(state)
    row = apply_page_image_replace_stack(
        cur,
        dict(state),
        new_url=b,
        new_webp=b,
        image_alt="",
        is_published=True,
        webp_provided=True,
    )
    assert row["image_url"] == b
    assert row["previous_image_url"] is None
    assert deleted == []


def test_cache_buster_replaces_existing_v_without_doubling_query():
    from app.image_urls import strip_cache_buster, with_cache_buster

    stamp = datetime(2025, 8, 12, 3, 12, 44, tzinfo=timezone.utc)
    busted = with_cache_buster("/static/images/learn-cards/faq.jpg?v=4", stamp)
    assert busted == "/static/images/learn-cards/faq.jpg?v=1754968364"
    assert busted.count("?") == 1
    assert busted.count("v=") == 1
    # Idempotent: re-busting the same row does not stack params.
    assert with_cache_buster(busted, stamp) == busted
    assert strip_cache_buster(busted) == "/static/images/learn-cards/faq.jpg"
    # Naive timestamps are read as UTC so the token is deterministic.
    assert with_cache_buster("/a.jpg", datetime(2025, 8, 12, 3, 12, 44)) == "/a.jpg?v=1754968364"
    assert with_cache_buster("/a.jpg", None) == "/a.jpg"


def test_cache_buster_pins_srcset_urls_and_keeps_other_params():
    from app.image_urls import with_cache_buster

    stamp = datetime(2025, 8, 12, 3, 12, 44, tzinfo=timezone.utc)
    srcset = "/static/images/learn-cards/faq-400.webp 400w, /static/images/learn-cards/faq.webp 800w"
    assert with_cache_buster(srcset, stamp) == (
        "/static/images/learn-cards/faq-400.webp?v=1754968364 400w, "
        "/static/images/learn-cards/faq.webp?v=1754968364 800w"
    )
    assert with_cache_buster("/a.jpg?w=800", stamp) == "/a.jpg?w=800&v=1754968364"


def test_serialize_page_image_busts_custom_and_default_from_updated_at():
    stamp = datetime(2025, 8, 12, 3, 12, 44, tzinfo=timezone.utc)
    later = datetime(2026, 8, 17, 6, 0, 0, tzinfo=timezone.utc)
    custom = _page_url("page-images/about/c.webp")
    row = serialize_page_image(
        _base_row(image_url=custom, image_webp=custom, updated_at=stamp)
    )
    assert row["display_url"] == f"{custom}?v=1754968364"
    assert row["display_webp"] == f"{custom}?v=1754968364"
    # Raw columns stay clean so a save round-trip cannot persist the buster.
    assert row["image_url"] == custom
    fallback = serialize_page_image(_base_row(updated_at=stamp))
    assert fallback["display_url"] == "/static/images/about/default.jpg?v=1754968364"
    assert fallback["display_webp"] == "/static/images/about/default.webp?v=1754968364"
    refreshed = serialize_page_image(_base_row(updated_at=later))
    assert refreshed["display_url"] == "/static/images/about/default.jpg?v=1786946400"
    assert refreshed["display_url"] != fallback["display_url"]


def test_page_image_payload_strips_round_tripped_buster():
    fields, error = parse_page_image_payload(
        {
            "pageKey": "/",
            "slotKey": "poem-visual",
            "imageUrl": _page_url("page-images/home/a.webp") + "?v=1754968364",
            "imageWebp": _page_url("page-images/home/a.webp") + "?v=1754968364",
        }
    )
    assert error is None
    assert fields
    assert fields["image_url"] == _page_url("page-images/home/a.webp")
    assert fields["image_webp"] == _page_url("page-images/home/a.webp")


def test_serialize_page_image_exposes_previous_camel():
    row = serialize_page_image(
        _base_row(
            previous_image_url=_page_url("page-images/about/a.webp"),
            previous_image_webp=_page_url("page-images/about/a.webp"),
            target_w=1600,
            target_h=900,
            sort_order=0,
        )
    )
    assert row["previousImageUrl"] == row["previous_image_url"]
    assert row["previousImageWebp"] == row["previous_image_webp"]
    assert row["previous_image_url"].endswith("/a.webp")


def test_replace_b_to_c_keeps_shared_previous_a(monkeypatch, _page_storage_env):
    """B→C drops previous A only when unreferenced; shared A stays."""
    a = _page_url("page-images/about/shared-a.webp")
    b = _page_url("page-images/about/b.webp")
    c = _page_url("page-images/about/c.webp")
    deleted: list[str] = []
    monkeypatch.setattr(
        "app.storage.delete_by_url",
        lambda u: deleted.append(u) or True,
    )
    monkeypatch.setattr(
        "app.content.ensure_page_images_previous_columns",
        lambda _cur: None,
    )
    shared_alive = {a}

    class SharedCur(_StackCur):
        def execute(self, sql, params=None):
            super().execute(sql, params)
            if "select 1 from page_images" in self._sql:
                url = params[0]
                self._ref = url in shared_alive or url in {
                    self.state.get("image_url"),
                    self.state.get("image_webp"),
                    self.state.get("default_image_url"),
                    self.state.get("default_image_webp"),
                    self.state.get("previous_image_url"),
                    self.state.get("previous_image_webp"),
                }

    state = _base_row(
        image_url=b,
        image_webp=b,
        previous_image_url=a,
        previous_image_webp=a,
    )
    cur = SharedCur(state)
    row = apply_page_image_replace_stack(
        cur,
        dict(state),
        new_url=c,
        new_webp=c,
        image_alt="",
        is_published=True,
        webp_provided=True,
    )
    assert row["image_url"] == c
    assert row["previous_image_url"] == b
    assert deleted == []

    shared_alive.clear()
    state2 = _base_row(
        image_url=b,
        image_webp=b,
        previous_image_url=a,
        previous_image_webp=a,
    )
    cur2 = _StackCur(state2)
    row2 = apply_page_image_replace_stack(
        cur2,
        dict(state2),
        new_url=c,
        new_webp=c,
        image_alt="",
        is_published=True,
        webp_provided=True,
    )
    assert row2["previous_image_url"] == b
    assert deleted == [a]
