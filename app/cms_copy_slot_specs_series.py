"""Series overview (/series) and series detail fragment slot specs.

Split from cms_copy_slot_specs.py to keep modules under 500 lines.
Data-driven: per-series copy lives in the tables below and is expanded
into slots by the generator functions.
"""

from __future__ import annotations

from typing import Any

from app.cms_copy_slot_specs import _btn, _t

_LINE_URL = "https://lin.ee/ktVBtmx"
_CALC_URL = "/shop/calculator/?category=diamond"
_CAPTURE_BODY = (
    "訂製一顆紀念鑽石，往往需要時間沉澱。"
    "加入官方 LINE，我們會不定期與您分享鑽石的培育故事、"
    "客人的紀念故事與最新價目。"
    "在您準備好的那一天，我們都在。"
)

# /series overview: per-series detail card + quick card copy (from series.html).
_OVERVIEW_CARDS: tuple[dict[str, Any], ...] = (
    {
        "slug": "first-love", "name": "滿月鑽石", "en": "First Love",
        "p1": "以寶寶的胎髮培育專屬鑽石，珍藏生命最初的印記。胎髮通常只剃一次：與其收進盒子裡漸漸泛黃，不如讓它凝成一顆會發光的鑽石，陪伴孩子長大、傳承給下一代。",
        "p2": "可鑲嵌為項鍊、戒指或手鍊；許多家庭會在滿月或周歲時開始規劃，實際訂製時間依您準備好的步調而定。",
        "facts": ("樣本：寶寶胎髮", "適合：滿月・周歲紀念", "週期：約 70～90 天"),
        "more": "了解滿月鑽石", "more_href": "/series/first-love/",
        "calc": "線上試算", "calc_href": _CALC_URL,
        "quick_text": "以寶寶的胎髮，珍藏生命最初的印記，成為陪伴孩子一生的傳家珍藏。",
    },
    {
        "slug": "pet", "name": "寵物鑽石", "en": "Companion",
        "p1": "以毛孩的毛髮培育專屬鑽石，讓那份無條件的陪伴，以另一種形式延續。無論牠還在身邊，或已經離開，這顆鑽石都是飼主與毛孩之間獨一無二的連結。",
        "p2": "毛髮約一顆雞蛋大小即可訂製；若毛量不足，請先透過官方 LINE 與顧問討論可行方案，不需要先寄送樣本。",
        "facts": ("樣本：寵物毛髮", "適合：陪伴紀念・離世追思", "週期：約 70～90 天"),
        "more": "了解寵物鑽石", "more_href": "/series/pet/",
        "calc": "線上試算", "calc_href": _CALC_URL,
        "quick_text": "以毛孩的毛髮培育專屬鑽石，讓那份無條件的陪伴，以另一種形式延續。",
    },
    {
        "slug": "love", "name": "結髮鑽石", "en": "Love",
        "p1": "結髮為夫妻：以兩人的髮絲共同培育一顆鑽石，見證一生一次的誓約。常見於求婚戒、結婚對戒或週年紀念，讓這顆鑽石同時承載兩個人的 DNA，是專屬於你們兩人的信物。",
        "p2": "可選擇單鑽、對戒或項鍊等多種形式；克拉數、形狀與金屬成色皆可在線上試算後，由專屬顧問與您一對一確認。",
        "facts": ("樣本：兩人髮絲", "適合：求婚・婚禮・週年", "週期：約 70～90 天"),
        "more": "了解結髮鑽石", "more_href": "/series/love/",
        "calc": "線上試算", "calc_href": _CALC_URL,
        "quick_text": "結髮為夫妻。以兩人的髮絲共同培育一顆鑽石，見證一生一次的誓約。",
    },
    {
        "slug": "family", "name": "全家福鑽石", "en": "Family",
        "p1": "集合全家人的髮絲，凝成一顆象徵家族連結的鑽石。父母、孩子、甚至祖父母：每一縷髮絲都代表一位家人，共同組成這顆獨一無二的家族之鑽。",
        "p2": "適合作為三代同堂的紀念、搬家或重要家庭里程碑的珍藏，也可在節日時開始規劃，讓家的記憶以可傳承的形式延續。",
        "facts": ("樣本：全家人髮絲", "適合：家族傳承・里程碑", "週期：約 70～90 天"),
        "more": "了解全家福鑽石", "more_href": "/series/family/",
        "calc": "線上試算", "calc_href": _CALC_URL,
        "quick_text": "集合全家人的髮絲，凝成一顆象徵家族連結的鑽石，讓家的記憶可以傳承。",
    },
    {
        "slug": "heirloom", "name": "生命鑽石", "en": "Heirloom",
        "p1": "回憶如汩汩泉湧，思念如雲煙繞樑。請永遠留在我身邊，讓記憶成為永恆的存在。以摯愛親人的毛髮或骨灰，培育成專屬紀念鑽石，讓思念有永恆的形狀。",
        "p2": "樣本全程於台灣在地實驗室處理，不需國際運送；0.20 克拉以上可代送 GIA 或 IGI 鑑定，讓這份珍藏在未來傳承時，有正式的身分證明。",
        "facts": ("樣本：毛髮或骨灰", "適合：追思・永恆陪伴", "週期：約 70～90 天"),
        "more": "了解生命鑽石", "more_href": "/series/heirloom/",
        "calc": "線上試算", "calc_href": _CALC_URL,
        "quick_text": "回憶如汩汩泉湧，思念如雲煙繞樑。請永遠留在我身邊，讓記憶成為永恆的存在。",
    },
    {
        "slug": "signature", "name": "真我鑽石", "en": "Signature",
        "p1": "以自己的髮絲，萃煉成獨一無二的鑽石，獻給值得被自己慶祝的此刻。",
        "p2": "可先以線上試算規劃規格，或從求婚與結髮飾品入口開始；正式細節仍由專屬顧問與您一對一確認。DNA 鑽石系列需先支付 50% 訂金，待培育完成再支付尾款。",
        "facts": ("樣本：依故事而定", "適合：為自己慶祝・專屬訂製", "週期：約 70～90 天"),
        "more": "了解真我鑽石", "more_href": "/series/signature/",
        "calc": "求婚與結髮", "calc_href": "/jewelry/engagement/",
        "quick_text": "以自己的髮絲，萃煉成獨一無二的鑽石，獻給值得被自己慶祝的此刻。",
    },
)

