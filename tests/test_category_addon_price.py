"""品項加價 (category addon_price_twd) — parse, labor replace, admin save wiring."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN_PRODUCTS_JS = ROOT / "public" / "js" / "admin-products.js"
API_CLIENT_JS = ROOT / "public" / "js" / "api-client.js"
ADMIN_HTML = ROOT / "admin1.html"


def _load_product_categories():
    """Load product_categories without importing full app package side effects."""
    if "app.image_urls" not in sys.modules:
        img = types.ModuleType("app.image_urls")
        img.resolve_product_image_url = lambda x: x
        sys.modules.setdefault("app", types.ModuleType("app"))
        sys.modules["app.image_urls"] = img
    path = ROOT / "app" / "product_categories.py"
    spec = importlib.util.spec_from_file_location("product_categories_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_parse_addon_price_accepts_non_negative_int():
    pc = _load_product_categories()
    assert pc.parse_addon_price(0) == (0, None)
    assert pc.parse_addon_price("1200") == (1200, None)
    assert pc.parse_addon_price(1200.0) == (1200, None)
    assert pc.parse_addon_price(-1)[1]
    assert pc.parse_addon_price("12.5")[1]


def test_fetch_categories_is_read_only_and_cached():
    pc = _load_product_categories()
    pc.clear_category_cache()

    class _ReadOnlyCur:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params=None):
            normalized = " ".join(sql.lower().split())
            self.calls.append(normalized)
            assert normalized.startswith("select ")
            self.rows = [
                {
                    "slug": "ring",
                    "label_zh": "ring",
                    "label_en": "Ring",
                    "thumb_path": None,
                    "sort_order": 0,
                    "addon_price_twd": 0,
                    "ring_size_config": None,
                    "created_at": None,
                    "updated_at": None,
                }
            ]

        def fetchall(self):
            return self.rows

    cur = _ReadOnlyCur()
    assert pc.fetch_categories(cur)[0]["slug"] == "ring"
    assert pc.fetch_categories(cur)[0]["slug"] == "ring"
    assert len(cur.calls) == 1


def test_labor_replace_formula_unchanged():
    from app.pricing import _labor_fee

    assert _labor_fee("pendant", "18k", 0) == 5000
    assert _labor_fee("pendant", "18k", 1200) == 1200
    assert _labor_fee("chain", "18k", 0) == 3000
    assert _labor_fee("chain", "s925", 0) == 500
    assert _labor_fee("chain", "s925", 800) == 800
    assert _labor_fee("earring", "18k", 2000) == 2000


def test_update_category_addon_writes_column():
    pc = _load_product_categories()

    class _Cur:
        def __init__(self):
            self.updated = None

        def execute(self, sql, params=None):
            sql_l = " ".join(sql.lower().split())
            if sql_l.startswith("create table") or sql_l.startswith("alter table"):
                return
            if sql_l.startswith("insert into product_categories"):
                return
            if "from product_categories order by" in sql_l or sql_l.startswith(
                "select slug, label_zh"
            ):
                self._rows = [
                    {
                        "slug": "pendant",
                        "label_zh": "項墜",
                        "label_en": "Pendant",
                        "thumb_path": None,
                        "sort_order": 0,
                        "addon_price_twd": 0,
                        "created_at": None,
                        "updated_at": None,
                    }
                ]
                return
            if sql_l.startswith("select addon_price_twd"):
                self._row = {"addon_price_twd": self.updated if self.updated is not None else 0}
                return
            if "update product_categories" in sql_l and "addon_price_twd" in sql_l:
                self.updated = params[0]
                self._row = {
                    "slug": "pendant",
                    "label_zh": "項墜",
                    "label_en": "Pendant",
                    "thumb_path": None,
                    "sort_order": 0,
                    "addon_price_twd": params[0],
                    "created_at": None,
                    "updated_at": params[1],
                }
                return
            if "select coalesce(max(sort_order)" in sql_l:
                self._row = {"next": 0}
                return
            self._row = None
            self._rows = []

        def fetchone(self):
            return getattr(self, "_row", None)

        def fetchall(self):
            return getattr(self, "_rows", [])

    cur = _Cur()
    # Bypass real ensure DDL; keep slug valid via fetch path above.
    pc.ensure_product_categories_schema = lambda _c: None
    cat, err = pc.update_category_addon(cur, "pendant", 4500)
    assert err is None
    assert cat is not None
    assert cat["addonPrice"] == 4500
    assert cat["addon_price_twd"] == 4500
    assert cur.updated == 4500


def test_overwrite_variant_addons_updates_all_rows():
    pc = _load_product_categories()

    class _Cur:
        def __init__(self):
            self.calls = []
            self.rowcount = 0
            self.updated = None

        def execute(self, sql, params=None):
            sql_l = " ".join(sql.lower().split())
            self.calls.append((sql_l, params))
            if sql_l.startswith("create table") or sql_l.startswith("alter table"):
                return
            if sql_l.startswith("insert into product_categories"):
                return
            if "from product_categories order by" in sql_l or sql_l.startswith(
                "select slug, label_zh"
            ):
                self._rows = [
                    {
                        "slug": "ring",
                        "label_zh": "戒指",
                        "label_en": "Ring",
                        "thumb_path": None,
                        "sort_order": 1,
                        "addon_price_twd": 0,
                        "created_at": None,
                        "updated_at": None,
                    }
                ]
                return
            if "update product_categories" in sql_l and "addon_price_twd" in sql_l:
                self.updated = params[0]
                self._row = {
                    "slug": "ring",
                    "label_zh": "戒指",
                    "label_en": "Ring",
                    "thumb_path": None,
                    "sort_order": 1,
                    "addon_price_twd": params[0],
                    "created_at": None,
                    "updated_at": params[1],
                }
                return
            if "update product_variants" in sql_l and "addon_price_twd" in sql_l:
                assert params == (3500, "ring")
                assert "select id from products where category" in sql_l
                self.rowcount = 3
                return
            self._row = None
            self._rows = []

        def fetchone(self):
            return getattr(self, "_row", None)

        def fetchall(self):
            return getattr(self, "_rows", [])

    cur = _Cur()
    pc.ensure_product_categories_schema = lambda _c: None
    cat, count, err = pc.force_overwrite_category_addon(cur, "ring", 3500)
    assert err is None
    assert cat is not None
    assert cat["addonPrice"] == 3500
    assert count == 3
    assert any("update product_variants" in sql for sql, _ in cur.calls)


def test_admin_js_wires_patch_and_surfaces_errors():
    src = ADMIN_PRODUCTS_JS.read_text(encoding="utf-8")
    assert "updateProductCategory" in src
    assert "addonPrice" in src
    assert "function saveCategoryAddon" in src
    assert "apCategoryAddonSave" in src
    assert "apCategoryAddonForce" in src
    assert "function forceOverwriteCategoryAddon" in src
    assert "forceProductCategoryAddon" in src
    assert "確定要以目前品項加價覆蓋此品項下所有款式列？" in src
    assert "強制覆蓋" in src
    assert "setCategoryAddonStatus" in src
    assert "請強制重新整理頁面" in src
    assert ".catch(function" in src
    api = API_CLIENT_JS.read_text(encoding="utf-8")
    assert "updateProductCategory: function" in api
    assert "forceProductCategoryAddon: function" in api
    assert "/force-addon" in api
    assert "/api/admin/product-category/" in api
    assert "method: 'PATCH'" in api
    html = ADMIN_HTML.read_text(encoding="utf-8")
    assert "api-client.js?v=24" in html
    assert "admin-products.js?v=61" in html


def test_default_categories_memorial_diamond_first():
    pc = _load_product_categories()
    slugs = [row["slug"] for row in pc.DEFAULT_CATEGORIES]
    assert slugs[0] == "diamond"
    assert pc.DEFAULT_CATEGORIES[0]["label_zh"] == "紀念鑽石"
    assert slugs == [
        "diamond",
        "pendant",
        "ring",
        "earring",
        "bracelet",
        "chain",
    ]
    assert [row["sort_order"] for row in pc.DEFAULT_CATEGORIES] == list(range(6))


def test_admin_js_category_order_diamond_first():
    src = ADMIN_PRODUCTS_JS.read_text(encoding="utf-8")
    assert (
        "var CATEGORY_ORDER = ['diamond', 'pendant', 'ring', 'earring', 'bracelet', 'chain'];"
        in src
    )
    assert "activeTab: 'cat-diamond'" in src
    html = ADMIN_HTML.read_text(encoding="utf-8")
    assert "admin-products.js?v=61" in html
