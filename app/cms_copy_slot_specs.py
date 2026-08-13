"""Editable text/button slot registry for marketing templates only."""

from __future__ import annotations

from typing import Any

EDITABLE_SITE_PAGES: tuple[dict[str, str], ...] = (
    {"route": "/", "title": "首頁", "content_tab": "page"},
    {"route": "/about", "title": "品牌故事", "content_tab": "page"},
    {"route": "/series", "title": "六大系列總覽", "content_tab": "page"},
    {"route": "/series/first-love/", "title": "滿月鑽石", "content_tab": "page"},
    {"route": "/series/pet/", "title": "寵物鑽石", "content_tab": "page"},
    {"route": "/series/love/", "title": "結髮鑽石", "content_tab": "page"},
    {"route": "/series/family/", "title": "全家福鑽石", "content_tab": "page"},
    {"route": "/series/heirloom/", "title": "生命鑽石", "content_tab": "page"},
    {"route": "/series/signature/", "title": "真我鑽石（Signature）", "content_tab": "page"},
    {"route": "/what-is-dna-diamond", "title": "DNA 鑽石的誕生", "content_tab": "page"},
    {"route": "/diamond-4c", "title": "鑽石 4C", "content_tab": "page"},
    {"route": "/lab-grown-diamond", "title": "什麼是培育鑽石", "content_tab": "page"},
    {"route": "/diamond-comparison", "title": "天然 vs 培育／DNA", "content_tab": "page"},
    {"route": "/contact", "title": "聯絡我們", "content_tab": "page"},
    {"route": "/faq", "title": "常見問題", "content_tab": "faq"},
    {"route": "/stories", "title": "客戶見證", "content_tab": "testimonials"},
    {"route": "/journal", "title": "品牌日誌", "content_tab": "page"},
    {"route": "/privacy", "title": "隱私權政策", "content_tab": "page"},
    {"route": "/terms", "title": "服務條款", "content_tab": "page"},
    {"route": "/return-policy", "title": "退換貨政策", "content_tab": "page"},
)


def _t(
    page: str,
    key: str,
    label: str,
    text: str,
    order: int,
    href: str = "",
    kind: str = "text",
) -> dict[str, Any]:
    return {
        "page_key": page,
        "slot_key": key,
        "kind": kind,
        "label": label,
        "default_text": text,
        "default_href": href,
        "sort_order": order,
    }


def _btn(page: str, key: str, label: str, text: str, href: str, order: int) -> dict[str, Any]:
    return _t(page, key, label, text, order, href=href, kind="button")


def copy_slot_specs() -> tuple[dict[str, Any], ...]:
    # Lazy imports: the sibling modules import _t/_btn from this module,
    # so importing them here (not at module top) avoids an import cycle.
    from app.cms_copy_slot_specs_education import education_slot_specs
    from app.cms_copy_slot_specs_legal import legal_slot_specs
    from app.cms_copy_slot_specs_series import series_slot_specs

    specs: list[dict[str, Any]] = []
    specs.extend(_home_slots())
    specs.extend(_about_slots())
    specs.extend(_contact_slots())
    specs.extend(education_slot_specs())
    specs.extend(legal_slot_specs())
    specs.extend(series_slot_specs())
    return tuple(specs)


