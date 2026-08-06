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


def test_home_banners_cache_bust():
    html = INDEX.read_text(encoding="utf-8")
    assert "home-banners.js?v=7" in html
