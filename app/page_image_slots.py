"""Deterministic inventory and targeted rendering for page-image CMS slots."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.settings import settings

_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_ATTR_RE = r"\b{name}\s*=\s*([\"'])(.*?)\1"
_URL_ATTRS = r"(?:src|srcset|data-src|data-srcset|data-jpg)"

# Admin「頁面圖片」sub-tab label (page_label) → Storage folder under page-images/.
# Keys are page_key values from SlotSpec; folder slugs are short English kebab-case.
PAGE_IMAGE_STORAGE_FOLDERS: dict[str, str] = {
    "/journal": "journal",
    "/": "home",  # 首頁
    "/about": "brand-story",  # 品牌故事
    "/series": "series-overview",  # 六大系列總覽
    "/series/first-love/": "moon-diamond",  # 滿月鑽石
    "/series/pet/": "pet-diamond",  # 寵物鑽石
    "/series/love/": "wedding-diamond",  # 結髮鑽石
    "/series/family/": "family-diamond",  # 全家福鑽石
    "/series/heirloom/": "life-diamond",  # 生命鑽石
    "/series/signature/": "signature-diamond",  # 真我鑽石 Signature
    "/what-is-dna-diamond": "dna-diamond",  # DNA 鑽石的誕生
    "/privacy": "privacy",  # 隱私權政策
    "/return-policy": "return-policy",  # 退換貨政策
}
PAGE_IMAGE_PENDING_FOLDER = "_pending"
_FOLDER_ASCII = re.compile(r"^[a-z0-9][a-z0-9._-]{0,78}$")


@dataclass(frozen=True)
class SlotSpec:
    page_key: str
    page_label: str
    slot_key: str
    slot_label: str
    group_key: str
    template: str
    image_indexes: tuple[int, ...]
    target_w: int
    target_h: int
    default_url: str = ""
    default_webp: str = ""
    image_alt: str = ""
    indexed: bool = False
    # Editable CMS row even when no asset exists yet (shows as 未設定).
    allow_empty: bool = False


_SERIES = {
    "first-love": ("滿月鑽石", "imprint-diamond-newborn-baby-necklace"),
    "pet": ("寵物鑽石", "imprint-diamond-pet-memorial-cat"),
    "love": ("結髮鑽石", "imprint-diamond-wedding-couple-ring"),
    "family": ("全家福鑽石", "imprint-diamond-family-portrait-jewelry"),
    "heirloom": ("生命鑽石", "imprint-diamond-heirloom-memorial"),
    "signature": ("真我鑽石", "imprint-diamond-wedding-couple-ring"),
}
_HERO_STEM_MAX_W = {
    "imprint-diamond-newborn-baby-necklace": 2400,
    "imprint-diamond-pet-memorial-cat": 2400,
    "imprint-diamond-wedding-couple-ring": 2400,
    "imprint-diamond-family-portrait-jewelry": 2400,
    "imprint-diamond-heirloom-memorial": 1500,
    "imprint-diamond-family-memorial": 2400,
}
_LOCAL_HERO_SKY = (
    "/static/images/ghibli/hero-sky.jpg",
    "/static/images/ghibli/hero-sky.webp",
)
_LOCAL_DNA_BLUE = "/static/images/diamonds/colors/blue-320.webp"
_HOME_RESPONSIVE_SLOTS = frozenset(
    {
        "poem-visual",
        "scene-wedding",
        *(f"series-{key}" for key in _SERIES),
    }
)
def _slot(
    route: str,
    page: str,
    key: str,
    label: str,
    group: str,
    template: str,
    indexes: tuple[int, ...],
    size: tuple[int, int],
    **kwargs: Any,
) -> SlotSpec:
    return SlotSpec(route, page, key, label, group, template, indexes, *size, **kwargs)


def _home_specs() -> list[SlotSpec]:
    template = "pages/index.html"
    entries = [
        ("hero-sky", "主視覺天空", (0,), (1024, 1024)),
        ("poem-visual", "詩文區塊", (7,), (2400, 1165)),
        ("scene-wedding", "婚戒情境", (8,), (2400, 1165)),
    ]
    entries += [
        (f"series-{key}", f"系列卡・{label}", (10 + i,), (2400, 1165))
        for i, (key, (label, _asset)) in enumerate(_SERIES.items())
    ]
    entries += [
        (f"learn-{key}", f"延伸閱讀・{label}", (15 + i,), (1200, 800))
        for i, (key, label) in enumerate(
            (("dna", "DNA 鑽石"), ("price", "價格"), ("stories", "見證"), ("faq", "FAQ"))
        )
    ]
    specs = [
        _slot("/", "首頁", key, label, "brand", template, indexes, size, indexed=True)
        for key, label, indexes, size in entries
    ]
    specs.append(
        _slot(
            "/",
            "首頁",
            "dna-cta-diamond",
            "DNA 介紹・鑽石意象",
            "brand",
            template,
            (),
            (800, 800),
            default_url=_LOCAL_DNA_BLUE,
            default_webp=_LOCAL_DNA_BLUE,
            image_alt="DNA 鑽石意象",
        )
    )
    return specs


def _about_specs() -> list[SlotSpec]:
    template = "pages/about.html"
    values = [
        (
            "cinema",
            "品牌實驗室主景",
            (0,),
            "/static/images/legacy-live/styles/taiwan-local-lab.jpg",
            "銘印鑽石台灣在地培育實驗室",
            (1920, 535),
        ),
        (
            "chapters-heirloom",
            "品牌承諾・家族陪伴",
            (1,),
            "/static/images/legacy-live/features/heirloom-life.jpg",
            "三代家人在溫暖日光中相伴散步",
            (1600, 1067),
        ),
        (
            "pullquote-memorial",
            "品牌託付・紀念鑽石",
            (2,),
            "/static/images/legacy-live/styles/eternal-memorial.jpg",
            "思念化為永恆的紀念鑽石意象",
            (1600, 1067),
        ),
    ]
    return [
        _slot(
            "/about",
            "品牌故事",
            key,
            label,
            "brand",
            template,
            indexes,
            size,
            default_url=url,
            image_alt=alt,
        )
        for key, label, indexes, url, alt, size in values
    ]


def _series_overview_specs() -> list[SlotSpec]:
    return [
        _slot(
            "/series",
            "六大系列總覽",
            key,
            f"系列・{label}",
            "series",
            "pages/series.html",
            (i, i + 5),
            (2400, 1165),
        )
        for i, (key, (label, _asset)) in enumerate(_SERIES.items())
    ]


def _series_detail_specs() -> list[SlotSpec]:
    specs: list[SlotSpec] = []
    for key, (label, _asset) in _SERIES.items():
        template = f"fragments/series/{key}.html"
        route = f"/series/{key}/"
        # Signature hero/intro must seed even when the archived fragment is
        # missing (body fallback can also miss). Live save cannot 404 a valid 主視覺.
        allow_empty = key == "signature"
        specs.append(
            _slot(
                route,
                label,
                "hero",
                "主視覺",
                "series",
                template,
                (0,),
                (2400, 1165),
                allow_empty=allow_empty,
            )
        )
        specs.append(
            _slot(
                route,
                label,
                "intro",
                "介紹圖",
                "series",
                template,
                (1,),
                (2400, 1165),
                allow_empty=allow_empty,
            )
        )
    return specs


def _dna_specs() -> list[SlotSpec]:
    base = "/static/images/"
    page = "/what-is-dna-diamond"
    label_page = "DNA 鑽石的誕生"
    template = "pages/what-is-dna-diamond.html"
    values = (
        ("intro", "DNA 鑽石意象", "dna-process/what-is-dna-diamond-hero.png"),
        ("process-sample", "流程 1・樣本萃取", "dna-process/collect-bottle.png"),
        ("process-growth", "流程 2・晶化培育", "dna-process/crystal-growth.png"),
        ("process-cutting", "流程 3・切割拋光", "dna-process/diamond-cutting.png"),
        ("process-certificate", "流程 4・鑑定保障", "dna-process/certificate-guarantee.png"),
        ("process-jewelry", "流程 5・鑲嵌成飾", "products/ring-classic-solitaire-1.jpg"),
        ("process-memorial-box", "流程 6・影音紀念盒", "dna-process/memorial-media-box.png"),
        ("sample-quantity", "樣本份量示意", "dna-process/sample-quantity-guide.png"),
        ("lab-photo", "在地實驗室（主文區）", ""),
        ("assurance-certificate", "鑑定與保障", "dna-process/certificate-guarantee.png"),
        ("usp-lab-photo", "四大保障・在地實驗室", ""),
        ("usp-certificate", "四大保障・鑑定", "dna-process/certificate-guarantee.png"),
        ("usp-memorial-box", "四大保障・影音盒", "dna-process/memorial-media-box.png"),
        ("usp-jewelry-making", "四大保障・飾品", "legacy-live/styles/jewelry-making.jpg"),
    )
    specs: list[SlotSpec] = []
    for key, label, path in values:
        empty = not path
        specs.append(
            _slot(
                page,
                label_page,
                key,
                label,
                "brand",
                template,
                (),
                (1200, 800),
                default_url=f"{base}{path}" if path else "",
                image_alt=(
                    "銘印鑽石在地 DNA 鑽石培育實驗室"
                    if key in ("lab-photo", "usp-lab-photo")
                    else label
                ),
                allow_empty=empty,
            )
        )
    return specs


def _journal_specs() -> list[SlotSpec]:
    """Expose the page-level journal image slot in the admin uploader."""
    return [
        _slot(
            "/journal",
            "品牌日誌",
            "hero",
            "頁首圖片",
            "brand",
            "pages/journal.html",
            (),
            (2400, 900),
            allow_empty=True,
        )
    ]


def _empty_hero_specs(
    route: str,
    page: str,
    template: str,
    alt: str,
) -> list[SlotSpec]:
    """Optional page-hero photo already bound via Jinja ``page_image``."""
    return [
        _slot(
            route,
            page,
            "hero",
            "頁首圖片",
            "brand",
            template,
            (),
            (2400, 900),
            image_alt=alt,
            allow_empty=True,
        )
    ]


def page_image_slot_specs() -> tuple[SlotSpec, ...]:
    """Return content-page image slots only.

    Excludes /shop/calculator/ and /jewelry/* product imagery — those belong
    in 商品上架, not 內容與頁面圖片.
    """
    specs = (
        _home_specs()
        + _about_specs()
        + _series_overview_specs()
        + _series_detail_specs()
        + _dna_specs()
        + _journal_specs()
        + _empty_hero_specs(
            "/privacy",
            "隱私權政策",
            "pages/privacy.html",
            "隱私權政策頁主圖",
        )
        + _empty_hero_specs(
            "/return-policy",
            "退換貨政策",
            "pages/return-policy.html",
            "退換貨政策頁主圖",
        )
    )
    return tuple(specs)


def _page_key_folder_candidates(page_key: str) -> list[str]:
    key = str(page_key or "").strip()
    if not key:
        return []
    out = [key]
    if key != "/" and key.endswith("/"):
        out.append(key.rstrip("/") or "/")
    elif key != "/":
        out.append(f"{key}/")
    return out


def _fallback_folder_from_page_key(page_key: str) -> str:
    """ASCII kebab slug from route path when page_key is not in the registry."""
    raw = str(page_key or "").strip().strip("/").lower().replace("/", "-")
    if not raw:
        return PAGE_IMAGE_PENDING_FOLDER
    slug = re.sub(r"[^a-z0-9._-]+", "-", raw)
    slug = re.sub(r"[-_]{2,}", "-", slug).strip("-_")
    if len(slug) > 80:
        slug = slug[:80].rstrip("-_")
    if slug and _FOLDER_ASCII.fullmatch(slug) and slug != "pending":
        return slug
    return PAGE_IMAGE_PENDING_FOLDER


def page_image_storage_folder(page_key: str | None) -> str:
    """English Storage folder for a page_key (admin 頁面圖片 tab).

    Known content tabs use PAGE_IMAGE_STORAGE_FOLDERS. Missing page_key →
    ``_pending``. Unknown CMS routes fall back to a sanitized path slug.
    """
    if page_key is None or not str(page_key).strip():
        return PAGE_IMAGE_PENDING_FOLDER
    for candidate in _page_key_folder_candidates(str(page_key)):
        folder = PAGE_IMAGE_STORAGE_FOLDERS.get(candidate)
        if folder:
            return folder
    return _fallback_folder_from_page_key(str(page_key))


def _route_body_key(page_key: str) -> str:
    if page_key == "/":
        return "home"
    return page_key.strip("/").replace("/", "__").replace(".html", "_html") or "home"


def _read_template(spec: SlotSpec) -> str:
    """Read archived page templates for seed defaults (indexes match Jinja sources)."""
    archived = settings.templates_dir / spec.template
    if archived.is_file():
        return archived.read_text(encoding="utf-8")
    # Fallback: rendered body (indexes may not match — skip missing in _slot_defaults)
    bodies = settings.site_content_dir / "bodies" / f"{_route_body_key(spec.page_key)}.html"
    if bodies.is_file():
        return bodies.read_text(encoding="utf-8")
    return ""


def _attribute(tag: str, name: str) -> str:
    match = re.search(_ATTR_RE.format(name=re.escape(name)), tag, re.IGNORECASE)
    return match.group(2).strip() if match else ""


def _picture_webp(html: str, image_match: re.Match[str]) -> str:
    start = html.rfind("<picture", 0, image_match.start())
    if start < 0 or html.rfind("</picture>", 0, image_match.start()) > start:
        return ""
    sources = re.findall(r"<source\b[^>]*>", html[start : image_match.start()], re.IGNORECASE)
    if not sources:
        return ""
    return _attribute(sources[-1], "srcset") or _attribute(sources[-1], "data-srcset")


def _slot_defaults(spec: SlotSpec) -> tuple[str, str, str]:
    if spec.default_url:
        return spec.default_url, spec.default_webp, spec.image_alt
    html = _read_template(spec)
    images = list(_IMG_RE.finditer(html))
    selected = []
    for index in spec.image_indexes:
        if 0 <= index < len(images):
            selected.append(images[index])
    if not selected and not spec.allow_empty:
        return "", "", spec.image_alt
    url = next((_attribute(item.group(), "src") or _attribute(item.group(), "data-src") for item in selected), "")
    alt = next((_attribute(item.group(), "alt") for item in selected if _attribute(item.group(), "alt")), "")
    webp = next((_picture_webp(html, item) for item in selected if _picture_webp(html, item)), "")
    return url, webp, alt


def build_page_image_seed() -> list[dict[str, Any]]:
    """Build compact registry into deterministic DB seed rows."""
    rows = []
    for order, spec in enumerate(page_image_slot_specs(), 1):
        url, webp, alt = _slot_defaults(spec)
        if not url and not spec.allow_empty:
            continue
        rows.append(
            {
                "page_key": spec.page_key,
                "slot_key": spec.slot_key,
                "label": spec.page_label,
                "slot_label": spec.slot_label,
                "group_key": spec.group_key,
                "image_url": url or "",
                "image_webp": webp or None,
                "image_alt": alt or spec.image_alt or "",
                "default_image_url": url or "",
                "default_image_webp": webp or None,
                "target_w": spec.target_w,
                "target_h": spec.target_h,
                "sort_order": order,
            }
        )
    return rows


def _effective_url(row: dict, key: str, default_key: str) -> str:
    if row.get("is_published") is False:
        return str(row.get(default_key) or "").strip()
    return str(row.get(key) or row.get(default_key) or "").strip()


def _is_remote_asset(url: str) -> bool:
    value = str(url or "").strip().lower()
    if not value:
        return False
    return value.startswith(("http://", "https://", "//")) or "supabase" in value


def _hero_stem(url: str) -> str:
    match = re.search(r"/([^/?#]+?)(?:\.(?:jpe?g|png|webp))?(?:[?#]|$)", str(url or ""), re.I)
    if not match:
        return ""
    return re.sub(r"-\d+w$", "", match.group(1), flags=re.I).lower()


def _hero_responsive_srcset(stem: str) -> str:
    max_w = _HERO_STEM_MAX_W.get(stem, 2400)
    return (
        f"/static/images/hero/{stem}-400w.webp 400w, "
        f"/static/images/hero/{stem}-800w.webp 800w, "
        f"/static/images/hero/{stem}-960w.webp 960w, "
        f"/static/images/hero/{stem}-1200w.webp 1200w, "
        f"/static/images/hero/{stem}.webp {max_w}w"
    )


def _prefer_local_home_asset(slot_key: str, url: str, webp: str) -> tuple[str, str]:
    """Keep homepage LCP/delivery on local static when CMS points at fat remotes."""
    key = str(slot_key or "")
    combined = f"{url} {webp}"
    if key == "hero-sky":
        # Decorative sky: never ship heavy remote as first-viewport paint.
        if (
            not url
            or _is_remote_asset(url)
            or _is_remote_asset(webp)
            or "hero-sky" in combined
            or "ghibli" in combined
        ):
            return _LOCAL_HERO_SKY
        return url, webp or url
    if key == "dna-cta-diamond":
        if (
            not url
            or _is_remote_asset(url)
            or _is_remote_asset(webp)
            or "colors/blue" in combined.replace("\\", "/")
        ):
            return _LOCAL_DNA_BLUE, _LOCAL_DNA_BLUE
        return url, webp or url
    if key in _HOME_RESPONSIVE_SLOTS:
        # Admin upload (Supabase / any remote) always wins. Do not remap it
        # back to the local wedding-couple srcset just because the stem matches.
        if _is_remote_asset(url) or _is_remote_asset(webp):
            return url, webp or url
        stem = _hero_stem(webp or url)
        if stem in _HERO_STEM_MAX_W:
            return f"/static/images/hero/{stem}-800w.webp", _hero_responsive_srcset(stem)
    return url, webp


def _series_key_from_home_slot(slot_key: str) -> str | None:
    raw = str(slot_key or "")
    if not raw.startswith("series-"):
        return None
    key = raw[len("series-") :]
    return key if key in _SERIES else None


def paired_series_slot(page_key: str, slot_key: str) -> tuple[str, str] | None:
    """Home series-* card <-> series page 主視覺."""
    home_key = _series_key_from_home_slot(slot_key)
    if page_key == "/" and home_key:
        return f"/series/{home_key}/", "hero"
    if str(slot_key or "") == "hero":
        for key in _SERIES:
            if page_key == f"/series/{key}/":
                return "/", f"series-{key}"
    return None


def sync_paired_series_image(cur, page_key: str, slot_key: str, image_url: str, image_webp: str | None) -> None:
    """Copy a 主視覺/home-card upload onto its twin so the two cannot drift."""
    pair = paired_series_slot(page_key, slot_key)
    if not pair:
        return
    twin_page, twin_slot = pair
    cur.execute(
        """
        update page_images
        set image_url = %s, image_webp = %s, updated_at = now()
        where page_key = %s and slot_key = %s
        """,
        (image_url, image_webp, twin_page, twin_slot),
    )


def _is_series_default_asset(series_key: str, url: str, webp: str) -> bool:
    """True for empty or the series' stock hero stem (local or site-images copy)."""
    if not (url or webp):
        return True
    default_stem = _SERIES[series_key][1]
    return _hero_stem(webp or url) == default_stem


def _home_series_admin_urls(slot_key: str, url: str, webp: str) -> tuple[str, str]:
    """Homepage series card: series 主視覺 wins over a leftover home-slot file."""
    series_key = _series_key_from_home_slot(slot_key)
    if not series_key:
        return url, webp
    try:
        from app.content import (
            effective_page_image_url,
            effective_page_image_webp,
            fetch_page_image,
        )
        from app.database import get_connection
        from app.image_urls import with_cache_buster

        with get_connection() as conn, conn.cursor() as cur:
            row = fetch_page_image(cur, f"/series/{series_key}/", "hero")
        if not row:
            return url, webp
        hero = effective_page_image_url(row)
        hero_webp = effective_page_image_webp(row)
        if hero and not _is_series_default_asset(series_key, hero, hero_webp):
            stamp = row.get("updated_at")
            return (
                with_cache_buster(hero, stamp),
                with_cache_buster(hero_webp or hero, stamp),
            )
    except Exception:
        pass
    return url, webp


def _is_stock_hero_asset(url: str) -> bool:
    return bool(url) and _hero_stem(url) in _HERO_STEM_MAX_W


def _drop_stale_stock_srcset(url: str, webp: str) -> tuple[str, str]:
    """Custom/admin URL must not keep leftover stock-hero webp or srcset."""
    if not url or _looks_like_srcset(url):
        return url, webp
    if webp and _looks_like_srcset(webp) and not _is_stock_hero_asset(url):
        return url, url
    if webp and _is_stock_hero_asset(webp) and not _is_stock_hero_asset(url):
        return url, url
    return url, webp


def _prefer_local_series_asset(url: str, webp: str) -> tuple[str, str]:
    """Series overview: local stock stems may keep responsive srcset.

    Remote/admin uploads pass through. Never re-attach /static/images/hero
    srcset onto a CMS swap — browser would keep painting the old files.
    """
    if _is_remote_asset(url) or _is_remote_asset(webp):
        return url, webp or url
    stem = _hero_stem(webp or url)
    if stem in _HERO_STEM_MAX_W:
        return url, _hero_responsive_srcset(stem)
    return url, webp


def _looks_like_srcset(value: str) -> bool:
    text = str(value or "").strip()
    return bool(re.search(r"\s+\d+w\b", text)) or "," in text


def _replace_values(html: str, old: str, new: str) -> str:
    if not old or not new or old == new:
        return html
    pattern = re.compile(rf"(\b{_URL_ATTRS}\s*=\s*[\"']){re.escape(old)}([\"'])", re.IGNORECASE)
    return pattern.sub(lambda match: f"{match.group(1)}{new}{match.group(2)}", html)


def _replace_attr(tag: str, name: str, value: str) -> str:
    if _attribute(tag, name):
        return re.sub(
            _ATTR_RE.format(name=re.escape(name)),
            lambda match: f"{name}={match.group(1)}{value}{match.group(1)}",
            tag,
            count=1,
            flags=re.IGNORECASE,
        )
    if tag.endswith("/>"):
        return f'{tag[:-2]} {name}="{value}"/>'
    if tag.endswith(">"):
        return f'{tag[:-1]} {name}="{value}">'
    return tag


def _replace_tag_url(tag: str, url: str, webp: str = "") -> str:
    if tag.lower().startswith("<source"):
        name = "srcset" if _attribute(tag, "srcset") else (
            "data-srcset" if _attribute(tag, "data-srcset") else "srcset"
        )
        return _replace_attr(tag, name, webp if webp else url)
    tag = _replace_attr(tag, "src" if _attribute(tag, "src") else (
        "data-src" if _attribute(tag, "data-src") else "src"
    ), url)
    # Mirror responsive webp onto img srcset so CMS cannot leave full-bleed remotes.
    if webp and _looks_like_srcset(webp):
        name = "srcset" if _attribute(tag, "srcset") else (
            "data-srcset" if _attribute(tag, "data-srcset") else "srcset"
        )
        tag = _replace_attr(tag, name, webp)
    else:
        # Custom single-URL upload: drop stale local responsive srcset or
        # browser keeps old PC hero bytes and ignores the new src.
        single = (webp or url).strip()
        if single:
            if _attribute(tag, "srcset"):
                tag = _replace_attr(tag, "srcset", single)
            if _attribute(tag, "data-srcset"):
                tag = _replace_attr(tag, "data-srcset", single)
    return tag


def _replace_picture_child(tag: str, url: str, webp: str) -> str:
    if tag.lower().startswith("<source"):
        existing = _attribute(tag, "srcset") or _attribute(tag, "data-srcset")
        # Drop leftover responsive hero srcset when the slot is now a single file.
        if existing and _looks_like_srcset(existing) and not _looks_like_srcset(webp):
            return ""
        if not webp and not url:
            return ""
    return _replace_tag_url(tag, url, webp)


def _replace_indexed(html: str, indexes: tuple[int, ...], url: str, webp: str) -> str:
    images = list(_IMG_RE.finditer(html))
    for index in sorted(indexes, reverse=True):
        image = images[index]
        start = html.rfind("<picture", 0, image.start())
        end = html.find("</picture>", image.end())
        if start >= 0 and end >= 0 and html.rfind("</picture>", 0, image.start()) < start:
            end += len("</picture>")
            block = re.sub(
                r"<(?:source|img)\b[^>]*>",
                lambda match: _replace_picture_child(match.group(), url, webp),
                html[start:end],
                flags=re.IGNORECASE,
            )
            html = html[:start] + block + html[end:]
        else:
            tag = _replace_tag_url(image.group(), url)
            html = html[: image.start()] + tag + html[image.end() :]
    return html


def _replace_marked(html: str, slot_key: str, url: str, webp: str) -> str | None:
    images = [
        index
        for index, match in enumerate(_IMG_RE.finditer(html))
        if _attribute(match.group(), "data-cms-slot") == slot_key
    ]
    if not images:
        return None
    return _replace_indexed(html, tuple(images), url, webp)


def apply_page_image_slots(html: str, route: str, rows: list[dict]) -> str:
    """Rewrite only image blocks declared for route and slot."""
    specs = {spec.slot_key: spec for spec in page_image_slot_specs() if spec.page_key == route}
    for row in rows:
        spec = specs.get(str(row.get("slot_key") or "hero"))
        if not spec:
            continue
        url = str(row.get("display_url") or "").strip() or _effective_url(
            row, "image_url", "default_image_url"
        )
        webp = (
            str(row.get("display_webp") or "").strip()
            if "display_webp" in row
            else _effective_url(row, "image_webp", "default_image_webp")
        )
        if route == "/":
            url, webp = _prefer_local_home_asset(spec.slot_key, url, webp)
            if _series_key_from_home_slot(spec.slot_key):
                url, webp = _home_series_admin_urls(spec.slot_key, url, webp)
        elif route == "/series":
            url, webp = _prefer_local_series_asset(url, webp)
        url, webp = _drop_stale_stock_srcset(url, webp)
        from app.image_urls import with_cache_buster

        stamp = row.get("updated_at")
        url = with_cache_buster(url, stamp)
        webp = with_cache_buster(webp, stamp)
        marked = _replace_marked(html, spec.slot_key, url, webp)
        if marked is not None:
            html = marked
            continue
        if spec.indexed:
            html = _replace_indexed(html, spec.image_indexes, url, webp)
            continue
        html = _replace_values(html, str(row.get("default_image_url") or ""), url)
        default_webp = str(row.get("default_image_webp") or "")
        html = _replace_values(html, default_webp, webp or url)
        # dna-cta default may still be legacy .png in older DB rows.
        if spec.slot_key == "dna-cta-diamond":
            html = _replace_values(html, "/static/images/diamonds/colors/blue.png", url)
    return html
