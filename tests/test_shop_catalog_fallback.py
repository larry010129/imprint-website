"""Phase 1B: bundled catalog is offline/demo only; prod must not resurrect SKUs on API failure."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOP_JS = ROOT / "public" / "js" / "shop.js"
ADMIN_PRODUCTS_JS = ROOT / "public" / "js" / "admin-products.js"


def _shop_src() -> str:
    return SHOP_JS.read_text(encoding="utf-8")


def test_shop_allows_static_catalog_gated_by_api_mode():
    src = _shop_src()
    assert "function shopAllowsStaticCatalog()" in src
    assert "return !shopUsesApi();" in src


def test_apply_static_catalog_fallback_offline_only():
    src = _shop_src()
    start = src.index("function applyStaticCatalogFallback()")
    body = src[start : src.index("function renderCatalogSkeleton", start)]
    assert "if (!shopAllowsStaticCatalog()) return false;" in body
    assert "catalog = window.shopCatalogData.categories;" in body


def test_enrich_catalog_from_static_offline_only():
    src = _shop_src()
    start = src.index("function enrichCatalogFromStatic()")
    body = src[start : src.index("function catalogHasJewelryFromApi()", start)]
    assert "if (!shopAllowsStaticCatalog()) return;" in body


def test_prod_api_success_injects_memorial_diamonds_not_full_static():
    src = _shop_src()
    assert "function injectMemorialDiamondCatalogIfNeeded()" in src
    assert "function catalogHasJewelryFromApi()" in src
    load_start = src.index("async function loadCatalog()")
    load_body = src[load_start : load_start + 3500]
    assert "injectMemorialDiamondCatalogIfNeeded();" in load_body
    assert "if (shopAllowsStaticCatalog())" in load_body
    assert "enrichCatalogFromStatic();" in load_body
    # Prod must not fall back to full static catalog when API returns empty
    assert "if (!catalogCategories().length && applyStaticCatalogFallback())" not in load_body


def test_api_error_does_not_resurrect_static_in_prod():
    src = _shop_src()
    catch_idx = src.index("} catch (err) {", src.index("async function loadCatalog()"))
    catch_body = src[catch_idx : catch_idx + 400]
    assert "if (applyStaticCatalogFallback())" in catch_body
    assert "if (shopUsesApi() && applyStaticCatalogFallback())" not in catch_body


def test_shop_uses_local_pricing_still_api_gated():
    """Sprint A money path unchanged — local pricing only when API is down."""
    src = _shop_src()
    assert "function shopUsesLocalPricing()" in src
    assert "&& !shopUsesApi()" in src.split("function shopUsesLocalPricing()")[1][:120]


def test_admin_products_memorial_series_note():
    src = ADMIN_PRODUCTS_JS.read_text(encoding="utf-8")
    assert "紀念鑽石系列" in src
    assert "不在此商品 CRUD 管理" in src
