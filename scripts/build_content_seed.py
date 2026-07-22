#!/usr/bin/env python3
"""Build app/data/content-seed.json from frontend TS sources (one-shot)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "data" / "content-seed.json"
TEASER_IDS = {"item-1", "item-6", "item-9", "item-10"}


def _unescape(s: str) -> str:
    return s.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")


def _extract_string_fields(block: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("name", "role", "category", "city", "text", "question", "answer", "title", "id"):
        m = re.search(rf'{key}:\s*"((?:\\.|[^"\\])*)"', block, re.S)
        if m:
            out[key] = _unescape(m.group(1))
    return out


def parse_testimonials(text: str) -> list[dict]:
    items = []
    for m in re.finditer(r"\{\s*id:\s*(\d+),.*?rating:\s*(\d+),?\s*\}", text, re.S):
        block = m.group(0)
        fields = _extract_string_fields(block)
        items.append(
            {
                "name": fields["name"],
                "role": fields["role"],
                "category": fields["category"],
                "city": fields["city"],
                "text": fields["text"],
                "rating": int(m.group(2)),
                "sort_order": int(m.group(1)),
            }
        )
    return items


def parse_faq(text: str) -> tuple[list[dict], list[dict]]:
    categories: list[dict] = []
    items: list[dict] = []
    # Split top-level category objects by id: "..."
    cat_blocks = re.findall(
        r'\{\s*id:\s*"([^"]+)",\s*title:\s*"([^"]+)",\s*items:\s*\[(.*?)\],\s*\}',
        text,
        re.S,
    )
    for sort_i, (cat_id, title, items_body) in enumerate(cat_blocks):
        categories.append({"id": cat_id, "title": title, "sort_order": sort_i})
        entry_blocks = re.findall(
            r'\{\s*id:\s*"([^"]+)",\s*question:\s*"((?:\\.|[^"\\])*)",\s*answer:\s*"((?:\\.|[^"\\])*)",?\s*\}',
            items_body,
            re.S,
        )
        for item_i, (item_id, question, answer) in enumerate(entry_blocks):
            q = _unescape(question)
            a = _unescape(answer)
            items.append(
                {
                    "id": item_id,
                    "category_id": cat_id,
                    "question": q,
                    "answer": a,
                    "sort_order": item_i,
                    "show_in_teaser": item_id in TEASER_IDS,
                }
            )
    return categories, items


def main() -> None:
    testimonials = parse_testimonials(
        (ROOT / "frontend/src/data/testimonials.ts").read_text(encoding="utf-8")
    )
    categories, faq_items = parse_faq(
        (ROOT / "frontend/src/data/faq-content.ts").read_text(encoding="utf-8")
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "testimonials": testimonials,
        "faq_categories": categories,
        "faq_items": faq_items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Wrote {OUT}: {len(testimonials)} testimonials, "
        f"{len(categories)} categories, {len(faq_items)} faq items"
    )


if __name__ == "__main__":
    main()