def _home_slots() -> list[dict[str, Any]]:
    p = "/"
    return [
        _t(p, "hero-title", "首頁・主視覺標題", "把最深的情感，銘印成永恆", 1),
        _t(
            p,
            "hero-lead",
            "首頁・主視覺引言",
            "全台唯一擁有在地 DNA 鑽石培育實驗室的紀念鑽石品牌。萃取毛髮、骨灰中的元素，於台灣在地培育成專屬於您的紀念鑽石，附鑑定保障與專屬影音紀念盒。",
            2,
        ),
        _btn(p, "hero-cta", "首頁・主視覺主按鈕", "開始訂製", "/shop/calculator/", 3),
        _t(p, "poem-title", "首頁・詩文標題", "一段思念，如何成為永恆。", 11),
        _t(
            p,
            "poem-text",
            "首頁・詩文內文",
            "我們樂意傾聽您的故事。照片無法滿足思念、信物無法填補情感——為了讓思親更親，才有了 DNA 鑽石，煉製獨一無二的專屬寶物。DNA 鑽石與天然鑽石唯一的不同：天然鑽石來自地底挖採；DNA 鑽石來自您的摯愛。",
            12,
        ),
        _t(p, "poem-link-dna", "首頁・詩文連結・DNA文字", "了解 DNA 鑽石的誕生", 13),
        _btn(p, "poem-link-about", "首頁・詩文連結・品牌", "認識銘印鑽石 →", "/about", 14),
        _t(p, "dna-script", "首頁・DNA區塊眉標", "What is DNA Diamond", 20),
        _t(p, "dna-title", "首頁・DNA區塊標題", "什麼是 DNA 鑽石", 21),
        _t(
            p,
            "dna-lead",
            "首頁・DNA區塊引言",
            "無需漂洋過海——從萃取、培育到飾品設計，全程於台灣完成。想將專屬 DNA 鑽石製作成飾品、時時刻刻配戴？在地更能瞭解您的需求。專業認證與真品保障細節，請見鑽石知識頁。",
            22,
        ),
        _btn(p, "dna-cta-process", "首頁・DNA主按鈕", "了解完整製程與保障", "/what-is-dna-diamond", 23),
        _btn(p, "dna-cta-about", "首頁・DNA次按鈕", "為什麼選擇銘印 →", "/about", 24),
        _t(p, "series-script", "首頁・系列眉標", "Six Collections", 30),
        _t(p, "series-title", "首頁・系列標題", "選擇屬於您的系列", 31),
        _t(
            p,
            "series-lead",
            "首頁・系列引言",
            "每一種羈絆，都有屬於它的光。先了解六大系列；銘印鑽石以自己的髮絲，萃煉成獨一無二的鑽石，獻給值得被自己慶祝的此刻。",
            32,
        ),
        _t(p, "card-first-love-title", "首頁・滿月卡標題", "滿月鑽石", 33),
        _t(
            p,
            "card-first-love-text",
            "首頁・滿月卡說明",
            "以寶寶的胎髮，珍藏生命最初的印記，成為陪伴孩子一生的傳家珍藏。",
            34,
        ),
        _t(p, "card-pet-title", "首頁・寵物卡標題", "寵物鑽石", 35),
        _t(
            p,
            "card-pet-text",
            "首頁・寵物卡說明",
            "以毛孩的毛髮培育專屬鑽石，讓那份無條件的陪伴，以另一種形式延續。",
            36,
        ),
        _t(p, "card-love-title", "首頁・結髮卡標題", "結髮鑽石", 37),
        _t(
            p,
            "card-love-text",
            "首頁・結髮卡說明",
            "結髮為夫妻。以兩人的髮絲共同培育一顆鑽石，見證一生一次的誓約。",
            38,
        ),
        _t(p, "card-family-title", "首頁・全家福卡標題", "全家福鑽石", 39),
        _t(
            p,
            "card-family-text",
            "首頁・全家福卡說明",
            "集合全家人的髮絲，凝成一顆象徵家族連結的鑽石，讓家的記憶可以傳承。",
            40,
        ),
        _t(p, "card-heirloom-title", "首頁・生命卡標題", "生命鑽石", 41),
        _t(
            p,
            "card-heirloom-text",
            "首頁・生命卡說明",
            "回憶如汩汩泉湧，思念如雲煙繞樑——請永遠留在我身邊，讓記憶成為永恆的存在。",
            42,
        ),
        _t(p, "card-signature-title", "首頁・真我卡標題", "真我鑽石", 43),
        _t(
            p,
            "card-signature-text",
            "首頁・銘印卡說明",
            "以自己的髮絲，萃煉成獨一無二的鑽石，獻給值得被自己慶祝的此刻。",
            44,
        ),
        _btn(p, "series-cta", "首頁・系列總覽按鈕", "查看系列總覽", "/series", 45),
        _t(p, "wall-script", "首頁・見證眉標", "Testimonials", 50),
        _t(p, "wall-title", "首頁・見證標題", "他們選擇把思念，留成永恆", 51),
        _t(
            p,
            "wall-lead",
            "首頁・見證引言",
            "來自不同城市、不同故事的顧客，寫下他們與銘印鑽石相遇的片刻。",
            52,
        ),
        _btn(p, "wall-cta", "首頁・見證按鈕", "閱讀更多客戶見證 →", "/stories", 53),
        _t(p, "learn-script", "首頁・了解更多眉標", "Learn More", 60),
        _t(p, "learn-title", "首頁・了解更多標題", "想多了解一點？", 61),
        _t(
            p,
            "learn-lead",
            "首頁・了解更多引言",
            "製程、價格、故事與常見問題——依您需要的步調，慢慢閱讀。",
            62,
        ),
        _t(p, "learn-dna-title", "首頁・學習卡・DNA標題", "什麼是 DNA 鑽石", 63),
        _t(p, "learn-dna-text", "首頁・學習卡・DNA說明", "從樣本萃取到鑑定交付，完整六步驟與四大保障說明。", 64),
        _t(p, "learn-price-title", "首頁・學習卡・價格標題", "價格試算", 65),
        _t(p, "learn-price-text", "首頁・學習卡・價格說明", "依克拉數、切工、彩鑽與飾品款式，線上即時試算參考價格。", 66),
        _t(p, "learn-stories-title", "首頁・學習卡・見證標題", "客戶見證", 67),
        _t(p, "learn-stories-text", "首頁・學習卡・見證說明", "寵物、生命、結髮、滿月——每一顆鑽石背後的情感故事。", 68),
        _t(p, "learn-faq-title", "首頁・學習卡・FAQ標題", "常見問題", 69),
        _t(p, "learn-faq-text", "首頁・學習卡・FAQ說明", "樣本份量、製作時間、鑑定證書與如何開始，一次解答。", 70),
        _t(p, "faq-script", "首頁・FAQ眉標", "FAQ", 80),
        _t(p, "faq-title", "首頁・FAQ標題", "常見問題", 81),
        _btn(p, "faq-more", "首頁・FAQ更多", "查看全部常見問題", "/faq", 82),
        _t(p, "cta-script", "首頁・頁尾眉標", "Join Us", 90),
        _t(p, "cta-title", "首頁・頁尾標題", "我們樂意傾聽您的故事", 91),
        _t(
            p,
            "cta-lead",
            "首頁・頁尾引言",
            "訂製一顆紀念鑽石，往往需要時間沉澱。加入官方 LINE，我們會與您分享培育故事與最新價目——在您準備好的那一天，我們都在。",
            92,
        ),
        _btn(p, "cta-line", "首頁・頁尾 LINE", "加入官方 LINE 好友", "https://lin.ee/ktVBtmx", 93),
        _t(p, "cta-hint", "首頁・頁尾提示", "不會頻繁打擾，隨時可以取消", 94),
    ]


