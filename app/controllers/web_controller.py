"""Web routes — renders the site's Jinja2 templates from the page registry."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.routes import ALL_PAGES, PAGE_404, STANDALONE_PAGES, PageMeta
from config.settings import settings
from app.youtube_channel import fetch_latest_channel_video, resolve_channel_id

templates = Jinja2Templates(directory=str(settings.templates_dir))
templates.env.globals["google_client_id"] = settings.google_client_id
_FRAGMENTS_DIR = settings.templates_dir / "fragments"
_FEATURED_VIDEO_PATH = Path(__file__).resolve().parent.parent / "data" / "featured-video.json"
_FEATURED_YOUTUBE_LATEST_PATH = Path(__file__).resolve().parent.parent / "data" / "featured-youtube-latest.json"
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


@lru_cache(maxsize=2)
def _fetch_page_images_cached(_time_bucket: int) -> dict[str, list[dict]]:
    from app.content import fetch_all_page_images
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        grouped: dict[str, list[dict]] = {}
        for row in fetch_all_page_images(cur):
            grouped.setdefault(row["page_key"], []).append(row)
        return grouped


def _load_page_images(route: str) -> list[dict]:
    try:
        time_bucket = int(monotonic() // _PAGE_IMAGE_CACHE_TTL_SECONDS)
        return _fetch_page_images_cached(time_bucket).get(route, [])
    except Exception:
        return []


def _load_page_image(route: str) -> dict | None:
    """Backward-compatible primary slot used by existing Jinja templates."""
    rows = _load_page_images(route)
    preferred = "cinema" if route == "/about.html" else "hero"
    return next((row for row in rows if row.get("slot_key") == preferred), None)


def clear_page_image_cache() -> None:
    _fetch_page_images_cached.cache_clear()


@lru_cache(maxsize=2)
def _fetch_page_copy_cached(_time_bucket: int) -> dict[str, list[dict]]:
    from app.cms_copy_slots import fetch_all_copy_slots
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        grouped: dict[str, list[dict]] = {}
        for row in fetch_all_copy_slots(cur):
            grouped.setdefault(row["page_key"], []).append(row)
        return grouped


def _load_page_copy_slots(route: str) -> list[dict]:
    try:
        time_bucket = int(monotonic() // _PAGE_IMAGE_CACHE_TTL_SECONDS)
        return _fetch_page_copy_cached(time_bucket).get(route, [])
    except Exception:
        return []


def clear_page_copy_cache() -> None:
    _fetch_page_copy_cached.cache_clear()


def _context(request: Request, meta: PageMeta) -> dict:
    page_images = _load_page_images(meta.route)
    page_image = _load_page_image(meta.route)
    page_copy_slots = _load_page_copy_slots(meta.route)
    lcp_image = None
    if page_image and meta.route not in {"/", "/about.html"}:
        lcp_image = page_image.get("display_webp") or page_image.get("display_url")
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
        "extra_head_blocks": [_strip_public_phone_metadata(block) for block in meta.extra_head_blocks],
        "page_image": page_image,
        "page_images": page_images,
        "page_copy_slots": page_copy_slots,
        "lcp_image": lcp_image,
        "lcp_image_type": "image/webp" if lcp_image and lcp_image.endswith(".webp") else None,
    }
    if meta.content_fragment:
        context["content_html"] = _load_fragment(meta.content_fragment)
    if meta.route in {"/", "/about.html"}:
        context["featured_video"] = load_featured_video()
    if meta.route == "/about.html":
        context["youtube_latest_video"] = load_youtube_latest_video()
    return context


def _make_handler(meta: PageMeta, status_code: int = 200):
    async def handler(request: Request) -> HTMLResponse:
        from app.auth import get_user_id, is_admin
        from app.cms_copy_slots import apply_page_copy_slots
        from app.page_image_slots import apply_page_image_slots

        context = _context(request, meta)
        response = templates.TemplateResponse(
            request, meta.template, context, status_code=status_code
        )
        html = response.body.decode(response.charset)
        html = apply_page_image_slots(html, meta.route, context["page_images"])
        html = apply_page_copy_slots(html, meta.route, context["page_copy_slots"])
        site_edit = (
            str(request.query_params.get("cms_edit") or "").lower() in {"1", "true", "yes"}
            and is_admin(get_user_id(request))
        )
        if site_edit:
            page_key = json.dumps(meta.route)
            edit_boot = (
                f"<script>window.__CMS_SITE_PAGE_KEY__={page_key};</script>"
                '<script src="/js/site-inline-edit.js?v=1"></script>'
            )
            html = html.replace(
                "<body ",
                f'<body data-cms-site-edit="1" data-cms-page-key={json.dumps(meta.route)} ',
                1,
            )
            html = html.replace("</body>", f"{edit_boot}</body>", 1)
            response.headers["Cache-Control"] = "no-store"
        response.body = html.encode(response.charset)
        response.headers["content-length"] = str(len(response.body))
        return response

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

    @app.get("/p/{slug}", include_in_schema=False)
    async def cms_public_page(request: Request, slug: str) -> HTMLResponse:
        from app.auth import get_user_id, is_admin
        from app.cms_boundary import is_reserved_cms_slug, normalize_cms_slug
        from app.cms_pages import SECTION_TYPES, ensure_cms_pages_schema, fetch_page_with_sections
        from app.content import fetch_faq_public, fetch_published_testimonials
        from app.database import get_connection

        clean = normalize_cms_slug(slug)
        if not clean or is_reserved_cms_slug(clean):
            raise StarletteHTTPException(status_code=404, detail="Not Found")

        preview = str(request.query_params.get("preview") or "") in {"1", "true", "yes"}
        inline = str(request.query_params.get("inline") or "") in {"1", "true", "yes"}
        admin_ok = is_admin(get_user_id(request))
        if (preview or inline) and not admin_ok:
            raise StarletteHTTPException(status_code=404, detail="Not Found")

        try:
            with get_connection() as conn, conn.cursor() as cur:
                ensure_cms_pages_schema(cur)
                page = fetch_page_with_sections(cur, slug=clean, visible_only=not preview)
                faq = fetch_faq_public(cur)
                testimonials = fetch_published_testimonials(cur)
        except Exception:
            raise StarletteHTTPException(status_code=404, detail="Not Found") from None

        if not page:
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        if page.get("status") != "published" and not (preview and admin_ok):
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        page["sections"] = [
            section
            for section in (page.get("sections") or [])
            if section.get("type") in SECTION_TYPES
        ]

        faq_items = faq.get("teaser") or []
        if not faq_items:
            faq_items = [
                item
                for cat in (faq.get("categories") or [])
                for item in (cat.get("items") or [])
            ]
        faq_by_category = {
            str(cat.get("id")): cat.get("items") or []
            for cat in (faq.get("categories") or [])
        }

        # Admin editor iframe: bare shell (no site nav/footer) so each page
        # preview is unique content only. Public /p/{slug} keeps full site chrome.
        embed = preview or inline
        context = {
            "request": request,
            "layout": "layouts/cms-embed.html" if embed else "layouts/base.html",
            "title": page.get("title") or "銘印鑽石",
            "description": page.get("meta_description") or "",
            "canonical_path": f"p/{page['slug']}",
            "og_title": page.get("title") or "",
            "og_description": page.get("meta_description") or "",
            "og_image": "images/hero/imprint-diamond-family-memorial.jpg",
            "breadcrumbs": [],
            "mvc_page": "cms",
            "extra_body_class": "cms-modular",
            "extra_head_blocks": [],
            "page_image": None,
            "page_images": [],
            "lcp_image": None,
            "lcp_image_type": None,
            "cms_page": page,
            "cms_sections": page.get("sections") or [],
            "cms_preview": preview,
            "cms_inline": inline,
            "cms_faq_items": faq_items,
            "cms_faq_all_items": faq.get("items") or [],
            "cms_faq_by_category": faq_by_category,
            "cms_testimonials": testimonials,
        }
        return templates.TemplateResponse(request, "pages/cms_page.html", context)

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
