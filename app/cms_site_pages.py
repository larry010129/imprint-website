"""Indexed fixed-route CMS page lookups."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from uuid import uuid4

from app.cms_boundary import assert_content_page_key, validate_cms_slug


def _serialize_page(row: dict) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    for key in ("created_at", "updated_at"):
        value = out.get(key)
        if isinstance(value, datetime):
            out[key] = value.isoformat()
    return out


def _invalidate_public_cache() -> None:
    from app.controllers.web_controller import clear_site_cms_cache

    clear_site_cms_cache()


def site_route_to_slug(route: str) -> str:
    key = str(route or "").strip()
    if key == "/":
        return "site-home"
    cleaned = re.sub(r"[^a-z0-9]+", "-", key.strip("/").lower()).strip("-")
    base = f"site-{cleaned}" if cleaned else ""
    if base and len(base) <= 63:
        slug, err = validate_cms_slug(base)
        if slug and not err:
            return slug
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return f"site-{digest}"


def page_key_for_cms_page(page: dict) -> str:
    route = str(page.get("site_route") or "").strip()
    if route:
        return route
    slug = str(page.get("slug") or "").strip()
    return f"/p/{slug}" if slug else ""


def fetch_page_by_site_route(cur, route: str) -> dict | None:
    cur.execute("select * from cms_pages where site_route = %s", (route,))
    row = cur.fetchone()
    return _serialize_page(row) if row else None


def ensure_site_route_page(cur, route: str, title: str | None = None) -> dict:
    from app.cms_copy_slot_specs import EDITABLE_SITE_PAGES

    page_key, key_err = assert_content_page_key(route)
    if key_err or not page_key:
        raise ValueError(key_err or "route 無效")
    title_map = {item["route"]: item["title"] for item in EDITABLE_SITE_PAGES}
    if page_key not in title_map:
        raise ValueError("此 route 非可編輯官網頁面")
    page_title = (title or title_map[page_key]).strip() or title_map[page_key]

    existing = fetch_page_by_site_route(cur, page_key)
    if existing:
        if existing.get("status") != "published":
            cur.execute(
                """
                update cms_pages set status = %s, updated_at = now()
                where id = %s returning *
                """,
                ("published", existing["id"]),
            )
            page = _serialize_page(cur.fetchone())
            _invalidate_public_cache()
            return page
        return existing

    slug = site_route_to_slug(page_key)
    cur.execute("select id from cms_pages where slug = %s", (slug,))
    if cur.fetchone():
        digest = hashlib.sha1(page_key.encode("utf-8")).hexdigest()[:8]
        slug = f"{slug[:54]}-{digest}"
    try:
        cur.execute(
            """
            insert into cms_pages (id, slug, title, meta_description, status, site_route)
            values (%s, %s, %s, %s, 'published', %s)
            returning *
            """,
            (str(uuid4()), slug, page_title, "", page_key),
        )
    except Exception as exc:
        if "unique" not in str(exc).lower() and "duplicate" not in str(exc).lower():
            raise
        existing = fetch_page_by_site_route(cur, page_key)
        if existing:
            return existing
        raise
    page = _serialize_page(cur.fetchone())
    _invalidate_public_cache()
    return page
