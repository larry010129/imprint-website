"""Metal-color preview: catalog slot lookup must not cross metals."""

from app.catalog import build_catalog_product


def test_catalog_product_keeps_only_configured_image_slots(monkeypatch):
    upload = "/static/uploads/products/custom-white.png"
    monkeypatch.setattr(
        "app.catalog.static_url_exists",
        lambda url: url == upload,
    )
    product = {
        "id": "prod-1",
        "category": "pendant",
        "name_zh": "四爪項墜",
        "name_en": None,
        "description_zh": None,
        "description_en": None,
        "default_color": "white",
        "sort_order": 0,
        "is_published": True,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }
    images = [
        {
            "color": "white-white",
            "file_path": upload,
        }
    ]
    variants = [{"gold": "14k", "carat": "0.3", "weight_chin": 1.0}]

    entry = build_catalog_product(product, variants, images)

    assert "white-white" in entry["images"]
    assert "rose-white" not in entry["images"]
    assert "yellow-white" not in entry["images"]
