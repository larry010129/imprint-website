"""Branded shop 404 — Jude-locked copy + shop chrome."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")

_TITLE = "找不到這個頁面"
_LEAD = "您要找的頁面不在這裡。可以回首頁，或從系列再看一次。"
_MISSING = "/this-path-does-not-exist-404-test"


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def _404_main(html: str) -> str:
    start = html.find('id="mvc-404"')
    assert start != -1
    end = html.find("</main>", start)
    return html[start:end]


def test_unmatched_route_renders_shop_404(client):
    resp = client.get(_MISSING)
    assert resp.status_code == 404
    html = resp.text
    assert f"<title>{_TITLE}｜銘印鑽石 IMPRINT DIAMOND</title>" in html
    assert f"<h1 id=\"error-404-title\">{_TITLE}</h1>" in html
    assert _LEAD in html
    main = _404_main(html)
    assert 'href="/">回首頁</a>' in main
    assert 'href="/series">系列</a>' in main
    assert 'class="site-chrome"' in html
    assert "error-404.css?v=2" in html
    assert 'content="noindex, nofollow"' in html
    assert "/jewelry/" not in main
    assert "shop.js" not in html


def test_404_route_uses_same_shop_body(client):
    resp = client.get("/404")
    html = resp.text
    assert f"<h1 id=\"error-404-title\">{_TITLE}</h1>" in html
    assert _LEAD in html
    main = _404_main(html)
    assert 'href="/">回首頁</a>' in main
    assert 'href="/series">系列</a>' in main
