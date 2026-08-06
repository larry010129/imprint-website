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
    assert "function ensureMemorialDiamondCatalog()" in src
    inject_start = src.index("function injectMemorialDiamondCatalogIfNeeded()")
    inject_body = src[inject_start : src.index("function injectDiamondCatalog()", inject_start)]
    assert "catalog.diamond" in inject_body
    assert "catalogHasJewelryFromApi()" not in inject_body


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


def test_admin_products_memorial_color_shape_note():
    src = ADMIN_PRODUCTS_JS.read_text(encoding="utf-8")
    assert "紀念鑽石" in src
    assert "不含金屬／價格" in src
    assert "前往價格設定" in src
    assert "不在此商品 CRUD 管理" not in src
    assert "ap-image-slot-diamond-only" in src
    assert "MEMORIAL_DIAMOND_STYLE_KEYS" in src
    assert "diamond-white" in src
    assert "DIAMOND_SHAPE_SLOT_OPTIONS" in src
    assert "鑽石切工" in src


def test_shop_memorial_color_first_flow():
    src = _shop_src()
    assert "function memorialDiamondProductForColor" in src
    assert "function applyMemorialDiamondProductColor" in src
    assert "function defaultMemorialDiamondTypeId" in src
    assert "enterDiamondLooseProduct" not in src
    assert "diamond-first-love" not in (
        ROOT / "public" / "js" / "shop-catalog-data.js"
    ).read_text(encoding="utf-8")
    assert "diamond-white" in (
        ROOT / "public" / "js" / "shop-catalog-data.js"
    ).read_text(encoding="utf-8")


def test_shop_memorial_skips_style_step_to_configure():
    src = _shop_src()
    cat_start = src.index("async function selectCategory(")
    cat_body = src[cat_start : src.index("function resolveMemorialDiamondTypeRef", cat_start)]
    assert "if (cat === 'diamond')" in cat_body
    assert "ensureMemorialDiamondCatalog()" in cat_body
    assert "await selectType(typeId, opts)" in cat_body
    assert "return;" in cat_body
    assert "setShopView('styles', opts)" not in cat_body.split("if (cat === 'diamond')")[1].split("await ensureCategoryCatalog")[0]
    set_view_start = src.index("function setShopView(")
    set_view_body = src[set_view_start : set_view_start + 280]
    assert "view === 'styles' && isDiamondOnlyCategory()" in set_view_body
    render_start = src.index("function renderTypeCards(")
    render_body = src[render_start : render_start + 220]
    assert "isDiamondOnlyCategory()" in render_body
    chrome_start = src.index("function updateDiamondWizardChrome")
    chrome_body = src[chrome_start : src.index("const WIZARD_GUIDE", chrome_start)]
    assert "stylesStep.hidden = skipStyles" in chrome_body
    back_start = src.index("document.getElementById('back-to-styles')?.addEventListener")
    back_body = src[back_start : back_start + 450]
    assert "isDiamondOnlyCategory()" in back_body
    assert "back-to-catalog" in back_body
    assert "memorialDiamondShapeImageUrl" in src
    assert "product?.images?.[shape]" in src
    get_product_start = src.index("function getProduct(")
    get_product_body = src[get_product_start : get_product_start + 320]
    assert "styleKey" in get_product_body


def test_admin_products_upload_waits_for_crop_modal():
    """Product upload must not silently skip crop when AdminTables is still loading."""
    src = ADMIN_PRODUCTS_JS.read_text(encoding="utf-8")
    assert "function whenProductCropReady(" in src
    assert "renderProductImageCropModal" in src
    assert "裁切元件尚未載入" in src
    crop_start = src.index("function openProductImageCrop(")
    crop_body = src[crop_start : src.index("function prepareFilesWithCrop", crop_start)]
    assert "whenProductCropReady" in crop_body
    # Regression: silent resolve(file) bypassed crop UI entirely.
    assert "resolve(file)" not in crop_body


def test_admin_products_autosave_never_publishes_from_checkbox():
    """Autosave must not honor 稍後上架 toggle — only explicit save publishes."""
    src = ADMIN_PRODUCTS_JS.read_text(encoding="utf-8")
    save_start = src.index("function saveProduct(")
    save_body = src[save_start : src.index("function fetchProducts(", save_start)]
    assert "if (isAutosave)" in save_body
    assert "payload.isPublished = product ? !!product.is_published : false" in save_body
    assert "payload.autosave = true" in save_body
    assert "isDraft = true" in save_body


def test_admin_product_update_autosave_preserves_publish_flag():
    """Server-side guard: autosave requests cannot flip is_published."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[1].joinpath(
        "app", "controllers", "admin_controller.py"
    ).read_text(encoding="utf-8")
    update_start = src.index("@router.post(\"/product-update\")")
    update_body = src[update_start : src.index("@router.post(\"/product-action\")", update_start)]
    assert 'if body.get("autosave"):' in update_body
    assert 'cleaned["isPublished"] = bool(existing["is_published"])' in update_body
    create_start = src.index("@router.post(\"/products\")")
    create_body = src[create_start : update_start]
    assert 'if body.get("autosave"):' in create_body
    assert 'cleaned["isPublished"] = False' in create_body
