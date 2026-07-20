# -*- coding: utf-8 -*-
"""Record completed pendant combo saves into progress.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROGRESS = Path(__file__).resolve().parents[1] / "scripts" / "pendant-combo-progress.json"


def main() -> int:
    dest = sys.argv[1]
    media_updates = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    data = json.loads(PROGRESS.read_text(encoding="utf-8")) if PROGRESS.exists() else {
        "completed": [],
        "failed": [],
        "media_cache": {},
    }
    if dest not in data["completed"]:
        data["completed"].append(dest)
    cache = data.setdefault("media_cache", {})
    cache.update(media_updates)
    PROGRESS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ok", len(data["completed"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
