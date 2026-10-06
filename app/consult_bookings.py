"""預約諮詢日曆 — admin booking calendar (one booking per slot).

Leads (contact_messages) carry the customer's suggested slots as free text
(`【希望預約時段】` block written by htmx_member.contact_submit). This module
parses those into "requested" pins and stores confirmed bookings in
consult_bookings, with a partial unique index so a slot can't be double-booked.
Settings (slot starts, weekly days off, blackout dates) live in cms_kv.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, time, timedelta, timezone

import psycopg

log = logging.getLogger(__name__)

TZ_TAIPEI = timezone(timedelta(hours=8))
SETTINGS_KEY = "booking_settings"
REQUEST_MARKER = "【希望預約時段】"
STATUSES = ("confirmed", "done", "cancelled")
# Same hourly slots the public contact form offers (contact.html).
DEFAULT_SLOTS = ("10:00", "11:00", "13:30", "14:30", "15:30", "16:30", "17:30")
SLOT_MINUTES = 60
MAX_BOOK_AHEAD_DAYS = 365
LEAD_LOOKBACK_DAYS = 180

_HHMM_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_SLOT_TIME_RE = re.compile(r"(上午|下午)?\s*(\d{1,2}):(\d{2})")


class BookingConflict(Exception):
    """The slot already has a non-cancelled booking."""


class BookingError(ValueError):
    """Invalid booking input (message is safe to show the admin)."""


# ── settings ─────────────────────────────────────────────────────────────

def default_settings() -> dict:
    return {"slots": list(DEFAULT_SLOTS), "closedWeekdays": [], "blackoutDates": []}


def normalize_settings(raw) -> dict:
    out = default_settings()
    if not isinstance(raw, dict):
        return out
    slots = raw.get("slots")
    if isinstance(slots, list):
        clean = sorted({s.strip().zfill(5) for s in slots if isinstance(s, str) and _HHMM_RE.match(s.strip())})
        if clean:
            out["slots"] = clean
    days = raw.get("closedWeekdays")
    if isinstance(days, list):
        out["closedWeekdays"] = sorted({d for d in days if isinstance(d, int) and 0 <= d <= 6})
    blackout = raw.get("blackoutDates")
    if isinstance(blackout, list):
        valid = []
        for item in blackout:
            if isinstance(item, str) and _DATE_RE.fullmatch(item.strip()):
                try:
                    date.fromisoformat(item.strip())
                    valid.append(item.strip())
                except ValueError:
                    pass
        out["blackoutDates"] = sorted(set(valid))
    return out


def load_settings() -> dict:
    from app.cms_kv_store import kv_get

    try:
        return normalize_settings(kv_get(SETTINGS_KEY))
    except Exception:
        log.exception("booking settings load failed; using defaults")
        return default_settings()


def save_settings(raw) -> dict:
    from app.cms_kv_store import kv_set

    settings = normalize_settings(raw)
    kv_set(SETTINGS_KEY, settings)
    return settings


# ── slots ────────────────────────────────────────────────────────────────

def now_local() -> datetime:
    return datetime.now(TZ_TAIPEI)


def slot_start_on(day: date, hhmm: str) -> datetime:
    hour, minute = map(int, hhmm.split(":"))
    return datetime.combine(day, time(hour, minute), tzinfo=TZ_TAIPEI)


def day_is_open(day: date, settings: dict) -> bool:
    return day.weekday() not in settings["closedWeekdays"] and day.isoformat() not in settings["blackoutDates"]


def slots_for_day(day: date, settings: dict) -> list[datetime]:
    if not day_is_open(day, settings):
        return []
    return [slot_start_on(day, hhmm) for hhmm in settings["slots"]]


def slot_label(start: datetime) -> str:
    local = start.astimezone(TZ_TAIPEI)
    end = local + timedelta(minutes=SLOT_MINUTES)
    return f"{local:%H:%M}–{end:%H:%M}"


def parse_slot_datetime(value) -> datetime:
    """ISO string from the client -> aware Taipei datetime. Raises BookingError."""
    if not isinstance(value, str) or not value.strip():
        raise BookingError("請選擇預約時段")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise BookingError("預約時段格式不正確") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TZ_TAIPEI)
    return parsed.astimezone(TZ_TAIPEI)


def validate_slot(start: datetime, settings: dict, *, now: datetime | None = None) -> None:
    now = now or now_local()
    local = start.astimezone(TZ_TAIPEI)
    if local.second or local.microsecond:
        raise BookingError("預約時段不在開放時段內")
    if local < now - timedelta(hours=1):
        raise BookingError("不能預約已過去的時段")
    if local > now + timedelta(days=MAX_BOOK_AHEAD_DAYS):
        raise BookingError("預約日期太遠")
    if local not in slots_for_day(local.date(), settings):
        raise BookingError("此時段不在開放時間內（公休日或未開放）")


# ── parsing leads ────────────────────────────────────────────────────────

def parse_requested_slots(message: str | None) -> list[datetime]:
    """Slots a customer suggested, from the 【希望預約時段】 block.

    Lines look like ``1. 2026-10-12 下午 1:30～2:30``. Lines without both a
    date and a clock time (尚未決定 / 其他 free text) are skipped.
    """
    if not message or REQUEST_MARKER not in message:
        return []
    block = message.split(REQUEST_MARKER, 1)[1]
    found: list[datetime] = []
    for line in block.splitlines():
        date_match = _DATE_RE.search(line)
        if not date_match:
            continue
        rest = line[date_match.end():]
        time_match = _SLOT_TIME_RE.search(rest)
        if not time_match:
            continue
        meridiem, hour_s, minute_s = time_match.groups()
        hour, minute = int(hour_s), int(minute_s)
        if meridiem == "下午" and hour < 12:
            hour += 12
        if meridiem == "上午" and hour == 12:
            hour = 0
        if hour > 23 or minute > 59:
            continue
        try:
            day = date(*map(int, date_match.groups()))
        except ValueError:
            continue
        found.append(datetime.combine(day, time(hour, minute), tzinfo=TZ_TAIPEI))
    return found


# ── storage ──────────────────────────────────────────────────────────────

def ensure_consult_bookings_schema(cur) -> None:
    cur.execute(
        """
        create table if not exists consult_bookings (
          id uuid primary key default gen_random_uuid(),
          slot_start timestamptz not null,
          name text not null,
          phone text not null default '',
          email text,
          note text,
          lead_id uuid references contact_messages(id) on delete set null,
          status text not null default 'confirmed'
            check (status in ('confirmed', 'done', 'cancelled')),
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    cur.execute(
        """
        create unique index if not exists consult_bookings_one_per_slot
          on consult_bookings (slot_start) where status <> 'cancelled'
        """
    )
    cur.execute(
        "create index if not exists consult_bookings_lead_idx on consult_bookings (lead_id)"
    )
    cur.execute("alter table consult_bookings enable row level security")


def serialize_booking(row: dict) -> dict:
    start = row["slot_start"].astimezone(TZ_TAIPEI)
    return {
        "id": str(row["id"]),
        "slot": start.isoformat(),
        "date": start.strftime("%Y-%m-%d"),
        "label": slot_label(start),
        "name": row.get("name") or "",
        "phone": row.get("phone") or "",
        "email": row.get("email") or "",
        "note": row.get("note") or "",
        "leadId": str(row["lead_id"]) if row.get("lead_id") else None,
        "status": row.get("status") or "confirmed",
    }


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    first = date(year, month, 1)
    nxt = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return (
        datetime.combine(first, time.min, tzinfo=TZ_TAIPEI),
        datetime.combine(nxt, time.min, tzinfo=TZ_TAIPEI),
    )


def fetch_month(cur, year: int, month: int) -> dict:
    start, end = month_bounds(year, month)
    cur.execute(
        """
        select id, slot_start, name, phone, email, note, lead_id, status
        from consult_bookings
        where slot_start >= %s and slot_start < %s and status <> 'cancelled'
        order by slot_start
        """,
        (start, end),
    )
    bookings = [serialize_booking(r) for r in cur.fetchall()]

    cur.execute(
        "select distinct lead_id from consult_bookings "
        "where lead_id is not null and status <> 'cancelled'"
    )
    scheduled_leads = {str(r["lead_id"]) for r in cur.fetchall()}
    booked_slots = {b["slot"] for b in bookings}

    cur.execute(
        """
        select id, name, phone, email, message, created_at from contact_messages
        where message like %s and created_at > now() - make_interval(days => %s)
        order by created_at desc limit 300
        """,
        (f"%{REQUEST_MARKER}%", LEAD_LOOKBACK_DAYS),
    )
    requested: list[dict] = []
    for row in cur.fetchall():
        lead_id = str(row["id"])
        if lead_id in scheduled_leads:
            continue
        for slot in parse_requested_slots(row.get("message")):
            if not (start <= slot < end) or slot.isoformat() in booked_slots:
                continue
            requested.append(
                {
                    "leadId": lead_id,
                    "name": row.get("name") or "",
                    "phone": row.get("phone") or "",
                    "email": row.get("email") or "",
                    "slot": slot.isoformat(),
                    "date": slot.strftime("%Y-%m-%d"),
                    "label": slot_label(slot),
                }
            )
    requested.sort(key=lambda r: r["slot"])
    return {"bookings": bookings, "requested": requested}


def _clean_text(value, limit: int) -> str:
    return str(value or "").strip()[:limit]


def create_booking(cur, *, slot_start: datetime, name, phone, email, note, lead_id) -> dict:
    name = _clean_text(name, 80)
    if not name:
        raise BookingError("請填寫姓名")
    try:
        cur.execute(
            """
            insert into consult_bookings (slot_start, name, phone, email, note, lead_id)
            values (%s, %s, %s, %s, %s, %s)
            returning id, slot_start, name, phone, email, note, lead_id, status
            """,
            (
                slot_start,
                name,
                _clean_text(phone, 40),
                _clean_text(email, 120) or None,
                _clean_text(note, 500) or None,
                lead_id,
            ),
        )
    except psycopg.errors.UniqueViolation as exc:
        raise BookingConflict("此時段已被預約") from exc
    return serialize_booking(cur.fetchone())


def update_booking(cur, booking_id: str, changes: dict) -> dict | None:
    sets: list[str] = []
    params: list = []
    if "slot_start" in changes:
        sets.append("slot_start = %s")
        params.append(changes["slot_start"])
    for key, limit in (("name", 80), ("phone", 40), ("email", 120), ("note", 500)):
        if key in changes:
            value = _clean_text(changes[key], limit)
            if key == "name" and not value:
                raise BookingError("請填寫姓名")
            sets.append(f"{key} = %s")
            params.append(value or (None if key in ("email", "note") else ""))
    if "status" in changes:
        if changes["status"] not in STATUSES:
            raise BookingError("狀態不正確")
        sets.append("status = %s")
        params.append(changes["status"])
    if not sets:
        raise BookingError("沒有要更新的欄位")
    sets.append("updated_at = now()")
    params.append(booking_id)
    try:
        cur.execute(
            f"""
            update consult_bookings set {", ".join(sets)} where id = %s
            returning id, slot_start, name, phone, email, note, lead_id, status
            """,
            params,
        )
    except psycopg.errors.UniqueViolation as exc:
        raise BookingConflict("此時段已被預約") from exc
    row = cur.fetchone()
    return serialize_booking(row) if row else None
