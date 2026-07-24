"""Product category (品項) registry — dynamic tabs for admin and shop step-1 tiles."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from app.image_urls import resolve_product_image_url

DEFAULT_CATEGORIES: list[dict] = [
    {"slug": "pendant", "label_zh": "項墜", "label_en": "Pendant", "thumb_path": None, "sort_order": 0},
    {"slug": "ring", "label_zh": "戒指", "label_en": "Ring", "thumb_path": None, "sort_order": 1},
    {"slug": "earring", "label_zh": "耳環", "label_en": "Earring", "thumb_path": None, "sort_order": 2},
    {"slug": "bracelet", "label_zh": "手鍊", "label_en": "Bracelet", "thumb_path": None, "sort_order": 3},
    {"slug": "chain", "label_zh": "鏈條", "label_en": "Chain", "thumb_path": None, "sort_order": 4},
]

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")


def _serialize_row(row: dict) -> dict:
    out = dict(row)
    for key, value in out.items():
        if isinstance(value, datetime):
            out[key] = value.isoformat()
    thumb = out.get("thumb_path")
    out["thumbUrl"] = resolve_product_image_url(thumb) if thumb else None
    return out


def fetch_categories(cur) -> list[dict]:
    rows: list = []
    try:
        cur.execute(
            "select slug, label_zh, label_en, thumb_path, sort_order, created_at, updated_at "
            "from product_categories order by sort_order, slug"
        )
        rows = cur.fetchall()
    except Exception:
        rows = []
    if rows:
        return [_serialize_row(dict(row)) for row in rows]
    return [_serialize_row(dict(row)) for row in DEFAULT_CATEGORIES]


def category_labels(cur) -> dict[str, str]:
    return {row["slug"]: row["label_zh"] for row in fetch_categories(cur)}


def valid_category_slugs(cur) -> set[str]:
    return {row["slug"] for row in fetch_categories(cur)}


def category_order(cur) -> list[str]:
    return [row["slug"] for row in fetch_categories(cur)]


def build_category_meta(cur) -> dict[str, dict]:
    meta: dict[str, dict] = {}
    for row in fetch_categories(cur):
        meta[row["slug"]] = {
            "labelZh": row["label_zh"],
            "labelEn": row.get("label_en"),
            "thumbUrl": row.get("thumbUrl"),
        }
    return meta


def make_slug(label_zh: str, existing: set[str]) -> str:
    ascii_base = re.sub(r"[^a-z0-9]+", "-", (label_zh or "").lower()).strip("-")
    if len(ascii_base) >= 2 and ascii_base not in existing and _SLUG_RE.match(ascii_base):
        return ascii_base[:32]
    for _ in range(12):
        slug = f"cat-{uuid.uuid4().hex[:8]}"
        if slug not in existing:
            return slug
    raise ValueError("could not generate slug")


def create_category(cur, *, label_zh: str, label_en: str | None = None) -> tuple[dict | None, str | None]:
    label_zh = (label_zh or "").strip()
    if not label_zh:
        return None, "請填寫品項名稱"
    if len(label_zh) > 50:
        return None, "品項名稱過長"

    label_en = (label_en or "").strip() or None
    if label_en and len(label_en) > 80:
        return None, "英文名稱過長"

    existing = valid_category_slugs(cur)
    slug = make_slug(label_zh, existing)

    try:
        cur.execute("select coalesce(max(sort_order), -1) + 1 as next from product_categories")
        sort_order = int(cur.fetchone()["next"])
        cur.execute(
            """
            insert into product_categories (slug, label_zh, label_en, sort_order)
            values (%s, %s, %s, %s)
            returning slug, label_zh, label_en, thumb_path, sort_order, created_at, updated_at
            """,
            (slug, label_zh, label_en, sort_order),
        )
        return _serialize_row(dict(cur.fetchone())), None
    except Exception:
        return None, "新增品項失敗"


def update_category_thumb(cur, slug: str, thumb_path: str) -> tuple[dict | None, str | None]:
    slug = (slug or "").strip()
    if slug not in valid_category_slugs(cur):
        return None, "品項不存在"
    cur.execute(
        """
        update product_categories
        set thumb_path = %s, updated_at = %s
        where slug = %s
        returning slug, label_zh, label_en, thumb_path, sort_order, created_at, updated_at
        """,
        (thumb_path, datetime.now(timezone.utc), slug),
    )
    row = cur.fetchone()
    if not row:
        return None, "品項不存在"
    return _serialize_row(dict(row)), None
