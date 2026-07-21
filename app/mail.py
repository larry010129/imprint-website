"""Transactional email via Resend. Missing config → silent no-op."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

log = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"


def _resend_key() -> str:
    return (os.environ.get("RESEND_API_KEY") or "").strip()


def _from_address() -> str:
    return (os.environ.get("RESET_EMAIL_FROM") or os.environ.get("EMAIL_FROM") or "").strip()


def _contact_notify_to() -> str:
    return (os.environ.get("CONTACT_NOTIFY_TO") or "").strip()


def send_email(*, to: str, subject: str, text: str) -> bool:
    """Send a plain-text email. Returns False if skipped or failed."""
    api_key = _resend_key()
    from_addr = _from_address()
    to_addr = (to or "").strip()
    if not api_key or not from_addr or not to_addr:
        log.info("mail: skip send (missing RESEND_API_KEY / from / to)")
        return False

    payload = json.dumps(
        {"from": from_addr, "to": [to_addr], "subject": subject, "text": text},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        _RESEND_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            if 200 <= resp.status < 300:
                return True
            log.warning("mail: Resend status %s", resp.status)
            return False
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        log.warning("mail: Resend HTTP %s %s", exc.code, body)
        return False
    except Exception:
        log.exception("mail: Resend request failed")
        return False


def notify_contact_message(
    *,
    name: str,
    phone: str,
    email: str | None,
    message: str,
    source_page: str | None,
) -> bool:
    """Best-effort staff alert for a new contact form lead."""
    to_addr = _contact_notify_to()
    if not to_addr:
        log.info("mail: skip contact notify (CONTACT_NOTIFY_TO unset)")
        return False

    subject = f"新留言｜{name}｜{phone}"
    lines = [
        "銘印鑽石 — 官網線上留言",
        "",
        f"姓名：{name}",
        f"電話：{phone}",
        f"Email：{email or '（未填）'}",
        f"來源頁：{source_page or '（未填）'}",
        "",
        "需求：",
        message,
        "",
        "請至後台 leads 查看並回覆。",
    ]
    return send_email(to=to_addr, subject=subject, text="\n".join(lines))
