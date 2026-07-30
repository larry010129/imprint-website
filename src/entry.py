"""Cloudflare Python Workers entry — ASGI bridge to FastAPI.

Deploy with:
  uvx --from workers-py pywrangler deploy

Local:
  uvx --from workers-py pywrangler dev

NOTE: This imprint app needs Postgres (psycopg), local disk uploads, Jinja
templates, and several native packages. Cloudflare Python Workers (Pyodide)
cannot run the full production stack. Keep production on Render
(`scripts/render-start.sh`). This entry exists so wrangler finds `main` and
for a future slim Worker / Containers path — not a drop-in Render replacement.
"""

from __future__ import annotations

from workers import WorkerEntrypoint

import asgi

# Prefer the same factory as main.py / gunicorn.
from app import create_app

app = create_app()


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)
