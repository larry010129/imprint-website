"""Admin API — 預約諮詢日曆 (consultation booking calendar)."""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app import admin_plugins as plugins
from app import consult_bookings as cb
from app.auth import enforce_rate_limit, log_admin_action, require_admin
from app.database import get_connection

router = APIRouter(prefix="/admin", tags=["admin-booking"])
# No login: feeds the public contact form's date/time picker.
public_router = APIRouter(tags=["booking-public"])

_MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def _require_admin(request: Request) -> str:
    """Signed-in admin AND the 預約諮詢日曆 plugin switched on."""
    admin_id = require_admin(request)
    if not plugins.is_on("booking"):
        raise HTTPException(status_code=403, detail="plugin_disabled")
    return admin_id


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


async def _json_body(request: Request) -> dict | None:
    try:
        body = await request.json()
    except Exception:
        return None
    return body if isinstance(body, dict) else None


def _audit(admin_id: str, action: str, detail: dict) -> None:
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select email from users where id = %s", (admin_id,))
            actor = cur.fetchone()
        log_admin_action(actor["email"] if actor else None, action, detail)
    except Exception:
        # Auditing must never fail the booking itself.
        cb.log.exception("booking audit log failed")


def _lead_id_or_none(value) -> str | None:
    if not value:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except ValueError:
        raise cb.BookingError("諮詢名單編號不正確")


@public_router.get("/booking-availability")
def booking_availability(request: Request):
    """Opening rules + taken slots (no personal data) for the contact form."""
    if not enforce_rate_limit(request, action="booking-availability", limit=120, window_seconds=600):
        return JSONResponse(
            status_code=429,
            content={"error": "請求過於頻繁，請稍後再試"},
            headers={"Cache-Control": "no-store"},
        )
    if not plugins.is_on("booking"):
        # Plugin paused/disabled: the contact form falls back to its fixed time list.
        return JSONResponse(content={"enabled": False}, headers={"Cache-Control": "no-store"})
    settings = cb.load_settings()
    with get_connection() as conn, conn.cursor() as cur:
        payload = cb.public_availability(cur, settings)
    return JSONResponse(content=payload, headers={"Cache-Control": "no-store"})


@router.get("/bookings")
def bookings_month(request: Request, month: str | None = Query(None)):
    _require_admin(request)
    now = cb.now_local()
    match = _MONTH_RE.match(month or "")
    year, mon = (int(match.group(1)), int(match.group(2))) if match else (now.year, now.month)
    settings = cb.load_settings()
    with get_connection() as conn, conn.cursor() as cur:
        data = cb.fetch_month(cur, year, mon)
    return {
        "month": f"{year:04d}-{mon:02d}",
        "today": now.strftime("%Y-%m-%d"),
        "settings": settings,
        "slotMinutes": cb.SLOT_MINUTES,
        **data,
    }


@router.put("/bookings-settings")
async def bookings_settings_save(request: Request):
    admin_id = _require_admin(request)
    body = await _json_body(request)
    if body is None:
        return _error(400, "invalid body")
    settings = cb.save_settings(body)
    _audit(admin_id, "booking_settings", {"settings": settings})
    return {"ok": True, "settings": settings}


@router.post("/bookings")
async def bookings_create(request: Request):
    admin_id = _require_admin(request)
    body = await _json_body(request)
    if body is None:
        return _error(400, "invalid body")
    try:
        start = cb.parse_slot_datetime(body.get("slot"))
        cb.validate_slot(start, cb.load_settings())
        lead_id = _lead_id_or_none(body.get("leadId"))
        with get_connection() as conn, conn.cursor() as cur:
            booking = cb.create_booking(
                cur,
                slot_start=start,
                name=body.get("name"),
                phone=body.get("phone"),
                email=body.get("email"),
                note=body.get("note"),
                lead_id=lead_id,
            )
    except cb.BookingConflict as exc:
        return _error(409, str(exc))
    except cb.BookingError as exc:
        return _error(400, str(exc))
    _audit(admin_id, "booking_create", {"id": booking["id"], "slot": booking["slot"]})
    return {"ok": True, "booking": booking}


@router.patch("/bookings/{booking_id}")
async def bookings_update(request: Request, booking_id: str):
    admin_id = _require_admin(request)
    try:
        booking_id = str(uuid.UUID(booking_id))
    except ValueError:
        return _error(400, "invalid booking id")
    body = await _json_body(request)
    if body is None:
        return _error(400, "invalid body")

    changes: dict = {}
    try:
        if "slot" in body:
            start = cb.parse_slot_datetime(body.get("slot"))
            cb.validate_slot(start, cb.load_settings())
            changes["slot_start"] = start
        for key in ("name", "phone", "email", "note", "status"):
            if key in body:
                changes[key] = body[key]
        with get_connection() as conn, conn.cursor() as cur:
            booking = cb.update_booking(cur, booking_id, changes)
    except cb.BookingConflict as exc:
        return _error(409, str(exc))
    except cb.BookingError as exc:
        return _error(400, str(exc))
    if booking is None:
        return _error(404, "找不到這筆預約")
    _audit(admin_id, "booking_update", {"id": booking_id, "fields": sorted(changes)})
    return {"ok": True, "booking": booking}


@router.delete("/bookings/{booking_id}")
def bookings_cancel(request: Request, booking_id: str):
    """Cancel (soft): frees the slot but keeps the record."""
    admin_id = _require_admin(request)
    try:
        booking_id = str(uuid.UUID(booking_id))
    except ValueError:
        return _error(400, "invalid booking id")
    with get_connection() as conn, conn.cursor() as cur:
        booking = cb.update_booking(cur, booking_id, {"status": "cancelled"})
    if booking is None:
        return _error(404, "找不到這筆預約")
    _audit(admin_id, "booking_cancel", {"id": booking_id})
    return {"ok": True}
