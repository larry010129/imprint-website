"""Cloudflare Python Worker entry (plain wrangler-compatible stub).

Cloudflare Git deploy runs `wrangler deploy`, which does NOT bundle the full
FastAPI app (psycopg / disk / Jinja). This stub deploys so the Worker exists.

Full site stays on Render: `bash scripts/render-start.sh`

To run a real FastAPI Worker later (limited packages only):
  uv sync
  uv run pywrangler deploy
and restore an ASGI bridge that imports a Workers-safe app — not `app.create_app()`.
"""

from __future__ import annotations

from js import Response


async def on_fetch(request):
    """Minimal handler — no `workers` SDK import (CI has no workers-py bundle)."""
    url = str(getattr(request, "url", "") or "")
    body = (
        '{"ok":true,'
        '"service":"imprint-website",'
        '"mode":"cloudflare-worker-stub",'
        '"message":"Full FastAPI site runs on Render, not this Worker."}'
    )
    if url.rstrip("/").endswith("/health"):
        body = '{"ok":true}'
    return Response.new(
        body,
        {
            "status": 200,
            "headers": {"content-type": "application/json; charset=utf-8"},
        },
    )
