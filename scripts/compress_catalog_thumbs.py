# -*- coding: utf-8 -*-
"""Calculator catalog thumbs: WebP siblings + display-size JPEG recompress.

- diamonds/colors/catalog-cluster.png -> .webp sibling (<100KB), PNG kept as fallback
- shop-product/thumbs/{cat}/{letter}.jpg -> resize to <=600px long edge, <60KB
- thumbs/{cat}/A.jpg also gains an A.webp sibling (categoryThumb prefers .webp)
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image

IMAGES_ROOT = Path(__file__).resolve().parents[1] / "public" / "images"
THUMBS_ROOT = IMAGES_ROOT / "shop-product" / "thumbs"
CLUSTER_PNG = IMAGES_ROOT / "diamonds" / "colors" / "catalog-cluster.png"

MAX_EDGE = 600
THUMB_MAX_BYTES = 60 * 1024
CLUSTER_MAX_BYTES = 100 * 1024


def _resized(im: Image.Image, max_edge: int = MAX_EDGE) -> Image.Image:
    w, h = im.size
    if max(w, h) <= max_edge:
        return im
    scale = max_edge / max(w, h)
    return im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)


def _jpeg_bytes(im: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="JPEG", optimize=True, progressive=True, quality=quality)
    return buf.getvalue()


def _webp_bytes(im: Image.Image, quality: int) -> bytes:
    img = im if im.mode in ("RGB", "RGBA") else im.convert("RGBA")
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, method=6)
    return buf.getvalue()


def _fit(save, im: Image.Image, max_bytes: int, qualities: tuple[int, ...]) -> bytes:
    best: bytes | None = None
    for q in qualities:
        data = save(im, q)
        if len(data) <= max_bytes:
            best = data
            break
        if best is None or len(data) < len(best):
            best = data
    if best is None or len(best) > max_bytes:
        raise RuntimeError(f"cannot fit under {max_bytes} bytes")
    return best


def process_cluster() -> dict:
    before = CLUSTER_PNG.stat().st_size
    im = Image.open(CLUSTER_PNG)
    im.load()
    data = _fit(_webp_bytes, _resized(im), CLUSTER_MAX_BYTES, (82, 75, 68, 60))
    out = CLUSTER_PNG.with_suffix(".webp")
    out.write_bytes(data)
    return {"file": out, "before": before, "after": len(data)}


def process_thumb(path: Path) -> dict:
    before = path.stat().st_size
    im = Image.open(path)
    im.load()
    im = _resized(im)
    results: dict = {"file": path, "before": before}

    if before > THUMB_MAX_BYTES or max(im.size) >= MAX_EDGE:
        data = _fit(_jpeg_bytes, im, THUMB_MAX_BYTES, (82, 75, 68, 60, 52))
        path.write_bytes(data)
        results["after"] = len(data)
    else:
        results["after"] = before

    if path.stem.upper() == "A":
        webp = _fit(_webp_bytes, im, THUMB_MAX_BYTES, (82, 75, 68, 60, 52))
        out = path.with_suffix(".webp")
        out.write_bytes(webp)
        results["webp"] = len(webp)

    return results


def main() -> int:
    done: list[dict] = [process_cluster()]
    errors: list[dict] = []
    for f in sorted(THUMBS_ROOT.rglob("*.jpg")):
        try:
            done.append(process_thumb(f))
        except Exception as e:  # noqa: BLE001 - report every file, fail at end
            errors.append({"file": f, "error": str(e)})

    saved = sum(r["before"] - r["after"] for r in done)
    print(f"processed={len(done)} errors={len(errors)} saved_kb={saved / 1024:.0f}")
    for r in done:
        line = f"  {r['before'] // 1024}KB -> {r['after'] // 1024}KB {Path(r['file']).name}"
        if r.get("webp"):
            line += f" (+webp {r['webp'] // 1024}KB)"
        print(line)
    for e in errors:
        print(f"  ERROR {e['file']}: {e['error']}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
    raise SystemExit(main())
