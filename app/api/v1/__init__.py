"""API v1 — versioned JSON surface. Handlers still live in app.controllers until moved."""

from app.api.v1.router import build_v1_router

__all__ = ["build_v1_router"]