_GUIDE_ROWS: tuple[tuple[str, str], ...] = (
    ("寶寶滿月或周歲，想留住第一縷胎髮", "滿月鑽石 →"),
    ("毛孩陪伴多年，想讓牠以另一種形式留在身邊", "寵物鑽石 →"),
    ("求婚、婚禮或週年，想以兩人髮絲見證誓約", "結髮鑽石 →"),
    ("想集合全家人的髮絲，凝成可以傳承的家族珍藏", "全家福鑽石 →"),
    ("摯愛親人已離開，想讓思念有永恆的形狀", "生命鑽石 →"),
    ("以自己的髮絲，為值得慶祝的此刻打造專屬鑽石", "真我鑽石 →"),
)

# Series detail fragments (content/site/fragments/series/*.html).
# hero_title/hero_lead keep their ORIGINAL seeded defaults verbatim — the live
# DB already serves those values; changing them would alter unedited pages.
_DETAIL_PAGES: tuple[dict[str, Any], ...] = (
    {
        "route": "/series/first-love/", "name": "滿月鑽石",
        "hero_title": "滿月鑽石－珍藏生命最初的印記",
        "hero_lead": "以寶寶的胎髮，在台灣在地實驗室培育成專屬鑽石。從滿月剃髮的那一刻，到孩子長大成人，這顆鑽石始終記得最初的模樣。",
        "crumb": "滿月鑽石", "eyebrow": "FIRST LOVE・滿月紀念",
        "intro_eyebrow": "為什麼選擇滿月鑽石", "intro_title": "迎接親愛寶貝，留住最初的純粹",
        "intro_paras": (
            "滿月剃髮留下的胎髮，常被稱為生命最初的印記。滿月鑽石系列即以胎髮培育的初生紀念鑽石：保存生命最初的純粹與溫柔，將那份第一次的感動，留存在未來每一天。",
            "寶寶的胎髮通常只剃一次。這份柔軟的髮絲，藏著孩子出生時最原始的印記：與其收進盒子裡漸漸泛黃，不如讓它凝成一顆會發光的鑽石，注入爹地和媽咪的無限關愛。",
            "毛髮份量約一顆雞蛋大小即可訂製；若剃髮量不足，歡迎先透過官方 LINE 與顧問確認，不必先寄送樣本。全程於台灣在地實驗室完成，單一客戶、單一培育流程，約 70～90 天交付，連同銘印保證卡與專屬影音紀念盒一併送到您手上。DNA 鑽石系列需先支付 50% 訂金，待培育完成再支付尾款。",
        ),
        "related": (
            ("DNA 鑽石怎麼做的？", "/what-is-dna-diamond"),
            ("查看價格總覽", "/price"),
            ("常見問題", "/faq"),
            ("六大系列總覽", "/series"),
        ),
        "faqs": (
            ("滿月鑽石和初生鑽石是同一系列嗎？", "滿月鑽石系列即以寶寶胎髮培育的初生紀念鑽石，珍藏生命最初印記；名稱因紀念時機（滿月剃髮）而常用「滿月鑽石」。"),
            ("胎髮要準備多少？", "約一顆雞蛋大小即可。若剃髮量不足，請先透過官方 LINE 與顧問確認，不必先寄送樣本。"),
            ("可以做成項鍊嗎？", "可以。完成後可鑲嵌為項鍊、戒指等，成為陪伴孩子成長的傳家珍藏。"),
            ("製作需要多久？", "全程台灣在地實驗室，約 70～90 天交付，附銘印保證卡與專屬影音紀念盒。"),
        ),
        "calc_title": "為滿月鑽石，線上試算規格",
        "calc_lead": "為寶寶胎髮鑽石選擇克拉數、顏色與刻字。正式規格仍由專屬顧問與您一對一確認。",
    },
    {
        "route": "/series/pet/", "name": "寵物鑽石",
        "hero_title": "寵物鑽石－讓陪伴延續成光",
        "hero_lead": "以毛孩的毛髮，在台灣在地實驗室培育成專屬鑽石。牠不在身邊了，但那份無條件的陪伴，可以換一種方式繼續跟著您。",
        "crumb": "寵物鑽石", "eyebrow": "COMPANION・毛孩陪伴",
        "intro_eyebrow": "為什麼選擇寵物鑽石", "intro_title": "永遠不離不棄，愛如家人",
        "intro_paras": (
            "毛孩子不管在哪裡，我們永遠不離不棄。寵物是我們最忠誠的伙伴與朋友：愛如家人、寶貝珍惜。即使離開，陪伴也從未消失；寵物鑽石不是要您忘記悲傷，而是給這份感情一個看得見、摸得到的去處。",
            "毛髮份量約一顆雞蛋大小即可訂製；若毛量不足，請先透過官方 LINE 與顧問討論。全程於台灣在地實驗室完成，單一客戶、單一培育流程，約 70～90 天交付，連同銘印保證卡與專屬影音紀念盒一併送到您手上。DNA 鑽石系列需先支付 50% 訂金，待培育完成再支付尾款。",
        ),
        "related": (
            ("寵物骨灰也能做成生命鑽石（骨灰鑽石）", "/series/heirloom/"),
            ("DNA 鑽石怎麼做的？", "/what-is-dna-diamond"),
            ("查看價格總覽", "/price"),
            ("常見問題", "/faq"),
        ),
        "faqs": (
            ("寵物鑽石需要準備多少毛髮？", "毛髮約需一顆雞蛋大小（或養樂多瓶約 8 分滿）即可訂製寵物鑽石。若毛量不足，請先透過官方 LINE 與顧問確認，不必先寄送樣本。"),
            ("寵物毛髮鑽石和寵物紀念品有何不同？", "寵物鑽石是以毛孩毛髮在台灣培育成真實鑽石，可鑲嵌為飾品；也常作為可傳承的寵物紀念品。成品附銘印保證卡與專屬影音紀念盒。"),
            ("寵物骨灰可以做成鑽石嗎？", "可以。若您手邊是寵物骨灰，請改看生命鑽石（骨灰鑽石）系列；顧問會依樣本類型協助評估。"),
            ("製作需要多久？", "全程於台灣在地實驗室完成，約 70～90 天交付，單一客戶、單一培育流程。"),
        ),
        "calc_title": "為寵物鑽石，線上試算規格",
        "calc_lead": "為毛孩選擇克拉數、顏色與刻字。正式規格仍由專屬顧問與您一對一確認。",
    },
    {
        "route": "/series/love/", "name": "結髮鑽石",
        "hero_title": "結髮鑽石－把兩人，凝成一顆鑽石",
        "hero_lead": "結髮為夫妻。以兩人的髮絲共同培育一顆鑽石，見證一生一次的誓約——這顆鑽石裡，有你也有我。",
        "crumb": "結髮鑽石", "eyebrow": "LOVE・愛情紀念",
        "intro_eyebrow": "為什麼選擇結髮鑽石", "intro_title": "一輩子的誓約，用一顆鑽石記住",
        "intro_paras": (
            "「結髮為夫妻，恩愛兩不疑」：結髮鑽石取自兩人的髮絲，共同培育成一顆鑽石，象徵從今以後，這段關係裡永遠有彼此的存在。",
            "很適合作為求婚戒、對戒的主石，也有新人選擇在結婚週年時訂製，把「走到現在」這件事也一起銘記下來。",
            "毛髮份量兩人合計約一顆雞蛋大小即可訂製；若不確定份量，請先透過官方 LINE 與顧問確認。全程於台灣在地實驗室完成，約 70～90 天交付。",
            "全程於台灣在地實驗室完成，單一客戶、單一培育流程，約 70～90 天交付，連同銘印保證卡與專屬影音紀念盒一併送到您手上。",
        ),
        "related": (
            ("求婚／結髮入口", "/jewelry/engagement/"),
            ("客製化鑽石戒指／婚戒款式", "/jewelry/rings/"),
            ("線上客製試算", "/shop/calculator/"),
            ("門市預約聯絡", "/contact"),
            ("DNA 鑽石怎麼做的？", "/what-is-dna-diamond"),
            ("常見問題", "/faq"),
        ),
        "faqs": (
            ("結髮鑽石適合做婚戒嗎？", "很適合作為培育鑽石婚戒或對戒主石。兩人髮絲共同培育一顆鑽石後，可至戒指系列選戒台，或先到線上試算規格。"),
            ("兩人需要準備多少頭髮？", "兩人合計約一顆雞蛋大小即可。若不確定份量，請先透過官方 LINE 與顧問確認。"),
            ("可以只訂鑽石再鑲戒嗎？", "可以。鑽石完成後可鑲嵌為戒指、項鍊等；戒台材質可選 18K／14K／9K 金或 PT950 鉑金。"),
            ("可以預約看款嗎？", "可以。門市在新北市三重區福德南路 43 號 1 樓（預約制），也可先 LINE 預約，或至聯絡我們留言。"),
        ),
        "calc_title": "為結髮鑽石，線上試算規格",
        "calc_lead": "為兩人共同培育的鑽石選擇規格。正式規格仍由專屬顧問與您一對一確認。",
    },
    {
        "route": "/series/family/", "name": "全家福鑽石",
        "hero_title": "全家福鑽石－讓家的記憶，可以傳承",
        "hero_lead": "集合全家人的髮絲，凝成一顆象徵家族連結的鑽石，讓家的記憶可以傳承。",
        "crumb": "全家福鑽石", "eyebrow": "FAMILY・家族傳承",
        "intro_eyebrow": "為什麼選擇全家福鑽石", "intro_title": "把「一家人」，變成傳家珍藏",
        "intro_paras": (
            "全家福鑽石集合每一位家人的髮絲，共同培育成一顆鑽石：它不屬於某一個人，而是屬於「這個家」，很適合作為家族傳承的信物，代代相傳。",
            "許多家庭選擇在長輩生日、結婚紀念日或家族團聚時訂製，把「我們曾經在一起」的證明，留成看得見的珍藏。",
            "全家人的毛髮份量合計約一顆雞蛋大小即可訂製；若人數較多、份量不確定，請先透過官方 LINE 與顧問討論。全程於台灣在地實驗室完成，約 70～90 天交付。",
            "全程於台灣在地實驗室完成，單一客戶、單一培育流程，約 70～90 天交付，連同銘印保證卡與專屬影音紀念盒一併送到您手上。",
        ),
        "related": (
            ("DNA 鑽石怎麼做的？", "/what-is-dna-diamond"),
            ("查看價格總覽", "/price"),
            ("常見問題", "/faq"),
            ("六大系列總覽", "/series"),
        ),
        "faqs": (
            ("全家福鑽石要收集哪些人的頭髮？", "可集合每一位家人的髮絲共同培育；合計約一顆雞蛋大小即可。人數較多時，請先 LINE 與顧問討論比例與份量。"),
            ("適合什麼時候訂製？", "常見於長輩生日、結婚紀念或家族團聚時訂製，把「一家人」留成可傳承的紀念鑽石。"),
            ("可以只做一顆給全家族嗎？", "可以。全家福鑽石通常做成一顆共享的家族信物，也可依需求討論顆數與鑲嵌方式。"),
            ("製作需要多久？", "全程台灣在地實驗室，約 70～90 天交付，附銘印保證卡與專屬影音紀念盒。"),
        ),
        "calc_title": "為全家福鑽石，線上試算規格",
        "calc_lead": "為全家福鑽石選擇克拉數、顆數與刻字。正式規格仍由專屬顧問與您一對一確認。",
    },
    {
        "route": "/series/heirloom/", "name": "生命鑽石",
        "hero_title": "生命鑽石－讓思念，有永恆的形狀",
        "hero_lead": "以摯愛親人的毛髮或骨灰，讓思念有永恆的形狀，靜靜陪在您身邊。",
        "crumb": "生命鑽石", "eyebrow": "HEIRLOOM・傳世典藏",
        "intro_eyebrow": "為什麼選擇生命鑽石", "intro_title": "回憶如汩汩泉湧，思念如雲煙繞樑",
        "intro_paras": (
            "請永遠留在我身邊，讓記憶成為永恆的存在。訂製一顆生命鑽石，往往需要時間與信任。猶豫很正常。生命鑽石取自親人的毛髮或骨灰，讓思念從抽象的情緒，變成一顆可以隨身攜帶的存在。",
            "樣本全程於台灣在地實驗室處理，不需經歷國際運送；0.20 克拉以上可代送 GIA 或 IGI 國際鑑定，讓這份珍藏在未來傳承時，有正式的身分證明。",
            "毛髮約需一顆雞蛋大小，骨灰約需 3 至 5 公克；若不確定份量是否足夠，請先透過官方 LINE 與顧問確認。單一客戶、單一培育流程，約 70～90 天交付，連同銘印保證卡與專屬影音紀念盒一併送到您手上。DNA 鑽石系列需先支付 50% 訂金，待培育完成再支付尾款。",
        ),
        "related": (
            ("毛孩毛髮紀念：寵物鑽石", "/series/pet/"),
            ("DNA 鑽石怎麼做的？", "/what-is-dna-diamond"),
            ("查看價格總覽", "/price"),
            ("常見問題", "/faq"),
        ),
        "faqs": (
            ("什麼是骨灰鑽石／生命鑽石？", "生命鑽石以親人毛髮或骨灰培育而成；骨灰約需 3 至 5 公克、毛髮約一顆雞蛋大小。樣本在台灣在地實驗室處理，不送海外。"),
            ("骨灰份量不夠怎麼辦？", "若不確定份量是否足夠，請先透過官方 LINE 與顧問確認，不需要先寄送樣本。顧問會依實際狀況給建議。"),
            ("有國際鑑定嗎？", "每顆附銘印保證卡；0.20 克拉以上可代送 GIA 或 IGI 國際鑑定（費用另計），讓珍藏在傳承時有正式身分證明。"),
            ("寵物骨灰也能做嗎？", "可以。寵物骨灰同樣可走生命鑽石流程；若以毛髮紀念毛孩，也可參考寵物鑽石系列。"),
        ),
        "calc_title": "為生命鑽石，線上試算規格",
        "calc_lead": "為生命紀念鑽石選擇克拉數、顏色與刻字。正式規格仍由專屬顧問與您一對一確認。",
    },
    {
        "route": "/series/signature/", "name": "真我鑽石",
        "hero_title": "真我鑽石｜為自己留下此刻",
        "hero_lead": "以自己的髮絲，萃煉成獨一無二的鑽石，獻給值得被自己慶祝的此刻。",
        "crumb": "真我鑽石", "eyebrow": "SIGNATURE・銘印專屬",
        "intro_eyebrow": "為什麼選擇真我鑽石", "intro_title": "讓每一個決定，都只屬於您的故事",
        "intro_paras": (
            "真我鑽石（Signature），從自己的髮絲出發，將此刻對自己的肯定與慶祝，萃煉成一顆獨一無二的鑽石。它不需要等待某個特別的人，這一次，主角就是自己。",
            "您可以先以線上試算規劃克拉數、形狀與材質，再由專屬顧問一對一確認樣本、預算與鑲嵌方式。",
            "毛髮份量約一顆雞蛋大小即可訂製；若不確定份量，請先透過官方 LINE 與顧問確認。全程於台灣在地實驗室完成，約 70～90 天交付。",
            "全程於台灣在地實驗室完成，單一客戶、單一培育流程，約 70～90 天交付，連同銘印保證卡與專屬影音紀念盒一併送到您手上。",
        ),
        "related": (
            ("線上客製試算", _CALC_URL),
            ("求婚／結髮入口", "/jewelry/engagement/"),
            ("門市預約聯絡", "/contact"),
            ("DNA 鑽石怎麼做的？", "/what-is-dna-diamond"),
            ("常見問題", "/faq"),
        ),
        "faqs": (
            ("真我鑽石可以使用哪些樣本？", "可依您的故事討論毛髮，正式評估由專屬顧問協助。若不確定份量，請先透過官方 LINE 與顧問確認。"),
            ("可以自己決定鑽石與飾品款式嗎？", "可以。克拉數、形狀、顏色、金屬材質與鑲嵌形式，都會依您的故事與預算一對一確認；也可先到線上試算規格。"),
            ("可以只訂鑽石再鑲飾嗎？", "可以。鑽石完成後可鑲嵌為戒指、項鍊等；戒台與鍊款材質可選 18K／14K／9K 金或 PT950 鉑金。"),
            ("製作需要多久？", "全程於台灣在地實驗室完成，通常約 70～90 天交付，並附銘印保證卡與專屬影音紀念盒。"),
        ),
        "calc_title": "為真我鑽石，線上試算規格",
        "calc_lead": "為自己選擇克拉數、顏色與刻字。正式規格仍由專屬顧問與您一對一確認。",
    },
)


