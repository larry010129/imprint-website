"""Application settings and paths."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

# Repository root (parent of config/)
ROOT = Path(__file__).resolve().parent.parent
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})


def public_reset_base_is_safe(base: str) -> bool:
    """True when a reset-link base is https and not loopback / empty."""
    raw = (base or "").strip()
    if not raw:
        return False
    parsed = urlparse(raw if "://" in raw else f"//{raw}")
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    if not host or host in _LOOPBACK_HOSTS or host.endswith(".localhost"):
        return False
    return True


class Settings:
    app_name: str = "Imprint Diamond"
    site_root: Path = ROOT
    static_dir: Path = ROOT / "public"
    # Jinja SSR root: layouts/, pages/, partials/. Fragments live in site_content_dir/fragments.
    templates_dir: Path = ROOT / "content" / "site" / "templates"
    site_content_dir: Path = ROOT / "content" / "site"
    docs_url: str | None = None
    redoc_url: str | None = None

    @property
    def port(self) -> str:
        return os.environ.get("PORT", "8080")

    @property
    def is_render(self) -> bool:
        return os.environ.get("RENDER") == "true" or bool(os.environ.get("RENDER_SERVICE_ID"))

    @property
    def google_client_id(self) -> str:
        return os.environ.get("GOOGLE_CLIENT_ID", "").strip()

    @property
    def recaptcha_site_key(self) -> str:
        return os.environ.get("RECAPTCHA_SITE_KEY", "").strip()

    @property
    def recaptcha_secret_key(self) -> str:
        return os.environ.get("RECAPTCHA_SECRET_KEY", "").strip()

    @property
    def public_base_url(self) -> str:
        # Prefer marketing/canonical URL for email + reset links; Render URL is fallback.
        base = (
            os.environ.get("PUBLIC_SITE_URL", "").strip()
            or os.environ.get("SITE_URL", "").strip()
            or os.environ.get("RENDER_EXTERNAL_URL", "").strip()
            or f"http://127.0.0.1:{self.port}"
        )
        if self.is_render and not base.startswith("http"):
            base = f"https://{base}"
        return base.rstrip("/")

    def reset_mail_base_ok(self) -> bool:
        """On Render, refuse empty / loopback / non-https reset-link bases."""
        if not self.is_render:
            return True
        return public_reset_base_is_safe(self.public_base_url)

    @property
    def supabase_url(self) -> str:
        return os.environ.get("SUPABASE_URL", "").strip().rstrip("/")

    @property
    def supabase_service_role_key(self) -> str:
        """Server key for Storage/admin APIs: SERVICE_ROLE, else SUPABASE_SECRET_KEY."""
        return (
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
            or os.environ.get("SUPABASE_SECRET_KEY", "").strip()
        )

    @property
    def supabase_storage_bucket(self) -> str:
        return os.environ.get("SUPABASE_STORAGE_BUCKET", "shop-media").strip() or "shop-media"

    @property
    def admin_release_notes_password(self) -> str:
        """6-char unlock code for /admin/release-notes editor (default 010129)."""
        return os.environ.get("ADMIN_RELEASE_NOTES_PASSWORD", "010129").strip() or "010129"


settings = Settings()

