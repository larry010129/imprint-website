"""Memorial diamond (紀念鑽石) style defaults — shop catalog + admin seed."""

from __future__ import annotations

import re
from typing import Any

DIAMOND_CARATS = [
    "0.1", "0.2", "0.3", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0", "1.5", "2.0", "3.0",
]

# Static memorial styles (shop linking keys). Admin edits overlay name/image/color.
DIAMOND_STYLES: list[dict[str, Any]] = [
    {
        "id": "diamond-first-love",
        "styleKey": "diamond-first-love",
        "nameZh": "滿月鑽石",
        "nameEn": "First Love Diamond",
        "descriptionZh": "以寶寶胎髮培育的紀念鑽石（裸鑽試算，不含鑲嵌）",
        "golds": [],
        "carats": DIAMOND_CARATS,
        "images": {"white": ["/static/images/hero/imprint-diamond-newborn-baby-necklace.jpg"]},
    },
    {
        "id": "diamond-pet",
        "styleKey": "diamond-pet",
        "nameZh": "寵物鑽石",
        "nameEn": "Pet Diamond",
        "descriptionZh": "以毛孩毛髮培育的紀念鑽石（裸鑽試算，不含鑲嵌）",
        "golds": [],
        "carats": DIAMOND_CARATS,
        "images": {"white": ["/static/images/hero/imprint-diamond-pet-memorial-cat.jpg"]},
    },
    {
        "id": "diamond-love",
        "styleKey": "diamond-love",
        "nameZh": "結髮鑽石",
        "nameEn": "Love Diamond",
        "descriptionZh": "以夫妻髮絲共同培育的紀念鑽石（裸鑽試算，不含鑲嵌）",
        "golds": [],
        "carats": DIAMOND_CARATS,
        "images": {"white": ["/static/images/hero/imprint-diamond-wedding-couple-ring.jpg"]},
    },
    {
        "id": "diamond-family",
        "styleKey": "diamond-family",
        "nameZh": "全家福鑽石",
        "nameEn": "Family Diamond",
        "descriptionZh": "集合全家人髮絲培育的紀念鑽石（裸鑽試算，不含鑲嵌）",
        "golds": [],
        "carats": DIAMOND_CARATS,
        "images": {"white": ["/static/images/hero/imprint-diamond-family-portrait-jewelry.jpg"]},
    },
    {
        "id": "diamond-heirloom",
        "styleKey": "diamond-heirloom",
        "nameZh": "生命鑽石",
        "nameEn": "Heirloom Diamond",
        "descriptionZh": "以親人毛髮或骨灰培育的紀念鑽石（裸鑽試算，不含鑲嵌）",
        "golds": [],
        "carats": DIAMOND_CARATS,
        "images": {"white": ["/static/images/hero/imprint-diamond-heirloom-memorial.jpg"]},
    },
]

VALID_DIAMOND_COLORS = frozenset({"white", "yellow", "blue", "pink"})
STYLE_KEY_RE = re.compile(r"^diamond-[a-z0-9][a-z0-9-]{0,40}$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def ensure_product_style_key_column(cur) -> None:
    """Add products.style_key for shop linking (memorial diamond styles)."""
    cur.execute("alter table products add column if not exists style_key text")
    cur.execute(
        """
        create unique index if not exists products_style_key_uidx
        on products (style_key)
        where style_key is not null
        """
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
    return {str(s["styleKey"]) for s in DIAMOND_STYLES}


def ensure_memorial_diamond_products(cur) -> int:
    """Upsert the five shop memorial styles into products for admin editing.

    Returns how many rows were inserted.
    """
    ensure_product_style_key_column(cur)
    inserted = 0
    for index, style in enumerate(DIAMOND_STYLES):
        key = str(style["styleKey"])
        cur.execute(
            "select id from products where style_key = %s limit 1",
            (key,),
        )
        if cur.fetchone():
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
                'white', false, true, true, true,
                true, now(), %s, %s
            )
            returning id
            """,
            (
                style["nameZh"],
                style.get("nameEn") or key,
                style.get("descriptionZh"),
                index,
                key,
            ),
        )
        row = cur.fetchone()
        product_id = row["id"] if row else None
        if not product_id:
            continue
        inserted += 1
        images = (style.get("images") or {}).get("white") or []
        for sort_order, url in enumerate(images):
            cur.execute(
                """
                insert into product_images (product_id, color, file_path, sort_order)
                values (%s, 'white', %s, %s)
                """,
                (product_id, url, sort_order),
            )
    return inserted


def _static_entry(style: dict[str, Any]) -> dict[str, Any]:
    images = {
        color: list(urls)
        for color, urls in (style.get("images") or {}).items()
        if isinstance(urls, list)
    }
    return {
        "id": style["id"],
        "styleKey": style["styleKey"],
        "nameZh": style["nameZh"],
        "nameEn": style.get("nameEn"),
        "descriptionZh": style.get("descriptionZh"),
        "descriptionEn": style.get("descriptionEn"),
        "defaultColor": style.get("defaultColor") or "white",
        "golds": [],
        "carats": list(style.get("carats") or DIAMOND_CARATS),
        "colors": list(images.keys()) or ["white"],
        "images": images,
        "weights": {},
        "manualPrices": {},
        "draft": False,
    }


def merge_memorial_diamond_catalog(db_entries: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Static styles as base; DB products overlay name/images/colors by styleKey."""
    by_key: dict[str, dict[str, Any]] = {}
    extras: list[dict[str, Any]] = []
    for entry in db_entries or []:
        key = str(entry.get("styleKey") or "").strip()
        if key in known_style_keys():
            by_key[key] = entry
        else:
            extras.append(entry)

    merged: list[dict[str, Any]] = []
    for style in DIAMOND_STYLES:
        key = str(style["styleKey"])
        base = _static_entry(style)
        db = by_key.get(key)
        if not db:
            merged.append(base)
            continue
        images = db.get("images") if isinstance(db.get("images"), dict) else None
        if not images:
            thumb = db.get("thumbUrl")
            if thumb:
                color_key = str(db.get("defaultColor") or "white")
                images = {color_key: [str(thumb)]}
            else:
                images = base["images"]
        colors = db.get("colors") if isinstance(db.get("colors"), list) and db.get("colors") else list(images.keys())
        carats = db.get("carats") if isinstance(db.get("carats"), list) and db.get("carats") else list(DIAMOND_CARATS)
        thumb = db.get("thumbUrl")
        if not thumb:
            for urls in images.values():
                if urls:
                    thumb = urls[0]
                    break
        merged.append(
            {
                **base,
                "id": db.get("id") or base["id"],
                "styleKey": key,
                "nameZh": db.get("nameZh") or base["nameZh"],
                "nameEn": db.get("nameEn") or base.get("nameEn"),
                "descriptionZh": db.get("descriptionZh") if db.get("descriptionZh") is not None else base.get("descriptionZh"),
                "descriptionEn": db.get("descriptionEn"),
                "defaultColor": db.get("defaultColor") or base["defaultColor"],
                "golds": [],
                "carats": [str(c) for c in carats],
                "colors": colors,
                "images": images,
                "thumbUrl": thumb or None,
                "draft": bool(db.get("draft")),
            }
        )

    for entry in extras:
        if entry.get("draft"):
            continue
        images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
        carats = entry.get("carats") if isinstance(entry.get("carats"), list) and entry.get("carats") else list(DIAMOND_CARATS)
        merged.append(
            {
                **entry,
                "golds": [],
                "carats": [str(c) for c in carats],
                "images": images or {},
                "colors": entry.get("colors") or list((images or {}).keys()) or ["white"],
            }
        )
    return merged
