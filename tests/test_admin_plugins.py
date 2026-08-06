"""Unit tests for admin_plugins registry (schema ensure + update validation)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.admin_plugins import (
    BUILTIN_SLUGS,
    ensure_admin_plugins_schema,
    list_plugins,
    update_plugin,
)


def test_ensure_admin_plugins_schema_creates_and_seeds():
    cur = MagicMock()
    ensure_admin_plugins_schema(cur)
    assert cur.execute.call_count == 1 + len(BUILTIN_SLUGS)
    sql = cur.execute.call_args_list[0].args[0]
    assert "create table if not exists admin_plugins" in sql
    seeded = {c.args[1][0] for c in cur.execute.call_args_list[1:]}
    assert seeded == set(BUILTIN_SLUGS)


def test_list_plugins_returns_builtin_order():
    cur = MagicMock()
    cur.fetchall.return_value = [
        {
            "slug": "analytics",
            "enabled": False,
            "config": {"k": 1},
            "updated_at": datetime(2026, 8, 6, tzinfo=timezone.utc),
        }
    ]
    plugins = list_plugins(cur)
    assert [p["slug"] for p in plugins] == [
        "seo-tools",
        "media-optimize",
        "analytics",
        "cms-content",
        "pricing-tools",
    ]
    analytics = next(p for p in plugins if p["slug"] == "analytics")
    assert analytics["enabled"] is False
    assert analytics["config"] == {"k": 1}
    assert analytics["labelZh"]
    assert analytics["panelHint"] == "dash"


def test_update_plugin_rejects_unknown_slug():
    cur = MagicMock()
    plugin, err = update_plugin(cur, "not-a-plugin", enabled=False)
    assert plugin is None
    assert err == "未知外掛"


def test_update_plugin_requires_fields():
    cur = MagicMock()
    plugin, err = update_plugin(cur, "seo-tools")
    assert plugin is None
    assert err == "缺少更新欄位"


def test_update_plugin_upserts_enabled():
    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"slug": "seo-tools", "enabled": True, "config": {}, "updated_at": None},
        {
            "slug": "seo-tools",
            "enabled": False,
            "config": {},
            "updated_at": datetime(2026, 8, 6, tzinfo=timezone.utc),
        },
    ]
    plugin, err = update_plugin(cur, "seo-tools", enabled=False)
    assert err is None
    assert plugin is not None
    assert plugin["slug"] == "seo-tools"
    assert plugin["enabled"] is False
    upsert_sql = cur.execute.call_args_list[-1].args[0]
    assert "on conflict (slug) do update" in upsert_sql
