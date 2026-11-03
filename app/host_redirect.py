"""301 the raw *.onrender.com host to the public site (PUBLIC_SITE_URL).

The Render URL serves the same pages as www.imprint-diamond.com; without a
redirect Google sees two copies. Only GET/HEAD page traffic moves — /health
(Render + the gold-quote workflow), /api/* (gold-refresh POSTs, JSON clients)
and /robots.txt (keeps its Disallow-all for the mirror) stay on the Render host.

No-op unless PUBLIC_SITE_URL (or SITE_URL) is an https URL on a different,
non-onrender host, so local dev, tests and a misconfigured env never loop.
"""

from __future__ import annotations

import os
from urllib.parse import urlsplit

from app.robots_host import normalize_request_host

_RENDER_HOST_SUFFIX = ".onrender.com"
_REDIRECT_METHODS = frozenset({"GET", "HEAD"})
_EXEMPT_PATHS = frozenset({"/health", "/robots.txt"})
_EXEMPT_PREFIXES = ("/api/",)


def _public_site_base() -> str | None:
    raw = (
        os.environ.get("PUBLIC_SITE_URL", "").strip()
        or os.environ.get("SITE_URL", "").strip()
    )
    parts = urlsplit(raw)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not host or host.endswith(_RENDER_HOST_SUFFIX):
        return None
    return f"https://{parts.netloc.lower()}"


def onrender_redirect_location(
    host_header: str | None, method: str, path: str, query: str
) -> str | None:
    """Return the 301 Location for a Render-host page request, else None."""
    host = normalize_request_host(host_header)
    if not host.endswith(_RENDER_HOST_SUFFIX):
        return None
    if method.upper() not in _REDIRECT_METHODS:
        return None
    if path in _EXEMPT_PATHS or path.startswith(_EXEMPT_PREFIXES):
        return None
    base = _public_site_base()
    if base is None or urlsplit(base).hostname == host:
        return None
    return f"{base}{path}?{query}" if query else f"{base}{path}"
