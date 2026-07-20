# -*- coding: utf-8 -*-
"""Local helpers for pendant combo Higgsfield batch (PUT uploads, save, progress)."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pendant_combo_helpers import (  # noqa: E402
    PROGRESS,
    PUBLIC,
    load_json,
    pending_jobs,
    resolve_ref,
    save_json,
)

ROOT = Path(__file__).resolve().parents[1]


def cmd_pending() -> int:
    jobs = pending_jobs()
    print(json.dumps(jobs, ensure_ascii=False))
    return 0


def cmd_refs_missing() -> int:
    prog = load_json(PROGRESS, {"media_cache": {}})
    cache = prog.get("media_cache", {})
    refs = sorted(set(r for j in pending_jobs() if (r := resolve_ref(j))))
    missing = [r for r in refs if r not in cache]
    print(json.dumps(missing, ensure_ascii=False))
    return 0


def cmd_put_uploads(upload_json: Path) -> int:
    data = json.loads(upload_json.read_text(encoding="utf-8"))
    uploads = data.get("uploads", data if isinstance(data, list) else [])
    for u in uploads:
        local = ROOT / u["local"] if "local" in u else PUBLIC / u["ref"]
        req = urllib.request.Request(
            u["upload_url"],
            data=Path(local).read_bytes(),
            method="PUT",
            headers={"Content-Type": "image/png"},
        )
        urllib.request.urlopen(req)
        print(f"PUT ok {u.get('ref', local)}")
    return 0


def cmd_cache_ref(ref: str, media_id: str) -> int:
    prog = load_json(PROGRESS, {"completed": [], "failed": [], "media_cache": {}})
    prog.setdefault("media_cache", {})[ref] = media_id
    save_json(PROGRESS, prog)
    print(f"cached {ref} -> {media_id}")
    return 0


def cmd_complete(dest: str) -> int:
    prog = load_json(PROGRESS, {"completed": [], "failed": [], "media_cache": {}})
    if dest not in prog["completed"]:
        prog["completed"].append(dest)
    save_json(PROGRESS, prog)
    return 0


def cmd_fail(dest: str, error: str) -> int:
    prog = load_json(PROGRESS, {"completed": [], "failed": [], "media_cache": {}})
    prog.setdefault("failed", []).append({"dest": dest, "error": error})
    save_json(PROGRESS, prog)
    return 0


def cmd_next_batch(n: int) -> int:
    prog = load_json(PROGRESS, {"media_cache": {}})
    cache = prog.get("media_cache", {})
    batch = []
    for job in pending_jobs():
        ref = resolve_ref(job)
        if not ref or ref not in cache:
            continue
        batch.append({**job, "media_id": cache[ref]})
        if len(batch) >= n:
            break
    print(json.dumps(batch, ensure_ascii=False))
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pending")
    sub.add_parser("refs-missing")
    b = sub.add_parser("next-batch")
    b.add_argument("-n", type=int, default=3)
    put = sub.add_parser("put-uploads")
    put.add_argument("file", type=Path)
    c = sub.add_parser("cache-ref")
    c.add_argument("ref")
    c.add_argument("media_id")
    done = sub.add_parser("complete")
    done.add_argument("dest")
    fail = sub.add_parser("fail")
    fail.add_argument("dest")
    fail.add_argument("error")
    args = p.parse_args()
    cmds = {
        "pending": cmd_pending,
        "refs-missing": cmd_refs_missing,
        "put-uploads": lambda: cmd_put_uploads(args.file),
        "cache-ref": lambda: cmd_cache_ref(args.ref, args.media_id),
        "complete": lambda: cmd_complete(args.dest),
        "fail": lambda: cmd_fail(args.dest, args.error),
        "next-batch": lambda: cmd_next_batch(args.n),
    }
    return cmds[args.cmd]()


if __name__ == "__main__":
    raise SystemExit(main())
