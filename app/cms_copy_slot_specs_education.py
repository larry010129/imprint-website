"""Education/knowledge page + journal/stories/faq chrome slot specs.

Split from cms_copy_slot_specs.py to keep modules under 500 lines.
Imports _t/_btn from the main module; the main module imports this one
lazily inside copy_slot_specs(), so there is no import cycle.
"""

from __future__ import annotations

from typing import Any

from app.cms_copy_slot_specs import _btn, _t

_LINE_URL = "https://lin.ee/ktVBtmx"


def education_slot_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    specs.extend(_diamond_4c_slots())
    specs.extend(_lab_grown_slots())
    specs.extend(_comparison_slots())
    specs.extend(_dna_slots())
    specs.extend(_journal_chrome_slots())
    specs.extend(_stories_chrome_slots())
    specs.extend(_faq_chrome_slots())
    return specs


def _diamond_4c_slots() -> list[dict[str, Any]]:
    p = "/diamond-4c"
    return [
        _t(p, "crumb-current", "4C・麵包屑", "鑽石 4C", 1),
        _btn(p, "crumb-mid", "4C・麵包屑中段", "鑽石知識", "/what-is-dna-diamond", 2),
        _t(p, "hero-eyebrow", "4C・眉標", "DIAMOND 4C", 3),
        _t(p, "hero-title", "4C・主標", "鑽石 4C｜Carat・Color・Clarity・Cut", 4),
        _t(p, "hero-lead", "4C・引言", "國際常見的鑽石品質語言。訂製 DNA 紀念鑽石時，可用來理解規格與報價差異。", 5),
        _t(p, "hero-review", "4C・審閱資訊", "本頁由銘印鑽石整理與審閱 · 最後審閱：2026 年 8 月 7 日", 6),
        _t(p, "sec-intro-title", "4C・什麼是標題", "什麼是 4C？", 10),
        _t(p, "sec-intro-body", "4C・什麼是內文", "4C 是鑽石業界常用的四個評估面向：克拉（Carat）、顏色（Color）、淨度（Clarity）與切工（Cut）。銘印鑽石依國際 4C 分級說明規格；實際可選顏色與淨度區間，請以顧問確認與報價單為準。", 11),
        _t(p, "sec-carat-title", "4C・克拉標題", "Carat｜克拉重量", 20),
        _t(p, "sec-carat-body", "4C・克拉內文", "鑽石的重量或大小用克拉表示（ct.）。1 克拉相當於 0.2 克，1 克拉等同於 100 分：例如 0.25 克拉又被稱作 25 分。1 克拉以上會精確至百分位描述。克拉重量也是決定鑽石價值的重要元素；銘印 DNA 鑽石價格依克拉數透明列於價格總覽，線上可先至客製試算估參考價。", 21),
        _t(p, "sec-clarity-title", "4C・淨度標題", "Clarity｜淨度", 30),
        _t(p, "sec-clarity-body", "4C・淨度內文", "淨度特徵分為包裹體（內部）與外部特徵。為了分級，需觀察特徵的數量、性質、大小與位置。一般而言，淨度越高價值越高。常見等級由高至低：", 31),
        _t(p, "sec-clarity-li-1", "4C・淨度等級1", "IF：十倍放大鏡下無包裹體，只有不明顯的可見外部瑕疵。", 32),
        _t(p, "sec-clarity-li-2", "4C・淨度等級2", "VVS1～VVS2：只有很小的包裹體，十倍放大鏡下很難見到。", 33),
        _t(p, "sec-clarity-li-3", "4C・淨度等級3", "VS1～VS2：很小的包裹體，十倍放大鏡下相對容易見到。", 34),
        _t(p, "sec-clarity-li-4", "4C・淨度等級4", "SI1～SI2：十倍放大鏡下可見明顯的包裹體。", 35),
        _t(p, "sec-clarity-li-5", "4C・淨度等級5", "I1～I3：對鑑定師而言包裹體在十倍放大鏡下極為明顯，並在檯面用裸眼即可看到。", 36),
        _t(p, "sec-clarity-note", "4C・淨度補充", "據本品牌營運說明，銘印鑽石淨度可達 VVS～VS 區間；實際成品以當次培育結果與保證文件為準。", 37),
        _t(p, "sec-color-title", "4C・顏色標題", "Color｜顏色", 40),
        _t(p, "sec-color-p1", "4C・顏色段落一", "多數寶石級鑽石有不同色度，可從完全無色到可見的黃色或棕色調。無色系中最罕見昂貴的是 D、E、F 級別，顏色系統一直劃分至 Z。若顏色比 Z 色級更濃重，或帶橙色、粉色、藍色等色調，則稱為「彩色鑽石」。", 41),
        _t(p, "sec-color-p2", "4C・顏色段落二", "彩鑽顏色外觀由色彩、色調與色度組成，常見等級術語包括：微（Faint）、很淡（Very Light）、淡（Light）、淡彩（Fancy Light）、彩（Fancy）、濃彩（Fancy Intense）、暗彩（Fancy Dark）、深彩（Fancy Deep）、豔彩（Fancy Vivid）。銘印提供多種顏色選項（含彩鑽）；彩鑽因特殊工序，時程可能較長。詳見常見問題與顧問說明。", 42),
        _t(p, "sec-cut-title", "4C・切工標題", "Cut｜切工與形狀", 50),
        _t(p, "sec-cut-p1", "4C・切工段落一", "從原石到成品需要精湛切割技藝；圓度、深度、寬度及刻面整齊度都影響光彩。切工越好，越能把光折射出最佳角度。切工（車工）由高至低常見為：EX 極優（Excellent）、VG 優良（Very Good）、G 良好（Good）、F 一般（Fair）、P 不佳（Poor）。", 51),
        _t(p, "sec-cut-p2", "4C・切工段落二", "形狀（如圓形、橢圓等）屬訂製選項。非圓形切工可能有加價或最低克拉限制，請見價格總覽說明。", 52),
        _t(p, "sec-cert-title", "4C・鑑定標題", "鑑定與保障", 60),
        _t(p, "sec-cert-body", "4C・鑑定內文", "每顆鑽石附銘印保證卡；0.20 克拉以上可代送 GIA 或 IGI 鑑定（費用另計）。", 61),
        _btn(p, "cta-lab", "4C・培育鑽石按鈕", "什麼是培育鑽石", "/lab-grown-diamond", 62),
        _btn(p, "cta-compare", "4C・比較按鈕", "天然 vs 培育／DNA", "/diamond-comparison", 63),
        _btn(p, "cta-dna", "4C・DNA按鈕", "DNA 鑽石怎麼做", "/what-is-dna-diamond", 64),
        _t(p, "footnote", "4C・頁尾註", "4C 為業界通用語言；銘印規格與「VVS～VS」等表述依本品牌營運說明整理，正式訂單以確認文件為準。", 70),
    ]


