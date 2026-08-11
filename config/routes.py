"""Route registry — maps each page URL to its Jinja view and SEO metadata.

Used by app/controllers/web_controller.py to register FastAPI page routes.
Hand-edit for pages added after the initial migration from static HTML.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PageMeta:
    route: str
    template: str
    title: str
    description: str
    canonical_path: str
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None
    breadcrumbs: list[tuple[str, str | None]] = field(default_factory=list)
    mvc_page: str | None = None
    extra_body_class: str | None = None
    content_fragment: str | None = None
    extra_head_blocks: list[str] = field(default_factory=list)
    robots: str | None = None


HOME = PageMeta(
    route='/',
    template='pages/index.html',
    title='銘印鑽石 IMPRINT DIAMOND｜台灣在地 DNA 紀念鑽石訂製',
    description='銘印鑽石｜全台唯一在地 DNA 鑽石培育實驗室。毛髮、骨灰可製成專屬紀念鑽石（骨灰、毛髮、生命、寵物、初生）；採 CVD 製程，附鑑定保障與影音紀念盒，預約制顧問。',
    canonical_path='',
    og_title='銘印鑽石 IMPRINT DIAMOND｜台灣在地 DNA 紀念鑽石訂製',
    og_description='全台唯一在地 DNA 鑽石培育實驗室。毛髮、骨灰可製成專屬紀念鑽石；CVD 製程、鑑定保障，預約制顧問。',
    og_image='static/images/hero/imprint-diamond-family-memorial.jpg',
    breadcrumbs=[],
    mvc_page=None,
    extra_body_class='page-home',
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_404 = PageMeta(
    route='/404',
    template='pages/404.html',
    title='找不到頁面｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='error-404',
    extra_body_class='page-404',
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_ABOUT = PageMeta(
    route='/about',
    template='pages/about.html',
    title='銘印鑽石品牌故事｜紀念鑽石的陪伴與託付',
    description='銘印鑽石（IMPRINT DIAMOND／心之銘印鑽石有限公司）品牌故事：我們相信思念可以有具體的形狀，也理解每一段考慮期都值得被尊重。預約制門市、全程在地託付、不催促成交。DNA 鑽石製程詳見鑽石知識頁。',
    canonical_path='about',
    og_title='銘印鑽石品牌故事｜IMPRINT DIAMOND',
    og_description='銘印鑽石｜在您準備好的時候，我們都在。預約制門市；紀念鑽石的陪伴、託付與服務承諾。',
    og_image='static/images/legacy-live/styles/taiwan-local-lab.jpg',
    breadcrumbs=[('首頁', '/'), ('關於我們', '/about'), ('品牌故事', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_ACCOUNT = PageMeta(
    route='/account',
    template='pages/account.html',
    title='會員專區｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='account',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='account',
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_CART = PageMeta(
    route='/cart',
    template='pages/cart.html',
    title='購物車｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='cart',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='cart',
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_CHECKOUT = PageMeta(
    route='/checkout',
    template='pages/checkout.html',
    title='確認訂單｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='checkout',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_CONTACT = PageMeta(
    route='/contact',
    template='pages/contact.html',
    title='銘印鑽石聯絡我們｜三重門市・02-2977-0268',
    description='銘印鑽石（IMPRINT DIAMOND）聯絡資訊：新北市三重區福德南路 43 號 1 樓（預約制），電話 02-2977-0268。訂製婚戒、結髮鑽石或專屬試算，歡迎官方 LINE 一對一預約，或於本頁留言。',
    canonical_path='contact',
    og_title='銘印鑽石聯絡我們｜三重門市預約制',
    og_description='銘印鑽石｜新北市三重區福德南路 43 號 1 樓（預約制），電話 02-2977-0268。訂製婚戒與結髮鑽石歡迎 LINE 預約。',
    og_image='static/images/hero/imprint-diamond-family-memorial.jpg',
    breadcrumbs=[('首頁', '/'), ('關於我們', '/about'), ('聯絡我們', None)],
    mvc_page='contact',
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_FAQ = PageMeta(
    route='/faq',
    template='pages/faq.html',
    title='常見問題｜DNA紀念鑽石怎麼做？毛髮骨灰需要多少？－銘印鑽石',
    description='DNA紀念鑽石常見問題一次解答：毛髮約一顆雞蛋大小、骨灰3至5公克即可訂製，製作約3個月，全程於台灣在地實驗室完成，0.20克拉以上可代送GIA/IGI鑑定。',
    canonical_path='faq',
    og_title='常見問題｜DNA紀念鑽石怎麼做？－銘印鑽石',
    og_description='毛髮約一顆雞蛋大小、骨灰3至5公克即可訂製，製作約3個月，全程台灣在地完成。',
    og_image='static/images/hero/imprint-diamond-family-memorial.jpg',
    breadcrumbs=[('首頁', '/'), ('常見問題', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_FAVORITES = PageMeta(
    route='/favorites',
    template='pages/favorites.html',
    title='收藏款式｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='favorites',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='favorites',
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_GOLD_PRICE = PageMeta(
    route='/gold-price',
    template='pages/gold-price.html',
    title='黃金牌價｜黃金最新牌價－銘印鑽石',
    description='即時黃金飾金牌價，9K/14K/18K 成色金價換算，供戒台訂製試算參考。',
    canonical_path='gold-price',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_HISTORY = PageMeta(
    route='/history',
    template='pages/history.html',
    title='訂購紀錄｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='history',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='history',
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_JOURNAL = PageMeta(
    route='/journal',
    template='pages/journal.html',
    title='品牌日誌｜銘印鑽石 IMPRINT DIAMOND',
    description='銘印鑽石品牌日誌：培育鑽石知識分享、品牌動態與展會紀錄。',
    canonical_path='journal',
    og_title='品牌日誌｜銘印鑽石 IMPRINT DIAMOND',
    og_description='培育鑽石知識分享、品牌動態與展會紀錄。',
    og_image='static/images/hero/imprint-diamond-family-memorial.jpg',
    breadcrumbs=[('首頁', '/'), ('品牌日誌', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_LOGIN = PageMeta(
    route='/login',
    template='pages/login.html',
    title='會員登入｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='login',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='login',
    extra_body_class='page-login',
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_LOGIN_2FA = PageMeta(
    route='/login-2fa',
    template='pages/login-2fa.html',
    title='雙因素驗證｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='login-2fa',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='login-2fa',
    extra_body_class='page-login-2fa',
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_ACCOUNT_SECURITY = PageMeta(
    route='/account-security',
    template='pages/account-security.html',
    title='帳戶安全｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='account-security',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='account-security',
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_NOTIFICATIONS = PageMeta(
    route='/notifications',
    template='pages/notifications.html',
    title='通知｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='notifications',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='notifications',
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_PRICE = PageMeta(
    route='/price',
    template='pages/price.html',
    title='價格總覽｜DNA紀念鑽石價格表－銘印鑽石 IMPRINT DIAMOND',
    description='DNA紀念鑽石(骨灰鑽石,毛髮鑽石,寵物鑽石,生命鑽石)價格總覽：0.10克拉NT$24,000起，依克拉數透明報價；非圓形切工加價10%且需0.30克拉以上，0.20克拉以上可代送GIA/IGI鑑定。',
    canonical_path='price',
    og_title='價格總覽｜DNA紀念鑽石價格表－銘印鑽石',
    og_description='依克拉數透明報價，沒有看不懂的名目。0.10克拉NT$24,000起。',
    og_image='static/images/hero/imprint-diamond-family-memorial.jpg',
    breadcrumbs=[('首頁', '/'), ('DNA 鑽石', '/price'), ('價格總覽', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_PRIVACY = PageMeta(
    route='/privacy',
    template='pages/privacy.html',
    title='隱私權政策（草稿）｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='privacy',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[('首頁', '/'), ('隱私權政策', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_TERMS = PageMeta(
    route='/terms',
    template='pages/terms.html',
    title='服務條款（草稿）｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='terms',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[('首頁', '/'), ('服務條款', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_RETURN_POLICY = PageMeta(
    route='/return-policy',
    template='pages/return-policy.html',
    title='退換貨與取消政策｜銘印鑽石 IMPRINT DIAMOND',
    description='銘印鑽石退換貨與取消政策：一般培育鑽石商品 7 天內可退換；DNA 鑽石等客製化商品因專屬培育，啟動生產後恕無法取消或退款。訂金、尺寸誤差與運送保障說明。',
    canonical_path='return-policy',
    og_title='退換貨與取消政策｜銘印鑽石 IMPRINT DIAMOND',
    og_description='一般培育鑽石商品 7 天內可退換；DNA 鑽石等客製化商品啟動生產後恕無法取消或退款。',
    og_image='static/images/hero/imprint-diamond-family-memorial.jpg',
    breadcrumbs=[('首頁', '/'), ('退換貨與取消政策', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_PROFILE = PageMeta(
    route='/profile',
    template='pages/profile.html',
    title='帳戶設定｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='profile',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='profile',
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_REGISTER = PageMeta(
    route='/register',
    template='pages/register.html',
    title='加入會員｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='register',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='register',
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_RESET_PASSWORD = PageMeta(
    route='/reset-password',
    template='pages/reset-password.html',
    title='重設密碼｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='reset-password',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='reset-password',
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_FORGOT_PASSWORD = PageMeta(
    route='/forgot-password',
    template='pages/forgot-password.html',
    title='忘記密碼｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='forgot-password',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='forgot-password',
    extra_body_class='page-forgot-password',
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_STORIES = PageMeta(
    route='/stories',
    template='pages/stories.html',
    title='客戶見證｜真實的紀念鑽石故事－銘印鑽石 IMPRINT DIAMOND',
    description='銘印鑽石客戶見證：寵物鑽石、生命鑽石、結髮鑽石、滿月鑽石的真實訂製故事。每一顆銘印鑽石背後，都是一段值得被記住的情感。',
    canonical_path='stories',
    og_title='客戶見證－銘印鑽石 IMPRINT DIAMOND',
    og_description='思念，在他們手中發著光。每一顆銘印鑽石背後，都是一段真實的故事。',
    og_image='static/images/hero/imprint-diamond-family-memorial.jpg',
    breadcrumbs=[('首頁', '/'), ('關於我們', '/about'), ('客戶見證', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_SUCCESS = PageMeta(
    route='/success',
    template='pages/success.html',
    title='訂單送出｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='success',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='success',
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, nofollow',
)

PAGE_TRACK_ORDER = PageMeta(
    route='/track-order',
    template='pages/track-order.html',
    title='查詢訂製進度｜銘印鑽石 IMPRINT DIAMOND',
    description='',
    canonical_path='track-order',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page='track-order',
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_WHAT_IS_DNA_DIAMOND = PageMeta(
    route='/what-is-dna-diamond',
    template='pages/what-is-dna-diamond.html',
    title='什麼是 DNA 鑽石｜CVD 製程與鑑定保障－銘印鑽石',
    description='DNA 鑽石是萃取毛髮或骨灰中的元素，於台灣以 CVD 等製程培育的專屬鑽石。本頁說明樣本份量、70–90 天培育週期，以及 0.20 克拉以上可代送 GIA／IGI 鑑定。',
    canonical_path='what-is-dna-diamond',
    og_title='什麼是 DNA 鑽石｜CVD 製程與鑑定保障－銘印鑽石',
    og_description='台灣 DNA 鑽石怎麼做？說明 CVD 培育、樣本份量、時程與可代送 GIA／IGI 鑑定。',
    og_image='static/images/hero/imprint-diamond-family-memorial.jpg',
    breadcrumbs=[('首頁', '/'), ('鑽石知識', '/what-is-dna-diamond'), ('什麼是 DNA 鑽石', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_DIAMOND_4C = PageMeta(
    route='/diamond-4c',
    template='pages/diamond-4c.html',
    title='鑽石 4C｜Carat・Color・Clarity・Cut－銘印鑽石',
    description='鑽石 4C（克拉、顏色、淨度、切工）說明：訂製 DNA 紀念鑽石時如何理解規格與報價；並說明銘印保證卡與可代送 GIA／IGI 鑑定。',
    canonical_path='diamond-4c',
    og_title='鑽石 4C｜規格語言說明－銘印鑽石',
    og_description='用 4C 理解克拉、顏色、淨度與切工；連結價格總覽、培育鑽石與 DNA 製程說明。',
    og_image='static/images/hero/imprint-diamond-family-memorial.jpg',
    breadcrumbs=[('首頁', '/'), ('鑽石知識', '/what-is-dna-diamond'), ('鑽石 4C', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_LAB_GROWN_DIAMOND = PageMeta(
    route='/lab-grown-diamond',
    template='pages/lab-grown-diamond.html',
    title='什麼是培育鑽石｜CVD 與 DNA 紀念鑽石－銘印鑽石',
    description='培育鑽石（lab-grown）是實驗室生長的鑽石晶體。說明 CVD 製程、與 DNA 紀念鑽石的差異，以及銘印在地培育與鑑定保障。',
    canonical_path='lab-grown-diamond',
    og_title='什麼是培育鑽石｜CVD 與 DNA－銘印鑽石',
    og_description='實驗室培育鑽石是什麼？CVD 怎麼長？DNA 紀念鑽石如何與一般培育鑽石不同？',
    og_image='static/images/hero/imprint-diamond-family-memorial.jpg',
    breadcrumbs=[('首頁', '/'), ('鑽石知識', '/what-is-dna-diamond'), ('培育鑽石', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_DIAMOND_COMPARISON = PageMeta(
    route='/diamond-comparison',
    template='pages/diamond-comparison.html',
    title='天然鑽石 vs 培育鑽石 vs DNA 鑽石｜比較說明－銘印鑽石',
    description='天然鑽石、實驗室培育鑽石與 DNA 紀念鑽石的差異與定位：晶體本質、來源故事、在地託付與鑑定保障。非他牌評比。',
    canonical_path='diamond-comparison',
    og_title='天然 vs 培育 vs DNA 鑽石｜比較說明－銘印鑽石',
    og_description='清楚對照天然、培育與 DNA 紀念鑽石的差異，協助選擇適合的紀念方式。',
    og_image='static/images/hero/imprint-diamond-family-memorial.jpg',
    breadcrumbs=[('首頁', '/'), ('鑽石知識', '/what-is-dna-diamond'), ('鑽石比較', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

PAGE_SERIES = PageMeta(
    route='/series',
    template='pages/series.html',
    title='六大系列總覽｜滿月・寵物・結髮・全家福・生命・真我（Signature）－銘印鑽石 IMPRINT DIAMOND',
    description='銘印鑽石六大系列完整介紹：滿月鑽石、寵物鑽石、結髮鑽石、全家福鑽石、生命鑽石與真我鑽石（Signature）。依您的羈絆與生命階段選擇系列，了解樣本來源、培育方式與線上試算。',
    canonical_path='series',
    og_title='六大系列總覽｜選擇屬於您的 DNA 鑽石系列－銘印鑽石',
    og_description='每一種羈絆，都有屬於它的光。完整介紹六大系列代表的意義、適合對象與訂製方式。',
    og_image='static/images/hero/imprint-diamond-family-portrait-jewelry.jpg',
    breadcrumbs=[('首頁', '/'), ('六大系列', None)],
    mvc_page=None,
    extra_body_class='page-series',
    content_fragment=None,
    extra_head_blocks=[],
)

JEWELRY_INDEX = PageMeta(
    route='/jewelry/',
    template='pages/jewelry/index.html',
    title='時尚珠寶｜戒指・項鍊・耳環・手鍊 DNA紀念鑽石訂製－銘印鑽石 IMPRINT DIAMOND',
    description='銘印鑽石時尚珠寶系列，提供戒指、項鍊、耳環、手鍊四大分類，以胎髮、髮絲、寵物毛髮或紀念物培育專屬 DNA 鑽石，搭配 18K/14K/9K 金與 PT950 鉑金材質，線上客製與試算，全程台灣在地實驗室培育。',
    canonical_path='jewelry/',
    og_title='時尚珠寶｜戒指・項鍊・耳環・手鍊 DNA紀念鑽石訂製－銘印鑽石 IMPRINT DIAMOND',
    og_description='銘印鑽石時尚珠寶系列，提供戒指、項鍊、耳環、手鍊四大分類，以胎髮、髮絲、寵物毛髮或紀念物培育專屬 DNA 鑽石，搭配 18K/14K/9K 金與 PT950 鉑金材質，線上客製與試算，全程台灣在地實驗室培育。',
    og_image='static/images/products/category-ring.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

JEWELRY_ENGAGEMENT = PageMeta(
    route='/jewelry/engagement/',
    template='pages/jewelry/engagement.html',
    title='求婚戒指與結髮鑽石｜培育鑽石婚戒訂製－銘印鑽石',
    description='求婚與結髮鑽石入口：以兩人髮絲共同培育 DNA 鑽石，再選經典單鑽、排鑽、復古或線戒等戒台；連結結髮系列、戒指分類與線上試算。',
    canonical_path='jewelry/engagement/',
    og_title='求婚戒指與結髮鑽石｜銘印鑽石',
    og_description='結髮 DNA 鑽石 × 求婚／婚戒戒台。先懂系列，再選款式與試算。',
    og_image='static/images/hero/imprint-diamond-wedding-couple-ring.jpg',
    breadcrumbs=[
        ('首頁', '/'),
        ('時尚珠寶', '/jewelry/'),
        ('求婚／結髮', None),
    ],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
)

SHOP_CALCULATOR = PageMeta(
    route='/shop/calculator/',
    template='pages/shop/calculator.html',
    title='品項訂製｜鑽石戒台選購試算－銘印鑽石 IMPRINT DIAMOND',
    description='線上選擇戒指、項墜、耳飾、手鍊與鍊條款式，配置克拉數、鑽石顏色、金屬成色與戒圍，即時試算參考價格並下單。',
    canonical_path='shop/calculator/',
    og_title=None,
    og_description=None,
    og_image=None,
    breadcrumbs=[],
    mvc_page=None,
    extra_body_class=None,
    content_fragment=None,
    extra_head_blocks=[],
    robots='noindex, follow',
)

JEWELRY_CATEGORY_BRACELETS = PageMeta(
    route='/jewelry/bracelets/',
    template='pages/jewelry_category.html',
    title='手鍊系列｜DNA紀念鑽石手鍊訂製－銘印鑽石 IMPRINT DIAMOND',
    description='銘印鑽石手鍊系列：以胎髮、髮絲、寵物毛髮或紀念物培育專屬 DNA 鑽石，打造獨一無二的手鍊。線上選擇克拉數、顏色、形狀與材質，立即試算參考價格，全程台灣在地實驗室培育。',
    canonical_path='jewelry/bracelets/',
    og_title='手鍊系列｜DNA紀念鑽石手鍊訂製－銘印鑽石 IMPRINT DIAMOND',
    og_description='銘印鑽石手鍊系列：以胎髮、髮絲、寵物毛髮或紀念物培育專屬 DNA 鑽石，打造獨一無二的手鍊。線上選擇克拉數、顏色、形狀與材質，立即試算參考價格，全程台灣在地實驗室培育。',
    og_image='static/images/products/category-bracelet.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('手鍊', '/jewelry/bracelets/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_category/bracelets.html',
    extra_head_blocks=['{\n  "@context": "https://schema.org",\n  "@type": "ItemList",\n  "itemListElement": [\n    {\n      "@type": "ListItem",\n      "position": 1,\n      "name": "網球手鍊",\n      "url": "https://www.imprintdiamond.com/jewelry/bracelets/tennis/"\n    },\n    {\n      "@type": "ListItem",\n      "position": 2,\n      "name": "鎖鏈手鍊",\n      "url": "https://www.imprintdiamond.com/jewelry/bracelets/chain/"\n    },\n    {\n      "@type": "ListItem",\n      "position": 3,\n      "name": "墜飾手鍊",\n      "url": "https://www.imprintdiamond.com/jewelry/bracelets/charm/"\n    },\n    {\n      "@type": "ListItem",\n      "position": 4,\n      "name": "手環",\n      "url": "https://www.imprintdiamond.com/jewelry/bracelets/bangle/"\n    }\n  ]\n}'],
)

JEWELRY_CATEGORY_EARRINGS = PageMeta(
    route='/jewelry/earrings/',
    template='pages/jewelry_category.html',
    title='耳環系列｜DNA紀念鑽石耳環訂製－銘印鑽石 IMPRINT DIAMOND',
    description='銘印鑽石耳環系列：以胎髮、髮絲、寵物毛髮或紀念物培育專屬 DNA 鑽石，打造獨一無二的耳環。線上選擇克拉數、顏色、形狀與材質，立即試算參考價格，全程台灣在地實驗室培育。',
    canonical_path='jewelry/earrings/',
    og_title='耳環系列｜DNA紀念鑽石耳環訂製－銘印鑽石 IMPRINT DIAMOND',
    og_description='銘印鑽石耳環系列：以胎髮、髮絲、寵物毛髮或紀念物培育專屬 DNA 鑽石，打造獨一無二的耳環。線上選擇克拉數、顏色、形狀與材質，立即試算參考價格，全程台灣在地實驗室培育。',
    og_image='static/images/products/category-earring.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('耳環', '/jewelry/earrings/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_category/earrings.html',
    extra_head_blocks=['{\n  "@context": "https://schema.org",\n  "@type": "ItemList",\n  "itemListElement": [\n    {\n      "@type": "ListItem",\n      "position": 1,\n      "name": "經典耳針",\n      "url": "https://www.imprintdiamond.com/jewelry/earrings/stud/"\n    },\n    {\n      "@type": "ListItem",\n      "position": 2,\n      "name": "垂墜耳環",\n      "url": "https://www.imprintdiamond.com/jewelry/earrings/drop/"\n    },\n    {\n      "@type": "ListItem",\n      "position": 3,\n      "name": "圈式耳環",\n      "url": "https://www.imprintdiamond.com/jewelry/earrings/hoop/"\n    },\n    {\n      "@type": "ListItem",\n      "position": 4,\n      "name": "耳骨夾",\n      "url": "https://www.imprintdiamond.com/jewelry/earrings/ear-cuff/"\n    }\n  ]\n}'],
)

JEWELRY_CATEGORY_NECKLACES = PageMeta(
    route='/jewelry/necklaces/',
    template='pages/jewelry_category.html',
    title='項鍊系列｜DNA紀念鑽石項鍊訂製－銘印鑽石 IMPRINT DIAMOND',
    description='銘印鑽石項鍊系列：以胎髮、髮絲、寵物毛髮或紀念物培育專屬 DNA 鑽石，打造獨一無二的項鍊。線上選擇克拉數、顏色、形狀與材質，立即試算參考價格，全程台灣在地實驗室培育。',
    canonical_path='jewelry/necklaces/',
    og_title='項鍊系列｜DNA紀念鑽石項鍊訂製－銘印鑽石 IMPRINT DIAMOND',
    og_description='銘印鑽石項鍊系列：以胎髮、髮絲、寵物毛髮或紀念物培育專屬 DNA 鑽石，打造獨一無二的項鍊。線上選擇克拉數、顏色、形狀與材質，立即試算參考價格，全程台灣在地實驗室培育。',
    og_image='static/images/products/category-necklace.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('項鍊', '/jewelry/necklaces/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_category/necklaces.html',
    extra_head_blocks=['{\n  "@context": "https://schema.org",\n  "@type": "ItemList",\n  "itemListElement": [\n    {\n      "@type": "ListItem",\n      "position": 1,\n      "name": "經典單鑽項鍊",\n      "url": "https://www.imprintdiamond.com/jewelry/necklaces/classic-pendant/"\n    },\n    {\n      "@type": "ListItem",\n      "position": 2,\n      "name": "光環墜飾項鍊",\n      "url": "https://www.imprintdiamond.com/jewelry/necklaces/halo-pendant/"\n    },\n    {\n      "@type": "ListItem",\n      "position": 3,\n      "name": "一字項鍊",\n      "url": "https://www.imprintdiamond.com/jewelry/necklaces/bar/"\n    },\n    {\n      "@type": "ListItem",\n      "position": 4,\n      "name": "雙層項鍊",\n      "url": "https://www.imprintdiamond.com/jewelry/necklaces/double-layer/"\n    }\n  ]\n}'],
)

JEWELRY_CATEGORY_RINGS = PageMeta(
    route='/jewelry/rings/',
    template='pages/jewelry_category.html',
    title='客製化鑽石戒指｜DNA 紀念戒－銘印鑽石 IMPRINT DIAMOND',
    description='客製化鑽石戒指｜以胎髮、髮絲或毛髮培育 DNA 鑽石，線上選克拉、顏色、形狀與戒台材質並試算。適合結髮婚戒與紀念戒；亦可搭配線上客製試算，全程台灣在地培育。',
    canonical_path='jewelry/rings/',
    og_title='客製化鑽石戒指｜DNA 紀念戒－銘印鑽石',
    og_description='客製化鑽石戒指：DNA 紀念鑽搭配戒台，線上試算，適合結髮婚戒與紀念戒。',
    og_image='static/images/products/category-ring.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('戒指', '/jewelry/rings/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_category/rings.html',
    extra_head_blocks=['{\n  "@context": "https://schema.org",\n  "@type": "ItemList",\n  "itemListElement": [\n    {\n      "@type": "ListItem",\n      "position": 1,\n      "name": "經典單鑽戒指",\n      "url": "https://www.imprintdiamond.com/jewelry/rings/classic-solitaire/"\n    },\n    {\n      "@type": "ListItem",\n      "position": 2,\n      "name": "華麗排鑽戒指",\n      "url": "https://www.imprintdiamond.com/jewelry/rings/pave-halo/"\n    },\n    {\n      "@type": "ListItem",\n      "position": 3,\n      "name": "復古藤蔓戒指",\n      "url": "https://www.imprintdiamond.com/jewelry/rings/vintage-vine/"\n    },\n    {\n      "@type": "ListItem",\n      "position": 4,\n      "name": "極簡線戒",\n      "url": "https://www.imprintdiamond.com/jewelry/rings/modern-band/"\n    }\n  ]\n}'],
)

JEWELRY_STYLE_BRACELETS_BANGLE = PageMeta(
    route='/jewelry/bracelets/bangle/',
    template='pages/jewelry_style.html',
    title='手環｜手鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='硬版手環設計，鑽石鑲嵌其中，線條俐落有型，適合喜歡簡約俐落風格的您。。手環可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/bracelets/bangle/',
    og_title='手環｜手鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='硬版手環設計，鑽石鑲嵌其中，線條俐落有型，適合喜歡簡約俐落風格的您。。手環可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/bracelet-bangle-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('手鍊', '/jewelry/bracelets/'), ('手環', '/jewelry/bracelets/bangle/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/bracelets-bangle.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"手環\",\n  \"description\": \"硬版手環設計，鑽石鑲嵌其中，線條俐落有型，適合喜歡簡約俐落風格的您。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/bracelet-bangle-1.jpg\",\n  \"category\": \"Jewelry > 手鍊\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"40000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/bracelets/bangle/\"\n  }\n}'],
)

JEWELRY_STYLE_BRACELETS_CHAIN = PageMeta(
    route='/jewelry/bracelets/chain/',
    template='pages/jewelry_style.html',
    title='鎖鏈手鍊｜手鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='鍊節式設計搭配鑽石墜飾，適合與其他手鍊或手環疊戴，打造層次豐富的手部造型。。鎖鏈手鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/bracelets/chain/',
    og_title='鎖鏈手鍊｜手鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='鍊節式設計搭配鑽石墜飾，適合與其他手鍊或手環疊戴，打造層次豐富的手部造型。。鎖鏈手鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/bracelet-chain-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('手鍊', '/jewelry/bracelets/'), ('鎖鏈手鍊', '/jewelry/bracelets/chain/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/bracelets-chain.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"鎖鏈手鍊\",\n  \"description\": \"鍊節式設計搭配鑽石墜飾，適合與其他手鍊或手環疊戴，打造層次豐富的手部造型。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/bracelet-chain-1.jpg\",\n  \"category\": \"Jewelry > 手鍊\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"40000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/bracelets/chain/\"\n  }\n}'],
)

JEWELRY_STYLE_BRACELETS_CHARM = PageMeta(
    route='/jewelry/bracelets/charm/',
    template='pages/jewelry_style.html',
    title='墜飾手鍊｜手鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='單顆鑽石墜飾垂墜於鍊身之上，隨手腕擺動輕輕搖曳，溫柔而不張揚。。墜飾手鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/bracelets/charm/',
    og_title='墜飾手鍊｜手鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='單顆鑽石墜飾垂墜於鍊身之上，隨手腕擺動輕輕搖曳，溫柔而不張揚。。墜飾手鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/bracelet-charm-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('手鍊', '/jewelry/bracelets/'), ('墜飾手鍊', '/jewelry/bracelets/charm/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/bracelets-charm.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"墜飾手鍊\",\n  \"description\": \"單顆鑽石墜飾垂墜於鍊身之上，隨手腕擺動輕輕搖曳，溫柔而不張揚。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/bracelet-charm-1.jpg\",\n  \"category\": \"Jewelry > 手鍊\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"40000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/bracelets/charm/\"\n  }\n}'],
)

JEWELRY_STYLE_BRACELETS_TENNIS = PageMeta(
    route='/jewelry/bracelets/tennis/',
    template='pages/jewelry_style.html',
    title='網球手鍊｜手鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='鑽石以鍊狀方式排列環繞手腕一圈，光芒連續不間斷，是經典不敗的手鍊款式。。網球手鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/bracelets/tennis/',
    og_title='網球手鍊｜手鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='鑽石以鍊狀方式排列環繞手腕一圈，光芒連續不間斷，是經典不敗的手鍊款式。。網球手鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/bracelet-tennis-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('手鍊', '/jewelry/bracelets/'), ('網球手鍊', '/jewelry/bracelets/tennis/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/bracelets-tennis.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"網球手鍊\",\n  \"description\": \"鑽石以鍊狀方式排列環繞手腕一圈，光芒連續不間斷，是經典不敗的手鍊款式。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/bracelet-tennis-1.jpg\",\n  \"category\": \"Jewelry > 手鍊\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"40000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/bracelets/tennis/\"\n  }\n}'],
)

JEWELRY_STYLE_EARRINGS_DROP = PageMeta(
    route='/jewelry/earrings/drop/',
    template='pages/jewelry_style.html',
    title='垂墜耳環｜耳環客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='鑽石垂墜於耳下，隨著步伐輕輕搖曳，為整體造型增添柔美與動態感。。垂墜耳環可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/earrings/drop/',
    og_title='垂墜耳環｜耳環客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='鑽石垂墜於耳下，隨著步伐輕輕搖曳，為整體造型增添柔美與動態感。。垂墜耳環可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/earring-drop-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('耳環', '/jewelry/earrings/'), ('垂墜耳環', '/jewelry/earrings/drop/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/earrings-drop.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"垂墜耳環\",\n  \"description\": \"鑽石垂墜於耳下，隨著步伐輕輕搖曳，為整體造型增添柔美與動態感。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/earring-drop-1.jpg\",\n  \"category\": \"Jewelry > 耳環\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"62000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/earrings/drop/\"\n  }\n}'],
)

JEWELRY_STYLE_EARRINGS_EAR_CUFF = PageMeta(
    route='/jewelry/earrings/ear-cuff/',
    template='pages/jewelry_style.html',
    title='耳骨夾｜耳環客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='無需穿耳洞即可配戴的耳骨夾設計，鑽石鑲嵌於夾式耳骨環上，個性又百搭。。耳骨夾可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/earrings/ear-cuff/',
    og_title='耳骨夾｜耳環客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='無需穿耳洞即可配戴的耳骨夾設計，鑽石鑲嵌於夾式耳骨環上，個性又百搭。。耳骨夾可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/earring-ear-cuff-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('耳環', '/jewelry/earrings/'), ('耳骨夾', '/jewelry/earrings/ear-cuff/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/earrings-ear-cuff.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"耳骨夾\",\n  \"description\": \"無需穿耳洞即可配戴的耳骨夾設計，鑽石鑲嵌於夾式耳骨環上，個性又百搭。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/earring-ear-cuff-1.jpg\",\n  \"category\": \"Jewelry > 耳環\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"62000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/earrings/ear-cuff/\"\n  }\n}'],
)

JEWELRY_STYLE_EARRINGS_HOOP = PageMeta(
    route='/jewelry/earrings/hoop/',
    template='pages/jewelry_style.html',
    title='圈式耳環｜耳環客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='鑽石鑲嵌於俐落的圈環之上，線條簡潔有型，適合喜歡俐落風格的您。。圈式耳環可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/earrings/hoop/',
    og_title='圈式耳環｜耳環客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='鑽石鑲嵌於俐落的圈環之上，線條簡潔有型，適合喜歡俐落風格的您。。圈式耳環可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/earring-hoop-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('耳環', '/jewelry/earrings/'), ('圈式耳環', '/jewelry/earrings/hoop/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/earrings-hoop.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"圈式耳環\",\n  \"description\": \"鑽石鑲嵌於俐落的圈環之上，線條簡潔有型，適合喜歡俐落風格的您。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/earring-hoop-1.jpg\",\n  \"category\": \"Jewelry > 耳環\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"62000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/earrings/hoop/\"\n  }\n}'],
)

JEWELRY_STYLE_EARRINGS_STUD = PageMeta(
    route='/jewelry/earrings/stud/',
    template='pages/jewelry_style.html',
    title='經典耳針｜耳環客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='鑽石緊貼耳垂配戴，款式簡約百搭，是最適合日常配戴的耳環款式。。經典耳針可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/earrings/stud/',
    og_title='經典耳針｜耳環客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='鑽石緊貼耳垂配戴，款式簡約百搭，是最適合日常配戴的耳環款式。。經典耳針可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/earring-stud-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('耳環', '/jewelry/earrings/'), ('經典耳針', '/jewelry/earrings/stud/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/earrings-stud.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"經典耳針\",\n  \"description\": \"鑽石緊貼耳垂配戴，款式簡約百搭，是最適合日常配戴的耳環款式。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/earring-stud-1.jpg\",\n  \"category\": \"Jewelry > 耳環\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"62000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/earrings/stud/\"\n  }\n}'],
)

JEWELRY_STYLE_NECKLACES_BAR = PageMeta(
    route='/jewelry/necklaces/bar/',
    template='pages/jewelry_style.html',
    title='一字項鍊｜項鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='細長墜飾如一字排開，適合刻上重要的日期或文字，是紀念意義濃厚的簡約款式。。一字項鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/necklaces/bar/',
    og_title='一字項鍊｜項鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='細長墜飾如一字排開，適合刻上重要的日期或文字，是紀念意義濃厚的簡約款式。。一字項鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/necklace-bar-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('項鍊', '/jewelry/necklaces/'), ('一字項鍊', '/jewelry/necklaces/bar/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/necklaces-bar.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"一字項鍊\",\n  \"description\": \"細長墜飾如一字排開，適合刻上重要的日期或文字，是紀念意義濃厚的簡約款式。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/necklace-bar-1.jpg\",\n  \"category\": \"Jewelry > 項鍊\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"34000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/necklaces/bar/\"\n  }\n}'],
)

JEWELRY_STYLE_NECKLACES_CLASSIC_PENDANT = PageMeta(
    route='/jewelry/necklaces/classic-pendant/',
    template='pages/jewelry_style.html',
    title='經典單鑽項鍊｜項鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='單顆主石垂墜於鍊身正中央，簡單卻最能凸顯鑽石本身的光芒，適合單獨配戴或作為紀念送禮首選。。經典單鑽項鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/necklaces/classic-pendant/',
    og_title='經典單鑽項鍊｜項鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='單顆主石垂墜於鍊身正中央，簡單卻最能凸顯鑽石本身的光芒，適合單獨配戴或作為紀念送禮首選。。經典單鑽項鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/necklace-classic-pendant-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('項鍊', '/jewelry/necklaces/'), ('經典單鑽項鍊', '/jewelry/necklaces/classic-pendant/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/necklaces-classic-pendant.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"經典單鑽項鍊\",\n  \"description\": \"單顆主石垂墜於鍊身正中央，簡單卻最能凸顯鑽石本身的光芒，適合單獨配戴或作為紀念送禮首選。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/necklace-classic-pendant-1.jpg\",\n  \"category\": \"Jewelry > 項鍊\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"34000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/necklaces/classic-pendant/\"\n  }\n}'],
)

JEWELRY_STYLE_NECKLACES_DOUBLE_LAYER = PageMeta(
    route='/jewelry/necklaces/double-layer/',
    template='pages/jewelry_style.html',
    title='雙層項鍊｜項鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='雙層鍊身設計，可分別鑲嵌兩顆鑽石，適合同時紀念兩位重要的人，或紀念不同階段的重要時刻。。雙層項鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/necklaces/double-layer/',
    og_title='雙層項鍊｜項鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='雙層鍊身設計，可分別鑲嵌兩顆鑽石，適合同時紀念兩位重要的人，或紀念不同階段的重要時刻。。雙層項鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/necklace-double-layer-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('項鍊', '/jewelry/necklaces/'), ('雙層項鍊', '/jewelry/necklaces/double-layer/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/necklaces-double-layer.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"雙層項鍊\",\n  \"description\": \"雙層鍊身設計，可分別鑲嵌兩顆鑽石，適合同時紀念兩位重要的人，或紀念不同階段的重要時刻。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/necklace-double-layer-1.jpg\",\n  \"category\": \"Jewelry > 項鍊\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"34000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/necklaces/double-layer/\"\n  }\n}'],
)

JEWELRY_STYLE_NECKLACES_HALO_PENDANT = PageMeta(
    route='/jewelry/necklaces/halo-pendant/',
    template='pages/jewelry_style.html',
    title='光環墜飾項鍊｜項鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='主石周圍鑲嵌一圈小鑽，讓墜飾視覺份量更飽滿，光芒層次也更豐富。。光環墜飾項鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/necklaces/halo-pendant/',
    og_title='光環墜飾項鍊｜項鍊客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='主石周圍鑲嵌一圈小鑽，讓墜飾視覺份量更飽滿，光芒層次也更豐富。。光環墜飾項鍊可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/necklace-halo-pendant-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('項鍊', '/jewelry/necklaces/'), ('光環墜飾項鍊', '/jewelry/necklaces/halo-pendant/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/necklaces-halo-pendant.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"光環墜飾項鍊\",\n  \"description\": \"主石周圍鑲嵌一圈小鑽，讓墜飾視覺份量更飽滿，光芒層次也更豐富。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/necklace-halo-pendant-1.jpg\",\n  \"category\": \"Jewelry > 項鍊\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"34000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/necklaces/halo-pendant/\"\n  }\n}'],
)

JEWELRY_STYLE_RINGS_CLASSIC_SOLITAIRE = PageMeta(
    route='/jewelry/rings/classic-solitaire/',
    template='pages/jewelry_style.html',
    title='經典單鑽戒指｜戒指客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='單一主石鑲嵌於簡約戒台之上，線條乾淨俐落，適合各種手型與風格，是最經典也最百搭的款式。。經典單鑽戒指可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/rings/classic-solitaire/',
    og_title='經典單鑽戒指｜戒指客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='單一主石鑲嵌於簡約戒台之上，線條乾淨俐落，適合各種手型與風格，是最經典也最百搭的款式。。經典單鑽戒指可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/ring-classic-solitaire-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('戒指', '/jewelry/rings/'), ('經典單鑽戒指', '/jewelry/rings/classic-solitaire/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/rings-classic-solitaire.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"經典單鑽戒指\",\n  \"description\": \"單一主石鑲嵌於簡約戒台之上，線條乾淨俐落，適合各種手型與風格，是最經典也最百搭的款式。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/ring-classic-solitaire-1.jpg\",\n  \"category\": \"Jewelry > 戒指\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"36000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/rings/classic-solitaire/\"\n  }\n}'],
)

JEWELRY_STYLE_RINGS_MODERN_BAND = PageMeta(
    route='/jewelry/rings/modern-band/',
    template='pages/jewelry_style.html',
    title='極簡線戒｜戒指客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='極簡戒環設計，鑽石鑲嵌方式低調內斂，適合疊戴，也適合作為日常配戴的第一枚紀念戒指。。極簡線戒可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/rings/modern-band/',
    og_title='極簡線戒｜戒指客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='極簡戒環設計，鑽石鑲嵌方式低調內斂，適合疊戴，也適合作為日常配戴的第一枚紀念戒指。。極簡線戒可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/ring-modern-band-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('戒指', '/jewelry/rings/'), ('極簡線戒', '/jewelry/rings/modern-band/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/rings-modern-band.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"極簡線戒\",\n  \"description\": \"極簡戒環設計，鑽石鑲嵌方式低調內斂，適合疊戴，也適合作為日常配戴的第一枚紀念戒指。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/ring-modern-band-1.jpg\",\n  \"category\": \"Jewelry > 戒指\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"36000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/rings/modern-band/\"\n  }\n}'],
)

JEWELRY_STYLE_RINGS_PAVE_HALO = PageMeta(
    route='/jewelry/rings/pave-halo/',
    template='pages/jewelry_style.html',
    title='華麗排鑽戒指｜戒指客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='主石周圍以一圈小鑽環繞鑲嵌，讓整體視覺份量感更足，光芒也更為集中閃耀，適合重要場合配戴。。華麗排鑽戒指可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/rings/pave-halo/',
    og_title='華麗排鑽戒指｜戒指客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='主石周圍以一圈小鑽環繞鑲嵌，讓整體視覺份量感更足，光芒也更為集中閃耀，適合重要場合配戴。。華麗排鑽戒指可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/ring-pave-halo-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('戒指', '/jewelry/rings/'), ('華麗排鑽戒指', '/jewelry/rings/pave-halo/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/rings-pave-halo.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"華麗排鑽戒指\",\n  \"description\": \"主石周圍以一圈小鑽環繞鑲嵌，讓整體視覺份量感更足，光芒也更為集中閃耀，適合重要場合配戴。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/ring-pave-halo-1.jpg\",\n  \"category\": \"Jewelry > 戒指\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"36000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/rings/pave-halo/\"\n  }\n}'],
)

JEWELRY_STYLE_RINGS_VINTAGE_VINE = PageMeta(
    route='/jewelry/rings/vintage-vine/',
    template='pages/jewelry_style.html',
    title='復古藤蔓戒指｜戒指客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='戒台線條如藤蔓般蜿蜒纏繞，帶有復古細節與溫潤手感，適合喜歡低調精緻風格的您。。復古藤蔓戒指可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    canonical_path='jewelry/rings/vintage-vine/',
    og_title='復古藤蔓戒指｜戒指客製鑽石－銘印鑽石 IMPRINT DIAMOND',
    og_description='戒台線條如藤蔓般蜿蜒纏繞，帶有復古細節與溫潤手感，適合喜歡低調精緻風格的您。。復古藤蔓戒指可線上選擇克拉數、鑽石顏色、形狀與材質成色，系統即時試算參考價格，全程台灣在地 DNA 鑽石實驗室培育，打造獨一無二的紀念珍藏。',
    og_image='static/images/products/ring-vintage-vine-1.jpg',
    breadcrumbs=[('首頁', '/'), ('時尚珠寶', '/jewelry/'), ('戒指', '/jewelry/rings/'), ('復古藤蔓戒指', '/jewelry/rings/vintage-vine/')],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='jewelry_style/rings-vintage-vine.html',
    extra_head_blocks=['{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Product\",\n  \"name\": \"復古藤蔓戒指\",\n  \"description\": \"戒台線條如藤蔓般蜿蜒纏繞，帶有復古細節與溫潤手感，適合喜歡低調精緻風格的您。\",\n  \"image\": \"https://www.imprintdiamond.com/static/images/products/ring-vintage-vine-1.jpg\",\n  \"category\": \"Jewelry > 戒指\",\n  \"brand\": {\n    \"@type\": \"Brand\",\n    \"name\": \"銘印鑽石 IMPRINT DIAMOND\"\n  },\n  \"offers\": {\n    \"@type\": \"AggregateOffer\",\n    \"priceCurrency\": \"TWD\",\n    \"lowPrice\": \"36000\",\n    \"highPrice\": \"990000\",\n    \"offerCount\": \"12\",\n    \"availability\": \"https://schema.org/InStock\",\n    \"url\": \"https://www.imprintdiamond.com/jewelry/rings/vintage-vine/\"\n  }\n}'],
)

SERIES_FAMILY = PageMeta(
    route='/series/family/',
    template='pages/series_detail.html',
    title='全家福鑽石｜全家人髮絲紀念鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='全家福鑽石｜集合全家人髮絲，培育成一顆象徵家族連結的紀念鑽石。全程台灣在地培育；線上試算克拉與款式，讓「我們一直都在一起」成為可以傳承的珍藏。',
    canonical_path='series/family/',
    og_title='全家福鑽石｜全家人髮絲紀念鑽石－銘印鑽石',
    og_description='集合全家人髮絲凝成一顆鑽石，讓家的記憶成為可以傳承的珍藏。',
    og_image='static/images/hero/imprint-diamond-family-portrait-jewelry.jpg',
    breadcrumbs=[('首頁', '/'), ('六大系列', '/series'), ('全家福鑽石', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='series/family.html',
    extra_head_blocks=['{\n  "@context": "https://schema.org",\n  "@type": "FAQPage",\n  "mainEntity": [\n    {\n      "@type": "Question",\n      "name": "全家福鑽石要收集哪些人的頭髮？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "可集合每一位家人的髮絲共同培育；合計約一顆雞蛋大小即可。人數較多時，請先 LINE 與顧問討論比例與份量。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "適合什麼時候訂製？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "常見於長輩生日、結婚紀念或家族團聚時訂製，把「一家人」留成可傳承的紀念鑽石。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "可以只做一顆給全家族嗎？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "可以。全家福鑽石通常做成一顆共享的家族信物，也可依需求討論顆數與鑲嵌方式。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "製作需要多久？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "全程台灣在地實驗室，約 70–90 天交付，附銘印保證卡與專屬影音紀念盒。"\n      }\n    }\n  ]\n}'],
)

SERIES_FIRST_LOVE = PageMeta(
    route='/series/first-love/',
    template='pages/series_detail.html',
    title='滿月鑽石｜初生胎髮紀念鑽石－銘印鑽石 IMPRINT DIAMOND',
    description='滿月鑽石｜以寶寶胎髮培育初生紀念鑽石，珍藏生命最初印記。全程台灣在地培育，可鑲嵌項鍊或戒指；線上試算克拉與款式，附銘印保證卡與影音紀念盒。',
    canonical_path='series/first-love/',
    og_title='滿月鑽石｜初生胎髮紀念鑽石－銘印鑽石',
    og_description='滿月／初生胎髮紀念鑽石：珍藏生命最初印記，台灣在地培育。',
    og_image='static/images/hero/imprint-diamond-newborn-baby-necklace.jpg',
    breadcrumbs=[('首頁', '/'), ('六大系列', '/series'), ('滿月鑽石', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='series/first-love.html',
    extra_head_blocks=['{\n  "@context": "https://schema.org",\n  "@type": "FAQPage",\n  "mainEntity": [\n    {\n      "@type": "Question",\n      "name": "滿月鑽石和初生鑽石是同一系列嗎？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "滿月鑽石系列即以寶寶胎髮培育的初生紀念鑽石，珍藏生命最初印記；名稱因紀念時機（滿月剃髮）而常用「滿月鑽石」。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "胎髮要準備多少？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "約一顆雞蛋大小即可。若剃髮量不足，請先透過官方 LINE 與顧問確認，不必先寄送樣本。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "可以做成項鍊嗎？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "可以。完成後可鑲嵌為項鍊、戒指等，成為陪伴孩子成長的傳家珍藏。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "製作需要多久？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "全程台灣在地實驗室，約 70–90 天交付，附銘印保證卡與專屬影音紀念盒。"\n      }\n    }\n  ]\n}'],
)

SERIES_HEIRLOOM = PageMeta(
    route='/series/heirloom/',
    template='pages/series_detail.html',
    title='骨灰鑽石｜生命鑽石紀念訂製－銘印鑽石 IMPRINT DIAMOND',
    description='骨灰鑽石與生命鑽石｜以親人毛髮或骨灰（約 3 至 5 公克）在台灣培育紀念鑽石，樣本不送海外。線上試算克拉與款式；附銘印保證卡，0.20 克拉以上可代送 GIA／IGI 鑑定。',
    canonical_path='series/heirloom/',
    og_title='骨灰鑽石｜生命鑽石紀念訂製－銘印鑽石',
    og_description='骨灰鑽石／生命鑽石：親人毛髮或骨灰在台灣培育，樣本不送海外，可代送鑑定。',
    og_image='static/images/hero/imprint-diamond-heirloom-memorial.jpg',
    breadcrumbs=[('首頁', '/'), ('六大系列', '/series'), ('生命鑽石', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='series/heirloom.html',
    extra_head_blocks=['{\n  "@context": "https://schema.org",\n  "@type": "FAQPage",\n  "mainEntity": [\n    {\n      "@type": "Question",\n      "name": "什麼是骨灰鑽石／生命鑽石？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "生命鑽石以親人毛髮或骨灰培育而成；骨灰約需 3 至 5 公克、毛髮約一顆雞蛋大小。樣本在台灣在地實驗室處理，不送海外。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "骨灰份量不夠怎麼辦？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "若不確定份量是否足夠，請先透過官方 LINE 與顧問確認，不需要先寄送樣本。顧問會依實際狀況給建議。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "有國際鑑定嗎？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "每顆附銘印保證卡；0.20 克拉以上可代送 GIA 或 IGI 國際鑑定（費用另計），讓珍藏在傳承時有正式身分證明。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "寵物骨灰也能做嗎？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "可以。寵物骨灰同樣可走生命鑽石流程；若以毛髮紀念毛孩，也可參考寵物鑽石系列。"\n      }\n    }\n  ]\n}'],
)

SERIES_LOVE = PageMeta(
    route='/series/love/',
    template='pages/series_detail.html',
    title='結髮鑽石｜培育鑽石婚戒訂製－銘印鑽石 IMPRINT DIAMOND',
    description='結髮鑽石｜以夫妻髮絲共同培育鑽石，可鑲嵌為培育鑽石婚戒或對戒。全程台灣在地製作；可先線上試算，或預約門市與顧問討論克拉、戒台與預算。',
    canonical_path='series/love/',
    og_title='結髮鑽石｜培育鑽石婚戒訂製－銘印鑽石',
    og_description='結髮鑽石與培育鑽石婚戒：兩人髮絲共同培育，可線上試算或預約。',
    og_image='static/images/hero/imprint-diamond-wedding-couple-ring.jpg',
    breadcrumbs=[('首頁', '/'), ('六大系列', '/series'), ('結髮鑽石', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='series/love.html',
    extra_head_blocks=['{\n  "@context": "https://schema.org",\n  "@type": "FAQPage",\n  "mainEntity": [\n    {\n      "@type": "Question",\n      "name": "結髮鑽石適合做婚戒嗎？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "很適合作為培育鑽石婚戒或對戒主石。兩人髮絲共同培育一顆鑽石後，可至戒指系列選戒台，或先到線上試算規格。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "兩人需要準備多少頭髮？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "兩人合計約一顆雞蛋大小即可。若不確定份量，請先透過官方 LINE 與顧問確認。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "可以只訂鑽石再鑲戒嗎？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "可以。鑽石完成後可鑲嵌為戒指、項鍊等；戒台材質可選 18K／14K／9K 金或 PT950 鉑金。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "可以預約看款嗎？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "可以。門市在新北市三重區福德南路 43 號 1 樓（預約制），也可先 LINE 預約討論結髮鑽石與婚戒需求。"\n      }\n    }\n  ]\n}'],
)

SERIES_PET = PageMeta(
    route='/series/pet/',
    template='pages/series_detail.html',
    title='寵物鑽石｜毛髮紀念與寵物紀念品－銘印鑽石 IMPRINT DIAMOND',
    description='寵物鑽石｜以毛孩毛髮在台灣培育專屬紀念鑽石，也可作為可傳承的寵物紀念品。毛髮約一顆雞蛋大小即可訂製；線上試算克拉與款式，全程在地實驗室，約 70–90 天交付。',
    canonical_path='series/pet/',
    og_title='寵物鑽石｜毛髮紀念與寵物紀念品－銘印鑽石',
    og_description='以毛孩毛髮培育專屬寵物鑽石，亦可作為可傳承的寵物紀念品；台灣在地實驗室。',
    og_image='static/images/hero/imprint-diamond-pet-memorial-cat.jpg',
    breadcrumbs=[('首頁', '/'), ('六大系列', '/series'), ('寵物鑽石', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='series/pet.html',
    extra_head_blocks=['{\n  "@context": "https://schema.org",\n  "@type": "FAQPage",\n  "mainEntity": [\n    {\n      "@type": "Question",\n      "name": "寵物鑽石需要準備多少毛髮？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "毛髮約需一顆雞蛋大小（或養樂多瓶約 8 分滿）即可訂製寵物鑽石。若毛量不足，請先透過官方 LINE 與顧問確認，不必先寄送樣本。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "寵物毛髮鑽石和寵物紀念品有何不同？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "寵物鑽石是以毛孩毛髮在台灣培育成真實鑽石，可鑲嵌為飾品；也常作為可傳承的寵物紀念品。成品附銘印保證卡與專屬影音紀念盒。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "寵物骨灰可以做成鑽石嗎？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "可以。若您手邊是寵物骨灰，請改看生命鑽石（骨灰鑽石）系列；寵物系列頁也提供連到生命鑽石的說明，顧問會依樣本類型協助評估。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "製作需要多久？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "全程於台灣在地實驗室完成，約 70–90 天交付，單一客戶、單一培育流程。"\n      }\n    }\n  ]\n}'],
)

SERIES_SIGNATURE = PageMeta(
    route='/series/signature/',
    template='pages/series_detail.html',
    title='真我鑽石｜Signature 專屬訂製－銘印鑽石 IMPRINT DIAMOND',
    description='真我鑽石（Signature）｜以自己的髮絲，萃煉成獨一無二的鑽石，獻給值得被自己慶祝的此刻。全程台灣在地培育，可線上試算並由專屬顧問確認細節。',
    canonical_path='series/signature/',
    og_title='真我鑽石｜Signature 專屬 DNA 鑽石－銘印鑽石',
    og_description='真我鑽石（Signature）：以自己的髮絲萃煉成獨一無二的鑽石，獻給值得被自己慶祝的此刻。',
    og_image='static/images/hero/imprint-diamond-wedding-couple-ring.jpg',
    breadcrumbs=[('首頁', '/'), ('六大系列', '/series'), ('真我鑽石', None)],
    mvc_page=None,
    extra_body_class=None,
    content_fragment='series/signature.html',
    extra_head_blocks=['{\n  "@context": "https://schema.org",\n  "@type": "FAQPage",\n  "mainEntity": [\n    {\n      "@type": "Question",\n      "name": "真我鑽石可以使用哪些樣本？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "可依您的故事討論毛髮，正式評估由專屬顧問協助。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "可以自己決定鑽石與飾品款式嗎？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "可以。克拉數、形狀、顏色、金屬材質與鑲嵌形式，都會依您的故事與預算一對一確認。"\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "製作需要多久？",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "全程於台灣在地實驗室完成，通常約 70～90 天交付，並附銘印保證卡與專屬影音紀念盒。"\n      }\n    }\n  ]\n}'],
)


STANDALONE_QUOTE_SHEET = PageMeta(
    route='/shop/quote-sheet',
    template='pages/shop/quote-sheet.html',
    title='珠寶報價單｜銘印鑽石',
    description='',
    canonical_path='shop/quote-sheet',
    robots='noindex, nofollow',
)

STANDALONE_QUOTE_SHEET_SHORT = PageMeta(
    route='/quote-sheet',
    template='pages/shop/quote-sheet.html',
    title='珠寶報價單｜銘印鑽石',
    description='',
    canonical_path='quote-sheet',
    robots='noindex, nofollow',
)

STANDALONE_SHARE_SUMMARY = PageMeta(
    route='/share/summary',
    template='pages/share/summary.html',
    title='分享試算｜銘印鑽石',
    description='',
    canonical_path='share/summary',
    robots='noindex, nofollow',
)


ALL_PAGES: list[PageMeta] = [
    HOME,
    PAGE_404,
    PAGE_ABOUT,
    PAGE_ACCOUNT,
    PAGE_CART,
    PAGE_CHECKOUT,
    PAGE_CONTACT,
    PAGE_FAQ,
    PAGE_FAVORITES,
    PAGE_GOLD_PRICE,
    PAGE_HISTORY,
    PAGE_JOURNAL,
    PAGE_LOGIN,
    PAGE_LOGIN_2FA,
    PAGE_ACCOUNT_SECURITY,
    PAGE_NOTIFICATIONS,
    PAGE_PRICE,
    PAGE_PRIVACY,
    PAGE_TERMS,
    PAGE_RETURN_POLICY,
    PAGE_PROFILE,
    PAGE_REGISTER,
    PAGE_RESET_PASSWORD,
    PAGE_FORGOT_PASSWORD,
    PAGE_STORIES,
    PAGE_SUCCESS,
    PAGE_TRACK_ORDER,
    PAGE_WHAT_IS_DNA_DIAMOND,
    PAGE_DIAMOND_4C,
    PAGE_LAB_GROWN_DIAMOND,
    PAGE_DIAMOND_COMPARISON,
    PAGE_SERIES,
    JEWELRY_INDEX,
    JEWELRY_ENGAGEMENT,
    SHOP_CALCULATOR,
    JEWELRY_CATEGORY_BRACELETS,
    JEWELRY_CATEGORY_EARRINGS,
    JEWELRY_CATEGORY_NECKLACES,
    JEWELRY_CATEGORY_RINGS,
    JEWELRY_STYLE_BRACELETS_BANGLE,
    JEWELRY_STYLE_BRACELETS_CHAIN,
    JEWELRY_STYLE_BRACELETS_CHARM,
    JEWELRY_STYLE_BRACELETS_TENNIS,
    JEWELRY_STYLE_EARRINGS_DROP,
    JEWELRY_STYLE_EARRINGS_EAR_CUFF,
    JEWELRY_STYLE_EARRINGS_HOOP,
    JEWELRY_STYLE_EARRINGS_STUD,
    JEWELRY_STYLE_NECKLACES_BAR,
    JEWELRY_STYLE_NECKLACES_CLASSIC_PENDANT,
    JEWELRY_STYLE_NECKLACES_DOUBLE_LAYER,
    JEWELRY_STYLE_NECKLACES_HALO_PENDANT,
    JEWELRY_STYLE_RINGS_CLASSIC_SOLITAIRE,
    JEWELRY_STYLE_RINGS_MODERN_BAND,
    JEWELRY_STYLE_RINGS_PAVE_HALO,
    JEWELRY_STYLE_RINGS_VINTAGE_VINE,
    SERIES_FAMILY,
    SERIES_FIRST_LOVE,
    SERIES_HEIRLOOM,
    SERIES_LOVE,
    SERIES_PET,
    SERIES_SIGNATURE,
]


STANDALONE_PAGES: list[PageMeta] = [
    STANDALONE_QUOTE_SHEET,
    STANDALONE_QUOTE_SHEET_SHORT,
    STANDALONE_SHARE_SUMMARY,
]
