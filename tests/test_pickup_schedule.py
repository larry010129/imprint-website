"""Ready-for-pickup filter + preferred pickup slot validation."""



from datetime import datetime, time



import pytest

from zoneinfo import ZoneInfo



from app.orders import (

    PICKUP_SLOT_STARTS,

    READY_FOR_PICKUP_STATUS,

    enrich_member_order,

    format_pickup_preferred_display,

    is_ready_for_pickup,

    parse_pickup_preferred_at,

    pickup_preferred_date_value,

    pickup_preferred_input_value,

    pickup_preferred_slot_value,

    pickup_slot_label,

    pickup_slot_options,

)



_TAIPEI = ZoneInfo("Asia/Taipei")



_EXPECTED_SLOT_STARTS = (

    time(9, 0),

    time(10, 0),

    time(11, 0),

    time(13, 0),

    time(14, 0),

    time(15, 0),

    time(16, 0),

    time(17, 0),

    time(18, 0),

    time(19, 0),

)





def test_ready_for_pickup_requires_pickup_and_shipped():

    assert READY_FOR_PICKUP_STATUS == "shipped"

    assert is_ready_for_pickup({"fulfillment_method": "pickup", "status": "shipped"})

    assert not is_ready_for_pickup({"fulfillment_method": "delivery", "status": "shipped"})

    assert not is_ready_for_pickup({"fulfillment_method": "pickup", "status": "quality_check"})

    assert not is_ready_for_pickup({"fulfillment_method": "pickup", "status": "completed"})

    assert not is_ready_for_pickup(None)





def test_pickup_slot_list_covers_store_hours():

    starts = list(PICKUP_SLOT_STARTS)

    assert starts == list(_EXPECTED_SLOT_STARTS)

    assert starts[0] == time(9, 0)

    assert starts[-1] == time(19, 0)

    assert time(8, 30) not in starts

    assert time(12, 0) not in starts

    assert time(19, 30) not in starts

    labels = [opt["label"] for opt in pickup_slot_options()]

    assert labels == [

        "09:00–10:00",

        "10:00–11:00",

        "11:00–12:00",

        "13:00–14:00",

        "14:00–15:00",

        "15:00–16:00",

        "16:00–17:00",

        "17:00–18:00",

        "18:00–19:00",

        "19:00–20:00",

    ]

    assert pickup_slot_label(time(14, 0)) == "14:00–15:00"





def test_enrich_sets_ready_and_preferred_display():

    when = datetime(2026, 8, 10, 14, 0, tzinfo=_TAIPEI)

    order = enrich_member_order(

        {

            "status": "shipped",

            "fulfillment_method": "pickup",

            "pickup_preferred_at": when,

            "summary_zh": "測試",

            "config_json": {},

        }

    )

    assert order["ready_for_pickup"] is True

    assert order["status_label"] == "可取貨"

    assert order["pickup_preferred_display"] == "2026/08/10 14:00–15:00"

    assert order["pickup_preferred_input"] == "2026-08-10T14:00"

    assert order["pickup_preferred_date"] == "2026-08-10"

    assert order["pickup_preferred_slot"] == "14:00"

    assert len(order["pickup_slot_options"]) == len(PICKUP_SLOT_STARTS)

    assert order["pickup_date_min"]

    assert order["pickup_date_max"]





def test_enrich_delivery_not_ready():

    order = enrich_member_order(

        {

            "status": "shipped",

            "fulfillment_method": "delivery",

            "summary_zh": "測試",

            "config_json": {},

        }

    )

    assert order["ready_for_pickup"] is False

    assert order["status_label"] == "已出貨"

    assert order["pickup_preferred_display"] == ""





def test_parse_pickup_preferred_at_valid_slot():

    now = datetime(2026, 8, 8, 10, 0, tzinfo=_TAIPEI)

    dt = parse_pickup_preferred_at("2026-08-09T15:00", now=now)

    assert dt.tzinfo == _TAIPEI

    assert dt.year == 2026 and dt.month == 8 and dt.day == 9

    assert dt.hour == 15 and dt.minute == 0





def test_parse_accepts_closing_slot():

    now = datetime(2026, 8, 8, 10, 0, tzinfo=_TAIPEI)

    dt = parse_pickup_preferred_at("2026-08-09T19:00", now=now)

    assert dt.hour == 19 and dt.minute == 0





