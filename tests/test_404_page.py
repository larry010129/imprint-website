"""Branded shop 404 — Jude-locked copy + shop chrome."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config.routes import PAGE_404

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "content" / "site" / "templates" / "pages" / "404.html"
BODY = ROOT / "content" / "site" / "bodies" / "404.html"
REGISTRY = ROOT / "content" / "site" / "page-registry.json"

_TITLE = "找不到這個頁面"
_LEAD = "您要找的頁面不在這裡。可以回首頁，或從系列再看一次。"
_HOME = "回首頁"
_SERIES = "系列"


@pytest.fixture(scope="module")
def client():
    from app.controllers.web_controller import register_pages

    app = FastAPI()
    register_pages(app)
    with TestClient(app) as c:
        yield c


def _404_main(html: str) -> str:
    start = html.find('id="mvc-404"')
    assert start != -1
    end = html.find("</main>", start)
    return html[start:end]


def test_template_and_body_lock_jude_copy():
    for src in (TEMPLATE.read_text(encoding="utf-8"), BODY.read_text(encoding="utf-8")):
        assert f"<h1 id=\"error-404-title\">{_TITLE}</h1>" in src
        assert _LEAD in src
        assert f'href="/">{_HOME}</a>' in src
        assert f'href="/series">{_SERIES}</a>' in src
        assert "/jewelry/" not in src
        assert "shop.js" not in src


def test_registry_and_route_meta():
    row = next(
        item
        for item in json.loads(REGISTRY.read_text(encoding="utf-8"))
        if item["route"] == "/404"
    )
    assert row["template"] == "pages/404.html"
    assert row["title"] == f"{_TITLE}｜銘印鑽石 IMPRINT DIAMOND"
    assert row["extra_css"] == ["/static/css/error-404.css?v=2"]
    assert PAGE_404.template == "pages/404.html"
    assert PAGE_404.title == f"{_TITLE}｜銘印鑽石 IMPRINT DIAMOND"
    assert PAGE_404.robots == "noindex, nofollow"
    extra = TEMPLATE.read_text(encoding="utf-8").split("{% block extra_css %}", 1)[1]
    extra = extra.split("{% endblock %}", 1)[0]
    assert "error-404.css?v=2" in extra


def test_unmatched_route_renders_shop_404(client):
    resp = client.get("/this-path-does-not-exist-404-test")
    assert resp.status_code == 404
    html = resp.text
    assert f"<title>{_TITLE}｜銘印鑽石 IMPRINT DIAMOND</title>" in html
    assert f"<h1 id=\"error-404-title\">{_TITLE}</h1>" in html
    assert _LEAD in html
    main = _404_main(html)
    assert f'href="/">{_HOME}</a>' in main
    assert f'href="/series">{_SERIES}</a>' in main
    assert 'class="site-chrome"' in html
    assert "error-404.css?v=2" in html
    assert 'content="noindex, nofollow"' in html
    assert "/jewelry/" not in main
    assert "shop.js" not in html
