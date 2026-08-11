"""Memorial diamond (紀念鑽石) color products — shop catalog + admin seed.

Product = gem COLOR (白鑽/黃鑽/藍鑽/粉鑽). Images inside = diamond SHAPES.
Legacy 滿月/寵物/結髮/全家福/生命 series rows are unpublished on seed.
"""

from __future__ import annotations

import re
from typing import Any

from app.diamond_shapes import (
    DEFAULT_SHAPES,
    builtin_shape_ids,
    is_allowed_shape_id,
    matrix_shapes_payload,
)

DIAMOND_CARATS = [
    "0.1", "0.2", "0.3", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0", "1.5", "2.0", "3.0",
]

VALID_DIAMOND_COLORS = frozenset({"white", "yellow", "blue", "pink"})

# Built-in cuts (incl. Asscher). Custom cuts live in diamond_shapes table.
DIAMOND_MATRIX_SHAPES: list[dict[str, str]] = matrix_shapes_payload()
VALID_DIAMOND_SHAPES = builtin_shape_ids()

# Old series products (滿月/寵物/…) — retired from admin listing + shop catalog.
LEGACY_SERIES_STYLE_KEYS = frozenset(
    {
        "diamond-first-love",
        "diamond-pet",
        "diamond-love",
        "diamond-family",
        "diamond-heirloom",
    }
)

_LEGACY_LIFESTYLE_IMAGE_RE = re.compile(
    r"(?:^|/)(?:static/)?images/hero/imprint-diamond-",
    re.IGNORECASE,
)
_GEM_COLOR_IMAGE_RE = re.compile(
    r"(?:^|/)(?:static/)?images/diamonds/colors/(?:white|yellow|blue|pink)\.png$",
    re.IGNORECASE,
)

