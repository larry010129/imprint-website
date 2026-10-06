"""預約諮詢日曆: parsing, slots, one-per-slot conflict, admin API guard (no DB)."""

from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import psycopg
import pytest
from fastapi import HTTPException

from app import consult_bookings as cb
from app.controllers import booking_controller as bc

TZ = cb.TZ_TAIPEI


def _dt(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=TZ)


# ── parsing leads ────────────────────────────────────────────────────────

def test_parse_requested_slots_reads_contact_form_block():
    msg = (
        "想看婚戒\n\n【希望預約時段】\n"
        "1. 2026-10-12 下午 1:30～2:30\n"
        "2. 2026-10-13 上午 10:00～11:00\n"
        "3. 2026-10-14 下午 5:30～6:30"
    )
    assert cb.parse_requested_slots(msg) == [
        _dt(2026, 10, 12, 13, 30),
        _dt(2026, 10, 13, 10, 0),
        _dt(2026, 10, 14, 17, 30),
    ]


def test_parse_requested_slots_skips_undecided_and_free_text():
    msg = (
        "【希望預約時段】\n1. 2026-10-12 尚未決定／稍後再約\n"
        "2. 2026-10-13 其他\n3. 2026-10-14 下午 2:30～3:30"
    )
    assert cb.parse_requested_slots(msg) == [_dt(2026, 10, 14, 14, 30)]


def test_parse_requested_slots_without_marker_or_bad_date():
    assert cb.parse_requested_slots("hello") == []
    assert cb.parse_requested_slots(None) == []
    assert cb.parse_requested_slots("【希望預約時段】\n1. 2026-13-45 上午 10:00") == []


# ── settings & slots ─────────────────────────────────────────────────────

def test_normalize_settings_defaults_and_cleaning():
    assert cb.normalize_settings(None) == cb.default_settings()
    out = cb.normalize_settings(
        {
            "slots": ["9:00", "bad", "13:30", "13:30"],
            "closedWeekdays": [6, 6, 9, "x"],
            "blackoutDates": ["2026-10-10", "nope", "2026-02-31"],
        }
    )
    assert out["slots"] == ["09:00", "13:30"]
    assert out["closedWeekdays"] == [6]
    assert out["blackoutDates"] == ["2026-10-10"]


def test_slots_for_day_respects_days_off_and_blackouts():
    settings = cb.normalize_settings({"closedWeekdays": [0], "blackoutDates": ["2026-10-14"]})
    monday = date(2026, 10, 12)
    assert cb.slots_for_day(monday, settings) == []
    assert cb.slots_for_day(date(2026, 10, 14), settings) == []
    tuesday = cb.slots_for_day(date(2026, 10, 13), settings)
    assert [s.strftime("%H:%M") for s in tuesday] == list(cb.DEFAULT_SLOTS)


def test_validate_slot_rules():
    settings = cb.default_settings()
    now = _dt(2026, 10, 7, 9)
    cb.validate_slot(_dt(2026, 10, 8, 10), settings, now=now)  # fine
    with pytest.raises(cb.BookingError):
        cb.validate_slot(_dt(2026, 10, 8, 10, 15), settings, now=now)  # not a slot
    with pytest.raises(cb.BookingError):
        cb.validate_slot(_dt(2026, 10, 1, 10), settings, now=now)  # past
    with pytest.raises(cb.BookingError):
        cb.validate_slot(now + timedelta(days=400), settings, now=now)  # too far
    closed = cb.normalize_settings({"closedWeekdays": [3]})  # Thursday
    with pytest.raises(cb.BookingError):
        cb.validate_slot(_dt(2026, 10, 8, 10), closed, now=now)


def test_parse_slot_datetime():
    assert cb.parse_slot_datetime("2026-10-12T13:30:00+08:00") == _dt(2026, 10, 12, 13, 30)
    assert cb.parse_slot_datetime("2026-10-12T05:30:00Z") == _dt(2026, 10, 12, 13, 30)
    with pytest.raises(cb.BookingError):
        cb.parse_slot_datetime("")
    with pytest.raises(cb.BookingError):
        cb.parse_slot_datetime("not a date")


# ── storage ──────────────────────────────────────────────────────────────

class _Cur:
    def __init__(self, row=None, raise_unique=False):
        self.sql: list[str] = []
        self.row = row
        self.raise_unique = raise_unique

    def execute(self, sql, params=None):
        self.sql.append(" ".join(sql.split()))
        if self.raise_unique and "insert into consult_bookings" in sql:
            raise psycopg.errors.UniqueViolation("dup")

    def fetchone(self):
        return self.row

    def fetchall(self):
        return []


