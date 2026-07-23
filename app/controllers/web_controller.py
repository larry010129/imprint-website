"""Web routes — renders the site's Jinja2 templates from the page registry."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.routes import ALL_PAGES, PAGE_404, STANDALONE_PAGES, PageMeta
from config.settings import settings
from app.youtube_channel import fetch_latest_channel_video, resolve_channel_id

templates = Jinja2Templates(directory=str(settings.templates_dir))
_FRAGMENTS_DIR = settings.templates_dir / "fragments"
_FEATURED_VIDEO_PATH = Path(__file__).resolve().parent.parent / "data" / "featured-video.json"
_FEATURED_YOUTUBE_LATEST_PATH = Path(__file__).resolve().parent.parent / "data" / "featured-youtube-latest.json"


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


def _context(request: Request, meta: PageMeta) -> dict:
    context = {
        "request": request,
        "title": meta.title,
        "description": meta.description,
        "canonical_path": meta.canonical_path,
        "og_title": meta.og_title,
        "og_description": meta.og_description,
        "og_image": meta.og_image,
        "breadcrumbs": meta.breadcrumbs,
        "mvc_page": meta.mvc_page,
        "extra_body_class": meta.extra_body_class,
        "extra_head_blocks": meta.extra_head_blocks,
    }
    if meta.content_fragment:
        context["content_html"] = _load_fragment(meta.content_fragment)
    if meta.route == "/about.html":
        context["featured_video"] = load_featured_video()
        context["youtube_latest_video"] = load_youtube_latest_video()
    return context


def _make_handler(meta: PageMeta, status_code: int = 200):
    async def handler(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request, meta.template, _context(request, meta), status_code=status_code
        )

    return handler


def register_pages(app: FastAPI) -> None:
    for meta in [*ALL_PAGES, *STANDALONE_PAGES]:
        app.add_api_route(meta.route, _make_handler(meta), methods=["GET"], include_in_schema=False)

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
        # Defense-in-depth: the admin API is already guarded per-route, and
        # admin.js redirects non-admins client-side — but don't hand the admin
        # shell to anonymous visitors at all. Serve it only to a signed-in admin.
        from app.auth import get_user_id, is_admin

        if not is_admin(get_user_id(request)):
            return RedirectResponse(url="/login.html?next=admin.html", status_code=302)
        path = settings.site_root / "admin.html"
        if not path.is_file():
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        return FileResponse(path, media_type="text/html; charset=utf-8")

    @app.get("/s/{token}", include_in_schema=False)
    async def share_config(request: Request, token: str) -> HTMLResponse:
        from config.routes import STANDALONE_SHARE_SUMMARY

        return templates.TemplateResponse(
            request,
            STANDALONE_SHARE_SUMMARY.template,
            _context(request, STANDALONE_SHARE_SUMMARY),
        )

    @app.exception_handler(StarletteHTTPException)
    async def not_found(request: Request, exc: StarletteHTTPException) -> HTMLResponse:
        if exc.status_code != 404:
            return HTMLResponse(content=exc.detail, status_code=exc.status_code)
        return await _make_handler(PAGE_404, status_code=404)(request)


def mount_static(app: FastAPI) -> None:
    """Mount static assets last so page + API routes take precedence."""
    js_dir = settings.static_dir / "js"
    css_dir = settings.static_dir / "css"
    if js_dir.is_dir():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    if css_dir.is_dir():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