STYLE_KEY_RE = re.compile(r"^diamond-[a-z0-9][a-z0-9-]{0,40}$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def matrix_shape_image_url(shape: str, color: str) -> str:
    """Bundled matrix PNG for shape × color."""
    shape_id = str(shape or "round").strip().lower()
    if not is_allowed_shape_id(shape_id):
        shape_id = "round"
    color_id = str(color or "white").strip().lower()
    if color_id not in VALID_DIAMOND_COLORS:
        color_id = "white"
    return f"/static/images/diamonds/matrix/{shape_id}-{color_id}.png"


def default_shape_images(color: str) -> dict[str, list[str]]:
    """All shape image slots for one color product."""
    return {
        shape["id"]: [matrix_shape_image_url(shape["id"], color)]
        for shape in DIAMOND_MATRIX_SHAPES
    }


def _color_product(
    color: str,
    name_zh: str,
    name_en: str,
    description_zh: str,
) -> dict[str, Any]:
    key = f"diamond-{color}"
    return {
        "id": key,
        "styleKey": key,
        "nameZh": name_zh,
        "nameEn": name_en,
        "descriptionZh": description_zh,
        "defaultColor": color,
        "golds": [],
        "carats": DIAMOND_CARATS,
        "images": default_shape_images(color),
    }


# Color = product. Shape images live inside each color row.
DIAMOND_COLOR_PRODUCTS: list[dict[str, Any]] = [
    _color_product(
        "white",
        "白鑽",
        "White Diamond",
        "紀念白鑽（裸鑽試算，不含鑲嵌）",
    ),
    _color_product(
        "yellow",
        "黃鑽",
        "Yellow Diamond",
        "紀念黃鑽（裸鑽試算，不含鑲嵌）",
    ),
    _color_product(
        "blue",
        "藍鑽",
        "Blue Diamond",
        "紀念藍鑽（裸鑽試算，不含鑲嵌）",
    ),
    _color_product(
        "pink",
        "粉鑽",
        "Pink Diamond",
        "紀念粉鑽（裸鑽試算，不含鑲嵌）",
    ),
]

# Back-compat alias for older imports/tests.
DIAMOND_STYLES = DIAMOND_COLOR_PRODUCTS


def ensure_product_style_key_column(cur) -> None:
    """Add products.style_key for shop linking (memorial diamond colors)."""
    cur.execute("alter table products add column if not exists style_key text")
    cur.execute(
        """
        create unique index if not exists products_style_key_uidx
        on products (style_key)
        where style_key is not null
        """
    )


def ensure_memorial_diamond_tombstone_table(cur) -> None:
    """Tombstones stop ensure/merge from resurrecting admin-deleted color products."""
    cur.execute(
        """
        create table if not exists memorial_diamond_style_tombstones (
            style_key text primary key,
            deleted_at timestamptz not null default now()
        )
        """
    )


def list_tombstoned_style_keys(cur) -> set[str]:
    ensure_memorial_diamond_tombstone_table(cur)
    cur.execute("select style_key from memorial_diamond_style_tombstones")
    return {str(row["style_key"]) for row in cur.fetchall() if row.get("style_key")}


def record_style_tombstone(cur, style_key: str | None) -> bool:
    """Mark a known color style_key as manually deleted. Returns True if recorded."""
    key = normalize_style_key(style_key)
    if not key or key not in known_style_keys():
        return False
    ensure_memorial_diamond_tombstone_table(cur)
    cur.execute(
        """
        insert into memorial_diamond_style_tombstones (style_key)
        values (%s)
        on conflict (style_key) do update set deleted_at = now()
        """,
        (key,),
    )
    return True


def clear_style_tombstone(cur, style_key: str | None) -> None:
    """Allow ensure/seed again after admin recreates that color product."""
    key = normalize_style_key(style_key)
    if not key:
        return
    ensure_memorial_diamond_tombstone_table(cur)
    cur.execute(
        "delete from memorial_diamond_style_tombstones where style_key = %s",
        (key,),
    )


def normalize_style_key(raw: str | None) -> str | None:
    key = str(raw or "").strip().lower()
    if not key:
        return None
    if not STYLE_KEY_RE.match(key):
        return None
    return key


def style_key_from_name_en(name_en: str | None) -> str | None:
    slug = _SLUG_RE.sub("-", str(name_en or "").strip().lower()).strip("-")
    if not slug:
        return None
    return normalize_style_key(f"diamond-{slug[:40]}")


def known_style_keys() -> set[str]:
    return {str(s["styleKey"]) for s in DIAMOND_COLOR_PRODUCTS}


def color_from_style_key(style_key: str | None) -> str | None:
    key = str(style_key or "").strip().lower()
    if key.startswith("diamond-"):
        color = key[len("diamond-") :]
        if color in VALID_DIAMOND_COLORS:
            return color
    return None


def is_legacy_lifestyle_image(path: str | None) -> bool:
    """True for series lifestyle heroes formerly used as diamond product thumbs."""
    normalized = str(path or "").replace("\\", "/")
    return bool(_LEGACY_LIFESTYLE_IMAGE_RE.search(normalized))


def is_legacy_gem_color_image(path: str | None) -> bool:
    """True for color-swatch PNGs wrongly used as product image slots."""
    normalized = str(path or "").replace("\\", "/")
    return bool(_GEM_COLOR_IMAGE_RE.search(normalized))


def _insert_product_image(cur, product_id: Any, slot: str, url: str, sort_order: int) -> None:
    cur.execute(
        """
        insert into product_images (product_id, color, file_path, sort_order)
        values (%s, %s, %s, %s)
        """,
        (product_id, slot, url, sort_order),
    )


def _seed_shape_images(cur, product_id: Any, color: str) -> None:
    sort_order = 0
    for shape in DEFAULT_SHAPES:
        _insert_product_image(
            cur,
            product_id,
            shape["id"],
            matrix_shape_image_url(shape["id"], color),
            sort_order,
        )
        sort_order += 1


def retire_legacy_series_products(cur) -> int:
    """Unpublish 滿月/寵物/… rows and clear style_key so color keys own linking.

    Soft-retire only — rows stay for history/orders; not in published catalog.
    """
    keys = sorted(LEGACY_SERIES_STYLE_KEYS)
    if not keys:
        return 0
    cur.execute(
        """
        update products
        set is_published = false,
            style_key = null,
            updated_at = now()
        where category = 'diamond'
          and style_key = any(%s)
        """,
        (keys,),
    )
    return int(cur.rowcount or 0)


def sync_memorial_diamond_seed_images(cur, product_id: Any, color: str | None = None) -> int:
    """Drop lifestyle/color-swatch thumbs; fill missing shape slots for this color.

    Custom shape uploads kept. Returns how many shape rows inserted.
    """
    gem_color = str(color or "white").strip().lower()
    if gem_color not in VALID_DIAMOND_COLORS:
        gem_color = "white"

    cur.execute(
        "select id, color, file_path from product_images where product_id = %s",
        (product_id,),
    )
    rows = list(cur.fetchall() or [])
    for row in rows:
        slot = str(row.get("color") or "").strip().lower()
        path = row.get("file_path")
        # Keep custom cut slots (registry / slug). Drop only legacy junk.
        drop = (
            is_legacy_lifestyle_image(path)
            or is_legacy_gem_color_image(path)
            or (slot and not is_allowed_shape_id(slot))
        )
        if drop:
            cur.execute("delete from product_images where id = %s", (row["id"],))

    cur.execute(
        """
        select color, coalesce(max(sort_order), -1) as max_sort
        from product_images
        where product_id = %s
        group by color
        """,
        (product_id,),
    )
    present = {str(r["color"]).lower(): int(r["max_sort"]) for r in (cur.fetchall() or [])}
    next_sort = max(present.values(), default=-1) + 1
    inserted = 0
    # Seed missing built-ins only — never wipe admin custom cuts.
    for shape in DEFAULT_SHAPES:
        shape_id = str(shape["id"])
        if shape_id in present:
            continue
        _insert_product_image(
            cur,
            product_id,
            shape_id,
            matrix_shape_image_url(shape_id, gem_color),
            next_sort,
        )
        next_sort += 1
        inserted += 1
    return inserted


def _backfill_color_style_keys(cur) -> int:
    """Link orphan diamond rows (no style_key) to diamond-{color} when name matches."""
    updated = 0
    for product in DIAMOND_COLOR_PRODUCTS:
        key = str(product["styleKey"])
        color = str(product["defaultColor"])
        cur.execute(
            """
            update products p
            set style_key = %s, updated_at = now()
            where p.category = 'diamond'
              and p.default_color = %s
              and p.style_key is null
              and p.name_zh = %s
              and not exists (
                select 1 from products x where x.style_key = %s
              )
            """,
            (key, color, product["nameZh"], key),
        )
        updated += int(cur.rowcount or 0)
    return updated


def _clear_orphan_tombstones_if_catalog_empty(cur) -> int:
    """When every color product is gone, tombstones block re-seed — clear them.

    Single admin deletes still tombstone (other rows remain). Only resets when
    zero memorial color products exist in DB.
    """
    keys = sorted(known_style_keys())
    if not keys:
        return 0
    cur.execute(
        """
        select count(*) as n from products
        where category = 'diamond'
          and style_key = any(%s)
        """,
        (keys,),
    )
    if int((cur.fetchone() or {}).get("n") or 0) > 0:
        return 0
    tombstoned = list_tombstoned_style_keys(cur)
    cleared = 0
    for key in keys:
        if key in tombstoned:
            clear_style_tombstone(cur, key)
            cleared += 1
    return cleared


def ensure_memorial_diamond_products(cur) -> int:
    """Upsert four color products; retire legacy five-series rows.

    Inserts missing color rows unless admin tombstoned that style_key.
    Syncs shape images on every call (admin list load / startup seed).

    Returns how many product rows were inserted.
    """
    ensure_product_style_key_column(cur)
    _clear_orphan_tombstones_if_catalog_empty(cur)
    retire_legacy_series_products(cur)
    _backfill_color_style_keys(cur)
    tombstoned = list_tombstoned_style_keys(cur)
    inserted = 0
    for index, product in enumerate(DIAMOND_COLOR_PRODUCTS):
        key = str(product["styleKey"])
        color = str(product["defaultColor"])
        cur.execute(
            """
            select id from products
            where category = 'diamond' and style_key = %s
            limit 1
            """,
            (key,),
        )
        row = cur.fetchone()
        if row:
            sync_memorial_diamond_seed_images(cur, row["id"], color)
            continue
        if key in tombstoned:
            continue
        cur.execute(
            """
            insert into products (
                category, name_zh, name_en, description_zh, description_en,
                default_color, allows_engraving, allows_fancy_shapes,
                allows_pendant_only, allows_with_chain,
                is_published, first_published_at, sort_order, style_key
            )
            values (
                'diamond', %s, %s, %s, null,
                %s, false, true, true, true,
                true, now(), %s, %s
            )
            returning id
            """,
            (
                product["nameZh"],
                product.get("nameEn") or key,
                product.get("descriptionZh"),
                color,
                index,
                key,
            ),
        )
        created = cur.fetchone()
        product_id = created["id"] if created else None
        if not product_id:
            continue
        inserted += 1
        _seed_shape_images(cur, product_id, color)
    return inserted


def _static_entry(product: dict[str, Any]) -> dict[str, Any]:
    images = {
        shape: list(urls)
        for shape, urls in (product.get("images") or {}).items()
        if isinstance(urls, list)
    }
    color = str(product.get("defaultColor") or "white")
    return {
        "id": product["id"],
        "styleKey": product["styleKey"],
        "nameZh": product["nameZh"],
        "nameEn": product.get("nameEn"),
        "descriptionZh": product.get("descriptionZh"),
        "descriptionEn": product.get("descriptionEn"),
        "defaultColor": color,
        "golds": [],
        "carats": list(product.get("carats") or DIAMOND_CARATS),
        "colors": [color],
        "images": images,
        "weights": {},
        "manualPrices": {},
        "draft": False,
        "thumbUrl": (images.get("round") or [None])[0],
    }


def _images_shape_slots(
    images: dict[str, Any] | None,
    base_images: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Keep shape-keyed URLs; drop lifestyle/gem-swatch; fill missing built-ins."""
    cleaned: dict[str, list[str]] = {}
    for slot, urls in (images or {}).items():
        if not isinstance(urls, list):
            continue
        shape = str(slot).strip().lower()
        if not is_allowed_shape_id(shape):
            continue
        kept = [
            str(u)
            for u in urls
            if u
            and not is_legacy_lifestyle_image(str(u))
            and not is_legacy_gem_color_image(str(u))
        ]
        if kept:
            cleaned[shape] = kept
    for shape, urls in base_images.items():
        if shape not in cleaned and urls:
            cleaned[shape] = list(urls)
    return cleaned or {s: list(u) for s, u in base_images.items()}


def merge_memorial_diamond_catalog(
    db_entries: list[dict[str, Any]] | None,
    excluded_style_keys: set[str] | frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Static color products as base; DB overlays name/images by styleKey.

    ``excluded_style_keys`` (admin tombstones) skip static fallback when no DB row.
    """
    excluded = {str(k).strip().lower() for k in (excluded_style_keys or set()) if k}
    by_key: dict[str, dict[str, Any]] = {}
    extras: list[dict[str, Any]] = []
    for entry in db_entries or []:
        key = str(entry.get("styleKey") or "").strip()
        # Skip retired series keys if any still appear without style_key clear.
        if key in LEGACY_SERIES_STYLE_KEYS:
            continue
        if key in known_style_keys():
            by_key[key] = entry
        else:
            extras.append(entry)

    merged: list[dict[str, Any]] = []
    for product in DIAMOND_COLOR_PRODUCTS:
        key = str(product["styleKey"])
        base = _static_entry(product)
        db = by_key.get(key)
        if not db:
            if key in excluded:
                continue
            merged.append(base)
            continue
        raw_images = db.get("images") if isinstance(db.get("images"), dict) else None
        if not raw_images:
            thumb = db.get("thumbUrl")
            if (
                thumb
                and not is_legacy_lifestyle_image(str(thumb))
                and not is_legacy_gem_color_image(str(thumb))
            ):
                raw_images = {"round": [str(thumb)]}
        images = _images_shape_slots(raw_images, base["images"])
        carats = (
            db.get("carats")
            if isinstance(db.get("carats"), list) and db.get("carats")
            else list(DIAMOND_CARATS)
        )
        thumb = db.get("thumbUrl")
        if (
            not thumb
            or is_legacy_lifestyle_image(str(thumb))
            or is_legacy_gem_color_image(str(thumb))
        ):
            thumb = (images.get("round") or [None])[0]
            if not thumb:
                for urls in images.values():
                    if urls:
                        thumb = urls[0]
                        break
        color = (
            db.get("defaultColor")
            or color_from_style_key(key)
            or base["defaultColor"]
        )
        merged.append(
            {
                **base,
                "id": db.get("id") or base["id"],
                "styleKey": key,
                "nameZh": db.get("nameZh") or base["nameZh"],
                "nameEn": db.get("nameEn") or base.get("nameEn"),
                "descriptionZh": (
                    db.get("descriptionZh")
                    if db.get("descriptionZh") is not None
                    else base.get("descriptionZh")
                ),
                "descriptionEn": db.get("descriptionEn"),
                "defaultColor": color,
                "golds": [],
                "carats": [str(c) for c in carats],
                "colors": [color],
                "images": images,
                "thumbUrl": thumb or None,
                "draft": bool(db.get("draft")),
            }
        )

    for entry in extras:
        if entry.get("draft"):
            continue
        # Never re-surface retired series via extras (style_key already cleared).
        entry_key = str(entry.get("styleKey") or entry.get("id") or "")
        if entry_key in LEGACY_SERIES_STYLE_KEYS:
            continue
        images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
        carats = (
            entry.get("carats")
            if isinstance(entry.get("carats"), list) and entry.get("carats")
            else list(DIAMOND_CARATS)
        )
        color = str(entry.get("defaultColor") or "white")
        merged.append(
            {
                **entry,
                "golds": [],
                "carats": [str(c) for c in carats],
                "images": images or {},
                "colors": entry.get("colors") or [color],
            }
        )
    return merged