def _lab_grown_slots() -> list[dict[str, Any]]:
    p = "/lab-grown-diamond"
    return [
        _t(p, "crumb-current", "培育鑽石・麵包屑", "培育鑽石", 1),
        _btn(p, "crumb-mid", "培育鑽石・麵包屑中段", "鑽石知識", "/what-is-dna-diamond", 2),
        _t(p, "hero-eyebrow", "培育鑽石・眉標", "LAB-GROWN DIAMOND", 3),
        _t(p, "hero-title", "培育鑽石・主標", "什麼是培育鑽石", 4),
        _t(p, "hero-lead", "培育鑽石・引言", "實驗室培育鑽石與天然鑽石同為鑽石晶體；差異在生長來源。銘印的 DNA 鑽石以 CVD 等製程，在台灣完成萃取與培育。", 5),
        _t(p, "hero-review", "培育鑽石・審閱資訊", "本頁由銘印鑽石整理與審閱 · 最後審閱：2026 年 8 月 7 日", 6),
        _t(p, "sec-what-title", "培育鑽石・什麼是標題", "實驗室培育鑽石是什麼？", 10),
        _t(p, "sec-what-p1", "培育鑽石・什麼是段落一", "人們自數百年前就嘗試合成鑽石，經過無數次失敗，上個世紀終於在實驗室合成出鑽石。目前合成寶石級鑽石的方法主要有兩種：高溫高壓法（HPHT）與化學氣相沉積法（CVD）。", 11),
        _t(p, "sec-what-p2", "培育鑽石・什麼是段落二", "「實驗室生長鑽石」又稱培育鑽石、未來鑽石、科技鑽石、環保鑽石。在鑑定類別上皆稱為實驗室生長鑽石（Lab Grown Diamond）。不僅外觀、成分一樣，物理化學特性與天然鑽石別無二致；不同之處在於生長方式：天然鑽石從地底開採，培育鑽石由實驗室模擬天然條件長成。若不藉助高解析儀器，差異往往只是淨度更趨完美、價格更親民。", 12),
        _t(p, "sec-methods-title", "培育鑽石・HPHT/CVD標題", "HPHT 與 CVD", 20),
        _t(p, "sec-methods-body", "培育鑽石・HPHT/CVD內文", "HPHT（高溫高壓法）與 CVD（化學氣相沉積／沉澱法）是兩種常見長晶方式。CVD 在受控環境中讓碳原子層層沉積、長成鑽石。銘印 DNA 鑽石在台灣完成萃取與培育；成品可依規格鑲嵌。完整流程見什麼是 DNA 鑽石。", 21),
        _t(p, "sec-ftc-title", "培育鑽石・FTC標題", "FTC 2018：鑽石定義不再限於「自然」", 30),
        _t(p, "sec-ftc-body", "培育鑽石・FTC內文", "2018 年 7 月，美國聯邦貿易委員會（FTC）選擇以科學定義鑽石：一種「碳晶體」，無論來自地球地底或實驗室。FTC 新定義指出：鑽石是一種礦物質，主要由在等軸晶系中結晶的「純碳」組成；並最終從鑽石定義中刪除「自然」一詞，因為實驗室生長的鑽石與開採鑽石具有基本相同的光學、物理與化學性質，因此它們都是鑽石。", 31),
        _t(p, "sec-ftc-callout", "培育鑽石・FTC結論", "結論：實驗室生長的鑽石與開採的鑽石具有基本相同的光學、物理和化學性質，因此它們都是鑽石。", 32),
        _t(p, "sec-dna-title", "培育鑽石・DNA比較標題", "DNA 鑽石與一般培育鑽石", 40),
        _t(p, "sec-dna-body", "培育鑽石・DNA比較內文", "一般培育鑽石使用實驗室碳源；DNA 紀念鑽石則萃取您提供之毛髮或骨灰中的元素，參與培育，使這顆鑽石承載專屬意義。樣本份量、時程與保障見常見問題。", 41),
        _t(p, "sec-dna-callout", "培育鑽石・DNA補充", "據本品牌營運說明，銘印為全台唯一擁有在地 DNA 鑽石培育實驗室的紀念鑽石品牌；樣本不需送往海外。", 42),
        _t(p, "sec-cert-title", "培育鑽石・鑑定標題", "鑑定與退換", 50),
        _t(p, "sec-cert-body", "培育鑽石・鑑定內文", "每顆 DNA 鑽石附銘印保證卡；0.20 克拉以上可代送 GIA 或 IGI（費用另計）。一般培育鑽石商品與客製 DNA 鑽石之退換規則不同，請見退換貨與取消政策。", 51),
        _btn(p, "cta-dna", "培育鑽石・DNA按鈕", "DNA 鑽石製程", "/what-is-dna-diamond", 52),
        _btn(p, "cta-4c", "培育鑽石・4C按鈕", "鑽石 4C", "/diamond-4c", 53),
        _btn(p, "cta-compare", "培育鑽石・比較按鈕", "天然 vs 培育／DNA", "/diamond-comparison", 54),
        _t(p, "footnote", "培育鑽石・頁尾註", "「全台唯一在地 DNA 鑽石培育實驗室」等表述依本品牌營運說明整理；歡迎預約現場了解製程。", 60),
    ]


