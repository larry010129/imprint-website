"""Weekly site report -> Discord webhook (counts and totals only, no PII).

Used by the in-app scheduler (`report_loop`, started from the FastAPI lifespan)
and by scripts/weekly_report.py (CLI / Render pre-deploy test send).

Schedule: Monday 09:00 Asia/Taipei for the previous Mon-Sun week. The loop wakes
every minute; a row in `weekly_report_log` (primary key = week end date) is
claimed atomically so only one gunicorn worker / overlapping deploy sends it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone

import requests

log = logging.getLogger("weekly_report")

TAIPEI = timezone(timedelta(hours=8))
NO_DATA = "n/a"


def week_bounds(today: date) -> tuple[date, date, date]:
    """(prev_start, start, end): last full Mon-Sun week and the week before it.

    `end` is exclusive (the Monday on/before `today`).
    """
    end = today - timedelta(days=today.weekday())
    start = end - timedelta(days=7)
    return start - timedelta(days=7), start, end


def _at(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=TAIPEI)


def _one(cur, sql: str, params: tuple) -> dict:
    cur.execute(sql, params)
    return cur.fetchone() or {}


def collect(cur, start: date, end: date) -> dict:
    """Metrics for [start, end). A failing query yields None, not a crash."""
    s, e = _at(start), _at(end)
    out: dict = {}

    def safe(key, fn):
        try:
            out[key] = fn()
        except Exception:
            log.exception("metric %s failed", key)
            out[key] = None

    def visits():
        r = _one(cur, "select coalesce(sum(views),0)::bigint v from site_visits_daily "
                 "where day >= %s and day < %s", (start, end))
        u = _one(cur, "select coalesce(sum(uniques),0)::bigint u from site_visit_uniques "
                 "where day >= %s and day < %s", (start, end))
        return {"views": int(r.get("v", 0)), "uniques": int(u.get("u", 0))}

    def orders():
        r = _one(cur, "select count(*)::bigint n, coalesce(sum(total_price),0) rev "
                 "from orders where created_at >= %s and created_at < %s "
                 "and status not in ('cancelled','canceled')", (s, e))
        return {"count": int(r.get("n", 0)), "revenue": float(r.get("rev", 0) or 0)}

    def count(table, extra=""):
        return lambda: int(_one(cur, f"select count(*)::bigint n from {table} "
                               f"where created_at >= %s and created_at < %s {extra}",
                               (s, e)).get("n", 0))

    safe("visits", visits)
    safe("orders", orders)
    safe("accounts", count("users"))
    safe("contacts", count("contact_messages"))
    safe("quotes", count("quote_requests"))
    safe("bookings", count("consult_bookings", "and status <> 'cancelled'"))
    safe("coupons", count("coupon_redemptions"))
    safe("lockouts", lambda: int(_one(
        cur, "select count(*)::bigint n from login_lockouts where locked_until is not null "
        "and updated_at >= %s and updated_at < %s", (s, e)).get("n", 0)))
    try:
        cur.execute("select path, sum(views)::bigint v from site_visits_daily "
                    "where day >= %s and day < %s group by path order by v desc, path limit 5",
                    (start, end))
        out["top_pages"] = [(r["path"], int(r["v"])) for r in cur.fetchall()]
    except Exception:
        log.exception("top_pages failed")
        out["top_pages"] = None
    return out


def _delta(cur_v, prev_v) -> str:
    if cur_v is None or prev_v is None:
        return ""
    diff = cur_v - prev_v
    if diff == 0:
        return " (no change)"
    sign = "+" if diff > 0 else "-"
    if prev_v:
        return f" ({sign}{abs(diff / prev_v) * 100:.0f}% vs last wk)"
    return f" ({sign}{abs(diff):g} vs last wk)"


def _num(v, fmt="{:,}") -> str:
    return NO_DATA if v is None else fmt.format(v)


def build_payload(cur_m: dict, prev_m: dict, start: date, end: date) -> dict:
    last = end - timedelta(days=1)

    def pick(m, key, sub=None):
        v = m.get(key)
        return v if sub is None or v is None else v[sub]

    def line(label, key, sub=None, fmt="{:,}"):
        c, p = pick(cur_m, key, sub), pick(prev_m, key, sub)
        return f"**{label}:** {_num(c, fmt)}{_delta(c, p)}"

    fields = [
        {"name": "Traffic", "inline": False, "value": "\n".join([
            line("Page views", "visits", "views"),
            line("Unique visitors", "visits", "uniques")])},
        {"name": "Sales", "inline": False, "value": "\n".join([
            line("Orders", "orders", "count"),
            line("Revenue", "orders", "revenue", "NT${:,.0f}"),
            line("Coupons used", "coupons")])},
        {"name": "Customers & enquiries", "inline": False, "value": "\n".join([
            line("New accounts", "accounts"),
            line("Consultation bookings", "bookings"),
            line("Contact messages", "contacts"),
            line("Quote requests", "quotes")])},
        {"name": "Security", "inline": False,
         "value": line("Login lockouts", "lockouts")},
    ]
    top = cur_m.get("top_pages")
    if top:
        fields.append({"name": "Top pages", "inline": False,
                       "value": "\n".join(f"`{p}` - {v:,}" for p, v in top)[:1000]})
    return {"embeds": [{
        "title": "Weekly site report",
        "description": f"{start:%Y-%m-%d} to {last:%Y-%m-%d} (Taipei time)",
        "color": 0x5865F2,
        "fields": fields,
    }]}


def send(payload: dict, url: str) -> None:
    r = requests.post(url, json=payload, timeout=15)
    r.raise_for_status()


# ── scheduling ───────────────────────────────────────────────────────────

REPORT_HOUR = 9
CATCH_UP_HOURS = 12      # a missed Monday report is still sent for this long
CHECK_SECONDS = 60
RETRY_SECONDS = 600      # after a failed Discord send
STATEMENT_TIMEOUT_MS = 15000


def webhook_url() -> str:
    return os.environ.get("DISCORD_REPORT_WEBHOOK_URL", "").strip()


def enabled() -> bool:
    return bool(webhook_url())


def due_week_end(now: datetime) -> date | None:
    """Monday (report period end) if `now` is inside that Monday's send window."""
    now = now.astimezone(TAIPEI)
    monday = now.date() - timedelta(days=now.weekday())
    due_at = datetime(monday.year, monday.month, monday.day, REPORT_HOUR, tzinfo=TAIPEI)
    if due_at <= now < due_at + timedelta(hours=CATCH_UP_HOURS):
        return monday
    return None


