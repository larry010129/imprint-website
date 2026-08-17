"""Memorial diamond admin: color products + shape image slots."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_STUB_KEYS = (
    "app.image_urls",
    "app.chain_catalog",
    "app.pricing_overrides",
    "app.storage",
    "app.memorial_diamonds",
    "app.admin_products",
    "psycopg",
    "psycopg.types",
    "psycopg.types.json",
)


@pytest.fixture(autouse=True)
def _isolate_module_stubs():
    """Avoid leaking import stubs into other test files."""
    saved = {k: sys.modules[k] for k in list(sys.modules) if k in _STUB_KEYS or k == "app"}
    for key in list(sys.modules):
        if key in _STUB_KEYS or key == "app":
            del sys.modules[key]
    yield
    for key in list(sys.modules):
        if key in _STUB_KEYS or key == "app":
            del sys.modules[key]
    sys.modules.update(saved)


def _ensure_stub_pkg() -> types.ModuleType:
    pkg = sys.modules.get("app")
    if pkg is None or not getattr(pkg, "__path__", None):
        pkg = types.ModuleType("app")
        pkg.__path__ = [str(ROOT / "app")]  # type: ignore[attr-defined]
        sys.modules["app"] = pkg
    return pkg


def _load_module(mod_name: str, rel_path: str):
    """Load a module file with light stubs; keep package path for sibling imports."""
    _ensure_stub_pkg()
    full = f"app.{mod_name}" if not mod_name.startswith("app.") else mod_name
    path = ROOT / rel_path
    spec = importlib.util.spec_from_file_location(full, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[full] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_memorial():
    return _load_module("memorial_diamonds", "app/memorial_diamonds.py")


def _load_admin_products():
    # Minimal stubs so admin_products imports resolve without DB stack.
    img = types.ModuleType("app.image_urls")
    img._is_raster_url = lambda u: bool(u) and str(u).lower().endswith(
        (".jpg", ".jpeg", ".png", ".webp")
    )
    img.resolve_product_image_url = lambda x: x
    img.static_url_exists = lambda u: True
    sys.modules["app.image_urls"] = img

    chain = types.ModuleType("app.chain_catalog")
    chain.DEFAULT_NECKLACE_TYPE = "round"
    chain.VALID_NECKLACE_TYPES = {"round"}
    chain.necklace_type_length_weights = lambda *_a, **_k: {}
    sys.modules["app.chain_catalog"] = chain

    po = types.ModuleType("app.pricing_overrides")
    po.canonical_carat = lambda c: str(c).strip() if c else None
    sys.modules["app.pricing_overrides"] = po

    st = types.ModuleType("app.storage")
    st.delete_by_url = lambda *_a, **_k: False
    st.is_pending_product_object_key = lambda *_a, **_k: False
    st.is_supabase_storage_url = lambda *_a, **_k: False
    st.metal_color_from_slot = lambda s: (str(s).split("-")[0] if s else None)
    st.object_path_from_public_url = lambda *_a, **_k: None
    st.product_folder_from_object_key = lambda *_a, **_k: None
    st.product_folder_segment = lambda *_a, **_k: "folder"
    st.promote_pending_product_url = lambda url, *_a, **_k: url
    st.relocate_product_object_url = lambda url, *_a, **_k: url
    st.site_image_public_url = lambda *_a, **_k: None
    sys.modules["app.storage"] = st

    jsonb_mod = types.ModuleType("psycopg.types.json")

    class Jsonb:
        def __init__(self, value):
            self.value = value

    jsonb_mod.Jsonb = Jsonb
    sys.modules["psycopg"] = types.ModuleType("psycopg")
    sys.modules["psycopg.types"] = types.ModuleType("psycopg.types")
    sys.modules["psycopg.types.json"] = jsonb_mod

    _load_memorial()
    return _load_module("admin_products", "app/admin_products.py")


def test_diamond_products_are_four_colors_with_shape_images():
    md = _load_memorial()
    assert len(md.DIAMOND_COLOR_PRODUCTS) == 4
    keys = {p["styleKey"] for p in md.DIAMOND_COLOR_PRODUCTS}
    assert keys == {
        "diamond-white",
        "diamond-yellow",
        "diamond-blue",
        "diamond-pink",
    }
    names = {p["nameZh"] for p in md.DIAMOND_COLOR_PRODUCTS}
    assert names == {"白鑽", "黃鑽", "藍鑽", "粉鑽"}
    for product in md.DIAMOND_COLOR_PRODUCTS:
        color = product["defaultColor"]
        images = product["images"]
        assert set(images) == md.VALID_DIAMOND_SHAPES
        assert images["round"] == [md.matrix_shape_image_url("round", color)]
        assert "diamonds/matrix/" in images["round"][0]
        assert not md.is_legacy_lifestyle_image(images["round"][0])
    assert "diamond-first-love" in md.LEGACY_SERIES_STYLE_KEYS


def test_sync_keeps_custom_cut_slots():
    """Custom cuts (not in built-in list) must survive seed sync."""
    md = _load_memorial()

    class FakeCur:
        def __init__(self):
            self.images = [
                {
                    "id": 9,
                    "color": "old-mine",
                    "file_path": "/static/images/uploads/old-mine.png",
                    "sort_order": 0,
                },
            ]
            self._last = None

        def execute(self, sql, params=None):
            sql_l = " ".join(str(sql).lower().split())
            if sql_l.startswith("select id, color, file_path"):
                self._last = list(self.images)
            elif sql_l.startswith("delete from product_images"):
                self.images = [r for r in self.images if r["id"] != params[0]]
                self._last = None
            elif "group by color" in sql_l:
                by_color = {}
                for row in self.images:
                    color = str(row["color"]).lower()
                    by_color[color] = max(by_color.get(color, -1), int(row.get("sort_order", 0)))
                self._last = [
                    {"color": color, "max_sort": max_sort}
                    for color, max_sort in by_color.items()
                ]
            elif sql_l.startswith("insert into product_images"):
                product_id, color, url, sort_order = params
                self.images.append(
                    {
                        "id": len(self.images) + 10,
                        "product_id": product_id,
                        "color": color,
                        "file_path": url,
                        "sort_order": sort_order,
                    }
                )
                self._last = None
            else:
                self._last = None

        def fetchall(self):
            return self._last or []

    cur = FakeCur()
    md.sync_memorial_diamond_seed_images(cur, "pid-custom", "white")
    slots = {row["color"] for row in cur.images}
    assert "old-mine" in slots
    assert "asscher" in slots
    assert "round" in slots


def test_sync_replaces_legacy_slots_and_fills_shapes():
    md = _load_memorial()

    class FakeCur:
        def __init__(self):
            self.images = [
                {
                    "id": 1,
                    "color": "white",
                    "file_path": "/static/images/hero/imprint-diamond-pet-memorial-cat.jpg",
                    "sort_order": 0,
                },
                {
                    "id": 2,
                    "color": "yellow",
                    "file_path": "/static/images/diamonds/colors/yellow.png",
                    "sort_order": 1,
                },
            ]
            self._last = None
            self.executed = []

        def execute(self, sql, params=None):
            sql_l = " ".join(str(sql).lower().split())
            self.executed.append((sql_l, params))
            if sql_l.startswith("select id, color, file_path"):
                self._last = list(self.images)
            elif sql_l.startswith("delete from product_images"):
                self.images = [r for r in self.images if r["id"] != params[0]]
                self._last = None
            elif "group by color" in sql_l:
                by_color = {}
                for row in self.images:
                    color = str(row["color"]).lower()
                    by_color[color] = max(by_color.get(color, -1), int(row.get("sort_order", 0)))
                self._last = [
                    {"color": color, "max_sort": max_sort}
                    for color, max_sort in by_color.items()
                ]
            elif sql_l.startswith("insert into product_images"):
                product_id, color, url, sort_order = params
                self.images.append(
                    {
                        "id": len(self.images) + 10,
                        "product_id": product_id,
                        "color": color,
                        "file_path": url,
                        "sort_order": sort_order,
                    }
                )
                self._last = None
            else:
                self._last = None

        def fetchall(self):
            return self._last or []

    cur = FakeCur()
    inserted = md.sync_memorial_diamond_seed_images(cur, "pid-1", "pink")
    assert inserted == len(md.VALID_DIAMOND_SHAPES)
    slots = {row["color"] for row in cur.images}
    assert slots == md.VALID_DIAMOND_SHAPES
    paths = {row["file_path"] for row in cur.images}
    assert all("/matrix/" in p and "-pink.png" in p for p in paths)
    assert not any(md.is_legacy_lifestyle_image(p) for p in paths)
    assert not any(md.is_legacy_gem_color_image(p) for p in paths)


def test_retire_legacy_series_clears_style_key():
    md = _load_memorial()

    class FakeCur:
        def __init__(self):
            self.rowcount = 5
            self.params = None

        def execute(self, sql, params=None):
            self.params = params

    cur = FakeCur()
    assert md.retire_legacy_series_products(cur) == 5
    assert set(cur.params[0]) == md.LEGACY_SERIES_STYLE_KEYS


def test_ensure_backfills_style_key_on_matching_name():
    """Orphan diamond row (no style_key) links to diamond-{color} instead of duplicating."""
    md = _load_memorial()

    class FakeCur:
        def __init__(self):
            self.rows = {
                "orphan-white": {
                    "id": "orphan-white",
                    "category": "diamond",
                    "name_zh": "白鑽",
                    "default_color": "white",
                    "style_key": None,
                }
            }
            self.products = {}
            self.inserts = []
            self.rowcount = 0
            self._fetchone = None
            self._last = None

        def execute(self, sql, params=None):
            sql_l = " ".join(str(sql).lower().split())
            if "create table" in sql_l or "alter table" in sql_l or "create unique index" in sql_l:
                return
            if sql_l.startswith("update products") and "style_key = any" in sql_l:
                self.rowcount = 0
                return
            if sql_l.startswith("update products p") and "style_key = %s" in sql_l:
                key, color, name, _dup_key = params
                n = 0
                for pid, row in self.rows.items():
                    if (
                        row["category"] == "diamond"
                        and row["default_color"] == color
                        and row["name_zh"] == name
                        and row["style_key"] is None
                        and key not in self.products
                    ):
                        row["style_key"] = key
                        self.products[key] = pid
                        n += 1
                self.rowcount = n
                return
            if "select style_key from memorial_diamond_style_tombstones" in sql_l:
                self._last = []
                return
            if "select id from products" in sql_l and "category = 'diamond'" in sql_l:
                key = params[0]
                pid = self.products.get(key)
                self._fetchone = {"id": pid} if pid else None
                return
            if sql_l.startswith("insert into products"):
                key = params[-1]
                pid = f"new-{key}"
                self.products[key] = pid
                self.inserts.append(key)
                self._fetchone = {"id": pid}
                return
            if "select id, color, file_path" in sql_l or "group by color" in sql_l:
                self._last = []
                return
            if sql_l.startswith("insert into product_images"):
                return

        def fetchone(self):
            return self._fetchone

        def fetchall(self):
            return self._last or []

    cur = FakeCur()
    inserted = md.ensure_memorial_diamond_products(cur)
    assert inserted == 3
    assert cur.products["diamond-white"] == "orphan-white"
    assert set(cur.inserts) == {"diamond-yellow", "diamond-blue", "diamond-pink"}


def test_ensure_skips_tombstoned_style_keys():
    """Deleted color products must not reappear on admin list ensure."""
    md = _load_memorial()

    class FakeCur:
        def __init__(self):
            self.products = {}  # style_key -> id
            self.tombstones = {"diamond-pink"}
            self.inserts = []
            self._last = None
            self._fetchone = None

        def execute(self, sql, params=None):
            sql_l = " ".join(str(sql).lower().split())
            if "create table if not exists memorial_diamond_style_tombstones" in sql_l:
                self._last = None
                self._fetchone = None
            elif "alter table products add column" in sql_l or "create unique index" in sql_l:
                self._last = None
                self._fetchone = None
            elif sql_l.startswith("update products") and "style_key = any" in sql_l:
                self.rowcount = 0
                self._last = None
                self._fetchone = None
            elif sql_l.startswith("select style_key from memorial_diamond_style_tombstones"):
                self._last = [{"style_key": k} for k in sorted(self.tombstones)]
                self._fetchone = None
            elif sql_l.startswith("select id from products where style_key"):
                key = params[0]
                if key in self.products:
                    self._fetchone = {"id": self.products[key]}
                else:
                    self._fetchone = None
                self._last = None
            elif "select id from products" in sql_l and "category = 'diamond'" in sql_l:
                key = params[0]
                if key in self.products:
                    self._fetchone = {"id": self.products[key]}
                else:
                    self._fetchone = None
                self._last = None
            elif sql_l.startswith("update products p") and "style_key = %s" in sql_l:
                self._last = None
                self._fetchone = None
            elif sql_l.startswith("insert into products"):
                key = params[-1]
                pid = f"new-{key}"
                self.products[key] = pid
                self.inserts.append(key)
                self._fetchone = {"id": pid}
                self._last = None
            elif sql_l.startswith("insert into product_images") or "select id, color, file_path" in sql_l:
                self._last = []
                self._fetchone = None
            elif "group by color" in sql_l:
                self._last = []
                self._fetchone = None
            else:
                self._last = None
                self._fetchone = None

        def fetchone(self):
            return self._fetchone

        def fetchall(self):
            return self._last or []

    cur = FakeCur()
    # Seed white/yellow/blue as existing; pink tombstoned and missing.
    cur.products = {
        "diamond-white": "w1",
        "diamond-yellow": "y1",
        "diamond-blue": "b1",
    }
    inserted = md.ensure_memorial_diamond_products(cur)
    assert inserted == 0
    assert "diamond-pink" not in cur.products
    assert "diamond-pink" not in cur.inserts

    # Clearing tombstone allows seed on next ensure.
    cur.tombstones.clear()
    inserted = md.ensure_memorial_diamond_products(cur)
    assert inserted == 1
    assert "diamond-pink" in cur.products


def test_merge_skips_excluded_tombstone_without_db_row():
    md = _load_memorial()
    merged = md.merge_memorial_diamond_catalog(
        [
            {
                "id": "uuid-1",
                "styleKey": "diamond-white",
                "nameZh": "白鑽",
                "defaultColor": "white",
                "images": {},
                "draft": False,
            }
        ],
        excluded_style_keys={"diamond-pink", "diamond-blue"},
    )
    keys = {row["styleKey"] for row in merged}
    assert "diamond-white" in keys
    assert "diamond-yellow" in keys  # static fallback still OK
    assert "diamond-pink" not in keys
    assert "diamond-blue" not in keys


def test_merge_memorial_overlays_name_and_shape_images():
    md = _load_memorial()
    merged = md.merge_memorial_diamond_catalog(
        [
            {
                "id": "uuid-1",
                "styleKey": "diamond-white",
                "nameZh": "白鑽（編輯）",
                "nameEn": "White Diamond",
                "defaultColor": "white",
                "images": {
                    "round": ["/static/uploads/custom-round.jpg"],
                    "heart": ["/static/uploads/heart.jpg"],
                },
                "colors": ["white"],
                "carats": [],
                "draft": False,
            },
            {
                "id": "uuid-old",
                "styleKey": "diamond-first-love",
                "nameZh": "滿月鑽石",
                "draft": False,
            },
        ]
    )
    by_key = {row["styleKey"]: row for row in merged}
    assert set(by_key) == {
        "diamond-white",
        "diamond-yellow",
        "diamond-blue",
        "diamond-pink",
    }
    white = by_key["diamond-white"]
    assert white["id"] == "uuid-1"
    assert white["nameZh"] == "白鑽（編輯）"
    assert white["golds"] == []
    assert "0.3" in white["carats"]
    assert white["images"]["round"] == ["/static/uploads/custom-round.jpg"]
    assert white["images"]["heart"] == ["/static/uploads/heart.jpg"]
    assert white["images"]["oval"] == [md.matrix_shape_image_url("oval", "white")]
    assert by_key["diamond-pink"]["nameZh"] == "粉鑽"


def test_merge_strips_lifestyle_and_gem_swatch_thumbs():
    md = _load_memorial()
    merged = md.merge_memorial_diamond_catalog(
        [
            {
                "id": "uuid-y",
                "styleKey": "diamond-yellow",
                "nameZh": "黃鑽",
                "defaultColor": "yellow",
                "thumbUrl": "/static/images/hero/imprint-diamond-pet-memorial-cat.jpg",
                "images": {
                    "white": ["/static/images/diamonds/colors/yellow.png"],
                },
                "colors": ["yellow"],
                "draft": False,
            }
        ]
    )
    yellow = {row["styleKey"]: row for row in merged}["diamond-yellow"]
    assert yellow["images"]["round"] == [md.matrix_shape_image_url("round", "yellow")]
    assert yellow["thumbUrl"] == md.matrix_shape_image_url("round", "yellow")
    assert not md.is_legacy_lifestyle_image(yellow["thumbUrl"])


def test_validate_diamond_skips_variants_requires_shape_image():
    ap = _load_admin_products()

    cleaned, err = ap.validate_product_fields(
        {
            "category": "diamond",
            "nameZh": "白鑽",
            "nameEn": "White Diamond",
            "defaultColor": "white",
            "styleKey": "diamond-white",
            "isPublished": True,
            "variants": [{"gold": "18k", "carat": "0.3", "weightChin": 1}],
            "images": [],
        }
    )
    assert cleaned is None
    assert err and "商品照片" in err

    cleaned, err = ap.validate_product_fields(
        {
            "category": "diamond",
            "nameZh": "白鑽",
            "nameEn": "White Diamond",
            "defaultColor": "white",
            "styleKey": "diamond-white",
            "isPublished": True,
            "variants": [],
            "images": [
                {
                    "color": "round",
                    "url": "/static/images/diamonds/matrix/round-white.png",
                }
            ],
        }
    )
    assert err is None
    assert cleaned is not None
    assert cleaned["variants"] == []
    assert cleaned["styleKey"] == "diamond-white"
    assert cleaned["allowsEngraving"] is False
    assert cleaned["images"][0]["color"] == "round"


def test_validate_diamond_rejects_metal_default_and_color_image_slot():
    ap = _load_admin_products()

    cleaned, err = ap.validate_product_fields(
        {
            "category": "diamond",
            "nameZh": "白鑽",
            "nameEn": "White Diamond",
            "defaultColor": "rose",
            "styleKey": "diamond-white",
            "isPublished": False,
            "images": [],
        }
    )
    assert cleaned is None
    assert err and "預設顏色" in err

    cleaned, err = ap.validate_product_fields(
        {
            "category": "diamond",
            "nameZh": "白鑽",
            "nameEn": "White Diamond",
            "defaultColor": "white",
            "styleKey": "diamond-white",
            "isPublished": True,
            "images": [
                {
                    "color": "white",
                    "url": "/static/images/diamonds/matrix/round-white.png",
                }
            ],
        }
    )
    assert cleaned is None
    assert err and ("圖片" in err or "顏色" in err or "選項" in err)


def test_admin_html_cache_bust_v50():
    # Canonical CMS shell is admin1.html (served at /admin); keep legacy in sync.
    for name in ("admin1.html", "admin.html"):
        html = (ROOT / name).read_text(encoding="utf-8")
        assert "admin-products.js?v=65" in html
        assert "api-client.js?v=25" in html


def test_jewelry_validate_still_requires_variant():
    ap = _load_admin_products()

    cleaned, err = ap.validate_product_fields(
        {
            "category": "ring",
            "nameZh": "測試戒",
            "nameEn": "Test Ring",
            "defaultColor": "white",
            "isPublished": True,
            "variants": [],
            "images": [
                {
                    "color": "white-white",
                    "url": "/static/images/diamonds/colors/white.png",
                }
            ],
        }
    )
    assert cleaned is None
    assert err and "款式選項" in err