def _about_slots() -> list[dict[str, Any]]:
    p = "/about"
    return [
        _t(p, "hero-overline", "品牌故事・眉標", "銘印鑽石 IMPRINT DIAMOND · TAIWAN", 1),
        _t(p, "hero-title", "品牌故事・主標", "銘印鑽石｜我們樂意傾聽您的故事", 2),
        _t(
            p,
            "hero-lead",
            "品牌故事・引言",
            "銘印鑽石（心之銘印鑽石有限公司）陪伴您走過一段無法催促的決定。我們存在，是為了讓思念可以被好好安放——成為您能觸碰、能珍藏的形式，而不帶任何壓力。門市位於新北市三重區，採預約制。",
            3,
        ),
        _btn(p, "hero-scroll", "品牌故事・閱讀承諾", "閱讀我們的承諾", "#story-begins", 4),
        _t(p, "belief-title", "品牌故事・信念標題", "我們樂意傾聽您的故事", 10),
        _t(
            p,
            "belief-p1",
            "品牌故事・信念段落一",
            "在這個充滿快速變化的社會中，人與人之間是否有許多情感都被忽略了？我們相信，照片無法滿足思念、信物無法填補情感——為了讓思親更親，才會有銘印鑽石來煉製獨一無二的 DNA 專屬貼身寶物；難忘時刻所化成的寶石，便是所愛的見證。",
            11,
        ),
        _t(
            p,
            "belief-p2",
            "品牌故事・信念段落二",
            "銘印鑽石與天然鑽石唯一的不同：天然鑽石來自地底挖採；銘印鑽石來自您的摯愛。我們以現代高科技與高工藝，模擬大自然鑽石生長環境，將碳化後的毛髮銘印封存於鑽石之中，以鑽石形式乘載記憶、留下感動，並堅持 4C 高品質原則。",
            12,
        ),
        _t(p, "local-title", "品牌故事・在地標題", "留在離您最近的地方", 20),
        _t(
            p,
            "local-p1",
            "品牌故事・在地段落一",
            "您交付給我們的，是無法重來的珍貴樣本。距離越遠、流程越不透明，不安就越難消散——所以我們選擇把整段旅程留在台灣，讓您始終知道記憶此刻身在何處。",
            21,
        ),
        _t(p, "time-title", "品牌故事・步調標題", "慢慢決定，也沒關係", 30),
        _t(
            p,
            "time-p1",
            "品牌故事・步調段落一",
            "訂製一顆紀念鑽石，往往不是一次衝動的消費，而是一個需要時間沉澱的決定。我們見過猶豫兩年才下定決心的客人，也理解每一段考慮期背後，都是還沒準備好放下、或還沒找到合適時機的心情。",
            31,
        ),
        _t(p, "care-title", "品牌故事・慎重標題", "每一顆，都被慎重對待", 40),
        _t(
            p,
            "care-lead",
            "品牌故事・慎重引言",
            "從樣本進入實驗室的那一刻，到成品被交回您手中——每一位客戶、每一段旅程，都以尊嚴與專屬的方式被對待。",
            41,
        ),
        _t(p, "care-1-title", "品牌故事・託付卡標題", "專屬託付", 42),
        _t(p, "care-1-body", "品牌故事・託付卡內文", "每一份樣本獨立處理，不混 batch、不代用。了解完整製程 →", 43),
        _t(p, "care-2-title", "品牌故事・透明卡標題", "透明可見", 44),
        _t(p, "care-2-body", "品牌故事・透明卡內文", "關鍵階段可追蹤；歡迎預約見證生長。查詢訂製進度 →", 45),
        _t(p, "care-3-title", "品牌故事・交付卡標題", "完整交付", 46),
        _t(p, "care-3-body", "品牌故事・交付卡內文", "鑽石連同紀念與證明一併交還，讓故事被保存。鑑定與保障說明 →", 47),
        _t(p, "next-title", "品牌故事・收尾標題", "不需要急著決定。準備好的那一天，我們都在。", 50),
        _t(
            p,
            "next-lead",
            "品牌故事・收尾引言",
            "您可以先了解製作方式、瀏覽訂製系列，或與顧問聊聊心裡的想法。",
            51,
        ),
        _btn(p, "cta-calculator", "品牌故事・試算按鈕", "開始客製試算", "/shop/calculator/", 52),
        _btn(p, "cta-dna", "品牌故事・DNA按鈕", "了解 DNA 鑽石的誕生", "/what-is-dna-diamond", 53),
    ]


