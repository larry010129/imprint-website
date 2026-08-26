"""Host-gated robots: noindex the no-hyphen imprintdiamond.com hosts + Render's
raw *.onrender.com test URL — never the production shop domain.

Shop hosts (imprint-diamond.com / www) stay index, follow. Other hosts
(localhost, TestClient) keep whatever the page already emits.
"""

from __future__ import annotations

# Apex + www without hyphen. Hyphenated shop domain is not in this set.
NOINDEX_HOSTS = frozenset(
    {
        "imprintdiamond.com",
        "www.imprintdiamond.com",
    }
)
# Render's raw <service>.onrender.com URL — always a test/staging mirror of
# whichever custom domain is live, never the canonical site.
_NOINDEX_HOST_SUFFIX = ".onrender.com"

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
    """True for a no-hyphen imprintdiamond.com host or any *.onrender.com host."""
    host = normalize_request_host(host_header)
    return host in NOINDEX_HOSTS or host.endswith(_NOINDEX_HOST_SUFFIX)


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


def apply_x_robots_tag(request, response) -> None:
    """Set X-Robots-Tag from request Host. Used by app middleware and tests."""
    tag = x_robots_tag_value(request.headers.get("host"))
    if tag:
        response.headers["X-Robots-Tag"] = tag
