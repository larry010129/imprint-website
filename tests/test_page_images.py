from collections import Counter

from app.content import effective_page_image_url, parse_page_image_payload
from app.controllers import web_controller
from app.page_image_slots import apply_page_image_slots, build_page_image_seed


def test_effective_url_falls_back_to_default():
    row = {
        "image_url": "",
        "default_image_url": "/static/a.jpg",
        "is_published": True,
    }
    assert effective_page_image_url(row) == "/static/a.jpg"


def test_home_slot_rewrite_does_not_touch_carousel_duplicate():
    html = (
        '<img src="/static/images/hero/imprint-diamond-family-memorial.jpg">'
        '<img data-cms-slot="cta-scene" '
        'src="/static/images/hero/imprint-diamond-family-memorial.jpg">'
    )
    row = {
        "slot_key": "cta-scene",
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


def test_home_series_slot_remaps_supabase_to_local_srcset():
    html = (
        '<picture><source type="image/webp" '
        'srcset="/static/images/hero/imprint-diamond-family-portrait-jewelry-800w.webp 800w">'
        '<img data-cms-slot="series-family" '
        'src="/static/images/hero/imprint-diamond-family-portrait-jewelry-800w.webp"></picture>'
    )
    row = {
        "slot_key": "series-family",
        "display_url": "https://xxx.supabase.co/storage/v1/object/public/cms/imprint-diamond-family-portrait-jewelry.jpg",
        "display_webp": "https://xxx.supabase.co/storage/v1/object/public/cms/imprint-diamond-family-portrait-jewelry.webp",
        "is_published": True,
    }
    out = apply_page_image_slots(html, "/", [row])
    assert "supabase.co" not in out
    assert "/static/images/hero/imprint-diamond-family-portrait-jewelry-800w.webp 800w" in out
    assert "/static/images/hero/imprint-diamond-family-portrait-jewelry-1200w.webp 1200w" in out


def test_home_dna_cta_prefers_local_webp():
    html = '<img data-cms-slot="dna-cta-diamond" src="/static/images/diamonds/colors/blue.webp">'
    row = {
        "slot_key": "dna-cta-diamond",
        "display_url": "https://xxx.supabase.co/storage/v1/object/public/cms/colors/blue.png",
        "display_webp": "",
        "is_published": True,
    }
    out = apply_page_image_slots(html, "/", [row])
    assert 'src="/static/images/diamonds/colors/blue.webp"' in out
    assert "supabase.co" not in out


def test_inventory_excludes_empty_calculator_and_jewelry_slots():
    rows = build_page_image_seed()
    counts = Counter(row["page_key"] for row in rows)
    by_slot = {row["slot_key"]: row for row in rows if row["page_key"] == "/what-is-dna-diamond.html"}
    assert len(rows) == 46
    assert len(counts) == 9
    assert counts["/about.html"] == 3
    assert counts["/what-is-dna-diamond.html"] == 14
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
    empty_slots = {"lab-photo", "usp-lab-photo"}
    assert all(row["default_image_url"] or row["slot_key"] in empty_slots for row in rows)
    assert all(not str(row["default_image_url"]).startswith("{{") for row in rows)


def test_payload_requires_valid_slot_key():
    fields, error = parse_page_image_payload({"pageKey": "/", "imageUrl": "/x.jpg"})
    assert fields is None
    assert error == "缺少 slot_key"
    fields, error = parse_page_image_payload(
        {"pageKey": "/", "slotKey": "cta-scene", "imageUrl": "/x.jpg"}
    )
    assert error is None
    assert fields and fields["slot_key"] == "cta-scene"


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
            elif "select page_key from page_images where" in query:
                pk, sk = params
                self._fetchone = {"page_key": pk} if (pk, sk) in self.rows else None
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
    cur.rows[("/about.html", "cinema")] = {"page_key": "/about.html", "slot_key": "cinema"}
    missing = fetch_missing_page_image_slots(cur)
    assert missing
    assert all(item["page_key"] != "/shop/calculator/" for item in missing)

    target = next(item for item in missing if item["page_key"] == "/about.html")
    created, error = create_page_image_from_registry(cur, target["page_key"], target["slot_key"])
    assert error is None
    assert created and created["slot_key"] == target["slot_key"]

    again, dup_error = create_page_image_from_registry(cur, target["page_key"], target["slot_key"])
    assert again is None
    assert dup_error == "此區塊已存在"


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
    out = apply_page_image_slots(html, "/what-is-dna-diamond.html", [row])
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
            {"page_key": "/what-is-dna-diamond.html", "slot_key": "intro"},
            {"page_key": "/what-is-dna-diamond.html", "slot_key": "process-sample"},
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
    assert web_controller._load_page_image("/what-is-dna-diamond.html")["slot_key"] == "intro"
    assert calls == ["/series/pet/", "/series/love/", "/what-is-dna-diamond.html"]
    web_controller.clear_page_image_cache()
