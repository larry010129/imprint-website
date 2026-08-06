"""Seed published catalog rows when the products table is empty (Render / fresh DB)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.database import get_connection, get_transaction
from app.admin_products import is_auto_stock_product_image, is_dead_catalog_placeholder, purge_auto_stock_product_images
from app.memorial_diamonds import ensure_memorial_diamond_products

log = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).resolve().parent / "data" / "catalog-seed-rows.json"
_LEGACY_METALS = frozenset({"white", "yellow", "rose"})


def backfill_catalog_image_slots(cur, seed_rows: list[dict]) -> tuple[int, int]:
    """Normalize legacy color keys only. Never invent shop-product letter SKU photos."""
    del seed_rows  # unused — style matrix backfill removed by design
    purged = purge_auto_stock_product_images(cur)

    cur.execute(
        """
        select id, product_id, color, file_path
        from product_images
        order by product_id, sort_order, id
        """
    )
    images = cur.fetchall()
    if not images and not purged:
        return (0, 0)

    normalized = 0
    for image in images:
        color = str(image.get("color") or "")
        path = image.get("file_path")
        if is_auto_stock_product_image(path):
            continue
        if color in _LEGACY_METALS:
            cur.execute(
                "update product_images set color = %s where id = %s",
                (f"{color}-white", image["id"]),
            )
            normalized += 1
        # Drop SVG placeholders only — never replace with shop-product stock.
        if is_dead_catalog_placeholder(path):
            cur.execute("delete from product_images where id = %s", (image["id"],))
            normalized += 1

    return normalized, 0


def seed_catalog_if_empty() -> int:
    rows: list[dict] = []
    if _SEED_PATH.is_file():
        rows = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    else:
        log.warning("catalog seed file missing: %s", _SEED_PATH)

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select count(*)::int as count from products")
            row = cur.fetchone()
            created = 0
            if not row or row["count"] == 0:
                for entry in rows:
                    cur.execute(
                        """
                        insert into products (
                          category, name_zh, default_color, is_published,
                          first_published_at, sort_order
                        ) values (%s, %s, %s, true, now(), %s)
                        returning id
                        """,
                        (
                            entry["category"],
                            entry["nameZh"],
                            entry.get("defaultColor") or "white",
                            entry.get("sortOrder", 0),
                        ),
                    )
                    product = cur.fetchone()
                    product_id = product["id"]

                    for variant in entry.get("variants") or []:
                        cur.execute(
                            """
                            insert into product_variants (product_id, gold, carat, weight_chin)
                            values (%s, %s, %s, %s)
                            """,
                            (
                                product_id,
                                variant["gold"],
                                variant["carat"],
                                float(variant["weightChin"]),
                            ),
                        )

                    for image in entry.get("images") or []:
                        file_path = image["filePath"]
                        # Never seed letter-SKU / SVG placeholders as product photos.
                        if str(file_path).lower().endswith(".svg"):
                            continue
                        if is_auto_stock_product_image(file_path):
                            continue
                        cur.execute(
                            """
                            insert into product_images (product_id, color, file_path, sort_order)
                            values (%s, %s, %s, 0)
                            """,
                            (product_id, image["color"], file_path),
                        )

                    created += 1
                    log.info(
                        "seeded catalog product: %s %s",
                        entry["category"],
                        entry.get("nameZh"),
                    )

            normalized, inserted = backfill_catalog_image_slots(cur, rows)
            if normalized or inserted:
                log.info(
                    "catalog images synchronized — %s legacy key(s), %s slot(s) added",
                    normalized,
                    inserted,
                )

            if created:
                log.info("catalog seed complete — %s product(s)", created)
            return created
    except Exception:
        log.exception("catalog seed failed")
        return 0


def seed_memorial_diamond_products() -> int:
    """Idempotent: four gem-color rows + shape matrix images (紀念鑽石 admin tab)."""
    try:
        with get_transaction() as conn, conn.cursor() as cur:
            inserted = ensure_memorial_diamond_products(cur)
            if inserted:
                log.info("memorial diamond seed — inserted %s color product(s)", inserted)
            return inserted
    except Exception:
        log.exception("memorial diamond seed failed")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    n = seed_catalog_if_empty()
    m = seed_memorial_diamond_products()
    print(f"seeded {n} jewelry product(s), {m} memorial diamond color(s)")
