# -*- coding: utf-8 -*-
"""Build PUT batch JSON from upload meta + MCP media_ids map."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    meta = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    ids = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    uploads = []
    for ref, upload_url, media_id in zip(meta["refs"], ids["urls"], ids["media_ids"]):
        uploads.append(
            {
                "local": str(ROOT / "public" / ref).replace("\\", "/"),
                "ref": ref,
                "media_id": media_id,
                "upload_url": upload_url,
            }
        )
    out = Path(sys.argv[3])
    out.write_text(json.dumps({"uploads": uploads}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(uploads)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
