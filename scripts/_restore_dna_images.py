"""One-off restore: 4 missing shop-media objects referenced by the CMS.

Converts local sources to WebP (q=85, method=6, alpha preserved) and uploads
to Supabase Storage bucket `shop-media` under the exact referenced keys, then
verifies each public URL returns 200 + image/webp.
"""

from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

JOBS = [
    (
        ROOT / "public/images/dna-process/what-is-dna-diamond-hero.png",
        "page-images/dna-diamond/what-is-dna-diamond-hero.webp",
    ),
    (
        ROOT / "public/images/dna-process/collect-bottle.png",
        "page-images/dna-diamond/collect-bottle.webp",
    ),
    (
        ROOT / "public/images/dna-process/diamond-cutting.png",
        "page-images/dna-diamond/diamond-cutting.webp",
    ),
    (
        ROOT / "public/images/products/ring-classic-solitaire-1.jpg",
        "page-images/dna-diamond/ring-classic-solitaire-1.webp",
    ),
]


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def main() -> int:
    env = load_env()
    base = env["SUPABASE_URL"].rstrip("/")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY") or env["SUPABASE_SECRET_KEY"]
    bucket = env.get("SUPABASE_STORAGE_BUCKET", "shop-media")

    failures = 0
    for src, obj_key in JOBS:
        if not src.is_file():
            print(f"[FAIL] missing source: {src}")
            failures += 1
            continue

        with Image.open(src) as im:
            im.load()
            src_size = src.stat().st_size
            print(
                f"[src ] {src.name}: {src_size} bytes, "
                f"{im.size[0]}x{im.size[1]}, mode={im.mode}, format={im.format}"
            )
            buf = io.BytesIO()
            im.save(buf, format="WEBP", quality=85, method=6)
        data = buf.getvalue()
        print(f"[webp] {obj_key}: {len(data)} bytes")

        upload_url = f"{base}/storage/v1/object/{bucket}/{obj_key}"
        headers = {
            "Authorization": f"Bearer {key}",
            "apikey": key,
            "Content-Type": "image/webp",
            "x-upsert": "true",
        }
        resp = requests.post(upload_url, data=data, headers=headers, timeout=60)
        if resp.status_code not in (200, 201):
            print(f"[FAIL] upload {obj_key}: HTTP {resp.status_code} {resp.text[:300]}")
            failures += 1
            continue
        print(f"[upld] {obj_key}: HTTP {resp.status_code}")

        public_url = f"{base}/storage/v1/object/public/{bucket}/{obj_key}"
        status, ctype = 0, ""
        for attempt in (1, 2):
            check = requests.get(public_url, timeout=30)
            status = check.status_code
            ctype = check.headers.get("Content-Type", "")
            if status == 200:
                break
            if attempt == 1:
                time.sleep(5)
        ok = status == 200 and "image/webp" in ctype
        print(
            f"[{'ok  ' if ok else 'FAIL'}] GET public: HTTP {status}, "
            f"Content-Type={ctype}\n      {public_url}"
        )
        if not ok:
            failures += 1

    print(f"\nDone. failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
