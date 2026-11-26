"""Translation layer: translate rendered Chinese HTML from a Chinese-keyed catalog.

Chinese pages render as usual; each Chinese text node / visible attribute is then
looked up in content/i18n/<language>/*.json (plus saved database translations).
Anything missing stays Chinese. Templates are not duplicated per language.

Keys containing "{}" are patterns for text with live values ("共 {} 件").
Scripts, styles, SVG, textarea contents and translate="no" elements are untouched.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from html import escape, unescape
from urllib.parse import urlsplit

from app.i18n_highlight import restore_styled_blocks, swap_styled_blocks
from config.routes import ALL_PAGES, STANDALONE_PAGES
from config.settings import settings

# Each URL prefix is also the language code (/en, /ja, /ko).
LOCALES = ("en", "ja", "ko")
_OG_LOCALE = {"en": "en_US", "ja": "ja_JP", "ko": "ko_KR"}
_LABELS = {"en": "English", "ja": "日本語", "ko": "한국어"}

# Public site pages. Admin / CMS screens are never translated.
_PAGE_ROUTES = frozenset(
    meta.route for meta in [*ALL_PAGES, *STANDALONE_PAGES] if "admin" not in meta.route
)
_DYNAMIC_ROUTE_RE = re.compile(r"^/(?:journal|p)/[A-Za-z0-9_-]+$")

_LEGAL_ROUTES = frozenset({"/privacy", "/terms", "/return-policy"})
_LEGAL_NOTICE = {
    "en": "This is a translation. If it differs from the Chinese version, "
    "the Chinese version prevails.",
    "ja": "本ページは翻訳版です。中国語版と相違がある場合は、中国語版が優先されます。",
    "ko": "이 페이지는 번역본입니다. 중국어 버전과 내용이 다를 경우 중국어 버전이 우선합니다.",
}

_TOKEN_RE = re.compile(
    r"(<!--.*?-->"
    # Each ends only at its own tag: a script may contain "</svg>" in a string.
    r"|<script\b.*?</script\s*>|<style\b.*?</style\s*>|<svg\b.*?</svg\s*>"
    r"""|</?[A-Za-z!](?:[^<>"']|"[^"]*"|'[^']*')*>)""",
    re.DOTALL | re.IGNORECASE,
)
_TAG_NAME_RE = re.compile(r"</?([A-Za-z][A-Za-z0-9-]*)")
_NO_TRANSLATE_RE = re.compile(r"""\stranslate\s*=\s*["']no["']""", re.IGNORECASE)
_ATTR_RE = re.compile(
    r"""(\s(?:alt|title|placeholder|aria-label|content|data-label|data-marquee-phrase)\s*=\s*)"([^"]*)\""""
)
_LINK_RE = re.compile(r"""(\s(?:href|action)\s*=\s*)"(/[^"]*)\"""")
_HAS_VALUE_RE = re.compile(r"\svalue\s*=", re.IGNORECASE)
# CJK ideographs plus CJK / full-width punctuation left between inline elements.
_NEEDS_TRANSLATION_RE = re.compile(r"[　-〿一-鿿＀-￯・｜]")
_HAN_RE = re.compile(r"[一-鿿]")


def normalize_segment(text: str) -> str:
    return " ".join(unescape(text).split())


class Catalog:
    """Exact phrases first, then "{}" patterns, then truncated excerpts."""

    def __init__(self, entries: dict[str, str]):
        self.exact: dict[str, str] = {}
        patterns: list[tuple[int, re.Pattern[str], str]] = []
        for source, target in entries.items():
            key = normalize_segment(source)
            self.exact[key] = target
            literal = key.replace("{}", "")
            # A pattern needs real Chinese text, or it would swallow anything.
            if "{}" in key and len(_HAN_RE.findall(literal)) >= 2:
                regex = "(.+?)".join(re.escape(part) for part in key.split("{}"))
                short = len(_HAN_RE.findall(literal)) <= 3
                patterns.append((len(literal), re.compile(f"^{regex}$"), target, short))
        patterns.sort(key=lambda item: -item[0])
        self.patterns = [item[1:] for item in patterns]

    def get(self, key: str) -> str | None:
        if key in self.exact:
            return self.exact[key]
        # Customer stories are displayed inside quote marks.
        if len(key) > 2 and key[0] == "「" and key[-1] == "」" and "」" not in key[1:-1]:
            inner = self.get(key[1:-1])
            if inner is not None:
                return f"“{inner}”"
        for regex, target, short in self.patterns:
            match = regex.match(key)
            # A short pattern may not swallow Chinese that has no translation.
            if match and short:
                if any(_HAN_RE.search(v) and v not in self.exact for v in match.groups()):
                    continue
            if match:
                pieces = target.split("{}")
                values = [self.exact.get(v, v) for v in match.groups()]
                out = pieces[0]
                for index, piece in enumerate(pieces[1:]):
                    out += (values[index] if index < len(values) else "") + piece
                return out
        # Excerpts such as "長文前 280 字…": show the start of the full translation.
        if key.endswith("…") and len(key) > 80:
            head = key[:-1]
            for source, target in self.exact.items():
                if source.startswith(head):
                    return target[: max(160, len(target) * len(head) // len(source))] + "…"
        return None


@lru_cache(maxsize=None)
def load_entries(language: str) -> dict[str, str]:
    """The committed catalog files for one language."""
    folder = settings.site_content_dir.parent / "i18n" / language
    entries: dict[str, str] = {}
    for path in sorted(folder.glob("*.json")):
        entries.update(json.loads(path.read_text(encoding="utf-8")))
    return {normalize_segment(source): target for source, target in entries.items()}


@lru_cache(maxsize=16)
def _build_catalog(language: str, version: int) -> Catalog:
    from app.i18n_store import saved_entries

    # Reviewed catalog files win over machine translations saved in the database.
    return Catalog({**saved_entries(language), **load_entries(language)})


def load_catalog(language: str) -> Catalog:
    from app.i18n_store import saved_version

    return _build_catalog(language, saved_version(language))


def is_localizable(path: str) -> bool:
    return path in _PAGE_ROUTES or bool(_DYNAMIC_ROUTE_RE.match(path))


def page_routes() -> list[str]:
    return sorted(_PAGE_ROUTES)


def localized_url(url: str, locale: str) -> str:
    """Prefix a root-relative page URL; assets, APIs and unknown paths stay."""
    parts = urlsplit(url)
    if parts.scheme or parts.netloc or not is_localizable(parts.path):
        return url
    return f"/{locale}{url}"


def translate_html(
    html: str,
    catalog: Catalog | dict[str, str],
    *,
    spaced: bool = True,
    link_prefix: str | None = None,
) -> tuple[str, list[str]]:
    """Return (translated html, Chinese segments that had no catalog entry)."""
    if isinstance(catalog, dict):
        catalog = Catalog(catalog)
    missing: dict[str, None] = {}

    def lookup(raw: str) -> str | None:
        key = normalize_segment(raw)
        if not key or not _NEEDS_TRANSLATION_RE.search(key):
            return None
        target = catalog.get(key)
        if target is None:
            missing[key] = None
        return target

    def swap_attr(match: re.Match[str]) -> str:
        target = lookup(match[2])
        if target is None:
            return match[0]
        return f'{match[1]}"{escape(target, quote=True)}"'

    def swap_link(match: re.Match[str]) -> str:
        return f'{match[1]}"{localized_url(match[2], link_prefix)}"'

    html, styled = swap_styled_blocks(html, catalog.get)
    parts = _TOKEN_RE.split(html)
    skip_tag, skip_depth = "", 0
    option_tag: int | None = None
    in_textarea = False
    padded: int | None = None  # last text part where a trailing space was added
    for index, part in enumerate(parts):
        if index % 2:  # markup token
            name_match = _TAG_NAME_RE.match(part)
            name = name_match[1].lower() if name_match else ""
            if name in {"script", "style", "svg"} or part.startswith("<!"):
                continue
            if skip_depth:
                if name == skip_tag:
                    skip_depth += -1 if part.startswith("</") else 1
                continue
            if _NO_TRANSLATE_RE.search(part):
                skip_tag, skip_depth = name, 1
                continue
            if name == "textarea":  # translate its placeholder, never its content
                in_textarea = not part.startswith("</")
            tag = _ATTR_RE.sub(swap_attr, part)
            if link_prefix and name in {"a", "form", "area"}:
                tag = _LINK_RE.sub(swap_link, tag)
            parts[index] = tag
            option_tag = index if part.lower().startswith("<option") else None
        elif not skip_depth and not in_textarea:
            target = lookup(part)
            if target is None:
                continue
            # An <option> without value= submits its text: keep the Chinese value.
            if option_tag == index - 1 and not _HAS_VALUE_RE.search(parts[option_tag]):
                original = escape(normalize_segment(part), quote=True)
                parts[option_tag] = f'{parts[option_tag][:-1]} value="{original}">'
            if padded is not None and target.startswith((".", ",", ")", ":", ";")):
                # only tags may sit between the two fragments
                if not any(parts[i].strip() for i in range(padded + 2, index, 2)):
                    parts[padded] = parts[padded].rstrip()
            padded = None
            lead = part[: len(part) - len(part.lstrip())]
            tail = part[len(part.rstrip()) :]
            # English needs a space where Chinese had none next to a link,
            # but not before closing punctuation or after "(" and "/".
            # Japanese does not put spaces between words (spaced=False).
            if spaced and not lead and not target.startswith((".", ",", ")", "/", ":")):
                lead = " "
            if spaced and not tail and not target.endswith(("(", "/")):
                tail = " "
                padded = index
            parts[index] = f"{lead}{escape(target, quote=False)}{tail}"
    return restore_styled_blocks("".join(parts), styled), list(missing)


def language_links(route: str, current: str = "zh") -> list[dict]:
    """Switcher entries for a Chinese path; empty when it has no translation."""
    if not is_localizable(route):
        return []
    links = [{"code": "zh", "label": "中文", "href": route, "lang": "zh-Hant"}]
    links += [
        {"code": loc, "label": _LABELS[loc], "href": f"/{loc}{route}", "lang": loc}
        for loc in LOCALES
    ]
    for link in links:
        link["current"] = link["code"] == current
    return links


def language_links_for_request(request) -> list[dict]:
    """Jinja global: request.url.path is already the Chinese path here."""
    return language_links(request.scope["path"], getattr(request.state, "locale", "zh"))


def locale_for_url(url: str | None) -> str | None:
    """Locale of the localized page a fragment request came from, else None."""
    first, _sep, rest = urlsplit(url or "").path.lstrip("/").partition("/")
    return first if first in LOCALES and is_localizable(f"/{rest}") else None


def translate_for_locale(html: str, locale: str) -> str:
    translated, _missing = translate_html(
        html, load_catalog(locale), spaced=locale != "ja", link_prefix=locale
    )
    return translated


def localize_html(html: str, locale: str, route: str) -> str:
    """Translate a rendered Chinese page and point its metadata at /<locale>."""
    from app.i18n_client import head_scripts

    html = translate_for_locale(html, locale)
    html = html.replace('<html lang="zh-Hant-TW">', f'<html lang="{locale}">', 1)
    html = html.replace('content="zh_TW"', f'content="{_OG_LOCALE[locale]}"', 1)
    base = settings.public_base_url.rstrip("/")
    for prefix in ('<link rel="canonical" href="', '<meta property="og:url" content="'):
        html = html.replace(f'{prefix}{base}{route}"', f'{prefix}{base}/{locale}{route}"', 1)
    scripts = head_scripts(locale)
    html = re.sub(r"(<head[^>]*>)", lambda m: m[1] + scripts, html, count=1)
    if route in _LEGAL_ROUTES:
        notice = (
            '<p class="i18n-legal-notice" translate="no" style="margin:0;padding:96px 16px 0;'
            f'text-align:center;font-size:.85rem">{_LEGAL_NOTICE[locale]}</p>'
        )
        html = re.sub(r"(<main[^>]*>)", lambda m: m[1] + notice, html, count=1)
    # Preview stage: keep translated pages out of search results.
    return re.sub(
        r'<meta name="robots" content="[^"]*">',
        '<meta name="robots" content="noindex, nofollow">',
        html,
        count=1,
    )
