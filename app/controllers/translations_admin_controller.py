"""Admin API — review and correct saved CMS translations."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from psycopg.errors import UndefinedColumn, UndefinedTable

from app import i18n_admin, i18n_store
from app.auth import log_admin_action, require_admin
from app.database import get_connection
from app.i18n import LOCALES
from app.paging import page_meta, parse_paging_from_mapping

router = APIRouter(prefix="/admin", tags=["admin-translations"])

# The migration has not been run yet (the app never creates the table itself).
_NOT_SET_UP = (UndefinedTable, UndefinedColumn)
_NOT_SET_UP_MESSAGE = "翻譯資料表尚未建立"


def _actor_email(user_id: str) -> str | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        row = cur.fetchone()
    return row["email"] if row else None


@router.get("/translations")
def list_translations(request: Request) -> JSONResponse:
    require_admin(request)
    language = request.query_params.get("lang", "en")
    if language not in LOCALES:
        return JSONResponse(status_code=400, content={"error": "不支援的語言"})
    search = request.query_params.get("q", "").strip()[:200]
    page, page_size, limit, offset = parse_paging_from_mapping(request.query_params)
    ready = True
    try:
        with get_connection() as conn, conn.cursor() as cur:
            total, rows = i18n_admin.list_translations(
                cur, language=language, search=search, limit=limit, offset=offset
            )
    except _NOT_SET_UP:
        ready, total, rows = False, 0, []
    return JSONResponse(
        content={
            "ready": ready,
            "enabled": i18n_store.enabled(),
            "items": rows,
            **page_meta(page=page, page_size=page_size, total=total),
        }
    )


@router.post("/translation-update")
async def update_translation(request: Request) -> JSONResponse:
    user_id = require_admin(request)
    try:
        body = await request.json()
    except ValueError:
        body = {}
    fields, error = i18n_admin.clean_update(body if isinstance(body, dict) else {})
    if error:
        return JSONResponse(status_code=400, content={"error": error})
    source_hash, language, text = fields  # type: ignore[misc]
    try:
        with get_connection() as conn, conn.cursor() as cur:
            row = i18n_admin.update_translation(cur, source_hash, language, text)
    except _NOT_SET_UP:
        return JSONResponse(status_code=503, content={"error": _NOT_SET_UP_MESSAGE})
    if not row:
        return JSONResponse(status_code=404, content={"error": "找不到這筆翻譯"})
    i18n_store.forget(language)  # show the correction without waiting for the cache
    log_admin_action(
        _actor_email(user_id),
        "translation_updated",
        {"lang": language, "source_hash": source_hash},
    )
    return JSONResponse(content={"item": row})
