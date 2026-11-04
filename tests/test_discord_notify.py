import re

from app import discord_notify as dn

BOOKING_MSG = "想看求婚鑽戒\n\n【希望預約時段】\n1. 2026-11-08 14:00\n2. 2026-11-09 10:30"


def _env(monkeypatch, booking="", report=""):
    monkeypatch.setenv("DISCORD_BOOKING_WEBHOOK_URL", booking)
    monkeypatch.setenv("DISCORD_REPORT_WEBHOOK_URL", report)


def test_dates_are_not_mistaken_for_phones():
    assert dn.safe_text("2026-11-08 14:00", 60) == "2026-11-08 14:00"
    assert dn.safe_text("call +886 912 345 678", 60) == "call •••5678"


def test_masks_name_and_phone():
    assert dn.mask_name("王小明") == "王○明"
    assert dn.mask_name("王明") == "王○"
    assert dn.mask_name("") == "（未填）"
    assert dn.mask_phone("0912-345-678") == "******5678"
    assert dn.mask_phone("") == "（未填）"


def test_booking_payload_has_slots_and_no_full_contact_details():
    p = dn.build_payload(name="王小明", phone="0912345678", message=BOOKING_MSG,
                         admin_url="https://www.imprint-diamond.com/admin/leads")
    embed = p["embeds"][0]
    text = str(p)
    assert embed["title"] == "🗓️ 新預約諮詢"
    assert embed["fields"][0]["value"] == "2026-11-08 14:00\n2026-11-09 10:30"
    assert "0912345678" not in text and "王小明" not in text
    assert "想看求婚鑽戒" in text
    assert p["allowed_mentions"] == {"parse": []}


def test_plain_message_without_slots_and_long_text_preview():
    p = dn.build_payload(name="Amy", phone="12", message="x" * 300, admin_url=None)
    embed = p["embeds"][0]
    assert embed["title"] == "✉️ 新留言"
    assert "url" not in embed
    need = next(f for f in embed["fields"] if f["name"] == "需求")["value"]
    assert len(need) == dn.PREVIEW_CHARS + 1


def test_webhook_falls_back_to_weekly_report_url(monkeypatch):
    _env(monkeypatch, report="https://discord.test/report")
    assert dn.webhook_url() == "https://discord.test/report"
    _env(monkeypatch, booking="https://discord.test/booking", report="https://discord.test/report")
    assert dn.webhook_url() == "https://discord.test/booking"


def test_disabled_without_webhook(monkeypatch):
    _env(monkeypatch)
    called = []
    monkeypatch.setattr(dn.requests, "post", lambda *a, **k: called.append(a))
    assert dn.notify_contact(name="a", phone="1", message="m") is False
    assert called == []


def test_send_failure_never_raises(monkeypatch):
    _env(monkeypatch, report="https://discord.test/report")

    def boom(*a, **k):
        raise dn.requests.ConnectionError("discord down")

    monkeypatch.setattr(dn.requests, "post", boom)
    assert dn.notify_contact(name="王小明", phone="0912345678", message=BOOKING_MSG,
                             background=False) is True


def test_posts_to_webhook(monkeypatch):
    _env(monkeypatch, report="https://discord.test/report")
    sent = {}

    class Ok:
        status_code = 204

    def fake_post(url, json=None, timeout=None):
        sent.update(url=url, json=json)
        return Ok()

    monkeypatch.setattr(dn.requests, "post", fake_post)
    dn.notify_contact(name="王小明", phone="0912345678", message=BOOKING_MSG,
                      background=False)
    assert sent["url"] == "https://discord.test/report"
    assert sent["json"]["embeds"][0]["title"] == "🗓️ 新預約諮詢"

# ── form-level integration tests ──────────────────────────────────────────

import time
from contextlib import contextmanager
from unittest.mock import MagicMock
import pytest


