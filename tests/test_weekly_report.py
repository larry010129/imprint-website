from datetime import date

from scripts import weekly_report as wr


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
