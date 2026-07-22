# -*- coding: utf-8 -*-
"""Compress shop-product PNG/JPEG files to <=700KB (Pillow; no ImageMagick)."""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / "public" / "images" / "shop-product"
IMAGES_ROOT = Path(__file__).resolve().parents[1] / "public" / "images"
MAX_BYTES = 700 * 1024
# ponytail: binary-search PNG resize to fit byte cap; upgrade path = WebP if quality complaints
EXT = {".png", ".jpg", ".jpeg", ".webp"}


def _save_png(im: Image.Image, scale: float) -> bytes:
    img = im
    if scale < 1.0:
        w, h = im.size
        img = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True, compress_level=9)
    return buf.getvalue()


def _save_jpeg(im: Image.Image, scale: float, quality: int) -> bytes:
    img = im.convert("RGB")
    if scale < 1.0:
        w, h = img.size
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", optimize=True, quality=quality)
    return buf.getvalue()


def _save_webp(im: Image.Image, scale: float, quality: int) -> bytes:
    img = im.convert("RGBA") if im.mode not in ("RGB", "RGBA") else im
    if scale < 1.0:
        w, h = img.size
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, method=6)
    return buf.getvalue()


def compress_file(path: Path, max_bytes: int = MAX_BYTES) -> dict:
    before = path.stat().st_size
    if before <= max_bytes:
        return {"file": str(path), "skipped": True, "before": before, "after": before}

    im = Image.open(path)
    im.load()
    suffix = path.suffix.lower()

    if suffix == ".png":
        data = _save_png(im, 1.0)
        if len(data) <= max_bytes:
            path.write_bytes(data)
            return {"file": str(path), "before": before, "after": len(data)}

        lo, hi = 0.5, 1.0
        best: bytes | None = None
        while hi - lo > 0.005:
            mid = (lo + hi) / 2
            data = _save_png(im, mid)
            if len(data) <= max_bytes:
                best = data
                lo = mid
            else:
                hi = mid
        if best is None:
            best = _save_png(im, 0.5)
        if len(best) > max_bytes:
            raise RuntimeError(f"cannot compress {path} under {max_bytes} bytes")
        path.write_bytes(best)
        return {"file": str(path), "before": before, "after": len(best)}

    if suffix == ".webp":
        best = None
        for quality in (82, 75, 68, 60, 52):
            lo, hi = 0.5, 1.0
            best_q: bytes | None = None
            while hi - lo > 0.005:
                mid = (lo + hi) / 2
                data = _save_webp(im, mid, quality)
                if len(data) <= max_bytes:
                    best_q = data
                    lo = mid
                else:
                    hi = mid
            if best_q and (best is None or len(best_q) > len(best)):
                best = best_q
            if best and len(best) <= max_bytes:
                break
        if best is None or len(best) > max_bytes:
            raise RuntimeError(f"cannot compress {path} under {max_bytes} bytes")
        path.write_bytes(best)
        return {"file": str(path), "before": before, "after": len(best)}

    best: bytes | None = None
    for quality in (85, 78, 72, 65, 58):
        lo, hi = 0.5, 1.0
        best_q: bytes | None = None
        while hi - lo > 0.005:
            mid = (lo + hi) / 2
            data = _save_jpeg(im, mid, quality)
            if len(data) <= max_bytes:
                best_q = data
                lo = mid
            else:
                hi = mid
        if best_q and (best is None or len(best_q) > len(best)):
            best = best_q
        if best and len(best) <= max_bytes:
            break

    if best is None or len(best) > max_bytes:
        raise RuntimeError(f"cannot compress {path} under {max_bytes} bytes")
    path.write_bytes(best)
    return {"file": str(path), "before": before, "after": len(best)}


def compress_path(path: Path, max_bytes: int = MAX_BYTES) -> dict:
    """Public entry for save_pendant_combo and other scripts."""
    return compress_file(path, max_bytes)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--max-kb", type=int, default=700)
    p.add_argument("--root", type=Path, default=IMAGES_ROOT)
    args = p.parse_args()
    max_bytes = args.max_kb * 1024

    files = sorted(f for f in args.root.rglob("*") if f.suffix.lower() in EXT)
    done: list[dict] = []
    errors: list[dict] = []
    for f in files:
        try:
            r = compress_file(f, max_bytes)
            if not r.get("skipped"):
                done.append(r)
        except Exception as e:
            errors.append({"file": str(f), "error": str(e)})

    saved = sum(r["before"] - r["after"] for r in done)
    print(
        f"scanned={len(files)} compressed={len(done)} errors={len(errors)} "
        f"saved_mb={saved / 1024 / 1024:.2f}"
    )
    for r in done:
        print(f"  {r['before'] // 1024}KB -> {r['after'] // 1024}KB {Path(r['file']).name}")
    for e in errors:
        print(f"  ERROR {e['file']}: {e['error']}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
