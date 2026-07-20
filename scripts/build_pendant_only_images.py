"""Crop pendant-only and chain-only PNGs from full-necklace shop-product renders.

Outputs (same folder as source):
  項墜A_silver_blue_only.png  — pendant close-up
  項墜A_silver_chain.png      — chain strip (white-diamond masters only)
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / "public" / "images" / "shop-product"
# ponytail: fixed crop ratios — re-tune if source art layout changes
PENDANT_CROP = (0.22, 0.48, 0.78, 0.92)
CHAIN_CROP = (0.08, 0.0, 0.92, 0.52)
BASE_METAL = re.compile(r"^項墜[ABC]_(silver|gold|rose)$")


def crop_box(im: Image.Image, ratios: tuple[float, float, float, float]) -> Image.Image:
    w, h = im.size
    box = (
        int(w * ratios[0]),
        int(h * ratios[1]),
        int(w * ratios[2]),
        int(h * ratios[3]),
    )
    return im.crop(box)


def main() -> None:
    pendant_n = chain_n = 0
    for src in sorted(ROOT.rglob("項墜*.png")):
        stem = src.stem
        if stem.endswith("_only") or stem.endswith("_chain"):
            continue
        only_dest = src.with_name(f"{stem}_only{src.suffix}")
        crop_box(Image.open(src), PENDANT_CROP).save(only_dest, optimize=True)
        pendant_n += 1
        if BASE_METAL.match(stem):
            chain_dest = src.with_name(f"{stem}_chain{src.suffix}")
            crop_box(Image.open(src), CHAIN_CROP).save(chain_dest, optimize=True)
            chain_n += 1
    print(f"done: {pendant_n} pendant-only, {chain_n} chain-only")


if __name__ == "__main__":
    main()
