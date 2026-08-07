"""Phase 1: marketing page text/button slots (no shop/jewelry product slots)."""

from __future__ import annotations

import re
from datetime import datetime
from html import escape
from typing import Any

from app.cms_boundary import assert_content_page_key, is_reserved_page_key
from app.cms_copy_slot_specs import copy_slot_specs
from app.cms_pages import validate_public_url

_SLOT_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_TEXT_ATTR_RE = re.compile(
    r"<(?P<tag>[a-zA-Z0-9]+)(?P<pre>[^>]*?)\bdata-cms-text\s*=\s*(?P<q>['\"])(?P<slot>[^'\"]+)(?P=q)(?P<post>[^>]*)>"
    r"(?P<body>.*?)"
    r"</(?P=tag)>",
    re.IGNORECASE | re.DOTALL,
)
_BUTTON_RE = re.compile(
    r"<(?P<tag>a|button)(?P<pre>[^>]*?)\bdata-cms-button\s*=\s*(?P<q>['\"])(?P<slot>[^'\"]+)(?P=q)(?P<post>[^>]*)>"
    r"(?P<body>.*?)"
    r"</(?P=tag)>",
    re.IGNORECASE | re.DOTALL,
)
_HREF_RE = re.compile(r"""\bhref\s*=\s*(['"])(.*?)\1""", re.IGNORECASE)


def ensure_page_copy_slots_schema(cur) -> None:
    cur.execute(
        """
        create table if not exists page_copy_slots (
          page_key text not null,
          slot_key text not null,
          kind text not null check (kind in ('text', 'button')),
          label text not null default '',
          text_value text not null default '',
          href text not null default '',
          default_text text not null default '',
          default_href text not null default '',
          sort_order int not null default 0,
          is_published boolean not null default true,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          primary key (page_key, slot_key)
        )
        """
    )
    cur.execute(
        """
        create index if not exists page_copy_slots_page_sort_idx
          on page_copy_slots (page_key, sort_order, slot_key)
        """
    )
    cur.execute(
        """
        delete from page_copy_slots
        where page_key like '/shop/%%'
           or page_key like '/jewelry/%%'
           or page_key = '/jewelry/'
           or page_key = '/price'
           or page_key = '/price.html'
        """
    )
    cur.execute(
        """
        update page_copy_slots as p
        set page_key = left(page_key, length(page_key) - 5)
        where page_key like '%%.html'
          and not exists (
            select 1 from page_copy_slots x
            where x.page_key = left(p.page_key, length(p.page_key) - 5)
              and x.slot_key = p.slot_key
          )
        """
    )
    cur.execute("delete from page_copy_slots where page_key like '%%.html'")


def seed_page_copy_slots(cur) -> int:
    inserted = 0
    for spec in copy_slot_specs():
        if is_reserved_page_key(spec["page_key"]):
            continue
        cur.execute(
            """
            insert into page_copy_slots (
              page_key, slot_key, kind, label, text_value, href,
              default_text, default_href, sort_order, is_published
            ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,true)
            on conflict (page_key, slot_key) do update set
              kind = excluded.kind,
              label = excluded.label,
              -- Keep custom CMS edits; refresh text_value only when still on prior default.
              text_value = case
                when page_copy_slots.text_value = page_copy_slots.default_text
                  or page_copy_slots.text_value = ''
                then excluded.default_text
                else page_copy_slots.text_value
              end,
              default_text = excluded.default_text,
              default_href = excluded.default_href,
              sort_order = excluded.sort_order
            """,
            (
                spec["page_key"],
                spec["slot_key"],
                spec["kind"],
                spec["label"],
                spec["default_text"],
                spec.get("default_href") or "",
                spec["default_text"],
                spec.get("default_href") or "",
                spec["sort_order"],
            ),
        )
        if cur.rowcount:
            inserted += 1
    return inserted


def serialize_copy_slot(row: dict) -> dict:
    out = dict(row)
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    if "is_published" in out:
        out["is_published"] = bool(out["is_published"])
    if out.get("sort_order") is not None:
        out["sort_order"] = int(out["sort_order"])
    out["display_text"] = effective_copy_text(out)
    out["display_href"] = effective_copy_href(out)
    return out


def effective_copy_text(row: dict | None) -> str:
    if not row:
        return ""
    if row.get("is_published") is False:
        return str(row.get("default_text") or "").strip()
    text = str(row.get("text_value") or "").strip()
    return text if text else str(row.get("default_text") or "").strip()


