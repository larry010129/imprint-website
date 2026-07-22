"""Imprint Diamond — FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

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
    from app.seed_catalog import seed_catalog_if_empty
    from app.seed_content import seed_content_if_empty

    _startup_banner()
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
    application.include_router(api_controller.router, prefix="/api")
    application.include_router(auth_controller.router, prefix="/api")
    application.include_router(notifications_controller.router, prefix="/api")
    application.include_router(shop_controller.router, prefix="/api")
    application.include_router(admin_controller.router, prefix="/api")
    web_controller.register_pages(application)
    web_controller.mount_static(application)
    return application
