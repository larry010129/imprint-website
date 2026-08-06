"""P3 smoke: key HTML pages + one HTMX partial with HX-Request."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
# Avoid background seed races during TestClient lifespan.
os.environ.setdefault("STARTUP_SEED_MODE", "off")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/login.html",
        "/register.html",
        "/cart.html",
        "/checkout.html",
        "/account.html",
        "/contact.html",
        "/track-order.html",
        "/stories.html",
        "/what-is-dna-diamond.html",
    ],
)
def test_member_and_chrome_pages_return_html(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, path
    ctype = resp.headers.get("content-type", "")
    assert "text/html" in ctype, path
    assert "htmx.min.js" in resp.text or path.endswith(
        (".html",)
    )  # auth layout also includes htmx
    if path in ("/", "/cart.html", "/stories.html"):
        assert "/static/js/htmx.min.js" in resp.text
    # Public pages must not load retired React islands (admin-tables is admin-only).
    for island in (
        "/static/react/nav.js",
        "/static/react/footer.js",
        "/static/react/checkout.js",
        "/static/react/auth.js",
        "/static/react/account.js",
        "/static/react/profile.js",
        "/static/react/stories.js",
        "/static/react/dna-diamond.js",
        "/static/react/shop-tour.js",
        "/static/react/price.js",
        "/static/react/faq.js",
    ):
        assert island not in resp.text, f"{path} still loads {island}"


def test_checkout_page_passes_items_without_js_vals(client):
    """CSP blocks unsafe-eval; checkout must not rely on hx-vals js:."""
    resp = client.get("/checkout.html?items=abc-123,def-456")
    assert resp.status_code == 200
    assert "載入訂單" in resp.text
    assert 'hx-get="/htmx/checkout?items=' in resp.text
    assert "abc-123" in resp.text
    assert "hx-vals=" not in resp.text or "js:" not in resp.text
    assert "確認訂單" in resp.text


def test_htmx_checkout_guest_redirect_preserves_items(client):
    resp = client.get(
        "/htmx/checkout?items=cart-item-1",
        headers={"HX-Request": "true"},
        follow_redirects=False,
    )
    assert resp.status_code == 200
    loc = resp.headers.get("HX-Redirect", "")
    assert loc.startswith("/login.html?next=")
    assert "checkout.html" in loc
    assert "cart-item-1" in loc


def test_htmx_checkout_empty_items_redirects_cart_when_authed(client, monkeypatch):
    monkeypatch.setattr(
        "app.controllers.htmx_shop.get_user_id", lambda _request: "user-test-id"
    )
    resp = client.get(
        "/htmx/checkout",
        headers={"HX-Request": "true"},
        follow_redirects=False,
    )
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect") == "/cart.html"


def test_success_page_loads_order_script(client):
    resp = client.get("/success.html?order=IM-TEST-1")
    assert resp.status_code == 200
    assert "訂單已送出" in resp.text
    assert "/static/js/order-success.js" in resp.text


def test_htmx_cart_badge_accepts_hx_request(client):
    resp = client.get("/htmx/cart-badge", headers={"HX-Request": "true"})
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "nav-cart-badge" in resp.text


def test_htmx_nav_cart_guest_empty(client):
    resp = client.get("/htmx/nav-cart", headers={"HX-Request": "true"})
    assert resp.status_code == 200
    assert resp.text.strip() == ""
    mobile = client.get("/htmx/nav-cart?variant=mobile", headers={"HX-Request": "true"})
    assert mobile.status_code == 200
    assert mobile.text.strip() == ""


def test_htmx_cart_partial_guest(client):
    resp = client.get("/htmx/cart", headers={"HX-Request": "true"})
    assert resp.status_code == 200
    assert "登入" in resp.text or "guest" in resp.text.lower() or "購物車" in resp.text


def test_login_page_has_htmx_form(client):
    resp = client.get("/login.html")
    assert resp.status_code == 200
    assert 'hx-post="/htmx/auth/login"' in resp.text
    assert 'id="forgot-form"' not in resp.text
    assert 'href="/forgot-password.html"' in resp.text
    assert "accounts.google.com/gsi/client" in resp.text or "google_client_id" not in resp.text


def test_forgot_password_page_explains_totp_requirement(client):
    resp = client.get("/forgot-password.html")
    assert resp.status_code == 200
    assert 'hx-post="/htmx/auth/forgot-password-verify"' in resp.text
    assert 'hx-post="/htmx/auth/forgot-password"' in resp.text
    assert 'data-fp-wizard' in resp.text
    assert 'data-otp-group' in resp.text
    assert 'data-otp-target="fpCodeHidden"' in resp.text
    assert 'id="fpCodeHidden"' in resp.text
    assert "forgot-password.js?v=3" in resp.text
    assert "otp-input.js?v=3" in resp.text
    assert "已啟用 Authenticator" in resp.text
    assert 'href="/account-security.html"' in resp.text
    assert 'href="/login.html?next=/account-security.html"' in resp.text


def test_account_security_page_has_htmx_and_totp_script(client):
    resp = client.get("/account-security.html")
    assert resp.status_code == 200
    assert 'hx-get="/htmx/account-security"' in resp.text
    assert "totp-security.js" in resp.text


def test_htmx_account_security_guest_shows_login(client):
    resp = client.get("/htmx/account-security", headers={"HX-Request": "true"})
    assert resp.status_code == 200
    assert "請先登入" in resp.text
    assert 'id="totp-start-btn"' not in resp.text


def test_calculator_page_shop_js_wizard(client):
    resp = client.get("/shop/calculator/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert 'id="shop-page"' in resp.text
    assert "/static/js/shop.js" in resp.text
    assert "/static/js/shop-i18n.js" in resp.text
    assert "/static/js/shop-pricing-local.js" in resp.text
    assert "shop-htmx-root" not in resp.text
    assert "htmx/shop/step/" not in resp.text


def test_htmx_shop_catalog_step(client):
    resp = client.get("/htmx/shop/step/catalog", headers={"HX-Request": "true"})
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "catalog-grid" in resp.text or "catalog-empty" in resp.text
    assert 'hx-get="/htmx/shop/step/styles' in resp.text or "目前沒有上架" in resp.text


def test_htmx_shop_diamond_styles_and_configure(client):
    styles = client.get(
        "/htmx/shop/step/styles?category=diamond", headers={"HX-Request": "true"}
    )
    assert styles.status_code == 200
    assert "diamond-white" in styles.text
    assert "白鑽" in styles.text
    assert "diamond-first-love" not in styles.text
    cfg = client.get(
        "/htmx/shop/step/configure?category=diamond&type=diamond-white",
        headers={"HX-Request": "true"},
    )
    assert cfg.status_code == 200
    assert 'hx-post="/htmx/shop/quote"' in cfg.text
    assert 'hx-post="/htmx/shop/cart"' in cfg.text
    assert "htmx-carat" in cfg.text


def test_htmx_shop_quote_partial(client):
    """Server quote via HTMX form fields — core diamond path (no metal)."""
    resp = client.post(
        "/htmx/shop/quote",
        headers={"HX-Request": "true"},
        data={
            "category": "diamond",
            "type": "diamond-white",
            "carat": "0.3",
            "diamondKind": "white",
            "diamondShape": "round",
            "summaryZh": "白鑽",
        },
    )
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "shop-quote" in resp.text or "預估總價" in resp.text or "NT$" in resp.text


def test_htmx_shop_cart_guest_redirects(client):
    resp = client.post(
        "/htmx/shop/cart",
        headers={"HX-Request": "true"},
        data={
            "category": "diamond",
            "type": "diamond-white",
            "carat": "0.3",
            "diamondKind": "white",
            "summaryZh": "白鑽",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect", "").startswith("/login.html")


def test_calculator_preview_banner_and_flag(client):
    resp = client.get("/shop/calculator/?preview=1&category=pendant")
    assert resp.status_code == 200
    assert "預覽模式｜不會送出真實訂單" in resp.text
    assert "is-shop-preview" in resp.text
    assert "shop_preview=1" in resp.text
    assert 'data-shop-preview="1"' in resp.text
    assert "preview: true" in resp.text or "preview:true" in resp.text.replace(" ", "")
    assert "<title>" in resp.text and "預覽模式" in resp.text
    assert "/static/js/shop.js" in resp.text


def test_htmx_styles_grid_has_size_class(client):
    resp = client.get(
        "/htmx/shop/step/styles?category=diamond&preview=1",
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    assert "type-grid--size-" in resp.text
    assert 'data-shop-preview="1"' in resp.text


def test_htmx_shop_cart_blocked_in_preview(client):
    resp = client.post(
        "/htmx/shop/cart?preview=1",
        headers={"HX-Request": "true"},
        data={
            "category": "diamond",
            "type": "diamond-white",
            "carat": "0.3",
            "diamondKind": "white",
            "summaryZh": "白鑽",
            "preview": "1",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 403
    assert "預覽模式" in resp.text
    assert not resp.headers.get("HX-Redirect")


def test_cart_checkout_blocked_by_preview_cookie(client):
    client.cookies.set("shop_preview", "1")
    resp = client.post("/api/cart-checkout", json={})
    assert resp.status_code in (401, 403)
    if resp.status_code == 403:
        assert "預覽" in resp.json().get("error", "")


def test_cms_page_template_and_freeform_partial_exist():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert (root / "content/site/templates/pages/cms_page.html").is_file()
    assert (root / "content/site/templates/partials/cms/section_freeform.html").is_file()
    for name in (
        "hero",
        "rich_text",
        "image_text",
        "cta_band",
        "faq_embed",
        "testimonials_embed",
        "button_row",
        "spacer",
        "freeform",
    ):
        assert (root / f"content/site/templates/partials/cms/section_{name}.html").is_file(), name


def test_page_context_bridge_removed(client):
    resp = client.get("/api/v1/page-context", params={"route": "/"})
    assert resp.status_code == 404


def test_apps_web_and_public_islands_gone():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert not (root / "apps" / "web").exists()
    react = root / "public" / "react"
    assert (react / "admin-tables.js").is_file()
    for name in (
        "nav.js",
        "footer.js",
        "checkout.js",
        "auth.js",
        "account.js",
        "stories.js",
        "faq.js",
        "price.js",
        "dna-diamond.js",
        "profile.js",
    ):
        assert not (react / name).exists(), name
    # Classic calculator wizard restored (pre-HTMX shop.js + optional tour island).
    assert (root / "public" / "js" / "shop.js").is_file()


def test_home_faq_ssr_and_wall_script(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "需要準備多少毛髮或骨灰" in resp.text
    assert "/static/js/home-wall.js" in resp.text
    assert "faq.js" not in resp.text
    assert "stories.js" not in resp.text
