# -*- coding: utf-8 -*-
"""Download a generated PNG into the shop-product pendant combo path."""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

from compress_shop_images import compress_path

ROOT = Path(__file__).resolve().parents[1] / "public" / "images" / "shop-product"
ZH = "項墜"
METAL_DIR = {"white": "silver", "yellow": "gold", "rose": "rose_gold"}
METAL_SUFFIX = {"white": "silver", "yellow": "gold", "rose": "rose"}


def combo_path(style: str, pendant: str, chain: str, diamond: str) -> Path:
    ps, cs = METAL_SUFFIX[pendant], METAL_SUFFIX[chain]
    d = "" if diamond == "white" else f"_{diamond}"
    name = f"{ZH}{style}_{ps}{d}.png" if pendant == chain else f"{ZH}{style}_{ps}_chain_{cs}{d}.png"
    return ROOT / METAL_DIR[pendant] / name


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--style", required=True, choices=["A", "B", "C"])
    p.add_argument("--pendant", required=True, choices=["white", "yellow", "rose"])
    p.add_argument("--chain", required=True, choices=["white", "yellow", "rose"])
    p.add_argument("--diamond", required=True, choices=["white", "blue", "yellow", "pink"])
    args = p.parse_args()
    dest = combo_path(args.style, args.pendant, args.chain, args.diamond)
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(args.url, dest)
    compress_path(dest)
    print(dest.relative_to(ROOT.parent.parent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
