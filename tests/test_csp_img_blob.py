"""CSP must allow blob: images for admin/CMS crop previews."""

from app import HTML_CONTENT_SECURITY_POLICY


def test_html_csp_allows_blob_images_for_crop_preview():
    assert "img-src" in HTML_CONTENT_SECURITY_POLICY
    assert "blob:" in HTML_CONTENT_SECURITY_POLICY
    # img-src directive itself must list blob: (not only elsewhere).
    img_src = ""
    for part in HTML_CONTENT_SECURITY_POLICY.split(";"):
        token = part.strip()
        if token.startswith("img-src"):
            img_src = token
            break
    assert img_src, "missing img-src directive"
    assert "blob:" in img_src
