from datetime import date

from app import weekly_report as wr


def test_week_bounds_uses_last_full_monday_week():
    # Monday 2026-11-02 09:00 -> report covers Mon 10-26 .. Sun 11-01
    assert wr.week_bounds(date(2026, 11, 2)) == (
        date(2026, 10, 19), date(2026, 10, 26), date(2026, 11, 2))
    # Mid-week gives the same completed week
    assert wr.week_bounds(date(2026, 11, 5))[1:] == (date(2026, 10, 26), date(2026, 11, 2))


def test_payload_handles_missing_metrics_and_no_personal_data():
    cur = {"visits": {"views": 120, "uniques": 40}, "orders": {"count": 3, "revenue": 45000.0},
           "accounts": 5, "contacts": None, "quotes": 0, "bookings": 2, "coupons": 1,
           "lockouts": 0, "top_pages": [("/", 80)]}
    prev = {"visits": {"views": 100, "uniques": 40}, "orders": {"count": 0, "revenue": 0.0},
            "accounts": 5}
    p = wr.build_payload(cur, prev, date(2026, 10, 26), date(2026, 11, 2))
    text = str(p)
    assert "n/a" in text            # failed metric degrades, no crash
    assert "+20% vs last wk" in text
    assert "2026-10-26 to 2026-11-01" in text


def test_due_window_is_monday_9am_taipei_with_catch_up():
    from datetime import datetime
    tz = wr.TAIPEI
    mon = date(2026, 11, 2)
    assert wr.due_week_end(datetime(2026, 11, 2, 8, 59, tzinfo=tz)) is None
    assert wr.due_week_end(datetime(2026, 11, 2, 9, 0, tzinfo=tz)) == mon
    assert wr.due_week_end(datetime(2026, 11, 2, 20, 59, tzinfo=tz)) == mon   # catch-up
    assert wr.due_week_end(datetime(2026, 11, 2, 21, 0, tzinfo=tz)) is None
    assert wr.due_week_end(datetime(2026, 11, 3, 10, 0, tzinfo=tz)) is None   # Tuesday
    # 01:00 UTC Monday == 09:00 Taipei
    from datetime import timezone
    assert wr.due_week_end(datetime(2026, 11, 2, 1, 0, tzinfo=timezone.utc)) == mon
