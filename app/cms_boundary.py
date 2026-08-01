"""CMS reserved-route denylist — calculator / shop / auth / API stay code-owned."""

from __future__ import annotations

import re
from posixpath import normpath
from urllib.parse import unquote

# Exact slugs blocked for cms_pages.slug (public URL is /p/{slug}).
RESERVED_CMS_SLUGS = frozenset(
    {
        "shop",
        "jewelry",
        "cart",
        "checkout",
        "login",
        "register",
        "account",
        "profile",
        "api",
        "admin",
        "static",
        "js",
        "css",
        "s",
        "price",
        "gold-price",
        "calculator",
        "auth",
        "orders",
        "favorites",
        "notifications",
        "history",
        "track-order",
        "success",
        "reset-password",
        "forgot-password",
    }
)

# Prefixes blocked for page_key used by page_images / page_copy_slots.
RESERVED_PAGE_KEY_PREFIXES = (
    "/shop/",
    "/jewelry/",
    "/api/",
    "/admin",
    "/cart",
    "/checkout",
    "/login",
    "/register",
    "/account",
    "/profile",
)

RESERVED_PAGE_KEYS = frozenset(
    {
        "/jewelry/",
        "/shop/calculator/",
        "/cart.html",
        "/checkout.html",
        "/login.html",
        "/register.html",
        "/account.html",
        "/profile.html",
        "/price.html",  # price table code-owned; no CMS ownership of pricing
    }
)

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


def normalize_cms_slug(raw: str) -> str:
    return str(raw or "").strip().lower().strip("/")


def is_reserved_cms_slug(slug: str) -> bool:
    s = normalize_cms_slug(slug)
    if not s:
        return True
    if s in RESERVED_CMS_SLUGS:
        return True
    head = s.split("/", 1)[0]
    return head in RESERVED_CMS_SLUGS


def validate_cms_slug(raw: str) -> tuple[str | None, str | None]:
    slug = normalize_cms_slug(raw)
    if not slug or not _SLUG_RE.fullmatch(slug):
        return None, "slug 無效（僅小寫英數與連字號）"
    if is_reserved_cms_slug(slug):
        return None, "此 slug 為系統保留路徑，不可使用"
    return slug, None


def normalize_page_key(raw: str) -> str | None:
    key = str(raw or "").strip()
    if not key or "\x00" in key or "?" in key or "#" in key:
        return None
    if key.startswith("//"):
        return None
    key = key.replace("\\", "/")
    for _ in range(3):
        decoded = unquote(key)
        if decoded == key:
            break
        key = decoded
    if "%" in key or not key.startswith("/"):
        return None
    key = re.sub(r"/+", "/", key).lower()
    key = normpath(key)
    return key if key.startswith("/") else None


def is_reserved_page_key(page_key: str) -> bool:
    key = normalize_page_key(page_key)
    if not key:
        return True
    reserved = {normalize_page_key(item) for item in RESERVED_PAGE_KEYS}
    if key in reserved:
        return True
    if key == "/jewelry" or key.startswith("/jewelry/"):
        return True
    return any(
        key == normalized or key.startswith(f"{normalized}/")
        for prefix in RESERVED_PAGE_KEY_PREFIXES
        if (normalized := normalize_page_key(prefix))
    )


def assert_content_page_key(page_key: str) -> tuple[str | None, str | None]:
    key = normalize_page_key(page_key)
    if not key:
        return None, "page_key 無效"
    if is_reserved_page_key(key):
        return None, "此頁面為系統保留（商店／結帳／登入／價格表），不可由 CMS 管理"
    return key, None
