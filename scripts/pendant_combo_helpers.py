# -*- coding: utf-8 -*-
"""Shared helpers for pendant combo batch generation."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
MANIFEST = ROOT / "scripts" / "pendant-combo-manifest.json"
CACHE = ROOT / "scripts" / "pendant-combo-media-cache.json"
PROGRESS = ROOT / "scripts" / "pendant-combo-progress.json"
ZH = "項墜"


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_ref(job: dict) -> str | None:
    if job.get("ref"):
        return job["ref"]
    st, dia = job["style"], job["diamond"]
    d = "" if dia == "white" else f"_{dia}"
    alt = f"images/shop-product/rose_gold/{ZH}{st}_rose{d}.png"
    if (PUBLIC / alt).exists():
        return alt
    base = f"images/shop-product/rose_gold/{ZH}{st}_rose.png"
    return base if (PUBLIC / base).exists() else None


def pending_jobs() -> list[dict]:
    manifest = load_json(MANIFEST, [])
    completed = set(load_json(PROGRESS, {"completed": []}).get("completed", []))
    jobs = []
    for job in manifest:
        dest = job["dest"]
        if dest in completed:
            continue
        if (PUBLIC / dest).exists():
            continue
        ref = resolve_ref(job)
        jobs.append({**job, "resolved_ref": ref})
    return jobs


def all_refs() -> list[str]:
    manifest = load_json(MANIFEST, [])
    return sorted(set(r for j in manifest if (r := resolve_ref(j))))


def append_progress(dest: str) -> None:
    prog = load_json(PROGRESS, {"completed": []})
    if dest not in prog["completed"]:
        prog["completed"].append(dest)
    save_json(PROGRESS, prog)


def update_cache(ref: str, media_id: str) -> None:
    cache = load_json(CACHE, {})
    cache[ref] = media_id
    save_json(CACHE, cache)
