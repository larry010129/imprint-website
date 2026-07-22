"""Paste colorless diamond from white+white master onto pink mixed-metal combos.

For each style A/B/C × chain rose/gold:
  base  = 項墜{S}_silver_chain_{chain}_pink.png  (correct mixed-metal + framing)
  donor = 項墜{S}_silver.png                     (white diamond)
  out   = 項墜{S}_silver_chain_{chain}.png
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1] / "public" / "images" / "shop-product" / "silver"
BAK = ROOT / "_bak_white_combo"


def gem_mask(im: Image.Image) -> Image.Image:
    """Mask saturated pink/magenta gem (not rose-gold chain)."""
    rgb = im.convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)
    w, h = rgb.size
    px = rgb.load()
    mask = Image.new("L", (w, h), 0)
    mp = mask.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if r > 248 and g > 248 and b > 248:
                continue
            mx, mn = max(r, g, b), min(r, g, b)
            if mx < 90:
                continue
            sat = (mx - mn) / mx if mx else 0
            # Pink gem: red-led, saturated; exclude yellow gold (r≈g)
            if sat < 0.12:
                continue
            if r < g + 5:
                continue
            if g >= r - 10 and (r - b) > 40 and (g - b) > 30:
                continue  # yellow gold
            if r >= 100 and r >= g + 5:
                mp[x, y] = 255
    mask = mask.filter(ImageFilter.MinFilter(3))
    mask = mask.filter(ImageFilter.MaxFilter(7))
    # Keep largest blob only
    mp = mask.load()
    seen = [[False] * w for _ in range(h)]
    best_cells: list[tuple[int, int]] = []
    for y0 in range(h):
        for x0 in range(w):
            if mp[x0, y0] < 128 or seen[y0][x0]:
                continue
            stack = [(x0, y0)]
            seen[y0][x0] = True
            cells: list[tuple[int, int]] = []
            while stack:
                x, y = stack.pop()
                cells.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and mp[nx, ny] >= 128:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if len(cells) > len(best_cells):
                best_cells = cells
    out = Image.new("L", (w, h), 0)
    op = out.load()
    for x, y in best_cells:
        op[x, y] = 255
    out = out.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.6))
    return out


def build(style: str, chain: str) -> None:
    pink_path = ROOT / f"項墜{style}_silver_chain_{chain}_pink.png"
    white_path = ROOT / f"項墜{style}_silver.png"
    dest = ROOT / f"項墜{style}_silver_chain_{chain}.png"
    if not pink_path.exists() or not white_path.exists():
        print(f"SKIP {style}/{chain}")
        return
    BAK.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        bak = BAK / f"{dest.stem}__pre_paste{dest.suffix}"
        if not bak.exists():
            shutil.copy2(dest, bak)
    base = Image.open(pink_path).convert("RGBA").resize((1024, 1024), Image.Resampling.LANCZOS)
    donor = Image.open(white_path).convert("RGBA").resize((1024, 1024), Image.Resampling.LANCZOS)
    mask = gem_mask(Image.open(pink_path))
    out = base.copy()
    out.paste(donor, (0, 0), mask)
    out.convert("RGB").save(dest, "PNG", optimize=True)
    print(f"OK {dest.name}")


def main() -> None:
    for style in ("A", "B", "C"):
        for chain in ("rose", "gold"):
            build(style, chain)


if __name__ == "__main__":
    main()