def ensure_weekly_report_schema(cur) -> None:
    cur.execute(
        """
        create table if not exists weekly_report_log (
          week_end date primary key,
          sent_at timestamptz not null default now()
        )
        """
    )
    cur.execute("alter table weekly_report_log enable row level security")


def build_report(end: date) -> dict:
    from app.database import get_connection

    start = end - timedelta(days=7)
    prev_start = start - timedelta(days=7)
    with get_connection() as conn, conn.cursor() as cur:
        try:
            cur.execute(f"set statement_timeout = {STATEMENT_TIMEOUT_MS}")
            cur_m = collect(cur, start, end)
            prev_m = collect(cur, prev_start, start)
        finally:
            cur.execute("reset statement_timeout")
    return build_payload(cur_m, prev_m, start, end)


def tick(now: datetime | None = None) -> bool:
    """Send this week's report if due and not yet claimed. True if sent."""
    from app.database import get_connection

    now = now or datetime.now(TAIPEI)
    end = due_week_end(now)
    if end is None or not enabled():
        return False
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "insert into weekly_report_log (week_end) values (%s) "
            "on conflict do nothing returning week_end", (end,))
        if cur.fetchone() is None:
            return False                      # another worker already has it
        try:
            send(build_report(end), webhook_url())
        except Exception:
            cur.execute("delete from weekly_report_log where week_end = %s", (end,))
            raise
    log.info("weekly report sent for week ending %s", end)
    return True


async def report_loop() -> None:
    last_fail = 0.0
    while True:
        await asyncio.sleep(CHECK_SECONDS)
        if time.monotonic() - last_fail < RETRY_SECONDS:
            continue
        try:
            await asyncio.to_thread(tick)
        except Exception:
            last_fail = time.monotonic()
            log.exception("weekly report failed; will retry")
