"""product_images.updated_at for thumb cache-busting."""

from __future__ import annotations

from datetime import datetime, timezone

from app.admin_products import (
    ensure_product_images_updated_at_column,
    serialize_product_image,
)


def test_serialize_product_image_exposes_iso_updated_at():
    stamp = datetime(2026, 8, 12, 4, 5, 6, tzinfo=timezone.utc)
    row = serialize_product_image(
        {
            "id": "img-1",
            "product_id": "prod-1",
            "color": "white",
            "file_path": "/static/a.webp",
            "sort_order": 0,
            "previous_file_path": None,
            "updated_at": stamp,
        }
    )
    assert row is not None
    assert row["id"] == "img-1"
    assert row["updated_at"] == stamp.isoformat()


def test_ensure_product_images_updated_at_column_sql():
    statements: list[str] = []

    class Cur:
        def execute(self, query, params=None):
            statements.append(" ".join(str(query).split()).lower())

    ensure_product_images_updated_at_column(Cur())
    assert any(
        "add column if not exists updated_at" in sql for sql in statements
    )
