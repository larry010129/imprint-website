#!/usr/bin/env python3
"""One-time migration: convert the baked static HTML pages into Jinja2 templates.

The site's old build step (scripts/build-site-layout.mjs) baked
partials/layout/{topbar,nav,footer,head-common}.html into every page. This
script reads those already-baked pages and mechanically extracts, per page:
  - <head> metadata (title, description, canonical, OG tags, breadcrumb
    JSON-LD, any extra <link>/<script type=ld+json> tags)
  - <body> metadata (data-site-active, data-mvc, extra body classes)
  - the <main>...</main> content
  - any extra <script src> tags beyond site-layout.js/main.js

...and emits:
  - app/templates/pages/**/*.html      one template per unique page
  - app/templates/fragments/**/*.html  per-item content for the three
    families of near-identical pages (jewelry category, jewelry style,
    series detail) — plain HTML data files, NOT Jinja templates (read as
    raw text by web_router.py so their content can never be mis-parsed as
    Jinja syntax)
  - app/routers/pages_registry.py      route -> template + metadata, used
    by app/routers/web_router.py to register FastAPI routes

Run once from the repo root:  python scripts/migrate_to_jinja.py
Safe to re-run — it always regenerates its outputs from the source HTML.
"""

from __future__ import annotations

import json
import posixpath
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "app" / "templates"
PAGES_DIR = TEMPLATES / "pages"
FRAGMENTS_DIR = TEMPLATES / "fragments"
REGISTRY_FILE = ROOT / "app" / "routers" / "pages_registry.py"

STANDARD_CSS = {"base.css", "nav.css", "home.css", "pages.css", "responsive.css"}
STANDARD_JS = {"site-layout.js", "main.js"}
SKIP_ROOT_FILES = {"admin.html", "template.html", "index.html"}

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
DESC_RE = re.compile(r'<meta name="description" content="(.*?)">')
CANON_RE = re.compile(r'<link rel="canonical" href="https://www\.imprint-diamond\.com/(.*?)">')
OG_TITLE_RE = re.compile(r'<meta property="og:title" content="(.*?)">')
OG_DESC_RE = re.compile(r'<meta property="og:description" content="(.*?)">')
OG_IMAGE_RE = re.compile(r'<meta property="og:image" content="https://www\.imprint-diamond\.com/(.*?)">')
BODY_TAG_RE = re.compile(r"<body([^>]*)>")
ATTR_RE = re.compile(r'(\S+)="([^"]*)"')
LD_JSON_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
CSS_LINK_RE = re.compile(r'<link rel="stylesheet" href="([^"]+)">')
TAIL_SCRIPT_RE = re.compile(r'<script src="([^"]+)"(?:\s[^>]*)?></script>')

registry_lines: list[str] = ["ALL_PAGES: list[PageMeta] = ["]
standalone_lines: list[str] = ["STANDALONE_PAGES: list[PageMeta] = ["]


def rewrite_asset_paths(html: str) -> str:
    return re.sub(r'(?:\.\./)*/?images/', "/static/images/", html)


def rewrite_internal_links(html: str, source_relpath: str, route_map: dict[str, str]) -> str:
    source_dir = posixpath.dirname(source_relpath)

    def repl(match: re.Match[str]) -> str:
        href = match.group(1)
        if href.startswith(("http://", "https://", "tel:", "mailto:", "#", "/static/")):
            return match.group(0)
        resolved = posixpath.normpath(posixpath.join(source_dir, href))
        new_route = route_map.get(resolved)
        if new_route is None:
            return match.group(0)
        return f'href="{new_route}"'

    return re.sub(r'href="([^"]+)"', repl, html)


MAIN_OPEN_RE = re.compile(r"<main([^>]*)>")


def extract_main(html: str) -> tuple[str, str | None]:
    m = MAIN_OPEN_RE.search(html)
    attrs = dict(ATTR_RE.findall(m.group(1))) if m.group(1) else {}
    start = m.end()
    end = html.rindex("</main>")
    return html[start:end].strip("\n"), attrs.get("class")


def extract_body_meta(html: str) -> dict:
    m = BODY_TAG_RE.search(html)
    attrs = dict(ATTR_RE.findall(m.group(1))) if m else {}
    body_class = attrs.get("class", "site-layout")
    extra_class = " ".join(c for c in body_class.split() if c != "site-layout") or None
    return {
        "nav_active": attrs.get("data-site-active") or None,
        "mvc_page": attrs.get("data-mvc") or None,
        "extra_body_class": extra_class,
    }


