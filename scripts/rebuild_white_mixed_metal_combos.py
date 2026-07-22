"""Rebuild white-diamond mixed-metal pendant combos from known-good pink combos.

Pink-diamond cross-metal PNGs have correct full-necklace framing + rose/gold chains.
White-diamond versions were wrong / looked like 項墜-only. This script:
  1. Backs up current white combo
  2. Takes *_chain_{rose|gold}_pink.png
  3. Recolors only the pink gemstone blob → colorless white diamond
  4. Writes *_chain_{rose|gold}.png
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1] / "public" / "images" / "shop-product" / "silver"
BAK = ROOT / "_bak_white_combo"
STYLES = ("A", "B", "C")
CHAINS = ("rose", "gold")


def is_pink_gem(r: int, g: int, b: int) -> bool:
    """True for pink/magenta diamond facets (not rose-gold metal)."""
    # Skip near-white / near-black
    if r > 245 and g > 245 and b > 245:
        return False
    if r < 40 and g < 40 and b < 40:
        return False
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx == 0:
        return False
    sat = (mx - mn) / mx
    # Pink gem: red-dominant, noticeable saturation, not yellow-gold (g close to r)
    if sat < 0.18:
        return False
    if r < g + 8:
        return False
    if r < b + 5:
        return False
    # Rose gold metal is warmer/duller; gems are brighter pink
    if r < 120:
        return False
    # Exclude yellow-ish gold (r≈g >> b)
    if g > r - 15 and b < g - 30:
        return False
    return True


def pink_mask(im: Image.Image) -> Image.Image:
    """Binary mask of pink gem pixels, cleaned so thin chain links drop out."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    mask = Image.new("L", (w, h), 0)
    mp = mask.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if is_pink_gem(r, g, b):
                mp[x, y] = 255
    # Drop thin structures (chain); keep compact stone
    mask = mask.filter(ImageFilter.MinFilter(3))
    mask = mask.filter(ImageFilter.MaxFilter(5))
    mask = mask.filter(ImageFilter.MaxFilter(5))
    mask = mask.filter(ImageFilter.MinFilter(3))
    return mask


def largest_blob_center(mask: Image.Image) -> tuple[int, int, int] | None:
    """Return (cx, cy, area) of largest connected white blob (4-connected)."""
    w, h = mask.size
    mp = mask.load()
    seen = [[False] * w for _ in range(h)]
    best = None
    best_area = 0
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
            area = len(cells)
            if area > best_area:
                best_area = area
                sx = sum(c[0] for c in cells)
                sy = sum(c[1] for c in cells)
                best = (sx // area, sy // area, area)
    return best


def recolor_pink_diamond_to_white(src: Image.Image) -> Image.Image:
    """Desaturate / cool the pink gem toward a colorless brilliant look."""
    out = src.convert("RGBA")
    mask = pink_mask(out)
    blob = largest_blob_center(mask)
    if not blob or blob[2] < 80:
        # Fallback: use full pink mask without blob filter
        gem = mask
    else:
        cx, cy, _ = blob
        # Keep only mask pixels near the stone center (exclude stray chain hits)
        w, h = mask.size
        mp = mask.load()
        gem = Image.new("L", (w, h), 0)
        gp = gem.load()
        radius = max(28, int((blob[2] ** 0.5) * 2.2))
        r2 = radius * radius
        for y in range(max(0, cy - radius), min(h, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(w, cx + radius + 1)):
                if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2 and mp[x, y] >= 128:
                    gp[x, y] = 255
        gem = gem.filter(ImageFilter.MaxFilter(3))
        gem = gem.filter(ImageFilter.GaussianBlur(1.2))

    px = out.load()
    gp = gem.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            a = gp[x, y]
            if a < 8:
                continue
            r, g, b, alpha = px[x, y]
            # Desaturate toward cool white / silver facet
            gray = int(0.30 * r + 0.35 * g + 0.35 * b)
            # Lift slightly so it reads as a bright white diamond
            gray = min(255, int(gray * 0.55 + 140 * 0.45))
            # Tiny cool bias
            nr = min(255, gray + 4)
            ng = min(255, gray + 2)
            nb = min(255, gray + 8)
            t = a / 255.0
            px[x, y] = (
                int(r + (nr - r) * t),
                int(g + (ng - g) * t),
                int(b + (nb - b) * t),
                alpha,
            )
    return out.convert("RGB")


def main() -> None:
    BAK.mkdir(parents=True, exist_ok=True)
    for style in STYLES:
        for chain in CHAINS:
            pink = ROOT / f"項墜{style}_silver_chain_{chain}_pink.png"
            dest = ROOT / f"項墜{style}_silver_chain_{chain}.png"
            if not pink.exists():
                print(f"SKIP missing pink ref: {pink.name}")
                continue
            if dest.exists():
                bak = BAK / dest.name
                if not bak.exists():
                    shutil.copy2(dest, bak)
                    print(f"bak {dest.name}")
            src = Image.open(pink)
            out = recolor_pink_diamond_to_white(src)
            # Match catalog size
            if out.size != (1024, 1024):
                out = out.resize((1024, 1024), Image.Resampling.LANCZOS)
            out.save(dest, "PNG", optimize=True)
            print(f"OK  {dest.name}  from {pink.name}  ({out.size})")


if __name__ == "__main__":
    main()
