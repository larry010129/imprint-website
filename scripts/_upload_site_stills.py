from __future__ import annotations

import base64
import hashlib
import mimetypes
import re
import sys
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parent.parent
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
FOLDERS = ("diamonds", "shop-product", "products")
UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def encode_stem(stem: str) -> str:
    payload = base64.urlsafe_b64encode(stem.encode("utf-8")).decode("ascii").rstrip("=")
    return f"u-{payload}"


def ascii_filename(value: str) -> str:
    raw = value.strip().strip("/")
    if "." in raw and not raw.startswith("."):
        stem, ext = raw.rsplit(".", 1)
        ext = f".{ext.lower()}"
    else:
        stem, ext = raw, ""
    if any(ord(ch) > 127 for ch in stem):
        out = f"{encode_stem(stem)}{ext}"
    else:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-") or hashlib.sha1(
            raw.encode()
        ).hexdigest()[:10]
        out = f"{safe}{ext}"
    if UNSAFE.search(out):
        raise ValueError(f"unsafe key {out!r}")
    return out


def dest_rel(folder: str, rel: str) -> str:
    parts = rel.replace("\\", "/").split("/")
    parts[-1] = ascii_filename(parts[-1])
    return f"{folder}/{'/'.join(parts)}"


def main() -> int:
    env = load_env(ROOT / ".env")
    base = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    bucket = env.get("SUPABASE_STORAGE_BUCKET", "shop-media") or "shop-media"
    if not base or not key:
        print("missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return 1
    images = ROOT / "public" / "images"
    ok = fail = skipped = 0
    print(f"target {base}/storage/v1/object/public/{bucket}/site-images/", flush=True)
    headers_base = {"Authorization": f"Bearer {key}", "apikey": key}
    with httpx.Client(timeout=90.0, follow_redirects=True) as client:
        for folder in FOLDERS:
            base_dir = images / folder
            files = [
                p
                for p in sorted(base_dir.rglob("*"))
                if p.is_file() and p.suffix.lower() in IMAGE_EXTS
            ]
            print(f"-- {folder}: {len(files)} files", flush=True)
            for path in files:
                rel = path.relative_to(base_dir).as_posix()
                dest = dest_rel(folder, rel)
                object_path = f"site-images/{dest}"
                encoded = "/".join(quote(part, safe="") for part in object_path.split("/") if part)
                public = f"{base}/storage/v1/object/public/{bucket}/{object_path}"
                try:
                    head = client.head(public)
                    if head.status_code == 200:
                        skipped += 1
                        if skipped % 25 == 0:
                            print(f"SKIP {skipped}", flush=True)
                        continue
                    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                    if path.suffix.lower() == ".webp":
                        mime = "image/webp"
                    api = f"{base}/storage/v1/object/{bucket}/{encoded}"
                    resp = client.post(
                        api,
                        content=path.read_bytes(),
                        headers={**headers_base, "Content-Type": mime, "x-upsert": "true"},
                    )
                    if resp.status_code not in (200, 201):
                        fail += 1
                        print(f"FAIL {rel} {resp.status_code} {resp.text[:160]}", flush=True)
                        continue
                    ok += 1
                    print(f"OK {rel}", flush=True)
                except httpx.HTTPError as exc:
                    fail += 1
                    print(f"FAIL {rel}: {exc}", flush=True)
    print(f"done ok={ok} skipped={skipped} fail={fail}", flush=True)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
