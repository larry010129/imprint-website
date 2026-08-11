"""Verify data-cms-text / data-cms-button template attributes against copy_slot_specs().

Checks, per mapped page:
1. Every attribute key in the template has a spec for that page.
2. Every spec for that page appears in the template (orphans reported).
3. default_text matches the template's current inner text (tags stripped,
   all whitespace removed for comparison). Mismatches on NEW slots are
   errors; pre-existing seeded drift is reported separately.

Usage: .venv\\Scripts\\python.exe scripts\\verify_cms_copy_slots.py
"""

from __future__ import annotations

import html as html_mod
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.cms_copy_slot_specs import copy_slot_specs  # noqa: E402

PAGES_DIR = ROOT / "content" / "site" / "templates" / "pages"
FRAGMENTS_DIR = ROOT / "content" / "site" / "fragments" / "series"

PAGE_ROUTES = {
    "index.html": "/",
    "about.html": "/about",
    "series.html": "/series",
    "contact.html": "/contact",
    "what-is-dna-diamond.html": "/what-is-dna-diamond",
    "diamond-4c.html": "/diamond-4c",
    "lab-grown-diamond.html": "/lab-grown-diamond",
    "diamond-comparison.html": "/diamond-comparison",
    "journal.html": "/journal",
    "stories.html": "/stories",
    "faq.html": "/faq",
    "privacy.html": "/privacy",
    "terms.html": "/terms",
    "return-policy.html": "/return-policy",
}

def _head_spec_keys() -> set[tuple[str, str]]:
    """(page_key, slot_key) pairs that already existed at git HEAD — those are
    pre-existing seeded rows whose defaults may legitimately differ from the
    template (the live site already serves the seeded values)."""
    import subprocess

    out = subprocess.run(
        ["git", "show", "HEAD:app/cms_copy_slot_specs.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        check=True,
    ).stdout
    ns: dict = {}
    exec(compile(out, "cms_copy_slot_specs@HEAD", "exec"), ns)  # noqa: S102
    return {(s["page_key"], s["slot_key"]) for s in ns["copy_slot_specs"]()}

_ATTR_RE = re.compile(
    r"<(?P<tag>[a-zA-Z0-9]+)(?P<attrs>[^>]*?)\bdata-cms-(?P<kind>text|button)\s*=\s*"
    r"(?P<q>['\"])(?P<slot>[^'\"]+)(?P=q)(?P<attrs2>[^>]*)>"
    r"(?P<body>.*?)"
    r"</(?P=tag)>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


def norm(text: str) -> str:
    text = html_mod.unescape(_TAG_RE.sub("", text))
    return re.sub(r"\s+", "", text)


def scan_file(path: Path) -> dict[str, tuple[str, str]]:
    """slot_key -> (kind, normalized body text)"""
    found: dict[str, tuple[str, str]] = {}
    for m in _ATTR_RE.finditer(path.read_text(encoding="utf-8")):
        found[m.group("slot")] = (m.group("kind"), norm(m.group("body")))
    return found


def main() -> int:
    specs = copy_slot_specs()
    preexisting = _head_spec_keys()
    by_page: dict[str, dict[str, dict]] = {}
    for spec in specs:
        by_page.setdefault(spec["page_key"], {})[spec["slot_key"]] = spec

    files: dict[str, Path] = {name: PAGES_DIR / name for name in PAGE_ROUTES}
    for frag in sorted(FRAGMENTS_DIR.glob("*.html")):
        files[f"series/{frag.name}"] = frag

    errors: list[str] = []
    drift: list[str] = []
    orphans: list[str] = []

    for name, route in {**PAGE_ROUTES, **{f"series/{p.name}": f"/series/{p.stem}/" for p in FRAGMENTS_DIR.glob('*.html')}}.items():
        path = files[name]
        if not path.is_file():
            errors.append(f"MISSING FILE {path}")
            continue
        attrs = scan_file(path)
        page_specs = by_page.get(route, {})
        for key, (kind, _body) in attrs.items():
            spec = page_specs.get(key)
            if not spec:
                errors.append(f"{route} {name}: attr '{key}' ({kind}) has NO spec")
            elif spec["kind"] != kind:
                errors.append(f"{route} {name}: '{key}' kind mismatch attr={kind} spec={spec['kind']}")
        for key, spec in page_specs.items():
            if key not in attrs:
                orphans.append(f"{route} '{key}' ({spec['kind']}) not in {name}")
        for key, (kind, body) in attrs.items():
            spec = page_specs.get(key)
            if not spec:
                continue
            if norm(spec["default_text"]) != body:
                entry = f"{route} '{key}': default != template text"
                if (route, key) in preexisting:
                    drift.append(entry)
                else:
                    errors.append(entry + f"\n    spec: {norm(spec['default_text'])[:80]}\n    tmpl: {body[:80]}")

    # Specs for pages with no scanned template at all
    scanned_routes = set(PAGE_ROUTES.values()) | {f"/series/{p.stem}/" for p in FRAGMENTS_DIR.glob("*.html")}
    for route, page_specs in sorted(by_page.items()):
        if route not in scanned_routes:
            orphans.append(f"{route}: NO template scanned ({len(page_specs)} specs)")

    print(f"specs total: {len(specs)}")
    print(f"drift (pre-existing, kept as-is): {len(drift)}")
    for d in drift:
        print("  DRIFT", d)
    print(f"orphans (spec without template attr): {len(orphans)}")
    for o in orphans:
        print("  ORPHAN", o)
    print(f"errors: {len(errors)}")
    for e in errors:
        print("  ERROR", e)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
