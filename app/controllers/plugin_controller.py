"""Admin API — plugin switches (viewing is open to admins; changing needs the password)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import admin_plugins as plugins
from app import release_notes as rn
from app.auth import log_admin_action, require_admin
from app.database import get_connection

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-plugins"])


def _require_admin(request: Request) -> str:
    return require_admin(request)


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


def _audit(admin_id: str, detail: dict) -> None:
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select email from users where id = %s", (admin_id,))
            actor = cur.fetchone()
        log_admin_action(actor["email"] if actor else None, "plugin_state", detail)
    except Exception:
        # Auditing must never block the switch itself.
        log.exception("plugin audit log failed")


@router.get("/plugins")
def plugins_get(request: Request):
    _require_admin(request)
    return {
        "plugins": plugins.get_states(),
        "labels": {slug: meta["label"] for slug, meta in plugins.LIVE_PLUGINS.items()},
    }


@router.patch("/plugins/{slug}")
async def plugins_set(request: Request, slug: str):
    admin_id = _require_admin(request)
    # The password gate: same unlock cookie as the release-notes editor.
    if not rn.require_unlock(request, admin_id):
        return _error(403, "unlock required")
    try:
        body = await request.json()
    except Exception:
        body = None
    if not isinstance(body, dict):
        return _error(400, "invalid body")
    try:
        previous, state = plugins.set_state(slug, str(body.get("state") or ""))
    except plugins.PluginError as exc:
        status = 404 if slug not in plugins.LIVE_PLUGINS else 400
        return _error(status, str(exc))
    if previous != state:
        _audit(admin_id, {"slug": slug, "from": previous, "to": state})
    return {"ok": True, "plugins": plugins.get_states()}
