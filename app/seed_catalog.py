"""Seed published catalog rows when the products table is empty (Render / fresh DB)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.database import get_connection
from app.image_urls import catalog_image_slot_urls, style_key_from_path

log = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).resolve().parent / "data" / "catalog-seed-rows.json"
_LEGACY_METALS = frozenset({"white", "yellow", "rose"})


def _seed_style_lookup(rows: list[dict]) -> dict[tuple[str, str], str]:
    return {
        (str(row.get("category") or ""), str(row.get("nameZh") or "")): (
            f"{row['category']}-{row['style']}"
        )
        for row in rows
        if row.get("category") and row.get("style") and row.get("nameZh")
    }


def _product_style_key(
    product: dict,
    images: list[dict],
    seed_styles: dict[tuple[str, str], str],
) -> str | None:
    for image in images:
        style_key = style_key_from_path(image.get("file_path"))
        if style_key:
            return style_key
    return seed_styles.get(
        (str(product.get("category") or ""), str(product.get("name_zh") or ""))
    )


def backfill_catalog_image_slots(cur, seed_rows: list[dict]) -> tuple[int, int]:
    """Normalize legacy image keys and add the canonical CMS image matrix."""
    cur.execute(
        "select id, category, name_zh, sort_order from products order by category, sort_order"
    )
    products = cur.fetchall()
    if not products:
        return (0, 0)

    cur.execute(
        """
        select id, product_id, color, file_path, sort_order
        from product_images
        order by product_id, sort_order, id
        """
    )
    by_product: dict[str, list[dict]] = {}
    for image in cur.fetchall():
        by_product.setdefault(str(image["product_id"]), []).append(image)

    seed_styles = _seed_style_lookup(seed_rows)
    normalized = 0
    inserted = 0
    for product in products:
        product_id = str(product["id"])
        images = by_product.get(product_id, [])
        style_key = _product_style_key(product, images, seed_styles)
        desired = catalog_image_slot_urls(style_key)
        if not desired:
            continue

        existing_keys: set[str] = set()
        next_sort = 0
        for image in images:
            color = str(image.get("color") or "")
            next_sort = max(next_sort, int(image.get("sort_order") or 0) + 1)
            if color in _LEGACY_METALS:
                color = f"{color}-white"
                cur.execute(
                    "update product_images set color = %s where id = %s",
                    (color, image["id"]),
                )
                normalized += 1
            existing_keys.add(color)

        for color, file_path in desired.items():
            if color in existing_keys:
                continue
            cur.execute(
                """
                insert into product_images (product_id, color, file_path, sort_order)
                values (%s, %s, %s, %s)
                """,
                (product["id"], color, file_path, next_sort),
            )
            next_sort += 1
            existing_keys.add(color)
            inserted += 1

    return normalized, inserted


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
                        if str(file_path).lower().endswith(".svg"):
                            file_path = (
                                f"/static/images/products/{image['color']}/"
                                f"{entry['category']}-{entry['style']}.png"
                            )
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    n = seed_catalog_if_empty()
    print(f"seeded {n} product(s)")
