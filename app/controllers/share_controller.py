"""Public API — short share links for the calculator's 分享摘要."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import share_links as sl
from app.auth import enforce_rate_limit
from app.database import get_connection

log = logging.getLogger(__name__)

router = APIRouter(prefix="/share", tags=["share"])


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message}, headers={"Cache-Control": "no-store"})


@router.post("")
async def create_share_link(request: Request) -> JSONResponse:
    """Store a configuration and return its short code. Anyone may create one, so it
    is rate limited, size limited, whitelisted and de-duplicated."""
    if not enforce_rate_limit(request, action="share-create", limit=30, window_seconds=600):
        return _error(429, "分享太頻繁，請稍後再試")
    raw = await request.body()
    if len(raw) > sl.MAX_BODY_BYTES:
        return _error(413, "資料過大")
    try:
        body = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return _error(400, "invalid body")
    config = sl.sanitize_config(body)
    if config is None:
        return _error(400, "試算資料不完整")
    with get_connection() as conn, conn.cursor() as cur:
        code = sl.get_or_create_code(cur, config)
        if sl.should_cleanup():
            # Housekeeping must never get in the way of sharing.
            try:
                removed = sl.delete_expired(cur)
                if removed:
                    log.info("share links: removed %s expired link(s)", removed)
            except Exception:
                log.exception("share link cleanup failed")
    return JSONResponse(
        content={"code": code, "path": f"/s/{code}"},
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{code}")
def read_share_link(code: str) -> JSONResponse:
    """The stored configuration (no price — the page asks /api/quote for that)."""
    if not sl.is_valid_code(code):
        return _error(404, "找不到這個分享連結")
    with get_connection() as conn, conn.cursor() as cur:
        config = sl.fetch_config(cur, code)
        if config is not None:
            # Opening a link keeps it alive (expiry counts from the last open).
            try:
                sl.touch_link(cur, code)
            except Exception:
                log.exception("share link touch failed")
    if config is None:
        return _error(404, "找不到這個分享連結")
    # The stored configuration never changes for a code, so it can be cached briefly.
    return JSONResponse(content={"config": config}, headers={"Cache-Control": "public, max-age=300"})
