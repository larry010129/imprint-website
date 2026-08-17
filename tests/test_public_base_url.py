"""public_base_url precedence: PUBLIC_SITE_URL > SITE_URL > RENDER_EXTERNAL_URL."""

from __future__ import annotations

from pathlib import Path

from config.settings import Settings, public_reset_base_is_safe


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


def test_public_reset_base_is_safe_accepts_live_shop_url():
    assert public_reset_base_is_safe("https://imprint-website-kh6x.onrender.com") is True
    assert public_reset_base_is_safe("https://imprint-website-kh6x.onrender.com/") is True


def test_public_reset_base_is_safe_rejects_empty_loopback_http():
    assert public_reset_base_is_safe("") is False
    assert public_reset_base_is_safe("   ") is False
    assert public_reset_base_is_safe("http://127.0.0.1:8080") is False
    assert public_reset_base_is_safe("https://127.0.0.1") is False
    assert public_reset_base_is_safe("https://localhost") is False
    assert public_reset_base_is_safe("http://imprint-website-kh6x.onrender.com") is False


def test_reset_mail_base_ok_skips_only_on_render(monkeypatch):
    _clear_url_env(monkeypatch)
    monkeypatch.setenv("PORT", "8080")
    assert Settings().reset_mail_base_ok() is True
    monkeypatch.setenv("RENDER", "true")
    assert Settings().reset_mail_base_ok() is False
    monkeypatch.setenv("PUBLIC_SITE_URL", "https://imprint-website-kh6x.onrender.com")
    assert Settings().reset_mail_base_ok() is True
    monkeypatch.setenv("PUBLIC_SITE_URL", "http://127.0.0.1:8080")
    assert Settings().reset_mail_base_ok() is False


def test_render_yaml_uses_live_shop_public_site_url():
    yaml = (Path(__file__).resolve().parents[1] / "render.yaml").read_text(encoding="utf-8")
    assert "value: https://imprint-website-kh6x.onrender.com" in yaml
    assert "value: https://www.imprintdiamond.com" not in yaml
