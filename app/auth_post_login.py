"""Shared post-login routing for password / Google auth."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request, Response

from app.auth import set_session_cookie, sign_session


@dataclass(frozen=True)
class PostLoginDecision:
    kind: str  # session
    next_url: str


def safe_next_url(raw: str | None, default: str = "/account.html") -> str:
    next_url = (raw or default).strip() or default
    if not next_url.startswith("/") or next_url.startswith("//"):
        return default
    return next_url


def decide_post_login(*, next_url: str, user_id: str | None = None) -> PostLoginDecision:
    """Route to the intended next page. Incomplete profile uses a soft prompt, not a hard gate."""
    _ = user_id  # call-site compatibility; prompt rendered on /htmx/account
    return PostLoginDecision("session", safe_next_url(next_url))


def apply_post_login_cookies(
    response: Response,
    request: Request,
    user: dict,
    decision: PostLoginDecision,
    *,
    remember: bool = True,
) -> None:
    user_id = str(user["id"])
    token = sign_session(user_id, int(user.get("token_version") or 0))
    set_session_cookie(response, token, request, remember=remember)


def post_login_json(decision: PostLoginDecision, user: dict) -> dict:
    return {
        "ok": True,
        "user": {"id": str(user["id"]), "email": user["email"]},
        "next": decision.next_url,
    }
