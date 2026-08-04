"""Member history status progress — same codes admin sets."""

from datetime import datetime, timezone

from app.controllers.admin_controller import ORDER_STATUSES
from app.orders import (
    ORDER_STATUS_FLOW,
    ORDER_STATUS_LABELS_ZH,
    enrich_member_order,
    format_status_date,
    merge_status_timestamps,
    order_status_steps,
)


def test_flow_matches_admin_statuses_minus_cancelled():
    assert set(ORDER_STATUS_FLOW) == ORDER_STATUSES - {"cancelled"}
    assert "cancelled" in ORDER_STATUSES
    assert "cancelled" in ORDER_STATUS_LABELS_ZH
    assert list(ORDER_STATUS_FLOW) == [
        "received",
        "order_confirming",
        "deposit_confirmed",
        "dna_lab",
        "in_production",
        "quality_check",
        "shipped",
        "completed",
    ]
    assert ORDER_STATUS_LABELS_ZH["order_confirming"] == "訂單已確認"


def test_progress_highlights_current_and_checks_prior():
    steps = order_status_steps("in_production")
    assert [s["code"] for s in steps] == list(ORDER_STATUS_FLOW)
    assert steps[0]["code"] == "received"
    assert steps[1]["code"] == "order_confirming"
    assert steps[2]["code"] == "deposit_confirmed"
    assert steps[3]["code"] == "dna_lab"
    assert steps[0]["state"] == "complete"
    assert steps[1]["state"] == "complete"
    assert steps[2]["state"] == "complete"
    assert steps[3]["state"] == "complete"
    assert steps[4]["code"] == "in_production"
    assert steps[4]["state"] == "current"
    assert steps[4]["label"] == "製作中"
    assert steps[5]["state"] == "incomplete"


def test_order_confirming_is_current_after_received():
    steps = order_status_steps("order_confirming")
    assert steps[0]["state"] == "complete"
    assert steps[1]["code"] == "order_confirming"
    assert steps[1]["state"] == "current"
    assert steps[1]["label"] == "訂單已確認"
    assert steps[2]["code"] == "deposit_confirmed"
    assert steps[2]["state"] == "incomplete"


def test_cancelled_has_no_pipeline_steps():
    steps = order_status_steps("cancelled")
    assert steps == []
    order = enrich_member_order(
        {
            "status": "cancelled",
            "summary_zh": "測試項墜",
            "config_json": {"category": "pendant", "gold": "14k", "color": "white"},
            "fulfillment_method": "pickup",
        }
    )
    assert order["status_cancelled"] is True
    assert order["status_label"] == "已取消"
    assert order["status_steps"] == []
    assert "14K白金" in order["details_zh"]


def test_merge_stamps_received_to_order_confirming():
    when = datetime(2026, 6, 25, 2, 0, tzinfo=timezone.utc)
    existing = {"received": "2026-06-20T02:00:00+00:00"}
    merged = merge_status_timestamps(existing, "received", "order_confirming", when)
    assert merged["received"] == existing["received"]
    assert merged["order_confirming"] == when.isoformat()
    assert "deposit_confirmed" not in merged


def test_merge_skip_ahead_fills_intermediate_once():
    when = datetime(2026, 9, 14, 7, 30, tzinfo=timezone.utc)
    existing = {"received": "2026-06-25T02:00:00+00:00"}
    merged = merge_status_timestamps(existing, "received", "shipped", when)
    stamp = when.isoformat()
    assert merged["received"] == existing["received"]
    for key in (
        "order_confirming",
        "deposit_confirmed",
        "dna_lab",
        "in_production",
        "quality_check",
        "shipped",
    ):
        assert merged[key] == stamp
    assert "completed" not in merged


def test_merge_does_not_overwrite_existing_stamp():
    when = datetime(2026, 9, 14, 7, 30, tzinfo=timezone.utc)
    existing = {
        "received": "2026-06-25T02:00:00+00:00",
        "order_confirming": "2026-07-01T04:00:00+00:00",
    }
    merged = merge_status_timestamps(existing, "received", "deposit_confirmed", when)
    assert merged["order_confirming"] == existing["order_confirming"]
    assert merged["deposit_confirmed"] == when.isoformat()


def test_format_status_date_taipei_unpadded():
    # 2026-06-25T02:00:00Z = 2026-06-25 10:00 Asia/Taipei
    assert format_status_date("2026-06-25T02:00:00+00:00") == "6/25"
    assert format_status_date("2026-12-03T16:00:00+00:00") == "12/4"
    assert format_status_date(None) == ""
    assert format_status_date("") == ""


def test_order_status_steps_exposes_date_md():
    stamps = {
        "received": "2026-06-25T02:00:00+00:00",
        "order_confirming": "2026-09-14T07:30:00+00:00",
    }
    steps = order_status_steps("order_confirming", stamps)
    assert steps[0]["date"] == "6/25"
    assert steps[1]["date"] == "9/14"
    assert steps[1]["state"] == "current"
    for step in steps[2:]:
        assert step["state"] == "incomplete"
        assert step["date"] == ""


def test_enrich_member_order_passes_timestamps_to_steps():
    order = enrich_member_order(
        {
            "status": "received",
            "status_timestamps": {"received": "2026-06-25T02:00:00+00:00"},
            "summary_zh": "測試",
            "config_json": {},
            "fulfillment_method": "pickup",
        }
    )
    assert order["status_steps"][0]["date"] == "6/25"
    assert order["status_steps"][1]["date"] == ""
