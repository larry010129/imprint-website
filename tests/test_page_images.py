from collections import Counter
from unittest.mock import MagicMock

import pytest

from app.content import (
    apply_page_image_replace_stack,
    delete_page_image_urls_if_unreferenced,
    effective_page_image_url,
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
    assert 'src="/static/images/diamonds/colors/blue-320.webp"' in out
    assert "supabase.co" not in out


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
    assert PAGE_IMAGE_STORAGE_FOLDERS["/what-is-dna-diamond"] == "dna-diamond"
    assert page_image_storage_folder(None) == "_pending"
    assert page_image_storage_folder("/series/pet") == "pet-diamond"


def test_inventory_excludes_empty_calculator_and_jewelry_slots():
    rows = build_page_image_seed()
    counts = Counter(row["page_key"] for row in rows)
    by_slot = {row["slot_key"]: row for row in rows if row["page_key"] == "/what-is-dna-diamond"}
    assert len(rows) == 45
    assert len(counts) == 10
    assert counts["/journal"] == 1
    assert counts["/about"] == 3
    assert counts["/what-is-dna-diamond"] == 14
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
