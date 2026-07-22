"""Build white-diamond mixed-metal combos from white+white masters by recoloring the chain.

Keeps the exact catalog framing (incl. IMPRINT logo) from 項墜X_silver.png,
only shifts chain metal to rose or yellow gold.
"""

from __future__ import annotations

import colorsys
import shutil
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1] / "public" / "images" / "shop-product" / "silver"
BAK = ROOT / "_bak_white_combo"


def is_bg(r: int, g: int, b: int) -> bool:
    return r >= 248 and g >= 248 and b >= 248


def is_silver_metal(r: int, g: int, b: int) -> bool:
    if is_bg(r, g, b):
        return False
    mx, mn = max(r, g, b), min(r, g, b)
    if mx < 55:
        return False
    # Neutral / cool gray metal (not saturated gem)
    if mx - mn > 28:
        return False
    return True


def chain_mask(im: Image.Image) -> Image.Image:
    """Approximate chain = silver metal in the upper portion of the frame."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    mask = Image.new("L", (w, h), 0)
    mp = mask.load()
    # Chain lives mostly in top ~55%; pendant stone sits lower-center
    y_max = int(h * 0.58)
    for y in range(0, y_max):
        for x in range(w):
            r, g, b = px[x, y]
            if not is_silver_metal(r, g, b):
                continue
            # Prefer outer V arms (left/right), still include center bail area lightly
            mp[x, y] = 255
    # Remove compact pendant-stone neighborhood (center lower in chain band)
    cx, cy = w // 2, int(h * 0.42)
    rad = int(min(w, h) * 0.09)
    r2 = rad * rad
    for y in range(max(0, cy - rad), min(h, cy + rad + 1)):
        for x in range(max(0, cx - rad), min(w, cx + rad + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                mp[x, y] = 0
    mask = mask.filter(ImageFilter.MinFilter(3))
    mask = mask.filter(ImageFilter.MaxFilter(3))
    mask = mask.filter(ImageFilter.GaussianBlur(0.8))
    return mask


def tint_pixel(r: int, g: int, b: int, mode: str) -> tuple[int, int, int]:
    """Preserve luminance, shift hue toward rose or yellow gold."""
    # Relative luminance
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    if mode == "rose":
        h = 0.02  # warm pink-rose
        s = min(1.0, max(0.22, s + 0.35))
    else:  # gold / yellow
        h = 0.12
        s = min(1.0, max(0.28, s + 0.40))
    # Keep value tied to original brightness so highlights survive
    v = max(v, lum)
    nr, ng, nb = colorsys.hsv_to_rgb(h, s, min(1.0, v * 1.02))
    return int(nr * 255), int(ng * 255), int(nb * 255)


def recolor_chain(src: Image.Image, mode: str) -> Image.Image:
    out = src.convert("RGB")
    mask = chain_mask(out)
    px = out.load()
    mp = mask.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            a = mp[x, y]
            if a < 10:
                continue
            r, g, b = px[x, y]
            tr, tg, tb = tint_pixel(r, g, b, mode)
            t = a / 255.0
            px[x, y] = (
                int(r + (tr - r) * t),
                int(g + (tg - g) * t),
                int(b + (tb - b) * t),
            )
    return out


def main() -> None:
    BAK.mkdir(parents=True, exist_ok=True)
    for style in ("A", "B", "C"):
        master = ROOT / f"項墜{style}_silver.png"
        if not master.exists():
            print(f"SKIP {master.name}")
            continue
        src = Image.open(master)
        for chain, mode in (("rose", "rose"), ("gold", "gold")):
            dest = ROOT / f"項墜{style}_silver_chain_{chain}.png"
            if dest.exists():
                bak = BAK / f"{dest.stem}__from_master{dest.suffix}"
                if not bak.exists():
                    shutil.copy2(dest, bak)
            out = recolor_chain(src, mode)
            out.save(dest, "PNG", optimize=True)
            print(f"OK {dest.name} from {master.name}")


if __name__ == "__main__":
    main()
