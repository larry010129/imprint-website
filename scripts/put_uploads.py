# -*- coding: utf-8 -*-
"""PUT local files to Higgsfield presigned upload URLs."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    batch_path = Path(sys.argv[1])
    data = json.loads(batch_path.read_text(encoding="utf-8"))
    ok = 0
    for item in data["uploads"]:
        src = ROOT / item["local"]
        url = item["upload_url"]
        req = urllib.request.Request(url, data=src.read_bytes(), method="PUT")
        req.add_header("Content-Type", "image/png")
        with urllib.request.urlopen(req) as resp:
            code = resp.status
        print(f"PUT {item['local']} -> {code}")
        ok += 1
    print(f"uploaded {ok}/{len(data['uploads'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
