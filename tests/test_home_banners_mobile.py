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
    assert "home-ghibli.css?v=63" in html
