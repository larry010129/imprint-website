#!/usr/bin/env python3
"""One-off: convert product_variants.weight_chin from per-metal成品重 to 蠟重(錢).

Derives wax from the 9K row when present: wax = metal_9k / 11.5.
Idempotent when all rows for (product_id, carat) already share the same weight.

Usage: python scripts/migrate_wax_weights.py
"""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

WAX_REFERENCE_GOLD = "9k"
WAX_TO_METAL_CHIN = {
    "9k": 11.5, "14k": 14.0, "18k": 16.0, "s925": 11.0, "pt950": 24.0,
}

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def wax_from_rows(rows: list[dict]) -> float | None:
    ref = WAX_TO_METAL_CHIN[WAX_REFERENCE_GOLD]
    for row in rows:
        if row["gold"] == WAX_REFERENCE_GOLD:
            return float(row["weight_chin"]) / ref
    row = rows[0]
    factor = WAX_TO_METAL_CHIN.get(row["gold"])
    if not factor:
        return None
    return float(row["weight_chin"]) / factor


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL not set")

    with psycopg.connect(url, row_factory=dict_row, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute("select product_id, gold, carat, weight_chin from product_variants order by product_id, carat, gold")
        all_rows = cur.fetchall()
        groups: dict[tuple, list] = defaultdict(list)
        for row in all_rows:
            groups[(row["product_id"], row["carat"])].append(row)

        updated = skipped = 0
        for key, rows in groups.items():
            weights = [round(float(r["weight_chin"]), 8) for r in rows]
            if len(set(weights)) == 1:
                skipped += len(rows)
                continue
            wax = wax_from_rows(rows)
            if wax is None or wax <= 0:
                print(f"  skip {key}: cannot derive wax")
                continue
            for row in rows:
                if abs(float(row["weight_chin"]) - wax) < 1e-8:
                    skipped += 1
                    continue
                cur.execute(
                    "update product_variants set weight_chin = %s where product_id = %s and gold = %s and carat = %s",
                    (wax, row["product_id"], row["gold"], row["carat"]),
                )
                updated += 1
        conn.commit()
        print(f"Done — {updated} rows updated, {skipped} unchanged/skipped.")


if __name__ == "__main__":
    main()
