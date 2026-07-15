"""Render legacy entry — dashboard may still use gunicorn server.main:app."""

from main import app

__all__ = ["app"]