def _comparison_slots() -> list[dict[str, Any]]:
    p = "/diamond-comparison"
    return [
        _t(p, "crumb-current", "鑽石比較・麵包屑", "鑽石比較", 1),
        _btn(p, "crumb-mid", "鑽石比較・麵包屑中段", "鑽石知識", "/what-is-dna-diamond", 2),
        _t(p, "hero-eyebrow", "鑽石比較・眉標", "COMPARE", 3),
        _t(p, "hero-title", "鑽石比較・主標", "天然鑽石 vs 培育鑽石 vs DNA 鑽石", 4),
        _t(p, "hero-lead", "鑽石比較・引言", "用清楚對照理解差異與定位。本頁說明性質與意義，不比較他家品牌。", 5),
        _t(p, "hero-review", "鑽石比較・審閱資訊", "本頁由銘印鑽石整理與審閱 · 最後審閱：2026 年 8 月 7 日", 6),
        _t(p, "sec-two-title", "鑽石比較・兩種標題", "真鑽石有兩種", 10),
        _t(p, "sec-two-p1", "鑽石比較・兩種段落一", "真鑽石分為兩種：一種是天然鑽石，在地球內部歷經漫長歷史與高溫高壓而形成；另一種是在實驗室中精密調整、模擬天然鑽石生長環境培育出來的實驗室鑽石。因此培育鑽石又可稱為環保鑽石、無衝突鑽石。天然與實驗室鑽石在化學成分、晶體結構、光學與物理特性方面完全一致。", 11),
        _t(p, "sec-two-p2", "鑽石比較・兩種段落二", "銘印 DNA 鑽石屬實驗室培育路徑，並以您提供的毛髮或骨灰元素參與培育，強調紀念意義與在地託付。一段思念如何成為永恆：天然鑽石來自地底挖採；DNA 鑽石來自您的摯愛。", 12),
        _t(p, "sec-fake-title", "鑽石比較・仿鑽標題", "仿鑽不是鑽石", 20),
        _t(p, "sec-fake-body", "鑽石比較・仿鑽內文", "俗稱的蘇聯鑽（二氧化鋯）、莫桑石等（碳化矽），則要歸類為仿鑽：它們在本質上不是鑽石晶體，不應與天然或培育真鑽混為一談。", 21),
        _t(p, "sec-enh-title", "鑽石比較・優化標題", "優化鑽石與改色", 30),
        _t(p, "sec-enh-p1", "鑽石比較・優化段落一", "「優化鑽石」是針對每顆真鑽獨一無二的特性，進一步施以優化處理，提升顏色、火彩、淨度、切工等品質。鑽石顏色可分為無色系列與彩色系列；品質優良、天然形成的彩色鑽石相當稀有。", 31),
        _t(p, "sec-enh-p2", "鑽石比較・優化段落二", "為滿足市場需求，現今可透過高溫高壓處理，將鑽石本來的顏色昇華成更具吸引力的顏色；高溫高壓改色的結果是恆久不變的，被改過成色的鑽石不會再變回原來的成色。", 32),
        _t(p, "sec-points-title", "鑽石比較・對照標題", "對照重點", 40),
        _t(p, "sec-points-li-1", "鑽石比較・對照1", "晶體本質：天然與培育（含 DNA）皆可為鑽石晶體；業界常用 4C 描述規格（見鑽石 4C）。", 41),
        _t(p, "sec-points-li-2", "鑽石比較・對照2", "來源故事：天然＝地質形成；一般培育＝實驗室碳源；DNA＝您的樣本元素參與培育。", 42),
        _t(p, "sec-points-li-3", "鑽石比較・對照3", "產地與託付：據本品牌營運說明，銘印從萃取、培育到飾品相關流程於台灣完成，樣本不送海外。", 43),
        _t(p, "sec-points-li-4", "鑽石比較・對照4", "保障文件：銘印每顆附保證卡；0.20 克拉以上可代送 GIA／IGI（費用另計）。", 44),
        _t(p, "sec-when-title", "鑽石比較・時機標題", "何時適合選 DNA 紀念鑽石？", 50),
        _t(p, "sec-when-body", "鑽石比較・時機內文", "當您想把毛髮、骨灰等紀念樣本，化為可鑲嵌、可傳承的實體時。系列入口見六大系列；求婚／結髮見求婚與結髮與結髮鑽石。", 51),
        _t(p, "sec-more-title", "鑽石比較・延伸標題", "延伸閱讀", 60),
        _btn(p, "cta-lab", "鑽石比較・培育按鈕", "什麼是培育鑽石", "/lab-grown-diamond", 61),
        _btn(p, "cta-dna", "鑽石比較・DNA按鈕", "DNA 鑽石製程", "/what-is-dna-diamond", 62),
        _btn(p, "cta-faq", "鑽石比較・FAQ按鈕", "常見問題", "/faq", 63),
        _t(p, "footnote", "鑽石比較・頁尾註", "本頁為品牌知識說明，非他牌評比。絕對性產地／唯一性表述依本品牌營運說明；歡迎預約核對細節。", 70),
    ]


