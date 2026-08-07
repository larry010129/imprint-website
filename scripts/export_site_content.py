"""Export Jinja pages → static bodies + page registry (slot seed / tooling).

Outputs:
  content/site/bodies/<key>.html
  content/site/fragments/** (copy)
  content/site/page-registry.json

Run from repo root:
  python scripts/export_site_content.py
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.requests import Request

from config.routes import ALL_PAGES, STANDALONE_PAGES, PageMeta
from config.settings import settings

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "content" / "site"
BODIES = OUT / "bodies"
FRAGMENTS_OUT = OUT / "fragments"
REGISTRY_OUT = OUT / "page-registry.json"

BASE_CSS = {
    "/static/css/base.css",
    "/static/css/nav.css",
    "/static/css/footer.css",
    "/static/css/pages.css",
    "/static/css/skeleton.css",
    "/static/css/responsive.css",
    "/static/css/social-fab.css",
    "/favicon.svg",
}
BASE_JS_PREFIXES = (
    "/static/js/htmx.min.js",
    "/static/js/nav-dropdown.js",
    "/static/js/nav-chrome.js",
    "/static/js/skeleton-ui.js",
    "/static/js/site-layout.js",
    "/static/js/main.js",
    "/static/js/social-fab.js",
)


def route_key(route: str) -> str:
    if route == "/":
        return "home"
    key = route.strip("/").replace("/", "__")
    key = key.replace(".html", "_html")
    return key or "home"


def layout_for(meta: PageMeta, template_src: str) -> str:
    if "base-auth.html" in template_src:
        return "auth"
    if meta.template in {
        "pages/shop/quote-sheet.html",
        "pages/share/summary.html",
    }:
        return "bare"
    return "site"


def meta_to_dict(meta: PageMeta) -> dict:
    return {
        "route": meta.route,
        "template": meta.template,
        "title": meta.title,
        "description": meta.description,
        "canonical_path": meta.canonical_path,
        "og_title": meta.og_title,
        "og_description": meta.og_description,
        "og_image": meta.og_image,
        "breadcrumbs": [[a, b] for a, b in meta.breadcrumbs],
        "mvc_page": meta.mvc_page,
        "extra_body_class": meta.extra_body_class,
        "content_fragment": meta.content_fragment,
        "extra_head_blocks": meta.extra_head_blocks,
        "body_key": route_key(meta.route),
    }


def build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(settings.templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.globals["google_client_id"] = settings.google_client_id
    env.globals["recaptcha_site_key"] = settings.recaptcha_site_key
    return env


def stub_request() -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 0),
            "server": ("127.0.0.1", 8080),
        }
    )


def render_context(meta: PageMeta) -> dict:
    from app.controllers.web_controller import _context, _load_fragment

    ctx = _context(stub_request(), meta)
    # Prefer raw defaults for slot apply later — empty CMS rows.
    ctx["page_images"] = []
    ctx["page_image"] = None
    ctx["page_copy_slots"] = []
    ctx["site_cms_edit"] = False
    if meta.content_fragment:
        ctx["content_html"] = _load_fragment(meta.content_fragment)
    return ctx


def strip_base_assets(links: list[str], scripts: list[dict]) -> tuple[list[str], list[dict]]:
    extra_css = []
    for href in links:
        path = href.split("?")[0]
        if path in BASE_CSS or path.startswith("/static/css/cms-"):
            continue
        extra_css.append(href)
    extra_scripts = []
    for scr in scripts:
        if scr.get("inline"):
            extra_scripts.append(scr)
            continue
        src = (scr.get("src") or "").split("?")[0]
        if any(src.startswith(p.split("?")[0]) for p in BASE_JS_PREFIXES):
            continue
        if "botpress" in src or "cdn.botpress" in src:
            continue
        extra_scripts.append(scr)
    return extra_css, extra_scripts


def export_page(env: Environment, meta: PageMeta) -> dict:
    template_path = settings.templates_dir / meta.template
    template_src = template_path.read_text(encoding="utf-8") if template_path.is_file() else ""
    layout = layout_for(meta, template_src)
    entry = meta_to_dict(meta)
    entry["layout"] = layout
    entry["main_class"] = ""
    entry["extra_css"] = []
    entry["extra_scripts"] = []
    entry["head_extras"] = []

    if layout == "bare":
        # Full document → keep body inner + head assets as extras
        html = template_src
        soup = BeautifulSoup(html, "html.parser")
        body = soup.body
        main = soup.find("main")
        body_html = str(main) if main else ("".join(str(c) for c in body.children) if body else html)
        key = route_key(meta.route)
        (BODIES / f"{key}.html").write_text(body_html, encoding="utf-8")
        links = [l.get("href") for l in soup.find_all("link", href=True)]
        scripts = []
        for s in soup.find_all("script"):
            item = {}
            if s.get("src"):
                item["src"] = s["src"]
            if s.get("type"):
                item["type"] = s["type"]
            if s.string and not s.get("src"):
                item["inline"] = s.string
            if item:
                scripts.append(item)
        entry["extra_css"] = [h for h in links if h and h.endswith(".css") or (h and "/css/" in h)]
        entry["extra_scripts"] = scripts
        entry["robots"] = "noindex"
        return entry

    ctx = render_context(meta)
    rendered = env.get_template(meta.template).render(**ctx)
    soup = BeautifulSoup(rendered, "html.parser")

    main = soup.find("main")
    if main:
        class_attr = main.get("class")
        if class_attr:
            entry["main_class"] = " ".join(class_attr)
        body_html = "".join(str(c) for c in main.children)
    else:
        body_html = ""

    if layout == "auth" and main:
        body_html = "".join(str(c) for c in main.children)

    key = route_key(meta.route)
    (BODIES / f"{key}.html").write_text(body_html, encoding="utf-8")

    links = []
    for link in soup.find_all("link", href=True):
        href = link["href"]
        if link.get("rel") and "stylesheet" in link.get("rel"):
            links.append(href)
    scripts = []
    for s in soup.find_all("script"):
        src = s.get("src")
        text = s.string or "".join(s.strings) or ""
        if not src:
            if not text.strip():
                continue
            stype = (s.get("type") or "").lower()
            if "ld+json" in stype:
                continue
            if "botpress" in text.lower() or "loadImprintChat" in text:
                continue
            if "imgFallback" in text:
                continue
            if "data-hover-footer-root" in text:
                continue
            item = {"inline": text}
            if s.get("type"):
                item["type"] = s["type"]
            scripts.append(item)
            continue
        item = {"src": src}
        if s.get("type"):
            item["type"] = s["type"]
        if s.get("defer") is not None:
            item["defer"] = True
        if s.get("async") is not None:
            item["async"] = True
        scripts.append(item)

    extra_css, extra_scripts = strip_base_assets(links, scripts)
    for s in soup.find_all("script", src=True):
        if "accounts.google.com" in s["src"]:
            extra_scripts.insert(0, {"src": s["src"], "async": True, "defer": True})

    entry["extra_css"] = extra_css
    entry["extra_scripts"] = extra_scripts
    if layout == "auth":
        entry["robots"] = "noindex, nofollow"

    for link in soup.find_all("link", rel=True):
        rel = link.get("rel")
        if rel and "preload" in rel and link.get("as") == "image":
            entry["head_extras"].append(
                {
                    "tag": "link",
                    "rel": "preload",
                    "as": "image",
                    "href": link.get("href"),
                    "type": link.get("type"),
                    "fetchpriority": link.get("fetchpriority"),
                }
            )

    m = re.search(
        r'\{%\s*block\s+main_class\s*%\}\s*class="([^"]+)"',
        template_src,
    )
    if m:
        entry["main_class"] = m.group(1)

    return entry


def main() -> None:
    BODIES.mkdir(parents=True, exist_ok=True)
    if FRAGMENTS_OUT.exists():
        shutil.rmtree(FRAGMENTS_OUT)
    src_frag = settings.templates_dir / "fragments"
    if src_frag.is_dir():
        shutil.copytree(src_frag, FRAGMENTS_OUT)

    env = build_env()
    pages = [*ALL_PAGES, *STANDALONE_PAGES]
    registry = []
    for meta in pages:
        print(f"export {meta.route}")
        registry.append(export_page(env, meta))

    # /s/{token} uses share summary body
    share = next(p for p in registry if p["route"] == "/share/summary")
    registry.append(
        {
            **share,
            "route": "/s/[token]",
            "body_key": share["body_key"],
            "title": "分享試算｜銘印鑽石",
            "is_share_token": True,
        }
    )

    REGISTRY_OUT.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote {len(registry)} entries → {REGISTRY_OUT}")


if __name__ == "__main__":
    main()
