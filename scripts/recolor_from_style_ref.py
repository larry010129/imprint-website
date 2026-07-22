"""Recolor the user gold IMPRINT catalog master into mixed-metal white-diamond combos.

Input:  gold all-metal solitaire shot (IMPRINT logo + full necklace framing)
Outputs:
  silver/項墜A_silver_chain_rose.png  — white-metal pendant + rose-gold chain
  silver/項墜A_silver_chain_gold.png  — white-metal pendant + yellow-gold chain
"""

from __future__ import annotations

import colorsys
import shutil
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SHOP = ROOT / "public" / "images" / "shop-product"
SILVER = SHOP / "silver"
BAK = SILVER / "_bak_white_combo"

# User-attached style reference (gold+gold IMPRINT catalog shot)
REF_CANDIDATES = [
    Path(r"C:\Users\user\.cursor\projects\c-Users-user-Documents-Diamond-web-imprint-website\assets\c__Users_user_AppData_Roaming_Cursor_User_workspaceStorage_0ee20e07382ec2ed82f0d487a033bbcf_images_image-2e4e7d60-324a-4b47-b211-20b63ffdb70c.png"),
    SHOP / "_gen_ref_style.png",
    SHOP / "gold" / "項墜A_gold.png",
]


def find_ref() -> Path:
    for p in REF_CANDIDATES:
        if p.exists():
            return p
    raise SystemExit("no style reference found")


def is_bg(r: int, g: int, b: int) -> bool:
    return r >= 245 and g >= 245 and b >= 245


def is_warm_metal(r: int, g: int, b: int) -> bool:
    """Yellow / rose gold metal (not diamond facets, not logo black)."""
    if is_bg(r, g, b):
        return False
    if max(r, g, b) < 70:
        return False
    mx, mn = max(r, g, b), min(r, g, b)
    if mx - mn < 18:
        return False  # neutral gray / silver already
    # Warm: r high, b low-ish
    if r < 120:
        return False
    if b > r - 10:
        return False
    if g > r + 15:
        return False
    return True


def is_diamondish(r: int, g: int, b: int) -> bool:
    """Bright near-neutral facets."""
    if is_bg(r, g, b):
        return False
    mx, mn = max(r, g, b), min(r, g, b)
    if mx < 140:
        return False
    return (mx - mn) <= 35 and mx >= 160


def to_silver(r: int, g: int, b: int) -> tuple[int, int, int]:
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    # Cool silver with slight lift
    v = min(255, int(lum * 0.92 + 28))
    return min(255, v + 2), min(255, v + 1), min(255, v + 6)


def to_rose(r: int, g: int, b: int) -> tuple[int, int, int]:
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    # Preserve highlights
    h, s, v = 0.025, 0.42, max(0.35, min(1.0, lum * 1.05 + 0.08))
    nr, ng, nb = colorsys.hsv_to_rgb(h, s, v)
    return int(nr * 255), int(ng * 255), int(nb * 255)


def to_yellow_gold(r: int, g: int, b: int) -> tuple[int, int, int]:
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    h, s, v = 0.12, 0.48, max(0.35, min(1.0, lum * 1.05 + 0.06))
    nr, ng, nb = colorsys.hsv_to_rgb(h, s, v)
    return int(nr * 255), int(ng * 255), int(nb * 255)


def build_masks(im: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Return (pendant_metal_mask, chain_metal_mask) as L images."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    pendant = Image.new("L", (w, h), 0)
    chain = Image.new("L", (w, h), 0)
    pp, cp = pendant.load(), chain.load()

    # Pendant sits lower-center; chain is the V above
    # Soft vertical split around ~52% height with radial pendant core
    cy_pendant = int(h * 0.62)
    cx = w // 2

    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if not is_warm_metal(r, g, b):
                continue
            if is_diamondish(r, g, b):
                continue
            # Distance from pendant center
            dx, dy = x - cx, y - cy_pendant
            dist2 = dx * dx + dy * dy
            # Pendant setting / bail neighborhood
            in_pendant = dist2 < (int(min(w, h) * 0.14) ** 2) and y > int(h * 0.45)
            # Bail slightly above stone
            in_bail = dist2 < (int(min(w, h) * 0.10) ** 2) and int(h * 0.48) < y < int(h * 0.62)
            if in_pendant or in_bail:
                pp[x, y] = 255
            else:
                # Upper frame = chain; also outer sides
                if y < int(h * 0.70):
                    cp[x, y] = 255

    pendant = pendant.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(3))
    chain = chain.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    # Don't let pendant mask steal chain: subtract overlap favoring pendant near center
    pp, cp = pendant.load(), chain.load()
    for y in range(h):
        for x in range(w):
            if pp[x, y] >= 128 and cp[x, y] >= 128:
                cp[x, y] = 0
    pendant = pendant.filter(ImageFilter.GaussianBlur(1.2))
    chain = chain.filter(ImageFilter.GaussianBlur(0.9))
    return pendant, chain


def apply_recolor(
    src: Image.Image,
    pendant_mask: Image.Image,
    chain_mask: Image.Image,
    chain_mode: str,
) -> Image.Image:
    out = src.convert("RGB")
    px = out.load()
    pp = pendant_mask.load()
    cp = chain_mask.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            pa = pp[x, y] / 255.0
            ca = cp[x, y] / 255.0
            if pa < 0.05 and ca < 0.05:
                continue
            if pa >= ca and pa >= 0.05:
                tr, tg, tb = to_silver(r, g, b)
                t = pa
            else:
                tr, tg, tb = (to_rose(r, g, b) if chain_mode == "rose" else to_yellow_gold(r, g, b))
                t = ca
            px[x, y] = (
                int(r + (tr - r) * t),
                int(g + (tg - g) * t),
                int(b + (tb - b) * t),
            )
    return out


def main() -> None:
    ref = find_ref()
    print(f"ref: {ref}")
    src = Image.open(ref).convert("RGB")
    if src.size != (1024, 1024):
        src = src.resize((1024, 1024), Image.Resampling.LANCZOS)

    # Keep a copy of the style ref in shop-product
    style_out = SHOP / "_gen_ref_style.png"
    src.save(style_out, "PNG")

    pendant_m, chain_m = build_masks(src)
    BAK.mkdir(parents=True, exist_ok=True)

    for chain_mode, name in (("rose", "項墜A_silver_chain_rose.png"), ("gold", "項墜A_silver_chain_gold.png")):
        dest = SILVER / name
        if dest.exists():
            bak = BAK / f"{dest.stem}__pre_style{dest.suffix}"
            if not bak.exists():
                shutil.copy2(dest, bak)
        out = apply_recolor(src, pendant_m, chain_m, chain_mode)
        out.save(dest, "PNG", optimize=True)
        print(f"OK {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