def _dna_slots() -> list[dict[str, Any]]:
    p = "/what-is-dna-diamond"
    return [
        _t(p, "hero-eyebrow", "DNA知識・眉標", "WHAT IS DNA DIAMOND", 1),
        _t(p, "hero-title", "DNA知識・主標", "DNA 鑽石的誕生", 2),
        _t(
            p,
            "hero-lead",
            "DNA知識・引言",
            "從一縷髮絲，到一顆會發光的鑽石——完整的製作過程與品質保障。",
            3,
        ),
        _t(p, "crumb-current", "DNA知識・麵包屑", "鑽石知識", 4),
        _t(p, "hero-review", "DNA知識・審閱資訊", "本頁由銘印鑽石整理與審閱 · 最後審閱：2026 年 8 月 7 日", 5),
        _t(p, "sec-what-title", "DNA知識・什麼是標題", "什麼是 DNA 鑽石", 10),
        _t(
            p,
            "sec-what-body",
            "DNA知識・什麼是內文",
            "每一顆 DNA 鑽石，都是一段無可取代的生命印記。我們溫柔萃取毛髮或骨灰中獨一無二的碳元素，在台灣唯一擁有培育技術的實驗室裡，讓思念隨著時間的沉澱，緩緩結晶成永恆的璀璨。",
            11,
        ),
        _t(p, "sec-what-callout", "DNA知識・什麼是補充", "據本品牌營運說明，銘印鑽石為全台唯一擁有在地 DNA 鑽石培育實驗室的紀念鑽石品牌。無需漂洋過海：從萃取、培育到飾品設計全程於台灣完成；每一份樣本都以單一客戶、單一培育流程處理。", 12),
        _t(p, "sec-cvd-title", "DNA知識・CVD標題", "什麼是 CVD 鑽石", 15),
        _t(p, "sec-cvd-body", "DNA知識・CVD內文", "CVD（化學氣相沉積）是實驗室培育鑽石常見的生長方式之一：在受控環境中，讓碳原子層層沉積、長成鑽石晶體。銘印的 DNA 鑽石在台灣完成萃取與培育流程，讓毛髮或骨灰中的元素得以參與這段結晶；成品可依規格鑲嵌，0.20 克拉以上並可代送 GIA 或 IGI 鑑定（費用另計）。更細節的樣本與時程說明，也可參考常見問題。", 16),
        _t(p, "sec-process-title", "DNA知識・流程標題", "時光與情感的淬鍊｜完整製作流程", 20),
        _t(p, "step-1-title", "DNA知識・步驟1標題", "樣本萃取", 21),
        _t(p, "step-1-body", "DNA知識・步驟1內文", "毛髮約一顆雞蛋大小、骨灰約 3～5 公克，單一客戶、單一培育流程。", 22),
        _t(p, "step-2-title", "DNA知識・步驟2標題", "元素注入・晶化培育", 23),
        _t(p, "step-2-body", "DNA知識・步驟2內文", "元素注入生長設備，讓晶體以自己的節奏，慢慢長成，約需 70～90 天。", 24),
        _t(p, "step-3-title", "DNA知識・步驟3標題", "切割拋光", 25),
        _t(p, "step-3-body", "DNA知識・步驟3內文", "依您選擇的克拉數與形狀，精工切磨。", 26),
        _t(p, "step-4-title", "DNA知識・步驟4標題", "鑑定保障", 27),
        _t(p, "step-4-body", "DNA知識・步驟4內文", "每顆附銘印保證卡；0.20 克拉以上可代送 GIA 或 IGI 國際鑑定機構出具證書。", 28),
        _t(p, "step-5-title", "DNA知識・步驟5標題", "製作成飾品（選擇性）", 29),
        _t(p, "step-5-body", "DNA知識・步驟5內文", "想將專屬 DNA 鑽石製作成飾品、時時刻刻配戴？沒問題。在地品牌更能瞭解您的需求，可與您討論製作細節，鑲嵌為戒指、項鍊、耳環或手鍊；材質可選 18K／14K／9K 金或 PT950 鉑金。", 32),
        _t(p, "step-6-title", "DNA知識・步驟6標題", "時光封存，璀璨躍然", 33),
        _t(p, "step-6-body", "DNA知識・步驟6內文", "當您緩緩打開專屬的淺藍色影音紀念盒，映入眼簾的那顆專屬於您的 DNA 鑽石，不僅是頂級的珠寶工藝，更是將牽絆化為具象的永恆。", 34),
        _t(p, "sec-sample-title", "DNA知識・樣本標題", "需要準備多少樣本", 30),
        _t(
            p,
            "sec-sample-body",
            "DNA知識・樣本內文",
            "毛髮約需一顆雞蛋的大小（或養樂多瓶約 8 分滿）；骨灰約需 3 至 5 公克。若份量不如預期，請透過官方 LINE 聯繫顧問評估，確認可行前不需寄出樣本。",
            31,
        ),
        _t(p, "sec-local-title", "DNA知識・在地標題", "最近的距離，最深的安心", 40),
        _t(p, "sec-local-body", "DNA知識・在地內文", "據本品牌營運說明，銘印為全台唯一擁有在地 DNA 鑽石培育實驗室的品牌，您珍視的記憶無需經歷漫長的國際漂流。歡迎預約蒞臨，親眼見證這份思念逐漸閃耀的過程。據本品牌營運說明，實驗室配置超過 60 台鑽石培育艙，並結合台灣團隊逾十年的高科技與工藝經驗。", 41),
        _t(p, "sec-cert-title", "DNA知識・鑑定標題", "鑑定與保障", 50),
        _t(p, "sec-cert-p1", "DNA知識・鑑定段落一", "每一顆經由銘印鑽石實驗室出品的 DNA 鑽石（毛髮鑽石、生命鑽石、骨灰鑽石、寵物鑽石），必須通過嚴格的真品檢查，確認在物理性質、化學性質與光學性質上，都與天然開採鑽石無異；客製化的獨特性也和天然鑽石一樣，每一顆都獨一無二。", 51),
        _t(p, "sec-cert-p2", "DNA知識・鑑定段落二", "每顆 DNA 鑽石皆免費提供銘印保證卡，或可加購代送第三方機構：美國寶石學院（GIA）或國際寶石學院（IGI）二者擇一，出具鑑定證書（費用另計），確保向銘印訂購的 DNA 鑽石為真品。", 52),
        _btn(p, "cta-series", "DNA知識・系列按鈕", "探索您的專屬紀念｜六大訂製系列", "/series", 53),
        _btn(p, "cta-4c", "DNA知識・4C按鈕", "鑽石 4C", "/diamond-4c", 54),
        _btn(p, "cta-lab", "DNA知識・培育按鈕", "培育鑽石說明", "/lab-grown-diamond", 55),
        _btn(p, "cta-compare", "DNA知識・比較按鈕", "天然 vs 培育／DNA", "/diamond-comparison", 56),
        _btn(p, "cta-faq", "DNA知識・FAQ按鈕", "常見問題", "/faq", 57),
        _t(p, "sec-care-title", "DNA知識・四大保障標題", "四大保障，讓您安心託付", 60),
        _t(p, "usp-1-title", "DNA知識・保障1標題", "在地實驗室", 61),
        _t(p, "usp-1-body", "DNA知識・保障1內文", "據本品牌營運說明：全台唯一在地 DNA 鑽石培育實驗室、60+ 台培育艙，樣本不送海外。", 62),
        _t(p, "usp-2-title", "DNA知識・保障2標題", "專業認證", 63),
        _t(p, "usp-2-body", "DNA知識・保障2內文", "真品檢查確認物化光性質與天然鑽石無異；附銘印保證卡，0.20 克拉以上可代送 GIA 或 IGI。", 64),
        _t(p, "usp-3-title", "DNA知識・保障3標題", "影音紀念盒", 65),
        _t(p, "usp-3-body", "DNA知識・保障3內文", "專屬淺藍色影音紀念盒，封存從樣本到成品的珍貴過程。", 66),
        _t(p, "usp-4-title", "DNA知識・保障4標題", "製作成飾品", 67),
        _t(p, "usp-4-body", "DNA知識・保障4內文", "在地更能瞭解需求，可溝通鑲嵌為戒指、項鍊、耳環或手鍊，讓 DNA 鑽石時時刻刻配戴在身上。", 68),
        _t(p, "footnote-cycle", "DNA知識・週期頁尾", "完整培育週期約 70～90 天｜歡迎預約蒞臨實驗室親眼見證", 70),
        _t(p, "footnote-source", "DNA知識・出處頁尾", "「全台唯一」「超過 60 台培育艙」「逾十年經驗」等表述依本品牌營運與實驗室配置說明整理；鑑定證書可代送 GIA／IGI（費用另計）。歡迎預約現場見證製程。", 71),
    ]


