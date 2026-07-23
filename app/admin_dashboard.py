"""Admin dashboard aggregates — day/week/month ranges and CSV export."""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime, timedelta, timezone

GRANULARITIES = ("day", "week", "month")
MAX_DAY_SPAN = 90
DAY_TREND_DEFAULT = 30
WEEK_TREND_COUNT = 12
MONTH_TREND_COUNT = 12
COMPLETE_STATUSES = {"completed", "shipped"}

STATUS_LABELS_ZH = {
    "received": "已收到申請",
    "dna_lab": "DNA 萃取鑑定中",
    "deposit_confirmed": "訂金已確認",
    "in_production": "製作中",
    "quality_check": "品管檢驗中",
    "shipped": "已出貨",
    "completed": "已完成",
}

_WEEK_RE = re.compile(r"^(\d{4})-W(\d{2})$")


def _now_local() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=8)


def _parse_date(value: str | None) -> date | None:
    try:
        return datetime.strptime(value or "", "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _parse_month(value: str | None) -> str | None:
    try:
        datetime.strptime(value or "", "%Y-%m")
        return value
    except (TypeError, ValueError):
        return None


def _parse_week(value: str | None) -> str | None:
    match = _WEEK_RE.match(value or "")
    if not match:
        return None
    year, week = int(match.group(1)), int(match.group(2))
    try:
        date.fromisocalendar(year, week, 1)
        return f"{year}-W{week:02d}"
    except ValueError:
        return None


def _week_start(week_str: str) -> date:
    year, week = map(int, week_str.split("-W"))
    return date.fromisocalendar(year, week, 1)


def _week_label(week_str: str) -> str:
    start = _week_start(week_str)
    end = start + timedelta(days=6)
    return f"{start.month}/{start.day}–{end.month}/{end.day}"


def _month_bucket_keys(now_local: datetime, count: int = MONTH_TREND_COUNT) -> list[str]:
    keys: list[str] = []
    year, month_num = now_local.year, now_local.month
    for offset in range(count - 1, -1, -1):
        index = year * 12 + (month_num - 1) - offset
        y, m = divmod(index, 12)
        keys.append(f"{y:04d}-{m + 1:02d}")
    return keys


def _week_bucket_keys(now_local: datetime, count: int = WEEK_TREND_COUNT) -> list[str]:
    today = now_local.date()
    iso = today.isocalendar()
    current = date.fromisocalendar(iso.year, iso.week, 1)
    keys: list[str] = []
    for offset in range(count - 1, -1, -1):
        week_start = current - timedelta(weeks=offset)
        iso_week = week_start.isocalendar()
        keys.append(f"{iso_week.year}-W{iso_week.week:02d}")
    return keys


def _day_bucket_keys(start_date: date, end_date: date) -> list[str]:
    keys: list[str] = []
    cursor = start_date
    while cursor <= end_date:
        keys.append(cursor.strftime("%Y-%m-%d"))
        cursor += timedelta(days=1)
    return keys


def _order_week_key(created_at: datetime | None) -> str:
    if not created_at:
        return ""
    local = created_at + timedelta(hours=8) if created_at.tzinfo else created_at
    iso = local.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _order_day_key(created_at: datetime | None) -> str:
    if not created_at:
        return ""
    local = created_at + timedelta(hours=8) if created_at.tzinfo else created_at
    return local.strftime("%Y-%m-%d")


def _order_month_key(created_at: datetime | None) -> str:
    if not created_at:
        return ""
    local = created_at + timedelta(hours=8) if created_at.tzinfo else created_at
    return local.strftime("%Y-%m")


def normalize_range(
    *,
    granularity: str | None = None,
    period: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    now_local = _now_local()
    today = now_local.date()
    gran = (granularity or "month").strip().lower()
    if gran not in GRANULARITIES:
        gran = "month"

    month_keys = _month_bucket_keys(now_local)
    week_keys = _week_bucket_keys(now_local)
    month_options = [{"value": key, "label": key} for key in reversed(month_keys)]
    week_options = [{"value": key, "label": _week_label(key)} for key in reversed(week_keys)]

    if gran == "month":
        selected = _parse_month(period) or now_local.strftime("%Y-%m")
        bucket_keys = month_keys
        period_label = selected
        range_start = range_end = None
    elif gran == "week":
        selected = _parse_week(period) or _order_week_key(now_local)
        bucket_keys = week_keys
        period_label = _week_label(selected)
        range_start = range_end = None
    else:
        end_date = _parse_date(end) or today
        start_date = _parse_date(start) or (end_date - timedelta(days=DAY_TREND_DEFAULT - 1))
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        if (end_date - start_date).days > MAX_DAY_SPAN - 1:
            start_date = end_date - timedelta(days=MAX_DAY_SPAN - 1)
        bucket_keys = _day_bucket_keys(start_date, end_date)
        selected = None
        period_label = f"{start_date.strftime('%Y-%m-%d')} – {end_date.strftime('%Y-%m-%d')}"
        range_start = start_date.strftime("%Y-%m-%d")
        range_end = end_date.strftime("%Y-%m-%d")

    return {
        "granularity": gran,
        "period": selected or "",
        "start": range_start or (today - timedelta(days=DAY_TREND_DEFAULT - 1)).strftime("%Y-%m-%d"),
        "end": range_end or today.strftime("%Y-%m-%d"),
        "periodLabel": period_label,
        "monthOptions": month_options,
        "weekOptions": week_options,
        "bucketKeys": bucket_keys,
    }


def _order_in_period(order: dict, cfg: dict) -> bool:
    created_at = order.get("created_at")
    gran = cfg["granularity"]
    if gran == "day":
        key = _order_day_key(created_at)
        return bool(key) and cfg["start"] <= key <= cfg["end"]
    if gran == "week":
        return _order_week_key(created_at) == cfg["period"]
    return _order_month_key(created_at) == cfg["period"]


def _trend_label(key: str, granularity: str) -> str:
    if granularity == "month" and len(key) >= 7:
        return f"{int(key[5:7])}月"
    if granularity == "week":
        return _week_label(key)
    if granularity == "day" and len(key) >= 10:
        return key[5:]
    return key


def _bucket_key(order: dict, granularity: str) -> str:
    created_at = order.get("created_at")
    if granularity == "day":
        return _order_day_key(created_at)
    if granularity == "week":
        return _order_week_key(created_at)
    return _order_month_key(created_at)


def build_dashboard_payload(orders: list[dict], cfg: dict) -> dict:
    bucket_keys = cfg["bucketKeys"]
    gran = cfg["granularity"]

    period_orders = [o for o in orders if _order_in_period(o, cfg)]
    period_completed = [o for o in period_orders if o.get("status") in COMPLETE_STATUSES]
    period_revenue = sum(float(o.get("total_price") or 0) for o in period_completed)
    period_order_count = len(period_orders)
    average_sale = period_revenue / len(period_completed) if period_completed else 0

    buckets: dict[str, dict] = {
        key: {"orderCount": 0, "completedOrders": 0, "orderTotal": 0.0, "revenue": 0.0}
        for key in bucket_keys
    }

    for order in orders:
        key = _bucket_key(order, gran)
        if key not in buckets:
            continue
        price = float(order.get("total_price") or 0)
        buckets[key]["orderCount"] += 1
        buckets[key]["orderTotal"] += price
        if order.get("status") in COMPLETE_STATUSES:
            buckets[key]["completedOrders"] += 1
            buckets[key]["revenue"] += price

    monthly_trend = [
        {
            "month": key,
            "label": _trend_label(key, gran),
            "orderCount": buckets[key]["orderCount"],
            "completedOrders": buckets[key]["completedOrders"],
            "orderTotal": buckets[key]["orderTotal"],
            "revenue": buckets[key]["revenue"],
        }
        for key in bucket_keys
    ]

    status_counts: dict[str, int] = {}
    for order in period_orders:
        status = order.get("status") or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
    total_status = sum(status_counts.values()) or 1
    status_rows = [
        {
            "code": code,
            "count": count,
            "percent": round(100 * count / total_status, 1),
        }
        for code, count in sorted(status_counts.items(), key=lambda x: -x[1])
    ]

    product_counts: dict[str, int] = {}
    for order in period_orders:
        name = (order.get("product_type") or order.get("category") or "").strip() or "其他"
        product_counts[name] = product_counts.get(name, 0) + 1
    top_products = [
        {"name": name, "orders": count}
        for name, count in sorted(product_counts.items(), key=lambda x: -x[1])[:6]
    ]

    series_stats: dict[str, dict] = {}
    for order in period_orders:
        name = (order.get("series") or "").strip() or "未分類"
        if name not in series_stats:
            series_stats[name] = {"orders": 0, "revenue": 0.0}
        series_stats[name]["orders"] += 1
        if order.get("status") in COMPLETE_STATUSES:
            series_stats[name]["revenue"] += float(order.get("total_price") or 0)
    top_series = [
        {"name": name, "orders": vals["orders"], "revenue": vals["revenue"]}
        for name, vals in sorted(series_stats.items(), key=lambda x: -x[1]["orders"])[:6]
    ]

    recent_orders = sorted(orders, key=lambda o: o.get("created_at") or datetime.min, reverse=True)[:10]

    return {
        "granularity": gran,
        "period": cfg["period"],
        "start": cfg["start"],
        "end": cfg["end"],
        "periodLabel": cfg["periodLabel"],
        "monthOptions": cfg["monthOptions"],
        "weekOptions": cfg["weekOptions"],
        "periodRevenue": period_revenue,
        "periodOrderCount": period_order_count,
        "totalRevenue": period_revenue,
        "averageSale": round(average_sale, 2),
        "monthlyTrend": monthly_trend,
        "statusRows": status_rows,
        "topProducts": top_products,
        "topSeries": top_series,
        "totalOrders": period_order_count,
        "recentOrders": recent_orders,
    }


def _csv_safe(value) -> str:
    """Neutralize spreadsheet formula injection. A cell beginning with = + - @
    (or tab/CR) is treated as a formula by Excel/Sheets; customer_name and the
    product summary are attacker-controlled at checkout, so prefix a single
    quote to force text interpretation. See OWASP "CSV Injection"."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def build_dashboard_csv(orders: list[dict], cfg: dict) -> tuple[str, str]:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["訂單編號", "日期", "客戶", "商品", "狀態", "含稅總計"])

    for order in sorted(orders, key=lambda o: o.get("created_at") or datetime.min):
        if not _order_in_period(order, cfg):
            continue
        created_at = order.get("created_at")
        if created_at:
            local = created_at + timedelta(hours=8) if created_at.tzinfo else created_at
            date_str = local.strftime("%Y-%m-%d %H:%M")
        else:
            date_str = ""
        product = (order.get("product_type") or order.get("category") or "").strip() or "-"
        status = STATUS_LABELS_ZH.get(order.get("status") or "", order.get("status") or "")
        writer.writerow([
            _csv_safe(order.get("order_number") or ""),
            date_str,
            _csv_safe(order.get("customer_name") or ""),
            _csv_safe(product),
            _csv_safe(status),
            round(float(order.get("total_price") or 0)),
        ])

    slug = cfg["period"] or f"{cfg['start']}_{cfg['end']}" or "all"
    return "\ufeff" + output.getvalue(), slug
