"""Necklace (chain-only) pricing types — wax tables from 鍊條價格.xlsx."""

from __future__ import annotations

from typing import Any

# Slug keys avoid encoding issues in DB/API; label_zh is the shop-facing name.
NECKLACE_TYPES: dict[str, dict[str, Any]] = {
    "douyuan": {
        "labelZh": "抖圓鏈",
        "thicknesses": ["1.0mm", "1.5mm", "2.0mm", "2.5mm", "3.0mm"],
        "lengthWeights": {
            "1.0mm": {
                "36": 0.014, "41": 0.016, "46": 0.018, "51": 0.02,
                "61": 0.024, "76": 0.03, "80": 0.032,
            },
            "1.5mm": {
                "36": 0.026, "41": 0.03, "46": 0.033, "51": 0.037,
                "61": 0.043, "76": 0.054, "80": 0.057,
            },
            "2.0mm": {
                "36": 0.04, "41": 0.046, "46": 0.051, "51": 0.056,
                "61": 0.066, "76": 0.083, "80": 0.087,
            },
            "2.5mm": {
                "36": 0.047, "41": 0.053, "46": 0.059, "51": 0.065,
                "61": 0.076, "76": 0.095, "80": 0.1,
            },
            "3.0mm": {
                "36": 0.052, "41": 0.06, "46": 0.066, "51": 0.074,
                "61": 0.086, "76": 0.11, "80": 0.12,
            },
        },
    },
}

DEFAULT_NECKLACE_TYPE = "douyuan"
VALID_NECKLACE_TYPES = frozenset(NECKLACE_TYPES)


def necklace_type_thicknesses(chain_type: str | None) -> list[str]:
    entry = NECKLACE_TYPES.get(chain_type or DEFAULT_NECKLACE_TYPE, {})
    return list(entry.get("thicknesses") or [])


def necklace_type_length_weights(chain_type: str | None) -> dict[str, dict[str, float]]:
    entry = NECKLACE_TYPES.get(chain_type or DEFAULT_NECKLACE_TYPE, {})
    raw = entry.get("lengthWeights") or {}
    out: dict[str, dict[str, float]] = {}
    for thick, lengths in raw.items():
        if not isinstance(lengths, dict):
            continue
        row: dict[str, float] = {}
        for length_key, wax in lengths.items():
            try:
                value = float(wax)
            except (TypeError, ValueError):
                continue
            if value > 0:
                row[str(length_key)] = value
        if row:
            out[str(thick)] = row
    return out


def chain_catalog_for_admin() -> dict[str, Any]:
    """JSON-safe catalog for admin UI (type selector + 填入標準蠟重表)."""
    types: dict[str, Any] = {}
    for slug, entry in NECKLACE_TYPES.items():
        types[slug] = {
            "labelZh": entry["labelZh"],
            "thicknesses": entry["thicknesses"],
            "lengthWeights": entry["lengthWeights"],
        }
    return {
        "defaultType": DEFAULT_NECKLACE_TYPE,
        "types": types,
    }
