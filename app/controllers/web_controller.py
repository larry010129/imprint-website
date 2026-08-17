"""Web routes — Jinja2 SSR pages, static mounts, admin shell, CMS public pages."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from config.routes import (
    ALL_PAGES,
    JEWELRY_STYLE_REDIRECTS,
    PAGE_404,
    STANDALONE_PAGES,
    STANDALONE_SHARE_SUMMARY,
    PageMeta,
)
from config.settings import settings
from app.youtube_channel import fetch_latest_channel_video, resolve_channel_id

log = logging.getLogger(__name__)
templates = Jinja2Templates(directory=str(settings.templates_dir))
templates.env.globals["google_client_id"] = settings.google_client_id
templates.env.globals["recaptcha_site_key"] = settings.recaptcha_site_key


def shop_media_config() -> dict[str, str]:
    """Public Storage bases for shop stills. Disk paths when SUPABASE_URL missing."""
    from app.storage import diamond_media_base

    base = diamond_media_base()
    origin = (settings.supabase_url or "").rstrip("/")
    if not base:
        return {
            "supabaseOrigin": origin,
            "siteImagesRoot": "/static/images/",
            "imageRoot": "/static/images/shop-product/",
        }
    root = base.rstrip("/") + "/"
    return {
        "supabaseOrigin": origin,
        "siteImagesRoot": root,
        "imageRoot": f"{root}shop-product/",
    }


def _diamond_media_base_global() -> str:
    from app.storage import diamond_media_base

    return diamond_media_base()


def _share_image_url_global(og_image: str | None = None) -> str:
    from app.image_urls import share_image_url

    return share_image_url(og_image)


templates.env.globals["shop_media_config"] = shop_media_config
templates.env.globals["diamond_media_base"] = _diamond_media_base_global
templates.env.globals["share_image_url"] = _share_image_url_global


# mtime-keyed so CSS edits apply without process restart (dev + hot reload).
_INLINE_CSS_CACHE: dict[str, tuple[float, str]] = {}


def _load_inline_css(filename: str) -> str:
    """Read a public/css/* file for inlining (e.g. base.css in <head>).

    Removes one render-blocking request on every page load — PageSpeed's
    network trace showed each small same-origin CSS file costing 160-490ms
    of request overhead regardless of its (tiny) transfer size. Reloads when
    the file mtime changes so local CSS edits show without a server restart.
    """
    path = settings.static_dir / "css" / filename
    if not path.is_file():
        return ""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return ""
    cached = _INLINE_CSS_CACHE.get(filename)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    text = path.read_text(encoding="utf-8")
    _INLINE_CSS_CACHE[filename] = (mtime, text)
    return text


templates.env.globals["inline_css"] = _load_inline_css

# Fragments live under content/site/fragments (not templates/).
_FRAGMENTS_DIR = settings.site_content_dir / "fragments"
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


def load_featured_video(request: Request | None = None) -> dict | None:
    """Return featured-video gallery for SSR (cms_kv / legacy file; no network)."""
    from app.featured_video import public_featured_payload, read_featured_video_file

    return public_featured_payload(read_featured_video_file())


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


def _resolve_fragment_path(relpath: str) -> Path:
    """Resolve legacy fragment names and the current body-file layout."""
    relative = Path(relpath)
    if relative.is_absolute() or ".." in relative.parts:
        raise StarletteHTTPException(status_code=404, detail="Not Found")

    path = _FRAGMENTS_DIR / relative
    if path.is_file():
        return path

    parts = relative.parts
    filename = relative.name
    stem = Path(filename).stem
    if parts and parts[0] == "series":
        body_name = f"series__{stem}.html"
    elif parts and parts[0] == "jewelry_category":
        body_name = f"jewelry__{stem}.html"
    elif parts and parts[0] == "jewelry_style" and "-" in stem:
        category, style = stem.split("-", 1)
        body_name = f"jewelry__{category}__{style}.html"
    else:
        body_name = "__".join(parts)
    body_path = settings.site_content_dir / "bodies" / body_name
    if body_path.is_file():
        return body_path
    raise StarletteHTTPException(status_code=404, detail="Not Found")


@lru_cache(maxsize=None)
def _load_fragment(relpath: str) -> str:
    path = _resolve_fragment_path(relpath)
    if not path.is_file():
        raise StarletteHTTPException(status_code=404, detail="Not Found")
    return path.read_text(encoding="utf-8")


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
        "/about": "cinema",
        "/what-is-dna-diamond": "intro",
    }.get(route, "hero")
    return next((row for row in rows if row.get("slot_key") == preferred), None)


def clear_page_image_cache() -> None:
    _fetch_page_images_cached.cache_clear()
    from app.content_cache import clear_content_api_caches

    clear_content_api_caches()


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


def _load_engagement_rings() -> list[dict]:
    """Four iconic ring cards for /jewelry/engagement/ (CMS product picks)."""
    from app.database import get_connection
    from app.engagement_rings import FALLBACK_CARDS, resolve_engagement_ring_cards

    try:
        with get_connection() as conn, conn.cursor() as cur:
            return resolve_engagement_ring_cards(cur)
    except Exception:
        return [dict(card) for card in FALLBACK_CARDS]


def _load_faq_public() -> dict:
    """Published FAQ categories for /faq (Supabase only; empty on miss/error)."""
    from app.content import fetch_faq_public
    from app.database import get_connection

    empty: dict = {"categories": [], "teaser": [], "items": []}
    try:
        with get_connection() as conn, conn.cursor() as cur:
            return fetch_faq_public(cur)
    except Exception:
        log.exception("FAQ SSR: Supabase fetch failed")
        return empty


def _faq_page_json_ld(faq_public: dict) -> str:
    """FAQPage JSON-LD from live faq_public (plain-text answers only)."""
    entities: list[dict] = []
    for cat in faq_public.get("categories") or []:
        for item in cat.get("items") or []:
            question = str(item.get("question") or "").strip()
            answer = str(item.get("answer") or "").strip()
            if not question or not answer:
                continue
            entities.append(
                {
                    "@type": "Question",
                    "name": question,
                    "acceptedAnswer": {"@type": "Answer", "text": answer},
                }
            )
    if not entities:
        return ""
    return json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": entities,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


STORIES_SSR_LIMIT = 12
JOURNAL_SSR_LIMIT = 12


def _load_stories_ssr(limit: int = STORIES_SSR_LIMIT) -> list[dict]:
    """First N published testimonials for SSR on /stories (Supabase only)."""
    from app.content import fetch_published_testimonials
    from app.database import get_connection

    try:
        with get_connection() as conn, conn.cursor() as cur:
            return fetch_published_testimonials(cur, limit=limit, offset=0)
    except Exception:
        log.exception("stories SSR: Supabase fetch failed")
        return []


def _load_journal_ssr(limit: int = JOURNAL_SSR_LIMIT) -> list[dict]:
    """Published journal posts for SSR teasers on /journal."""
    from app.content import fetch_published_journal_posts
    from app.database import get_connection

    try:
        with get_connection() as conn, conn.cursor() as cur:
            return fetch_published_journal_posts(cur, limit=limit, offset=0)
    except Exception:
        return []


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

            bundle["cms_testimonials"] = fetch_published_testimonials(
                cur, limit=24, offset=0
            )
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
    from app.content_cache import clear_content_api_caches

    clear_content_api_caches()


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
    """Last-known gold quote from DB for SSR on /gold-price."""
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


def _build_canonical_url(canonical_path: str | None, *, omit: bool = False) -> str | None:
    """Absolute canonical from settings.public_base_url + path; None omits the tag."""
    if omit:
        return None
    base = settings.public_base_url.rstrip("/")
    path = (canonical_path or "").strip().lstrip("/")
    if not path:
        return f"{base}/"
    return f"{base}/{path}"


def _context(request: Request, meta: PageMeta, *, include_journal_ssr: bool = True) -> dict:
    # /shop/calculator/ has no image slots; catalog SSR is not free (per-category
    # fetch_catalog_rows) and JS already boots via /api/catalog + shop.js.
    is_shop_calculator = meta.route == "/shop/calculator/"
    page_images = [] if is_shop_calculator else _load_page_images(meta.route)
    page_image = _load_page_image(meta.route, page_images)
    page_copy_slots = _load_page_copy_slots(meta.route)
    lcp_image = None
    if page_image and meta.route not in {"/"}:
        lcp_image = page_image.get("display_webp") or page_image.get("display_url")
    omit_canonical = meta.route == PAGE_404.route
    context = {
        "request": request,
        "title": meta.title,
        "description": meta.description,
        "canonical_path": meta.canonical_path,
        "canonical_url": _build_canonical_url(meta.canonical_path, omit=omit_canonical),
        "robots": meta.robots,
        "og_title": meta.og_title,
        "og_description": meta.og_description,
        "og_image": meta.og_image,
        "keywords": meta.keywords,
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
        "engagement_rings": [],
        "cms_page": {"title": meta.title, "slug": "", "site_route": meta.route},
        "cms_faq_items": [],
        "cms_faq_all_items": [],
        "cms_faq_by_category": {},
        "cms_testimonials": [],
        "faq_public": {"categories": [], "teaser": [], "items": []},
        "faq_json_ld": "",
        "stories_ssr": [],
        "journal_ssr": [],
        "shop_catalog_ssr": [],
    }
    if meta.content_fragment:
        context["content_html"] = _load_fragment(meta.content_fragment)
    if meta.route == "/faq":
        context["faq_public"] = _load_faq_public()
        context["faq_json_ld"] = _faq_page_json_ld(context["faq_public"])
    if meta.route == "/stories":
        context["stories_ssr"] = _load_stories_ssr()
    if meta.route == "/journal" and include_journal_ssr:
        context["journal_ssr"] = _load_journal_ssr()
    if meta.route in {"/", "/about"}:
        context["featured_video"] = load_featured_video(request)
    if meta.route == "/about":
        context["youtube_latest_video"] = load_youtube_latest_video()
    if meta.route == "/jewelry/engagement/":
        context["engagement_rings"] = _load_engagement_rings()
    if meta.route == "/gold-price":
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
        from app.image_urls import rewrite_shop_stills_in_html

        html = rewrite_shop_stills_in_html(html)
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


# Legacy on-disk shells; excluded from generic *.html→clean PageMeta redirects.
# Canonical CMS URLs: /admin, /admin/settings, /admin/plugins (see register_pages).
_ADMIN_LEGACY_TO_CANONICAL: dict[str, str] = {
    "/admin.html": "/admin",
    "/admin1.html": "/admin",
    "/admin1-settings.html": "/admin/settings",
    "/admin1-plugins.html": "/admin/plugins",
    "/admin1-release-notes.html": "/admin/release-notes",
}


_ADMIN_HTML_SHELLS = frozenset(
    {
        *_ADMIN_LEGACY_TO_CANONICAL.keys(),
        "/admin1-login.html",
    }
)


def _legacy_html_redirects() -> dict[str, str]:
    """Map former `/foo.html` PageMeta routes to extensionless `/foo`."""
    mapping: dict[str, str] = {}
    for meta in [*ALL_PAGES, *STANDALONE_PAGES]:
        route = meta.route
        if route in {"/",} or route.endswith("/") or route.endswith(".html"):
            continue
        legacy = f"{route}.html"
        if legacy in _ADMIN_HTML_SHELLS:
            continue
        mapping[legacy] = route
    return mapping


def _make_html_redirect(target: str):
    async def redirect_html(request: Request) -> RedirectResponse:
        query = request.url.query
        location = f"{target}?{query}" if query else target
        return RedirectResponse(url=location, status_code=301)

    return redirect_html


def register_pages(app: FastAPI) -> None:
    """Register Jinja page routes, health, admin shell, share + CMS public pages."""

    @app.api_route("/health", methods=["GET", "HEAD"], include_in_schema=False)
    async def api_health() -> JSONResponse:
        """Render / load-balancer health — must not 404 or the API service is SIGTERM'd."""
        return JSONResponse({"ok": True, "service": "imprint-api"})

    def _shop_index_redirect(request: Request) -> RedirectResponse:
        query = request.url.query
        location = f"/shop/calculator/?{query}" if query else "/shop/calculator/"
        return RedirectResponse(url=location, status_code=302)

    for shop_index in ("/shop", "/shop/"):
        app.add_api_route(
            shop_index,
            _shop_index_redirect,
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )

    # 301 old *.html public page URLs → extensionless (query string preserved).
    for legacy, clean in _legacy_html_redirects().items():
        app.add_api_route(
            legacy,
            _make_html_redirect(clean),
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )

    # Retired jewelry style PDPs → live shop catalog.
    for retired, target in JEWELRY_STYLE_REDIRECTS.items():
        app.add_api_route(
            retired,
            _make_html_redirect(target),
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )

    # Include HEAD: Render probes HEAD / (405 if GET-only → deploy marked unhealthy).
    for meta in [*ALL_PAGES, *STANDALONE_PAGES]:
        app.add_api_route(
            meta.route,
            _make_handler(meta),
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )

    journal_meta = next((item for item in ALL_PAGES if item.route == "/journal"), None)
    if journal_meta is not None:
        @app.api_route(
            "/journal/{post_id}",
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )
        async def journal_post_detail(request: Request, post_id: str) -> HTMLResponse:
            from uuid import UUID

            from app.content import fetch_published_journal_post
            from app.database import get_connection

            try:
                post_uuid = UUID(post_id)
            except (ValueError, AttributeError):
                raise StarletteHTTPException(status_code=404, detail="Not Found") from None

            try:
                with get_connection() as conn, conn.cursor() as cur:
                    post = fetch_published_journal_post(cur, post_uuid)
            except Exception:
                raise StarletteHTTPException(status_code=404, detail="Not Found") from None
            if not post:
                raise StarletteHTTPException(status_code=404, detail="Not Found")

            title = str(post.get("title") or journal_meta.title).strip()
            body = str(post.get("body") or "").strip()
            context = _context(request, journal_meta, include_journal_ssr=False)
            canonical_path = f"journal/{post['id']}"
            context.update(
                {
                    "title": title,
                    "description": body[:160] or journal_meta.description,
                    "canonical_path": canonical_path,
                    "canonical_url": _build_canonical_url(canonical_path),
                    "og_title": title,
                    "og_description": body[:160] or journal_meta.description,
                    "breadcrumbs": [
                        (journal_meta.breadcrumbs[0][0], journal_meta.breadcrumbs[0][1]),
                        (journal_meta.breadcrumbs[1][0], "/journal"),
                        (title, None),
                    ],
                    "journal_post": post,
                }
            )
            return templates.TemplateResponse(request, journal_meta.template, context)

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

    def _admin_gated_html(request: Request, filename: str, next_path: str):
        """Serve an admin HTML shell; non-admins go to login with next=/admin…."""
        from app.auth import get_user_id, is_admin

        if not next_path.startswith("/") or next_path.startswith("//"):
            next_path = "/admin"
        if not is_admin(get_user_id(request)):
            return RedirectResponse(url=f"/login?next={next_path}", status_code=302)
        path = settings.site_root / filename
        if not path.is_file():
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        return FileResponse(path, media_type="text/html; charset=utf-8")

    # Official CMS shells (admin1 UI) at clean URLs.
    @app.api_route("/admin", methods=["GET", "HEAD"], include_in_schema=False)
    async def admin_page(request: Request):
        return _admin_gated_html(request, "admin1.html", "/admin")

    @app.api_route("/admin/settings", methods=["GET", "HEAD"], include_in_schema=False)
    async def admin_settings_page(request: Request):
        return _admin_gated_html(request, "admin1-settings.html", "/admin/settings")

    @app.api_route("/admin/plugins", methods=["GET", "HEAD"], include_in_schema=False)
    async def admin_plugins_page(request: Request):
        return _admin_gated_html(request, "admin1-plugins.html", "/admin/plugins")

    @app.api_route("/admin/release-notes", methods=["GET", "HEAD"], include_in_schema=False)
    async def admin_release_notes_page(request: Request):
        """Hidden editor — admin session + unlock cookie required."""
        from app.auth import get_user_id, is_admin
        from app.release_notes import require_unlock

        next_path = "/admin/release-notes"
        user_id = get_user_id(request)
        if not is_admin(user_id):
            return RedirectResponse(url=f"/login?next={next_path}", status_code=302)
        if not user_id or not require_unlock(request, user_id):
            return RedirectResponse(url="/admin", status_code=302)
        path = settings.site_root / "admin1-release-notes.html"
        if not path.is_file():
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        return FileResponse(path, media_type="text/html; charset=utf-8")

    # Deep-linkable admin tabs: /admin/<tab> serves the same admin1 shell.
    # Registered AFTER the explicit /admin/settings|plugins|release-notes routes
    # so those keep their own shells; single-segment {tab} never touches
    # /api/admin/* (different prefix) or static mounts (/css, /js, /static).
    @app.api_route("/admin/{tab}", methods=["GET", "HEAD"], include_in_schema=False)
    async def admin_tab_page(request: Request, tab: str):
        next_path = request.url.path
        return _admin_gated_html(request, "admin1.html", next_path)


    # Legacy *.html shells → canonical paths (query string preserved).
    for legacy, clean in _ADMIN_LEGACY_TO_CANONICAL.items():
        app.add_api_route(
            legacy,
            _make_html_redirect(clean),
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )

    @app.api_route("/admin1-login.html", methods=["GET", "HEAD"], include_in_schema=False)
    async def admin1_login_redirect() -> RedirectResponse:
        """Old admin1 login helper → site login with CMS next target."""
        return RedirectResponse(url="/login?next=/admin", status_code=302)

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
        cms_canonical_path = f"p/{page['slug']}"
        context = {
            "request": request,
            "layout": "layouts/cms-embed.html" if embed else "layouts/base.html",
            "title": page.get("title") or "銘印鑽石",
            "description": page.get("meta_description") or "",
            "canonical_path": cms_canonical_path,
            "canonical_url": _build_canonical_url(cms_canonical_path),
            "og_title": page.get("title") or "",
            "og_description": page.get("meta_description") or "",
            "og_image": "static/images/hero/imprint-diamond-family-memorial.jpg",
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
    async def not_found(request: Request, exc: StarletteHTTPException) -> Response:
        # register_pages used to replace FastAPI's JSON handler entirely, so
        # /api/* 401/403 became text/html and the admin UI showed "HTTP 403".
        if request.url.path.startswith("/api/"):
            return await http_exception_handler(request, exc)
        if exc.status_code != 404:
            return HTMLResponse(content=str(exc.detail), status_code=exc.status_code)
        return await _make_handler(PAGE_404, status_code=404)(request)


def _shop_still_redirect(folder: str):
    """302 leftover /static/images/{folder}/* to shop-media/site-images."""

    async def redirect_shop_still(request: Request, rest: str) -> RedirectResponse:
        from app.storage import SHOP_STILL_FOLDERS, site_image_public_url

        if folder not in SHOP_STILL_FOLDERS:
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        target = site_image_public_url(f"{folder}/{rest}")
        if not target:
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        query = request.url.query
        location = f"{target}?{query}" if query else target
        return RedirectResponse(url=location, status_code=302)

    return redirect_shop_still


def mount_static(app: FastAPI) -> None:
    """Mount static assets last so page + API routes take precedence."""
    # Leftover HTML/JS still hits /static/images/{diamonds|shop-product|products}.
    # Register before the /static mount so the 302 wins after those folders leave git.
    if settings.supabase_url:
        from app.storage import SHOP_STILL_FOLDERS

        for folder in sorted(SHOP_STILL_FOLDERS):
            app.add_api_route(
                f"/static/images/{folder}/{{rest:path}}",
                _shop_still_redirect(folder),
                methods=["GET", "HEAD"],
                include_in_schema=False,
            )
    js_dir = settings.static_dir / "js"
    css_dir = settings.static_dir / "css"
    if js_dir.is_dir():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    if css_dir.is_dir():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
