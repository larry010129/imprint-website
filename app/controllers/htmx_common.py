"""Shared helpers for HTMX partial controllers."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from app.auth import get_user_id, is_admin
from app.content import TAIWAN_CITIES
from app.database import get_connection
from app.profile_schema import fetch_profile
from config.settings import settings

templates = Jinja2Templates(directory=str(settings.templates_dir))

PREVIEW_COOKIE = "shop_preview"
SHIPPING_CITIES = tuple(c for c in TAIWAN_CITIES if c != "其他")


def format_twd(n: Any) -> str:
    if n is None:
        return "—"
    try:
        return "NT$" + f"{int(round(float(n))):,}"
    except (TypeError, ValueError):
        return "—"


templates.env.globals["format_twd"] = format_twd
templates.env.globals["taiwan_cities"] = SHIPPING_CITIES


def html(request: Request, name: str, ctx: dict[str, Any], status: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(
        request, f"partials/htmx/{name}", {"request": request, **ctx}, status_code=status
    )


def form_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def is_shop_preview(request: Request, form: Any | None = None) -> bool:
    """True when admin product preview (query, cookie, or form field)."""
    q = str(request.query_params.get("preview") or "").strip().lower()
    if q in {"1", "true", "yes"}:
        return True
    if request.cookies.get(PREVIEW_COOKIE) == "1":
        return True
    if form is not None and form_bool(form.get("preview")):
        return True
    return False


def hx_redirect(url: str) -> Response:
    resp = Response(status_code=200, content="")
    resp.headers["HX-Redirect"] = url
    return resp


def nav_user(request: Request) -> dict[str, Any] | None:
    user_id = get_user_id(request)
    if not user_id:
        return None
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select id, email from users where id = %s", (user_id,))
            user = cur.fetchone()
            if not user:
                return None
            profile = fetch_profile(cur, user_id) or {}
        name = (profile.get("full_name") or user["email"] or "").strip()
        return {
            "id": str(user["id"]),
            "email": user["email"],
            "name": name or user["email"],
            "is_admin": is_admin(user_id),
        }
    except Exception:
        return None


def cart_count(user_id: str | None) -> int:
    if not user_id:
        return 0
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select count(*) as n from cart_items where user_id = %s", (user_id,))
            row = cur.fetchone()
        return int((row or {}).get("n") or 0)
    except Exception:
        return 0


def json_error_message(result: Response, fallback: str) -> str:
    try:
        import json

        return json.loads(result.body.decode()).get("error") or fallback
    except Exception:
        return fallback
