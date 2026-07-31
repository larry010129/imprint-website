"""Catalog API must not invent shop-product letter PNGs for missing uploads."""

from app.catalog import build_catalog_product

SUPABASE_PRODUCT = (
    "https://abc123.supabase.co/storage/v1/object/public/shop-media/products/x.webp"
)


def test_build_catalog_includes_supabase_storage_url():
    product = {
        "id": "c54963cb-7c3d-469e-b26d-ae4372870445",
        "category": "pendant",
        "name_zh": "四爪項墜",
        "name_en": None,
        "description_zh": None,
        "description_en": None,
        "default_color": "white",
        "sort_order": 0,
        "is_published": True,
        "allows_engraving": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }
    images = [{"color": "white-white", "file_path": SUPABASE_PRODUCT}]
    entry = build_catalog_product(product, [], images)
    assert SUPABASE_PRODUCT in entry["images"].get("white-white", [])


def test_build_catalog_drops_missing_upload_without_style_fallback():
    product = {
        "id": "c54963cb-7c3d-469e-b26d-ae4372870445",
        "category": "pendant",
        "name_zh": "四爪項墜",
        "name_en": None,
        "description_zh": None,
        "description_en": None,
        "default_color": "white",
        "sort_order": 0,
        "is_published": True,
        "allows_engraving": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }
    images = [
        {
            "color": "white-white",
            "file_path": "/static/uploads/products/test.png",
        }
    ]

    entry = build_catalog_product(product, [], images)

    assert entry["images"] == {}
    assert entry["styleKey"] is None


def test_build_catalog_drops_auto_stock_shop_product_paths():
    product = {
        "id": "c54963cb-7c3d-469e-b26d-ae4372870445",
        "category": "pendant",
        "name_zh": "測試",
        "name_en": None,
        "description_zh": None,
        "description_en": None,
        "default_color": "white",
        "sort_order": 0,
        "is_published": True,
        "allows_engraving": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }
    images = [
        {
            "color": "white-white",
            "file_path": "/static/images/shop-product/silver/%E9%A0%85%E5%A2%9CA_silver.png",
        }
    ]

    entry = build_catalog_product(product, [], images)

    assert entry["images"] == {}
    assert entry["styleKey"] is None
