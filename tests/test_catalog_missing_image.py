"""Catalog API must not surface missing /static upload paths."""

from app.catalog import build_catalog_product


def test_build_catalog_rewrites_missing_upload_for_style_slot():
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
    urls = entry["images"].get("white-white") or []

    assert urls, "expected rewritten shop-product URL"
    assert all(not u.endswith("test.png") for u in urls)
    assert all("/static/images/shop-product/" in u for u in urls)
    assert entry["styleKey"] == "pendant-A"
