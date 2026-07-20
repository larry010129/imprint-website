# -*- coding: utf-8 -*-
"""Prepare next Higgsfield batch: stage refs, skip existing, reuse media cache."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SHOP = PUBLIC / "images" / "shop-product"
UPLOAD = ROOT / "scripts" / "_hf_upload"
PROGRESS = ROOT / "scripts" / "pendant-combo-progress.json"
BATCH_OUT = ROOT / "scripts" / "_hf_batch.json"

# reuse path logic from generate_pendant_combos
sys.path.insert(0, str(ROOT / "scripts"))
from generate_pendant_combos import missing_jobs  # noqa: E402


def load_progress() -> dict:
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    return {"completed": [], "failed": [], "media_cache": {}}


def save_progress(data: dict) -> None:
    PROGRESS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_ref(ref_rel: str) -> Path:
    name = Path(ref_rel).name
    matches = list((PUBLIC / "images" / "shop-product").rglob(name))
    if not matches:
        raise FileNotFoundError(ref_rel)
    return matches[0]


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    jobs = missing_jobs()
    progress = load_progress()
    cache = progress.setdefault("media_cache", {})
    completed = set(progress.get("completed", []))

    pending = []
    for job in jobs:
        dest = PUBLIC / job["dest"]
        if dest.exists() or job["dest"] in completed:
            continue
        pending.append(job)
        if len(pending) >= n:
            break

    remaining = len([j for j in jobs if not (PUBLIC / j["dest"]).exists()])

    if not pending:
        print(json.dumps({"done": True, "remaining": remaining}))
        return 0

    UPLOAD.mkdir(exist_ok=True)
    batch = []
    uploads_needed = []
    for i, job in enumerate(pending):
        ref_rel = job["ref"]
        entry = {**job, "media_id": cache.get(ref_rel)}
        if not entry["media_id"]:
            src = resolve_ref(ref_rel)
            upload_name = f"ref-{i}.png"
            dst = UPLOAD / upload_name
            shutil.copy2(src, dst)
            entry["upload_name"] = upload_name
            entry["upload_path"] = str(dst)
            uploads_needed.append({"filename": upload_name, "ref_rel": ref_rel})
        batch.append(entry)

    BATCH_OUT.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "done": False,
                "remaining": remaining,
                "batch_size": len(batch),
                "uploads_needed": uploads_needed,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
