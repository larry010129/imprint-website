"""Canonical CMS section image props and their page_images projection."""

from __future__ import annotations

import re

from psycopg.types.json import Jsonb

from app.cms_boundary import assert_content_page_key
from app.cms_site_pages import page_key_for_cms_page

SECTION_IMAGE_TYPES = frozenset({"hero", "image_text", "cta_band"})
SECTION_IMAGE_LABELS = {
    "hero": "Hero 區塊",
    "image_text": "圖文區塊",
    "cta_band": "CTA 區塊",
}
SECTION_IMAGE_TARGETS = {
    "hero": (1600, 900),
    "image_text": (1200, 900),
    "cta_band": (1600, 600),
}


def section_page_image_slot_key(section_id: str) -> str:
    return f"cms-section-{section_id}"


def upsert_section_page_image(
    cur,
    *,
    page_key: str,
    section_id: str,
    section_type: str,
    image_url: str,
    image_alt: str = "",
    image_webp: str | None = None,
) -> dict | None:
    from app.content import ensure_page_images_schema, serialize_page_image

    if section_type not in SECTION_IMAGE_TYPES:
        return None
    key, key_err = assert_content_page_key(page_key)
    if key_err or not key:
        raise ValueError(key_err or "invalid page_key")
    slot_key = section_page_image_slot_key(section_id)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", slot_key):
        raise ValueError("invalid slot_key")
    url = str(image_url or "").strip()
    alt = str(image_alt or "").strip()
    ensure_page_images_schema(cur)
    if not url:
        delete_section_page_image(cur, page_key=key, section_id=section_id, hide=True)
        return None

    label = SECTION_IMAGE_LABELS.get(section_type, "CMS 區塊")
    target_w, target_h = SECTION_IMAGE_TARGETS.get(section_type, (1200, 900))
    webp = (
        str(image_webp).strip()
        if image_webp is not None
        else (url if url.lower().endswith(".webp") else None)
    )
    cur.execute(
        """
        insert into page_images (
          page_key, slot_key, label, slot_label, group_key,
          image_url, image_webp, image_alt,
          default_image_url, default_image_webp,
          target_w, target_h, sort_order, is_published
        ) values (
          %s, %s, %s, %s, 'cms-section', %s, %s, %s,
          '', null, %s, %s, 900, true
        )
        on conflict (page_key, slot_key) do update set
          label = excluded.label,
          slot_label = excluded.slot_label,
          image_url = excluded.image_url,
          image_webp = excluded.image_webp,
          image_alt = excluded.image_alt,
          is_published = true,
          updated_at = now()
        returning *
        """,
        (key, slot_key, label, label, url, webp, alt, target_w, target_h),
    )
    return serialize_page_image(cur.fetchone())


def delete_section_page_image(
    cur, *, page_key: str, section_id: str, hide: bool = False
) -> bool:
    from app.content import ensure_page_images_schema

    key, key_err = assert_content_page_key(page_key)
    if key_err or not key:
        return False
    ensure_page_images_schema(cur)
    slot_key = section_page_image_slot_key(section_id)
    if hide:
        cur.execute(
            """
            update page_images
            set is_published = false, image_url = '', image_webp = null, updated_at = now()
            where page_key = %s and slot_key = %s returning page_key
            """,
            (key, slot_key),
        )
    else:
        cur.execute(
            "delete from page_images where page_key = %s and slot_key = %s returning page_key",
            (key, slot_key),
        )
    return bool(cur.fetchone())


def sync_section_page_image_from_props(cur, section: dict, page: dict) -> dict | None:
    section_type = str(section.get("type") or "")
    if section_type not in SECTION_IMAGE_TYPES:
        return None
    props = section.get("props") if isinstance(section.get("props"), dict) else {}
    page_key = page_key_for_cms_page(page)
    if not page_key:
        return None
    return upsert_section_page_image(
        cur,
        page_key=page_key,
        section_id=str(section["id"]),
        section_type=section_type,
        image_url=str(props.get("image_url") or ""),
        image_alt=str(props.get("image_alt") or ""),
    )


def update_section_from_page_image(
    cur,
    *,
    page_key: str,
    slot_key: str,
    image_url: str,
    image_alt: str,
    image_webp: str | None = None,
) -> dict | None:
    """Write a generic Page Images edit through the canonical section props."""
    prefix = "cms-section-"
    section_id = slot_key[len(prefix):] if slot_key.startswith(prefix) else ""
    if not section_id:
        return None
    cur.execute(
        """
        select s.*, p.slug, p.site_route
        from cms_page_sections s
        join cms_pages p on p.id = s.page_id
        where s.id = %s
        """,
        (section_id,),
    )
    row = cur.fetchone()
    if not row or page_key_for_cms_page(row) != page_key:
        return None
    section_type = str(row.get("type") or "")
    if section_type not in SECTION_IMAGE_TYPES:
        return None
    props = dict(row.get("props") or {})
    props["image_url"] = str(image_url or "").strip()
    props["image_alt"] = str(image_alt or "").strip()
    cur.execute(
        """
        update cms_page_sections set props = %s, updated_at = now()
        where id = %s
        """,
        (Jsonb(props), section_id),
    )
    cur.execute("update cms_pages set updated_at = now() where id = %s", (row["page_id"],))
    return upsert_section_page_image(
        cur,
        page_key=page_key,
        section_id=section_id,
        section_type=section_type,
        image_url=props["image_url"],
        image_alt=props["image_alt"],
        image_webp=image_webp,
    )


def move_section_image_page_key(cur, old_key: str, new_key: str) -> None:
    if old_key and new_key and old_key != new_key:
        cur.execute(
            """
            update page_images set page_key = %s, updated_at = now()
            where page_key = %s and group_key = 'cms-section'
            """,
            (new_key, old_key),
        )
