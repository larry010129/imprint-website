"""ERP Inbound Events Controller.

Implements the HTTP pull/ack endpoints according to WEBSITE_TO_ERP_SECURITY.md
and WEBSITE_TO_ERP_INTEGRATION.md.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.database import get_connection
from app.erp_inbound import (
    AUTH_ERROR_RESPONSE,
    ensure_erp_events_schema,
    is_erp_events_enabled,
    verify_erp_request,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/erp", tags=["erp-inbound"])


def _err(status: int, detail: str = "unauthorized") -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": detail})


@router.get("/health")
async def erp_health(request: Request) -> JSONResponse:
    """Connectivity and queue health check."""
    enabled = is_erp_events_enabled()
    if not enabled:
        return JSONResponse(content={"status": "ok", "enabled": False, "pending_count": 0})

    try:
        with get_connection() as conn, conn.cursor() as cur:
            ensure_erp_events_schema(cur)
            cur.execute("SELECT COUNT(*) AS cnt FROM erp_inbound_events WHERE status = 'pending'")
            row = cur.fetchone()
            cnt = row["cnt"] if row and isinstance(row, dict) else (row[0] if row else 0)
        return JSONResponse(content={"status": "ok", "enabled": True, "pending_count": cnt})
    except Exception as exc:
        log.warning("ERP health check failed: %s", exc)
        return JSONResponse(content={"status": "degraded", "enabled": enabled, "pending_count": 0})


@router.get("/v1/events")
@router.get("/events/pull")
async def pull_events(
    request: Request,
    after: str = Query("0"),
    limit: int = Query(50),
) -> JSONResponse:
    """Pull pending inbound events for the ERP desktop client."""
    if not is_erp_events_enabled():
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    after_clean = (after or "0").strip()
    try:
        after_val = int(after_clean)
        if after_val < 0:
            return _err(400, "invalid cursor")
    except ValueError:
        return _err(400, "invalid cursor")

    limit = max(1, min(100, limit))

    body_bytes = await request.body()
    with get_connection() as conn, conn.cursor() as cur:
        ensure_erp_events_schema(cur)
        ok, key_id, status_code = verify_erp_request(request, body_bytes, cur)
        if not ok:
            return JSONResponse(status_code=status_code, content=AUTH_ERROR_RESPONSE)

        if after_val > 0:
            cur.execute(
                """
                SELECT id, event_type, idempotency_key, occurred_at, entity_ref, schema_version, payload, seq
                FROM erp_inbound_events
                WHERE status = 'pending' AND seq > %s
                ORDER BY seq ASC
                LIMIT %s
                """,
                (after_val, limit),
            )
        else:
            cur.execute(
                """
                SELECT id, event_type, idempotency_key, occurred_at, entity_ref, schema_version, payload, seq
                FROM erp_inbound_events
                WHERE status = 'pending'
                ORDER BY seq ASC
                LIMIT %s
                """,
                (limit,),
            )
        rows = cur.fetchall() or []

    items = []
    max_cursor = after_val
    for r in rows:
        c = r["seq"]
        if c > max_cursor:
            max_cursor = c
        payload_val = r["payload"] if isinstance(r["payload"], dict) else json.loads(r["payload"])
        occ = r["occurred_at"]
        occ_str = occ.isoformat() if hasattr(occ, "isoformat") else str(occ)
        items.append({
            "event_id": str(r["id"]),
            "event_type": r["event_type"],
            "occurred_at": occ_str,
            "idempotency_key": r["idempotency_key"],
            "entity_ref": r.get("entity_ref") or r["idempotency_key"],
            "schema_version": r.get("schema_version") or 1,
            "cursor": str(c),
            "payload": payload_val,
        })

    response_data = {
        "events": items,
        "cursor": max_cursor,
        "next_cursor": max_cursor,
        "has_more": len(rows) == limit,
    }

    # Response size cap: 1 MB
    resp_bytes = json.dumps(response_data).encode("utf-8")
    if len(resp_bytes) > 1048576 and len(items) > 1:
        # Clamped items to fit under 1MB
        while len(items) > 1 and len(json.dumps(response_data).encode("utf-8")) > 1048576:
            items.pop()
        response_data["events"] = items
        response_data["has_more"] = True
        response_data["cursor"] = items[-1]["cursor"] if items else str(after_val)
        response_data["next_cursor"] = response_data["cursor"]

    return JSONResponse(content=response_data)


@router.post("/v1/events/ack")
@router.post("/events/ack")
async def ack_events(request: Request) -> JSONResponse:
    """Acknowledge committed events from ERP desktop client."""
    if not is_erp_events_enabled():
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    raw_body = await request.body()
    with get_connection() as conn, conn.cursor() as cur:
        ensure_erp_events_schema(cur)
        ok, key_id, status_code = verify_erp_request(request, raw_body, cur)
        if not ok:
            return JSONResponse(status_code=status_code, content=AUTH_ERROR_RESPONSE)

        try:
            data = json.loads(raw_body) if raw_body else {}
        except Exception:
            return _err(400, "invalid json")

        event_ids = data.get("event_ids")
        if not isinstance(event_ids, list):
            return _err(400, "event_ids must be a list")

        if len(event_ids) > 100:
            return _err(400, "cannot acknowledge more than 100 event_ids at once")

        clean_ids = [str(eid) for eid in event_ids if eid]
        if not clean_ids:
            return JSONResponse(content={"ok": True, "success": True, "acked": 0})

        cur.execute(
            """
            UPDATE erp_inbound_events
            SET status = 'acked', acked_at = NOW()
            WHERE id = ANY(%s::uuid[]) AND status = 'pending'
            """,
            (clean_ids,),
        )
        acked = cur.rowcount

    return JSONResponse(content={"ok": True, "success": True, "acked": acked})