def series_slot_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    specs.extend(_series_overview_slots())
    specs.extend(_series_detail_slots())
    return specs


def _series_overview_slots() -> list[dict[str, Any]]:
    p = "/series"
    out: list[dict[str, Any]] = [
        _t(p, "hero-eyebrow", "系列總覽・眉標", "Six Collections", 1),
        _t(p, "hero-title", "系列總覽・主標", "選擇屬於您的系列", 2),
        _t(
            p,
            "hero-lead",
            "系列總覽・引言",
            "銘印鑽石依不同的羈絆與生命階段，整理成六個系列；銘印鑽石以自己的髮絲，萃煉成獨一無二的鑽石，獻給值得被自己慶祝的此刻。每一顆鑽石都從您珍視的樣本中真實培育而成——先了解各系列意義，再選擇克拉數、形狀與飾品款式。",
            3,
        ),
        _t(p, "crumb-current", "系列總覽・麵包屑", "六大系列", 4),
        _t(p, "intro-title", "系列總覽・介紹標題", "六大系列，對應六種珍視的連結", 10),
        _t(
            p,
            "intro-body",
            "系列總覽・介紹內文",
            "無論是寶寶的第一縷胎髮、毛孩多年的陪伴、伴侶之間的誓約、全家人的髮絲，或是已離開的摯愛——我們以相同的在地培育技術，為不同故事找到最貼切的起點。系列之間沒有優劣，只有「哪一種連結，此刻最貼近您的心」。銘印鑽石則以自己的髮絲，萃煉成獨一無二的鑽石，獻給值得被自己慶祝的此刻。",
            11,
        ),
        _t(p, "guide-title", "系列總覽・導引標題", "不確定從哪個系列開始？", 20),
        _t(p, "guide-lead", "系列總覽・導引引言", "依您目前的狀況快速對照——點選即可進入該系列詳細介紹。", 21),
        _t(p, "details-title", "系列總覽・詳情標題", "各系列詳細介紹", 30),
        _btn(p, "cta-calculator", "系列總覽・試算按鈕", "開始客製試算", "/shop/calculator/", 90),
    ]
    for i, (situation, series_label) in enumerate(_GUIDE_ROWS, start=1):
        out.append(_t(p, f"guide-{i}-situation", f"系列總覽・導引{i}情境", situation, 21 + i * 2))
        out.append(_t(p, f"guide-{i}-series", f"系列總覽・導引{i}系列", series_label, 22 + i * 2))
    pillars = (
        ("sample", "Sample", "樣本來源", "胎髮、髮絲、寵物毛髮或骨灰：依系列不同而異。毛髮約一顆雞蛋大小；骨灰約 3～5 公克。份量不足時，可先透過 LINE 與顧問確認。"),
        ("process", "Process", "培育方式", "全台唯一在地 DNA 鑽石實驗室，單一客戶、單一流程，樣本不送海外。從萃取到晶化約需 70～90 天，歡迎預約蒞臨見證。"),
        ("delivery", "Delivery", "交付內容", "裸鑽或鑲嵌飾品、銘印保證卡，以及封存培育歷程的影音紀念盒。0.20 克拉以上可代送 GIA／IGI 國際鑑定（費用另計）。DNA 鑽石系列需先支付 50% 訂金，待培育完成再支付尾款。"),
    )
    for i, (slug, label, title, body) in enumerate(pillars):
        base = 40 + i * 3
        out.append(_t(p, f"pillar-{slug}-label", f"系列總覽・{title}眉標", label, base))
        out.append(_t(p, f"pillar-{slug}-title", f"系列總覽・{title}標題", title, base + 1))
        out.append(_t(p, f"pillar-{slug}-body", f"系列總覽・{title}內文", body, base + 2))
    for i, card in enumerate(_OVERVIEW_CARDS):
        base = (50, 60, 70, 80, 91, 101)[i]
        slug, name = card["slug"], card["name"]
        out.append(_t(p, f"det-{slug}-en", f"系列總覽・{name}卡眉標", card["en"], base))
        out.append(_t(p, f"det-{slug}-title", f"系列總覽・{name}卡標題", name, base + 1))
        out.append(_t(p, f"det-{slug}-p1", f"系列總覽・{name}卡段落一", card["p1"], base + 2))
        out.append(_t(p, f"det-{slug}-p2", f"系列總覽・{name}卡段落二", card["p2"], base + 3))
        for j, fact in enumerate(card["facts"], start=1):
            out.append(_t(p, f"det-{slug}-fact-{j}", f"系列總覽・{name}卡規格{j}", fact, base + 3 + j))
        out.append(_btn(p, f"det-{slug}-more", f"系列總覽・{name}卡了解更多", card["more"], card["more_href"], base + 7))
        out.append(_btn(p, f"det-{slug}-calc", f"系列總覽・{name}卡次按鈕", card["calc"], card["calc_href"], base + 8))
    out.append(_t(p, "cards-title", "系列總覽・快速瀏覽標題", "快速瀏覽六大系列", 120))
    for i, card in enumerate(_OVERVIEW_CARDS):
        base = 121 + i * 4
        slug, name = card["slug"], card["name"]
        out.append(_t(p, f"quick-{slug}-en", f"系列總覽・快覽{name}眉標", card["en"], base))
        out.append(_t(p, f"quick-{slug}-title", f"系列總覽・快覽{name}標題", name, base + 1))
        out.append(_t(p, f"quick-{slug}-text", f"系列總覽・快覽{name}說明", card["quick_text"], base + 2))
        out.append(_t(p, f"quick-{slug}-more", f"系列總覽・快覽{name}連結", "立即客製 →", base + 3))
    out.extend(
        [
            _t(p, "next-title", "系列總覽・收尾標題", "還想多了解一點？", 150),
            _t(p, "next-body", "系列總覽・收尾內文", "系列選定之後，您可以進一步了解製程細節、價格試算，或直接與專屬顧問聊聊。我們會依您的步調，不催促、不打擾。", 151),
            _btn(p, "cta-dna", "系列總覽・DNA按鈕", "DNA 鑽石怎麼做的", "/what-is-dna-diamond", 152),
            _btn(p, "cta-price", "系列總覽・價格按鈕", "查看價格總覽", "/price", 153),
            _btn(p, "cta-faq", "系列總覽・FAQ按鈕", "常見問題", "/faq", 154),
        ]
    )
    return out