@pytest.fixture
def contact_client(monkeypatch):
    """FastAPI TestClient with DB, captcha, and rate limit mocked."""
    from fastapi.testclient import TestClient
    from app import create_app
    from app.controllers import htmx_member as hm

    @contextmanager
    def fake_conn():
        conn = MagicMock()
        yield conn

    monkeypatch.setattr(hm, "get_connection", fake_conn)
    monkeypatch.setattr(hm, "load_dynamic_keywords", lambda cur: [])
    monkeypatch.setattr(hm, "enforce_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr(hm, "recaptcha_error_or_none", lambda *a, **k: None)
    monkeypatch.setattr("app.consult_bookings.check_requested_slots", lambda cur, pairs: None)
    monkeypatch.setattr("app.mail.notify_contact_message", lambda **k: None)

    return TestClient(create_app())


def test_valid_contact_form_calls_notify_contact_once(contact_client, monkeypatch):
    notify_calls = []
    monkeypatch.setattr(dn, "notify_contact", lambda **k: notify_calls.append(k) or True)

    data = {
        "name": "王小明",
        "phone": "0912345678",
        "email": "test@example.com",
        "message": "想看求婚鑽戒",
        "hp_trap_x": "",
        "hp_ts": str(time.time() * 1000 - 30000),
        "preferred_date": "2026-11-08",
        "preferred_slot": "14:00",
    }
    resp = contact_client.post("/htmx/contact", data=data)
    assert resp.status_code == 200
    assert "已收到您的留言" in resp.text
    assert len(notify_calls) == 1
    call = notify_calls[0]
    assert call["name"] == "王小明"
    assert call["phone"] == "0912345678"
    assert call["email"] == "test@example.com"
    assert "【希望預約時段】" in call["message"]
    assert "2026-11-08 14:00" in call["message"]


def test_spam_honeypot_submission_does_not_call_notify(contact_client, monkeypatch):
    notify_calls = []
    monkeypatch.setattr(dn, "notify_contact", lambda **k: notify_calls.append(k) or True)

    data = {
        "name": "Spam Bot",
        "phone": "0912345678",
        "email": "bot@example.com",
        "message": "Visit our casino website",
        "hp_trap_x": "http://spam.test",
        "hp_ts": str(time.time() * 1000 - 30000),
        "preferred_date": "2026-11-08",
        "preferred_slot": "14:00",
    }
    resp = contact_client.post("/htmx/contact", data=data)
    assert resp.status_code == 200
    assert len(notify_calls) == 0


def test_contact_form_success_even_when_discord_post_raises(contact_client, monkeypatch):
    _env(monkeypatch, booking="https://discord.test/booking")

    post_called = []

    def boom(*a, **k):
        post_called.append(True)
        raise dn.requests.ConnectionError("discord unreachable")

    monkeypatch.setattr(dn.requests, "post", boom)

    data = {
        "name": "王小明",
        "phone": "0912345678",
        "email": "test@example.com",
        "message": "想看求婚鑽戒",
        "hp_trap_x": "",
        "hp_ts": str(time.time() * 1000 - 30000),
        "preferred_date": "2026-11-08",
        "preferred_slot": "14:00",
    }
    resp = contact_client.post("/htmx/contact", data=data)
    time.sleep(0.1)
    assert resp.status_code == 200
    assert "已收到您的留言" in resp.text
    assert len(post_called) == 1



# ── security hardening ───────────────────────────────────────────────────

def test_free_text_is_masked_escaped_and_capped():
    nasty = "請打 0912-345-678 或寄 me@x.com [後台登入](https://evil.example) @everyone " + "字" * 2000
    msg = f"{nasty}\n\n【希望預約時段】\n1. {nasty}"
    p = dn.build_payload(name="王小明", phone="0912345678", message=msg,
                         admin_url=None)
    for f in p["embeds"][0]["fields"]:
        assert len(f["value"]) <= 1024
        assert "0912-345-678" not in f["value"] and "me@x.com" not in f["value"]
        assert "](" not in f["value"].replace("\](", "")
        assert not re.search(r"(?<!\\)@everyone", f["value"])


def test_failure_logs_never_contain_webhook_token(monkeypatch, caplog):
    secret = "https://discord.com/api/webhooks/123/SECRETTOKEN"
    _env(monkeypatch, booking=secret)

    def boom(url, **k):
        raise dn.requests.ConnectionError(f"Max retries exceeded with url: {url}")

    monkeypatch.setattr(dn.requests, "post", boom)
    dn.notify_contact(name="a", phone="1", message="m", background=False)

    class Bad:
        status_code = 404

    monkeypatch.setattr(dn.requests, "post", lambda *a, **k: Bad())
    dn.notify_contact(name="a", phone="1", message="m", background=False)
    assert "SECRETTOKEN" not in caplog.text
    assert "HTTP 404" in caplog.text


def test_global_cap_stops_flood(monkeypatch):
    _env(monkeypatch, report="https://discord.test/report")
    monkeypatch.setattr(dn, "_sent_at", [])
    monkeypatch.setattr(dn, "_post", lambda *a: None)
    results = [dn.notify_contact(name="a", phone="1", message="m",
                                 background=False) for _ in range(dn.MAX_ALERTS_PER_WINDOW + 3)]
    assert results.count(True) == dn.MAX_ALERTS_PER_WINDOW


# ── admin link button ────────────────────────────────────────────────────

ADMIN = "https://www.imprint-diamond.com/admin/leads"


class _Resp:
    def __init__(self, status):
        self.status_code = status


def test_payload_has_admin_link_button():
    p = dn.build_payload(name="王小明", phone="0912345678", message=BOOKING_MSG, admin_url=ADMIN)
    button = p["components"][0]["components"][0]
    assert button == {"type": 2, "style": 5, "label": "開啟後台諮詢名單", "url": ADMIN}
    assert "footer" not in p["embeds"][0]
    assert "components" not in dn.build_payload(name="a", phone="1", message="m", admin_url=None)


def test_button_sent_with_components_flag(monkeypatch):
    urls = []
    monkeypatch.setattr(dn.requests, "post", lambda url, **k: urls.append(url) or _Resp(204))
    p = dn.build_payload(name="a", phone="1", message="m", admin_url=ADMIN)
    dn._post("https://discord.test/hook?thread_id=9", p)
    assert urls == ["https://discord.test/hook?thread_id=9&with_components=true"]


def test_rejected_button_resends_without_it(monkeypatch):
    calls = []

    def fake_post(url, json=None, timeout=None):
        calls.append((url, "components" in json))
        return _Resp(400 if "components" in json else 204)

    monkeypatch.setattr(dn.requests, "post", fake_post)
    dn._post("https://discord.test/hook",
             dn.build_payload(name="a", phone="1", message="m", admin_url=ADMIN))
    assert calls == [("https://discord.test/hook?with_components=true", True),
                     ("https://discord.test/hook", False)]


def test_email_shown_in_full_and_phone_keeps_last_four():
    p = dn.build_payload(name="王小明", phone="0912345678", message="hi",
                         email="amy_lin@example.com", admin_url=None)
    fields = {f["name"]: f["value"] for f in p["embeds"][0]["fields"]}
    assert fields["Email"] == r"amy\_lin@example.com"
    assert fields["電話"] == "******5678"
    assert dn.build_payload(name="a", phone="1", message="m",
                            admin_url=None)["embeds"][0]["fields"][2]["value"] == "（未填）"
