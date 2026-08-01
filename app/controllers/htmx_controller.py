"""HTMX HTML partial router — chrome + mounts auth/shop/member sub-routers."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.auth import bump_token_version, clear_pre2fa_cookie, clear_session_cookie, get_user_id
from app.controllers import htmx_auth, htmx_member, htmx_shop, htmx_shop_wizard
from app.controllers.htmx_common import cart_count, html, hx_redirect, nav_user

router = APIRouter(prefix="/htmx", tags=["htmx"])
router.include_router(htmx_auth.router)
router.include_router(htmx_shop.router)
router.include_router(htmx_shop_wizard.router)
router.include_router(htmx_member.router)


@router.get("/cart-badge", response_class=HTMLResponse)
async def cart_badge(request: Request) -> HTMLResponse:
    return html(request, "cart_badge.html", {"count": cart_count(get_user_id(request)), "oob": False})


@router.get("/nav-cart", response_class=HTMLResponse)
async def nav_cart(request: Request) -> HTMLResponse:
    """Cart control HTML — empty when guest so slot leaves the DOM (outerHTML)."""
    uid = get_user_id(request)
    if not uid:
        return HTMLResponse("")
    variant = (request.query_params.get("variant") or "desktop").strip().lower()
    if variant == "mobile":
        return html(request, "nav_cart_mobile.html", {"count": cart_count(uid)})
    return html(request, "nav_cart.html", {"count": cart_count(uid)})


@router.get("/nav-account", response_class=HTMLResponse)
async def nav_account(request: Request) -> HTMLResponse:
    uid = get_user_id(request)
    return html(
        request,
        "nav_account.html",
        {"nav_user": nav_user(request), "cart_count": cart_count(uid)},
    )


@router.post("/logout")
async def logout(request: Request) -> Response:
    user_id = get_user_id(request)
    if user_id:
        bump_token_version(user_id)
    resp = hx_redirect("/")
    clear_session_cookie(resp, request)
    clear_pre2fa_cookie(resp, request)
    return resp