def extract_breadcrumbs(block: dict) -> list[tuple[str, str | None]]:
    items = sorted(block.get("itemListElement", []), key=lambda i: i.get("position", 0))
    out = []
    for item in items:
        name = item.get("name", "")
        url = item.get("item")
        path = None
        if url:
            path = "/" + url.split("imprint-diamond.com/", 1)[-1]
        out.append((name, path))
    return out


def extract_head(html: str) -> dict:
    title_m = TITLE_RE.search(html)
    desc_m = DESC_RE.search(html)
    canon_m = CANON_RE.search(html)
    og_title_m = OG_TITLE_RE.search(html)
    og_desc_m = OG_DESC_RE.search(html)
    og_image_m = OG_IMAGE_RE.search(html)

    breadcrumbs: list[tuple[str, str | None]] = []
    extra_head_blocks: list[str] = []
    for raw in LD_JSON_RE.findall(html):
        try:
            block = json.loads(raw.strip())
        except json.JSONDecodeError:
            extra_head_blocks.append(raw.strip())
            continue
        if block.get("@type") == "BreadcrumbList":
            breadcrumbs = extract_breadcrumbs(block)
        else:
            extra_head_blocks.append(json.dumps(block, ensure_ascii=False, indent=2))

    extra_css: list[str] = []
    for href in CSS_LINK_RE.findall(html):
        name = href.split("?")[0].rsplit("/", 1)[-1]
        if name not in STANDARD_CSS:
            extra_css.append("/static/css/" + href.rsplit("css/", 1)[-1])

    return {
        "title": title_m.group(1).strip() if title_m else "",
        "description": desc_m.group(1).strip() if desc_m else "",
        "canonical_path": canon_m.group(1).strip() if canon_m else "",
        "og_title": og_title_m.group(1).strip() if og_title_m else None,
        "og_description": og_desc_m.group(1).strip() if og_desc_m else None,
        "og_image": og_image_m.group(1).strip() if og_image_m else None,
        "breadcrumbs": breadcrumbs,
        "extra_head_blocks": extra_head_blocks,
        "extra_css": extra_css,
    }


def extract_extra_scripts(html: str) -> list[str]:
    tail = html[html.rindex("</footer>"):]
    scripts = []
    for src in TAIL_SCRIPT_RE.findall(tail):
        name = src.split("?")[0].rsplit("/", 1)[-1]
        if name in STANDARD_JS:
            continue
        scripts.append("/static/js/" + src.rsplit("js/", 1)[-1])
    return scripts


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def page_meta_literal(var_name: str, route: str, template: str, head: dict, body: dict,
                       content_fragment: str | None = None) -> str:
    return (
        f"{var_name} = PageMeta(\n"
        f"    route={route!r},\n"
        f"    template={template!r},\n"
        f"    title={head['title']!r},\n"
        f"    description={head['description']!r},\n"
        f"    canonical_path={head['canonical_path']!r},\n"
        f"    og_title={head['og_title']!r},\n"
        f"    og_description={head['og_description']!r},\n"
        f"    og_image={head['og_image']!r},\n"
        f"    breadcrumbs={head['breadcrumbs']!r},\n"
        f"    nav_active={body['nav_active']!r},\n"
        f"    mvc_page={body['mvc_page']!r},\n"
        f"    extra_body_class={body['extra_body_class']!r},\n"
        f"    content_fragment={content_fragment!r},\n"
        f"    extra_head_blocks={head['extra_head_blocks']!r},\n"
        f")"
    )


def process_simple(source_relpath: str, route: str, template_relpath: str, var_name: str,
                    route_map: dict[str, str]) -> str:
    html = (ROOT / source_relpath).read_text(encoding="utf-8")
    head = extract_head(html)
    body = extract_body_meta(html)
    main_html, main_class = extract_main(html)
    main_html = rewrite_asset_paths(main_html)
    main_html = rewrite_internal_links(main_html, source_relpath, route_map)
    extra_scripts = [rewrite_asset_paths(s) for s in extract_extra_scripts(html)]

    parts = ['{% extends "base.html" %}']
    if main_class:
        parts.append("{% block main_class %} class=\"" + main_class + "\"{% endblock %}")
    if head["extra_css"]:
        parts.append("{% block extra_css %}")
        parts += [f'<link rel="stylesheet" href="{href}">' for href in head["extra_css"]]
        parts.append("{% endblock %}")
    if head["extra_head_blocks"]:
        parts.append("{% block extra_head %}")
        for block in head["extra_head_blocks"]:
            parts.append(f'<script type="application/ld+json">\n{block}\n</script>')
        parts.append("{% endblock %}")
    parts.append("{% block content %}")
    parts.append(main_html)
    parts.append("{% endblock %}")
    if extra_scripts:
        parts.append("{% block extra_scripts %}")
        parts += [f'<script src="{src}"></script>' for src in extra_scripts]
        parts.append("{% endblock %}")

    write(PAGES_DIR / template_relpath, "\n".join(parts) + "\n")
    template_key = "pages/" + template_relpath.replace("\\", "/")
    literal = page_meta_literal(var_name, route, template_key, head, body)
    registry_lines.append(f"    {var_name},")
    return literal


