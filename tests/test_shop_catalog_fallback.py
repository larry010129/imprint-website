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

    from app.admin_products import should_skip_published_autosave_write

    assert should_skip_published_autosave_write(True, True) is True
    assert should_skip_published_autosave_write(True, False) is False
    assert should_skip_published_autosave_write(False, True) is False
    assert should_skip_published_autosave_write(False, False) is False

    src = Path(__file__).resolve().parents[1].joinpath(
        "app", "controllers", "admin_controller.py"
    ).read_text(encoding="utf-8")
    update_start = src.index("@router.post(\"/product-update\")")
    update_body = src[update_start : src.index("@router.post(\"/product-action\")", update_start)]
    assert "should_skip_published_autosave_write" in update_body
    assert 'if body.get("autosave"):' in update_body
    assert 'cleaned["isPublished"] = bool(existing["is_published"])' in update_body
    create_start = src.index("@router.post(\"/products\")")
    create_body = src[create_start : update_start]
    assert "should_skip_published_autosave_write" not in create_body
    assert 'if body.get("autosave"):' in create_body
    assert 'cleaned["isPublished"] = False' in create_body


def test_ensure_category_catalog_does_not_complete_on_empty_incoming():
    src = _shop_src()
    body = src.split("async function ensureCategoryCatalog(", 1)[1].split(
        "function applyCategoryAddonPricesFromMeta(", 1
    )[0]
    assert "incoming.length === 0 && total === 0" in body
    assert "incomingCategoryProducts" in body
    assert "|| incoming.length === 0," not in body.replace(" ", "")


def test_render_type_cards_hides_no_matches_when_unfiltered_empty():
    src = _shop_src()
    body = src.split("function renderTypeCards()", 1)[1].split(
        "function syncVariantChipActiveStates()", 1
    )[0]
    assert "classList.toggle('hidden', products.length > 0)" not in body
    assert "syncCatalogFilterEmpty" in body
    sync = src.split("function syncCatalogFilterEmpty(", 1)[1].split(
        "function populateCatalogFilters(", 1
    )[0]
    assert "catalogSearchOrFiltersActive" in sync
    assert "catalog_no_matches" in sync
    assert "此品項暫無上架款式。" in sync


def test_admin_products_tab_fetch_seq_guard():
    """Tab changes must fetch category=<slug> and ignore stale getProducts results."""
    src = ADMIN_PRODUCTS_JS.read_text(encoding="utf-8")
    fetch_start = src.index("function fetchProducts(")
    fetch_body = src[fetch_start : src.index("function load(", fetch_start)]
    assert "category:" in fetch_body
    assert "getProducts" in fetch_body

    load_start = src.index("function load(")
    load_body = src[load_start : src.index("function prefetch(", load_start)]
    assert "var _loadSeq = 0;" in src
    assert "var seq = ++_loadSeq;" in load_body
    assert "if (seq !== _loadSeq) return;" in load_body
    assert "clearTimeout(timer)" in load_body
    assert "LOAD_TIMEOUT_MS" in load_body
    assert "requestedCat !== currentCat" in load_body
    assert "state.products = incoming;" in load_body
    assert "currentCat !== requestedCat" in load_body

    ensure_start = src.index("function ensureLoaded(")
    ensure_body = src[ensure_start : src.index("window.AdminProductsPanel", ensure_start)]
    assert "load(false, true)" in ensure_body

    tab_start = src.index("root.querySelectorAll('.ap-tab-btn')")
    tab_body = src[tab_start : src.index("var addCatBtn", tab_start)]
    assert "ap-tab-btn--add" in tab_body
    assert "unmountProductsTable()" in tab_body
    assert "tableAreaSkeletonHtml()" in tab_body
    assert "load(true, true)" in tab_body


