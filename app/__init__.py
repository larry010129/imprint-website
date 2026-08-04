"""Imprint Diamond — FastAPI application factory."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

from config.settings import settings

from app.controllers import (
    admin_controller,
    api_controller,
    auth_controller,
    cms_admin_controller,
    htmx_controller,
    notifications_controller,
    shop_controller,
    web_controller,
)

log = logging.getLogger(__name__)

# blob: required for admin/CMS crop UI (URL.createObjectURL local previews).
# img-src: self + data/blob + known hosts (Supabase media, Botpress, Google).
HTML_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.botpress.cloud "
    "https://files.bpcontent.cloud https://*.botpress.cloud "
    "https://accounts.google.com https://www.google.com https://www.gstatic.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob: https://*.supabase.co https://*.bpcontent.cloud "
    "https://*.botpress.cloud https://www.google.com https://www.gstatic.com "
    "https://lh3.googleusercontent.com; "
    "connect-src 'self' https://*.botpress.cloud wss://*.botpress.cloud "
    "https://cdn.botpress.cloud https://files.bpcontent.cloud "
    "https://accounts.google.com https://oauth2.googleapis.com "
    "https://people.googleapis.com "
    "https://www.google.com https://www.gstatic.com; "
    # 'self' required for CMS page-builder preview iframe (/p/{slug}?preview=1)
    # www.google.com / recaptcha.google.com required for reCAPTCHA v2 checkbox
    "frame-src 'self' https://www.google.com https://recaptcha.google.com "
    "https://accounts.google.com "
    "https://www.youtube.com https://www.youtube-nocookie.com "
    "https://*.botpress.cloud; "
    "form-action 'self'; "
    "frame-ancestors 'self'; object-src 'none'; base-uri 'self'"
)

HTML_PERMISSIONS_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
    "interest-cohort=(), browsing-topics=()"
)


def _startup_banner() -> None:
    from app.database import database_target_label, require_database_url

    api = settings.public_base_url
    label = "Diamond v3 on Render" if settings.is_render else "Diamond v3 local dev"
    dsn = require_database_url()
    print("")
    print(f"  {label}")
    print(f"  DB: {database_target_label(dsn)}")
    print(f"  Site (Jinja SSR): {api}/")
    print(f"  API: {api}/api/bot-gold")
    if not settings.is_render:
        print("  Browse http://127.0.0.1:8080/ — Next not required")
    print("")


def _startup_seed_mode() -> str:
    mode = os.environ.get("STARTUP_SEED_MODE", "background").strip().lower()
    if mode not in {"background", "blocking", "off"}:
        log.warning("invalid STARTUP_SEED_MODE=%r; using background", mode)
        return "background"
    return mode


def _response_sets_cookie(response, cookie_name: str) -> bool:
    prefix = f"{cookie_name}=".encode()
    for name, value in response.raw_headers:
        if name.lower() == b"set-cookie" and value.startswith(prefix):
            return True
    return False


def _slide_max_age(claims) -> int | None:
    if not claims.remember:
        return None
    from datetime import datetime, timezone

    seconds = int((claims.exp - datetime.now(timezone.utc)).total_seconds())
    return max(seconds, 0)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from app.admin_products import (
        ensure_product_chain_type_column,
        ensure_product_length_weights_column,
        ensure_product_sell_mode_columns,
        purge_auto_stock_product_images,
    )
    from app.auth import ensure_google_id_column
    from app.totp import ensure_totp_columns
    from app.database import get_connection, get_transaction
    from app.cms_copy_slots import ensure_page_copy_slots_schema, seed_page_copy_slots
    from app.cms_media import ensure_cms_media_schema
    from app.cms_pages import ensure_cms_pages_schema
    from app.cms_seed import remove_legacy_seeded_pages
    from app.content import (
        ensure_banner_mobile_column,
        ensure_page_images_schema,
        ensure_testimonial_country_column,
    )
    from app.membership_config import ensure_membership_schema
    from app.orders import ensure_order_status_timestamps_column
    from app.profile_schema import ensure_profile_address_columns
    from app.seed_catalog import seed_catalog_if_empty
    from app.seed_content import seed_content_if_empty

    _startup_banner()
    ensure_profile_address_columns()
    ensure_google_id_column()
    ensure_totp_columns()
    try:
        with get_connection() as conn, conn.cursor() as cur:
            ensure_order_status_timestamps_column(cur)
    except Exception:
        log.exception("ensure_order_status_timestamps_column failed")
    try:
        from app.controllers.admin_controller import _ensure_invite_schema

        with get_connection() as conn, conn.cursor() as cur:
            _ensure_invite_schema(cur)
    except Exception:
        log.exception("ensure_invite_schema failed")
    # Sell-mode columns must not ride the silent try below — missing cols = product-update 500.
    try:
        with get_connection() as conn, conn.cursor() as cur:
            ensure_product_sell_mode_columns(cur)
            ensure_product_length_weights_column(cur)
            ensure_product_chain_type_column(cur)
    except Exception:
        log.exception("ensure_product_sell_mode_columns failed")
    try:
        with get_transaction() as conn, conn.cursor() as cur:
            removed = purge_auto_stock_product_images(cur)
            if removed:
                log.info("purged %s auto shop-product image row(s) from product_images", removed)
    except Exception:
        log.exception("purge_auto_stock_product_images failed")
    try:
        with get_connection() as conn, conn.cursor() as cur:
            ensure_membership_schema(cur)
            ensure_page_images_schema(cur)
            ensure_banner_mobile_column(cur)
            ensure_testimonial_country_column(cur)
            ensure_cms_pages_schema(cur)
            ensure_page_copy_slots_schema(cur)
            ensure_cms_media_schema(cur)
            seed_page_copy_slots(cur)
            remove_legacy_seeded_pages(cur)
    except Exception:
        pass

    def seed_initial_content() -> None:
        seed_catalog_if_empty()
        seed_content_if_empty()

    seed_task: asyncio.Task[None] | None = None
    seed_mode = _startup_seed_mode()
    if seed_mode == "blocking":
        seed_initial_content()
    elif seed_mode == "background":
        seed_task = asyncio.create_task(
            asyncio.to_thread(seed_initial_content),
            name="imprint-startup-seed",
        )

    try:
        yield
    finally:
        if seed_task is not None:
            await seed_task
        try:
            from app.database import close_pool

            close_pool()
        except Exception:
            log.exception("close_pool failed")


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        lifespan=lifespan,
    )
    application.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)

    _CSRF_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
    # Cookie-auth mutating routes. startswith so /api/cart covers cart-item + cart-checkout.
    _CSRF_PREFIXES = (
        "/api/auth/",
        "/htmx/",
        "/api/admin/",
        "/api/cart",
        "/api/order",
        "/api/coupon",
        "/api/favorites",
        "/api/notifications",
        "/api/pricing",
        "/api/v1/auth/",
        "/api/v1/admin/",
        "/api/v1/cart",
        "/api/v1/order",
        "/api/v1/coupon",
        "/api/v1/favorites",
        "/api/v1/notifications",
        "/api/v1/pricing",
    )

    @application.middleware("http")
    async def csrf_same_site_origin(request, call_next):
        """Reject cross-site Origin/Referer on cookie-auth mutating routes.

        Missing both Origin and Referer is allowed (TestClient / some HTMX);
        browsers send Origin on cross-site POSTs so mismatches still block CSRF.
        """
        if request.method not in _CSRF_SAFE_METHODS:
            path = request.url.path
            if any(path.startswith(prefix) for prefix in _CSRF_PREFIXES):
                from app.auth import same_site_origin
                from fastapi.responses import JSONResponse

                if not same_site_origin(request):
                    return JSONResponse(
                        status_code=403,
                        content={"error": "請求來源不被允許"},
                    )
        return await call_next(request)

    @application.middleware("http")
    async def session_touch(request, call_next):
        """Slide idle window by re-issuing iat when under 50% idle TTL remains."""
        response = await call_next(request)
        from app.auth import (
            COOKIE_NAME,
            reissue_session_token,
            session_needs_slide,
            set_session_cookie,
            verify_session_claims,
        )

        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return response
        if _response_sets_cookie(response, COOKIE_NAME):
            return response
        claims = verify_session_claims(token)
        if not claims or not session_needs_slide(claims):
            return response
        set_session_cookie(
            response,
            reissue_session_token(claims),
            request,
            remember=claims.remember,
            is_admin=claims.role == "admin",
            max_age_seconds=_slide_max_age(claims),
        )
        return response

    @application.middleware("http")
    async def dev_static_fresh(request, call_next):
        """Local dev: skip conditional-cache 304s so static assets always revalidate as 200."""
        if not settings.is_render:
            path = request.url.path
            if path.startswith(("/static/", "/js/", "/css/")):
                request.scope["headers"] = [
                    (name, value)
                    for name, value in request.scope["headers"]
                    if name.lower() not in (b"if-none-match", b"if-modified-since")
                ]
        response = await call_next(request)
        if request.url.path.startswith(("/static/", "/js/", "/css/")):
            if settings.is_render and response.status_code == 200:
                if request.url.query or request.url.path.startswith("/static/uploads/"):
                    cache_control = "public, max-age=31536000, immutable"
                else:
                    cache_control = "public, max-age=86400, stale-while-revalidate=604800"
                response.headers.setdefault("Cache-Control", cache_control)
            elif not settings.is_render:
                response.headers["Cache-Control"] = "no-store"
        return response

    @application.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if request.url.scheme == "https" or settings.is_render:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        # CSP on HTML documents only (not JSON/static). script-src keeps
        # 'unsafe-inline' because pages use inline handlers (onerror=…) that
        # can't be nonced piecemeal, but is still locked to an origin allowlist,
        # so injected external <script src=evil> is blocked. Allowed origins are
        # exactly what the site loads: Botpress webchat, Google Maps, Google
        # Fonts, YouTube embeds. frame-ancestors 'self' + object-src 'none' +
        # base-uri 'self' are the high-value additions.
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers.setdefault(
                "Content-Security-Policy",
                HTML_CONTENT_SECURITY_POLICY,
            )
            response.headers.setdefault("Permissions-Policy", HTML_PERMISSIONS_POLICY)
        return response

    # Legacy + versioned JSON mounts (public HTML is Jinja/HTMX, not JSON clients).
    application.include_router(api_controller.router, prefix="/api")
    application.include_router(auth_controller.router, prefix="/api")
    application.include_router(notifications_controller.router, prefix="/api")
    application.include_router(shop_controller.router, prefix="/api")
    application.include_router(admin_controller.router, prefix="/api")
    application.include_router(cms_admin_controller.router, prefix="/api")

    from app.api.v1 import build_v1_router

    application.include_router(build_v1_router(), prefix="/api/v1")

    # HTMX HTML partials (chrome / auth / cart / member).
    application.include_router(htmx_controller.router)

    # Public HTML via Jinja SSR; static + admin shell.
    web_controller.register_pages(application)
    web_controller.mount_static(application)
    return application

