"""Assemble /api/v1/* from endpoint re-exports. Legacy /api/* mounts stay in create_app."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import admin as admin_ep
from app.api.v1.endpoints import auth as auth_ep
from app.api.v1.endpoints import catalog as catalog_ep
from app.api.v1.endpoints import notifications as notifications_ep
from app.api.v1.endpoints import shop as shop_ep


def build_v1_router() -> APIRouter:
    """Same handlers as /api — also available under /api/v1."""
    router = APIRouter()
    # catalog_ep.router == api_controller.router (pricing, catalog, gold, …)
    router.include_router(catalog_ep.router)
    router.include_router(auth_ep.router)
    router.include_router(notifications_ep.router)
    router.include_router(shop_ep.router)
    router.include_router(admin_ep.admin_router)
    router.include_router(admin_ep.cms_admin_router)
    router.include_router(admin_ep.release_notes_router)
    return router
