#!/usr/bin/env python3
"""Push wax weights from catalog-seed-data buildSeedRows into product_variants.

Usage: node -e "console.log(JSON.stringify(require('./backend/lib/catalog-seed-data').buildSeedRows()))" > /tmp/rows.json
       python scripts/sync_wax_weights.py

Or run standalone after generating rows via subprocess.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def build_seed_rows() -> list[dict]:
    out = subprocess.check_output(
        ["node", "-e", "console.log(JSON.stringify(require('./backend/lib/catalog-seed-data').buildSeedRows()))"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )
    return json.loads(out)


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL not set")

    rows = build_seed_rows()
    updated = unchanged = missing = 0

    with psycopg.connect(url, row_factory=dict_row, autocommit=False) as conn, conn.cursor() as cur:
        for row in rows:
            cur.execute(
                "select id from products where category = %s and name_zh = %s",
                (row["category"], row["nameZh"]),
            )
            product = cur.fetchone()
            if not product:
                print(f"  ! no product: {row['category']}/{row['nameZh']}")
                missing += len(row["variants"])
                continue
            for v in row["variants"]:
                cur.execute(
                    """
                    select weight_chin from product_variants
                    where product_id = %s and gold = %s and carat = %s
                    """,
                    (product["id"], v["gold"], v["carat"]),
                )
                variant = cur.fetchone()
                if not variant:
                    missing += 1
                    continue
                new_wax = float(v["weightChin"])
                old_wax = float(variant["weight_chin"])
                if abs(old_wax - new_wax) < 1e-8:
                    unchanged += 1
                    continue
                cur.execute(
                    """
                    update product_variants set weight_chin = %s
                    where product_id = %s and gold = %s and carat = %s
                    """,
                    (new_wax, product["id"], v["gold"], v["carat"]),
                )
                print(f"  {row['category']}/{row['nameZh']}/{v['gold']}/{v['carat']}: {old_wax} -> {new_wax}")
                updated += 1
        conn.commit()

    print(f"Done — {updated} updated, {unchanged} unchanged, {missing} missing.")


if __name__ == "__main__":
    main()
