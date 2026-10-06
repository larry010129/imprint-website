"""Visit counter: filter rules, hashing, buffering, flush SQL, dashboard payload.

No test touches the DB (local .env points at production).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from app import site_visits as sv


def _countable(**over):
    args = dict(
        method="GET",
        status=200,
        content_type="text/html; charset=utf-8",
        path="/about",
        user_agent="Mozilla/5.0 (Windows NT 10.0) Chrome/120",
        host="www.imprint-diamond.com",
        htmx=False,
    )
    args.update(over)
    return sv.is_countable(**args)


def test_normal_page_counts_without_login():
    assert _countable()


def test_non_pages_are_skipped():
    assert not _countable(method="HEAD")
    assert not _countable(status=404)
    assert not _countable(content_type="application/json")
    assert not _countable(htmx=True)
    for path in ("/api/x", "/htmx/cart", "/admin", "/admin1.html", "/static/a.css", "/health", "/robots.txt"):
        assert not _countable(path=path), path


def test_bots_and_mirror_hosts_are_skipped():
    assert not _countable(user_agent="Googlebot/2.1")
    assert not _countable(user_agent="curl/8.0")
    assert not _countable(user_agent="")
    assert not _countable(host="imprintdiamond.com")
    assert not _countable(host="imprint.onrender.com")


def test_normalize_path_hides_share_tokens():
    assert sv.normalize_path("/s/secret-token") == "/s/*"
    assert sv.normalize_path("/about/") == "/about"
    assert sv.normalize_path("/") == "/"


def test_visitor_hash_is_stable_per_day_and_differs_across_days():
    a = sv.visitor_hash("1.2.3.4", "ua", "2026-10-06")
    assert a == sv.visitor_hash("1.2.3.4", "ua", "2026-10-06")
    assert a != sv.visitor_hash("1.2.3.4", "ua", "2026-10-07")
    assert a != sv.visitor_hash("1.2.3.5", "ua", "2026-10-06")
    assert "1.2.3.4" not in a


def test_buffer_counts_every_view_but_each_visitor_once():
    buf = sv._Buffer()
    for _ in range(3):
        buf.record("2026-10-06", "/", "v1")
    buf.record("2026-10-06", "/about", "v2")
    views, visitors = buf.drain()
    assert views == {("2026-10-06", "/"): 3, ("2026-10-06", "/about"): 1}
    assert visitors == {"2026-10-06": {"v1", "v2"}}
    assert buf.drain() == ({}, {})


def test_buffer_restore_merges_back():
    buf = sv._Buffer()
    buf.record("2026-10-06", "/", "v1")
    views, visitors = buf.drain()
    buf.record("2026-10-06", "/", "v2")
    buf.restore(views, visitors)
    views2, visitors2 = buf.drain()
    assert views2[("2026-10-06", "/")] == 2
    assert visitors2["2026-10-06"] == {"v1", "v2"}


class _Cur:
    def __init__(self, added=2):
        self.calls = []
        self.many = []
        self.rowcount = added

    def execute(self, sql, params=None):
        self.calls.append((" ".join(sql.split()), params))

    def executemany(self, sql, rows):
        self.many.append((" ".join(sql.split()), list(rows)))


def test_write_batch_upserts_views_and_new_uniques():
    cur = _Cur(added=2)
    sv._write_batch(
        cur,
        {("2026-10-06", "/"): 3},
        {"2026-10-06": {"a", "b"}},
    )
    assert cur.many[0][1] == [(date(2026, 10, 6), "/", 3)]
    sql = [c[0] for c in cur.calls]
    assert any("insert into site_visit_uniques" in s for s in sql)
    assert any(s.startswith("delete from site_visitor_days") for s in sql)
    uniques_call = next(c for c in cur.calls if "site_visit_uniques" in c[0])
    assert uniques_call[1] == (date(2026, 10, 6), 2)


def test_write_batch_skips_uniques_when_all_already_seen():
    cur = _Cur(added=0)
    sv._write_batch(cur, {}, {"2026-10-06": {"a"}})
    assert not any("insert into site_visit_uniques" in c[0] for c in cur.calls)


def _cfg(gran="month", period="2026-10", keys=None, start="2026-10-01", end="2026-10-31"):
    return {
        "granularity": gran,
        "period": period,
        "start": start,
        "end": end,
        "bucketKeys": keys or ["2026-09", "2026-10"],
    }


def test_build_visit_payload_month_period_and_trend():
    daily = {
        "2026-09-30": {"views": 5, "uniques": 2},
        "2026-10-01": {"views": 10, "uniques": 4},
        "2026-10-02": {"views": 6, "uniques": 3},
    }
    out = sv.build_visit_payload(daily, _cfg(), [{"path": "/", "views": 9}])
    assert out["views"] == 16 and out["uniques"] == 7
    assert out["trend"] == [
        {"key": "2026-09", "views": 5, "uniques": 2},
        {"key": "2026-10", "views": 16, "uniques": 7},
    ]
    assert out["topPages"] == [{"path": "/", "views": 9}]


def test_build_visit_payload_day_range():
    keys = ["2026-10-01", "2026-10-02"]
    daily = {"2026-10-01": {"views": 3, "uniques": 1}, "2026-10-02": {"views": 4, "uniques": 2}}
    out = sv.build_visit_payload(
        daily, _cfg("day", "", keys, "2026-10-01", "2026-10-02"), []
    )
    assert (out["views"], out["uniques"]) == (7, 3)


def test_period_day_bounds():
    assert sv.period_day_bounds(_cfg(period="2026-12")) == (date(2026, 12, 1), date(2027, 1, 1))
    assert sv.period_day_bounds(_cfg("week", "2026-W41")) == (date(2026, 10, 5), date(2026, 10, 12))
    assert sv.period_day_bounds(_cfg("day", "", None, "2026-10-01", "2026-10-03")) == (
        date(2026, 10, 1),
        date(2026, 10, 4),
    )


def test_bounds_to_days_uses_taipei_dates():
    since = datetime(2026, 9, 30, 16, 0, tzinfo=timezone.utc)  # 10/01 00:00 +08
    until = datetime(2026, 10, 31, 16, 0, tzinfo=timezone.utc)  # 11/01 00:00 +08
    assert sv.bounds_to_days(since, until) == (date(2026, 10, 1), date(2026, 11, 1))
