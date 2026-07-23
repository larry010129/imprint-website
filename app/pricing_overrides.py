"""Admin-editable pricing overrides (the `pricing_settings` singleton row).

The admin 價格設定 panel writes a JSON `overrides` blob here via POST /api/pricing;
the public configurator reads it via GET /api/pricing; and — crucially — the
server checkout authority (app/pricing.py) reads it too, so an admin price edit
actually changes what a customer is charged, not just what the configurator
displays.

Design guarantee: an EMPTY overrides blob (the default) resolves to exactly the
hard-coded tables in app/pricing.py, so checkout math is unchanged until an admin
deliberately sets a value. Override keys use the client's carat format ('0.10',
'1.00'); we canonicalize to float so they line up with the server's ('0.1', '1').
"""

from __future__ import annotations

from typing import Any


def load_overrides(cur) -> dict[str, Any]:
    cur.execute("select overrides from pricing_settings where id = 1")
    row = cur.fetchone()
    if not row:
        return {}
    ov = row["overrides"]
    return ov if isinstance(ov, dict) else {}


def save_overrides(cur, overrides: dict[str, Any]) -> dict[str, Any]:
    from psycopg.types.json import Jsonb

    clean = overrides if isinstance(overrides, dict) else {}
    cur.execute(
        """
        insert into pricing_settings (id, overrides, updated_at)
        values (1, %s, now())
        on conflict (id) do update set overrides = excluded.overrides, updated_at = now()
        """,
        (Jsonb(clean),),
    )
    return clean


def canonical_carat(key: Any) -> str | None:
    """'0.10' / '0.5' / 1 -> '0.1' / '0.5' / '1.0' so client and server keys meet."""
    try:
        return f"{float(key):g}" if float(key) != int(float(key)) else f"{int(float(key))}.0"
    except (TypeError, ValueError):
        return None


def _merge_table(base: dict, override: Any) -> dict:
    """Overlay an override price table onto a base table, keyed by canonical carat."""
    out: dict[str, float] = {}
    for k, v in (base or {}).items():
        ck = canonical_carat(k)
        if ck is not None:
            out[ck] = v
    if isinstance(override, dict):
        for k, v in override.items():
            ck = canonical_carat(k)
            if ck is not None and isinstance(v, (int, float)):
                out[ck] = v
    return out


def _merge_multi(base: dict, override: Any) -> dict:
    """Multi-stone tables: carat -> {stone_count -> price}."""
    out: dict[str, dict] = {}
    for k, row in (base or {}).items():
        ck = canonical_carat(k)
        if ck is not None and isinstance(row, dict):
            out[ck] = {str(sc): px for sc, px in row.items()}
    if isinstance(override, dict):
        for k, row in override.items():
            ck = canonical_carat(k)
            if ck is not None and isinstance(row, dict):
                dst = out.setdefault(ck, {})
                for sc, px in row.items():
                    if isinstance(px, (int, float)):
                        dst[str(sc)] = px
    return out
