"""Content CMS helpers — FAQ + testimonials + home banners."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


def serialize_testimonial(row: dict) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    if "is_published" in out:
        out["is_published"] = bool(out["is_published"])
    if out.get("rating") is not None:
        out["rating"] = int(out["rating"])
    if out.get("sort_order") is not None:
        out["sort_order"] = int(out["sort_order"])
    return out


def serialize_faq_category(row: dict) -> dict:
    out = dict(row)
    if out.get("sort_order") is not None:
        out["sort_order"] = int(out["sort_order"])
    return out


def serialize_faq_item(row: dict) -> dict:
    out = dict(row)
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    for key in ("is_published", "show_in_teaser"):
        if key in out:
            out[key] = bool(out[key])
    if out.get("sort_order") is not None:
        out["sort_order"] = int(out["sort_order"])
    return out


def fetch_published_testimonials(cur) -> list[dict]:
    cur.execute(
        """
        select * from testimonials
        where is_published = true
        order by sort_order asc, created_at asc
        """
    )
    return [serialize_testimonial(r) for r in cur.fetchall()]


def fetch_all_testimonials(cur) -> list[dict]:
    cur.execute("select * from testimonials order by sort_order asc, created_at asc")
    return [serialize_testimonial(r) for r in cur.fetchall()]


def fetch_faq_public(cur) -> dict[str, Any]:
    cur.execute("select * from faq_categories order by sort_order asc, id asc")
    categories = [serialize_faq_category(r) for r in cur.fetchall()]
    cur.execute(
        """
        select * from faq_items
        where is_published = true
        order by sort_order asc, id asc
        """
    )
    items = [serialize_faq_item(r) for r in cur.fetchall()]
    by_cat: dict[str, list] = {c["id"]: [] for c in categories}
    for item in items:
        by_cat.setdefault(item["category_id"], []).append(item)
    nested = []
    for cat in categories:
        cat_items = by_cat.get(cat["id"]) or []
        if not cat_items:
            continue
        nested.append(
            {
                "id": cat["id"],
                "title": cat["title"],
                "items": [
                    {"id": i["id"], "question": i["question"], "answer": i["answer"]}
                    for i in cat_items
                ],
            }
        )
    teaser = [
        {"id": i["id"], "question": i["question"], "answer": i["answer"]}
        for i in items
        if i.get("show_in_teaser")
    ]
    return {"categories": nested, "teaser": teaser, "items": items}


def fetch_faq_admin(cur) -> dict[str, Any]:
    cur.execute("select * from faq_categories order by sort_order asc, id asc")
    categories = [serialize_faq_category(r) for r in cur.fetchall()]
    cur.execute("select * from faq_items order by sort_order asc, id asc")
    items = [serialize_faq_item(r) for r in cur.fetchall()]
    return {"categories": categories, "items": items}


def new_faq_id(prefix: str = "faq") -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def serialize_banner(row: dict) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    if "is_published" in out:
        out["is_published"] = bool(out["is_published"])
    if out.get("sort_order") is not None:
        out["sort_order"] = int(out["sort_order"])
    return out


def fetch_published_banners(cur) -> list[dict]:
    cur.execute(
        """
        select * from home_banners
        where is_published = true
        order by sort_order asc, created_at asc
        """
    )
    return [serialize_banner(r) for r in cur.fetchall()]


def fetch_all_banners(cur) -> list[dict]:
    cur.execute("select * from home_banners order by sort_order asc, created_at asc")
    return [serialize_banner(r) for r in cur.fetchall()]
