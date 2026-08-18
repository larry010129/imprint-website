"""Host-gated robots: noindex only the no-hyphen imprintdiamond.com hosts.

Shop hosts (imprint-diamond.com / www) stay index, follow. Other hosts
(localhost, Render, TestClient) keep whatever the page already emits.
"""

from __future__ import annotations

# Apex + www without hyphen. Hyphenated shop domain is not in this set.
NOINDEX_HOSTS = frozenset(
    {
        "imprintdiamond.com",
        "www.imprintdiamond.com",
    }
)

HOST_NOINDEX_ROBOTS = "noindex, follow"


def normalize_request_host(host_header: str | None) -> str:
    """Lowercase Host and drop :port. ``[::1]:443`` keeps the address only."""
    raw = (host_header or "").strip().lower()
    if not raw:
        return ""
    if raw.startswith("["):
        end = raw.find("]")
        host = raw[1:end] if end != -1 else raw.strip("[]")
    else:
        host, sep, maybe_port = raw.rpartition(":")
        host = host if sep and maybe_port.isdigit() else raw
    return host.rstrip(".")


def is_noindex_host(host_header: str | None) -> bool:
    """True when FastAPI request Host is a no-hyphen imprintdiamond.com host."""
    return normalize_request_host(host_header) in NOINDEX_HOSTS


def _is_indexable_robots(page_robots: str | None) -> bool:
    if page_robots is None:
        return True
    token = page_robots.split(",", 1)[0].strip().lower()
    return token == "index"


def html_robots_content(host_header: str | None, page_robots: str | None) -> str | None:
    """Replace indexable robots with noindex, follow on no-hyphen hosts only.

    ``page_robots is None`` means the layout default (index, follow, …).
    Pages that already noindex (privacy, terms, 404) keep their value.
    """
    if is_noindex_host(host_header) and _is_indexable_robots(page_robots):
        return HOST_NOINDEX_ROBOTS
    return page_robots


def x_robots_tag_value(host_header: str | None) -> str | None:
    """Same host gate as :func:`html_robots_content` — one check, one constant."""
    if is_noindex_host(host_header):
        return HOST_NOINDEX_ROBOTS
    return None
