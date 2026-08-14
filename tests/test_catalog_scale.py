"""List/detail catalog split — lite payload, full detail, product endpoint."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import load_dotenv

from app.catalog import (
    _first_thumb_url,
    build_catalog_product,
    build_catalog_product_lite,
    build_catalog_response,
    normalize_catalog_detail,
)

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")

SUPABASE_PRODUCT = (
    "https://abc123.supabase.co/storage/v1/object/public/shop-media/products/x.webp"
)


def _product_row(product_id="prod-scale-1", category="ring", published=True):
    return {
        "id": product_id,
        "category": category,
        "name_zh": "測試戒",
        "name_en": "Test Ring",
        "description_zh": "說明",
        "description_en": "Desc",
        "default_color": "white",
        "sort_order": 0,
        "is_published": published,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }


def _variants():
    return [
        {"gold": "14k", "carat": "0.3", "weight_chin": 1.2},
        {"gold": "18k", "carat": "0.5", "weight_chin": 1.4},
    ]


def _images():
    return [{"color": "white-white", "file_path": SUPABASE_PRODUCT}]


def test_normalize_catalog_detail_defaults_lite():
    assert normalize_catalog_detail(None) == "lite"
    assert normalize_catalog_detail("") == "lite"
    assert normalize_catalog_detail("LITE") == "lite"
    assert normalize_catalog_detail("full") == "full"
    assert normalize_catalog_detail("FULL") == "full"


def test_lite_thumb_url_prefers_default_color_over_block_order():
    fancy = "https://abc123.supabase.co/storage/v1/object/public/shop-media/products/fancy.webp"
    rose = "https://abc123.supabase.co/storage/v1/object/public/shop-media/products/rose.webp"
    images = [
        {"color": "yellow-pink", "file_path": fancy},
        {"color": "rose", "file_path": rose},
        {"color": "white-white", "file_path": SUPABASE_PRODUCT},
    ]
    entry = build_catalog_product_lite(_product_row(), _variants(), images)
    assert entry["thumbUrl"] == SUPABASE_PRODUCT
    assert entry["imageSlotOrder"] == ["yellow-pink", "rose", "white-white"]


def test_build_catalog_product_lite_omits_heavy_maps():
    entry = build_catalog_product_lite(_product_row(), _variants(), _images())

    assert entry["id"] == "prod-scale-1"
    assert entry["nameZh"] == "測試戒"
    assert entry["golds"] == ["14k", "18k"]
    assert entry["carats"] == ["0.3", "0.5"]
    assert "white-white" in entry["colors"]
    assert entry["thumbUrl"] == SUPABASE_PRODUCT
    assert "weights" not in entry
    assert "images" not in entry
    assert "manualPrices" not in entry
    assert "lengthWeights" not in entry
    assert entry["allowsEngraving"] is True
    assert entry["draft"] is False


def test_catalog_image_slot_order_follows_admin_block_save_order():
    from app.catalog import _image_slot_order

    images = [
        {"color": "rose-white", "file_path": "https://cdn.example/rose.png"},
        {"color": "white-white", "file_path": "https://cdn.example/white.png"},
        {"color": "white-yellow", "file_path": "https://cdn.example/yellow.png"},
    ]
    assert _image_slot_order(images) == ["rose-white", "white-white", "white-yellow"]

    fancy = "https://cdn.example/fancy-pink.webp"
    white = "https://cdn.example/white-white.webp"
    images_by_color = {
        "yellow-pink": [fancy],
        "white-white": [white],
    }
    rows = [
        {"color": "yellow-pink", "file_path": fancy},
        {"color": "white-white", "file_path": white},
    ]
    assert _first_thumb_url(images_by_color, images=rows, default_color="white") == white
    assert _first_thumb_url(images_by_color, images=rows) == white


def test_lite_thumb_default_metal_before_block_order():
    fancy = "https://cdn.example/rose-yellow.webp"
    white = "https://cdn.example/rose-white.webp"
    images = [
        {"color": "rose-yellow", "file_path": fancy},
        {"color": "rose-white", "file_path": white},
    ]
    product = {**_product_row(), "default_color": "rose"}
    entry = build_catalog_product_lite(product, _variants(), images)
    assert entry["thumbUrl"] == white
    assert entry["imageSlotOrder"] == ["rose-yellow", "rose-white"]


def test_lite_thumb_skips_pending_default_color_falls_through_block_order():
    """泡泡手鍊 pattern: 預設顏色=white pending → next slot in block order."""
    pending = "https://x.supabase.co/storage/v1/object/public/shop-media/products/_pending/x.png"
    yellow = "https://x.supabase.co/storage/v1/object/public/shop-media/products/yellow.png"
    images = [
        {"color": "white-white", "file_path": pending},
        {"color": "yellow-white", "file_path": yellow},
    ]
    product = {**_product_row(category="bracelet"), "name_zh": "泡泡手鍊", "default_color": "white"}
    entry = build_catalog_product_lite(product, _variants(), images)
    assert entry["thumbUrl"] == yellow


def test_lite_thumb_uses_realistic_supabase_storage_url():
    """Step-2 thumb must keep admin Storage URL (not letter invent / SVG seed)."""
    url = (
        "https://erobemoojyptyxvnyvuf.supabase.co/storage/v1/object/public/"
        "shop-media/products/gabriel-cross-pendant/white/c8d5658258e245d4aa3145b52aeb70ce.png"
    )
    images = [
        {"color": "white-white", "file_path": url},
        {"color": "yellow-pink", "file_path": "https://cdn.example/wrong-fancy.webp"},
    ]
    entry = build_catalog_product_lite(
        {**_product_row(category="pendant"), "sort_order": 0},
        _variants(),
        images,
    )
    assert entry["thumbUrl"] == url
    assert entry["styleKey"] is None


def test_build_catalog_product_full_keeps_previous_shape():
    entry = build_catalog_product(_product_row(), _variants(), _images())

    assert entry["weights"]["14k"]["0.3"] == 1.2
    assert SUPABASE_PRODUCT in entry["images"]["white-white"]
    assert entry["descriptionZh"] == "說明"
    assert "manualPrices" in entry
    assert "lengthWeights" in entry


def test_build_catalog_response_detail_modes():
    products = [_product_row()]
    variants = {products[0]["id"]: _variants()}
    images = {products[0]["id"]: _images()}

    lite = build_catalog_response(products, variants, images, detail="lite")
    full = build_catalog_response(products, variants, images, detail="full")

    lite_prod = lite["categories"]["ring"][0]
    full_prod = full["categories"]["ring"][0]

    assert "weights" not in lite_prod
    assert lite_prod["thumbUrl"] == SUPABASE_PRODUCT
    assert full_prod["weights"]["18k"]["0.5"] == 1.4
    assert "thumbUrl" not in full_prod


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def test_api_catalog_default_is_lite(client):
    resp = client.get("/api/catalog")
    assert resp.status_code == 200
    assert "public, max-age=60" in (resp.headers.get("Cache-Control") or "")
    data = resp.json()
    assert "categories" in data
    assert "page" in data and "page_size" in data and "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 20
    for products in (data.get("categories") or {}).values():
        for product in products:
            # Memorial diamond merge keeps style payloads (weights/images).
            style_key = str(product.get("styleKey") or "")
            if product.get("category") == "diamond" or style_key.startswith("diamond-"):
                continue
            assert "weights" not in product
            assert "images" not in product
            assert "golds" in product
            assert "carats" in product
            assert "thumbUrl" in product


def test_api_catalog_category_paging(client):
    listing = client.get("/api/catalog", params={"page": 1, "page_size": 1})
    assert listing.status_code == 200
    body = listing.json()
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert isinstance(body["total"], int)

    # Pick a jewelry category that has products (skip diamond-only).
    jewelry_cat = next(
        (
            cat
            for cat, products in (body.get("categories") or {}).items()
            if cat != "diamond" and (products or cat in (body.get("categories") or {}))
        ),
        None,
    )
    # Prefer a category with a nonempty list or seeded empty key from available slugs.
    for cat in body.get("categoryOrder") or []:
        if cat == "diamond":
            continue
        jewelry_cat = cat
        break
    if not jewelry_cat:
        pytest.skip("no jewelry categories in DB")

    page1 = client.get(
        "/api/catalog",
        params={"category": jewelry_cat, "page": 1, "page_size": 1},
    )
    assert page1.status_code == 200
    p1 = page1.json()
    assert p1["page"] == 1
    assert p1["page_size"] == 1
    products = p1.get("categories", {}).get(jewelry_cat) or []
    assert len(products) <= 1
    if p1["total"] > 1:
        page2 = client.get(
            "/api/catalog",
            params={"category": jewelry_cat, "page": 2, "page_size": 1},
        )
        assert page2.status_code == 200
        p2 = page2.json()
        ids1 = {p["id"] for p in products}
        ids2 = {p["id"] for p in (p2.get("categories", {}).get(jewelry_cat) or [])}
        assert ids1.isdisjoint(ids2) or not ids2


def test_api_catalog_detail_full_has_weights(client):
    resp = client.get("/api/catalog", params={"detail": "full"})
    assert resp.status_code == 200
    # Full / preview responses should not advertise the short lite cache.
    assert "max-age=60" not in (resp.headers.get("Cache-Control") or "")
    data = resp.json()
    jewelry = [
        p
        for products in (data.get("categories") or {}).values()
        for p in products
        if p.get("golds")
    ]
    if not jewelry:
        pytest.skip("no published jewelry products in DB")
    sample = jewelry[0]
    assert "weights" in sample
    assert "images" in sample


def test_api_catalog_product_detail_200_and_404(client):
    listing = client.get("/api/catalog", params={"detail": "full"})
    assert listing.status_code == 200
    jewelry = [
        p
        for products in (listing.json().get("categories") or {}).values()
        for p in products
        if p.get("golds")
    ]
    if not jewelry:
        pytest.skip("no published jewelry products in DB")

    product_id = jewelry[0]["id"]
    detail = client.get(f"/api/catalog/product/{product_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["product"]["id"] == product_id
    assert "weights" in body["product"]
    assert "images" in body["product"]

    missing = client.get(f"/api/catalog/product/{uuid4()}")
    assert missing.status_code == 404


def _nav_category_rows():
    return [
        {"slug": "diamond", "label_zh": "紀念鑽石", "label_en": "Memorial diamond", "thumbUrl": None, "addonPrice": 0},
        {"slug": "pendant", "label_zh": "項墜", "label_en": "Pendant", "thumbUrl": None, "addonPrice": 0},
        {"slug": "ring", "label_zh": "戒指", "label_en": "Ring", "thumbUrl": None, "addonPrice": 0},
        {"slug": "earring", "label_zh": "耳環", "label_en": "Earring", "thumbUrl": None, "addonPrice": 0},
        {"slug": "bracelet", "label_zh": "手鍊", "label_en": "Bracelet", "thumbUrl": None, "addonPrice": 0},
        {"slug": "chain", "label_zh": "鏈條", "label_en": "Chain", "thumbUrl": None, "addonPrice": 0},
    ]


class _NavCursor:
    def __init__(self, *, tombstones_missing=False, diamond_rows=None, image_rows=None, slugs=None):
        self.statements: list[str] = []
        self.tombstones_missing = tombstones_missing
        self.diamond_rows = diamond_rows or []
        self.image_rows = image_rows or []
        self.slugs = slugs or ["pendant", "ring", "diamond"]
        self._result: list = []

    def execute(self, sql, params=None):
        text = " ".join(str(sql).split())
        self.statements.append(text)
        lowered = text.lower()
        if "memorial_diamond_style_tombstones" in lowered:
            if self.tombstones_missing:
                from psycopg.errors import UndefinedTable

                raise UndefinedTable("relation memorial_diamond_style_tombstones does not exist")
            self._result = []
            return
        if "distinct category" in lowered:
            self._result = [{"category": slug} for slug in self.slugs]
            return
        if "from products" in lowered and "category = 'diamond'" in lowered:
            assert "select *" not in lowered
            self._result = self.diamond_rows
            return
        if "from product_images" in lowered:
            self._result = self.image_rows
            return
        raise AssertionError(f"unexpected nav SQL: {text}")

    def fetchall(self):
        return list(self._result)


def _assert_nav_sql_allowlist(statements: list[str]) -> None:
    joined = " ".join(statements).lower()
    assert "product_variants" not in joined
    assert "create table" not in joined
    assert "alter table" not in joined
    assert "count(" not in joined
    assert "select *" not in joined


def test_fetch_shop_nav_catalog_shape_and_queries(monkeypatch):
    from app.catalog import fetch_shop_nav_catalog

    monkeypatch.setattr("app.catalog.fetch_categories", lambda cur: _nav_category_rows())
    diamond = {
        "id": "d1",
        "category": "diamond",
        "name_zh": "白",
        "name_en": "White",
        "style_key": "diamond-white",
        "default_color": "white",
        "description_zh": None,
        "description_en": None,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
        "sort_order": 0,
        "is_published": True,
    }
    cur = _NavCursor(
        diamond_rows=[diamond],
        image_rows=[
            {
                "product_id": "d1",
                "color": "round",
                "file_path": SUPABASE_PRODUCT,
                "sort_order": 0,
                "updated_at": None,
            }
        ],
    )
    payload = fetch_shop_nav_catalog(cur)
    _assert_nav_sql_allowlist(cur.statements)
    assert set(payload) == {"categoryOrder", "categoryMeta", "categories"}
    assert payload["categoryOrder"][0] == "diamond"
    assert payload["categories"]["pendant"] == []
    assert payload["categories"]["ring"] == []
    assert payload["categories"]["earring"] == []
    assert payload["categories"]["bracelet"] == []
    assert payload["categories"]["chain"] == []
    diamonds = payload["categories"]["diamond"]
    assert diamonds
    assert all(not p.get("golds") for p in diamonds)
    assert all("weights" not in p for p in diamonds)
    assert any(p.get("styleKey") == "diamond-white" for p in diamonds)


def test_fetch_shop_nav_catalog_missing_tombstones_is_empty(monkeypatch):
    from app.catalog import fetch_shop_nav_catalog

    monkeypatch.setattr("app.catalog.fetch_categories", lambda cur: _nav_category_rows())
    cur = _NavCursor(tombstones_missing=True)
    payload = fetch_shop_nav_catalog(cur)
    _assert_nav_sql_allowlist(cur.statements)
    assert payload["categories"]["diamond"]
    assert payload["categories"]["pendant"] == []


def test_api_catalog_nav_skips_jewelry_children(client):
    resp = client.get("/api/catalog", params={"nav": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data) == {"categoryOrder", "categoryMeta", "categories"}
    assert data["categoryOrder"][0] == "diamond"
    cats = data["categories"]
    assert isinstance(cats.get("diamond"), list)
    for slug, products in cats.items():
        if slug == "diamond":
            continue
        assert products == []
    for product in cats.get("diamond") or []:
        assert "weights" not in product
        assert product.get("golds") == []


def test_api_catalog_without_nav_keeps_live_rows(client):
    nav = client.get("/api/catalog", params={"nav": 1})
    full = client.get("/api/catalog")
    assert nav.status_code == 200
    assert full.status_code == 200
    nav_body = nav.json()
    full_body = full.json()
    assert "total" in full_body
    assert "page" in full_body
    jewelry_nav = [
        product
        for slug, products in (nav_body.get("categories") or {}).items()
        if slug != "diamond"
        for product in (products or [])
    ]
    jewelry_full = [
        product
        for slug, products in (full_body.get("categories") or {}).items()
        if slug != "diamond"
        for product in (products or [])
    ]
    assert jewelry_nav == []
    if not jewelry_full:
        pytest.skip("no published jewelry products in DB")
    assert any(product.get("golds") or product.get("thumbUrl") for product in jewelry_full)