def _contact_slots() -> list[dict[str, Any]]:
    p = "/contact"
    return [
        _t(p, "card-title", "聯絡・卡片標題", "聯絡銘印鑽石｜三重門市", 1),
        _t(
            p,
            "card-lead",
            "聯絡・卡片說明",
            "銘印鑽石（IMPRINT DIAMOND／心之銘印鑽石有限公司）門市位於新北市三重區福德南路 43 號 1 樓，採預約制；電話 02-2977-0268。歡迎預約來店，親眼見證鑽石生長——可先到線上客製試算，或了解結髮鑽石／訂製婚戒後再蒞臨。",
            2,
        ),
        _btn(p, "card-line", "聯絡・LINE按鈕", "加入官方 LINE 諮詢", "https://lin.ee/ktVBtmx", 3),
        _t(p, "info-title", "聯絡・聯絡方式標題", "聯絡方式", 4),
        _t(p, "info-k-address", "聯絡・門市標籤", "門市", 5),
        _btn(p, "info-address", "聯絡・門市地址", "新北市三重區福德南路 43 號 1 樓（預約制，請先聯繫再蒞臨）", "https://maps.app.goo.gl/3Fed2YEpWa8LxQoy9", 6),
        _t(p, "info-k-phone", "聯絡・電話標籤", "電話", 7),
        _t(p, "info-phone", "聯絡・電話號碼", "02-2977-0268", 8),
        _t(p, "info-k-hours", "聯絡・時段標籤", "預約時段", 9),
        _t(p, "form-title", "聯絡・表單標題", "線上留言諮詢", 10),
        _t(
            p,
            "form-lead",
            "聯絡・表單引言",
            "不方便加 LINE 也沒關係，留下您的聯絡方式、需求與希望預約時段（上午 10:00–12:00 或下午 1:30–6:30），顧問會盡快與您聯繫。",
            11,
        ),
        _t(p, "info-hours", "聯絡・預約時段", "上午 10:00～12:00／下午 1:30～6:30（預約制）", 12),
        _t(p, "info-k-line", "聯絡・LINE標籤", "LINE", 13),
        _btn(p, "info-line", "聯絡・LINE帳號", "@imprintdiamond 官方帳號", "https://lin.ee/ktVBtmx", 14),
        _t(p, "info-k-fb", "聯絡・FB標籤", "Facebook", 15),
        _btn(p, "info-fb", "聯絡・FB專頁", "Imprint Diamond 銘印鑽石", "https://www.facebook.com/Imprintdiamond/", 16),
        _t(p, "scroll-hint", "聯絡・捲動提示", "↓ 線上留言諮詢", 17),
        _t(p, "reach-muted", "聯絡・直接聯繫提示", "也可以直接聯繫", 18),
        _t(p, "reach-or", "聯絡・LINE分隔字", "官方 LINE", 19),
        _t(p, "form-muted", "聯絡・表單提示", "留下簡短訊息", 20),
        _t(p, "form-label-name", "聯絡・姓名標籤", "姓名 *", 21),
        _t(p, "form-label-phone", "聯絡・電話標籤", "電話 *", 22),
        _t(p, "form-label-email", "聯絡・Email標籤", "Email", 23),
        _t(p, "form-label-slot", "聯絡・時段標籤", "希望預約時段", 24),
        _t(p, "form-opt-1", "聯絡・時段選項1", "尚未決定／稍後再約", 25),
        _t(p, "form-opt-2", "聯絡・時段選項2", "上午 10:00～12:00", 26),
        _t(p, "form-opt-3", "聯絡・時段選項3", "下午 1:30～6:30", 27),
        _t(p, "form-label-message", "聯絡・需求標籤", "您的需求 *", 28),
        _btn(p, "form-submit", "聯絡・送出按鈕", "送出留言", "", 29),
    ]


