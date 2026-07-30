"""Modular CMS pages + ordered section stack (Wix Studio–style)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from app.cms_boundary import validate_cms_slug
from app.cms_section_images import (
    SECTION_IMAGE_LABELS,
    SECTION_IMAGE_TARGETS,
    SECTION_IMAGE_TYPES,
    delete_section_page_image,
    section_page_image_slot_key,
    sync_section_page_image_from_props,
    upsert_section_page_image,
)
from app.cms_site_pages import (
    ensure_site_route_page,
    fetch_page_by_site_route,
    page_key_for_cms_page,
    site_route_to_slug,
)

SECTION_TYPES = (
    "hero",
    "rich_text",
    "image_text",
    "cta_band",
    "faq_embed",
    "testimonials_embed",
    "button_row",
    "spacer",
)

DEFAULT_PROPS: dict[str, dict[str, Any]] = {
    "hero": {
        "anchor": "end",
        "eyebrow": "",
        "title": "新頁面標題",
        "lead": "",
        "image_url": "",
        "image_alt": "",
        "cta_label": "了解更多",
        "cta_href": "/contact.html",
        "cta_secondary_label": "",
        "cta_secondary_href": "",
    },
    "rich_text": {"anchor": "end", "title": "", "body": "", "columns": 1},
    "image_text": {
        "anchor": "end",
        "title": "",
        "body": "",
        "image_url": "",
        "image_alt": "",
        "layout": "stack",
        "cta_label": "",
        "cta_href": "",
    },
    "cta_band": {
        "anchor": "end",
        "title": "準備好開始了嗎？",
        "lead": "",
        "image_url": "",
        "image_alt": "",
        "cta_label": "客製試算",
        "cta_href": "/shop/calculator/",
        "cta_secondary_label": "聯絡我們",
        "cta_secondary_href": "/contact.html",
    },
    "faq_embed": {"anchor": "end", "mode": "teaser", "category_id": "", "limit": 6},
    "testimonials_embed": {"anchor": "end", "limit": 6},
    "button_row": {
        "anchor": "end",
        "buttons": [
            {"label": "客製試算", "href": "/shop/calculator/"},
            {"label": "查看價格", "href": "/price.html"},
        ]
    },
    "spacer": {"anchor": "end", "size": "md"},
}

_PROP_KEYS = {section_type: frozenset(props) for section_type, props in DEFAULT_PROPS.items()}
_TEXT_LIMITS = {
    "eyebrow": 160,
    "title": 300,
    "lead": 2000,
    "body": 12000,
    "image_alt": 500,
    "cta_label": 160,
    "cta_secondary_label": 160,
}
_URL_KEYS = {
    "image_url",
    "cta_href",
    "cta_secondary_href",
}


def ensure_cms_pages_schema(cur) -> None:
    cur.execute(
        """
        create table if not exists cms_pages (
          id uuid primary key default gen_random_uuid(),
          slug text not null unique,
          title text not null default '',
          meta_description text not null default '',
          status text not null default 'draft'
            check (status in ('draft', 'published')),
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    cur.execute("alter table cms_pages add column if not exists site_route text")
    cur.execute(
        """
        create unique index if not exists cms_pages_site_route_uidx
          on cms_pages (site_route)
          where site_route is not null
        """
    )
    cur.execute(
        """
        create table if not exists cms_page_sections (
          id uuid primary key default gen_random_uuid(),
          page_id uuid not null references cms_pages(id) on delete cascade,
          sort_order int not null default 0,
          type text not null,
          props jsonb not null default '{}'::jsonb,
          is_visible boolean not null default true,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    cur.execute(
        """
        create index if not exists cms_page_sections_page_sort_idx
          on cms_page_sections (page_id, sort_order, id)
        """
    )
    cur.execute(
        "create index if not exists cms_pages_status_idx on cms_pages (status, updated_at desc)"
    )


def serialize_page(row: dict, sections: list[dict] | None = None) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    if sections is not None:
        out["sections"] = sections
    return out


def serialize_section(row: dict) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    if out.get("page_id") is not None:
        out["page_id"] = str(out["page_id"])
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    if "is_visible" in out:
        out["is_visible"] = bool(out["is_visible"])
    if out.get("sort_order") is not None:
        out["sort_order"] = int(out["sort_order"])
    props = out.get("props")
    if props is None:
        out["props"] = {}
    elif not isinstance(props, dict):
        out["props"] = dict(props) if hasattr(props, "keys") else {}
    if out.get("type") in SECTION_TYPES:
        try:
            out["props"] = _normalize_section_props(out["type"], out["props"])
        except ValueError:
            out["props"] = default_props_for(out["type"])
    return out


def default_props_for(section_type: str) -> dict[str, Any]:
    base = DEFAULT_PROPS.get(section_type) or {}
    return {**base}


def parse_page_payload(body: dict | None, *, partial: bool = False) -> tuple[dict | None, str | None]:
    body = body or {}
    cleaned: dict[str, Any] = {}
    if not partial or "slug" in body or "title" in body:
        if "slug" in body or not partial:
            slug, err = validate_cms_slug(str(body.get("slug") or ""))
            if err:
                return None, err
            cleaned["slug"] = slug
        title_value = body.get("title") or ""
        if not isinstance(title_value, str):
            return None, "title 必須為文字"
        title = title_value.strip()
        if len(title) > 300:
            return None, "title 過長"
        if not partial and not title:
            return None, "請填寫頁面標題"
        if "title" in body or not partial:
            cleaned["title"] = title or "未命名頁面"
    if "metaDescription" in body or "meta_description" in body:
        meta = body.get("metaDescription") or body.get("meta_description") or ""
        if not isinstance(meta, str):
            return None, "meta_description 必須為文字"
        meta = meta.strip()
        if len(meta) > 1000:
            return None, "meta_description 過長"
        cleaned["meta_description"] = meta
    if "status" in body:
        status = str(body.get("status") or "draft").strip()
        if status not in ("draft", "published"):
            return None, "status 無效"
        cleaned["status"] = status
    return cleaned, None


def parse_section_payload(body: dict | None) -> tuple[dict | None, str | None]:
    body = body or {}
    section_type = str(body.get("type") or "").strip()
    if section_type not in SECTION_TYPES:
        return None, f"不支援的區塊類型：{section_type or '(空)'}"
    props = body.get("props")
    if props is None:
        props = default_props_for(section_type)
    if not isinstance(props, dict):
        return None, "props 必須為物件"
    unknown = set(props) - _PROP_KEYS[section_type]
    if unknown:
        return None, f"props 含不支援欄位：{', '.join(sorted(unknown))}"
    try:
        props = _normalize_section_props(section_type, props)
    except ValueError as exc:
        return None, str(exc)
    is_visible = bool(body.get("isVisible") if body.get("isVisible") is not None else body.get("is_visible", True))
    cleaned: dict[str, Any] = {"type": section_type, "props": props, "is_visible": is_visible}
    if body.get("sortOrder") not in (None, "") or body.get("sort_order") not in (None, ""):
        try:
            cleaned["sort_order"] = max(
                0, int(body.get("sortOrder") if body.get("sortOrder") not in (None, "") else body.get("sort_order"))
            )
        except (TypeError, ValueError):
            return None, "排序無效"
    return cleaned, None


def _normalize_section_props(section_type: str, props: dict) -> dict[str, Any]:
    out = {**default_props_for(section_type), **props}
    for key, limit in _TEXT_LIMITS.items():
        if key not in out:
            continue
        value = out[key]
        if not isinstance(value, str):
            raise ValueError(f"{key} 必須為文字")
        value = value.strip()
        if len(value) > limit:
            raise ValueError(f"{key} 過長")
        out[key] = value
    for key in _URL_KEYS:
        if key in out:
            out[key] = validate_public_url(out[key], key, image=key == "image_url")
    anchor = str(out.get("anchor") or "end").strip().lower()
    if not re.fullmatch(r"[a-z0-9-]{1,64}", anchor or ""):
        anchor = "end"
    out["anchor"] = anchor
    if section_type == "image_text":
        layout = str(out.get("layout") or "stack").strip()
        out["layout"] = layout if layout in ("left", "right", "stack") else "stack"
    if section_type == "rich_text":
        try:
            cols = int(out.get("columns") or 1)
        except (TypeError, ValueError):
            cols = 1
        out["columns"] = cols if cols in (1, 2, 3) else 1
    if section_type == "spacer":
        size = str(out.get("size") or "md").strip()
        out["size"] = size if size in ("sm", "md", "lg") else "md"
    if section_type == "button_row":
        buttons = out.get("buttons")
        if not isinstance(buttons, list):
            buttons = []
        cleaned_btns = []
        for item in buttons[:8]:
            if not isinstance(item, dict):
                raise ValueError("buttons 項目必須為物件")
            if set(item) - {"label", "href"}:
                raise ValueError("buttons 含不支援欄位")
            label = item.get("label") or ""
            if not isinstance(label, str):
                raise ValueError("button label 必須為文字")
            label = label.strip()
            if len(label) > 160:
                raise ValueError("button label 過長")
            href = validate_public_url(item.get("href") or "", "button href")
            if label or href:
                cleaned_btns.append({"label": label or "連結", "href": href or "/"})
        out["buttons"] = cleaned_btns or default_props_for("button_row")["buttons"]
    if section_type == "faq_embed":
        mode = out.get("mode") or "teaser"
        if mode not in ("teaser", "all"):
            raise ValueError("FAQ mode 無效")
        out["mode"] = mode
        category_id = out.get("category_id") or ""
        if not isinstance(category_id, str):
            raise ValueError("category_id 必須為文字")
        out["category_id"] = category_id.strip()
        if len(out["category_id"]) > 64:
            raise ValueError("category_id 過長")
    if section_type in ("faq_embed", "testimonials_embed"):
        try:
            out["limit"] = max(1, min(24, int(out.get("limit") or 6)))
        except (TypeError, ValueError):
            out["limit"] = 6
    return out


def validate_public_url(value: Any, field: str, *, image: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} 必須為文字")
    value = value.strip()
    if not value:
        return ""
    if len(value) > 2000 or any(ord(char) < 32 for char in value):
        raise ValueError(f"{field} 無效")
    if value.startswith(("/", "#")) and not value.startswith("//"):
        return value
    parsed = urlsplit(value)
    allowed = {"http", "https"} if image else {"http", "https", "mailto", "tel"}
    if parsed.scheme.lower() not in allowed:
        raise ValueError(f"{field} 連結格式無效")
    return value


def fetch_all_pages(cur) -> list[dict]:
    cur.execute("select * from cms_pages order by updated_at desc, created_at desc")
    return [serialize_page(r) for r in cur.fetchall()]


def fetch_page_by_id(cur, page_id: str) -> dict | None:
    cur.execute("select * from cms_pages where id = %s", (page_id,))
    row = cur.fetchone()
    return serialize_page(row) if row else None


def fetch_page_by_slug(cur, slug: str) -> dict | None:
    cur.execute("select * from cms_pages where slug = %s", (slug,))
    row = cur.fetchone()
    return serialize_page(row) if row else None


def fetch_sections(cur, page_id: str, *, visible_only: bool = False) -> list[dict]:
    if visible_only:
        cur.execute(
            """
            select * from cms_page_sections
            where page_id = %s and is_visible = true
            order by sort_order asc, id asc
            """,
            (page_id,),
        )
    else:
        cur.execute(
            """
            select * from cms_page_sections
            where page_id = %s
            order by sort_order asc, id asc
            """,
            (page_id,),
        )
    return [serialize_section(r) for r in cur.fetchall()]


def fetch_page_with_sections(
    cur, *, page_id: str | None = None, slug: str | None = None, visible_only: bool = False
) -> dict | None:
    page = fetch_page_by_id(cur, page_id) if page_id else fetch_page_by_slug(cur, slug or "")
    if not page:
        return None
    page["sections"] = fetch_sections(cur, page["id"], visible_only=visible_only)
    return page


def next_section_sort(cur, page_id: str) -> int:
    cur.execute(
        "select coalesce(max(sort_order), -1) + 1 as next from cms_page_sections where page_id = %s",
        (page_id,),
    )
    return int(cur.fetchone()["next"])


from app.cms_page_mutations import (  # noqa: E402
    create_page,
    create_section,
    delete_page,
    delete_section,
    reorder_sections,
    update_page,
    update_section,
)
