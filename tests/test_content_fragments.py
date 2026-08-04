"""Guard: every routed content_fragment file exists on disk (no DB)."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.routes import ALL_PAGES

_FRAGMENTS_DIR = Path(__file__).resolve().parents[1] / "content" / "site" / "fragments"


def test_all_page_content_fragments_exist():
    missing: list[str] = []
    checked = 0
    for page in ALL_PAGES:
        rel = page.content_fragment
        if not rel:
            continue
        checked += 1
        path = _FRAGMENTS_DIR / rel
        if not path.is_file():
            missing.append(f"{page.route} -> {rel}")
    assert checked > 0, "expected at least one content_fragment in ALL_PAGES"
    assert not missing, "missing fragment files:\n" + "\n".join(missing)


def test_load_fragment_missing_returns_404_path():
    from app.controllers import web_controller as wc

    wc._load_fragment.cache_clear()
    with pytest.raises(StarletteHTTPException) as exc:
        wc._load_fragment("__missing__/does-not-exist.html")
    assert exc.value.status_code == 404
