"""Audit image URL columns: cloud vs local vs other."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.database import get_connection
from app.storage import is_supabase_storage_url, local_upload_to_object_key

COLS = [
    ("product_images", "file_path"),
    ("product_categories", "thumb_path"),
    ("home_banners", "image_url"),
    ("home_banners", "image_url_mobile"),
    ("home_banners", "image_webp"),
    ("testimonials", "image_url"),
    ("page_images", "image_url"),
    ("page_images", "image_webp"),
    ("page_images", "default_image_url"),
    ("page_images", "default_image_webp"),
    ("cms_media", "url"),
]


def main() -> None:
    with get_connection() as conn, conn.cursor() as cur:
        for table, column in COLS:
            cur.execute(
                """
                select count(*) as c from information_schema.columns
                where table_schema = 'public' and table_name = %s and column_name = %s
                """,
                (table, column),
            )
            if not int(cur.fetchone()["c"]):
                print(f"{table}.{column}: (no column)")
                continue
            cur.execute(
                f"select {column} as v from {table} "
                f"where {column} is not null and btrim({column}) <> ''"
            )
            rows = [r["v"] for r in cur.fetchall()]
            cloud = sum(1 for v in rows if is_supabase_storage_url(v))
            local = sum(1 for v in rows if local_upload_to_object_key(str(v)))
            other = len(rows) - cloud - local
            print(
                f"{table}.{column}: total={len(rows)} cloud={cloud} "
                f"local_upload={local} other={other}"
            )
            for v in rows[:5]:
                s = str(v)
                print(f"  {s[:120]}{'...' if len(s) > 120 else ''}")


if __name__ == "__main__":
    main()
