"""CSP must allow blob: images for admin/CMS crop previews."""

from app import HTML_CONTENT_SECURITY_POLICY


def _directive(name: str) -> str:
    for part in HTML_CONTENT_SECURITY_POLICY.split(";"):
        token = part.strip()
        if token.startswith(name):
            return token
    return ""


def test_html_csp_allows_blob_images_for_crop_preview():
    assert "img-src" in HTML_CONTENT_SECURITY_POLICY
    assert "blob:" in HTML_CONTENT_SECURITY_POLICY
    # img-src directive itself must list blob: (not only elsewhere).
    img_src = _directive("img-src")
    assert img_src, "missing img-src directive"
    assert "blob:" in img_src


def test_html_csp_allows_recaptcha_v2_hosts():
    script_src = _directive("script-src")
    connect_src = _directive("connect-src")
    frame_src = _directive("frame-src")
    assert "https://www.google.com" in script_src
    assert "https://www.gstatic.com" in script_src
    assert "https://www.google.com" in connect_src
    assert "https://www.gstatic.com" in connect_src
    assert "https://www.google.com" in frame_src
    assert "https://recaptcha.google.com" in frame_src
