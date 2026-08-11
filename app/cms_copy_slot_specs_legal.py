"""Legal page slot specs (/privacy, /terms, /return-policy).

Bodies are modeled as one 'text' slot per heading / paragraph / list item
(the render pipeline is plain-text only — no richtext kind). Split from
cms_copy_slot_specs.py to keep modules under 500 lines.
"""

from __future__ import annotations

from typing import Any

from app.cms_copy_slot_specs import _t


def legal_slot_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    specs.extend(_privacy_slots())
    specs.extend(_terms_slots())
    specs.extend(_return_policy_slots())
    return specs


def _privacy_slots() -> list[dict[str, Any]]:
    p = "/privacy"
    return [
        _t(p, "hero-title", "隱私權・標題", "隱私權政策", 1),
        _t(p, "crumb-current", "隱私權・麵包屑", "隱私權政策", 2),
        _t(p, "hero-eyebrow", "隱私權・眉標", "PRIVACY POLICY", 3),
        _t(p, "callout-top", "隱私權・草稿提示", "本頁面為草稿，尚待法務審閱與正式公告，目前設定為不開放搜尋引擎索引（noindex）。以下已整理網站目前實際蒐集之資料類型；標示為「TODO」的段落仍需法務補充後才能正式上線。", 10),
        _t(p, "collect-title", "隱私權・蒐集標題", "我們蒐集哪些資料", 20),
        _t(p, "collect-lead", "隱私權・蒐集引言", "當您透過網站與我們互動時，可能會提供以下資料：", 21),
        _t(p, "collect-li-1", "隱私權・蒐集項目1", "線上留言諮詢表單：姓名、電話、Email（選填）、留言內容（見聯絡我們頁面）", 22),
        _t(p, "collect-li-2", "隱私權・蒐集項目2", "訂購流程：訂單內容、收件資訊（見客製試算與購物車流程）", 23),
        _t(p, "collect-li-3", "隱私權・蒐集項目3", "會員註冊／帳戶設定：姓名、聯絡電話、Email、寄送地址（選填）", 24),
        _t(p, "google-title", "隱私權・Google登入標題", "使用 Google 登入時", 30),
        _t(p, "google-lead", "隱私權・Google登入引言", "若您選擇「使用 Google 登入」，我們會向 Google 取得並用於建立或連結會員帳號的資料包括：", 31),
        _t(p, "google-li-1", "隱私權・Google項目1", "Email（須為 Google 已驗證之信箱）", 32),
        _t(p, "google-li-2", "隱私權・Google項目2", "顯示名稱", 33),
        _t(p, "google-li-3", "隱私權・Google項目3", "Google 帳戶識別碼（用於辨識同一 Google 帳號，非您的 Google 密碼）", 34),
        _t(p, "google-note", "隱私權・Google補充", "我們不會取得您的 Google 密碼，也不會存取 Gmail、聯絡人、日曆或其他 Google 服務內容。", 35),
        _t(p, "import-title", "隱私權・匯入標題", "自 Google 帳戶匯入電話與地址（選填）", 40),
        _t(p, "import-body", "隱私權・匯入內文", "登入後，您可於會員專區主動點選「從 Google 帳戶匯入電話與地址」。僅在您同意 Google 的額外授權後，我們才會讀取 Google 帳戶中您已儲存的電話與地址，並填入尚未填寫的帳戶欄位。若 Google 帳戶中無此資料，或您拒絕授權，您仍可手動填寫。", 41),
        _t(p, "cookie-title", "隱私權・Cookie標題", "Cookie 與登入狀態", 50),
        _t(p, "cookie-body", "隱私權・Cookie內文", "登入成功後，網站會設定 imprint_session Cookie（httpOnly），用於維持登入狀態。登出或密碼重設後，此 Cookie 會失效。", 51),
        _t(p, "purpose-title", "隱私權・目的標題", "資料使用目的", 60),
        _t(p, "purpose-body", "隱私權・目的內文", "上述資料用於：建立與管理會員帳號、回覆諮詢、確認訂製需求、處理與交付訂單、以及與您聯繫訂單進度。", 61),
        _t(p, "third-title", "隱私權・第三方標題", "第三方服務", 70),
        _t(p, "third-body", "隱私權・第三方內文", "Google 登入由 Google 提供身份驗證服務，其資料處理受 Google 隱私權政策規範。您可於 Google 帳戶設定中管理或撤銷本網站的存取權限。", 71),
        _t(p, "todo-title", "隱私權・TODO標題", "TODO：待補充事項（請法務／品牌方確認後移除本區塊）", 80),
        _t(p, "todo-li-1", "隱私權・TODO項目1", "TODO：個人資料保存期限", 81),
        _t(p, "todo-li-2", "隱私權・TODO項目2", "TODO：是否委託第三方廠商處理資料（例如金流、物流業者名稱），以及其資料保護承諾", 82),
        _t(p, "todo-li-3", "隱私權・TODO項目3", "TODO：使用者查詢、更正、刪除個人資料的行使方式與聯絡窗口", 83),
        _t(p, "todo-li-4", "隱私權・TODO項目4", "TODO：其他 Cookie／追蹤技術使用情形（如有 GA、廣告像素等）", 84),
        _t(p, "todo-li-5", "隱私權・TODO項目5", "TODO：依個人資料保護法應揭露之其他事項", 85),
        _t(p, "callout-bottom", "隱私權・聯絡提示", "如對個人資料處理有疑問，可透過官方 LINE 與我們聯繫。", 90),
    ]


