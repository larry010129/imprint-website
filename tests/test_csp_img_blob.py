"""CSP must allow blob: images for admin/CMS crop previews."""

from app import HTML_CONTENT_SECURITY_POLICY, HTML_PERMISSIONS_POLICY


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
    # Phase-1 tighten: no open https: wildcard on img-src.
    assert " https:;" not in HTML_CONTENT_SECURITY_POLICY
    assert "https://*.supabase.co" in img_src


def test_html_csp_form_action_self():
    form_action = _directive("form-action")
    assert form_action
    assert "'self'" in form_action


def test_html_permissions_policy_lockdown():
    assert "camera=()" in HTML_PERMISSIONS_POLICY
    assert "geolocation=()" in HTML_PERMISSIONS_POLICY


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


def test_html_csp_allows_google_ads_conversion_hosts():
    script_src = _directive("script-src")
    img_src = _directive("img-src")
    connect_src = _directive("connect-src")
    frame_src = _directive("frame-src")
    for host in ("https://www.googleadservices.com", "https://googleads.g.doubleclick.net"):
        assert host in script_src
        assert host in img_src
        assert host in connect_src
    assert "https://*.g.doubleclick.net" in img_src
    assert "https://pagead2.googlesyndication.com" in connect_src
    assert "https://td.doubleclick.net" in frame_src
    # Google tag's ccm/s/collect beacon (not covered by *.g.doubleclick.net).
    assert "https://ad.doubleclick.net" in img_src
    assert "https://ad.doubleclick.net" in connect_src
    # Existing sources are kept.
    assert "https://www.googletagmanager.com" in script_src
    assert "https://www.youtube.com" in frame_src
