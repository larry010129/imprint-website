"""Per-product ring size config — admin validate, catalog, quote stack on labor."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.admin_products import validate_product_fields
from app.catalog import build_catalog_product
from app.pricing import compute_order_pricing, ring_size_addon_from_config


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
            "startSize": 7,
            "sizes": [
                {"size": 7, "addonPriceTwd": 0},
                {"size": 12, "addonPriceTwd": 800},
            ],
        },
    }
    body.update(overrides)
    return body


def test_validate_keeps_ring_size_config():
    cleaned, err = validate_product_fields(_ring_body())
    assert err is None
    cfg = cleaned["ringSizeConfig"]
    assert cfg["startSize"] == 7
    assert cfg["sizes"] == [
        {"size": 7, "addonPriceTwd": 0.0},
        {"size": 12, "addonPriceTwd": 800.0},
    ]


def test_validate_clears_ring_size_for_non_ring():
    body = _ring_body(category="pendant")
    cleaned, err = validate_product_fields(body)
    assert err is None
    assert cleaned["ringSizeConfig"] is None


def test_validate_rejects_bad_start_size():
    cleaned, err = validate_product_fields(
        _ring_body(ringSizeConfig={"startSize": 3, "sizes": []})
    )
    assert cleaned is None
    assert "起始戒圍" in (err or "")


def test_validate_rejects_duplicate_size():
    cleaned, err = validate_product_fields(
        _ring_body(
            ringSizeConfig={
                "startSize": 7,
                "sizes": [
                    {"size": 9, "addonPriceTwd": 100},
                    {"size": 9, "addonPriceTwd": 200},
                ],
            }
        )
    )
    assert cleaned is None
    assert "戒圍尺寸重複" in (err or "")


def test_validate_rejects_negative_size_addon():
    cleaned, err = validate_product_fields(
        _ring_body(
            ringSizeConfig={
                "startSize": 7,
                "sizes": [{"size": 12, "addonPriceTwd": -1}],
            }
        )
    )
    assert cleaned is None
    assert "戒圍品項加價" in (err or "")


def test_ring_size_addon_helper():
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
    assert ring_size_addon_from_config(None, 12) == 0


def test_catalog_exposes_ring_size_config():
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
    # Variant labor 3500 + ring size 800 (does not replace variant addon).
    assert quote["laborPrice"] == 4300
    assert quote["ringSizePrice"] == 800


def test_quote_ring_size_missing_row_is_zero(monkeypatch):
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
            "ringSize": 9,
        },
    )
    assert quote["ready"] is True
    assert quote["laborPrice"] == 3500
    assert quote["ringSizePrice"] is None
