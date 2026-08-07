"""Generate App Router page.tsx files from content/site/page-registry.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "content" / "site" / "page-registry.json"
APP = ROOT / "apps" / "web" / "src" / "app"

PAGE_TMPL = '''import {{ createPage }} from "@/lib/site-page";

const page = createPage({route!r});

export const generateMetadata = page.generateMetadata;
export default page.Page;
'''

NOT_FOUND_TMPL = '''import { createPage } from "@/lib/site-page";

const page = createPage("/404");

export default async function NotFound() {
  return page.Page({});
}
'''

SHARE_TMPL = '''import { createPage } from "@/lib/site-page";

const page = createPage("/share/summary");

export const generateMetadata = page.generateMetadata;
export default page.Page;
'''


def route_to_dir(route: str) -> Path:
    if route == "/":
        return APP
    # /about → about/
    # /jewelry/rings/ → jewelry/rings/
    # /shop/calculator/ → shop/calculator/
    # /s/[token] → s/[token]/
    rel = route.lstrip("/")
    if rel.endswith("/") and not rel.endswith(".html/"):
        rel = rel.rstrip("/")
    return APP / rel


def main() -> None:
    rows = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for row in rows:
        route = row["route"]
        if route == "/s/[token]":
            dest = APP / "s" / "[token]"
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "page.tsx").write_text(SHARE_TMPL, encoding="utf-8")
            print("write", dest / "page.tsx")
            continue
        if route == "/404":
            continue  # handled by not-found.tsx
        dest = route_to_dir(route)
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "page.tsx").write_text(
            PAGE_TMPL.format(route=route), encoding="utf-8"
        )
        print("write", dest / "page.tsx")

    (APP / "not-found.tsx").write_text(NOT_FOUND_TMPL, encoding="utf-8")
    print("write", APP / "not-found.tsx")


if __name__ == "__main__":
    main()
