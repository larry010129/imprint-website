#!/usr/bin/env python3
"""Re-seed FAQ tables from content-seed.json (fixes mojibake)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "app" / "data" / "content-seed.json"

load_dotenv(ROOT / ".env")


def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is not set")
    data = json.loads(SEED.read_text(encoding="utf-8"))
    sample_q = data["faq_items"][0]["question"]
    if "ç" in sample_q or "為什麼" not in sample_q:
        raise SystemExit(f"seed still looks wrong: {sample_q!r} — run build_content_seed.py first")

    with psycopg.connect(dsn, row_factory=dict_row, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("delete from faq_items")
            cur.execute("delete from faq_categories")
            for cat in data["faq_categories"]:
                cur.execute(
                    "insert into faq_categories (id, title, sort_order) values (%s, %s, %s)",
                    (cat["id"], cat["title"], int(cat.get("sort_order") or 0)),
                )
            for item in data["faq_items"]:
                cur.execute(
                    """
                    insert into faq_items (
                      id, category_id, question, answer, sort_order,
                      is_published, show_in_teaser
                    ) values (%s, %s, %s, %s, %s, true, %s)
                    """,
                    (
                        item["id"],
                        item["category_id"],
                        item["question"],
                        item["answer"],
                        int(item.get("sort_order") or 0),
                        bool(item.get("show_in_teaser")),
                    ),
                )
            cur.execute("select question from faq_items where id = %s", ("brand-why",))
            row = cur.fetchone()
            print("reseeded faq_items:", len(data["faq_items"]))
            print("brand-why:", row["question"] if row else None)


if __name__ == "__main__":
    main()
