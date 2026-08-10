"""Admin API — release notes unlock, draft, publish."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app import release_notes as rn
from app.auth import log_admin_action, require_admin
from app.database import get_connection

router = APIRouter(prefix="/admin", tags=["admin-release-notes"])


def _require_admin(request: Request) -> str:
    return require_admin(request)


def _actor_email(user_id: str) -> str | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        row = cur.fetchone()
    return row["email"] if row else None


def _unlock_denied() -> JSONResponse:
    return JSONResponse(status_code=403, content={"error": "unlock required"})


@router.get("/release-notes")
async def get_published(request: Request) -> JSONResponse:
    _require_admin(request)
    store = rn.load_store()
    return JSONResponse(
        content={
            "published": store.get("published"),
            "history": store.get("history") or [],
        }
    )


@router.get("/nav-visibility")
async def get_nav_visibility(request: Request) -> JSONResponse:
    _require_admin(request)
    store = rn.load_store()
    return JSONResponse(content={"visibility": store.get("nav_visibility")})


@router.patch("/nav-visibility")
async def update_nav_visibility(request: Request) -> JSONResponse:
    _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    visibility = rn.normalize_nav_visibility(body.get("visibility"))
    store = rn.load_store()
    store["nav_visibility"] = visibility
    rn.save_store(store)
    return JSONResponse(content={"ok": True, "visibility": visibility})


@router.post("/release-notes/unlock")
async def unlock(request: Request) -> JSONResponse:
    admin_id = _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    code = rn.normalize_code(body.get("code"))
    if not code or not rn.codes_match(code, rn.release_notes_password()):
        return JSONResponse(status_code=401, content={"error": "通行碼錯誤"})
    resp = JSONResponse(content={"ok": True})
    rn.set_unlock_cookie(resp, admin_id, request)
    return resp


@router.get("/release-notes/draft")
async def get_draft(request: Request) -> JSONResponse:
    admin_id = _require_admin(request)
    if not rn.require_unlock(request, admin_id):
        return _unlock_denied()
    store = rn.load_store()
    return JSONResponse(content={"draft": store.get("draft")})


@router.put("/release-notes/draft")
async def put_draft(request: Request) -> JSONResponse:
    admin_id = _require_admin(request)
    if not rn.require_unlock(request, admin_id):
        return _unlock_denied()
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    draft, err = rn.validate_draft_fields(
        {
            "version": body.get("version"),
            "title": body.get("title"),
            "notes": body.get("notes"),
        }
    )
    if err or not draft:
        return JSONResponse(status_code=400, content={"error": err or "invalid draft"})
    store = rn.load_store()
    store["draft"] = draft
    rn.save_store(store)
    return JSONResponse(content={"ok": True, "draft": draft})


@router.post("/release-notes/publish")
async def publish(request: Request) -> JSONResponse:
    admin_id = _require_admin(request)
    if not rn.require_unlock(request, admin_id):
        return _unlock_denied()
    try:
        published = rn.publish_draft()
    except HTTPException as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(exc.detail)},
        )
    log_admin_action(
        _actor_email(admin_id),
        "release_notes_published",
        {
            "releaseId": published.get("releaseId"),
            "version": published.get("version"),
        },
    )
    return JSONResponse(content={"ok": True, "published": published})
