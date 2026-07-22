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
    "/static/images/testimonials/presets/ring-A.jpg",
    "/static/images/testimonials/presets/ring-B.jpg",
    "/static/images/testimonials/presets/ring-C.jpg",
    "/static/images/testimonials/testimonial-ring-01.jpg",
    "/static/images/testimonials/testimonial-ring-02.jpg",
    "/static/images/testimonials/testimonial-ring-03.jpg",
    "/static/images/testimonials/testimonial-ring-04.jpg",
    "/static/images/testimonials/testimonial-ring-05.jpg",
    "/static/images/testimonials/testimonial-ring-06.jpg",
    "/static/images/testimonials/testimonial-ring-07.jpg",
    "/static/images/testimonials/testimonial-ring-08.jpg",
]
NECKLACES = [
    "/static/images/testimonials/presets/pendant-A.jpg",
    "/static/images/testimonials/presets/pendant-B.jpg",
    "/static/images/testimonials/presets/pendant-C.jpg",
    "/static/images/testimonials/testimonial-pendant-01.jpg",
    "/static/images/testimonials/testimonial-pendant-02.jpg",
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

    items = []
    for t in testimonials:
        items.append(
            "  {\n"
            f'    id: {int(t["sort_order"])},\n'
            f'    name: {json.dumps(t["name"], ensure_ascii=False)},\n'
            f'    role: {json.dumps(t["role"], ensure_ascii=False)},\n'
            f'    category: {json.dumps(t["category"], ensure_ascii=False)},\n'
            f'    city: {json.dumps(t["city"], ensure_ascii=False)},\n'
            f'    text: {json.dumps(t["text"], ensure_ascii=False)},\n'
            f'    rating: {int(t["rating"])},\n'
            f'    image: {json.dumps(t["image_url"], ensure_ascii=False)},\n'
            "  }"
        )
    out = (
        "export type Testimonial = {\n"
        "  id: number;\n"
        "  name: string;\n"
        "  role: string;\n"
        "  text: string;\n"
        "  rating: number;\n"
        "  category: string;\n"
        "  city: string;\n"
        "  image?: string;\n"
        "};\n\n"
        "export const TESTIMONIALS: Testimonial[] = [\n"
        + ",\n".join(items)
        + "\n];\n"
    )
    (ROOT / "frontend/src/data/testimonials.ts").write_text(out, encoding="utf-8")
    print("ok rings", ring_i, "necks", neck_i)


if __name__ == "__main__":
    main()
