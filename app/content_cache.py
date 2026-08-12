"""Short process-local caches for admin content lists and public content APIs."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from threading import Lock
from time import monotonic
from typing import Any

ADMIN_CONTENT_CACHE_TTL_SECONDS = 12.0
PUBLIC_CONTENT_API_CACHE_TTL_SECONDS = 30.0

_admin_lock = Lock()
_admin_cache: dict[tuple, tuple[float, dict[str, Any]]] = {}
_admin_generation = 0

_public_lock = Lock()
_public_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def admin_cache_generation() -> int:
    with _admin_lock:
        return _admin_generation


def get_admin_content_cache(key: tuple) -> dict[str, Any] | None:
    now = monotonic()
    with _admin_lock:
        entry = _admin_cache.get(key)
        if not entry:
            return None
        if now - entry[0] >= ADMIN_CONTENT_CACHE_TTL_SECONDS:
            _admin_cache.pop(key, None)
            return None
        return deepcopy(entry[1])


def set_admin_content_cache(key: tuple, payload: dict[str, Any]) -> None:
    with _admin_lock:
        _admin_cache[key] = (monotonic(), deepcopy(payload))


def clear_admin_content_cache() -> None:
    global _admin_generation
    with _admin_lock:
        _admin_cache.clear()
        _admin_generation += 1


def get_public_content_api_cache(key: str) -> dict[str, Any] | None:
    now = monotonic()
    with _public_lock:
        entry = _public_cache.get(key)
        if not entry:
            return None
        if now - entry[0] >= PUBLIC_CONTENT_API_CACHE_TTL_SECONDS:
            _public_cache.pop(key, None)
            return None
        return deepcopy(entry[1])


def set_public_content_api_cache(key: str, payload: dict[str, Any]) -> None:
    with _public_lock:
        _public_cache[key] = (monotonic(), deepcopy(payload))


def clear_public_content_api_cache() -> None:
    with _public_lock:
        _public_cache.clear()


def clear_content_api_caches() -> None:
    """Invalidate admin list/bootstrap + public /api/banners|/api/testimonials."""
    clear_admin_content_cache()
    clear_public_content_api_cache()


def content_etag(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f'"{digest}"'
