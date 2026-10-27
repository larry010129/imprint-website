"""Weekly site report -> Discord webhook.

Counts and totals only (no customer names or contact details).

  python scripts/weekly_report.py             # send last Mon-Sun (Taipei) report
  python scripts/weekly_report.py --dry-run   # print the payload, send nothing
  python scripts/weekly_report.py --on-deploy # Render pre-deploy: send only when
                                              # REPORT_ON_DEPLOY=1 is set

Never exits non-zero, so it cannot block a Render deploy. Needs DATABASE_URL and
DISCORD_REPORT_WEBHOOK_URL.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

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


def run(argv: list[str]) -> None:
    dry = "--dry-run" in argv
    if "--on-deploy" in argv and os.environ.get("REPORT_ON_DEPLOY") != "1":
        print("weekly_report: REPORT_ON_DEPLOY not set, skipping")
        return
    url = os.environ.get("DISCORD_REPORT_WEBHOOK_URL", "").strip()
    if not url and not dry:
        print("weekly_report: DISCORD_REPORT_WEBHOOK_URL not set, skipping")
        return

    from app.database import get_connection

    prev_start, start, end = week_bounds(datetime.now(TAIPEI).date())
    with get_connection() as conn, conn.cursor() as cur:
        cur_m = collect(cur, start, end)
        prev_m = collect(cur, prev_start, start)
    payload = build_payload(cur_m, prev_m, start, end)
    if dry:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    send(payload, url)
    print(f"weekly_report: sent report for {start} to {end - timedelta(days=1)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        run(sys.argv[1:])
    except Exception:
        # Never fail the deploy / cron over a report.
        log.exception("weekly_report failed")
    sys.exit(0)
