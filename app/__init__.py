"""Imprint Diamond — FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routers import admin_router, api_router, auth_router, notifications_router, shop_router, web_router


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
    _startup_banner()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        lifespan=lifespan,
    )
    application.include_router(api_router.router, prefix="/api")
    application.include_router(auth_router.router, prefix="/api")
    application.include_router(notifications_router.router, prefix="/api")
    application.include_router(shop_router.router, prefix="/api")
    application.include_router(admin_router.router, prefix="/api")
    web_router.register_pages(application)
    web_router.mount_static(application)
    return application
