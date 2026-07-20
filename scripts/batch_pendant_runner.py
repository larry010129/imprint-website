# -*- coding: utf-8 -*-
"""Batch state helpers for pendant combo Higgsfield generation."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from pendant_combo_helpers import (
    append_progress,
    load_json,
    pending_jobs,
    resolve_ref,
    save_json,
    CACHE,
    ROOT,
)

BATCH_SIZE = 4


def cache_ref(ref: str, media_id: str) -> None:
    cache = load_json(CACHE, {})
    cache[ref] = media_id
    save_json(CACHE, cache)


def save_result(job: dict, url: str) -> None:
    cmd = [
        str(ROOT / ".venv" / "Scripts" / "python.exe"),
        str(ROOT / "scripts" / "save_pendant_combo.py"),
        "--url",
        url,
        "--style",
        job["style"],
        "--pendant",
        job["pendant"],
        "--chain",
        job["chain"],
        "--diamond",
        job["diamond"],
    ]
    subprocess.check_call(cmd, cwd=ROOT)
    append_progress(job["dest"])


def cmd_status() -> None:
    jobs = pending_jobs()
    cache = load_json(CACHE, {})
    refs_needed = sorted({j["resolved_ref"] for j in jobs if j["resolved_ref"] and j["resolved_ref"] not in cache})
    ready = [j for j in jobs if j.get("resolved_ref") in cache]
    print(json.dumps({"pending": len(jobs), "cached_refs": len(cache), "refs_needed": len(refs_needed), "ready": len(ready)}, indent=2))


def cmd_next() -> None:
    jobs = pending_jobs()
    cache = load_json(CACHE, {})
    ready = [j for j in jobs if j.get("resolved_ref") in cache][:BATCH_SIZE]
    out = []
    for j in ready:
        ref = j["resolved_ref"]
        out.append(
            {
                "dest": j["dest"],
                "style": j["style"],
                "pendant": j["pendant"],
                "chain": j["chain"],
                "diamond": j["diamond"],
                "ref": ref,
                "media_id": cache[ref],
                "prompt": j["prompt"],
            }
        )
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_refs(batch: int) -> None:
    jobs = pending_jobs()
    cache = load_json(CACHE, {})
    refs = sorted({j["resolved_ref"] for j in jobs if j["resolved_ref"] and j["resolved_ref"] not in cache})
    start = batch * 8
    chunk = refs[start : start + 8]
    files = [{"filename": (ROOT / "public" / r).name, "content_type": "image/png"} for r in chunk]
    print(json.dumps({"refs": chunk, "files": files}, ensure_ascii=False, indent=2))


def cmd_cache_uploads(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    for u in data["uploads"]:
        cache_ref(u["ref"], u["media_id"])
    print(f"cached {len(data['uploads'])} refs")


def cmd_record(path: Path) -> None:
    records = json.loads(path.read_text(encoding="utf-8"))
    for r in records:
        job = r["job"]
        save_result(job, r["url"])
    print(f"saved {len(records)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("next")
    p_refs = sub.add_parser("refs")
    p_refs.add_argument("--batch", type=int, default=0)
    p_cache = sub.add_parser("cache-uploads")
    p_cache.add_argument("path", type=Path)
    p_rec = sub.add_parser("record")
    p_rec.add_argument("path", type=Path)
    args = ap.parse_args()
    if args.cmd == "status":
        cmd_status()
    elif args.cmd == "next":
        cmd_next()
    elif args.cmd == "refs":
        cmd_refs(args.batch)
    elif args.cmd == "cache-uploads":
        cmd_cache_uploads(args.path)
    elif args.cmd == "record":
        cmd_record(args.path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