def _row(**over):
    row = {
        "id": "11111111-1111-1111-1111-111111111111",
        "slot_start": _dt(2026, 10, 12, 13, 30),
        "name": "王小明",
        "phone": "0912",
        "email": None,
        "note": None,
        "lead_id": None,
        "status": "confirmed",
    }
    row.update(over)
    return row


def test_schema_has_partial_unique_index_and_rls():
    cur = _Cur()
    cb.ensure_consult_bookings_schema(cur)
    joined = " ".join(cur.sql)
    assert "create unique index if not exists consult_bookings_one_per_slot" in joined
    assert "where status <> 'cancelled'" in joined
    assert "enable row level security" in joined


def test_create_booking_conflict_and_validation():
    with pytest.raises(cb.BookingConflict):
        cb.create_booking(
            _Cur(raise_unique=True),
            slot_start=_dt(2026, 10, 12, 13, 30),
            name="A", phone="", email="", note="", lead_id=None,
        )
    with pytest.raises(cb.BookingError):
        cb.create_booking(
            _Cur(), slot_start=_dt(2026, 10, 12, 13, 30),
            name="  ", phone="", email="", note="", lead_id=None,
        )


def test_create_booking_returns_serialized_row():
    out = cb.create_booking(
        _Cur(row=_row()), slot_start=_dt(2026, 10, 12, 13, 30),
        name="王小明", phone="0912", email="", note="", lead_id=None,
    )
    assert out["date"] == "2026-10-12"
    assert out["label"] == "13:30–14:30"
    assert out["status"] == "confirmed"


def test_update_booking_rejects_bad_status_and_empty():
    with pytest.raises(cb.BookingError):
        cb.update_booking(_Cur(), "x", {"status": "weird"})
    with pytest.raises(cb.BookingError):
        cb.update_booking(_Cur(), "x", {})


# ── admin API ────────────────────────────────────────────────────────────

def _request(body=None):
    req = MagicMock()

    async def _json():
        return body

    req.json = _json
    return req


def _body(resp):
    return json.loads(resp.body)


@contextmanager
def _fake_conn(cur):
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    yield conn


def test_admin_guard_blocks_every_route(monkeypatch):
    def deny(_request):
        raise HTTPException(status_code=401, detail="no")

    monkeypatch.setattr(bc, "_require_admin", deny)
    uid = "11111111-1111-1111-1111-111111111111"
    calls = [
        lambda: bc.bookings_month(_request()),
        lambda: asyncio.run(bc.bookings_create(_request({}))),
        lambda: asyncio.run(bc.bookings_update(_request({}), uid)),
        lambda: bc.bookings_cancel(_request(), uid),
        lambda: asyncio.run(bc.bookings_settings_save(_request({}))),
    ]
    for call in calls:
        with pytest.raises(HTTPException) as err:
            call()
        assert err.value.status_code == 401


def test_create_returns_409_when_slot_taken(monkeypatch):
    monkeypatch.setattr(bc, "_require_admin", lambda r: "admin-1")
    monkeypatch.setattr(bc, "_audit", lambda *a, **k: None)
    monkeypatch.setattr(bc.cb, "load_settings", lambda: cb.default_settings())
    monkeypatch.setattr(bc.cb, "validate_slot", lambda *a, **k: None)
    monkeypatch.setattr(bc, "get_connection", lambda: _fake_conn(_Cur(raise_unique=True)))
    resp = asyncio.run(
        bc.bookings_create(_request({"slot": "2026-10-12T13:30:00+08:00", "name": "A"}))
    )
    assert resp.status_code == 409
    assert "已被預約" in _body(resp)["error"]


def test_create_rejects_bad_input(monkeypatch):
    monkeypatch.setattr(bc, "_require_admin", lambda r: "admin-1")
    monkeypatch.setattr(bc.cb, "load_settings", lambda: cb.default_settings())
    resp = asyncio.run(bc.bookings_create(_request({"slot": "", "name": "A"})))
    assert resp.status_code == 400
    assert asyncio.run(bc.bookings_create(_request(None))).status_code == 400
    bad_id = asyncio.run(bc.bookings_update(_request({"name": "x"}), "not-a-uuid"))
    assert bad_id.status_code == 400


def test_create_success_returns_booking(monkeypatch):
    monkeypatch.setattr(bc, "_require_admin", lambda r: "admin-1")
    monkeypatch.setattr(bc, "_audit", lambda *a, **k: None)
    monkeypatch.setattr(bc.cb, "load_settings", lambda: cb.default_settings())
    monkeypatch.setattr(bc.cb, "validate_slot", lambda *a, **k: None)
    monkeypatch.setattr(bc, "get_connection", lambda: _fake_conn(_Cur(row=_row())))
    out = asyncio.run(
        bc.bookings_create(_request({"slot": "2026-10-12T13:30:00+08:00", "name": "王小明"}))
    )
    assert out["ok"] is True
    assert out["booking"]["name"] == "王小明"
