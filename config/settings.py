"""Application settings and paths."""

from __future__ import annotations

import os
from pathlib import Path

# Repository root (parent of config/)
ROOT = Path(__file__).resolve().parent.parent


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


settings = Settings()
