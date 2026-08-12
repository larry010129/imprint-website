"""Assign ring/necklace testimonial images (11:5) from presets + generated."""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "app" / "data" / "content-seed.json"
PUBLIC = ROOT / "public"

# 11 rings : 5 necklaces — shop presets + generated (not shop-product paths)
RINGS = [
    "/static/images/testimonials/presets/ring-A.webp",
    "/static/images/testimonials/presets/ring-B.webp",
    "/static/images/testimonials/presets/ring-C.webp",
    "/static/images/testimonials/testimonial-ring-01.webp",
    "/static/images/testimonials/testimonial-ring-02.webp",
    "/static/images/testimonials/testimonial-ring-03.webp",
    "/static/images/testimonials/testimonial-ring-04.webp",
    "/static/images/testimonials/testimonial-ring-05.webp",
    "/static/images/testimonials/testimonial-ring-06.webp",
    "/static/images/testimonials/testimonial-ring-07.webp",
    "/static/images/testimonials/testimonial-ring-08.webp",
]
NECKLACES = [
    "/static/images/testimonials/presets/pendant-A.webp",
    "/static/images/testimonials/presets/pendant-B.webp",
    "/static/images/testimonials/presets/pendant-C.webp",
    "/static/images/testimonials/testimonial-pendant-01.webp",
    "/static/images/testimonials/testimonial-pendant-02.webp",
]

# Prefer necklace for wear/pendant stories
NECKLACE_SORT = {5, 10, 11, 13, 16}


def main() -> None:
    for url in RINGS + NECKLACES:
        fp = PUBLIC / url.replace("/static/", "")
        if not fp.is_file():
            raise SystemExit(f"missing {url}")
    assert len(RINGS) == 11 and len(NECKLACES) == 5
    assert len(set(RINGS + NECKLACES)) == 16

    data = json.loads(SEED.read_text(encoding="utf-8"))
    testimonials = sorted(data["testimonials"], key=lambda x: int(x.get("sort_order") or 0))
    ring_i = neck_i = 0
    for t in testimonials:
        so = int(t.get("sort_order") or 0)
        if so in NECKLACE_SORT:
            t["image_url"] = NECKLACES[neck_i]
            neck_i += 1
        else:
            t["image_url"] = RINGS[ring_i]
            ring_i += 1
    assert ring_i == 11 and neck_i == 5
    data["testimonials"] = testimonials
    SEED.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    load_dotenv()
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn, conn.cursor() as cur:
        for t in testimonials:
            cur.execute(
                """
                update testimonials
                set image_url = %s, updated_at = now()
                where name = %s and sort_order = %s
                """,
                (t["image_url"], t["name"], int(t["sort_order"])),
            )
        cur.execute(
            """
            select count(*)::int as c,
                   count(distinct image_url)::int as uniq,
                   count(*) filter (where image_url like '%/shop-product/%' or image_url like '%/products/%')::int as shop_raw
            from testimonials
            """
        )
        print(cur.fetchone())
        conn.commit()

    # Live UI reads Postgres only — do not regenerate frontend seed arrays.
    print("ok rings", ring_i, "necks", neck_i, "(DB only; no testimonials.ts write)")


if __name__ == "__main__":
    main()
