import pytest

from app.image_urls import catalog_image_slot_urls, shop_product_image_url
from app.seed_catalog import backfill_catalog_image_slots
from app.storage import site_image_public_url


@pytest.fixture(autouse=True)
def _shop_stills_storage(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://abc123.supabase.co")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "shop-media")


EXPECTED_SLOT_COUNTS = {
    "pendant-A": 48,
    "pendant-B": 48,
    "pendant-C": 48,
    "ring-A": 12,
    "ring-B": 12,
    "ring-C": 12,
    "earring-A": 12,
    "bracelet-A": 12,
    "bracelet-B": 12,
    "bracelet-C": 12,
    "chain-A": 3,
    "chain-B": 3,
    "chain-C": 3,
}


@pytest.mark.parametrize(("style_key", "expected"), EXPECTED_SLOT_COUNTS.items())
def test_every_catalog_slot_resolves_to_an_existing_image(style_key, expected):
    slots = catalog_image_slot_urls(style_key)

    assert len(slots) == expected
    for image_url in slots.values():
        assert "/storage/v1/object/public/shop-media/site-images/shop-product/" in image_url


def test_earring_yellow_fancy_uses_gold_fancy_renders():
    """Gold earring fancy must be gold-folder assets, not silver-metal copies."""
    for diamond in ("yellow", "blue", "pink"):
        image_url = shop_product_image_url("earring-A", "yellow", diamond_color=diamond)
        assert "/gold/" in image_url
        assert image_url == site_image_public_url(
            f"shop-product/gold/耳飾A_gold_{diamond}.png"
        )


def test_earring_rose_fancy_stays_in_rose_gold_folder():
    for diamond in ("yellow", "blue", "pink"):
        image_url = shop_product_image_url("earring-A", "rose", diamond_color=diamond)
        assert "/rose_gold/" in image_url
        assert image_url == site_image_public_url(
            f"shop-product/rose_gold/耳飾A_rose_{diamond}.png"
        )


def test_missing_fancy_renders_use_same_product_originals():
    # Bracelet still has no fancy-stone library files → same-metal white fallback.
    assert shop_product_image_url(
        "bracelet-A", "rose", diamond_color="blue"
    ) == shop_product_image_url("bracelet-A", "rose", diamond_color="white")


def test_chain_b_rose_uses_the_rose_gold_photo():
    image_url = shop_product_image_url("chain-B", "rose", diamond_color="white")

    assert "/rose_gold/" in image_url
    assert image_url == site_image_public_url("shop-product/rose_gold/斗圓鍊_rose.png")
    assert "silver2" not in image_url


class _CatalogCursor:
    def __init__(self):
        self.rows = []
        self.updates = []
        self.inserts = []
        self.deletes = []
        self.rowcount = 0

    def execute(self, query, params=None):
        normalized = " ".join(query.split()).lower()
        if normalized.startswith("delete from product_images"):
            self.deletes.append(params)
            self.rowcount = 0
        elif "from product_images" in normalized and "file_path" in normalized:
            self.rows = [
                {
                    "id": f"image-{index}",
                    "product_id": "product-1",
                    "color": color,
                    "file_path": f"/static/uploads/products/{color}.png",
                    "category": "ring",
                    "sort_order": index,
                }
                for index, color in enumerate(("white", "yellow", "rose"))
            ]
        elif normalized.startswith("update product_images"):
            self.updates.append(params)
        elif normalized.startswith("insert into product_images"):
            self.inserts.append(params)
        else:
            raise AssertionError(f"Unexpected query: {normalized}")

    def fetchall(self):
        return self.rows


def test_backfill_normalizes_legacy_keys_without_inventing_stock():
    cursor = _CatalogCursor()

    normalized, inserted = backfill_catalog_image_slots(cursor, [])

    assert normalized == 3
    assert inserted == 0
    assert cursor.inserts == []
    assert {color for color, _ in cursor.updates} == {
        "white-white",
        "yellow-white",
        "rose-white",
    }


class _MissingImageCursor(_CatalogCursor):
    def execute(self, query, params=None):
        normalized = " ".join(query.split()).lower()
        if normalized.startswith("delete from product_images"):
            self.deletes.append(params)
            self.rowcount = 0
        elif "from product_images" in normalized and "file_path" in normalized:
            self.rows = [
                {
                    "id": "image-dead",
                    "product_id": "product-1",
                    "color": "white-white",
                    "file_path": "/static/uploads/products/test.png",
                    "category": "ring",
                    "sort_order": 0,
                }
            ]
        elif normalized.startswith("update product_images"):
            self.updates.append(params)
        elif normalized.startswith("insert into product_images"):
            self.inserts.append(params)
        else:
            raise AssertionError(f"Unexpected query: {normalized}")


def test_backfill_does_not_replace_missing_upload_with_stock():
    cursor = _MissingImageCursor()

    normalized, inserted = backfill_catalog_image_slots(cursor, [])

    assert inserted == 0
    assert cursor.inserts == []
    assert not any(
        str(params[0]).startswith("/static/images/shop-product/")
        for params in cursor.updates
        if params
    )
    # Missing upload stays; only SVG / shop-product stock are removed.
    assert all(
        params != ("image-dead",)
        for params in cursor.deletes
        if params
    )