def test_admin_products_editor_category_rebuilds_image_slots():
    """品項 change must rebuild slots from catSel.value — jewelry metal×diamond, diamond cut-only."""
    src = ADMIN_PRODUCTS_JS.read_text(encoding="utf-8")
    pair_start = src.index("function slotPairSelectHtml(")
    pair_body = src[pair_start : src.index("function groupImagesForSlots(", pair_start)]
    assert "category === 'diamond'" in pair_body
    assert "ap-image-slot-diamond-only" in pair_body
    assert "ap-image-slot-metal" in pair_body
    assert "ap-image-slot-diamond'" in pair_body or 'ap-image-slot-diamond"' in pair_body

    chrome_idx = src.index("function syncDiamondEditorChrome(cat) {")
    change_idx = src.index("catSel?.addEventListener('change', function () {", chrome_idx)
    change_body = src[change_idx : src.index("form.addEventListener('submit'", change_idx)]
    assert "syncDiamondEditorChrome(cat)" in change_body
    assert "imageSlotsHtml(currentImages, catSel.value)" in change_body
    assert "data-category" in change_body
    assert "ap-image-slot-diamond-only" in change_body
    assert "ap-image-slot-metal" in change_body
    assert "imageSlotsHtml([], catSel.value)" in change_body


def test_sync_chain_variant_thickness_guards_non_chain():
    """HIGH 2: never rewrite ring/pendant/earring/bracelet carat selects."""
    src = ADMIN_PRODUCTS_JS.read_text(encoding="utf-8")
    start = src.index("function syncChainVariantThicknessOptions(")
    body = src[start : src.index("function productsInCategory(", start)]
    assert "category !== 'chain'" in body
    assert "return;" in body.split("category !== 'chain'")[1][:80]


def test_collect_form_saves_null_not_empty_length_weights():
    """HIGH 3: empty wax grid is unset (null), not {}."""
    src = ADMIN_PRODUCTS_JS.read_text(encoding="utf-8")
    collect = src[src.index("function collectForm(") : src.index("function validateProductPayload(")]
    assert "collectChainLengthWeights(form) || {}" not in collect
    assert "collectChainLengthWeights(form)" in collect


def test_load_catalog_boot_uses_nav_flag():
    """Step-1 boot hits GET /api/catalog?nav=1, not page=1&pageSize=1."""
    src = _shop_src()
    start = src.index("async function loadCatalog()")
    body = src[start : src.index("function renderCatalogTiles()", start)]
    assert "fetchCatalogPage({ nav: 1 })" in body
    assert "fetchCatalogPage({ page: 1, pageSize: 1 })" not in body
    fetch_start = src.index("async function fetchCatalogPage(")
    fetch_body = src[fetch_start : src.index("function applyCatalogMeta(", fetch_start)]
    assert "params.set('nav', '1')" in fetch_body
    ensure = src[src.index("async function ensureCategoryCatalog(") : src.index("function applyCategoryAddonPricesFromMeta(")]
    assert "fetchCatalogPage({ category, page, pageSize })" in ensure


def test_load_catalog_not_empty_when_api_total_positive():
    """HIGH 4: /api/catalog total > 0 must not show catalog_empty."""
    src = _shop_src()
    start = src.index("async function loadCatalog()")
    body = src[start : src.index("function renderCatalogTiles()", start)]
    assert "catalogPublishedTotal" in body
    assert "categoryOrder" in body
    assert "catalogPublishedTotal <= 0" in body
    render = src[src.index("function renderCatalogTiles()") : src.index("function lookupWeight(", src.index("function renderCatalogTiles()"))]
    assert "catalogPublishedTotal <= 0" in render
    assert "showEmpty" in render


def test_price_hint_quiet_until_quote_fails():
    """HIGH 4: first paint is 選擇規格後顯示估價 until a real failed quote."""
    src = _shop_src()
    hint = src[src.index("function updatePriceHint(") : src.index("function updateCtaState(")]
    assert "lastQuoteFailed" in hint
    assert "shop_price_unavailable" in hint
    assert "shop_complete_options" in hint
    refresh = src[src.index("async function refreshQuotePrices()") : src.index("function updateRingSizeStep(")]
    assert "lastQuoteFailed = isReadyToSubmit()" in refresh
    i18n = (ROOT / "public" / "js" / "shop-i18n.js").read_text(encoding="utf-8")
    assert "選擇規格後顯示估價" in i18n
    calc = (
        ROOT / "content" / "site" / "templates" / "pages" / "shop" / "calculator.html"
    ).read_text(encoding="utf-8")
    assert "選擇規格後顯示估價" in calc
    assert 'id="catalog-empty" hidden' in calc or 'id="catalog-empty" hidden>' in calc
    assert 'data-i18n="catalog_empty">目前沒有上架商品。' not in calc
