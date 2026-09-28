"""HTMX HTML partial router — chrome + mounts auth/shop/member sub-routers."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.auth import (
    NAV_HINT_COOKIE,
    bump_token_version,
    clear_nav_hint_cookie,
    clear_pre2fa_cookie,
    clear_session_cookie,
    get_user_id,
)
from app.controllers import htmx_auth, htmx_member, htmx_shop, htmx_shop_wizard
from app.controllers.htmx_common import (
    cart_count,
    html,
    hx_redirect,
    nav_state,
    nav_user,
    templates,
)

router = APIRouter(prefix="/htmx", tags=["htmx"])
router.include_router(htmx_auth.router)
router.include_router(htmx_shop.router)
router.include_router(htmx_shop_wizard.router)
router.include_router(htmx_member.router)


@router.get("/cart-badge", response_class=HTMLResponse)
def cart_badge(request: Request) -> HTMLResponse:
    return html(request, "cart_badge.html", {"count": cart_count(get_user_id(request)), "oob": False})


@router.get("/nav-cart", response_class=HTMLResponse)
def nav_cart(request: Request) -> HTMLResponse:
    """Cart control HTML — empty when guest so slot leaves the DOM (outerHTML)."""
    uid = get_user_id(request)
    if not uid:
        return HTMLResponse("")
    variant = (request.query_params.get("variant") or "desktop").strip().lower()
    if variant == "mobile":
        return html(request, "nav_cart_mobile.html", {"count": cart_count(uid)})
    return html(request, "nav_cart.html", {"count": cart_count(uid)})


@router.get("/nav-account", response_class=HTMLResponse)
def nav_account(request: Request) -> HTMLResponse:
    uid = get_user_id(request)
    variant = (request.query_params.get("variant") or "desktop").strip().lower()
    return html(
        request,
        "nav_account.html",
        {
            "nav_user": nav_user(request),
            "cart_count": cart_count(uid),
            "variant": "drawer" if variant == "drawer" else "desktop",
        },
    )


_NAV_SLOTS = ("nav-account-desktop", "nav-account-drawer", "site-nav-cart-slot")


@router.get("/nav-state", response_class=HTMLResponse)
def nav_state_view(request: Request) -> HTMLResponse:
    """Whole nav account/cart state in one request, as OOB swaps into nav.html slots.

    The same markup is cached in localStorage by nav.html so later pages paint it
    before this request returns (keyed by the imprint_nav hint cookie).
    """
    user, count = nav_state(request)
    render = templates.get_template
    parts = {
        "nav-account-desktop": render("partials/htmx/nav_account.html").render(
            request=request, nav_user=user, cart_count=count, variant="desktop"
        ),
        "nav-account-drawer": render("partials/htmx/nav_account.html").render(
            request=request, nav_user=user, cart_count=count, variant="drawer"
        ),
        "site-nav-cart-slot": (
            render("partials/htmx/nav_cart.html").render(request=request, count=count)
            if user
            else ""
        ),
    }
    body = "".join(
        f'<div data-nav-slot="{slot}" hx-swap-oob="innerHTML:#{slot}">{parts[slot]}</div>'
        for slot in _NAV_SLOTS
    )
    resp = HTMLResponse(body, headers={"Cache-Control": "no-store"})
    resp.headers["X-Nav-User"] = "1" if user else "0"
    if not user and request.cookies.get(NAV_HINT_COOKIE):
        # Session expired/revoked server-side: drop the hint so the cached
        # account menu stops painting on later pages.
        clear_nav_hint_cookie(resp, request)
    return resp


@router.post("/logout")
async def logout(request: Request) -> Response:
    user_id = get_user_id(request)
    if user_id:
        bump_token_version(user_id)
    resp = hx_redirect("/")
    clear_session_cookie(resp, request)
    clear_pre2fa_cookie(resp, request)
    return resp
