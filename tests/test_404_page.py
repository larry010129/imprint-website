"""Shop 404 template — Jude-locked copy. Handler wiring is Rex's."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "content" / "site" / "templates" / "pages" / "404.html"
BODY = ROOT / "content" / "site" / "bodies" / "404.html"
REGISTRY = ROOT / "content" / "site" / "page-registry.json"

_TITLE = "找不到這個頁面"
_LEAD = "您要找的頁面不在這裡。可以回首頁，或從系列再看一次。"
_HOME = "回首頁"
_SERIES = "系列"


def test_template_and_body_lock_jude_copy():
    for src in (TEMPLATE.read_text(encoding="utf-8"), BODY.read_text(encoding="utf-8")):
        assert f"<h1 id=\"error-404-title\">{_TITLE}</h1>" in src
        assert _LEAD in src
        assert f'href="/">{_HOME}</a>' in src
        assert f'href="/series">{_SERIES}</a>' in src
        assert "/jewelry/" not in src
        assert "shop.js" not in src


def test_registry_points_at_shop_404_template():
    row = next(
        item
        for item in json.loads(REGISTRY.read_text(encoding="utf-8"))
        if item["route"] == "/404"
    )
    assert row["template"] == "pages/404.html"
    assert row["title"] == f"{_TITLE}｜銘印鑽石 IMPRINT DIAMOND"
    assert row["extra_css"] == ["/static/css/error-404.css?v=2"]
    extra = TEMPLATE.read_text(encoding="utf-8").split("{% block extra_css %}", 1)[1]
    extra = extra.split("{% endblock %}", 1)[0]
    assert "error-404.css?v=2" in extra
    assert "{% extends \"layouts/base.html\" %}" in TEMPLATE.read_text(encoding="utf-8")
