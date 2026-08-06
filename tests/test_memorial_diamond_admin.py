"""Memorial diamond admin shapes: name + image + color, no metal/price."""

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


def test_merge_memorial_overlays_name_and_images():
    md = _load_memorial()
    merged = md.merge_memorial_diamond_catalog(
        [
            {
                "id": "uuid-1",
                "styleKey": "diamond-first-love",
                "nameZh": "滿月鑽石（編輯）",
                "nameEn": "First Love Diamond",
                "defaultColor": "white",
                "images": {
                    "white": ["/static/uploads/custom-moon.jpg"],
                    "pink": ["/static/uploads/pink.jpg"],
                },
                "colors": ["white", "pink"],
                "carats": [],
                "draft": False,
            }
        ]
    )
    by_key = {row["styleKey"]: row for row in merged}
    assert set(by_key) >= {
        "diamond-first-love",
        "diamond-pet",
        "diamond-love",
        "diamond-family",
        "diamond-heirloom",
    }
    moon = by_key["diamond-first-love"]
    assert moon["id"] == "uuid-1"
    assert moon["nameZh"] == "滿月鑽石（編輯）"
    assert moon["golds"] == []
    assert "0.3" in moon["carats"]
    assert moon["images"]["white"] == ["/static/uploads/custom-moon.jpg"]
    assert moon["images"]["pink"] == ["/static/uploads/pink.jpg"]
    assert by_key["diamond-pet"]["nameZh"] == "寵物鑽石"


def test_validate_diamond_skips_variants_requires_image():
    ap = _load_admin_products()

    cleaned, err = ap.validate_product_fields(
        {
            "category": "diamond",
            "nameZh": "滿月鑽石",
            "nameEn": "First Love Diamond",
            "defaultColor": "white",
            "styleKey": "diamond-first-love",
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
            "nameZh": "滿月鑽石",
            "nameEn": "First Love Diamond",
            "defaultColor": "white",
            "styleKey": "diamond-first-love",
            "isPublished": True,
            "variants": [],
            "images": [
                {
                    "color": "white",
                    "url": "/static/images/hero/imprint-diamond-newborn-baby-necklace.jpg",
                }
            ],
        }
    )
    assert err is None
    assert cleaned is not None
    assert cleaned["variants"] == []
    assert cleaned["styleKey"] == "diamond-first-love"
    assert cleaned["allowsEngraving"] is False
    assert cleaned["images"][0]["color"] == "white"


def test_validate_diamond_rejects_metal_default_and_metal_image_slot():
    ap = _load_admin_products()

    cleaned, err = ap.validate_product_fields(
        {
            "category": "diamond",
            "nameZh": "滿月鑽石",
            "nameEn": "First Love Diamond",
            "defaultColor": "rose",
            "styleKey": "diamond-first-love",
            "isPublished": False,
            "images": [],
        }
    )
    assert cleaned is None
    assert err and "預設顏色" in err

    cleaned, err = ap.validate_product_fields(
        {
            "category": "diamond",
            "nameZh": "滿月鑽石",
            "nameEn": "First Love Diamond",
            "defaultColor": "white",
            "styleKey": "diamond-first-love",
            "isPublished": True,
            "images": [
                {
                    "color": "white-yellow",
                    "url": "/static/images/hero/imprint-diamond-newborn-baby-necklace.jpg",
                }
            ],
        }
    )
    assert cleaned is None
    assert err and ("圖片" in err or "顏色" in err or "選項" in err)


def test_admin_html_cache_bust_v46():
    for name in ("admin.html", "admin1.html"):
        html = (ROOT / name).read_text(encoding="utf-8")
        assert "admin-products.js?v=46" in html


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
                    "url": "/static/images/hero/imprint-diamond-newborn-baby-necklace.jpg",
                }
            ],
        }
    )
    assert cleaned is None
    assert err and "款式選項" in err
