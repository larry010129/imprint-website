"""User notifications API."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.auth import get_user_id
from app.database import get_connection

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _display_time(created: datetime | None) -> str:
    if not created:
        return ""
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    local = created.astimezone()
    return local.strftime("%Y/%m/%d %H:%M")


def _group_key(created: datetime | None) -> str:
    if not created:
        return "較早"
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    day = created.astimezone().date()
    today = date.today()
    if day == today:
        return "today"
    if (today - day).days == 1:
        return "yesterday"
    return day.strftime("%Y/%m/%d")


def _serialize_notification(row: dict) -> dict:
    created = row.get("created_at")
    return {
        "id": str(row["id"]),
        "kind": row.get("kind") or "system",
        "message": row.get("message") or "",
        "order_summary": row.get("order_summary") or "系統通知",
        "is_read": bool(row.get("is_read")),
        "unread": not bool(row.get("is_read")),
        "show_unread": not bool(row.get("is_read")),
        "created_at": created.isoformat() if created else None,
        "created_at_display": _display_time(created),
    }


@router.get("/recent")
async def notifications_recent(request: Request) -> dict:
    from app.paging import page_meta, parse_paging_from_mapping, sql_count_total

    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not signed in")

    page, page_size, limit, offset = parse_paging_from_mapping(
        request.query_params, default_page_size=50, max_page_size=50
    )

    with get_connection() as conn, conn.cursor() as cur:
        total = sql_count_total(
            cur,
            "select count(*) as n from user_notifications where user_id = %s",
            (user_id,),
        )
        cur.execute(
            """
            select id, kind, message, order_id, order_summary, is_read, created_at
            from user_notifications
            where user_id = %s
            order by created_at desc
            limit %s offset %s
            """,
            (user_id, limit, offset),
        )
        rows = cur.fetchall()

    items = [_serialize_notification(row) for row in rows]
    unread_count = sum(1 for n in items if n["unread"])

    buckets: dict[str, list] = {}
    for item in items:
        key = _group_key(
            datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            if item.get("created_at")
            else None
        )
        buckets.setdefault(key, []).append(item)

    order = ["today", "yesterday"]
    groups = []
    for key in order:
        if key in buckets:
            groups.append([key, buckets.pop(key)])
    for key in sorted(buckets.keys(), reverse=True):
        groups.append([key, buckets[key]])

    meta = page_meta(page=page, page_size=page_size, total=total)
    return {
        "groups": groups,
        "unread_count": unread_count,
        "unreadCount": unread_count,
        **meta,
    }


@router.post("/mark-read")
async def notifications_mark_read(request: Request) -> JSONResponse:
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not signed in")

    body = await request.json()
    note_id = body.get("id")
    if not note_id:
        return JSONResponse(status_code=400, content={"error": "missing id"})

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "update user_notifications set is_read = true where id = %s and user_id = %s",
            (note_id, user_id),
        )
    return JSONResponse(content={"ok": True})


@router.post("/delete")
async def notifications_delete(request: Request) -> JSONResponse:
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not signed in")

    body = await request.json()
    note_id = body.get("id")
    if not note_id:
        return JSONResponse(status_code=400, content={"error": "missing id"})

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "delete from user_notifications where id = %s and user_id = %s",
            (note_id, user_id),
        )
    return JSONResponse(content={"success": True})