STANDALONE_TITLE_RE = TITLE_RE
STANDALONE_CSS_RE = re.compile(r'<link rel="stylesheet" href="([^"]+)">')
STANDALONE_SCRIPT_RE = re.compile(r'<script src="([^"]+)"></script>')
STANDALONE_MAIN_RE = re.compile(r"<main([^>]*)>(.*?)</main>", re.S)


def process_standalone(source_relpath: str, route: str, template_relpath: str, var_name: str) -> str:
    """Quote-sheet / share-summary pages: no nav/footer chrome, client-rendered.
    Kept as their own minimal documents rather than extending base.html —
    and routes stay byte-identical since these are shared externally."""
    html = (ROOT / source_relpath).read_text(encoding="utf-8")
    title = STANDALONE_TITLE_RE.search(html).group(1).strip()
    css_href = STANDALONE_CSS_RE.search(html).group(1)
    css_href = "/static/css/" + css_href.rsplit("css/", 1)[-1]
    main_m = STANDALONE_MAIN_RE.search(html)
    main_attrs = main_m.group(1)
    main_inner = main_m.group(2).strip()
    scripts = STANDALONE_SCRIPT_RE.findall(html)
    scripts = ["/static/js/" + s.rsplit("js/", 1)[-1] for s in scripts]

    doc = (
        "<!doctype html>\n"
        '<html lang="zh-Hant-TW">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '  <meta name="robots" content="noindex">\n'
        f"  <title>{title}</title>\n"
        f'  <link rel="stylesheet" href="{css_href}">\n'
        "</head>\n"
        '<body class="quote-sheet-body">\n'
        f"  <main{main_attrs}>\n"
        f"    {main_inner}\n"
        "  </main>\n"
        + "".join(f'  <script src="{s}"></script>\n' for s in scripts)
        + "</body>\n"
        "</html>\n"
    )
    write(PAGES_DIR / template_relpath, doc)
    template_key = "pages/" + template_relpath.replace("\\", "/")
    literal = (
        f"{var_name} = PageMeta(\n"
        f"    route={route!r},\n"
        f"    template={template_key!r},\n"
        f"    title={title!r},\n"
        f"    description='',\n"
        f"    canonical_path='',\n"
        f")"
    )
    standalone_lines.append(f"    {var_name},")
    return literal


def process_family(source_relpath: str, route: str, shared_template: str, fragment_relpath: str,
                    var_name: str, route_map: dict[str, str]) -> str:
    html = (ROOT / source_relpath).read_text(encoding="utf-8")
    head = extract_head(html)
    body = extract_body_meta(html)
    main_html, _main_class = extract_main(html)
    main_html = rewrite_asset_paths(main_html)
    main_html = rewrite_internal_links(main_html, source_relpath, route_map)

    write(FRAGMENTS_DIR / fragment_relpath, main_html + "\n")
    fragment_key = fragment_relpath.replace("\\", "/")
    literal = page_meta_literal(var_name, route, shared_template, head, body, content_fragment=fragment_key)
    registry_lines.append(f"    {var_name},")
    return literal


def discover_jewelry() -> tuple[list[str], list[tuple[str, str]]]:
    jewelry_root = ROOT / "jewelry"
    categories = []
    styles = []
    for cat_dir in sorted(jewelry_root.iterdir()):
        if not cat_dir.is_dir() or not (cat_dir / "index.html").exists():
            continue
        categories.append(cat_dir.name)
        for style_dir in sorted(cat_dir.iterdir()):
            if style_dir.is_dir() and (style_dir / "index.html").exists():
                styles.append((cat_dir.name, style_dir.name))
    return categories, styles


def discover_series() -> list[str]:
    series_root = ROOT / "series"
    return sorted(d.name for d in series_root.iterdir() if d.is_dir() and (d / "index.html").exists())


