"""Member history status progress — same codes admin sets."""

from app.controllers.admin_controller import ORDER_STATUSES
from app.orders import (
    ORDER_STATUS_FLOW,
    ORDER_STATUS_LABELS_ZH,
    enrich_member_order,
    order_status_steps,
)


def test_flow_matches_admin_statuses_minus_cancelled():
    assert set(ORDER_STATUS_FLOW) == ORDER_STATUSES - {"cancelled"}
    assert "cancelled" in ORDER_STATUSES
    assert "cancelled" in ORDER_STATUS_LABELS_ZH
    assert list(ORDER_STATUS_FLOW) == [
        "received",
        "deposit_confirmed",
        "dna_lab",
        "in_production",
        "quality_check",
        "shipped",
        "completed",
    ]


def test_progress_highlights_current_and_checks_prior():
    steps = order_status_steps("in_production")
    assert [s["code"] for s in steps] == list(ORDER_STATUS_FLOW)
    assert steps[0]["code"] == "received"
    assert steps[1]["code"] == "deposit_confirmed"
    assert steps[2]["code"] == "dna_lab"
    assert steps[0]["state"] == "complete"
    assert steps[1]["state"] == "complete"
    assert steps[2]["state"] == "complete"
    assert steps[3]["code"] == "in_production"
    assert steps[3]["state"] == "current"
    assert steps[3]["label"] == "製作中"
    assert steps[4]["state"] == "incomplete"


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
