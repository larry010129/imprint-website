"""Ring size config — category policy, product legacy, catalog, step quote."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

from app.admin_products import validate_product_fields
from app.catalog import build_catalog_product, build_catalog_response
from app.pricing import compute_order_pricing, ring_size_addon_from_config

ROOT = Path(__file__).resolve().parents[1]
ADMIN_PRODUCTS_JS = ROOT / "public" / "js" / "admin-products.js"


def _load_product_categories():
    if "app.image_urls" not in sys.modules:
        img = types.ModuleType("app.image_urls")
        img.resolve_product_image_url = lambda x: x
        sys.modules.setdefault("app", types.ModuleType("app"))
        sys.modules["app.image_urls"] = img
    path = ROOT / "app" / "product_categories.py"
    spec = importlib.util.spec_from_file_location("product_categories_ring_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _ring_body(**overrides):
    body = {
        "category": "ring",
        "nameZh": "測試戒指",
        "nameEn": "Test Ring",
        "defaultColor": "white",
        "isPublished": False,
        "variants": [
            {
                "gold": "18k",
                "carat": "0.3",
                "weightChin": 0.02,
                "addonPriceTwd": 3500,
            }
        ],
        "images": [],
        "ringSizeConfig": {
            "minSize": 7,
            "maxSize": 14,
            "pricePerSizeTwd": 100,
        },
    }
    body.update(overrides)
    return body


def test_validate_keeps_ring_size_config():
    cleaned, err = validate_product_fields(_ring_body())
    assert err is None
    cfg = cleaned["ringSizeConfig"]
    assert cfg["minSize"] == 7
    assert cfg["maxSize"] == 14
    assert cfg["pricePerSizeTwd"] == 100.0
    assert cfg["startSize"] == 7


def test_validate_clears_ring_size_for_non_ring():
    body = _ring_body(category="pendant")
    cleaned, err = validate_product_fields(body)
    assert err is None
    assert cleaned["ringSizeConfig"] is None


def test_validate_rejects_bad_min_size():
    cleaned, err = validate_product_fields(
        _ring_body(ringSizeConfig={"minSize": 3, "maxSize": 14, "pricePerSizeTwd": 100})
    )
    assert cleaned is None
    assert "最小戒圍" in (err or "")


def test_validate_rejects_min_greater_than_max():
    cleaned, err = validate_product_fields(
        _ring_body(ringSizeConfig={"minSize": 12, "maxSize": 8, "pricePerSizeTwd": 100})
    )
    assert cleaned is None
    assert "最小戒圍不可大於最大戒圍" in (err or "")


def test_validate_rejects_negative_price_per_size():
    cleaned, err = validate_product_fields(
        _ring_body(ringSizeConfig={"minSize": 7, "maxSize": 14, "pricePerSizeTwd": -1})
    )
    assert cleaned is None
    assert "每圍加價" in (err or "")


def test_validate_accepts_start_size_alias():
    cleaned, err = validate_product_fields(
        _ring_body(
            ringSizeConfig={"startSize": 8, "maxSize": 16, "pricePerSizeTwd": 50}
        )
    )
    assert err is None
    assert cleaned["ringSizeConfig"]["minSize"] == 8
    assert cleaned["ringSizeConfig"]["startSize"] == 8


def test_validate_defaults_max_when_omitted():
    cleaned, err = validate_product_fields(
        _ring_body(ringSizeConfig={"minSize": 7, "pricePerSizeTwd": 100})
    )
    assert err is None
    assert cleaned["ringSizeConfig"]["maxSize"] == 18


def test_ring_size_addon_step_formula():
    cfg = {"minSize": 7, "maxSize": 14, "pricePerSizeTwd": 100}
    assert ring_size_addon_from_config(cfg, 10) == 300
    assert ring_size_addon_from_config(cfg, 7) == 0
    assert ring_size_addon_from_config(cfg, 6) == 0
    assert ring_size_addon_from_config(None, 12) == 0


def test_ring_size_addon_legacy_sizes_lookup():
    cfg = {
        "startSize": 7,
        "sizes": [
            {"size": 7, "addonPriceTwd": 0},
            {"size": 12, "addonPriceTwd": 800},
        ],
    }
    assert ring_size_addon_from_config(cfg, 12) == 800
    assert ring_size_addon_from_config(cfg, 7) == 0
    assert ring_size_addon_from_config(cfg, 10) == 0


def _ring_product(**overrides):
    product = {
        "id": "p1",
        "category": "ring",
        "name_zh": "戒指",
        "name_en": "Ring",
        "description_zh": "",
        "description_en": "",
        "default_color": "white",
        "is_published": True,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
        "sort_order": 0,
        "chain_type": None,
        "length_weights": None,
        "ring_size_config": {
            "minSize": 8,
            "maxSize": 15,
            "pricePerSizeTwd": 200,
        },
    }
    product.update(overrides)
    return product


def _ring_variants():
    return [
        {
            "gold": "18k",
            "carat": "0.3",
            "weight_chin": 0.02,
            "manual_price_twd": None,
            "side_stone_price_twd": None,
            "side_stone_carat": None,
            "side_stone_total_twd": None,
            "addon_price_twd": 3500,
        }
    ]


def test_catalog_exposes_ring_size_config():
    out = build_catalog_product(_ring_product(), _ring_variants(), [])
    assert out["ringSizeConfig"]["minSize"] == 8
    assert out["ringSizeConfig"]["maxSize"] == 15
    assert out["ringSizeConfig"]["pricePerSizeTwd"] == 200.0
    assert out["ringSizeConfig"]["startSize"] == 8


def test_catalog_prefers_category_ring_size_config():
    product = _ring_product(
        ring_size_config={"minSize": 8, "maxSize": 15, "pricePerSizeTwd": 200}
    )
    out = build_catalog_product(
        product,
        _ring_variants(),
        [],
        category_ring_size_config={
            "minSize": 7,
            "maxSize": 14,
            "pricePerSizeTwd": 100,
        },
    )
    assert out["ringSizeConfig"]["minSize"] == 7
    assert out["ringSizeConfig"]["pricePerSizeTwd"] == 100.0


def test_catalog_response_injects_category_ring_config():
    product = _ring_product(
        ring_size_config={"minSize": 9, "maxSize": 16, "pricePerSizeTwd": 50}
    )
    payload = build_catalog_response(
        [product],
        {product["id"]: _ring_variants()},
        {product["id"]: []},
        category_order=["ring"],
        category_meta={
            "ring": {
                "labelZh": "戒指",
                "addonPrice": 0,
                "ringSizeConfig": {
                    "minSize": 6,
                    "maxSize": 18,
                    "pricePerSizeTwd": 150,
                },
            }
        },
        detail="full",
    )
    cfg = payload["categories"]["ring"][0]["ringSizeConfig"]
    assert cfg["minSize"] == 6
    assert cfg["pricePerSizeTwd"] == 150.0


def test_parse_category_ring_size_config():
    pc = _load_product_categories()
    ok, err = pc.parse_ring_size_config(
        {"minSize": 7, "maxSize": 14, "pricePerSizeTwd": 100}
    )
    assert err is None
    assert ok["minSize"] == 7
    assert ok["startSize"] == 7
    bad, err2 = pc.parse_ring_size_config({"minSize": 12, "maxSize": 8, "pricePerSizeTwd": 1})
    assert bad is None
    assert "最小戒圍不可大於最大戒圍" in (err2 or "")


def test_update_category_ring_size_writes_json():
    pc = _load_product_categories()

    class _Cur:
        def __init__(self):
            self.saved = None

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
                        "slug": "ring",
                        "label_zh": "戒指",
                        "label_en": "Ring",
                        "thumb_path": None,
                        "sort_order": 2,
                        "addon_price_twd": 0,
                        "ring_size_config": None,
                        "created_at": None,
                        "updated_at": None,
                    }
                ]
                return
            if "update product_categories" in sql_l and "ring_size_config" in sql_l:
                self.saved = params[0]
                payload = None
                if params[0] is not None:
                    payload = getattr(params[0], "obj", params[0])
                self._row = {
                    "slug": "ring",
                    "label_zh": "戒指",
                    "label_en": "Ring",
                    "thumb_path": None,
                    "sort_order": 2,
                    "addon_price_twd": 0,
                    "ring_size_config": payload,
                    "created_at": None,
                    "updated_at": params[1],
                }
                return
            self._row = None
            self._rows = []

        def fetchone(self):
            return getattr(self, "_row", None)

        def fetchall(self):
            return getattr(self, "_rows", [])

    cur = _Cur()
    pc.ensure_product_categories_schema = lambda _c: None
    cat, err = pc.update_category_ring_size(
        cur, "ring", {"minSize": 7, "maxSize": 14, "pricePerSizeTwd": 100}
    )
    assert err is None
    assert cat is not None
    assert cat["ringSizeConfig"]["minSize"] == 7
    assert cat["ringSizeConfig"]["pricePerSizeTwd"] == 100.0
    assert cur.saved is not None


def test_admin_list_hosts_ring_size_not_editor():
    src = ADMIN_PRODUCTS_JS.read_text(encoding="utf-8")
    assert "categoryRingSizeSectionHtml" in src
    assert "apCategoryRingSizeSave" in src
    assert "function ringSizeSectionHtml" not in src
    assert "ringSizeConfig: collectRingSizeConfig" not in src
    # List page hosts section below product table; product form does not.
    assert "categoryRingSizeSectionHtml(cat)" in src
    shell_start = src.index("function renderShell")
    shell_end = src.index("function toProductTableRow")
    shell = src[shell_start:shell_end]
    assert "apProductsTableRoot" in shell
    assert "categoryRingSizeSectionHtml" in shell
    assert shell.index("apProductsTableRoot") < shell.index("categoryRingSizeSectionHtml")
    assert "refreshRingSizeSection" in src


def test_catalog_exposes_legacy_sizes():
    product = {
        "id": "p1",
        "category": "ring",
        "name_zh": "戒指",
        "name_en": "Ring",
        "description_zh": "",
        "description_en": "",
        "default_color": "white",
        "is_published": True,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
        "sort_order": 0,
        "chain_type": None,
        "length_weights": None,
        "ring_size_config": {
            "startSize": 8,
            "sizes": [{"size": 14, "addonPriceTwd": 500}],
        },
    }
    variants = [
        {
            "gold": "18k",
            "carat": "0.3",
            "weight_chin": 0.02,
            "manual_price_twd": None,
            "side_stone_price_twd": None,
            "side_stone_carat": None,
            "side_stone_total_twd": None,
            "addon_price_twd": 3500,
        }
    ]
    out = build_catalog_product(product, variants, [])
    assert out["ringSizeConfig"]["startSize"] == 8
    assert out["ringSizeConfig"]["sizes"][0]["addonPriceTwd"] == 500.0


def test_quote_stacks_ring_size_addon_on_labor(monkeypatch):
    variant = {
        "weight_chin": 0.01,
        "manual_price_twd": None,
        "side_stone_price_twd": None,
        "side_stone_carat": None,
        "side_stone_total_twd": None,
        "addon_price_twd": 3500,
    }
    monkeypatch.setattr(
        "app.pricing._lookup_weight",
        lambda *a, **k: (variant, 0.01),
    )
    monkeypatch.setattr(
        "app.pricing.get_metal_prices",
        lambda cur: {"XAU": 1.0, "XPT": 1.0, "XAG": 1.0},
    )
    monkeypatch.setattr("app.pricing.load_overrides", lambda cur: {})
    monkeypatch.setattr("app.pricing.category_addon_price", lambda cur, cat: 2000)
    monkeypatch.setattr(
        "app.pricing.compute_diamond_list_price",
        lambda *a, **k: 10000,
    )
    monkeypatch.setattr(
        "app.pricing._product_ring_size_config",
        lambda *a, **k: {
            "minSize": 7,
            "maxSize": 14,
            "pricePerSizeTwd": 100,
        },
    )
    quote = compute_order_pricing(
        MagicMock(),
        {
            "category": "ring",
            "type": "r1",
            "gold": "18k",
            "carat": "0.3",
            "ringSize": 10,
        },
    )
    assert quote["ready"] is True
    # Variant labor 3500 + ring size (10-7)*100 = 300.
    assert quote["laborPrice"] == 3800
    assert quote["ringSizePrice"] == 300


def test_quote_ring_size_at_min_is_zero(monkeypatch):
    variant = {
        "weight_chin": 0.01,
        "manual_price_twd": None,
        "side_stone_price_twd": None,
        "side_stone_carat": None,
        "side_stone_total_twd": None,
        "addon_price_twd": 3500,
    }
    monkeypatch.setattr(
        "app.pricing._lookup_weight",
        lambda *a, **k: (variant, 0.01),
    )
    monkeypatch.setattr(
        "app.pricing.get_metal_prices",
        lambda cur: {"XAU": 1.0, "XPT": 1.0, "XAG": 1.0},
    )
    monkeypatch.setattr("app.pricing.load_overrides", lambda cur: {})
    monkeypatch.setattr("app.pricing.category_addon_price", lambda cur, cat: 2000)
    monkeypatch.setattr(
        "app.pricing.compute_diamond_list_price",
        lambda *a, **k: 10000,
    )
    monkeypatch.setattr(
        "app.pricing._product_ring_size_config",
        lambda *a, **k: {
            "minSize": 7,
            "maxSize": 14,
            "pricePerSizeTwd": 100,
        },
    )
    quote = compute_order_pricing(
        MagicMock(),
        {
            "category": "ring",
            "type": "r1",
            "gold": "18k",
            "carat": "0.3",
            "ringSize": 7,
        },
    )
    assert quote["ready"] is True
    assert quote["laborPrice"] == 3500
    assert quote["ringSizePrice"] is None


def test_quote_legacy_sizes_still_works(monkeypatch):
    variant = {
        "weight_chin": 0.01,
        "manual_price_twd": None,
        "side_stone_price_twd": None,
        "side_stone_carat": None,
        "side_stone_total_twd": None,
        "addon_price_twd": 3500,
    }
    monkeypatch.setattr(
        "app.pricing._lookup_weight",
        lambda *a, **k: (variant, 0.01),
    )
    monkeypatch.setattr(
        "app.pricing.get_metal_prices",
        lambda cur: {"XAU": 1.0, "XPT": 1.0, "XAG": 1.0},
    )
    monkeypatch.setattr("app.pricing.load_overrides", lambda cur: {})
    monkeypatch.setattr("app.pricing.category_addon_price", lambda cur, cat: 2000)
    monkeypatch.setattr(
        "app.pricing.compute_diamond_list_price",
        lambda *a, **k: 10000,
    )
    monkeypatch.setattr(
        "app.pricing._product_ring_size_config",
        lambda *a, **k: {
            "startSize": 7,
            "sizes": [{"size": 12, "addonPriceTwd": 800}],
        },
    )
    quote = compute_order_pricing(
        MagicMock(),
        {
            "category": "ring",
            "type": "r1",
            "gold": "18k",
            "carat": "0.3",
            "ringSize": 12,
        },
    )
    assert quote["ready"] is True
    assert quote["laborPrice"] == 4300
    assert quote["ringSizePrice"] == 800