def _journal_chrome_slots() -> list[dict[str, Any]]:
    p = "/journal"
    return [
        _t(p, "crumb-current", "日誌・麵包屑", "品牌日誌", 1),
        _t(p, "list-eyebrow", "日誌・眉標", "JOURNAL", 2),
        _t(p, "list-title", "日誌・主標", "品牌日誌", 3),
        _t(p, "list-lead", "日誌・引言", "培育鑽石知識分享、品牌動態與展會紀錄。", 4),
    ]


def _stories_chrome_slots() -> list[dict[str, Any]]:
    p = "/stories"
    return [
        _t(p, "chrome-eyebrow", "見證・眉標", "STORIES", 1),
        _t(p, "chrome-title", "見證・主標", "客戶見證", 2),
        _t(p, "chrome-lead", "見證・引言", "真實故事，銘印成永恆。", 3),
        _btn(p, "load-more", "見證・載入更多", "載入更多", "", 4),
        _t(p, "cta-title", "見證・CTA標題", "您的故事，也值得被好好記住", 5),
        _t(p, "cta-lead", "見證・CTA引言", "歡迎加入官方 LINE，讓顧問陪您慢慢聊聊。", 6),
        _btn(p, "cta-line", "見證・LINE按鈕", "加入官方 LINE 好友", _LINE_URL, 7),
    ]