def _series_detail_slots() -> list[dict[str, Any]]:
    """Series detail fragments share series_detail.html shell; slots on fragment HTML."""
    out: list[dict[str, Any]] = []
    for d in _DETAIL_PAGES:
        route, name = d["route"], d["name"]
        out.append(_t(route, "crumb-current", f"{name}・麵包屑", d["crumb"], 0))
        out.append(_t(route, "hero-title", f"{d['hero_title']}・主標", d["hero_title"], 1))
        out.append(_t(route, "hero-lead", f"{d['hero_title']}・引言", d["hero_lead"], 2))
        out.append(_btn(route, "cta-calculator", f"{d['hero_title']}・試算", "開始客製試算", _CALC_URL, 3))
        out.append(_t(route, "hero-eyebrow", f"{name}・眉標", d["eyebrow"], 4))
        out.append(_t(route, "intro-eyebrow", f"{name}・介紹眉標", d["intro_eyebrow"], 10))
        out.append(_t(route, "intro-title", f"{name}・介紹標題", d["intro_title"], 11))
        for i, para in enumerate(d["intro_paras"], start=1):
            out.append(_t(route, f"intro-p{i}", f"{name}・介紹段落{i}", para, 11 + i))
        for i, (text, href) in enumerate(d["related"], start=1):
            out.append(_btn(route, f"rel-{i}", f"{name}・相關連結{i}", text, href, 20 + i))
        out.append(_t(route, "faq-eyebrow", f"{name}・FAQ眉標", "FAQ", 30))
        out.append(_t(route, "faq-title", f"{name}・FAQ標題", "這個系列常見問題", 31))
        for i, (q, a) in enumerate(d["faqs"], start=1):
            out.append(_t(route, f"faq-{i}-q", f"{name}・FAQ{i}問題", q, 30 + i * 2))
            out.append(_t(route, f"faq-{i}-a", f"{name}・FAQ{i}回答", a, 31 + i * 2))
        out.append(_btn(route, "faq-more", f"{name}・FAQ更多", "查看全部常見問題", "/faq", 40))
        out.append(_t(route, "calc-eyebrow", f"{name}・試算眉標", "CUSTOMIZE YOUR DIAMOND", 50))
        out.append(_t(route, "calc-title", f"{name}・試算標題", d["calc_title"], 51))
        out.append(_t(route, "calc-lead", f"{name}・試算引言", d["calc_lead"], 52))
        out.append(_btn(route, "cta-line", f"{name}・LINE諮詢", "加入官方 LINE 諮詢", _LINE_URL, 53))
        out.append(_t(route, "capture-title", f"{name}・收尾標題", "讓思念，有個可以慢慢決定的地方", 60))
        out.append(_t(route, "capture-body", f"{name}・收尾內文", _CAPTURE_BODY, 61))
        out.append(_btn(route, "capture-line", f"{name}・收尾LINE", "加入官方 LINE 好友", _LINE_URL, 62))
        out.append(_t(route, "capture-hint", f"{name}・收尾提示", "不會頻繁打擾，隨時可以取消", 63))
    return out
