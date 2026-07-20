# -*- coding: utf-8 -*-
"""Compose metal+diamond PNG from white-metal base + silver fancy color reference.

ponytail: offline fallback when Higgsfield unavailable; upgrade = regenerate via
diamond-variant-batches.json + nano_banana_pro reference edit.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SHOP = ROOT / "public" / "images" / "shop-product"


def compose(base_path: Path, ref_white_path: Path, ref_fancy_path: Path, out_path: Path) -> None:
    base_img = Image.open(base_path).convert("RGB")
    size = base_img.size

    base = np.array(base_img, dtype=np.float32)
    white = np.array(Image.open(ref_white_path).convert("RGB").resize(size, Image.LANCZOS), dtype=np.float32)
    fancy = np.array(Image.open(ref_fancy_path).convert("RGB").resize(size, Image.LANCZOS), dtype=np.float32)

    delta = fancy - white
    diff = np.abs(delta).sum(axis=2)
    mask = (diff > 18).astype(np.float32)
    mask = np.array(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)), dtype=np.float32) / 255.0

    result = base.copy()
    for channel in range(3):
        tinted = np.clip(base[:, :, channel] + delta[:, :, channel], 0, 255)
        result[:, :, channel] = base[:, :, channel] * (1.0 - mask) + tinted * mask

    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(result.astype(np.uint8)).save(out_path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compose fancy diamond variant onto a metal base PNG.")
    parser.add_argument("base", type=Path, help="Target metal PNG (e.g. rose_gold/耳飾A_rose.png)")
    parser.add_argument("ref_white", type=Path, help="Silver white-diamond reference")
    parser.add_argument("ref_fancy", type=Path, help="Silver fancy-diamond reference")
    parser.add_argument("out", type=Path, help="Output PNG path")
    args = parser.parse_args()
    compose(args.base, args.ref_white, args.ref_fancy, args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
