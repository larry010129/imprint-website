"""First-party, cookieless page-view counter for the admin dashboard.

Every public HTML page load is +1 view (no login needed). Unique visitors are
counted once per day from a one-way hash of IP + User-Agent salted with the
day, so nothing is stored on the visitor's device and no raw IP is saved.
The request path only touches an in-memory buffer; a background task writes
batched upserts every FLUSH_INTERVAL_SECONDS.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import threading
from datetime import date, datetime, timedelta, timezone

from app.robots_host import is_noindex_host

log = logging.getLogger(__name__)

FLUSH_INTERVAL_SECONDS = 30
MAX_PATH_LEN = 200
MAX_BUFFER_KEYS = 20000
# Visitor hashes only need to live long enough to dedupe within a day.
VISITOR_RETENTION_DAYS = 2
TOP_PAGES_LIMIT = 8

_TZ_TAIPEI = timezone(timedelta(hours=8))

_SKIP_PREFIXES = ("/api/", "/htmx/", "/admin", "/static/", "/js/", "/css/")
_SKIP_PATHS = frozenset(
    {"/health", "/robots.txt", "/sitemap.xml", "/llms.txt", "/favicon.svg"}
)
_BOT_MARKERS = (
    "bot", "crawl", "spider", "slurp", "headless", "preview", "monitor",
    "curl/", "wget", "python-requests", "python-urllib", "httpx", "aiohttp",
    "go-http-client", "okhttp", "java/", "libwww", "scrapy", "lighthouse",
    "facebookexternalhit", "pingdom", "uptime",
)


def enabled() -> bool:
    """Count only on Render (or VISIT_COUNTER=1). Local dev and TestClient use
    the production DB, so counting there would pollute live numbers."""
    from config.settings import settings

    return bool(settings.is_render) or os.environ.get("VISIT_COUNTER") == "1"


def is_bot(user_agent: str | None) -> bool:
    ua = (user_agent or "").strip().lower()
    return not ua or any(marker in ua for marker in _BOT_MARKERS)


def is_countable(
    *,
    method: str,
    status: int,
    content_type: str,
    path: str,
    user_agent: str | None,
    host: str | None,
    htmx: bool = False,
) -> bool:
    if method != "GET" or status != 200 or htmx:
        return False
    if not (content_type or "").lower().startswith("text/html"):
        return False
    if path in _SKIP_PATHS or path.startswith(_SKIP_PREFIXES):
        return False
    if is_noindex_host(host):
        return False
    return not is_bot(user_agent)


def normalize_path(path: str) -> str:
    # Shared-quote tokens (/s/<token>) must not be stored as page names.
    if path.startswith("/s/"):
        return "/s/*"
    if len(path) > 1:
        path = path.rstrip("/") or "/"
    return path[:MAX_PATH_LEN]


def visitor_hash(ip: str, user_agent: str, day: str) -> str:
    secret = os.environ.get("JWT_SECRET", "")
    raw = f"{secret}|{day}|{ip}|{user_agent}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def today_local() -> str:
    return datetime.now(_TZ_TAIPEI).strftime("%Y-%m-%d")


class _Buffer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.views: dict[tuple[str, str], int] = {}
        self.visitors: dict[str, set[str]] = {}
        self._seen_day = ""
        self._seen: set[str] = set()

    def record(self, day: str, path: str, visitor: str) -> None:
        with self._lock:
            key = (day, path)
            if key in self.views or len(self.views) < MAX_BUFFER_KEYS:
                self.views[key] = self.views.get(key, 0) + 1
            if day != self._seen_day:
                self._seen_day = day
                self._seen = set()
            if visitor not in self._seen and len(self._seen) < MAX_BUFFER_KEYS * 10:
                self._seen.add(visitor)
                self.visitors.setdefault(day, set()).add(visitor)

    def drain(self) -> tuple[dict, dict]:
        with self._lock:
            views, visitors = self.views, self.visitors
            self.views, self.visitors = {}, {}
            return views, visitors

    def restore(self, views: dict, visitors: dict) -> None:
        """Put a failed batch back so the next flush retries it."""
        with self._lock:
            for key, count in views.items():
                if key in self.views or len(self.views) < MAX_BUFFER_KEYS:
                    self.views[key] = self.views.get(key, 0) + count
            for day, hashes in visitors.items():
                self.visitors.setdefault(day, set()).update(hashes)


_buffer = _Buffer()


def record_visit(request, response) -> None:
    """Called from the HTTP middleware after the response is built."""
    if not enabled():
        return
    path = request.url.path
    ua = request.headers.get("user-agent", "")
    if not is_countable(
        method=request.method,
        status=response.status_code,
        content_type=response.headers.get("content-type", ""),
        path=path,
        user_agent=ua,
        host=request.headers.get("host"),
        htmx=request.headers.get("hx-request") == "true",
    ):
        return
    from app.auth import client_ip

    day = today_local()
    _buffer.record(day, normalize_path(path), visitor_hash(client_ip(request), ua, day))


# ── storage ──────────────────────────────────────────────────────────────

def ensure_site_visits_schema(cur) -> None:
    cur.execute(
        """
        create table if not exists site_visits_daily (
          day date not null,
          path text not null,
          views bigint not null default 0,
          primary key (day, path)
        )
        """
    )
    cur.execute(
        """
        create table if not exists site_visit_uniques (
          day date primary key,
          uniques bigint not null default 0
        )
        """
    )
    cur.execute(
        """
        create table if not exists site_visitor_days (
          day date not null,
          visitor text not null,
          primary key (day, visitor)
        )
        """
    )
    for table in ("site_visits_daily", "site_visit_uniques", "site_visitor_days"):
        cur.execute(f"alter table {table} enable row level security")


def _write_batch(cur, views: dict, visitors: dict) -> None:
    if views:
        cur.executemany(
            """
            insert into site_visits_daily (day, path, views) values (%s, %s, %s)
            on conflict (day, path) do update
              set views = site_visits_daily.views + excluded.views
            """,
            [(date.fromisoformat(d), p, n) for (d, p), n in views.items()],
        )
    for day, hashes in visitors.items():
        day_value = date.fromisoformat(day)
        cur.execute(
            """
            insert into site_visitor_days (day, visitor)
            select %s, unnest(%s::text[]) on conflict do nothing
            """,
            (day_value, list(hashes)),
        )
        added = cur.rowcount
        if added and added > 0:
            cur.execute(
                """
                insert into site_visit_uniques (day, uniques) values (%s, %s)
                on conflict (day) do update
                  set uniques = site_visit_uniques.uniques + excluded.uniques
                """,
                (day_value, added),
            )
    cutoff = date.fromisoformat(today_local()) - timedelta(days=VISITOR_RETENTION_DAYS)
    cur.execute("delete from site_visitor_days where day < %s", (cutoff,))


def flush() -> None:
    """Write buffered counts to the DB. Safe to call from any thread."""
    views, visitors = _buffer.drain()
    if not views and not visitors:
        return
    try:
        from app.database import get_transaction

        with get_transaction() as conn, conn.cursor() as cur:
            _write_batch(cur, views, visitors)
    except Exception:
        log.exception("site visit flush failed; will retry")
        _buffer.restore(views, visitors)


async def flush_loop() -> None:
    while True:
        await asyncio.sleep(FLUSH_INTERVAL_SECONDS)
        await asyncio.to_thread(flush)


# ── dashboard queries ────────────────────────────────────────────────────

def bounds_to_days(since: datetime, until: datetime) -> tuple[date, date]:
    """UTC [since, until) from dashboard_fetch_bounds -> Taipei [start, end) dates."""
    offset = timedelta(hours=8)
    return (since + offset).date(), (until + offset).date()


def _bucket_key(day: str, granularity: str) -> str:
    if granularity == "day":
        return day
    if granularity == "week":
        iso = date.fromisoformat(day).isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return day[:7]


def period_day_bounds(cfg: dict) -> tuple[date, date]:
    """[start, end) local dates of the selected dashboard period."""
    gran = cfg.get("granularity")
    if gran == "day":
        return (
            date.fromisoformat(cfg["start"]),
            date.fromisoformat(cfg["end"]) + timedelta(days=1),
        )
    if gran == "week":
        year, week = map(int, cfg["period"].split("-W"))
        start = date.fromisocalendar(year, week, 1)
        return start, start + timedelta(days=7)
    year, month = map(int, cfg["period"].split("-"))
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def fetch_visit_daily(cur, start: date, end: date) -> dict[str, dict]:
    cur.execute(
        """
        select to_char(day, 'YYYY-MM-DD') as day, sum(views)::bigint as views
        from site_visits_daily where day >= %s and day < %s group by day
        """,
        (start, end),
    )
    daily: dict[str, dict] = {
        r["day"]: {"views": int(r["views"]), "uniques": 0} for r in cur.fetchall()
    }
    cur.execute(
        """
        select to_char(day, 'YYYY-MM-DD') as day, uniques
        from site_visit_uniques where day >= %s and day < %s
        """,
        (start, end),
    )
    for r in cur.fetchall():
        daily.setdefault(r["day"], {"views": 0, "uniques": 0})["uniques"] = int(r["uniques"])
    return daily


def fetch_top_pages(cur, start: date, end: date, limit: int = TOP_PAGES_LIMIT) -> list[dict]:
    cur.execute(
        """
        select path, sum(views)::bigint as views from site_visits_daily
        where day >= %s and day < %s group by path order by views desc, path limit %s
        """,
        (start, end, limit),
    )
    return [{"path": r["path"], "views": int(r["views"])} for r in cur.fetchall()]


def build_visit_payload(daily: dict[str, dict], cfg: dict, top_pages: list[dict]) -> dict:
    gran = cfg["granularity"]
    buckets = {key: {"views": 0, "uniques": 0} for key in cfg["bucketKeys"]}
    for day, vals in daily.items():
        key = _bucket_key(day, gran)
        if key in buckets:
            buckets[key]["views"] += vals["views"]
            buckets[key]["uniques"] += vals["uniques"]
    if gran == "day":
        period = [v for d, v in daily.items() if cfg["start"] <= d <= cfg["end"]]
        views = sum(v["views"] for v in period)
        uniques = sum(v["uniques"] for v in period)
    else:
        selected = buckets.get(cfg["period"], {})
        views = selected.get("views", 0)
        uniques = selected.get("uniques", 0)
    return {
        # Uniques are per day; a multi-day total is the sum of daily uniques.
        "views": views,
        "uniques": uniques,
        "trend": [
            {"key": key, "views": b["views"], "uniques": b["uniques"]}
            for key, b in buckets.items()
        ],
        "topPages": top_pages,
    }


def empty_visit_payload() -> dict:
    return {"views": 0, "uniques": 0, "trend": [], "topPages": []}
