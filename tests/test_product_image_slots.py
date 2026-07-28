from pathlib import Path
from urllib.parse import unquote

import pytest

from app.image_urls import catalog_image_slot_urls, shop_product_image_url
from app.seed_catalog import backfill_catalog_image_slots
from config.settings import settings


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
        assert image_url.startswith("/static/images/shop-product/")
        relative_path = Path(unquote(image_url.removeprefix("/static/")))
        assert (settings.static_dir / relative_path).is_file()


def test_missing_fancy_renders_use_same_product_originals():
    assert shop_product_image_url(
        "earring-A", "yellow", diamond_color="pink"
    ) == shop_product_image_url("earring-A", "yellow", diamond_color="white")
    assert shop_product_image_url(
        "bracelet-A", "rose", diamond_color="blue"
    ) == shop_product_image_url("bracelet-A", "rose", diamond_color="white")


def test_chain_b_rose_uses_the_rose_gold_photo():
    image_url = shop_product_image_url("chain-B", "rose", diamond_color="white")

    assert "/rose_gold/" in image_url
    assert image_url.endswith("_rose.png")
    assert "silver2" not in image_url


class _CatalogCursor:
    def __init__(self):
        self.rows = []
        self.updates = []
        self.inserts = []

    def execute(self, query, params=None):
        normalized = " ".join(query.split()).lower()
        if normalized.startswith("select id, category, name_zh"):
            self.rows = [
                {
                    "id": "product-1",
                    "category": "pendant",
                    "name_zh": "Pendant A",
                    "sort_order": 1,
                }
            ]
        elif normalized.startswith("select id, product_id, color"):
            self.rows = [
                {
                    "id": f"image-{index}",
                    "product_id": "product-1",
                    "color": color,
                    "file_path": f"/static/images/products/{color}/pendant-A.png",
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


def test_backfill_preserves_originals_and_populates_empty_slots():
    cursor = _CatalogCursor()

    normalized, inserted = backfill_catalog_image_slots(cursor, [])

    assert normalized == 3
    assert inserted == 45
    assert {color for color, _ in cursor.updates} == {
        "white-white",
        "yellow-white",
        "rose-white",
    }
    assert all(Path(unquote(path.removeprefix("/static/"))).suffix == ".png" for _, _, path, _ in cursor.inserts)
