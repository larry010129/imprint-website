"""Seed FAQ + testimonials when tables are empty."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.database import get_connection

log = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).resolve().parent / "data" / "content-seed.json"
_BANNERS_SEED = Path(__file__).resolve().parent / "data" / "banners-seed.json"


def seed_content_if_empty() -> int:
    created = 0
    created += _seed_faq_testimonials()
    created += _seed_banners()
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
            if t_count > 0 and f_count > 0:
                return 0

            data = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
            created = 0

            if t_count == 0:
                for entry in data.get("testimonials") or []:
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
                    created += 1

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
