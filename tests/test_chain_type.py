"""Necklace type selection — catalog, admin validation, and pricing fallback."""

from unittest.mock import MagicMock

from app.admin_products import validate_product_fields
from app.chain_catalog import DEFAULT_NECKLACE_TYPE, NECKLACE_TYPES, necklace_type_length_weights
from app.pricing import _lookup_weight, _resolve_chain_wax


def _chain_publish_body(**overrides):
    body = {
        "category": "chain",
        "nameZh": "測試鍊條",
        "defaultColor": "white",
        "isPublished": True,
        "variants": [{"gold": "18k", "carat": "1.5mm", "weightChin": 0.033}],
        "lengthWeights": {"1.5mm": {"36": 0.099, "46": 0.033}},
        "images": [{"color": "white", "url": "/static/uploads/products/chain-test.png"}],
    }
    body.update(overrides)
    return body


def test_chain_catalog_has_douyuan_from_excel():
    entry = NECKLACE_TYPES["douyuan"]
    assert entry["labelZh"] == "抖圓鏈"
    assert entry["thicknesses"] == ["1.0mm", "1.5mm", "2.0mm", "2.5mm", "3.0mm"]
    table = necklace_type_length_weights("douyuan")
    assert table["1.5mm"]["46"] == 0.033
    assert table["3.0mm"]["80"] == 0.12


def test_validate_chain_type_round_trip():
    body = {
        "category": "chain",
        "nameZh": "測試鍊",
        "defaultColor": "white",
        "isPublished": False,
        "chainType": "douyuan",
        "variants": [{"gold": "18k", "carat": "1.5mm", "weightChin": 0.033}],
        "lengthWeights": {"1.5mm": {"46": 0.033}},
        "images": [],
    }
    cleaned, err = validate_product_fields(body)
    assert err is None
    assert cleaned["chainType"] == "douyuan"


def test_validate_chain_publish_defaults_chain_type():
    body = {
        "category": "chain",
        "nameZh": "測試鍊",
        "defaultColor": "white",
        "isPublished": False,
        "variants": [{"gold": "18k", "carat": "1.5mm", "weightChin": 0.033}],
        "lengthWeights": {"1.5mm": {"46": 0.033}},
        "images": [],
    }
    cleaned, err = validate_product_fields(body)
    assert err is None
    assert cleaned["chainType"] is None


def test_validate_chain_publish_sets_default_chain_type(monkeypatch):
    monkeypatch.setattr("app.admin_products.static_url_exists", lambda _url: True)
    body = _chain_publish_body()
    cleaned, err = validate_product_fields(body)
    assert err is None
    assert cleaned["chainType"] == DEFAULT_NECKLACE_TYPE


def test_resolve_chain_wax_prefers_admin_over_type_catalog(monkeypatch):
    product_id = "chain-type-1"
    admin = {"1.5mm": {"46": 0.055}}

    def fake_length_weights(cur, pid):
        return admin

    def fake_chain_type(cur, pid):
        return "douyuan"

    monkeypatch.setattr("app.pricing._product_length_weights", fake_length_weights)
    monkeypatch.setattr("app.pricing._product_chain_type", fake_chain_type)
    monkeypatch.setattr(
        "app.pricing.resolve_product_id",
        lambda *a, **k: product_id,
    )

    cur = MagicMock()
    assert _resolve_chain_wax(cur, product_id=product_id, carat="1.5mm", length_cm=46) == 0.055


def test_resolve_chain_wax_falls_back_to_type_catalog(monkeypatch):
    product_id = "chain-type-2"

    def fake_length_weights(cur, pid):
        return {"1.5mm": {"36": 0.099}}

    def fake_chain_type(cur, pid):
        return "douyuan"

    monkeypatch.setattr("app.pricing._product_length_weights", fake_length_weights)
    monkeypatch.setattr("app.pricing._product_chain_type", fake_chain_type)
    monkeypatch.setattr(
        "app.pricing.resolve_product_id",
        lambda *a, **k: product_id,
    )

    cur = MagicMock()
    assert _resolve_chain_wax(cur, product_id=product_id, carat="1.5mm", length_cm=46) == 0.033


def test_lookup_weight_chain_uses_type_fallback_when_length_missing(monkeypatch):
    product_id = "chain-type-3"

    def fake_get_product_variant(cur, **kwargs):
        return {"weight_chin": 0.018}

    def fake_resolve(cur, **kwargs):
        return product_id

    def fake_length_weights(cur, pid):
        return {"1.5mm": {"36": 0.099}}

    def fake_chain_type(cur, pid):
        return "douyuan"

    monkeypatch.setattr("app.pricing.get_product_variant", fake_get_product_variant)
    monkeypatch.setattr("app.pricing.resolve_product_id", fake_resolve)
    monkeypatch.setattr("app.pricing._product_length_weights", fake_length_weights)
    monkeypatch.setattr("app.pricing._product_chain_type", fake_chain_type)

    cur = MagicMock()
    looked_up = _lookup_weight(
        cur,
        category="chain",
        product_id=product_id,
        gold="18k",
        carat="1.5mm",
        length_cm=46,
        require_published=True,
    )
    assert looked_up is not None
    _, weight_chin = looked_up
    assert abs(weight_chin - 0.528) < 1e-6