def effective_copy_href(row: dict | None) -> str:
    if not row:
        return ""
    if row.get("is_published") is False:
        return str(row.get("default_href") or "").strip()
    href = str(row.get("href") or "").strip()
    return href if href else str(row.get("default_href") or "").strip()


def fetch_all_copy_slots(cur) -> list[dict]:
    cur.execute(
        """
        select * from page_copy_slots
        where page_key not like '/shop/%%'
          and page_key not like '/jewelry/%%'
          and page_key <> '/jewelry/'
          and page_key <> '/price'
        order by page_key asc, sort_order asc, slot_key asc
        """
    )
    return [serialize_copy_slot(r) for r in cur.fetchall()]


def fetch_copy_slots_for_page(cur, page_key: str) -> list[dict]:
    from app.cms_boundary import page_key_aliases

    for key in page_key_aliases(page_key):
        cur.execute(
            "select * from page_copy_slots where page_key = %s order by sort_order, slot_key",
            (key,),
        )
        rows = cur.fetchall()
        if rows:
            return [serialize_copy_slot(r) for r in rows]
    return []


def parse_copy_slot_payload(body: dict | None) -> tuple[dict | None, str | None]:
    body = body or {}
    page_key, err = assert_content_page_key(
        str(body.get("pageKey") or body.get("page_key") or "")
    )
    if err:
        return None, err
    slot_key = str(body.get("slotKey") or body.get("slot_key") or "").strip()
    if not slot_key or not _SLOT_KEY_RE.fullmatch(slot_key):
        return None, "slot_key 無效"
    text_value = str(body.get("textValue") or body.get("text_value") or "").strip()
    if len(text_value) > 12000:
        return None, "文字過長"
    try:
        href = validate_public_url(body.get("href") or "", "href")
    except ValueError as exc:
        return None, str(exc)
    is_published = bool(
        body.get("isPublished") if body.get("isPublished") is not None else body.get("is_published", True)
    )
    return {
        "page_key": page_key,
        "slot_key": slot_key,
        "text_value": text_value,
        "href": href,
        "is_published": is_published,
    }, None


def update_copy_slot(cur, fields: dict) -> dict | None:
    cur.execute(
        """
        update page_copy_slots set
          text_value = %s, href = %s, is_published = %s, updated_at = now()
        where page_key = %s and slot_key = %s
        returning *
        """,
        (
            fields["text_value"],
            fields.get("href") or "",
            fields.get("is_published", True),
            fields["page_key"],
            fields["slot_key"],
        ),
    )
    row = cur.fetchone()
    return serialize_copy_slot(row) if row else None


def apply_page_copy_slots(html: str, route: str, rows: list[dict]) -> str:
    if not html or not rows:
        return html
    by_slot = {str(r.get("slot_key")): r for r in rows}
    if not by_slot:
        return html

    def replace_text(match: re.Match[str]) -> str:
        slot = match.group("slot")
        row = by_slot.get(slot)
        if not row or row.get("kind") == "button":
            return match.group(0)
        text = effective_copy_text(row)
        if not text:
            return match.group(0)
        open_tag = f"<{match.group('tag')}{match.group('pre')}data-cms-text=\"{slot}\"{match.group('post')}>"
        # Preserve simple <br> in titles when default had them — plain text only for CMS value.
        return f"{open_tag}{escape(text)}</{match.group('tag')}>"

    def replace_button(match: re.Match[str]) -> str:
        slot = match.group("slot")
        row = by_slot.get(slot)
        if not row:
            return match.group(0)
        label = effective_copy_text(row)
        href = effective_copy_href(row)
        try:
            href = validate_public_url(href, "href")
        except ValueError:
            href = ""
        attrs = f"{match.group('pre')}data-cms-button=\"{slot}\"{match.group('post')}"
        if href and match.group("tag").lower() == "a":
            href = escape(href, quote=True)
            if _HREF_RE.search(attrs):
                attrs = _HREF_RE.sub(lambda m: f"href={m.group(1)}{href}{m.group(1)}", attrs, count=1)
            else:
                attrs = f' href="{href}"' + attrs
        body = escape(label) if label else match.group("body")
        return f"<{match.group('tag')}{attrs}>{body}</{match.group('tag')}>"

    html = _TEXT_ATTR_RE.sub(replace_text, html)
    html = _BUTTON_RE.sub(replace_button, html)
    return html