def _faq_chrome_slots() -> list[dict[str, Any]]:
    p = "/faq"
    return [
        _t(p, "crumb-current", "FAQ頁・麵包屑", "常見問題", 1),
        _t(p, "hero-eyebrow", "FAQ頁・眉標", "FAQ", 2),
        _t(p, "hero-title", "FAQ頁・主標", "常見問題", 3),
        _t(p, "hero-lead", "FAQ頁・引言", "訂製一顆 DNA 紀念鑽石，是一個需要時間與信任的決定。願這些答案，讓您安心地慢慢考慮。", 4),
        _btn(p, "hero-cta", "FAQ頁・顧問按鈕", "還有想了解的？問問顧問", _LINE_URL, 5),
        _t(p, "know-eyebrow", "FAQ頁・知識眉標", "鑽石知識", 10),
        _t(p, "know-title", "FAQ頁・知識標題", "想先讀完整說明？", 11),
        _t(p, "know-lead", "FAQ頁・知識引言", "下列頁面補充 FAQ 未盡之處：", 12),
        _t(p, "know-dna-title", "FAQ頁・知識卡DNA標題", "什麼是 DNA 鑽石", 20),
        _t(p, "know-dna-desc", "FAQ頁・知識卡DNA說明", "CVD 製程、樣本與時程", 21),
        _t(p, "know-4c-title", "FAQ頁・知識卡4C標題", "鑽石 4C", 22),
        _t(p, "know-4c-desc", "FAQ頁・知識卡4C說明", "克拉、顏色、淨度、切工", 23),
        _t(p, "know-lab-title", "FAQ頁・知識卡培育標題", "什麼是培育鑽石", 24),
        _t(p, "know-lab-desc", "FAQ頁・知識卡培育說明", "實驗室培育與 DNA 定位", 25),
        _t(p, "know-cmp-title", "FAQ頁・知識卡比較標題", "天然 vs 培育／DNA", 26),
        _t(p, "know-cmp-desc", "FAQ頁・知識卡比較說明", "差異對照（非他牌評比）", 27),
    ]
