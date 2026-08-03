"""Web routes — Jinja2 SSR pages, static mounts, admin shell, CMS public pages."""

from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.routes import ALL_PAGES, PAGE_404, STANDALONE_PAGES, STANDALONE_SHARE_SUMMARY, PageMeta
from config.settings import settings
from app.youtube_channel import fetch_latest_channel_video, resolve_channel_id

templates = Jinja2Templates(directory=str(settings.templates_dir))
templates.env.globals["google_client_id"] = settings.google_client_id
templates.env.globals["recaptcha_site_key"] = settings.recaptcha_site_key

# Fragments live under content/site/fragments (not templates/).
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
    """Primary page-image slot for Jinja page context."""
    rows = rows if rows is not None else _load_page_images(route)
    preferred = {
        "/about.html": "cinema",
        "/what-is-dna-diamond.html": "intro",
    }.get(route, "hero")
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


def _load_faq_public() -> dict:
    """Published FAQ categories for /faq.html (DB first, seed fallback)."""
    from app.content import faq_public_from_seed, fetch_faq_public
    from app.database import get_connection

    try:
        with get_connection() as conn, conn.cursor() as cur:
            data = fetch_faq_public(cur)
        if data.get("categories"):
            return data
    except Exception:
        pass
    return faq_public_from_seed()


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


def _load_gold_quote_bootstrap() -> dict | None:
    """Last-known gold quote from DB for SSR on /gold-price.html."""
    try:
        from app.bot_gold import build_payload_from_cache
        from app.database import get_connection

        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select * from gold_price_cache where id = 1")
            row = cur.fetchone()
        if row and float(row.get("xau_per_gram") or 0) > 0:
            payload = build_payload_from_cache(row)
            return {
                "quote": payload["quote"],
                "alloyRates": payload["alloyRates"],
                "metals": payload.get("metals"),
            }
    except Exception:
        return None
    return None


def _context(request: Request, meta: PageMeta) -> dict:
    page_images = _load_page_images(meta.route)
    page_image = _load_page_image(meta.route, page_images)
    page_copy_slots = _load_page_copy_slots(meta.route)
    lcp_image = None
    if page_image and meta.route not in {"/"}:
        lcp_image = page_image.get("display_webp") or page_image.get("display_url")
    context = {
        "request": request,
        "title": meta.title,
        "description": meta.description,
        "canonical_path": meta.canonical_path,
        "robots": meta.robots,
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
        "lcp_image_type": "image/webp" if lcp_image and str(lcp_image).endswith(".webp") else None,
        "site_cms_sections": [],
        "site_cms_sections_by_anchor": {},
        "site_cms_edit": False,
        "cms_page": {"title": meta.title, "slug": "", "site_route": meta.route},
        "cms_faq_items": [],
        "cms_faq_all_items": [],
        "cms_faq_by_category": {},
        "cms_testimonials": [],
        "faq_public": {"categories": [], "teaser": [], "items": []},
    }
    if meta.content_fragment:
        context["content_html"] = _load_fragment(meta.content_fragment)
    if meta.route == "/faq.html":
        context["faq_public"] = _load_faq_public()
    if meta.route in {"/", "/about.html"}:
        context["featured_video"] = load_featured_video()
    if meta.route == "/about.html":
        context["youtube_latest_video"] = load_youtube_latest_video()
    if meta.route == "/gold-price.html":
        context["gold_quote_bootstrap"] = _load_gold_quote_bootstrap()
    # Live env read so register page picks up keys without process restart in tests.
    from app.captcha import recaptcha_site_key as _recaptcha_site_key

    context["recaptcha_site_key"] = _recaptcha_site_key()
    return context


