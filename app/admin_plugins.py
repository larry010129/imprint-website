"""Admin plugin switches: 未啟用 (disabled) → 已啟用·關閉 (off) → 已啟用·開啟 (on).

Only plugins that really exist server-side are listed in LIVE_PLUGINS; the rest
of the 插件 catalog is display-only. States live in the cms_kv table (key
``admin-plugins``). Changing a state needs the admin password unlock — that
check lives in the controller, not here.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

KV_KEY = "admin-plugins"
STATES = ("disabled", "off", "on")

# default "on" keeps already-running plugins working until someone switches them.
LIVE_PLUGINS: dict[str, dict[str, str]] = {
    "booking": {"label": "預約諮詢日曆", "default": "on"},
}

# disabled → off → on, and back one step; on → disabled is allowed as a shortcut.
_ALLOWED = frozenset(
    {
        ("disabled", "off"),
        ("off", "on"),
        ("on", "off"),
        ("off", "disabled"),
        ("on", "disabled"),
    }
)


class PluginError(ValueError):
    """Invalid plugin change (message is safe to show the admin)."""


def default_states() -> dict[str, str]:
    return {slug: meta["default"] for slug, meta in LIVE_PLUGINS.items()}


def normalize_states(raw) -> dict[str, str]:
    out = default_states()
    if isinstance(raw, dict):
        for slug in LIVE_PLUGINS:
            if raw.get(slug) in STATES:
                out[slug] = raw[slug]
    return out


def get_states() -> dict[str, str]:
    from app.cms_kv_store import kv_get

    try:
        return normalize_states(kv_get(KV_KEY))
    except Exception:
        log.exception("plugin states load failed; using defaults")
        return default_states()


def is_on(slug: str) -> bool:
    return get_states().get(slug) == "on"


def set_state(slug: str, state: str) -> tuple[str, str]:
    """Validate and store a new state. Returns (previous, new)."""
    from app.cms_kv_store import kv_set

    if slug not in LIVE_PLUGINS:
        raise PluginError("找不到這個插件")
    if state not in STATES:
        raise PluginError("插件狀態不正確")
    states = get_states()
    previous = states[slug]
    if state == previous:
        return previous, state
    if (previous, state) not in _ALLOWED:
        raise PluginError("請依序操作：未啟用 → 關閉 → 開啟")
    states[slug] = state
    kv_set(KV_KEY, states)
    return previous, state
