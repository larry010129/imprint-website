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
    assert "<title>隱私權政策｜銘印鑽石 IMPRINT DIAMOND</title>" in html
    assert "隱私權政策（草稿）" not in html
    assert "本頁面為草稿" in html
    assert "TODO：待補充" not in html
    assert "已整理全部資料類型" not in html
    assert "或其他 Google 服務內容" not in html
    assert "尚待確認" not in html
    assert "Pending confirmation" not in html
    assert "金流、物流業者名稱尚待確認" not in html
    assert "Names of payment and logistics providers are still pending confirmation." not in html
    assert "保存期限" in html
    assert "個人資料保存期限為一年。" in html
    assert "款項以匯款方式處理，不經第三方金流業者。出貨由順豐速運配送。" in html
    assert "不臆造" not in html
    assert "Zeczec" not in html
    body_start = html.find("Cookie 與登入狀態")
    body = html[body_start : html.find("資料使用目的")]
    assert "imprint_session Cookie（httpOnly）" in body
    assert "官網頁面載入 Google 代碼管理工具（Google Tag Manager）。GTM 可能載入 Google Ads 轉換追蹤。" in body
    assert "並載入" not in body
    assert "頁面測量" not in body
    assert "imprint_pre2fa" not in body
    assert "AW-" not in body
    assert "GTM-" not in body
    assert "GA4" not in body
    assert "TikTok" not in body
    third = html[html.find("第三方服務") : html.find("查詢、更正與刪除")]
    assert "Google Ads 轉換追蹤亦由 Google 處理。" in third
    assert "出貨由順豐速運配送。" in third
    assert "尚待確認" not in third
    assert "reCAPTCHA" not in third
    assert "Botpress" not in third
    assert "AW-" not in third
    assert "GA4" not in third
    assert "TikTok" not in third
    slots = _legal_slots("/privacy")
    assert slots["cookie-gtm"] == (
        "官網頁面載入 Google 代碼管理工具（Google Tag Manager）。GTM 可能載入 Google Ads 轉換追蹤。"
    )
    assert "third-recaptcha" not in slots
    assert "third-chat" not in slots
    assert slots["third-body"] == (
        "Google 登入由 Google 提供身份驗證，其資料處理受 Google 隱私權政策規範。"
        "您可於 Google 帳戶設定中管理或撤銷本網站的存取權限。Google Ads 轉換追蹤亦由 Google 處理。"
    )
    assert slots["third-ship"] == "出貨由順豐速運配送。"
    assert slots["retain-body"] == "個人資料保存期限為一年。"
    assert slots["pay-body"] == (
        "款項以匯款方式處理，不經第三方金流業者。出貨由順豐速運配送。"
    )
    assert "pending-title" not in slots
    assert "pending-li-1" not in slots
    assert "pending-li-2" not in slots
    assert "Retention period" not in slots.values()
    assert "Payment and shipping" not in slots.values()
    assert "hero-lead" not in slots


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
    assert "NT$98,000" not in html
    assert "NT$250,000" not in html
    slots = _legal_slots("/terms")
    assert slots["price-body"] == "鑽石與飾品價格以雙方確認及價格總覽為準。本頁不列克拉價目。"
    assert "管轄法院" not in slots.get("todo-li-3", "")
    assert "todo-title" not in slots
    assert "取件與保管" in html
    assert (
        "成品完成並通知您後，請於三個月內取件。"
        "逾期未取，自第四個月起酌收保管費，金額為尾款的 5%，未滿一個月以一個月計算。"
    ) in html
    assert slots["hold-title"] == "取件與保管"
    assert slots["hold-body"] == (
        "成品完成並通知您後，請於三個月內取件。"
        "逾期未取，自第四個月起酌收保管費，金額為尾款的 5%，未滿一個月以一個月計算。"
    )
    image_keys = {spec.page_key for spec in page_image_slot_specs()}
    assert "/terms" not in image_keys
    assert "hero-lead" not in slots


def test_return_policy_stays_indexable(client):
    resp = client.get("/return-policy")
    assert resp.status_code == 200
    html = resp.text
    assert 'content="noindex' not in html
    assert "index, follow, max-image-preview:large" in html
    assert "退換貨與取消政策" in html
    assert "50% 訂金" in html
    assert 'href="/return"' not in html
    assert "NT$250,000" not in html
    assert "克拉尺寸誤差" not in html
    assert "若成品大於訂購尺寸，無需支付額外費用。若成品小於訂購尺寸，將按比例退款。" in html
    slots = _legal_slots("/return-policy")
    assert slots["carat-title"] == "克拉尺寸"
    assert slots["carat-body"] == (
        "若成品大於訂購尺寸，無需支付額外費用。若成品小於訂購尺寸，將按比例退款。"
    )
    assert "取件與保管" in html
    assert slots["hold-body"] == (
        "成品完成並通知您後，請於三個月內取件。"
        "逾期未取，自第四個月起酌收保管費，金額為尾款的 5%，未滿一個月以一個月計算。"
    )


