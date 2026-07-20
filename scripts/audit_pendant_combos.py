# -*- coding: utf-8 -*-
"""List missing cross-metal pendant×chain×diamond PNG combos."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "public" / "images" / "shop-product"
ZH = "項墜"
METAL_DIR = {"white": "silver", "yellow": "gold", "rose": "rose_gold"}
METAL_SUFFIX = {"white": "silver", "yellow": "gold", "rose": "rose"}
DIAMONDS = ["white", "blue", "yellow", "pink"]
STYLES = ["A", "B", "C"]


def combo_path(style: str, pend: str, chain: str, diamond: str) -> Path:
    ps, cs = METAL_SUFFIX[pend], METAL_SUFFIX[chain]
    d = "" if diamond == "white" else f"_{diamond}"
    if pend == chain:
        return ROOT / METAL_DIR[pend] / f"{ZH}{style}_{ps}{d}.png"
    return ROOT / METAL_DIR[pend] / f"{ZH}{style}_{ps}_chain_{cs}{d}.png"


def main() -> None:
    missing: list[dict] = []
    have = 0
    for style in STYLES:
        for pend in METAL_DIR:
            for chain in METAL_DIR:
                for diamond in DIAMONDS:
                    p = combo_path(style, pend, chain, diamond)
                    if p.exists():
                        have += 1
                    else:
                        missing.append(
                            {
                                "style": style,
                                "pendant": pend,
                                "chain": chain,
                                "diamond": diamond,
                                "path": str(p.relative_to(ROOT.parent.parent)),
                            }
                        )
    print(f"have={have} missing={len(missing)} total={have + len(missing)}")
    for row in missing[:8]:
        print(row)


if __name__ == "__main__":
    main()
