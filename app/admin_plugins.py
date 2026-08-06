"""Built-in admin plugin registry (v1 — toggles + JSON config, no marketplace)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from psycopg.types.json import Jsonb

BUILTIN_PLUGINS: list[dict[str, str]] = [
    {
        "slug": "seo-tools",
        "labelZh": "SEO 工具",
        "labelEn": "SEO tools",
        "panelHint": "content",
    },
    {
        "slug": "media-optimize",
        "labelZh": "媒體優化",
        "labelEn": "Media optimize",
        "panelHint": "media",
    },
    {
        "slug": "analytics",
        "labelZh": "分析",
        "labelEn": "Analytics",
        "panelHint": "dash",
    },
    {
        "slug": "cms-content",
        "labelZh": "內容 CMS",
        "labelEn": "CMS content",
        "panelHint": "content",
    },
    {
        "slug": "pricing-tools",
        "labelZh": "定價工具",
        "labelEn": "Pricing tools",
        "panelHint": "pricing",
    },
]

BUILTIN_SLUGS: frozenset[str] = frozenset(p["slug"] for p in BUILTIN_PLUGINS)
_META_BY_SLUG: dict[str, dict[str, str]] = {p["slug"]: p for p in BUILTIN_PLUGINS}

_SELECT = "slug, enabled, config, updated_at"


def ensure_admin_plugins_schema(cur) -> None:
    """Create admin_plugins + seed built-ins (migration may not have run)."""
    cur.execute(
        """
        create table if not exists admin_plugins (
          slug text primary key,
          enabled boolean not null default true,
          config jsonb not null default '{}'::jsonb,
          updated_at timestamptz not null default now()
        )
        """
    )
    for plugin in BUILTIN_PLUGINS:
        cur.execute(
            """
            insert into admin_plugins (slug, enabled, config)
            values (%s, true, '{}'::jsonb)
            on conflict (slug) do nothing
            """,
            (plugin["slug"],),
        )


def _serialize_row(row: dict) -> dict:
    slug = str(row.get("slug") or "")
    meta = _META_BY_SLUG.get(slug, {})
    config = row.get("config")
    if not isinstance(config, dict):
        config = {}
    updated = row.get("updated_at")
    if isinstance(updated, datetime):
        updated = updated.isoformat()
    return {
        "slug": slug,
        "enabled": bool(row.get("enabled")),
        "config": config,
        "updatedAt": updated,
        "labelZh": meta.get("labelZh") or slug,
        "labelEn": meta.get("labelEn") or slug,
        "panelHint": meta.get("panelHint") or "",
    }


def list_plugins(cur) -> list[dict]:
    ensure_admin_plugins_schema(cur)
    cur.execute(
        f"select {_SELECT} from admin_plugins where slug = any(%s) order by slug",
        (list(BUILTIN_SLUGS),),
    )
    by_slug = {dict(r)["slug"]: dict(r) for r in cur.fetchall()}
    out: list[dict] = []
    for meta in BUILTIN_PLUGINS:
        row = by_slug.get(meta["slug"]) or {
            "slug": meta["slug"],
            "enabled": True,
            "config": {},
        }
        out.append(_serialize_row(row))
    return out


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off"):
            return False
        return None
    return bool(value)


def _fetch_one(cur, slug: str) -> dict | None:
    cur.execute(f"select {_SELECT} from admin_plugins where slug = %s", (slug,))
    row = cur.fetchone()
    return dict(row) if row else None


def update_plugin(
    cur, slug: str, *, enabled: Any = None, config: Any = None
) -> tuple[dict | None, str | None]:
    """Patch one built-in plugin. Returns (plugin, error)."""
    slug = (slug or "").strip()
    if slug not in BUILTIN_SLUGS:
        return None, "未知外掛"
    ensure_admin_plugins_schema(cur)
    enabled_val = _as_bool(enabled) if enabled is not None else None
    if enabled is not None and enabled_val is None:
        return None, "enabled 必須是布林值"
    if config is not None and not isinstance(config, dict):
        return None, "config 必須是物件"
    if enabled_val is None and config is None:
        return None, "缺少更新欄位"
    existing = _fetch_one(cur, slug)
    next_enabled = enabled_val if enabled_val is not None else (
        bool(existing["enabled"]) if existing else True
    )
    next_config = config if config is not None else (
        existing.get("config") if existing and isinstance(existing.get("config"), dict) else {}
    )
    cur.execute(
        """
        insert into admin_plugins (slug, enabled, config, updated_at)
        values (%s, %s, %s, now())
        on conflict (slug) do update set
          enabled = excluded.enabled,
          config = excluded.config,
          updated_at = now()
        returning slug, enabled, config, updated_at
        """,
        (slug, next_enabled, Jsonb(next_config)),
    )
    row = cur.fetchone()
    return _serialize_row(dict(row)), None