def test_parse_rejects_empty_past_and_non_slot():

    now = datetime(2026, 8, 8, 12, 0, tzinfo=_TAIPEI)

    with pytest.raises(ValueError, match="請選擇"):

        parse_pickup_preferred_at("", now=now)

    with pytest.raises(ValueError, match="不可早於"):

        parse_pickup_preferred_at("2026-08-07T10:00", now=now)

    with pytest.raises(ValueError, match="可預約時段"):

        parse_pickup_preferred_at("2026-08-09T15:45", now=now)

    with pytest.raises(ValueError, match="可預約時段"):

        parse_pickup_preferred_at("2026-08-09T19:30", now=now)

    with pytest.raises(ValueError, match="可預約時段"):

        parse_pickup_preferred_at("2026-08-09T12:00", now=now)

    with pytest.raises(ValueError, match="可預約時段"):

        parse_pickup_preferred_at("2026-08-09T08:30", now=now)





def test_parse_rejects_too_far_ahead():

    now = datetime(2026, 8, 8, 12, 0, tzinfo=_TAIPEI)

    with pytest.raises(ValueError, match="60"):

        parse_pickup_preferred_at("2026-12-01T10:00", now=now)





def test_format_helpers_empty():

    assert format_pickup_preferred_display(None) == ""

    assert pickup_preferred_input_value("") == ""

    assert pickup_preferred_date_value(None) == ""

    assert pickup_preferred_slot_value("") == ""




def test_pickup_schedule_template_renders_slot_options():
    """Select must list hourly slots even if order omitted pickup_slot_options."""
    from app.controllers.htmx_common import templates

    order = {
        "id": "ord-1",
        "ready_for_pickup": True,
        "pickup_preferred_date": "2026-08-17",
        "pickup_preferred_slot": "",
        "pickup_date_min": "2026-08-08",
        "pickup_date_max": "2026-10-07",
    }
    html = templates.env.get_template("partials/htmx/pickup_schedule.html").render(
        order=order,
        schedule_target="pickup-schedule-test",
    )
    assert 'data-pickup-slot-options=' in html
    assert 'value="09:00"' in html
    assert "09:00–10:00" in html
    assert 'value="12:00"' not in html
    assert 'value="19:00"' in html
    assert html.count("<option") == 1 + len(PICKUP_SLOT_STARTS)

def test_enrich_rejects_invalid_legacy_preferred_time():
    when = datetime(2026, 8, 10, 23, 40, tzinfo=_TAIPEI)
    order = enrich_member_order(
        {
            "status": "shipped",
            "fulfillment_method": "pickup",
            "pickup_preferred_at": when,
            "summary_zh": "測試",
            "config_json": {},
        }
    )
    assert order["status_label"] == "可取貨"
    assert order["pickup_preferred_invalid"] is True
    assert order["pickup_preferred_display"] == ""
    assert order["pickup_preferred_slot"] == ""
    assert order["pickup_preferred_date"] == "2026-08-10"
    assert "23:40" not in (order["pickup_preferred_display"] or "")


def test_format_pickup_preferred_display_hides_invalid_slot():
    assert format_pickup_preferred_display(datetime(2026, 8, 10, 23, 40, tzinfo=_TAIPEI)) == ""
    assert format_pickup_preferred_display(datetime(2026, 8, 10, 14, 0, tzinfo=_TAIPEI)) == "2026/08/10 14:00–15:00"


def test_pickup_schedule_template_invalid_time_and_options():
    from app.controllers.htmx_common import templates
    from app.orders import enrich_member_order, PICKUP_SLOT_STARTS

    order = enrich_member_order(
        {
            "id": "ord-1",
            "status": "shipped",
            "fulfillment_method": "pickup",
            "pickup_preferred_at": datetime(2026, 8, 10, 23, 40, tzinfo=_TAIPEI),
            "summary_zh": "測試",
            "config_json": {},
        }
    )
    html = templates.env.get_template("partials/htmx/pickup_schedule.html").render(
        order=order,
        schedule_target="pickup-schedule-test",
    )
    assert "23:40" not in html
    assert "history_pickup_preferred_invalid" in html or "無效" in html
    assert html.count('value="09:00"') >= 1
    assert html.count("<option") == 1 + len(PICKUP_SLOT_STARTS)
    assert "data-pickup-slot-catalog" in html
    assert 'value="14:00"' in html

