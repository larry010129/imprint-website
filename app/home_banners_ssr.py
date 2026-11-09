"""Server-side render of the home hero carousel (mirrors public/js/home-banners.js).

The homepage used to ship six hard-coded slides and swap them for the CMS banners
after load, which made new/reordered banners "jump". Rendering the published
banners into the HTML removes the swap. The markup below must stay in step with
``slideHtml`` in home-banners.js; a shared ``version`` hash (also returned by
/api/banners) lets the script skip the swap when the page is already current.
"""

from __future__ import annotations

import hashlib
import json
import re
from html import escape as _escape
from typing import Any

MEMORIAL_MOBILE = (
    "/static/images/hero/imprint-diamond-family-memorial-800w.webp 800w, "
    "/static/images/hero/imprint-diamond-family-memorial-960w.webp 960w, "
    "/static/images/hero/imprint-diamond-family-memorial-1200w.webp 1200w"
)
MEMORIAL_DESKTOP = "/static/images/hero/imprint-diamond-family-memorial.webp"
MEMORIAL_IMG = "/static/images/hero/imprint-diamond-family-memorial-800w.webp"

BANNER_TEXT_COLORS = {
    "cream": "#fbf6ed",
    "mint": "#8eedf0",
    "teal": "#52c4c8",
    "deep-teal": "#1f6f72",
    "ink": "#242220",
}

LOCAL_HERO_MAX_W = {
    "imprint-diamond-newborn-baby-necklace": 2400,
    "imprint-diamond-pet-memorial-cat": 2400,
    "imprint-diamond-wedding-couple-ring": 2400,
    "imprint-diamond-family-portrait-jewelry": 2400,
    "imprint-diamond-heirloom-memorial": 1500,
}

_WEBP_RE = re.compile(r"\.webp(\s|\?|$)", re.I)
_WIDTH_SRCSET_RE = re.compile(r",\s*|\s+\d+w\b|\s+[\d.]+x\b")
_HEX_RE = re.compile(r"^#[0-9a-f]{6}$")


def _esc(value: Any) -> str:
    return _escape("" if value is None else str(value), quote=True)


