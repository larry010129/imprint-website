"""Seed FAQ + testimonials when tables are empty."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.database import get_connection

log = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).resolve().parent / "data" / "content-seed.json"
_BANNERS_SEED = Path(__file__).resolve().parent / "data" / "banners-seed.json"

# Legacy homepage social-proof names (imprint-diamond.com/imprint/index).
_LEGACY_HOMEPAGE_TESTIMONIAL_NAMES = frozenset(
    {
        "沈小姐",
        "徐小姐",
        "賴先生",
        "朱小姐",
        "張小姐",
        "吳小姐",
        "陳先生",
        "簡小姐",
    }
)


def seed_content_if_empty() -> int:
    created = 0
    created += _seed_faq_testimonials()
    created += _seed_banners()
    created += _seed_page_images()
    return created


def _insert_testimonial(cur, entry: dict) -> None:
    cur.execute(
        """
        insert into testimonials (
          name, role, category, city, text, image_url, rating, sort_order, is_published
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, true)
        """,
        (
            entry["name"],
            entry.get("role") or "",
            entry.get("category") or "",
            entry.get("city") or "",
            entry["text"],
            entry.get("image_url") or "",
            int(entry.get("rating") or 5),
            int(entry.get("sort_order") or 0),
        ),
    )


def _ensure_legacy_homepage_testimonials(cur, data: dict) -> int:
    """Insert any of the 8 legacy homepage quotes missing by name."""
    created = 0
    for entry in data.get("testimonials") or []:
        name = str(entry.get("name") or "").strip()
        if name not in _LEGACY_HOMEPAGE_TESTIMONIAL_NAMES:
            continue
        cur.execute(
            "select 1 from testimonials where name = %s limit 1",
            (name,),
        )
        if cur.fetchone():
            continue
        _insert_testimonial(cur, entry)
        created += 1
    return created


def _seed_faq_testimonials() -> int:
    if not _SEED_PATH.is_file():
        log.warning("content seed file missing: %s", _SEED_PATH)
        return 0

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select to_regclass('public.testimonials') as t,
                       to_regclass('public.faq_categories') as c
                """
            )
            reg = cur.fetchone() or {}
            if not reg.get("t") or not reg.get("c"):
                log.warning("content tables missing — run migration first")
                return 0

            cur.execute("select count(*)::int as count from testimonials")
            t_count = (cur.fetchone() or {}).get("count") or 0
            cur.execute("select count(*)::int as count from faq_items")
            f_count = (cur.fetchone() or {}).get("count") or 0

            data = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
            created = 0

            if t_count == 0:
                for entry in data.get("testimonials") or []:
                    _insert_testimonial(cur, entry)
                    created += 1
            else:
                created += _ensure_legacy_homepage_testimonials(cur, data)

            if f_count == 0:
                for cat in data.get("faq_categories") or []:
                    cur.execute(
                        """
                        insert into faq_categories (id, title, sort_order)
                        values (%s, %s, %s)
                        on conflict (id) do nothing
                        """,
                        (cat["id"], cat["title"], int(cat.get("sort_order") or 0)),
                    )
                for item in data.get("faq_items") or []:
                    cur.execute(
                        """
                        insert into faq_items (
                          id, category_id, question, answer, sort_order,
                          is_published, show_in_teaser
                        ) values (%s, %s, %s, %s, %s, true, %s)
                        on conflict (id) do nothing
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
                    created += 1

            if created:
                log.info("seeded %s content rows", created)
            return created
    except Exception:
        log.exception("content seed failed")
        return 0


def _seed_banners() -> int:
    if not _BANNERS_SEED.is_file():
        return 0
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select to_regclass('public.home_banners') as t")
            if not (cur.fetchone() or {}).get("t"):
                return 0
            cur.execute("select count(*)::int as count from home_banners")
            if (cur.fetchone() or {}).get("count"):
                return 0
            rows = json.loads(_BANNERS_SEED.read_text(encoding="utf-8"))
            created = 0
            for entry in rows:
                cur.execute(
                    """
                    insert into home_banners (
                      eyebrow, title, lead, image_url, image_webp, image_alt,
                      cta_primary_label, cta_primary_href,
                      cta_secondary_label, cta_secondary_href,
                      tone, sort_order, is_published
                    ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true)
                    """,
                    (
                        entry.get("eyebrow") or "",
                        entry["title"],
                        entry.get("lead") or "",
                        entry["image_url"],
                        entry.get("image_webp"),
                        entry.get("image_alt") or "",
                        entry.get("cta_primary_label") or "",
                        entry.get("cta_primary_href") or "",
                        entry.get("cta_secondary_label") or "",
                        entry.get("cta_secondary_href") or "",
                        entry.get("tone") or "warm",
                        int(entry.get("sort_order") or 0),
                    ),
                )
                created += 1
            if created:
                log.info("seeded %s home banners", created)
            return created
    except Exception:
        log.exception("banner seed failed")
        return 0


def _seed_page_images() -> int:
    try:
        from app.content import ensure_page_images_schema
        from app.page_image_slots import build_page_image_seed

        with get_connection() as conn, conn.cursor() as cur:
            ensure_page_images_schema(cur)
            rows = build_page_image_seed()
            registry = [
                {"page_key": row["page_key"], "slot_key": row["slot_key"]} for row in rows
            ]
            cur.execute(
                """
                delete from page_images
                where not exists (
                  select 1
                  from jsonb_to_recordset(%s::jsonb) as slot(page_key text, slot_key text)
                  where slot.page_key = page_images.page_key
                    and slot.slot_key = page_images.slot_key
                )
                """,
                (json.dumps(registry),),
            )
            created = 0
            for entry in rows:
                cur.execute(
                    """
                    insert into page_images (
                      page_key, slot_key, label, slot_label, group_key,
                      image_url, image_webp, image_alt,
                      default_image_url, default_image_webp,
                      target_w, target_h, sort_order, is_published
                    ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true)
                    on conflict (page_key, slot_key) do update set
                      label = excluded.label,
                      slot_label = excluded.slot_label,
                      group_key = excluded.group_key,
                      default_image_url = excluded.default_image_url,
                      default_image_webp = excluded.default_image_webp,
                      target_w = excluded.target_w,
                      target_h = excluded.target_h,
                      sort_order = excluded.sort_order
                    """,
                    (
                        entry["page_key"],
                        entry["slot_key"],
                        entry["label"],
                        entry["slot_label"],
                        entry["group_key"],
                        entry["image_url"],
                        entry.get("image_webp"),
                        entry.get("image_alt") or "",
                        entry["default_image_url"],
                        entry.get("default_image_webp"),
                        entry["target_w"],
                        entry["target_h"],
                        entry["sort_order"],
                    ),
                )
                created += 1
            if created:
                log.info("seeded %s page images", created)
            return created
    except Exception:
        log.exception("page images seed failed")
        return 0
