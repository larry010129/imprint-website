"""Engagement page: 4 iconic ring product slots (CMS dropdown picks)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

from app.image_urls import is_uuid, resolve_product_image_url

SLOT_COUNT = 4
_DEFAULT_PATH = Path(__file__).resolve().parent / "data" / "engagement-rings.json"

# Fallback cards when a slot has no published product (legacy static copy).
FALLBACK_CARDS: tuple[dict[str, str], ...] = (
    {
        "name_en": "CLASSIC SOLITAIRE",
        "name_zh": "經典單鑽戒指",
        "description": "凸顯主石光芒，常見求婚首選。",
        "image_url": "",
        "href": "/jewelry/rings/classic-solitaire/",
    },
    {
        "name_en": "PAVE HALO",
        "name_zh": "華麗排鑽戒指",
        "description": "主石外圈排鑽，儀式感更足。",
        "image_url": "",
        "href": "/jewelry/rings/pave-halo/",
    },
    {
        "name_en": "VINTAGE VINE",
        "name_zh": "復古藤蔓戒指",
        "description": "線條溫柔，適合重視故事感的訂製。",
        "image_url": "",
        "href": "/jewelry/rings/vintage-vine/",
    },
    {
        "name_en": "MODERN BAND",
        "name_zh": "極簡線戒",
        "description": "簡潔日常，也適合作為對戒搭配。",
        "image_url": "",
        "href": "/jewelry/rings/modern-band/",
    },
)


def empty_product_ids() -> list[str]:
    return [""] * SLOT_COUNT


def shop_step2_url(category: str, product_id: str) -> str:
    """Wizard depth 2 = configure view (?category=&product=)."""
    cat = quote(str(category or "ring").strip() or "ring", safe="")
    pid = quote(str(product_id).strip(), safe="")
    return f"/shop/calculator/?category={cat}&product={pid}"


def normalize_product_ids(raw: Any) -> list[str]:
    """Pad/trim to SLOT_COUNT; keep empty slots; UUID strings only when set."""
    ids: list[str] = []
    if isinstance(raw, list):
        source = raw
    elif isinstance(raw, dict):
        source = raw.get("productIds") or raw.get("product_ids") or []
    else:
        source = []
    if not isinstance(source, list):
        source = []
    for i in range(SLOT_COUNT):
        value = source[i] if i < len(source) else ""
        text = str(value or "").strip()
        if not text:
            ids.append("")
        elif is_uuid(text):
            ids.append(text)
        else:
            ids.append("")
    return ids


_KV_KEY = "engagement-rings"


def _read_legacy_file(target: Path) -> dict[str, Any] | None:
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def read_engagement_rings_file(path: Path | None = None) -> dict[str, Any]:
    """Read slot picks. Default path → shared DB (cms_kv, one-time import of
    the legacy local JSON); explicit path → file (tests/tools)."""
    if path is not None:
        data = _read_legacy_file(path)
    else:
        from app.cms_kv_store import kv_get_or_import_file

        data = kv_get_or_import_file(_KV_KEY, lambda: _read_legacy_file(_DEFAULT_PATH))
    if not isinstance(data, dict):
        return {"productIds": empty_product_ids()}
    return {"productIds": normalize_product_ids(data)}


def validate_admin_body(
    body: dict[str, Any] | None,
    *,
    cur=None,
) -> tuple[dict[str, Any] | None, str | None]:
    body = body or {}
    if not isinstance(body, dict):
        return None, "invalid body"
    raw = body.get("productIds")
    if raw is None:
        raw = body.get("product_ids")
    if raw is None:
        return None, "productIds required"
    if not isinstance(raw, list):
        return None, "productIds must be a list"
    if len(raw) > SLOT_COUNT:
        return None, f"at most {SLOT_COUNT} productIds"
    ids: list[str] = []
    for i, value in enumerate(raw):
        text = str(value or "").strip()
        if not text:
            ids.append("")
            continue
        if not is_uuid(text):
            return None, f"slot {i + 1}: invalid product id"
        ids.append(text)
    while len(ids) < SLOT_COUNT:
        ids.append("")
    if cur is not None:
        for i, product_id in enumerate(ids):
            if not product_id:
                continue
            cur.execute(
                "select id, category from products where id = %s",
                (product_id,),
            )
            row = cur.fetchone()
            if not row:
                return None, f"slot {i + 1}: product not found"
            if str(row.get("category") or "") != "ring":
                return None, f"slot {i + 1}: must be a ring product"
    return {"productIds": ids}, None


def save_engagement_rings_file(
    data: dict[str, Any],
    path: Path | None = None,
) -> dict[str, Any]:
    """Persist slot picks. Default path → shared DB only (raises on failure
    so saves never silently diverge per environment); explicit path → file."""
    payload = {"productIds": normalize_product_ids(data)}
    if path is None:
        from app.cms_kv_store import kv_set

        kv_set(_KV_KEY, payload)
        return payload
    target = path
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=target.parent,
        delete=False,
        suffix=".tmp",
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    tmp_path.replace(target)
    return payload


def admin_engagement_rings_payload(data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"productIds": normalize_product_ids(data or read_engagement_rings_file())}


def _first_product_image_url(image_rows: list[dict] | None) -> str:
    if not image_rows:
        return ""
    for row in image_rows:
        url = resolve_product_image_url(row.get("file_path"))
        if url:
            return url
    return ""


def fetch_ring_options(cur) -> list[dict[str, str]]:
    """Published + draft rings for CMS dropdowns."""
    cur.execute(
        """
        select id, name_zh, name_en, is_published
        from products
        where category = 'ring'
        order by sort_order nulls last, created_at desc nulls last, id
        """
    )
    out: list[dict[str, str]] = []
    for row in cur.fetchall() or []:
        pid = str(row.get("id") or "")
        if not pid:
            continue
        name_zh = str(row.get("name_zh") or "").strip()
        name_en = str(row.get("name_en") or "").strip()
        label = name_zh or name_en or pid
        if name_zh and name_en:
            label = f"{name_zh}（{name_en}）"
        if not row.get("is_published"):
            label = f"{label}（草稿）"
        out.append({"id": pid, "label": label})
    return out


def resolve_engagement_ring_cards(cur, path: Path | None = None) -> list[dict[str, str]]:
    """Public cards for engagement template — product data or static fallback."""
    ids = normalize_product_ids(read_engagement_rings_file(path))
    cards: list[dict[str, str]] = []
    for index, product_id in enumerate(ids):
        fallback = dict(FALLBACK_CARDS[index])
        if not product_id:
            cards.append(fallback)
            continue
        cur.execute(
            """
            select id, category, name_zh, name_en, description_zh, default_color, is_published
            from products
            where id = %s and category = 'ring'
            """,
            (product_id,),
        )
        product = cur.fetchone()
        if not product or not product.get("is_published"):
            cards.append(fallback)
            continue
        cur.execute(
            """
            select color, file_path
            from product_images
            where product_id = %s
            order by sort_order, id
            """,
            (product_id,),
        )
        images = cur.fetchall() or []
        name_en = str(product.get("name_en") or "").strip() or fallback["name_en"]
        name_zh = str(product.get("name_zh") or "").strip() or fallback["name_zh"]
        description = (
            str(product.get("description_zh") or "").strip() or fallback["description"]
        )
        image_url = _first_product_image_url(images)
        category = str(product.get("category") or "ring")
        cards.append(
            {
                "name_en": name_en,
                "name_zh": name_zh,
                "description": description,
                "image_url": image_url,
                "href": shop_step2_url(category, product_id),
                "product_id": product_id,
            }
        )
    return cards
