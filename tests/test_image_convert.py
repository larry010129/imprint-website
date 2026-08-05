"""Unit tests for app.image_convert.ensure_webp."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image

from app.image_convert import (
    MAX_OUTPUT_BYTES,
    ImageConvertError,
    ensure_webp,
)


def _rgb_bytes(fmt: str, size=(48, 32), color=(20, 40, 200), **save_kw) -> bytes:
    img = Image.new("RGB", size, color)
    buf = BytesIO()
    img.save(buf, format=fmt, **save_kw)
    return buf.getvalue()


def _assert_webp(data: bytes) -> None:
    assert len(data) >= 12
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WEBP"
    with Image.open(BytesIO(data)) as img:
        assert img.format == "WEBP"


def test_png_to_webp():
    png = _rgb_bytes("PNG")
    out, name, ext = ensure_webp(png, "shot.png", ".png")
    assert name == "shot.webp"
    assert ext == ".webp"
    assert len(out) <= MAX_OUTPUT_BYTES
    _assert_webp(out)


def test_jpeg_to_webp():
    jpeg = _rgb_bytes("JPEG", quality=90)
    out, name, ext = ensure_webp(jpeg, "folder/pic.jpg", ".jpg")
    assert name == "folder/pic.webp"
    assert ext == ".webp"
    assert len(out) <= MAX_OUTPUT_BYTES
    _assert_webp(out)


def test_webp_passthrough_when_under_limit():
    webp = _rgb_bytes("WEBP", quality=80)
    assert len(webp) <= MAX_OUTPUT_BYTES
    out, name, ext = ensure_webp(webp, "keep.webp", ".webp")
    assert out == webp
    assert name == "keep.webp"
    assert ext == ".webp"


def test_large_image_compresses_to_limit():
    # Large colorful image that would exceed 500KB as uncompressed PNG.
    img = Image.new("RGB", (2200, 1800))
    pixels = img.load()
    for y in range(0, 1800, 3):
        for x in range(0, 2200, 3):
            pixels[x, y] = ((x * 37) % 256, (y * 53) % 256, (x + y) % 256)
    buf = BytesIO()
    img.save(buf, format="PNG")
    png = buf.getvalue()
    assert len(png) > MAX_OUTPUT_BYTES

    out, name, ext = ensure_webp(png, "huge.png", ".png")
    assert name == "huge.webp"
    assert ext == ".webp"
    assert len(out) <= MAX_OUTPUT_BYTES
    _assert_webp(out)


def test_empty_data_raises():
    with pytest.raises(ImageConvertError, match="\u7a7a"):
        ensure_webp(b"", "x.png", ".png")


def test_bad_bytes_raise():
    with pytest.raises(ImageConvertError):
        ensure_webp(b"not-an-image", "x.png", ".png")


def test_oversize_after_compress_raises():
    png = _rgb_bytes("PNG", size=(64, 64))
    huge = b"x" * (MAX_OUTPUT_BYTES + 1)

    with patch("app.image_convert._encode_webp", return_value=huge):
        with pytest.raises(ImageConvertError, match="500KB"):
            ensure_webp(png, "loud.png", ".png")
