"""CMS page and section write operations."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb


def _helpers():
    from app.cms_pages import (
        fetch_page_by_id,
        fetch_sections,
        next_section_sort,
        serialize_page,
        serialize_section,
    )

    return fetch_page_by_id, fetch_sections, next_section_sort, serialize_page, serialize_section


def _invalidate_public_cache() -> None:
    from app.controllers.web_controller import clear_site_cms_cache

    clear_site_cms_cache()


def create_page(cur, fields: dict) -> dict:
    _, _, _, serialize_page, _ = _helpers()
    cur.execute(
        """
        insert into cms_pages (id, slug, title, meta_description, status)
        values (%s, %s, %s, %s, %s) returning *
        """,
        (
            str(uuid4()),
            fields["slug"],
            fields.get("title") or "未命名頁面",
            fields.get("meta_description") or "",
            fields.get("status") or "draft",
        ),
    )
    page = serialize_page(cur.fetchone(), sections=[])
    _invalidate_public_cache()
    return page


def update_page(cur, page_id: str, fields: dict) -> dict | None:
    fetch_page_by_id, _, _, serialize_page, _ = _helpers()
    existing = fetch_page_by_id(cur, page_id)
    if not existing:
        return None
    sets: list[str] = []
    values: list[Any] = []
    for column in ("slug", "title", "meta_description", "status"):
        if column in fields:
            sets.append(f"{column} = %s")
            values.append(fields[column])
    if not sets:
        return existing
    values.append(page_id)
    cur.execute(
        f"update cms_pages set {', '.join(sets)}, updated_at = now() where id = %s returning *",
        values,
    )
    page = serialize_page(cur.fetchone())
    if existing.get("slug") != page.get("slug"):
        from app.cms_section_images import move_section_image_page_key
        from app.cms_site_pages import page_key_for_cms_page

        move_section_image_page_key(
            cur, page_key_for_cms_page(existing), page_key_for_cms_page(page)
        )
    _invalidate_public_cache()
    return page


def delete_page(cur, page_id: str) -> bool:
    from app.cms_site_pages import page_key_for_cms_page

    fetch_page_by_id, _, _, _, _ = _helpers()
    page = fetch_page_by_id(cur, page_id)
    if not page:
        return False
    page_key = page_key_for_cms_page(page)
    cur.execute("delete from cms_pages where id = %s returning id", (page_id,))
    deleted = bool(cur.fetchone())
    if deleted and page_key:
        cur.execute(
            "delete from page_images where page_key = %s and group_key = 'cms-section'",
            (page_key,),
        )
        _invalidate_public_cache()
    return deleted


def create_section(cur, page_id: str, fields: dict) -> dict:
    _, _, next_section_sort, _, serialize_section = _helpers()
    sort_order = fields.get("sort_order")
    if sort_order is None:
        sort_order = next_section_sort(cur, page_id)
    cur.execute(
        """
        insert into cms_page_sections (page_id, sort_order, type, props, is_visible)
        values (%s, %s, %s, %s, %s) returning *
        """,
        (
            page_id,
            sort_order,
            fields["type"],
            Jsonb(fields.get("props") or {}),
            fields.get("is_visible", True),
        ),
    )
    section = serialize_section(cur.fetchone())
    cur.execute("update cms_pages set updated_at = now() where id = %s", (page_id,))
    _invalidate_public_cache()
    return section


def update_section(cur, section_id: str, fields: dict) -> dict | None:
    _, _, _, _, serialize_section = _helpers()
    cur.execute("select page_id from cms_page_sections where id = %s", (section_id,))
    existing = cur.fetchone()
    if not existing:
        return None
    sets: list[str] = []
    values: list[Any] = []
    mapping = (
        ("type", str),
        ("props", Jsonb),
        ("is_visible", bool),
        ("sort_order", int),
    )
    for key, convert in mapping:
        if key in fields:
            sets.append(f"{key} = %s")
            values.append(convert(fields[key]))
    if not sets:
        cur.execute("select * from cms_page_sections where id = %s", (section_id,))
        return serialize_section(cur.fetchone())
    values.append(section_id)
    cur.execute(
        f"""
        update cms_page_sections set {', '.join(sets)}, updated_at = now()
        where id = %s returning *
        """,
        values,
    )
    section = serialize_section(cur.fetchone())
    cur.execute(
        "update cms_pages set updated_at = now() where id = %s",
        (existing["page_id"],),
    )
    _invalidate_public_cache()
    return section


def delete_section(cur, section_id: str) -> bool:
    cur.execute(
        "delete from cms_page_sections where id = %s returning page_id",
        (section_id,),
    )
    row = cur.fetchone()
    if not row:
        return False
    cur.execute("update cms_pages set updated_at = now() where id = %s", (row["page_id"],))
    _invalidate_public_cache()
    return True


def reorder_sections(cur, page_id: str, ordered_ids: list[str]) -> list[dict]:
    _, fetch_sections, _, _, _ = _helpers()
    cur.execute("select id from cms_page_sections where page_id = %s", (page_id,))
    existing = {str(row["id"]) for row in cur.fetchall()}
    section_ids = [str(value) for value in ordered_ids]
    if (
        len(section_ids) != len(existing)
        or len(set(section_ids)) != len(section_ids)
        or set(section_ids) != existing
    ):
        raise ValueError("sectionIds 必須完整且不可重複")
    if not section_ids:
        return []
    values_sql = ", ".join(["(%s::uuid, %s::int)"] * len(section_ids))
    params: list[Any] = [
        value for index, section_id in enumerate(section_ids) for value in (section_id, index)
    ]
    params.append(page_id)
    cur.execute(
        f"""
        update cms_page_sections as section
        set sort_order = ordered.sort_order, updated_at = now()
        from (values {values_sql}) as ordered(id, sort_order)
        where section.id = ordered.id and section.page_id = %s
        """,
        params,
    )
    cur.execute("update cms_pages set updated_at = now() where id = %s", (page_id,))
    _invalidate_public_cache()
    return fetch_sections(cur, page_id)
