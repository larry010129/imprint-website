"""Convert uploaded images to WebP compressed to ≤500KB."""

from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath

from PIL import Image

MAX_OUTPUT_BYTES = 500 * 1024
_START_QUALITY = 88
_QUALITY_FLOOR = 40
_QUALITY_STEP = 8
_MIN_LONG_EDGE = 640
_RESIZE_FACTOR = 0.84
# CMS/hero images render at most ~852px wide on screen; cap the source long
# edge well above that (2x for retina) instead of only capping byte size.
# Without this, an already-small-enough-in-bytes WebP (e.g. a photo saved at
# 1867x1165, ~90KB) passed straight through untouched — oversized dimensions,
# wasted download/decode cost — since the old gate only checked file size.
_MAX_UPLOAD_LONG_EDGE = 1800
_OVERSIZE_MSG = "圖片壓縮後仍超過 500KB，請換較小的圖"


class ImageConvertError(ValueError):
    """Image could not be converted or compressed within the size limit."""


def ensure_webp(data: bytes, filename: str, ext: str) -> tuple[bytes, str, str]:
    """Return WebP bytes, `.webp` filename, and `.webp` ext (≤500KB, ≤1800px long edge)."""
    if not data:
        raise ImageConvertError("圖片資料為空")
    name_webp = _webp_filename(filename)
    if _is_webp_passthrough(data, ext):
        return data, name_webp, ".webp"
    image = _decode_image(data)
    if max(image.size) > _MAX_UPLOAD_LONG_EDGE:
        image = _resize_long_edge(image, _MAX_UPLOAD_LONG_EDGE)
    out = _compress_to_limit(image)
    return out, name_webp, ".webp"


def _webp_filename(filename: str) -> str:
    path = PurePosixPath(filename.replace("\\", "/"))
    stem = path.stem or "image"
    parent = path.parent.as_posix()
    if parent in ("", "."):
        return f"{stem}.webp"
    return f"{parent}/{stem}.webp"


def _is_webp_passthrough(data: bytes, ext: str) -> bool:
    if ext.lower() != ".webp" or len(data) > MAX_OUTPUT_BYTES:
        return False
    try:
        with Image.open(BytesIO(data)) as probe:
            return max(probe.size) <= _MAX_UPLOAD_LONG_EDGE
    except Exception:
        return False


def _decode_image(data: bytes) -> Image.Image:
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except Exception as exc:
        raise ImageConvertError("無法讀取圖片") from exc
    return _normalize_mode(image)


def _normalize_mode(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        return image.convert("RGBA")
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _compress_to_limit(image: Image.Image) -> bytes:
    quality = _START_QUALITY
    current = image
    while True:
        payload = _encode_webp(current, quality)
        if len(payload) <= MAX_OUTPUT_BYTES:
            return payload
        if quality - _QUALITY_STEP >= _QUALITY_FLOOR:
            quality -= _QUALITY_STEP
            continue
        if quality > _QUALITY_FLOOR:
            quality = _QUALITY_FLOOR
            continue
        long_edge = max(current.size)
        if long_edge <= _MIN_LONG_EDGE:
            raise ImageConvertError(_OVERSIZE_MSG)
        next_edge = max(_MIN_LONG_EDGE, int(long_edge * _RESIZE_FACTOR))
        if next_edge >= long_edge:
            raise ImageConvertError(_OVERSIZE_MSG)
        current = _resize_long_edge(current, next_edge)
        quality = _START_QUALITY


def _encode_webp(image: Image.Image, quality: int) -> bytes:
    buf = BytesIO()
    image.save(buf, format="WEBP", quality=quality, method=4)
    return buf.getvalue()


def _resize_long_edge(image: Image.Image, long_edge: int) -> Image.Image:
    width, height = image.size
    if width >= height:
        new_w = long_edge
        new_h = max(1, int(round(height * (long_edge / width))))
    else:
        new_h = long_edge
        new_w = max(1, int(round(width * (long_edge / height))))
    return image.resize((new_w, new_h), Image.Resampling.LANCZOS)
