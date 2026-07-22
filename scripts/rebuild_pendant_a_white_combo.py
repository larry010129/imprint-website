"""Improve style-A white mixed-metal combos: paste white diamond from silver.png onto pink combo base."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1] / "public" / "images" / "shop-product" / "silver"


def diamond_mask_from_pink(im: Image.Image) -> Image.Image:
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    mask = Image.new("L", (w, h), 0)
    mp = mask.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if r > 245 and g > 245 and b > 245:
                continue
            mx, mn = max(r, g, b), min(r, g, b)
            if mx == 0:
                continue
            sat = (mx - mn) / mx
            if sat < 0.15 or r < g + 6 or r < 110:
                continue
            if g > r - 12 and b < g - 25:
                continue
            mp[x, y] = 255
    mask = mask.filter(ImageFilter.MinFilter(3))
    mask = mask.filter(ImageFilter.MaxFilter(7))
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    return mask


def paste_white_diamond(base_pink: Image.Image, white_full: Image.Image) -> Image.Image:
    base = base_pink.convert("RGBA").resize((1024, 1024), Image.Resampling.LANCZOS)
    donor = white_full.convert("RGBA").resize((1024, 1024), Image.Resampling.LANCZOS)
    mask = diamond_mask_from_pink(base_pink.resize((1024, 1024), Image.Resampling.LANCZOS))
    # Soften and expand a bit so prong inner edges stay clean
    mask = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.5))
    out = base.copy()
    out.paste(donor, (0, 0), mask)
    return out.convert("RGB")


def main() -> None:
    white = Image.open(ROOT / "項墜A_silver.png")
    for chain in ("rose", "gold"):
        pink = Image.open(ROOT / f"項墜A_silver_chain_{chain}_pink.png")
        out = paste_white_diamond(pink, white)
        dest = ROOT / f"項墜A_silver_chain_{chain}.png"
        out.save(dest, "PNG", optimize=True)
        print(f"OK {dest.name}")


if __name__ == "__main__":
    main()
