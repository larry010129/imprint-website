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
    templates_dir: Path = ROOT / "app" / "views"
    docs_url: str | None = None
    redoc_url: str | None = None

    @property
    def port(self) -> str:
        return os.environ.get("PORT", "8080")

    @property
    def is_render(self) -> bool:
        return os.environ.get("RENDER") == "true" or bool(os.environ.get("RENDER_SERVICE_ID"))

    @property
    def public_base_url(self) -> str:
        external = os.environ.get("RENDER_EXTERNAL_URL")
        if external:
            base = external
        else:
            base = f"http://127.0.0.1:{self.port}"
        if self.is_render and not base.startswith("http"):
            base = f"https://{base}"
        return base


settings = Settings()
