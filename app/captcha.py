"""Google reCAPTCHA v2 siteverify helpers for registration."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from fastapi import Request

log = logging.getLogger(__name__)

SITEVERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
RECAPTCHA_ERROR = "請完成驗證"
RECAPTCHA_CONFIG_ERROR = "註冊驗證尚未設定，請稍後再試或聯絡客服。"


def recaptcha_site_key() -> str:
    return os.environ.get("RECAPTCHA_SITE_KEY", "").strip()


def recaptcha_secret_key() -> str:
    return os.environ.get("RECAPTCHA_SECRET_KEY", "").strip()


def verify_recaptcha(token: str | None, remote_ip: str | None = None) -> bool:
    """POST token to Google siteverify. Fail closed if secret or token missing."""
    secret = recaptcha_secret_key()
    if not secret:
        log.error("RECAPTCHA_SECRET_KEY is not set — rejecting verification")
        return False
    token = (token or "").strip()
    if not token:
        return False
    data: dict[str, str] = {"secret": secret, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(SITEVERIFY_URL, data=data)
            resp.raise_for_status()
            payload = resp.json()
    except (httpx.HTTPError, ValueError, TypeError):
        log.exception("reCAPTCHA siteverify request failed")
        return False
    return bool(payload.get("success"))


def recaptcha_error_or_none(request: "Request", token: str | None) -> str | None:
    """Return Chinese error if token missing/invalid; None if ok."""
    if not recaptcha_secret_key():
        return RECAPTCHA_CONFIG_ERROR
    remote_ip = request.client.host if request.client else None
    if verify_recaptcha(token, remote_ip):
        return None
    return RECAPTCHA_ERROR
