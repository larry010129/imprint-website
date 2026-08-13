"""Home banner phone crop (image_url_mobile) must reach ≤900px picture sources."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME_BANNERS = ROOT / "public" / "js" / "home-banners.js"
INDEX = ROOT / "content" / "site" / "templates" / "pages" / "index.html"


def test_home_banners_honors_mobile_crop_on_memorial_slide():
    src = HOME_BANNERS.read_text(encoding="utf-8")
    # Memorial desktop LCP path still exists…
    assert "function memorialPicture" in src
    assert "MEMORIAL_MOBILE" in src
    # …but phone crop override must be wired through.
    assert "memorialPicture(sourceAttr, mobileValue)" in src
    assert "mobileOverride" in src
    # matchesSsr must see image_url_mobile or CMS phone crops never apply.
    assert "norm(b.image_url_mobile || '')" in src
    assert "assetKey" in src
    # Phone <img> must use phone crop URL — never desktop — when admin crop set.
    assert "var imgSrc = mobileValue || MEMORIAL_IMG;" in src
    assert 'media="(min-width:901px)"' in src
    assert "b.image_url || desktop" not in src
    # Desktop must not ride along on <img srcset> (phone-safe only).
    assert "MEMORIAL_MOBILE + ', ' + MEMORIAL_DESKTOP" not in src
    assert "localHeroMobileSrcset(stem) + ', ' + desktopSrcset" not in src


def test_home_first_slide_matches_banner_seed():
    """SSR slide 0 must match banners-seed so home-banners.js skips rebuild (no hero jump)."""
    import json
    import re

    seed = json.loads((ROOT / "app" / "data" / "banners-seed.json").read_text(encoding="utf-8"))
    html = INDEX.read_text(encoding="utf-8")
    first = seed[0]
    m = re.search(
        r'<li class="hc-slide is-active".*?</li>',
        html,
        re.DOTALL,
    )
    assert m, "active hero slide missing"
    slide = m.group(0)
    title_m = re.search(r"<h1 class=\"gh-hero__title\"[^>]*>(.*?)</h1>", slide, re.DOTALL)
    lead_m = re.search(r"<p class=\"gh-hero__lead\"[^>]*>(.*?)</p>", slide, re.DOTALL)
    assert title_m and lead_m
    title = re.sub(r"<[^>]+>", "", title_m.group(1))
    lead = re.sub(r"<[^>]+>", "", lead_m.group(1))
    assert " ".join(title.split()) == first["title"]
    assert " ".join(lead.split()) == first["lead"]
    assert "銘印鑽石｜" not in slide


def test_home_banners_cache_bust():
    html = INDEX.read_text(encoding="utf-8")
    assert "home-banners.js?v=13" in html
    # Phone crops must not wait on 10s below-fold delay.
    assert "HOME_EXTRAS_MS" not in html
    assert "inject('/static/js/home-banners.js?v=13');" in html
    assert "aspect-ratio:800/388" not in html


def test_home_banners_refresh_asap():
    src = HOME_BANNERS.read_text(encoding="utf-8")
    assert "timeout: 800" in src
    assert "DOMContentLoaded" in src
    assert "window.addEventListener('load', scheduleRefresh" not in src

def test_home_hero_slides_use_responsive_webp_srcset():
    html = INDEX.read_text(encoding="utf-8")
    stems = [
        "imprint-diamond-newborn-baby-necklace",
        "imprint-diamond-pet-memorial-cat",
        "imprint-diamond-wedding-couple-ring",
        "imprint-diamond-family-portrait-jewelry",
        "imprint-diamond-heirloom-memorial",
    ]
    for stem in stems:
        assert f"{stem}-400w.webp 400w" in html
        assert f"{stem}-800w.webp 800w" in html
        assert f"{stem}-1200w.webp 1200w" in html


def test_home_series_cards_use_local_hero_srcset():
    html = INDEX.read_text(encoding="utf-8")
    for slot, stem in (
        ("series-first-love", "imprint-diamond-newborn-baby-necklace"),
        ("series-pet", "imprint-diamond-pet-memorial-cat"),
        ("series-love", "imprint-diamond-wedding-couple-ring"),
        ("series-family", "imprint-diamond-family-portrait-jewelry"),
        ("series-heirloom", "imprint-diamond-heirloom-memorial"),
    ):
        assert f'data-cms-slot="{slot}"' in html
        assert f"/static/images/hero/{stem}-800w.webp" in html
    assert 'src="/static/images/diamonds/colors/blue-320.webp"' in html
    assert "function posterForId" in html
    assert "data-yt-poster=" not in html
    assert "style=\"background-image:url" not in html
    assert "i.ytimg.com" not in html


def test_home_banners_expands_local_hero_srcset():
    src = HOME_BANNERS.read_text(encoding="utf-8")
    assert "LOCAL_HERO_MAX_W" in src
    assert "localHeroMobileSrcset" in src
    assert "replace(/-\\d+w$/i, '')" in src


def test_home_banners_use_saved_alignment_and_invalidate_ssr_match():
    src = HOME_BANNERS.read_text(encoding="utf-8")
    admin = (ROOT / "public" / "js" / "admin-content.js").read_text(encoding="utf-8")
    assert "b.align || (index === 3 ? 'right' : 'left')" in src
    assert "data-align=\"' + esc(align)" in src
    assert "name=\"align\"" in admin
    assert "align: String(fd.get('align') || 'left').trim()" in admin


def test_home_banners_per_role_text_colors():
    """眉題 / 標題 / 說明 each get their own color control + CSS vars."""
    src = HOME_BANNERS.read_text(encoding="utf-8")
    admin = (ROOT / "public" / "js" / "admin-content.js").read_text(encoding="utf-8")
    css = (ROOT / "public" / "css" / "home-ghibli.css").read_text(encoding="utf-8")
    assert "function slideRoleColors" in src
    assert "--hc-eyebrow:" in src
    assert "--hc-title:" in src
    assert "--hc-lead:" in src
    assert "hc-has-color--eyebrow" in src
    assert "hc-has-color--title" in src
    assert "hc-has-color--lead" in src
    assert "slideColorSig(b)" in src
    assert "'eyebrowColor'" in admin
    assert "'titleColor'" in admin
    assert "'leadColor'" in admin
    assert "眉題顏色" in admin
    assert "標題顏色" in admin
    assert "說明顏色" in admin
    assert "eyebrowColor: eyebrowColor" in admin
    assert "titleColor: titleColor" in admin
    assert "leadColor: leadColor" in admin
    assert "function bannerColorFieldHtml" in admin
    assert "function readBannerColorValue" in admin
    assert "--hc-eyebrow" in css
    assert "--hc-title" in css
    assert "--hc-lead" in css
    assert "hc-has-color--eyebrow" in css


def test_home_yt_gallery_autoplay_mute_has_gesture_unmute():
    """IO autoplay may mute for browser policy; user gesture must unmute."""
    html = INDEX.read_text(encoding="utf-8")
    css = (ROOT / "public" / "css" / "home-ghibli.css").read_text(encoding="utf-8")
    assert "embedFacade(facade, { muted: true })" in html
    assert "function unmuteActive" in html
    assert "mountUnmuteCatcher" in html
    assert 'data-yt-unmute' in html
    assert "activateThumb(thumb, { play: true, muted: false })" in html
    assert "embedFacade(btn, { muted: false })" in html
    assert ".gh-yt-unmute{" in css
    assert "home-ghibli.css?v=64" in html


def test_phone_card_images_fill_media_box():
    """Global max-width:100% on img must not collapse card photos into a strip."""
    base = (ROOT / "public" / "css" / "base.css").read_text(encoding="utf-8")
    home = (ROOT / "public" / "css" / "home.css").read_text(encoding="utf-8")
    shop = (ROOT / "public" / "css" / "shop.css").read_text(encoding="utf-8")
    assert "img{height:auto;}" in base.replace(" ", "")
    assert "max-width:none" in home.replace(" ", "")
    media = shop.split(".catalog-tile__media,", 1)[1].split("}", 1)[0]
    tile = shop.split(".catalog-tile__media img,", 1)[1].split("}", 1)[0]
    assert "width: 100%" in media
    assert "aspect-ratio: 1 / 1" in media
    assert "overflow: hidden" in media
    assert "width: 100%" in tile
    assert "height: 100%" in tile
    assert "object-fit: contain" in tile
    assert "max-width: none" in tile
    assert "padding: 0" in tile
    assert "repeat(2, minmax(0, 1fr))" in shop


def test_shop_catalog_tiles_square_cover_fill():
    """Step-1/2 snaps fill a fixed 1:1 box; extra_css + cache bump for phone defer."""
    shop = (ROOT / "public" / "css" / "shop.css").read_text(encoding="utf-8")
    calc = (
        ROOT / "content" / "site" / "templates" / "pages" / "shop" / "calculator.html"
    ).read_text(encoding="utf-8")
    js = (ROOT / "public" / "js" / "shop.js").read_text(encoding="utf-8")
    htmx = (
        ROOT / "content" / "site" / "templates" / "partials" / "htmx" / "shop_catalog.html"
    ).read_text(encoding="utf-8")
    extra = calc.split("{% block extra_css %}", 1)[1].split("{% endblock %}", 1)[0]
    media = shop.split(".catalog-tile__media,", 1)[1].split("}", 1)[0]
    img = shop.split(".catalog-tile__media img,", 1)[1].split("}", 1)[0]
    type_media = shop.split("#shop-styles .type-card__media {", 1)[1].split("}", 1)[0]
    type_img = shop.split("#shop-styles .type-card__media img,", 1)[1].split("}", 1)[0]
    assert "aspect-ratio: 1 / 1" in media
    assert "object-fit: contain" in img
    assert "height: 100%" in img
    assert "aspect-ratio: 1 / 1" in type_media
    assert "object-fit: contain" in type_img
    assert "catalog-tile__media" in extra
    assert "aspect-ratio: 1 / 1" in extra
    assert "object-fit: contain" in extra
    assert "width: 18px" in extra
    extra_preview = extra.split(".shop-fit .shop-girdle-engrave .cfg-engrave-preview {", 1)[1].split("}", 1)[0]
    extra_gem = extra.split(".shop-fit .shop-girdle-engrave .cfg-engrave-gem {", 1)[1].split("}", 1)[0]
    assert "position: relative" in extra_preview
    assert "width: 100%" in extra_preview
    assert "max-width: 100%" in extra_preview
    assert "overflow: hidden" in extra_preview
    assert "max-width: 16rem" not in extra_preview
    assert "width: 100%" in extra_gem
    assert "object-fit: contain" in extra_gem
    assert "object-fit: cover" not in extra_gem
    assert "shop.css?v=6.54" in extra
    assert "catalog-tile__media" in js
    assert "media.className = 'catalog-tile__media'" in js
    assert "catalog-tile__media" in htmx
    opt = js.split("function optimizedCategoryImageUrl(", 1)[1].split("function categoryImageUrl(", 1)[0]
    assert "searchParams.set('resize', 'contain')" in opt
    assert "searchParams.set('height', '320')" in opt
    assert "searchParams.set('width', '320')" in opt
    shop_preview = shop.split(".shop-fit .shop-girdle-engrave .cfg-engrave-preview {", 1)[1].split("}", 1)[0]
    shop_gem = shop.split(".shop-fit .shop-girdle-engrave .cfg-engrave-gem {", 1)[1].split("}", 1)[0]
    assert "width: 100%" in shop_preview
    assert "max-width: 100%" in shop_preview
    assert "overflow: hidden" in shop_preview
    assert "max-width: 16rem" not in shop_preview
    assert "width: 100%" in shop_gem
    assert "object-fit: contain" in shop_gem
    assert "max-width: 16rem" in shop