def _terms_slots() -> list[dict[str, Any]]:
    p = "/terms"
    return [
        _t(p, "hero-title", "服務條款・標題", "服務條款", 1),
        _t(p, "crumb-current", "服務條款・麵包屑", "服務條款", 2),
        _t(p, "hero-eyebrow", "服務條款・眉標", "TERMS OF SERVICE", 3),
        _t(p, "callout-top", "服務條款・草稿提示", "本頁面為草稿，尚待法務審閱與正式公告，目前設定為不開放搜尋引擎索引（noindex）。內容僅整理自常見問題與官網已公開的服務說明；標示為「TODO」的段落需由品牌方或法務補充後才能正式上線。", 10),
        _t(p, "svc-title", "服務條款・性質標題", "服務性質", 20),
        _t(p, "svc-body", "服務條款・性質內文", "銘印鑽石提供預約制、一對一顧問服務，將客戶提供的毛髮或骨灰樣本，於台灣在地實驗室培育為客製化紀念鑽石。", 21),
        _t(p, "order-title", "服務條款・訂購標題", "訂購流程", 30),
        _t(p, "order-body", "服務條款・訂購內文", "可透過線上客製試算頁面選擇品項、款式、金屬與鑽石規格並送出訂單，或透過官方 LINE 預約顧問一對一討論需求、確認樣本份量與報價。訂單細節以雙方確認之內容為準。", 31),
        _t(p, "price-title", "服務條款・價格標題", "價格", 40),
        _t(p, "price-body", "服務條款・價格內文", "依克拉數計算：0.10 克拉 NT$24,000 起、0.50 克拉 NT$98,000、1.00 克拉 NT$250,000（圓形明亮式切工／白鑽）。非圓形切工加價 10%，且需 0.30 克拉以上；彩鑽最低 0.30 克拉，報價依顏色稀有度而定；3.00 克拉以上請洽官方 LINE 專屬報價。飾品戒台費用另計，依款式與材質而定。完整價目請見價格總覽。", 41),
        _t(p, "time-title", "服務條款・時程標題", "製作時程", 50),
        _t(p, "time-body", "服務條款・時程內文", "自訂單確認且碳源送至實驗室之日起算，一般約 70～90 天；彩鑽因特殊工序可能需 90～120 天。每一顆鑽石的培育過程皆獨立進行。", 51),
        _t(p, "deposit-title", "服務條款・訂金標題", "訂金與尾款（公開營運說明）", 60),
        _t(p, "deposit-body", "服務條款・訂金內文", "依官網公開說明：DNA 鑽石系列需先支付 50% 訂金，待培育完成再支付尾款。取消與退款條件詳見退換貨與取消政策；其餘細節以訂單確認內容為準。", 61),
        _t(p, "cert-title", "服務條款・鑑定標題", "鑑定與保障", 70),
        _t(p, "cert-body", "服務條款・鑑定內文", "每顆鑽石皆附銘印保證卡；0.20 克拉以上可代送 GIA 或 IGI 國際鑑定機構出具證書（費用另計）。鑽石在送達客戶手上之前，享有全額保險保障。", 71),
        _t(p, "carat-title", "服務條款・誤差標題", "克拉誤差處理", 80),
        _t(p, "carat-body", "服務條款・誤差內文", "若成品大於訂購尺寸，無需支付額外費用；若成品小於訂購尺寸，將按比例退款。", 81),
        _t(p, "todo-title", "服務條款・TODO標題", "TODO：待補充事項（請法務／品牌方確認後移除本區塊）", 90),
        _t(p, "todo-li-1", "服務條款・TODO項目1", "TODO：責任限制與免責聲明", 91),
        _t(p, "todo-li-2", "服務條款・TODO項目2", "TODO：智慧財產權歸屬（含影音紀念盒內容、網站素材）", 92),
        _t(p, "todo-li-3", "服務條款・TODO項目3", "TODO：爭議處理方式與管轄法院", 93),
        _t(p, "todo-li-4", "服務條款・TODO項目4", "TODO：條款修改與生效方式", 94),
    ]


