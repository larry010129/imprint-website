"""Shared post-login routing for password / Google auth."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from fastapi import Request, Response

from app.auth import (
    clear_session_cookie,
    is_admin,
    set_pre2fa_cookie,
    set_session_cookie,
    sign_pre2fa,
    sign_session,
)


@dataclass(frozen=True)
class PostLoginDecision:
    kind: str  # session | pre2fa
    next_url: str


# Legacy admin shell next= values → canonical CMS paths.
_ADMIN_NEXT_ALIASES: dict[str, str] = {
    "/admin.html": "/admin",
    "/admin1.html": "/admin",
    "/admin1-settings.html": "/admin/settings",
    "/admin1-plugins.html": "/admin/plugins",
    "/admin1-release-notes.html": "/admin/release-notes",
    "/admin1-login.html": "/admin",
}


def safe_next_url(raw: str | None, default: str = "/account") -> str:
    next_url = (raw or default).strip() or default
    if not next_url.startswith("/") or next_url.startswith("//"):
        return default
    path, sep, query = next_url.partition("?")
    # Canonicalize admin shells so post-login lands on /admin (not *.html).
    admin_canonical = _ADMIN_NEXT_ALIASES.get(path)
    if admin_canonical is not None:
        return f"{admin_canonical}?{query}" if sep else admin_canonical
    # Normalize legacy *.html bookmarks (non-admin).
    if path.endswith(".html") and path.count("/") <= 2:
        path = path[: -len(".html")]
        next_url = f"{path}?{query}" if sep else path
    return next_url or default


def decide_post_login(
    *,
    next_url: str,
    user_id: str | None = None,
    totp_enabled: bool = False,
    remember: bool = True,
) -> PostLoginDecision:
    """Route after password/Google check.

    Staff with TOTP enrolled get a short-lived pre2fa cookie only — full session
    is issued after /verify-2fa. Members and staff without TOTP get a normal
    session (admin APIs do not require TOTP enrollment).
    """
    safe = safe_next_url(next_url)
    if user_id and totp_enabled and is_admin(user_id):
        q = urlencode({"next": safe, "remember": "1" if remember else "0"})
        return PostLoginDecision("pre2fa", f"/login-2fa?{q}")
    return PostLoginDecision("session", safe)


def apply_post_login_cookies(
    response: Response,
    request: Request,
    user: dict,
    decision: PostLoginDecision,
    *,
    remember: bool = True,
) -> None:
    user_id = str(user["id"])
    if decision.kind == "pre2fa":
        clear_session_cookie(response, request)
        set_pre2fa_cookie(response, sign_pre2fa(user_id), request)
        return

    admin = is_admin(user_id)
    token = sign_session(
        user_id,
        int(user.get("token_version") or 0),
        is_admin=admin,
        remember=remember,
    )
    set_session_cookie(response, token, request, remember=remember, is_admin=admin)


def post_login_json(decision: PostLoginDecision, user: dict) -> dict:
    payload = {
        "ok": True,
        "user": {"id": str(user["id"]), "email": user["email"]},
        "next": decision.next_url,
    }
    if decision.kind == "pre2fa":
        payload["requires2fa"] = True
    return payload
