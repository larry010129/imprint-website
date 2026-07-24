"""Imprint Diamond — FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

from config.settings import settings

from app.controllers import (
    admin_controller,
    api_controller,
    auth_controller,
    notifications_controller,
    shop_controller,
    web_controller,
)


def _startup_banner() -> None:
    base = settings.public_base_url
    label = "Diamond v3 on Render" if settings.is_render else "Diamond v3 local dev"
    print("")
    print(f"  {label}")
    print(f"  Site: {base}/")
    print(f"  Gold: {base}/gold-price.html")
    print(f"  API:  {base}/api/bot-gold")
    print("")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from app.profile_schema import ensure_profile_address_columns
    from app.seed_catalog import seed_catalog_if_empty
    from app.seed_content import seed_content_if_empty

    _startup_banner()
    ensure_profile_address_columns()
    seed_catalog_if_empty()
    seed_content_if_empty()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        lifespan=lifespan,
    )
    application.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)

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
                response.headers.setdefault("Cache-Control", "public, max-age=300")
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
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.botpress.cloud "
                "https://files.bpcontent.cloud https://*.botpress.cloud; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com data:; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://*.botpress.cloud wss://*.botpress.cloud "
                "https://cdn.botpress.cloud https://files.bpcontent.cloud; "
                "frame-src https://www.google.com https://www.youtube.com "
                "https://www.youtube-nocookie.com https://*.botpress.cloud; "
                "frame-ancestors 'self'; object-src 'none'; base-uri 'self'",
            )
        return response

    application.include_router(api_controller.router, prefix="/api")
    application.include_router(auth_controller.router, prefix="/api")
    application.include_router(notifications_controller.router, prefix="/api")
    application.include_router(shop_controller.router, prefix="/api")
    application.include_router(admin_controller.router, prefix="/api")
    web_controller.register_pages(application)
    web_controller.mount_static(application)
    return application
