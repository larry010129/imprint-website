"""Catalog API must not invent shop-product letter PNGs for missing uploads."""

from app.catalog import build_catalog_product

SUPABASE_PRODUCT = (
    "https://abc123.supabase.co/storage/v1/object/public/shop-media/products/x.webp"
)


def test_build_catalog_includes_supabase_storage_url():
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
    images = [{"color": "white-white", "file_path": SUPABASE_PRODUCT}]
    entry = build_catalog_product(product, [], images)
    assert SUPABASE_PRODUCT in entry["images"].get("white-white", [])
    assert entry["category"] == "pendant"
    assert entry["sortOrder"] == 0
    # sortOrder for client letter-SKU stock; styleKey still not invented.
    assert entry["styleKey"] is None


def test_build_catalog_rewrites_untyped_storage_thumb_to_category_folder():
    """Legacy products/{slug}/… URLs 400 after move under products/{category}/…."""
    from app.catalog import build_catalog_product_lite

    base = "https://abc123.supabase.co/storage/v1/object/public/shop-media"
    untyped = f"{base}/products/imprint-necklace/white/a605.png"
    typed = f"{base}/products/pendant/imprint-necklace/white/a605.png"
    product = {
        "id": "c54963cb-7c3d-469e-b26d-ae4372870445",
        "category": "pendant",
        "name_zh": "銘印單鑽項鍊",
        "name_en": None,
        "default_color": "white",
        "sort_order": 0,
        "is_published": True,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }
    images = [
        {"color": "white-white", "file_path": untyped, "sort_order": 0},
        {"color": "white-white", "file_path": typed, "sort_order": 1},
    ]
    entry = build_catalog_product_lite(product, [], images)
    assert entry["thumbUrl"] == typed
    assert "/products/imprint-necklace/" not in (entry["thumbUrl"] or "")


def test_build_catalog_prefers_majority_storage_folder_for_thumb():
    """Collision-slug folder used by other slots beats orphan untyped rewrite."""
    from app.catalog import build_catalog_product_lite

    base = "https://abc123.supabase.co/storage/v1/object/public/shop-media"
    orphan = f"{base}/products/pendant/four-prong-solitaire-necklace/white/a.png"
    keep = (
        f"{base}/products/pendant/four-prong-solitaire-necklace-408642ff/white/a.png"
    )
    product = {
        "id": "c54963cb-7c3d-469e-b26d-ae4372870445",
        "category": "pendant",
        "name_zh": "四爪單鑽項鍊",
        "name_en": None,
        "default_color": "white",
        "sort_order": 0,
        "is_published": True,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }
    images = [
        {"color": "white-white", "file_path": orphan, "sort_order": 0},
        {"color": "white-white", "file_path": keep, "sort_order": 0},
        {
            "color": "yellow-white",
            "file_path": (
                f"{base}/products/pendant/"
                "four-prong-solitaire-necklace-408642ff/yellow/b.png"
            ),
            "sort_order": 1,
        },
    ]
    entry = build_catalog_product_lite(product, [], images)
    assert entry["thumbUrl"] == keep


def test_build_catalog_drops_pending_autosave_urls():
    """Temp Storage _pending paths must not appear in shop catalog."""
    from app.catalog import build_catalog_product_lite

    product = {
        "id": "11ff6e28-31cd-491b-8a75-16da9c333ed3",
        "category": "bracelet",
        "name_zh": "泡泡手鍊",
        "name_en": "Bubble Bracelet",
        "default_color": "white",
        "sort_order": 0,
        "is_published": True,
        "allows_engraving": True,
        "allows_fancy_shapes": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }
    pending = (
        "https://x.supabase.co/storage/v1/object/public/shop-media/"
        "products/_pending/a5ce2ca51cb145ed8fa874ff47095ab8.png"
    )
    good = (
        "https://x.supabase.co/storage/v1/object/public/shop-media/"
        "products/bracelet/bubble-bracelet/yellow/23274bf09a66468fb57642f44b93e602.png"
    )
    images = [
        {"color": "white-white", "file_path": pending},
        {"color": "yellow-white", "file_path": good},
    ]
    entry = build_catalog_product_lite(product, [], images)
    assert pending not in (entry.get("thumbUrl") or "")
    assert entry["thumbUrl"] == good


def test_build_catalog_drops_missing_upload_without_style_fallback():
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

    assert entry["images"] == {}
    assert entry["styleKey"] is None


def test_build_catalog_drops_auto_stock_shop_product_paths():
    product = {
        "id": "c54963cb-7c3d-469e-b26d-ae4372870445",
        "category": "pendant",
        "name_zh": "測試",
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
            "file_path": "/static/images/shop-product/silver/%E9%A0%85%E5%A2%9CA_silver.png",
        }
    ]

    entry = build_catalog_product(product, [], images)

    assert entry["images"] == {}
    assert entry["styleKey"] is None


def test_build_catalog_empty_images_stay_empty_no_style_key():
    """New/empty products must not invent styleKey or shop-product slots."""
    product = {
        "id": "c54963cb-7c3d-469e-b26d-ae4372870445",
        "category": "pendant",
        "name_zh": "空白新品",
        "name_en": None,
        "description_zh": None,
        "description_en": None,
        "default_color": "white",
        "sort_order": 0,
        "is_published": False,
        "allows_engraving": True,
        "allows_pendant_only": True,
        "allows_with_chain": True,
    }

    entry = build_catalog_product(product, [], [])

    assert entry["images"] == {}
    assert entry["styleKey"] is None
    assert entry["colors"] == []


def test_style_key_ignores_shop_product_only_rows():
    """Stock letter paths must not mint styleKey (would re-invent shop images)."""
    from app.catalog import style_key_from_images

    assert (
        style_key_from_images(
            [
                {
                    "file_path": "/static/images/shop-product/silver/%E9%A0%85%E5%A2%9CA_silver.png",
                }
            ]
        )
        is None
    )
    assert (
        style_key_from_images(
            [{"file_path": "/static/images/products/white/pendant-A.png"}]
        )
        == "pendant-A"
    )
