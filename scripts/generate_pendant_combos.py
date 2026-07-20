# -*- coding: utf-8 -*-
"""Manifest + prompts for missing pendant×chain×diamond PNGs (Higgsfield batch)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "public" / "images" / "shop-product"
ZH = "項墜"
METAL_DIR = {"white": "silver", "yellow": "gold", "rose": "rose_gold"}
METAL_SUFFIX = {"white": "silver", "yellow": "gold", "rose": "rose"}
DIAMONDS = ["white", "blue", "yellow", "pink"]
STYLES = ["A", "B", "C"]

METAL_PROMPT = {
    "white": "white gold (K white / platinum tone)",
    "yellow": "yellow gold (K yellow)",
    "rose": "rose gold (K rose)",
}
DIAMOND_PROMPT = {
    "white": "colorless white diamond",
    "blue": "vivid blue diamond",
    "yellow": "fancy yellow diamond",
    "pink": "fancy pink diamond",
}


def combo_path(style: str, pend: str, chain: str, diamond: str) -> Path:
    ps, cs = METAL_SUFFIX[pend], METAL_SUFFIX[chain]
    d = "" if diamond == "white" else f"_{diamond}"
    if pend == chain:
        return ROOT / METAL_DIR[pend] / f"{ZH}{style}_{ps}{d}.png"
    return ROOT / METAL_DIR[pend] / f"{ZH}{style}_{ps}_chain_{cs}{d}.png"


def ref_path(style: str, pend: str, diamond: str) -> Path | None:
    p = combo_path(style, pend, pend, diamond)
    if p.exists():
        return p
    base = combo_path(style, pend, pend, "white")
    return base if base.exists() else None


def build_prompt(style: str, pend: str, chain: str, diamond: str) -> str:
    return (
        "Professional e-commerce product photo on pure white background. "
        f"Same style {style} pendant necklace design and pendant silhouette as the reference image. "
        f"{METAL_PROMPT[pend].capitalize()} pendant with {METAL_PROMPT[chain]} chain necklace. "
        f"Center stone is a {DIAMOND_PROMPT[diamond]}. "
        "Front-facing studio lighting, sharp focus, no text, no watermark, no hands, no model."
    )


def missing_jobs(style: str | None = None) -> list[dict]:
    jobs = []
    styles = [style] if style else STYLES
    for st in styles:
        for pend in METAL_DIR:
            for chain in METAL_DIR:
                for diamond in DIAMONDS:
                    dest = combo_path(st, pend, chain, diamond)
                    if dest.exists():
                        continue
                    ref = ref_path(st, pend, diamond)
                    jobs.append(
                        {
                            "style": st,
                            "pendant": pend,
                            "chain": chain,
                            "diamond": diamond,
                            "dest": str(dest.relative_to(ROOT.parent.parent)).replace("\\", "/"),
                            "ref": str(ref.relative_to(ROOT.parent.parent)).replace("\\", "/") if ref else None,
                            "prompt": build_prompt(st, pend, chain, diamond),
                        }
                    )
    return jobs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", choices=["A", "B", "C"])
    ap.add_argument("--manifest", type=Path, help="Write JSON manifest of missing jobs")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    jobs = missing_jobs(args.style)
    if args.limit:
        jobs = jobs[: args.limit]
    if args.manifest:
        args.manifest.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {len(jobs)} jobs -> {args.manifest}")
    else:
        print(f"missing={len(jobs)}")
        for j in jobs[:5]:
            print(j["dest"])


if __name__ == "__main__":
    main()