def test_checkout_hold_notice_is_copy_only():
    root = Path(__file__).resolve().parents[1]
    panel = (root / "content/site/templates/partials/htmx/checkout_panel.html").read_text(
        encoding="utf-8"
    )
    notice = (
        "成品通知後請於三個月內取件；逾期自第四個月起，"
        "按尾款 5% 計收保管費（未滿一個月以一個月計）。"
    )
    assert panel.count(notice) == 2
    fulfillment = panel[panel.find("取貨方式") : panel.find("給銘印鑽石的訊息")]
    assert f'<p class="checkout-block-hint">{notice}</p>' in fulfillment
    assert "製作期約三個月" in fulfillment
    submit_zone = panel[panel.find("此步驟尚未付款") : panel.find("確認送出訂單")]
    assert f'<p class="checkout-pay-note" role="note">{notice}</p>' in submit_zone
    notice_box = panel[panel.find("checkout-notice") : panel.find("checkout-lead")]
    assert notice not in notice_box
    mobile_bar = panel[panel.find("checkout-mobile-bar") :]
    assert notice not in mobile_bar
    shop_js = (root / "public/js/shop.js").read_text(encoding="utf-8")
    assert notice not in shop_js
    assert "保管費" not in shop_js


def test_calculator_omits_hold_notice():
    root = Path(__file__).resolve().parents[1]
    notice = (
        "成品通知後請於三個月內取件；逾期自第四個月起，"
        "按尾款 5% 計收保管費（未滿一個月以一個月計）。"
    )
    calc = (root / "content/site/templates/pages/shop/calculator.html").read_text(
        encoding="utf-8"
    )
    body = (root / "content/site/bodies/shop__calculator.html").read_text(encoding="utf-8")
    assert notice not in calc
    assert notice not in body
    shop_js = (root / "public/js/shop.js").read_text(encoding="utf-8")
    assert notice not in shop_js


def test_calculator_terms_include_pickup_hold():
    root = Path(__file__).resolve().parents[1]
    sentence = (
        "成品完成通知後，須於三個月內取件，逾期未取件者，"
        "第四個月起酌收尾款5%之保管費，未滿一個月以一個月計算。"
    )
    calc = (root / "content/site/templates/pages/shop/calculator.html").read_text(
        encoding="utf-8"
    )
    body = (root / "content/site/bodies/shop__calculator.html").read_text(encoding="utf-8")
    for html in (calc, body):
        dialog = html[html.find("shop-terms-dialog") : html.find("ring-size-guide-dialog")]
        headings = (
            "一、條款接受",
            "二、試算價格",
            "三、鑽石顏色與預覽",
            "四、訂製品與交期",
            "五、訂金與付款",
            "六、取件與保管",
            "七、個人資料",
            "八、責任限制與準據法",
            "九、條款修訂",
        )
        found = [dialog.find(f"<strong>{title}</strong>") for title in headings]
        assert all(i != -1 for i in found)
        assert found == sorted(found)
        assert dialog.count('class="shop-terms-section"') == 9
        assert sentence in dialog
    shop_js = (root / "public/js/shop.js").read_text(encoding="utf-8")
    assert sentence not in shop_js


def test_calculator_terms_dialog_uses_viewport_units_on_phones():
    root = Path(__file__).resolve().parents[1]
    css = (root / "public/css/shop.css").read_text(encoding="utf-8")
    start = css.find(".shop-terms-dialog[open]")
    end = css.find(".ring-size-guide-dialog")
    assert start != -1 and end > start
    dialog_css = css[start:end]
    assert "calc(100vw - 2rem)" in dialog_css
    assert "calc(100% - 2rem)" not in dialog_css
    assert "100svh" in dialog_css
    assert "@media (max-width: 639px), (max-height: 540px)" in dialog_css
    assert "safe-area-inset-top" in dialog_css

    calc = (root / "content/site/templates/pages/shop/calculator.html").read_text(
        encoding="utf-8"
    )
    critical = calc[calc.find(".shop-terms-dialog[open]") : calc.find("</style>")]
    assert "calc(100vw - 2rem)" in critical
    assert "calc(100% - 2rem)" not in critical
    assert "@media (max-width: 639px), (max-height: 540px)" in critical
