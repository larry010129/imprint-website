"""New contact form / 預約諮詢 -> Discord webhook (staff alert, masked contact details).

Sends to DISCORD_BOOKING_WEBHOOK_URL, falling back to the weekly report's
DISCORD_REPORT_WEBHOOK_URL so one webhook covers both. Unset = no-op.

Best-effort: posts from a small thread pool so the customer never waits on
Discord, and any failure is logged (without the URL, which holds the webhook
token), never raised into the form handler. Customer free text is masked
(emails, phone-like numbers), markdown-escaped and length-capped.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

log = logging.getLogger("discord_notify")

BOOKING_MARKER = "【希望預約時段】"
PREVIEW_CHARS = 100
SLOT_CHARS = 60
TIMEOUT_SECONDS = 10
MAX_ALERTS_PER_WINDOW = 20   # per worker process; protects the shared webhook
WINDOW_SECONDS = 600
COLOR_BOOKING = 0xC9A86A
COLOR_MESSAGE = 0x8A8F98

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Taiwan numbers (09xx / 0x / +886); dates like 2026-11-08 don't start with 0.
_PHONEISH = re.compile(r"(?<!\d)(?:\+?886[\s-]?|0)\d(?:[\s-]?\d){7,9}(?!\d)")
_MD = re.compile(r"([\\*_~`|>\[\]()#<@])")

_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="discord-notify")
_sent_at: list[float] = []
_sent_lock = threading.Lock()


def webhook_url() -> str:
    return (
        os.environ.get("DISCORD_BOOKING_WEBHOOK_URL", "").strip()
        or os.environ.get("DISCORD_REPORT_WEBHOOK_URL", "").strip()
    )


def mask_name(name: str) -> str:
    """王小明 -> 王○明, 王明 -> 王○, John Smith -> J○○○○○○○○h."""
    name = (name or "").strip()
    if len(name) <= 1:
        return name or "（未填）"
    if len(name) == 2:
        return name[0] + "○"
    return name[0] + "○" * (len(name) - 2) + name[-1]


def mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 4:
        return "（未填）" if not digits else "***"
    return "*" * (len(digits) - 3) + digits[-3:]


def split_message(message: str) -> tuple[str, list[str]]:
    """(customer text, requested slots) — undoes the 【希望預約時段】 block the form appends."""
    text, _, slots_block = (message or "").partition(BOOKING_MARKER)
    slots = [
        re.sub(r"^\d+\.\s*", "", line).strip()
        for line in slots_block.splitlines()
        if line.strip()
    ]
    return text.strip(), slots


def safe_text(text: str | None, limit: int) -> str:
    """Customer text -> Discord: hide emails/phones, escape markdown, cap length."""
    text = " ".join((text or "").split())
    text = _EMAIL.sub("（email）", text)
    text = _PHONEISH.sub(lambda m: "•••" + re.sub(r"\D", "", m.group())[-3:], text)
    if len(text) > limit:
        text = text[:limit] + "…"
    return _MD.sub(r"\\\1", text)


def build_payload(*, name: str, phone: str, message: str,
                  admin_url: str | None) -> dict:
    text, slots = split_message(message)
    fields = []
    if slots:
        fields.append({"name": "希望預約時段",
                       "value": "\n".join(safe_text(s, SLOT_CHARS) for s in slots[:3]),
                       "inline": False})
    fields += [
        {"name": "姓名", "value": safe_text(mask_name(name), 40), "inline": True},
        {"name": "電話", "value": mask_phone(phone), "inline": True},
        {"name": "需求", "value": safe_text(text, PREVIEW_CHARS) or "（無內容）", "inline": False},
    ]
    embed = {
        "title": "🗓️ 新預約諮詢" if slots else "✉️ 新留言",
        "color": COLOR_BOOKING if slots else COLOR_MESSAGE,
        "fields": fields,
    }
    # allowed_mentions: customer text must never ping @everyone / roles.
    payload = {"embeds": [embed], "allowed_mentions": {"parse": []}}
    if admin_url:
        embed["url"] = admin_url
        # Link button (style 5); plain webhooks may send it with ?with_components=true.
        payload["components"] = [{"type": 1, "components": [
            {"type": 2, "style": 5, "label": "開啟後台諮詢名單", "url": admin_url}]}]
    return payload


def _with_components(url: str) -> str:
    return url + ("&" if "?" in url else "?") + "with_components=true"


def _admin_url() -> str | None:
    try:
        from config.settings import settings

        base = (settings.public_base_url or "").rstrip("/")
        return f"{base}/admin/leads" if base.startswith("https://") else None
    except Exception:
        return None


def _post(url: str, payload: dict) -> None:
    # Never log str(exc) or use raise_for_status(): both include the webhook URL/token.
    try:
        if payload.get("components"):
            r = requests.post(_with_components(url), json=payload, timeout=TIMEOUT_SECONDS)
            if r.status_code != 400:
                return _log_status(r)
            # Button rejected: never lose the alert over it, resend without.
            log.warning("discord contact notify: button rejected, resending without")
            payload = {k: v for k, v in payload.items() if k != "components"}
        r = requests.post(url, json=payload, timeout=TIMEOUT_SECONDS)
    except Exception as exc:
        log.warning("discord contact notify failed: %s", type(exc).__name__)
        return
    _log_status(r)


def _log_status(r) -> None:
    if r.status_code >= 400:
        log.warning("discord contact notify failed: HTTP %s", r.status_code)


def _under_cap() -> bool:
    now = time.monotonic()
    with _sent_lock:
        _sent_at[:] = [t for t in _sent_at if now - t < WINDOW_SECONDS]
        if len(_sent_at) >= MAX_ALERTS_PER_WINDOW:
            return False
        _sent_at.append(now)
        return True


def notify_contact(*, name: str, phone: str, message: str,
                   background: bool = True) -> bool:
    """Queue a Discord alert for a saved contact form. Returns False when disabled."""
    url = webhook_url()
    if not url:
        return False
    if not _under_cap():
        log.warning("discord contact notify skipped: %s alerts in %ss",
                    MAX_ALERTS_PER_WINDOW, WINDOW_SECONDS)
        return False
    try:
        payload = build_payload(name=name, phone=phone, message=message, admin_url=_admin_url())
    except Exception:
        log.exception("discord contact payload failed")
        return False
    if background:
        _POOL.submit(_post, url, payload)
    else:
        _post(url, payload)
    return True