def _make_handler(meta: PageMeta, status_code: int = 200):
    async def handler(request: Request) -> HTMLResponse:
        from app.auth import get_user_id, is_admin
        from app.cms_copy_slots import apply_page_copy_slots
        from app.page_image_slots import apply_page_image_slots

        site_edit = (
            str(request.query_params.get("cms_edit") or "").lower() in {"1", "true", "yes"}
            and is_admin(get_user_id(request))
        )
        context = _context(request, meta)
        context["site_cms_edit"] = site_edit
        context.update(_load_site_cms_bundle(meta.route, visible_only=not site_edit))
        response = templates.TemplateResponse(
            request, meta.template, context, status_code=status_code
        )
        html = response.body.decode(response.charset)
        html = apply_page_image_slots(html, meta.route, context["page_images"])
        html = apply_page_copy_slots(html, meta.route, context["page_copy_slots"])
        if site_edit:
            page_key = json.dumps(meta.route)
            edit_boot = (
                f"<script>window.__CMS_SITE_PAGE_KEY__={page_key};</script>"
                '<script src="/js/site-inline-edit.js?v=6"></script>'
                '<script src="/js/cms-inline-edit.js?v=10"></script>'
                '<script src="/js/cms-canvas-controls.js?v=1"></script>'
            )
            html = html.replace(
                "<body ",
                f'<body data-cms-site-edit="1" data-cms-inline="1" '
                f'data-cms-page-key={json.dumps(meta.route)} ',
                1,
            )
            html = html.replace("</body>", f"{edit_boot}</body>", 1)
            response.headers["Cache-Control"] = "no-store"
        response.body = html.encode(response.charset)
        response.headers["content-length"] = str(len(response.body))
        return response

    return handler


def register_pages(app: FastAPI) -> None:
    """Register Jinja page routes, health, admin shell, share + CMS public pages."""

    @app.api_route("/health", methods=["GET", "HEAD"], include_in_schema=False)
    async def api_health() -> JSONResponse:
        """Render / load-balancer health — must not 404 or the API service is SIGTERM'd."""
        return JSONResponse({"ok": True, "service": "imprint-api"})

    # Include HEAD: Render probes HEAD / (405 if GET-only → deploy marked unhealthy).
    for meta in [*ALL_PAGES, *STANDALONE_PAGES]:
        app.add_api_route(
            meta.route,
            _make_handler(meta),
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )

    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon() -> FileResponse:
        return FileResponse(settings.site_root / "favicon.svg")

    @app.get("/robots.txt", include_in_schema=False)
    async def robots() -> FileResponse:
        return FileResponse(settings.site_root / "robots.txt")

    @app.get("/llms.txt", include_in_schema=False)
    async def llms_txt() -> FileResponse:
        return FileResponse(settings.site_root / "llms.txt", media_type="text/plain; charset=utf-8")

    @app.get("/sitemap.xml", include_in_schema=False)
    async def sitemap() -> FileResponse:
        return FileResponse(settings.site_root / "sitemap.xml")

    @app.get("/admin.html", include_in_schema=False)
    async def admin_page(request: Request):
        from app.auth import get_user_id, is_admin

        if not is_admin(get_user_id(request)):
            return RedirectResponse(url="/login.html?next=admin.html", status_code=302)
        path = settings.site_root / "admin.html"
        if not path.is_file():
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        return FileResponse(path, media_type="text/html; charset=utf-8")

    @app.get("/s/{token}", include_in_schema=False)
    async def share_config(request: Request, token: str) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            STANDALONE_SHARE_SUMMARY.template,
            _context(request, STANDALONE_SHARE_SUMMARY),
        )

    @app.get("/p/{slug}", include_in_schema=False)
    async def cms_public_page(request: Request, slug: str) -> HTMLResponse:
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

        try:
            if preview:
                bundle = _fetch_public_cms_page(clean, visible_only=False)
            else:
                time_bucket = int(monotonic() // _PAGE_IMAGE_CACHE_TTL_SECONDS)
                bundle = deepcopy(_fetch_public_cms_page_cached(clean, time_bucket))
        except Exception:
            raise StarletteHTTPException(status_code=404, detail="Not Found") from None

        if not bundle:
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        page = bundle["page"]
        faq = bundle.get("faq") or {}
        testimonials = bundle.get("testimonials") or []
        if not page:
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        if page.get("status") != "published" and not (preview and admin_ok):
            raise StarletteHTTPException(status_code=404, detail="Not Found")

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

        # Admin editor iframe: bare shell (no site nav/footer).
        embed = preview or inline
        meta = bundle.get("meta") or {}
        lcp_section_id = None if embed else meta.get("lcp_section_id")
        lcp_image = None if embed else meta.get("lcp_image")
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
            "lcp_image": lcp_image,
            "lcp_image_type": meta.get("lcp_image_type") if lcp_image else None,
            "cms_lcp_section_id": lcp_section_id,
            "cms_page": page,
            "cms_sections": page.get("sections") or bundle.get("sections") or [],
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
            return HTMLResponse(content=str(exc.detail), status_code=exc.status_code)
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
