"""Shop must expose only admin-configured 款式選項, not bundled static full matrices."""

from app.catalog import build_catalog_product
from app.controllers.shop_controller import _validate_product_variant


class _VariantCursor:
    def __init__(self, variant=None):
        self.variant = variant
        self.queries: list[str] = []

    def execute(self, query, params=None):
        self.queries.append(" ".join(query.split()))
        return None

    def fetchone(self):
        return self.variant


def test_build_catalog_product_limits_golds_and_carats_to_variants():
    product = {
        "id": "prod-1",
        "category": "ring",
        "name_zh": "Test Ring",
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
    variants = [
        {"gold": "14k", "carat": "0.3", "weight_chin": 1.2},
        {"gold": "18k", "carat": "0.5", "weight_chin": 1.4},
    ]

    entry = build_catalog_product(product, variants, [])

    assert entry["golds"] == ["14k", "18k"]
    assert entry["carats"] == ["0.3", "0.5"]
    assert set(entry["weights"]["14k"]) == {"0.3"}
    assert set(entry["weights"]["18k"]) == {"0.5"}


def test_validate_product_variant_rejects_unconfigured_combo(monkeypatch):
    body = {
        "category": "ring",
        "type": "ring-A",
        "gold": "14k",
        "carat": "0.5",
    }

    def fake_get_product_variant(cur, **kwargs):
        assert kwargs["gold"] == "14k"
        assert kwargs["carat"] == "0.5"
        return None

    monkeypatch.setattr(
        "app.controllers.shop_controller.get_product_variant",
        fake_get_product_variant,
    )
    err = _validate_product_variant(_VariantCursor(), body)
    assert err == "所選金屬或克拉不在此商品款式選項中"


def test_build_catalog_exposes_image_slot_colors_for_metal_filter():
    """Shop 金屬顏色 options are derived from admin image slot keys + defaultColor."""
    product = {
        "id": "prod-color",
        "category": "pendant",
        "name_zh": "Yellow Only",
        "name_en": None,
        "description_zh": None,
        "description_en": None,
        "default_color": "yellow",
        "sort_order": 0,
        "is_published": True,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }
    variants = [{"gold": "14k", "carat": "0.3", "weight_chin": 1.0}]
    images = [
        {
            "color": "yellow-white",
            "file_path": "/static/uploads/products/yellow.png",
        }
    ]

    # Missing file on disk is dropped from images map; colors still come from keys
    # that survive — use empty images list and assert defaultColor is on entry.
    entry = build_catalog_product(product, variants, [])
    assert entry["defaultColor"] == "yellow"

    entry_with = build_catalog_product(
        product,
        variants,
        [{"color": "yellow-white", "file_path": "https://cdn.example/y.png"}],
    )
    assert "yellow-white" in entry_with["colors"]


def test_validate_product_variant_accepts_configured_combo(monkeypatch):
    body = {
        "category": "ring",
        "type": "ring-A",
        "gold": "14k",
        "carat": "0.3",
    }

    def fake_get_product_variant(cur, **kwargs):
        return {"gold": "14k", "carat": "0.3", "weight_chin": 1.0}

    monkeypatch.setattr(
        "app.controllers.shop_controller.get_product_variant",
        fake_get_product_variant,
    )
    assert _validate_product_variant(_VariantCursor(), body) is None
