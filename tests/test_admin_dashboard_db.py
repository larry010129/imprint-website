"""P3 DB hot-path: dashboard bounds + admin order search typed columns only."""

from __future__ import annotations

import inspect

from app.admin_dashboard import dashboard_fetch_bounds, normalize_range
from app.controllers import admin_controller as ac


def test_dashboard_fetch_bounds_day_span():
    cfg = normalize_range(granularity="day", start="2026-07-01", end="2026-07-10")
    since, until = dashboard_fetch_bounds(cfg)
    assert until > since
    assert (until - since).days == 10
    assert since.tzinfo is not None


def test_dashboard_fetch_bounds_month_covers_buckets():
    cfg = normalize_range(granularity="month")
    since, until = dashboard_fetch_bounds(cfg)
    assert until > since
    # 12 month buckets ⇒ roughly a year of rows, not full history
    assert 300 <= (until - since).days <= 400


def test_fetch_orders_requires_bounds():
    try:
        ac._fetch_orders(None)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "since/until" in str(exc)


def test_admin_order_search_skips_config_json_cast():
    src = inspect.getsource(ac.orders_list)
    assert "config_json::text" not in src
    assert "oi.summary_zh ilike" in src
    assert "o.order_number ilike" in src
