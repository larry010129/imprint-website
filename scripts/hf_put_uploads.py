# -*- coding: utf-8__
"""PUT staged PNGs to Higgsfield presigned URLs."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

UPLOAD = Path(__file__).resolve().parents[1] / "scripts" / "_hf_upload"


def put_file(path: Path, url: str) -> int:
    data = path.read_bytes()
    req = urllib.request.Request(url, data=data, method="PUT", headers={"Content-Type": "image/png"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.status


def main() -> int:
    mapping = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for item in mapping:
        code = put_file(UPLOAD / item["file"], item["url"])
        print(item["file"], code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