def discover_flat_pages() -> list[str]:
    return sorted(f.name for f in ROOT.glob("*.html") if f.name not in SKIP_ROOT_FILES)


def main() -> None:
    categories, styles = discover_jewelry()
    series_slugs = discover_series()
    flat_pages = discover_flat_pages()

    route_map: dict[str, str] = {"index.html": "/"}
    for name in flat_pages:
        route_map[name] = f"/{name}"
    route_map["jewelry/index.html"] = "/jewelry/"
    for cat in categories:
        route_map[f"jewelry/{cat}/index.html"] = f"/jewelry/{cat}/"
    for cat, style in styles:
        route_map[f"jewelry/{cat}/{style}/index.html"] = f"/jewelry/{cat}/{style}/"
    for slug in series_slugs:
        route_map[f"series/{slug}/index.html"] = f"/series/{slug}/"
    route_map["shop/calculator/index.html"] = "/shop/calculator/"
    route_map["shop/quote-sheet.html"] = "/shop/quote-sheet.html"
    route_map["share/summary.html"] = "/share/summary.html"

    literals: list[str] = []

    literals.append(process_simple("index.html", "/", "index.html", "HOME", route_map))
    for name in flat_pages:
        var = "PAGE_" + name.replace(".html", "").replace("-", "_").upper()
        literals.append(process_simple(name, route_map[name], name, var, route_map))
    literals.append(process_simple("jewelry/index.html", "/jewelry/", "jewelry/index.html", "JEWELRY_INDEX", route_map))
    literals.append(process_simple("shop/calculator/index.html", "/shop/calculator/", "shop/calculator.html", "SHOP_CALCULATOR", route_map))

    for cat in categories:
        var = f"JEWELRY_CATEGORY_{cat.upper().replace('-', '_')}"
        literals.append(process_family(
            f"jewelry/{cat}/index.html", f"/jewelry/{cat}/", "pages/jewelry_category.html",
            f"jewelry_category/{cat}.html", var, route_map,
        ))

    for cat, style in styles:
        var = f"JEWELRY_STYLE_{cat.upper().replace('-', '_')}_{style.upper().replace('-', '_')}"
        literals.append(process_family(
            f"jewelry/{cat}/{style}/index.html", f"/jewelry/{cat}/{style}/", "pages/jewelry_style.html",
            f"jewelry_style/{cat}-{style}.html", var, route_map,
        ))

    for slug in series_slugs:
        var = f"SERIES_{slug.upper().replace('-', '_')}"
        literals.append(process_family(
            f"series/{slug}/index.html", f"/series/{slug}/", "pages/series_detail.html",
            f"series/{slug}.html", var, route_map,
        ))

    # Standalone no-chrome pages (shareable links — routes/URLs must stay exact)
    standalone_literals = [
        process_standalone("shop/quote-sheet.html", "/shop/quote-sheet.html", "shop/quote-sheet.html", "STANDALONE_QUOTE_SHEET"),
        process_standalone("share/summary.html", "/share/summary.html", "share/summary.html", "STANDALONE_SHARE_SUMMARY"),
    ]

    registry_lines.append("]")
    standalone_lines.append("]")

    header = '''"""Route registry — generated by scripts/migrate_to_jinja.py.

Maps each page URL to its Jinja template and the metadata base.html needs
(title, description, canonical, OG tags, breadcrumbs, nav highlight).
Regenerate by re-running the migration script; hand-edit only for pages
added after the migration.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PageMeta:
    route: str
    template: str
    title: str
    description: str
    canonical_path: str
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None
    breadcrumbs: list[tuple[str, str | None]] = field(default_factory=list)
    nav_active: str | None = None
    mvc_page: str | None = None
    extra_body_class: str | None = None
    content_fragment: str | None = None
    extra_head_blocks: list[str] = field(default_factory=list)


'''

    body_text = (
        "\n\n".join(literals) + "\n\n\n"
        + "\n\n".join(standalone_literals) + "\n\n\n"
        + "\n".join(registry_lines) + "\n\n\n"
        + "\n".join(standalone_lines) + "\n"
    )
    write(REGISTRY_FILE, header + body_text)

    print(f"Wrote {len(literals)} page templates/fragments.")
    print(f"Jewelry categories: {categories}")
    print(f"Jewelry styles: {len(styles)} -> {styles}")
    print(f"Series: {series_slugs}")
    print(f"Registry written to {REGISTRY_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
