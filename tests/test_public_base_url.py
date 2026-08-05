"""public_base_url precedence: PUBLIC_SITE_URL > SITE_URL > RENDER_EXTERNAL_URL."""

from __future__ import annotations

from config.settings import Settings


def _clear_url_env(monkeypatch):
    for key in ("PUBLIC_SITE_URL", "SITE_URL", "RENDER_EXTERNAL_URL", "RENDER", "RENDER_SERVICE_ID"):
        monkeypatch.delenv(key, raising=False)


def test_public_base_url_prefers_public_site_url(monkeypatch):
    _clear_url_env(monkeypatch)
    monkeypatch.setenv("PUBLIC_SITE_URL", "https://www.imprintdiamond.com/")
    monkeypatch.setenv("SITE_URL", "https://ignored.example/")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://app.onrender.com/")
    assert Settings().public_base_url == "https://www.imprintdiamond.com"


def test_public_base_url_falls_back_to_site_url(monkeypatch):
    _clear_url_env(monkeypatch)
    monkeypatch.setenv("SITE_URL", "https://www.imprintdiamond.com")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://app.onrender.com/")
    assert Settings().public_base_url == "https://www.imprintdiamond.com"


def test_public_base_url_falls_back_to_render_external(monkeypatch):
    _clear_url_env(monkeypatch)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://app.onrender.com/")
    assert Settings().public_base_url == "https://app.onrender.com"


def test_public_base_url_localhost_default(monkeypatch):
    _clear_url_env(monkeypatch)
    monkeypatch.setenv("PORT", "9090")
    assert Settings().public_base_url == "http://127.0.0.1:9090"
