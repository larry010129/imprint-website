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
    try:
        cur.execute("select day, sum(views)::bigint v from site_visits_daily "
                    "where day >= %s and day < %s group by day", (start, end))
        by_day = {r["day"]: int(r["v"]) for r in cur.fetchall()}
        out["daily_views"] = [by_day.get(start + timedelta(days=i), 0) for i in range(7)]
    except Exception:
        log.exception("daily_views failed")
        out["daily_views"] = None
    return out


def _delta(cur_v, prev_v) -> str:
    """Arrow + change vs last week; empty when unchanged (keeps zero rows quiet)."""
    if cur_v is None or prev_v is None:
        return ""
    diff = cur_v - prev_v
    if diff == 0:
        return ""
    arrow = "🔺" if diff > 0 else "🔻"
    if prev_v:
        return f"  {arrow} {abs(diff / prev_v) * 100:.0f}%"
    return f"  {arrow} {abs(diff):g}"


def _num(v, fmt="{:,}") -> str:
    return NO_DATA if v is None else fmt.format(v)


# ── chart ────────────────────────────────────────────────────────────────

CHART_W, CHART_H = 900, 380
_BG, _FG, _MUTED, _GRID = (43, 45, 49), (242, 243, 245), (148, 155, 164), (70, 73, 79)
_THIS = (88, 101, 242)
_LAST = tuple(int(0.4 * t + 0.6 * b) for t, b in zip(_THIS, _BG))
_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _font(size: int):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                    # Pillow < 10.1: fixed-size bitmap font
        return ImageFont.load_default()


def build_chart(this_daily: list[int], last_daily: list[int] | None,
                start: date, end: date) -> bytes:
    """PNG bar chart: page views per day, this week vs last week."""
    import io
    from PIL import Image, ImageDraw

    last_daily = last_daily or [0] * 7
    img = Image.new("RGB", (CHART_W, CHART_H), _BG)
    d = ImageDraw.Draw(img)
    last_day = end - timedelta(days=1)
    d.text((30, 16), "Page views per day", font=_font(22), fill=_FG)
    d.text((30, 50), f"{start:%Y-%m-%d} to {last_day:%Y-%m-%d} (Taipei time)",
           font=_font(14), fill=_MUTED)
    d.rectangle([CHART_W - 250, 22, CHART_W - 236, 36], fill=_THIS)
    d.text((CHART_W - 230, 19), "This week", font=_font(13), fill=_FG)
    d.rectangle([CHART_W - 140, 22, CHART_W - 126, 36], fill=_LAST)
    d.text((CHART_W - 120, 19), "Last week", font=_font(13), fill=_FG)

    x0, y0, x1, y1 = 60, 90, CHART_W - 30, CHART_H - 50
    peak = max(max(this_daily, default=0), max(last_daily, default=0), 1)
    base = 10 ** max(len(str(peak)) - 2, 0)
    for mult in (1, 2, 5, 10, 20, 50):   # 4 gridline gaps of a round size
        tick = base * mult
        if tick * 4 >= peak:
            break
    top_val = tick * 4
    for i in range(5):
        g = tick * i
        y = y1 - (y1 - y0) * g / top_val
        d.line([(x0, y), (x1, y)], fill=_GRID, width=1)
        d.text((14, y - 8), f"{g:,.0f}", font=_font(12), fill=_MUTED)
    slot = (x1 - x0) / 7
    bw = slot * 0.30
    for i, name in enumerate(_DAYS):
        cx = x0 + slot * (i + 0.5)
        for off, v, col in ((-bw / 2 - 2, last_daily[i], _LAST), (bw / 2 + 2, this_daily[i], _THIS)):
            top = y1 - (y1 - y0) * v / top_val
            if v:
                d.rounded_rectangle([cx + off - bw / 2, top, cx + off + bw / 2, y1],
                                    radius=4, fill=col)
        d.text((cx - 14, y1 + 8), name, font=_font(13), fill=_MUTED)
        if this_daily[i]:
            ty = y1 - (y1 - y0) * this_daily[i] / top_val - 18
            d.text((cx + bw / 2 + 2 - 14, ty), f"{this_daily[i]:,}", font=_font(11), fill=_FG)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


CHART_FILENAME = "chart.png"


def build_payload(cur_m: dict, prev_m: dict, start: date, end: date,
                  with_chart: bool = False) -> dict:
    last = end - timedelta(days=1)

    def pick(m, key, sub=None):
        v = m.get(key)
        return v if sub is None or v is None else v[sub]

    def line(label, key, sub=None, fmt="{:,}"):
        c, p = pick(cur_m, key, sub), pick(prev_m, key, sub)
        return f"**{label}:** {_num(c, fmt)}{_delta(c, p)}"

    fields = [
        {"name": "🌐 Traffic", "inline": False, "value": "\n".join([
            line("Page views", "visits", "views"),
            line("Unique visitors", "visits", "uniques")])},
        {"name": "🛒 Sales", "inline": False, "value": "\n".join([
            line("Orders", "orders", "count"),
            line("Revenue", "orders", "revenue", "NT${:,.0f}"),
            line("Coupons used", "coupons")])},
        {"name": "👥 Customers & enquiries", "inline": False, "value": "\n".join([
            line("New accounts", "accounts"),
            line("Consultation bookings", "bookings"),
            line("Contact messages", "contacts"),
            line("Quote requests", "quotes")])},
        {"name": "🔒 Security", "inline": False,
         "value": line("Login lockouts", "lockouts")},
    ]
    top = cur_m.get("top_pages")
    if top:
        fields.append({"name": "🔥 Top pages", "inline": False, "value": "\n".join(
            f"{i}. `{p}` - {v:,}" for i, (p, v) in enumerate(top, 1))[:1000]})
    embed = {
        "title": "📊 Weekly site report",
        "description": f"{start:%Y-%m-%d} to {last:%Y-%m-%d} (Taipei time)",
        "color": 0x5865F2,
        "fields": fields,
    }
    if with_chart:
        embed["image"] = {"url": f"attachment://{CHART_FILENAME}"}
    return {"embeds": [embed]}


def send(payload: dict, url: str, chart_png: bytes | None = None) -> None:
    if chart_png:
        r = requests.post(
            url, data={"payload_json": json.dumps(payload)},
            files={"files[0]": (CHART_FILENAME, chart_png, "image/png")}, timeout=20)
    else:
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


def build_report(end: date) -> tuple[dict, bytes | None]:
    """(Discord payload, chart PNG or None). A chart failure never blocks the text."""
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
    png = None
    if cur_m.get("daily_views") is not None:
        try:
            png = build_chart(cur_m["daily_views"], prev_m.get("daily_views"), start, end)
        except Exception:
            log.exception("chart failed; sending text only")
    return build_payload(cur_m, prev_m, start, end, with_chart=png is not None), png


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
            payload, png = build_report(end)
            send(payload, webhook_url(), png)
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
