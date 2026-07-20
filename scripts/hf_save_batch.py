# -*- coding: utf-8 -*-
"""Save multiple generated combo PNGs from result records."""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv" / "Scripts" / "python.exe"
SAVE = ROOT / "scripts" / "save_pendant_combo.py"
MARK = ROOT / "scripts" / "hf_mark_done.py"


def main() -> int:
    records = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for r in records:
        subprocess.check_call(
            [
                str(PY),
                str(SAVE),
                "--url",
                r["url"],
                "--style",
                r["style"],
                "--pendant",
                r["pendant"],
                "--chain",
                r["chain"],
                "--diamond",
                r["diamond"],
            ]
        )
        if "dest" in r:
            media = json.dumps(r.get("media_updates", {}))
            subprocess.check_call([str(PY), str(MARK), r["dest"], media])
    print("saved", len(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
