"""Admin + CMS admin JSON — routes in admin_controller / cms_admin_controller."""

from app.controllers import admin_controller, cms_admin_controller

admin_router = admin_controller.router
cms_admin_router = cms_admin_controller.router

__all__ = ["admin_router", "cms_admin_router"]
