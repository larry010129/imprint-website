"""Product admin image URLs must persist as server/SQL paths, not browser-local."""

from app.admin_products import (
    ensure_product_sell_mode_columns,
    is_auto_stock_product_image,
    is_browser_local_image_url,
    is_dead_catalog_placeholder,
    normalize_product_image_url,
    validate_product_fields,
)


def test_rejects_browser_local_urls():
    assert is_browser_local_image_url("blob:http://localhost/abc")
    assert is_browser_local_image_url("data:image/png;base64,abc")
    assert not is_browser_local_image_url("/static/uploads/products/a.png")


def test_detects_dead_svg_placeholders():
    assert is_dead_catalog_placeholder("images/shop/styles/pendant-B.svg")
    assert is_dead_catalog_placeholder("/static/images/shop/styles/ring-A.svg")
    assert not is_dead_catalog_placeholder(
        "/static/images/shop-product/silver/%E9%A0%85%E5%A2%9CB_silver.png"
    )


def test_detects_auto_stock_shop_product_images():
    assert is_auto_stock_product_image(
        "/static/images/shop-product/silver/%E9%A0%85%E5%A2%9CB_silver.png"
    )
    assert is_auto_stock_product_image("images/shop-product/gold/項墜A_gold.png")
    assert not is_auto_stock_product_image("/static/uploads/products/abc.png")


def test_normalize_drops_svg_placeholder():
    assert normalize_product_image_url(
        "images/shop/styles/pendant-B.svg",
        "white-white",
    ) is None


def test_normalize_drops_auto_stock_shop_product():
    assert normalize_product_image_url(
        "/static/images/shop-product/silver/%E9%A0%85%E5%A2%9CB_silver.png",
        "white-white",
    ) is None


def test_normalize_drops_blob_urls():
    assert normalize_product_image_url("blob:http://localhost/x", "white-white") is None


def test_normalize_drops_missing_upload_without_style_hint():
    assert normalize_product_image_url("/static/uploads/products/test.png", "white-white") is None


def test_normalize_keeps_supabase_storage_url():
    url = (
        "https://abc123.supabase.co/storage/v1/object/public/shop-media/products/x.webp"
    )
    assert normalize_product_image_url(url, "white-white") == url


def test_validate_draft_keeps_empty_images_without_inventing():
    cleaned, err = validate_product_fields(
        {
            "category": "pendant",
            "nameZh": "空白新品",
            "defaultColor": "white",
            "isPublished": False,
            "variants": [],
            "images": [],
        }
    )
    assert err is None
    assert cleaned is not None
    assert cleaned["images"] == []


def test_validate_product_fields_drops_dead_placeholders_and_rejects_blob():
    ok, err = validate_product_fields(
        {
            "category": "pendant",
            "nameZh": "測試",
            "defaultColor": "white",
            "isPublished": False,
            "variants": [],
            "images": [
                {"color": "white-white", "url": "images/shop/styles/pendant-A.svg"},
                {"color": "yellow-white", "url": "blob:http://localhost/x"},
            ],
        }
    )
    assert err is None
    assert ok is not None
    assert ok["images"] == []


def test_validate_published_rejects_only_blob_images():
    cleaned, err = validate_product_fields(
        {
            "category": "ring",
            "nameZh": "測試戒",
            "defaultColor": "white",
            "isPublished": True,
            "variants": [
                {"gold": "14k", "carat": "0.5", "weightChin": 0.1},
            ],
            "images": [
                {"color": "white-white", "url": "blob:http://localhost/x"},
            ],
        }
    )
    assert cleaned is None
    assert err
    assert "商品照片" in err


def test_validate_pendant_sell_modes():
    cleaned, err = validate_product_fields(
        {
            "category": "pendant",
            "nameZh": "測試墜",
            "defaultColor": "white",
            "isPublished": False,
            "allowsPendantOnly": True,
            "allowsWithChain": False,
            "variants": [],
            "images": [],
        }
    )
    assert err is None
    assert cleaned["allowsPendantOnly"] is True
    assert cleaned["allowsWithChain"] is False
    assert cleaned["allowsFancyShapes"] is True

    # Left mode (可不含鍊賣): customer may choose with/without chain.
    choose, choose_err = validate_product_fields(
        {
            "category": "pendant",
            "nameZh": "測試墜",
            "defaultColor": "white",
            "isPublished": False,
            "allowsPendantOnly": True,
            "allowsWithChain": True,
            "variants": [],
            "images": [],
        }
    )
    assert choose_err is None
    assert choose["allowsPendantOnly"] is True
    assert choose["allowsWithChain"] is True

    # Right mode (含鍊賣): with-chain only.
    chain_only, chain_err = validate_product_fields(
        {
            "category": "pendant",
            "nameZh": "測試墜",
            "defaultColor": "white",
            "isPublished": False,
            "allowsPendantOnly": False,
            "allowsWithChain": True,
            "variants": [],
            "images": [],
        }
    )
    assert chain_err is None
    assert chain_only["allowsPendantOnly"] is False
    assert chain_only["allowsWithChain"] is True

    cleaned_off, _ = validate_product_fields(
        {
            "category": "ring",
            "nameZh": "測試戒",
            "defaultColor": "white",
            "isPublished": False,
            "allowsFancyShapes": False,
            "variants": [],
            "images": [],
        }
    )
    assert cleaned_off["allowsFancyShapes"] is False

    bad, bad_err = validate_product_fields(
        {
            "category": "pendant",
            "nameZh": "測試墜",
            "defaultColor": "white",
            "isPublished": False,
            "allowsPendantOnly": False,
            "allowsWithChain": False,
            "variants": [],
            "images": [],
        }
    )
    assert bad is None
    assert bad_err and "可不含鍊賣" in bad_err


def test_ensure_product_sell_mode_columns_idempotent():
    import os

    from dotenv import load_dotenv

    load_dotenv()
    if not os.environ.get("DATABASE_URL"):
        import pytest

        pytest.skip("DATABASE_URL not set")

    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        ensure_product_sell_mode_columns(cur)
        ensure_product_sell_mode_columns(cur)
        cur.execute(
            """
            select column_name from information_schema.columns
            where table_schema = 'public' and table_name = 'products'
              and column_name in ('allows_pendant_only', 'allows_with_chain', 'allows_fancy_shapes')
            order by column_name
            """
        )
        cols = [row["column_name"] for row in cur.fetchall()]
    assert cols == ["allows_fancy_shapes", "allows_pendant_only", "allows_with_chain"]
