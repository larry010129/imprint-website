"""Shared CMS media library for modular page editor uploads."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4


def ensure_cms_media_schema(cur) -> None:
    cur.execute(
        """
        create table if not exists cms_media (
          id uuid primary key default gen_random_uuid(),
          url text not null,
          alt text not null default '',
          filename text not null default '',
          created_at timestamptz not null default now()
        )
        """
    )
    cur.execute(
        "create index if not exists cms_media_created_idx on cms_media (created_at desc)"
    )


def serialize_media(row: dict) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    val = out.get("created_at")
    if isinstance(val, datetime):
        out["created_at"] = val.isoformat()
    return out


def count_media(cur) -> int:
    cur.execute("select count(*)::int as n from cms_media")
    row = cur.fetchone() or {}
    return int(row.get("n") or 0)


def fetch_media(
    cur,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    limit = max(1, min(100, int(limit)))
    offset = max(0, int(offset))
    cur.execute(
        "select * from cms_media order by created_at desc limit %s offset %s",
        (limit, offset),
    )
    return [serialize_media(r) for r in cur.fetchall()]


def create_media(cur, *, url: str, alt: str = "", filename: str = "") -> dict:
    mid = str(uuid4())
    cur.execute(
        """
        insert into cms_media (id, url, alt, filename)
        values (%s, %s, %s, %s)
        returning *
        """,
        (mid, url, alt or "", filename or ""),
    )
    return serialize_media(cur.fetchone())


def delete_media(cur, media_id: str) -> str | None:
    cur.execute("delete from cms_media where id = %s returning url", (media_id,))
    row = cur.fetchone()
    return str(row["url"]) if row else None