def banners_version(banners: list[dict]) -> str:
    raw = json.dumps(banners, sort_keys=True, default=str, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _text_color(tone: Any) -> str:
    t = str(tone or "").strip().lower()
    if t in BANNER_TEXT_COLORS:
        return BANNER_TEXT_COLORS[t]
    if _HEX_RE.match(t):
        return t
    return ""


def _role_tone(b: dict, role: str) -> Any:
    legacy = b.get("tone") or "warm"
    return b.get(f"{role}_color") or legacy


def _asset_key(url: Any) -> str:
    s = str(url or "").strip()
    if not s:
        return ""
    if re.search(r"imprint-diamond-family-memorial", s, re.I):
        return "memorial"
    m = re.search(r"/([^/?#]+)(?:[?#]|$)", s)
    if not m:
        return s.lower()
    name = re.sub(r"\.(jpe?g|png|webp)$", "", m.group(1), flags=re.I)
    return re.sub(r"-\d+w$", "", name, flags=re.I).lower()


def _local_hero_stem(url: Any) -> str:
    key = _asset_key(url)
    return key if key in LOCAL_HERO_MAX_W else ""


def _local_mobile_srcset(stem: str) -> str:
    base = f"/static/images/hero/{stem}"
    return ", ".join(f"{base}-{w}w.webp {w}w" for w in (640, 800, 960, 1200, 1280))


def _is_width_srcset(value: str) -> bool:
    return bool(_WIDTH_SRCSET_RE.search(value or ""))


def _desktop_source(attr: str, srcset: str, is_webp: bool) -> str:
    if not srcset:
        return ""
    typ = ' type="image/webp"' if is_webp else ""
    return f'<source media="(min-width:901px)" {attr}="{_esc(srcset)}"{typ} sizes="100vw">'


def _is_memorial(b: dict) -> bool:
    urls = " ".join(str(b.get(k) or "") for k in ("image_url", "image_webp"))
    return bool(re.search(r"imprint-diamond-family-memorial", urls, re.I))


def _memorial_picture(attr: str, mobile_override: str) -> dict:
    mobile_value = (mobile_override or "").strip()
    img_src = mobile_value or MEMORIAL_IMG
    webp = _desktop_source(attr, MEMORIAL_DESKTOP, True)
    if mobile_value and not _is_width_srcset(mobile_value):
        return {"mobile": "", "webp": webp, "img_src": img_src, "img_extra": ""}
    mobile_src = mobile_value or MEMORIAL_MOBILE
    typ = ' type="image/webp"' if (not mobile_value or _WEBP_RE.search(mobile_src)) else ""
    mobile = (
        f'<source media="(max-width:900px)" {attr}="{_esc(mobile_src)}"{typ} sizes="100vw">'
    )
    img_extra = (
        ""
        if mobile_value
        else f' width="800" height="388" sizes="100vw" srcset="{_esc(MEMORIAL_MOBILE)}"'
    )
    return {"mobile": mobile, "webp": webp, "img_src": img_src, "img_extra": img_extra}


def _remote_picture(b: dict, attr: str) -> dict:
    mobile_value = str(b.get("image_url_mobile") or "").strip()
    desktop_url = str(b.get("image_webp") or b.get("image_url") or "").strip()
    stem = _local_hero_stem(b.get("image_webp") or b.get("image_url"))
    if stem:
        desktop = f"/static/images/hero/{stem}.webp"
        desktop_srcset = (
            f"/static/images/hero/{stem}-1280w.webp 1280w, "
            f"/static/images/hero/{stem}-1200w.webp 1200w, "
            f"{desktop} {LOCAL_HERO_MAX_W[stem]}w"
        )
        webp = _desktop_source(attr, desktop_srcset, True)
        if mobile_value and not _is_width_srcset(mobile_value):
            return {"mobile": "", "webp": webp, "img_src": mobile_value, "img_extra": ""}
        mobile_srcset = mobile_value or _local_mobile_srcset(stem)
        typ = ' type="image/webp"' if _WEBP_RE.search(mobile_srcset) else ""
        mobile = (
            f'<source media="(max-width:900px)" {attr}="{_esc(mobile_srcset)}"{typ} sizes="100vw">'
        )
        img_src = mobile_value or f"/static/images/hero/{stem}-800w.webp"
        img_extra = ""
        if not mobile_value:
            img_extra = ' width="800" height="388" sizes="100vw"'
            if attr == "srcset":
                img_extra += f' srcset="{_esc(_local_mobile_srcset(stem))}"'
        return {"mobile": mobile, "webp": webp, "img_src": img_src, "img_extra": img_extra}

    mobile_src = mobile_value or desktop_url
    desktop_src = desktop_url
    img_src = mobile_value or desktop_src
    webp = ""
    if desktop_src and (desktop_src != mobile_src or not mobile_value):
        webp = _desktop_source(attr, desktop_src, bool(_WEBP_RE.search(desktop_src)))
    if mobile_src and not _is_width_srcset(mobile_src):
        return {"mobile": "", "webp": webp, "img_src": img_src, "img_extra": ""}
    typ = ' type="image/webp"' if _WEBP_RE.search(mobile_src) else ""
    mobile = f'<source media="(max-width:900px)" {attr}="{_esc(mobile_src)}"{typ} sizes="100vw">'
    return {"mobile": mobile, "webp": webp, "img_src": img_src, "img_extra": ""}


def _format_lead(lead: Any) -> str:
    return re.sub(r"\bDNA\b", '<span class="gh-dna">DNA</span>', _esc(lead))


def _format_title(title: Any, index: int) -> str:
    text = _esc(title)
    split_at = text.find("，")
    if index != 0 or split_at < 0:
        return text
    return f"{text[: split_at + 1]}<em>{text[split_at + 1:]}</em>"


def _cta_secondary(b: dict) -> str:
    label = str(b.get("cta_secondary_label") or "").strip()
    href = str(b.get("cta_secondary_href") or "").strip()
    if not label or not href:
        return ""
    if href.startswith("#"):
        return (
            f'<button type="button" class="gh-btn gh-btn--ghost" '
            f'data-scroll-to="{_esc(href[1:])}">{_esc(label)}</button>'
        )
    return f'<a class="gh-btn gh-btn--ghost" href="{_esc(href)}">{_esc(label)}</a>'


def render_slide(b: dict, index: int) -> str:
    tone = b.get("tone") or "warm"
    colors = {r: _text_color(_role_tone(b, r)) for r in ("eyebrow", "title", "lead")}
    align = b.get("align") or ("right" if index == 3 else "left")
    title_tag = "h1" if index == 0 else "p"
    loading = 'loading="eager" fetchpriority="high"' if index == 0 else 'loading="lazy"'
    attr = "srcset" if index == 0 else "data-srcset"
    mobile_value = str(b.get("image_url_mobile") or "").strip()
    pic = (
        _memorial_picture(attr, mobile_value)
        if index == 0 and _is_memorial(b)
        else _remote_picture(b, attr)
    )
    primary = ""
    if b.get("cta_primary_label") and b.get("cta_primary_href"):
        primary = (
            f'<a class="gh-btn gh-btn--primary" href="{_esc(b["cta_primary_href"])}">'
            f'{_esc(b["cta_primary_label"])}</a>'
        )
    secondary = _cta_secondary(b)
    first = index == 0
    r_eyebrow = "" if first else " reveal"
    r_title = "" if first else " reveal reveal-d1"
    r_lead = "" if first else " reveal reveal-d2"
    r_actions = "" if first else " reveal reveal-d3"
    style_parts = [
        f"--hc-{role}:{colors[role]}" for role in ("eyebrow", "title", "lead") if colors[role]
    ]
    style_attr = f' style="{_esc(";".join(style_parts))}"' if style_parts else ""
    custom = " hc-slide--custom-text" if any(colors.values()) else ""
    eyebrow_html = ""
    if b.get("eyebrow"):
        has = " hc-has-color hc-has-color--eyebrow" if colors["eyebrow"] else ""
        eyebrow_html = f'<p class="gh-script{r_eyebrow}{has}">{_esc(b["eyebrow"])}</p>'
    title_has = " hc-has-color hc-has-color--title" if colors["title"] else ""
    lead_html = ""
    if b.get("lead"):
        has = " hc-has-color hc-has-color--lead" if colors["lead"] else ""
        lead_html = f'<p class="gh-hero__lead{r_lead}{has}">{_format_lead(b["lead"])}</p>'
    actions_html = (
        f'<div class="gh-hero__actions{r_actions}">{primary}{secondary}</div>'
        if (primary or secondary)
        else ""
    )
    alt = b.get("image_alt") or b.get("title")
    return (
        f'<li class="hc-slide{" is-active" if first else ""}{custom}" '
        f'data-align="{_esc(align)}" data-tone="{_esc(tone)}"{style_attr}>'
        f'<div class="hc-media"><picture>{pic["mobile"]}{pic["webp"]}'
        f'<img src="{_esc(pic["img_src"])}" alt="{_esc(alt)}"{pic["img_extra"]} '
        f'{loading} decoding="async"></picture></div>'
        f'<div class="hc-scrim gh-hc-scrim"></div>'
        f'<div class="container hc-copy gh-hc-copy">{eyebrow_html}'
        f'<{title_tag} class="gh-hero__title{r_title}{title_has}">'
        f'{_format_title(b.get("title"), index)}</{title_tag}>'
        f"{lead_html}{actions_html}</div></li>"
    )


def render_slides(banners: list[dict]) -> str:
    return "".join(render_slide(b, i) for i, b in enumerate(banners))


def render_dots(banners: list[dict]) -> str:
    out = []
    for i, b in enumerate(banners):
        label = re.sub(r"\s+", " ", str(b.get("title") or "")).strip() or f"投影片 {i + 1}"
        label = label.replace('"', "")
        out.append(
            f'<button type="button" class="hc-dot{" is-active" if i == 0 else ""}" '
            f'data-index="{i}" role="tab" aria-label="{_esc(label)}" '
            f'aria-selected="{"true" if i == 0 else "false"}"></button>'
        )
    return "".join(out)


def load_public_banners_payload() -> dict:
    """Published banners + version hash, sharing the /api/banners cache."""
    from app.content import fetch_published_banners
    from app.content_cache import get_public_content_api_cache, set_public_content_api_cache
    from app.database import get_connection

    cached = get_public_content_api_cache("banners")
    if cached is not None:
        return cached
    with get_connection() as conn, conn.cursor() as cur:
        banners = fetch_published_banners(cur)
    payload = {"banners": banners, "version": banners_version(banners)}
    set_public_content_api_cache("banners", payload)
    return payload


def home_hero_context() -> dict:
    """Template variables for the home hero; empty dict → template keeps its fallback slides."""
    try:
        payload = load_public_banners_payload()
    except Exception:  # noqa: BLE001 — never break the homepage over the carousel
        return {}
    banners = payload.get("banners") or []
    if not banners:
        return {}
    return {
        "hero_slides_html": render_slides(banners),
        "hero_dots_html": render_dots(banners),
        "hero_banner_count": len(banners),
        "hero_banners_version": payload.get("version") or banners_version(banners),
    }


_SLIDES_RE = re.compile(r"<!--hc-slides:start-->.*?<!--hc-slides:end-->", re.S)
_DOTS_RE = re.compile(r"<!--hc-dots:start-->.*?<!--hc-dots:end-->", re.S)


def apply_home_hero(html: str, hero: dict) -> str:
    """Swap the template's fallback slides/dots for the published banners.

    Runs AFTER the page-image/copy slot passes: those address <img> tags by their
    position in the page, so the hero must keep its fixed six fallback images until
    they are done (a different banner count would shift every later index).
    """
    if not hero.get("hero_slides_html"):
        return html
    html = _SLIDES_RE.sub(lambda _m: hero["hero_slides_html"], html, count=1)
    html = _DOTS_RE.sub(lambda _m: hero["hero_dots_html"], html, count=1)
    count = int(hero.get("hero_banner_count") or 0)
    html = html.replace(
        '<ul id="hcTrack" class="hc-track">',
        f'<ul id="hcTrack" class="hc-track" data-banners-version="{_esc(hero.get("hero_banners_version"))}">',
        1,
    )
    dots_attrs = f' style="--hc-n:{count}"' + (" hidden" if count <= 1 else "")
    html = html.replace(
        'class="hc-dots gh-hc-dots" role="tablist" aria-label="輪播指示">',
        f'class="hc-dots gh-hc-dots" role="tablist" aria-label="輪播指示"{dots_attrs}>',
        1,
    )
    return html
