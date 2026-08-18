"""Pin Jude-locked legal copy, robots, and slot fallbacks."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from app.cms_copy_slot_specs import copy_slot_specs
from app.page_image_slots import page_image_slot_specs

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def _legal_slots(route: str) -> dict[str, str]:
    return {
        spec["slot_key"]: spec["default_text"]
        for spec in copy_slot_specs()
        if spec["page_key"] == route
    }


def test_privacy_keeps_draft_noindex_and_locked_cookie_third(client):
    resp = client.get("/privacy")
    assert resp.status_code == 200
    html = resp.text
    assert 'content="noindex, nofollow"' in html
    assert "本頁面為草稿" in html
    assert "已整理全部資料類型" not in html
    assert "或其他 Google 服務內容" not in html
    assert "尚待確認" in html
    assert "不臆造" in html
    assert "Botpress" not in html
    body_start = html.find("Cookie 與登入狀態")
    body = html[body_start : html.find("資料使用目的")]
    assert "imprint_session Cookie（httpOnly）" in body
    assert "imprint_pre2fa" in body
    assert "imprint_pwreset" in body
    assert "官網頁面載入 Google 代碼管理工具（Google Tag Manager）。GTM 可能載入 Google Ads 轉換追蹤。" in body
    assert "AW-" not in body
    assert "GTM-" not in body
    third = html[html.find("第三方服務") : html.find("查詢、更正與刪除")]
    assert "Google Ads 轉換追蹤亦由 Google 處理。" in third
    assert "註冊頁使用 reCAPTCHA。" in third
    assert "線上客服對話框僅在您點選後載入。" in third
    assert "Botpress" not in third
    assert "AW-" not in third
    slots = _legal_slots("/privacy")
    assert slots["cookie-gtm"] == (
        "官網頁面載入 Google 代碼管理工具（Google Tag Manager）。GTM 可能載入 Google Ads 轉換追蹤。"
    )
    assert slots["third-chat"] == "線上客服對話框僅在您點選後載入。"
    assert slots["pending-title"] == "尚待確認"


def test_terms_keeps_draft_noindex_and_return_policy_links(client):
    resp = client.get("/terms")
    assert resp.status_code == 200
    html = resp.text
    assert 'content="noindex, nofollow"' in html
    assert "本頁面為草稿" in html
    assert "管轄法院" not in html
    assert "TODO：待補充" not in html
    assert "本頁不列克拉價目" in html
    assert html.count('href="/return-policy"') >= 3
    assert 'href="/return"' not in html
    assert "NT$24,000" not in html
    image_keys = {spec.page_key for spec in page_image_slot_specs()}
    assert "/terms" not in image_keys


def test_return_policy_stays_indexable(client):
    resp = client.get("/return-policy")
    assert resp.status_code == 200
    html = resp.text
    assert 'content="noindex' not in html
    assert "index, follow, max-image-preview:large" in html
    assert "退換貨與取消政策" in html
    assert "50% 訂金" in html
    assert 'href="/return"' not in html
