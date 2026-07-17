"""Seed published catalog rows when the products table is empty (Render / fresh DB)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.database import get_connection

log = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).resolve().parent / "data" / "catalog-seed-rows.json"


def seed_catalog_if_empty() -> int:
    if not _SEED_PATH.is_file():
        log.warning("catalog seed file missing: %s", _SEED_PATH)
        return 0

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select count(*)::int as count from products")
            row = cur.fetchone()
            if row and row["count"] > 0:
                return 0

            rows = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
            created = 0
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
                    cur.execute(
                        """
                        insert into product_images (product_id, color, file_path, sort_order)
                        values (%s, %s, %s, 0)
                        """,
                        (product_id, image["color"], image["filePath"]),
                    )

                created += 1
                log.info("seeded catalog product: %s %s", entry["category"], entry.get("nameZh"))

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
