"""Product admin image URLs must persist as server/SQL paths, not browser-local."""

from app.admin_products import (
    ensure_product_sell_mode_columns,
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


def test_normalize_rewrites_svg_placeholder_to_shop_product():
    url = normalize_product_image_url(
        "images/shop/styles/pendant-B.svg",
        "white-white",
    )
    assert url
    assert url.startswith("/static/images/shop-product/")
    assert not is_dead_catalog_placeholder(url)


def test_normalize_drops_blob_urls():
    assert normalize_product_image_url("blob:http://localhost/x", "white-white") is None


def test_normalize_drops_missing_upload_without_style_hint():
    assert normalize_product_image_url("/static/uploads/products/test.png", "white-white") is None


def test_validate_product_fields_rewrites_images_and_rejects_blob():
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
    assert len(ok["images"]) == 1
    assert ok["images"][0]["color"] == "white-white"
    assert ok["images"][0]["url"].startswith("/static/images/shop-product/")


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


def test_validate_pendant_sell_modes_xor():
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
    assert bad_err and "僅墜子賣" in bad_err


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
              and column_name in ('allows_pendant_only', 'allows_with_chain')
            order by column_name
            """
        )
        cols = [row["column_name"] for row in cur.fetchall()]
    assert cols == ["allows_pendant_only", "allows_with_chain"]
