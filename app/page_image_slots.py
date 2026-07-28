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
}
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
    entries.append(("cta-scene", "頁尾行動情境", (19,), (2400, 1165)))
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
            default_url="/static/images/diamonds/colors/blue.png",
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
            "/about.html",
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
            "/series.html",
            "五大系列總覽",
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
        specs.append(
            _slot(route, label, "hero", "主視覺", "series", template, (0,), (2400, 1165))
        )
        specs.append(
            _slot(route, label, "intro", "介紹圖", "series", template, (1,), (2400, 1165))
        )
    return specs


def _dna_specs() -> list[SlotSpec]:
    base = "/static/images/"
    page = "/what-is-dna-diamond.html"
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
    )
    return tuple(specs)


def _read_template(spec: SlotSpec) -> str:
    return (settings.templates_dir / spec.template).read_text(encoding="utf-8")


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
    selected = [images[index] for index in spec.image_indexes]
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


def _replace_values(html: str, old: str, new: str) -> str:
    if not old or not new or old == new:
        return html
    pattern = re.compile(rf"(\b{_URL_ATTRS}\s*=\s*[\"']){re.escape(old)}([\"'])", re.IGNORECASE)
    return pattern.sub(lambda match: f"{match.group(1)}{new}{match.group(2)}", html)


def _replace_tag_url(tag: str, url: str, webp: str = "") -> str:
    name = "srcset" if tag.lower().startswith("<source") else "src"
    if not _attribute(tag, name):
        name = f"data-{name}"
    value = webp if tag.lower().startswith("<source") and webp else url
    return re.sub(
        _ATTR_RE.format(name=re.escape(name)),
        lambda match: f'{name}={match.group(1)}{value}{match.group(1)}',
        tag,
        count=1,
        flags=re.IGNORECASE,
    )


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
                lambda match: (
                    ""
                    if match.group().lower().startswith("<source") and not webp
                    else _replace_tag_url(match.group(), url, webp)
                ),
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
    return html
