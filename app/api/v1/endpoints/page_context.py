"""Page context for Next.js SSR — CMS slots, videos, auth flags, slotted body HTML."""

from __future__ import annotations

import json
import re

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from config.routes import ALL_PAGES, STANDALONE_PAGES, PageMeta
from config.settings import ROOT as REPO_ROOT
from config.settings import settings

router = APIRouter(tags=["page-context"])

_BODIES = REPO_ROOT / "content" / "site" / "bodies"
_REGISTRY = REPO_ROOT / "content" / "site" / "page-registry.json"

# Export leftover: BeautifulSoup sometimes unwraps <!-- @component ... --> into visible text.
_LEAKED_COMPONENT = re.compile(
    r"(?:<!--\s*)?@component\s+[^\n<>]+(?:-->)?\s*\n?",
    re.IGNORECASE,
)

_PAGES_BY_ROUTE: dict[str, PageMeta] = {
    p.route: p for p in [*ALL_PAGES, *STANDALONE_PAGES]
}


def _route_key(route: str) -> str:
    if route == "/":
        return "home"
    key = route.strip("/").replace("/", "__").replace(".html", "_html")
    return key or "home"


def _load_registry_entry(route: str) -> dict | None:
    if not _REGISTRY.is_file():
        return None
    try:
        rows = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return next((row for row in rows if row.get("route") == route), None)


def _read_body(route: str, body_key: str | None = None) -> str:
    key = body_key or _route_key(route)
    path = _BODIES / f"{key}.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"No body for {route}")
    html = path.read_text(encoding="utf-8")
    return _LEAKED_COMPONENT.sub("", html)


def _build_context(request: Request, route: str, *, include_body: bool) -> dict:
    from app.auth import get_user_id, is_admin
    from app.cms_copy_slots import apply_page_copy_slots
    from app.controllers import web_controller as wc
    from app.page_image_slots import apply_page_image_slots

    meta = _PAGES_BY_ROUTE.get(route)
    reg = _load_registry_entry(route)
    if meta is None and reg is None:
        # /s/{token} aliases share summary
        if route.startswith("/s/"):
            meta = _PAGES_BY_ROUTE.get("/share/summary.html")
            reg = _load_registry_entry("/share/summary.html")
            route = "/share/summary.html"
        else:
            raise HTTPException(status_code=404, detail="Unknown route")

    page_images = wc._load_page_images(route)
    page_image = wc._load_page_image(route, page_images)
    page_copy_slots = wc._load_page_copy_slots(route)

    site_edit = (
        str(request.query_params.get("cms_edit") or "").lower() in {"1", "true", "yes"}
        and is_admin(get_user_id(request))
    )

    lcp_image = None
    if page_image and route not in {"/", "/about.html"}:
        lcp_image = page_image.get("display_webp") or page_image.get("display_url")

    payload: dict = {
        "route": route,
        "google_client_id": settings.google_client_id,
        "page_images": page_images,
        "page_image": page_image,
        "page_copy_slots": page_copy_slots,
        "lcp_image": lcp_image,
        "lcp_image_type": "image/webp" if lcp_image and str(lcp_image).endswith(".webp") else None,
        "site_cms_edit": site_edit,
        "featured_video": None,
        "youtube_latest_video": None,
        "layout": (reg or {}).get("layout") or "site",
        "extra_css": (reg or {}).get("extra_css") or [],
        "extra_scripts": (reg or {}).get("extra_scripts") or [],
        "main_class": (reg or {}).get("main_class") or "",
        "mvc_page": (meta.mvc_page if meta else (reg or {}).get("mvc_page")),
        "extra_body_class": (meta.extra_body_class if meta else (reg or {}).get("extra_body_class")),
        "title": meta.title if meta else (reg or {}).get("title"),
        "description": meta.description if meta else (reg or {}).get("description"),
        "canonical_path": meta.canonical_path if meta else (reg or {}).get("canonical_path"),
        "og_title": meta.og_title if meta else (reg or {}).get("og_title"),
        "og_description": meta.og_description if meta else (reg or {}).get("og_description"),
        "og_image": meta.og_image if meta else (reg or {}).get("og_image"),
        "breadcrumbs": list(meta.breadcrumbs) if meta else (reg or {}).get("breadcrumbs") or [],
        "extra_head_blocks": (
            [wc._strip_public_phone_metadata(b) for b in meta.extra_head_blocks]
            if meta
            else (reg or {}).get("extra_head_blocks") or []
        ),
        "head_extras": (reg or {}).get("head_extras") or [],
        "robots": (reg or {}).get("robots"),
    }

    if route in {"/", "/about.html"}:
        payload["featured_video"] = wc.load_featured_video()
    if route == "/about.html":
        payload["youtube_latest_video"] = wc.load_youtube_latest_video()

    cms_bundle = wc._load_site_cms_bundle(route, visible_only=not site_edit)
    payload.update(
        {
            "cms_page": cms_bundle.get("cms_page"),
            "site_cms_sections": cms_bundle.get("site_cms_sections") or [],
            "site_cms_sections_by_anchor": cms_bundle.get("site_cms_sections_by_anchor") or {},
            "cms_faq_items": cms_bundle.get("cms_faq_items") or [],
            "cms_testimonials": cms_bundle.get("cms_testimonials") or [],
        }
    )

    if include_body:
        body_key = (reg or {}).get("body_key") or _route_key(route)
        html = _read_body(route, body_key)
        html = apply_page_image_slots(html, route, page_images)
        html = apply_page_copy_slots(html, route, page_copy_slots)
        gid = settings.google_client_id or ""
        if gid:
            html = html.replace('data-google-client-id=""', f'data-google-client-id="{gid}"')
            html = html.replace("data-google-client-id=''", f"data-google-client-id='{gid}'")
        payload["body_html"] = html

    return payload


@router.get("/page-context")
async def page_context(
    request: Request,
    route: str = Query(..., min_length=1, max_length=200),
    include_body: bool = Query(True),
) -> JSONResponse:
    """SSR helper for Next: metadata-adjacent data + optional slotted body HTML."""
    if not route.startswith("/"):
        route = "/" + route
    payload = _build_context(request, route, include_body=include_body)
    headers = {}
    if payload.get("site_cms_edit"):
        headers["Cache-Control"] = "no-store"
    return JSONResponse(payload, headers=headers)


@router.post("/page-context/apply")
async def apply_slots(request: Request) -> JSONResponse:
    """Apply image/copy slots to an HTML fragment (marker contract)."""
    from app.cms_copy_slots import apply_page_copy_slots
    from app.controllers import web_controller as wc
    from app.page_image_slots import apply_page_image_slots

    try:
        data = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    route = str(data.get("route") or "")
    html = str(data.get("html") or "")
    if not route.startswith("/"):
        raise HTTPException(status_code=400, detail="route required")
    images = wc._load_page_images(route)
    copies = wc._load_page_copy_slots(route)
    html = apply_page_image_slots(html, route, images)
    html = apply_page_copy_slots(html, route, copies)
    return JSONResponse({"html": html})