def _return_policy_slots() -> list[dict[str, Any]]:
    p = "/return-policy"
    return [
        _t(p, "hero-title", "退換貨・標題", "退換貨與取消政策", 1),
        _t(p, "crumb-current", "退換貨・麵包屑", "退換貨與取消政策", 2),
        _t(p, "hero-eyebrow", "退換貨・眉標", "RETURNS & CANCELLATION", 3),
        _t(p, "lead", "退換貨・引言", "感謝您選擇銘印鑽石 Imprint Diamond。我們為每位顧客打造專屬、獨一無二的鑽石飾品；為保障雙方權益，請詳閱以下退款與退貨政策。", 10),
        _t(p, "general-title", "退換貨・一般商品標題", "一般培育鑽石商品", 20),
        _t(p, "general-body", "退換貨・一般商品內文", "若您購買的是「一般培育鑽石」飾品（非個人化訂製），請於收到商品 7 天內（含例假日）主動與我們聯繫，並保持商品未使用、完整包裝與保證書。經檢查確認無損後，我們將依您原付款方式辦理退款或換貨。退回商品請保持完整包裝（含外盒、保證書、贈品與發票），否則恕無法受理。", 21),
        _t(p, "custom-title", "退換貨・客製商品標題", "DNA 鑽石及其他客製化商品", 30),
        _t(p, "custom-body", "退換貨・客製商品內文", "DNA 鑽石、寵物鑽石、結髮鑽石、生命鑽石等屬於個人化訂製服務，每一顆皆以您的毛髮、DNA 或指定材料專屬培育，具唯一性與不可重製性，因此一經製作或啟動生產流程後，恕無法取消、退貨或退款。我們會在製作前與您再次確認細節，並於培育過程中提供進度回報。", 31),
        _t(p, "deposit-title", "退換貨・訂金標題", "訂金與尾款", 40),
        _t(p, "deposit-body", "退換貨・訂金內文", "DNA 鑽石系列需先支付 50% 訂金以啟動製作／培育流程；鑽石完成後，我們將通知您檢視成品，再行支付尾款。若您因個人因素中途取消訂單，訂金將不予退還。", 41),
        _t(p, "carat-title", "退換貨・誤差標題", "克拉尺寸誤差", 50),
        _t(p, "carat-body", "退換貨・誤差內文", "若收到的銘印鑽石成品大於訂購尺寸，無需支付額外費用；若成品小於訂購尺寸，將按比例退款。例如：訂購 1.00 克拉白鑽（NT$250,000，誤差範圍 1.00～1.24 克拉），若收到 0.80 克拉則退還差價；若收到 1.45 克拉則無需加價。", 51),
        _t(p, "ship-title", "退換貨・運送標題", "運送瑕疵或損壞", 60),
        _t(p, "ship-body", "退換貨・運送內文", "鑽石在送達客戶手上之前，若發生任何意外，客戶可獲得全額保險保障。若商品於運送過程中發生瑕疵或損壞，請於收到後 3 日內與我們聯繫，我們將協助您辦理更換或修復。", 61),
        _t(p, "company-title", "退換貨・公司標題", "公司資訊", 70),
        _t(p, "company-body", "退換貨・公司內文", "公司抬頭：心之銘印鑽石有限公司　統一編號：45901568", 71),
        _t(p, "callout-bottom", "退換貨・聯絡提示", "如需辦理相關事宜，請透過官方 LINE 與專屬顧問聯繫。", 80),
    ]
