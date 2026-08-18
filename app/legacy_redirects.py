"""301s for old Google / CMS paths after the imprint-diamond.com cutover.

Jewelry is retired: every /jewelry path goes home. DNA shop IDs come from
docs/legacy-content-gap-matrix.md (legacy /imprint/shop/{8,11,18,19,20}).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

HOME = "/"
SERIES = "/series"

# 初生 / 寵物 / 結髮 / 全家福 / 生命 — path IDs only; do not invent jewelry SKUs.
DNA_SHOP_IDS: dict[str, str] = {
    "8": "/series/pet/",
    "11": "/series/love/",
    "18": "/series/first-love/",
    "19": "/series/family/",
    "20": "/series/heirloom/",
}

SERIES_SLUGS: dict[str, str] = {
    "first-love": "/series/first-love/",
    "pet": "/series/pet/",
    "love": "/series/love/",
    "family": "/series/family/",
    "heirloom": "/series/heirloom/",
}

HOME_INDEX_NAMES = frozenset({"index", "index.php", "index.html"})


def is_retired_jewelry_route(path: str) -> bool:
    """True for /jewelry and every child — those routes must not stay 200."""
    p = _path_only(path)
    return p == "/jewelry" or p.startswith("/jewelry/")


def _path_only(path: str) -> str:
    p = (path or "").split("?", 1)[0]
    if not p.startswith("/"):
        p = f"/{p}"
    return p


def _strip_slash(path: str) -> str:
    if path == "/":
        return path
    return path.rstrip("/")


def lookup_legacy_redirect(path: str) -> str | None:
    """Return a 301 Location, or None so the app can 404."""
    p = _path_only(path)
    stripped = _strip_slash(p)

    if is_retired_jewelry_route(p):
        return HOME
    if stripped == "/imprint/jewelry" or stripped.startswith("/imprint/jewelry/"):
        return HOME

    if stripped == "/imprint" or stripped in {f"/imprint/{name}" for name in HOME_INDEX_NAMES}:
        return HOME

    if stripped == "/imprint/shop":
        return SERIES

    shop_prefix = "/imprint/shop/"
    if p.startswith(shop_prefix) or stripped.startswith(shop_prefix):
        ident = stripped[len(shop_prefix) :]
        if not ident or "/" in ident:
            return None
        return DNA_SHOP_IDS.get(ident)

    imprint_prefix = "/imprint/"
    if stripped.startswith(imprint_prefix):
        slug = stripped[len(imprint_prefix) :]
        if slug in SERIES_SLUGS:
            return SERIES_SLUGS[slug]
        return None

    return None


def _redirect_response(request: Request, target: str) -> RedirectResponse:
    query = request.url.query
    location = f"{target}?{query}" if query else target
    return RedirectResponse(url=location, status_code=301)


def register_legacy_redirects(app: FastAPI) -> None:
    """Register /imprint and /jewelry 301s before any Jinja jewelry page route."""

    async def legacy_imprint(request: Request) -> RedirectResponse:
        target = lookup_legacy_redirect(request.url.path)
        if target is None:
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        return _redirect_response(request, target)

    async def legacy_jewelry(request: Request) -> RedirectResponse:
        return _redirect_response(request, HOME)

    for path in ("/imprint", "/imprint/"):
        app.add_api_route(
            path,
            legacy_imprint,
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )
    app.add_api_route(
        "/imprint/{rest:path}",
        legacy_imprint,
        methods=["GET", "HEAD"],
        include_in_schema=False,
    )

    for path in ("/jewelry", "/jewelry/"):
        app.add_api_route(
            path,
            legacy_jewelry,
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )
    app.add_api_route(
        "/jewelry/{rest:path}",
        legacy_jewelry,
        methods=["GET", "HEAD"],
        include_in_schema=False,
    )
