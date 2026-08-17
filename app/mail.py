"""Transactional email via Resend API. Missing API key → silent no-op.

Password reset is this shop mailer (token link), not Supabase Auth.
Set RESEND_API_KEY on the host — never commit the key.
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import os
import urllib.error
import urllib.request

log = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "nonreply@imprintdiamond.com"
PASSWORD_RESET_SUBJECT = "重設銘印鑽石帳戶密碼"


def _resend_key() -> str:
    return (os.environ.get("RESEND_API_KEY") or "").strip()


def _from_address() -> str:
    return (
        os.environ.get("RESET_EMAIL_FROM") or os.environ.get("EMAIL_FROM") or DEFAULT_FROM
    ).strip()


def _contact_notify_to() -> str:
    return (os.environ.get("CONTACT_NOTIFY_TO") or "").strip()


def send_email(*, to: str, subject: str, text: str, html: str | None = None) -> bool:
    """Send a plain-text email (optional HTML). Returns False if skipped or failed."""
    api_key = _resend_key()
    from_addr = _from_address()
    to_addr = (to or "").strip()
    if not api_key or not from_addr or not to_addr:
        log.info("mail: skip send (missing RESEND_API_KEY / from / to)")
        return False

    body: dict[str, object] = {
        "from": from_addr,
        "to": [to_addr],
        "subject": subject,
        "text": text,
    }
    if html:
        body["html"] = html
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        _RESEND_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "imprint-website/1.0",
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


def send_password_reset_email(*, to: str, reset_url: str) -> bool:
    """Shop-owned reset mail. Token link only — no Supabase Auth templates."""
    url = (reset_url or "").strip()
    text = (
        "您好，\n\n我們收到您重設銘印鑽石帳戶密碼的請求。"
        "請於 1 小時內點擊以下連結設定新密碼：\n\n"
        f"{url}\n\n若您沒有提出此請求，請忽略這封信，您的密碼不會變更。\n\n"
        "銘印鑽石 IMPRINT DIAMOND"
    )
    safe_url = html_lib.escape(url, quote=True)
    html = (
        "<p>您好，</p>"
        "<p>我們收到您重設銘印鑽石帳戶密碼的請求。請於 1 小時內點擊以下連結設定新密碼：</p>"
        f'<p><a href="{safe_url}" referrerpolicy="no-referrer" rel="noreferrer">{safe_url}</a></p>'
        "<p>若您沒有提出此請求，請忽略這封信，您的密碼不會變更。</p>"
        "<p>銘印鑽石 IMPRINT DIAMOND</p>"
    )
    return send_email(to=to, subject=PASSWORD_RESET_SUBJECT, text=text, html=html)
