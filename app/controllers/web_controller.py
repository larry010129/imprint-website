"""Web routes — static mounts, admin shell, CMS proxy. HTML pages owned by Next.js."""

from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.settings import settings
from app.youtube_channel import fetch_latest_channel_video, resolve_channel_id

_FRAGMENTS_DIR = settings.site_content_dir / "fragments"
_FEATURED_VIDEO_PATH = Path(__file__).resolve().parent.parent / "data" / "featured-video.json"
_FEATURED_YOUTUBE_LATEST_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "featured-youtube-latest.json"
)
_PUBLIC_PHONE_TEXT = "電話：02-2977-0268；"
_PAGE_IMAGE_CACHE_TTL_SECONDS = 30


def _strip_public_phone_metadata(block: str) -> str:
    """Remove public phone fields and copy from JSON-LD registry blocks."""
    try:
        payload = json.loads(block)
    except json.JSONDecodeError:
        return block

    def clean(value):
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items() if key != "telephone"}
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, str):
            return value.replace(_PUBLIC_PHONE_TEXT, "")
        return value

    return json.dumps(clean(payload), ensure_ascii=False, indent=2)


def load_featured_video() -> dict | None:
    """Pinned About-page video (fixed ID from JSON)."""
    if not _FEATURED_VIDEO_PATH.is_file():
        return None
    try:
        data = json.loads(_FEATURED_VIDEO_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not data.get("enabled") or not data.get("youtube_id"):
        return None
    return data


def load_youtube_latest_video() -> dict | None:
    """Latest upload from the configured YouTube channel."""
    if not _FEATURED_YOUTUBE_LATEST_PATH.is_file():
        return None
    try:
        data = json.loads(_FEATURED_YOUTUBE_LATEST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not data.get("enabled"):
        return None

    source = (data.get("source") or "fixed").strip().lower()
    if source == "channel_latest":
        channel_id = resolve_channel_id(
            data.get("channel_id"),
            data.get("channel_handle"),
        )
        ttl = int(data.get("cache_ttl_seconds") or 21600)
        if channel_id:
            try:
                latest = fetch_latest_channel_video(channel_id, ttl_seconds=ttl)
                if latest:
                    data = {**data, **latest}
            except OSError:
                pass

    if not data.get("youtube_id"):
        return None
    return data


@lru_cache(maxsize=None)
def _load_fragment(relpath: str) -> str:
    return (_FRAGMENTS_DIR / relpath).read_text(encoding="utf-8")


@lru_cache(maxsize=512)
def _fetch_page_images_cached(route: str, _time_bucket: int) -> list[dict]:
    from app.content import fetch_page_images
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        return fetch_page_images(cur, route)


def _load_page_images(route: str) -> list[dict]:
    try:
        time_bucket = int(monotonic() // _PAGE_IMAGE_CACHE_TTL_SECONDS)
        return deepcopy(_fetch_page_images_cached(route, time_bucket))
    except Exception:
        return []


def _load_page_image(route: str, rows: list[dict] | None = None) -> dict | None:
    """Backward-compatible primary slot used by page-context."""
    rows = rows if rows is not None else _load_page_images(route)
    preferred = "cinema" if route == "/about.html" else "hero"
    return next((row for row in rows if row.get("slot_key") == preferred), None)


def clear_page_image_cache() -> None:
    _fetch_page_images_cached.cache_clear()


@lru_cache(maxsize=512)
def _fetch_page_copy_cached(route: str, _time_bucket: int) -> list[dict]:
    from app.cms_copy_slots import fetch_copy_slots_for_page
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        return fetch_copy_slots_for_page(cur, route)


def _load_page_copy_slots(route: str) -> list[dict]:
    try:
        time_bucket = int(monotonic() // _PAGE_IMAGE_CACHE_TTL_SECONDS)
        return deepcopy(_fetch_page_copy_cached(route, time_bucket))
    except Exception:
        return []


def clear_page_copy_cache() -> None:
    _fetch_page_copy_cached.cache_clear()


def _editable_site_routes() -> set[str]:
    from app.cms_copy_slot_specs import EDITABLE_SITE_PAGES

    return {item["route"] for item in EDITABLE_SITE_PAGES}


def _empty_cms_bundle(route: str) -> dict:
    return {
        "cms_page": {"title": "", "slug": "", "site_route": route},
        "site_cms_sections": [],
        "site_cms_sections_by_anchor": {},
        "cms_faq_items": [],
        "cms_faq_all_items": [],
        "cms_faq_by_category": {},
        "cms_testimonials": [],
    }


def _fetch_site_cms_bundle(route: str, *, visible_only: bool) -> dict:
    """Load one host-page stack with only the embed data it actually uses."""
    from app.cms_pages import SECTION_TYPES, fetch_page_by_site_route, fetch_sections
    from app.database import get_connection

    empty = _empty_cms_bundle(route)
    with get_connection() as conn, conn.cursor() as cur:
        page = fetch_page_by_site_route(cur, route)
        if not page:
            return empty
        sections = [
            section
            for section in fetch_sections(cur, page["id"], visible_only=visible_only)
            if section.get("type") in SECTION_TYPES
        ]
        by_anchor: dict[str, list] = {}
        for section in sections:
            props = section.get("props") if isinstance(section.get("props"), dict) else {}
            anchor = str(props.get("anchor") or "end").strip().lower() or "end"
            by_anchor.setdefault(anchor, []).append(section)
        bundle = {
            **empty,
            "cms_page": page,
            "site_cms_sections": sections,
            "site_cms_sections_by_anchor": by_anchor,
        }
        section_types = {section.get("type") for section in sections}
        if "faq_embed" in section_types:
            from app.content import fetch_faq_public

            faq = fetch_faq_public(cur)
            faq_items = faq.get("teaser") or [
                item
                for cat in (faq.get("categories") or [])
                for item in (cat.get("items") or [])
            ]
            bundle.update(
                {
                    "cms_faq_items": faq_items,
                    "cms_faq_all_items": faq.get("items") or [],
                    "cms_faq_by_category": {
                        str(cat.get("id")): cat.get("items") or []
                        for cat in (faq.get("categories") or [])
                    },
                }
            )
        if "testimonials_embed" in section_types:
            from app.content import fetch_published_testimonials

            bundle["cms_testimonials"] = fetch_published_testimonials(cur)
        return bundle


@lru_cache(maxsize=512)
def _fetch_site_cms_bundle_cached(route: str, _time_bucket: int) -> dict:
    return _fetch_site_cms_bundle(route, visible_only=True)


def _load_site_cms_bundle(route: str, *, visible_only: bool) -> dict:
    if route not in _editable_site_routes():
        return _empty_cms_bundle(route)
    try:
        if not visible_only:
            return _fetch_site_cms_bundle(route, visible_only=False)
        time_bucket = int(monotonic() // _PAGE_IMAGE_CACHE_TTL_SECONDS)
        return deepcopy(_fetch_site_cms_bundle_cached(route, time_bucket))
    except Exception:
        return _empty_cms_bundle(route)


def clear_site_cms_cache() -> None:
    _fetch_site_cms_bundle_cached.cache_clear()
    _fetch_public_cms_page_cached.cache_clear()


def _fetch_public_cms_page(slug: str, *, visible_only: bool) -> dict | None:
    from app.cms_pages import fetch_public_cms_bundle
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        return fetch_public_cms_bundle(cur, slug, visible_only=visible_only)


@lru_cache(maxsize=512)
def _fetch_public_cms_page_cached(slug: str, _time_bucket: int) -> dict | None:
    bundle = _fetch_public_cms_page(slug, visible_only=True)
    if not bundle or bundle["page"].get("status") != "published":
        return None
    return bundle


def register_pages(app: FastAPI) -> None:
    """Register non-Jinja web routes. HTML pages are served by Next.js (apps/web)."""

    @app.api_route("/health", methods=["GET", "HEAD"], include_in_schema=False)
    async def api_health() -> JSONResponse:
        """Render / load-balancer health — must not 404 or the API service is SIGTERM'd."""
        return JSONResponse({"ok": True, "service": "imprint-api"})

    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    async def api_root():
        """API root is not the marketing site. Redirect to Next when configured."""
        next_origin = settings.next_public_origin
        api_base = settings.public_base_url.rstrip("/")
        if next_origin and next_origin.rstrip("/") != api_base:
            return RedirectResponse(url=f"{next_origin}/", status_code=307)
        return JSONResponse(
            {
                "ok": True,
                "service": "imprint-api",
                "health": "/health",
                "api": "/api/bot-gold",
                "hint": (
                    "This host is FastAPI only. Public pages are on imprint-web (Next.js). "
                    "Deploy render.yaml Blueprint and open the imprint-web URL, "
                    "or set NEXT_PUBLIC_ORIGIN to that host."
                ),
            }
        )

    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon() -> FileResponse:
        return FileResponse(settings.site_root / "favicon.svg")

    @app.get("/robots.txt", include_in_schema=False)
    async def robots() -> FileResponse:
        return FileResponse(settings.site_root / "robots.txt")

    @app.get("/sitemap.xml", include_in_schema=False)
    async def sitemap() -> FileResponse:
        return FileResponse(settings.site_root / "sitemap.xml")

    @app.get("/admin.html", include_in_schema=False)
    async def admin_page(request: Request):
        from app.auth import get_user_id, is_admin

        if not is_admin(get_user_id(request)):
            next_origin = settings.next_public_origin or ""
            login = f"{next_origin}/login.html?next=admin.html" if next_origin else "/login.html?next=admin.html"
            return RedirectResponse(url=login, status_code=302)
        path = settings.site_root / "admin.html"
        if not path.is_file():
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        return FileResponse(path, media_type="text/html; charset=utf-8")

    @app.get("/p/{slug}", include_in_schema=False)
    async def cms_public_page(request: Request, slug: str):
        """CMS public HTML is owned by Next.js. FastAPI proxies (preview) or redirects."""
        from app.auth import get_user_id, is_admin
        from app.cms_boundary import is_reserved_cms_slug, normalize_cms_slug

        clean = normalize_cms_slug(slug)
        if not clean or is_reserved_cms_slug(clean):
            raise StarletteHTTPException(status_code=404, detail="Not Found")

        preview = str(request.query_params.get("preview") or "") in {"1", "true", "yes"}
        inline = str(request.query_params.get("inline") or "") in {"1", "true", "yes"}
        admin_ok = is_admin(get_user_id(request))
        if (preview or inline) and not admin_ok:
            raise StarletteHTTPException(status_code=404, detail="Not Found")

        next_origin = settings.next_public_origin or "http://127.0.0.1:3000"
        qs = str(request.url.query or "")
        target = f"{next_origin}/p/{clean}"
        if qs:
            target = f"{target}?{qs}"

        if preview or inline:
            import urllib.error
            import urllib.request

            req = urllib.request.Request(
                target,
                headers={
                    "Accept": "text/html",
                    "Cookie": request.headers.get("cookie") or "",
                    "User-Agent": request.headers.get("user-agent") or "imprint-cms-proxy",
                },
                method="GET",
            )
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    body = resp.read()
                    ctype = resp.headers.get("Content-Type") or "text/html; charset=utf-8"
                    return HTMLResponse(content=body, status_code=resp.status, media_type=ctype)
            except urllib.error.HTTPError as exc:
                raise StarletteHTTPException(
                    status_code=exc.code if exc.code in (401, 403, 404) else 502,
                    detail="CMS preview unavailable",
                ) from None
            except Exception:
                raise StarletteHTTPException(
                    status_code=502, detail="Next.js CMS preview unavailable — run npm run dev:web"
                ) from None

        return RedirectResponse(url=target, status_code=307)


def mount_static(app: FastAPI) -> None:
    """Mount static assets last so page + API routes take precedence."""
    js_dir = settings.static_dir / "js"
    css_dir = settings.static_dir / "css"
    if js_dir.is_dir():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    if css_dir.is_dir():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
