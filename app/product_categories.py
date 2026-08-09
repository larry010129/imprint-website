"""Product category (品項) registry — dynamic tabs for admin and shop step-1 tiles."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from threading import Lock
from time import monotonic
import uuid
from datetime import datetime, timezone
from typing import Any

from psycopg import errors as pg_errors
from psycopg.types.json import Jsonb

from app.image_urls import resolve_product_image_url

DEFAULT_CATEGORIES: list[dict] = [
    {"slug": "diamond", "label_zh": "紀念鑽石", "label_en": "Memorial diamond", "thumb_path": None, "sort_order": 0, "addon_price_twd": 0},
    {"slug": "pendant", "label_zh": "項墜", "label_en": "Pendant", "thumb_path": None, "sort_order": 1, "addon_price_twd": 0},
    {"slug": "ring", "label_zh": "戒指", "label_en": "Ring", "thumb_path": None, "sort_order": 2, "addon_price_twd": 0},
    {"slug": "earring", "label_zh": "耳環", "label_en": "Earring", "thumb_path": None, "sort_order": 3, "addon_price_twd": 0},
    {"slug": "bracelet", "label_zh": "手鍊", "label_en": "Bracelet", "thumb_path": None, "sort_order": 4, "addon_price_twd": 0},
    {"slug": "chain", "label_zh": "鏈條", "label_en": "Chain", "thumb_path": None, "sort_order": 5, "addon_price_twd": 0},
]

_CATEGORY_SELECT = (
    "slug, label_zh, label_en, thumb_path, sort_order, addon_price_twd, "
    "ring_size_config, created_at, updated_at"
)
_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
_ADDON_MAX_TWD = 10_000_000
# Positive integer floor only — no hard upper ceiling on ring sizes.
_RING_SIZE_MIN = 1
# Soft UX default when maxSize omitted (not a validation ceiling).
_RING_SIZE_DEFAULT_MAX = 18
_CATEGORY_CACHE_TTL_SECONDS = 60.0
_category_cache_lock = Lock()
_category_cache: tuple[float, list[dict]] | None = None


def clear_category_cache() -> None:
    """Invalidate the short-lived public category snapshot after writes."""
    global _category_cache
    with _category_cache_lock:
        _category_cache = None


def ensure_product_categories_schema(cur) -> None:
    """Create product_categories + seed defaults (migration may not have run)."""
    cur.execute(
        """
        create table if not exists product_categories (
          slug text primary key,
          label_zh text not null,
          label_en text,
          thumb_path text,
          sort_order int not null default 0,
          addon_price_twd int not null default 0,
          ring_size_config jsonb,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    cur.execute(
        "alter table product_categories "
        "add column if not exists addon_price_twd int not null default 0"
    )
    cur.execute(
        "alter table product_categories "
        "add column if not exists ring_size_config jsonb"
    )
    cur.execute(
        """
        insert into product_categories (slug, label_zh, label_en, sort_order, addon_price_twd) values
          ('diamond', '紀念鑽石', 'Memorial diamond', 0, 0),
          ('pendant', '項墜', 'Pendant', 1, 0),
          ('ring', '戒指', 'Ring', 2, 0),
          ('earring', '耳環', 'Earring', 3, 0),
          ('bracelet', '手鍊', 'Bracelet', 4, 0),
          ('chain', '鏈條', 'Chain', 5, 0)
        on conflict (slug) do nothing
        """
    )
    # Existing DBs seeded jewelry-only — insert diamond + pin default sort order.
    for cat in DEFAULT_CATEGORIES:
        cur.execute(
            """
            insert into product_categories (slug, label_zh, label_en, sort_order, addon_price_twd)
            values (%s, %s, %s, %s, %s)
            on conflict (slug) do update set
              sort_order = excluded.sort_order,
              label_zh = excluded.label_zh,
              label_en = coalesce(product_categories.label_en, excluded.label_en),
              updated_at = now()
            """,
            (
                cat["slug"],
                cat["label_zh"],
                cat["label_en"],
                cat["sort_order"],
                int(cat.get("addon_price_twd") or 0),
            ),
        )
    # Schema initialization is also used by legacy write paths.  Invalidate
    # any snapshot before those paths commit their changes.
    clear_category_cache()


def _as_jsonb(value: Any) -> Jsonb | None:
    if value is None:
        return None
    if isinstance(value, Jsonb):
        return value
    if isinstance(value, (dict, list)):
        return Jsonb(value)
    return None


def _ring_charge_after_raw(raw: dict) -> Any:
    for key in (
        "chargeAfter",
        "charge_after",
        "priceFromSize",
        "price_from_size",
        "baseSize",
        "base_size",
    ):
        if raw.get(key) not in (None, ""):
            return raw.get(key)
    return None


def _normalize_ring_size_config(raw: Any) -> dict | None:
    """Return camelCase ringSizeConfig or None (empty/invalid → None)."""
    if raw in (None, "", {}):
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    if not isinstance(raw, dict):
        return None
    min_raw = raw.get("minSize")
    if min_raw is None:
        min_raw = raw.get("min_size")
    if min_raw is None:
        min_raw = raw.get("startSize")
    if min_raw is None:
        min_raw = raw.get("start_size")
    max_raw = raw.get("maxSize")
    if max_raw is None:
        max_raw = raw.get("max_size")
    price_raw = raw.get("pricePerSizeTwd")
    if price_raw is None:
        price_raw = raw.get("price_per_size_twd")
    charge_raw = _ring_charge_after_raw(raw)
    # Legacy sizes[] passthrough for catalog/quote fallback.
    if all(v in (None, "") for v in (min_raw, max_raw, price_raw, charge_raw)):
        if raw.get("sizes") or raw.get("startSize") is not None or raw.get("start_size") is not None:
            return dict(raw)
        return None
    try:
        min_size = int(round(float(min_raw))) if min_raw not in (None, "") else None
    except (TypeError, ValueError):
        min_size = None
    try:
        max_size = int(round(float(max_raw))) if max_raw not in (None, "") else None
    except (TypeError, ValueError):
        max_size = None
    try:
        price = float(price_raw) if price_raw not in (None, "") else 0.0
    except (TypeError, ValueError):
        price = 0.0
    if min_size is None or min_size < _RING_SIZE_MIN:
        return None
    if max_size is None:
        max_size = _RING_SIZE_DEFAULT_MAX
    elif max_size < _RING_SIZE_MIN:
        return None
    try:
        charge_after = (
            int(round(float(charge_raw))) if charge_raw not in (None, "") else min_size
        )
    except (TypeError, ValueError):
        charge_after = min_size
    if charge_after < _RING_SIZE_MIN:
        charge_after = min_size
    return {
        "minSize": min_size,
        "maxSize": max_size,
        "chargeAfter": charge_after,
        "pricePerSizeTwd": price,
        "startSize": min_size,
    }


def _serialize_row(row: dict) -> dict:
    out = dict(row)
    for key, value in out.items():
        if isinstance(value, datetime):
            out[key] = value.isoformat()
    thumb = out.get("thumb_path")
    out["thumbUrl"] = resolve_product_image_url(thumb) if thumb else None
    addon = out.get("addon_price_twd")
    try:
        addon_int = int(addon) if addon is not None else 0
    except (TypeError, ValueError):
        addon_int = 0
    out["addon_price_twd"] = max(0, addon_int)
    out["addonPrice"] = out["addon_price_twd"]
    rsc = _normalize_ring_size_config(out.pop("ring_size_config", None))
    out["ring_size_config"] = rsc
    out["ringSizeConfig"] = rsc
    return out


def fetch_categories(cur) -> list[dict]:
    global _category_cache
    now = monotonic()
    with _category_cache_lock:
        cached = _category_cache
    if cached and now - cached[0] < _CATEGORY_CACHE_TTL_SECONDS:
        return deepcopy(cached[1])

    cur.execute(
        f"select {_CATEGORY_SELECT} from product_categories order by sort_order, slug"
    )
    rows = cur.fetchall()
    if rows:
        result = [_serialize_row(dict(row)) for row in rows]
    else:
        result = [_serialize_row(dict(row)) for row in DEFAULT_CATEGORIES]
    with _category_cache_lock:
        _category_cache = (now, result)
    return deepcopy(result)


def category_labels(cur) -> dict[str, str]:
    return {row["slug"]: row["label_zh"] for row in fetch_categories(cur)}


def valid_category_slugs(cur) -> set[str]:
    return {row["slug"] for row in fetch_categories(cur)}


def category_order(cur) -> list[str]:
    return [row["slug"] for row in fetch_categories(cur)]


def build_category_meta(cur) -> dict[str, dict]:
    return build_category_meta_from_rows(fetch_categories(cur))


def build_category_meta_from_rows(rows: list[dict]) -> dict[str, dict]:
    meta: dict[str, dict] = {}
    for row in rows:
        entry = {
            "labelZh": row["label_zh"],
            "labelEn": row.get("label_en"),
            "thumbUrl": row.get("thumbUrl"),
            "addonPrice": int(row.get("addonPrice") or 0),
        }
        if row.get("slug") == "ring" and row.get("ringSizeConfig"):
            entry["ringSizeConfig"] = row["ringSizeConfig"]
        meta[row["slug"]] = entry
    return meta


def category_ring_size_config(cur, slug: str) -> dict | None:
    """Category-level ringSizeConfig for ring slug; None if unset/non-ring."""
    slug = (slug or "").strip()
    if slug != "ring":
        return None
    cur.execute(
        "select ring_size_config from product_categories where slug = %s",
        (slug,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return _normalize_ring_size_config(row.get("ring_size_config"))


def category_addon_price(cur, slug: str) -> int:
    """NT$ 品項加價 for category — replaces default labor when > 0.

    0 / unset keeps built-in labor defaults (chain s925 500 / chain other
    3000 / else 5000). Folded into labor / 金工價格 (never a separate line).
    """
    slug = (slug or "").strip()
    if not slug:
        return 0
    cur.execute(
        "select addon_price_twd from product_categories where slug = %s",
        (slug,),
    )
    row = cur.fetchone()
    if row:
        try:
            return max(0, int(row["addon_price_twd"] or 0))
        except (TypeError, ValueError):
            return 0
    for default in DEFAULT_CATEGORIES:
        if default["slug"] == slug:
            return int(default.get("addon_price_twd") or 0)
    return 0


def parse_addon_price(value) -> tuple[int | None, str | None]:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, "請填寫品項加價"
    try:
        if isinstance(value, bool):
            raise ValueError("bool")
        if isinstance(value, float):
            if not value.is_integer():
                return None, "品項加價須為整數"
            amount = int(value)
        else:
            amount = int(value)
    except (TypeError, ValueError):
        return None, "品項加價須為整數"
    if amount < 0:
        return None, "品項加價不可為負數"
    if amount > _ADDON_MAX_TWD:
        return None, "品項加價過大"
    return amount, None


def make_slug(label_zh: str, existing: set[str]) -> str:
    ascii_base = re.sub(r"[^a-z0-9]+", "-", (label_zh or "").lower()).strip("-")
    if len(ascii_base) >= 2 and ascii_base not in existing and _SLUG_RE.match(ascii_base):
        return ascii_base[:32]
    for _ in range(12):
        slug = f"cat-{uuid.uuid4().hex[:8]}"
        if slug not in existing:
            return slug
    raise ValueError("could not generate slug")


def create_category(cur, *, label_zh: str, label_en: str | None = None) -> tuple[dict | None, str | None]:
    label_zh = (label_zh or "").strip()
    if not label_zh:
        return None, "請填寫品項名稱"
    if len(label_zh) > 50:
        return None, "品項名稱過長"

    label_en = (label_en or "").strip() or None
    if label_en and len(label_en) > 80:
        return None, "英文名稱過長"

    ensure_product_categories_schema(cur)
    existing = valid_category_slugs(cur)
    slug = make_slug(label_zh, existing)

    try:
        cur.execute("select coalesce(max(sort_order), -1) + 1 as next from product_categories")
        sort_order = int(cur.fetchone()["next"])
        cur.execute(
            f"""
            insert into product_categories (slug, label_zh, label_en, sort_order, addon_price_twd)
            values (%s, %s, %s, %s, 0)
            returning {_CATEGORY_SELECT}
            """,
            (slug, label_zh, label_en, sort_order),
        )
        return _serialize_row(dict(cur.fetchone())), None
    except pg_errors.UniqueViolation:
        return None, "品項已存在（名稱或代碼重複）"
    except Exception as exc:
        msg = str(exc).strip().split("\n", 1)[0][:200]
        return None, f"新增品項失敗：{msg}" if msg else "新增品項失敗"


def delete_category(cur, slug: str) -> tuple[bool, str | None]:
    slug = (slug or "").strip()
    categories = fetch_categories(cur)
    if slug not in {row["slug"] for row in categories}:
        return False, "品項不存在"
    if len(categories) <= 1:
        return False, "至少需保留一個品項"

    cur.execute("select count(*) as c from products where category = %s", (slug,))
    in_use = int(cur.fetchone()["c"])
    if in_use > 0:
        return False, "此品項下尚有商品，請先刪除或移動商品後再刪除品項"

    cur.execute("delete from product_categories where slug = %s", (slug,))
    return True, None


def update_category_thumb(cur, slug: str, thumb_path: str) -> tuple[dict | None, str | None]:
    slug = (slug or "").strip()
    ensure_product_categories_schema(cur)
    if slug not in valid_category_slugs(cur):
        return None, "品項不存在"
    try:
        cur.execute(
            f"""
            update product_categories
            set thumb_path = %s, updated_at = %s
            where slug = %s
            returning {_CATEGORY_SELECT}
            """,
            (thumb_path, datetime.now(timezone.utc), slug),
        )
        row = cur.fetchone()
    except Exception as exc:
        msg = str(exc).strip().split("\n", 1)[0][:200]
        return None, f"更新品項圖失敗：{msg}" if msg else "更新品項圖失敗"
    if not row:
        return None, "品項不存在"
    return _serialize_row(dict(row)), None


def parse_ring_size_config(value: Any) -> tuple[dict | None, str | None]:
    """Validate category ringSizeConfig. None clears. Errors in Chinese."""
    if value in (None, "", {}):
        return None, None
    if not isinstance(value, dict):
        return None, "戒圍設定無效"
    min_raw = value.get("minSize")
    if min_raw is None:
        min_raw = value.get("min_size")
    if min_raw is None:
        min_raw = value.get("startSize")
    if min_raw is None:
        min_raw = value.get("start_size")
    max_raw = value.get("maxSize")
    if max_raw is None:
        max_raw = value.get("max_size")
    price_raw = value.get("pricePerSizeTwd")
    if price_raw is None:
        price_raw = value.get("price_per_size_twd")
    charge_raw = _ring_charge_after_raw(value)
    if all(v in (None, "") for v in (min_raw, max_raw, price_raw, charge_raw)):
        return None, None
    if min_raw in (None, ""):
        return None, "請填寫最小戒圍"
    try:
        min_size = int(round(float(min_raw)))
    except (TypeError, ValueError):
        return None, "最小戒圍無效（須為 ≥ 1 的整數）"
    if min_size < _RING_SIZE_MIN:
        return None, "最小戒圍無效（須為 ≥ 1 的整數）"
    if max_raw in (None, ""):
        max_size = _RING_SIZE_DEFAULT_MAX
    else:
        try:
            max_size = int(round(float(max_raw)))
        except (TypeError, ValueError):
            return None, "最大戒圍無效（須為 ≥ 1 的整數）"
        if max_size < _RING_SIZE_MIN:
            return None, "最大戒圍無效（須為 ≥ 1 的整數）"
    if min_size > max_size:
        return None, "最小戒圍不可大於最大戒圍"
    if charge_raw in (None, ""):
        charge_after = min_size
    else:
        try:
            charge_after = int(round(float(charge_raw)))
        except (TypeError, ValueError):
            return None, "從多少之後開始加價無效（須為 ≥ 1 的整數）"
        if charge_after < _RING_SIZE_MIN:
            return None, "從多少之後開始加價無效（須為 ≥ 1 的整數）"
        if charge_after < min_size or charge_after > max_size:
            return None, "從多少之後開始加價須在最小與最大之間"
    if price_raw in (None, ""):
        price = 0.0
    else:
        try:
            price = float(price_raw)
        except (TypeError, ValueError):
            return None, "加多少無效"
        if price < 0:
            return None, "加多少不可為負"
    return {
        "minSize": min_size,
        "maxSize": max_size,
        "chargeAfter": charge_after,
        "pricePerSizeTwd": price,
        "startSize": min_size,
    }, None


def update_category_addon(cur, slug: str, addon_price_twd: int) -> tuple[dict | None, str | None]:
    slug = (slug or "").strip()
    amount, err = parse_addon_price(addon_price_twd)
    if err:
        return None, err
    try:
        ensure_product_categories_schema(cur)
        if slug not in valid_category_slugs(cur):
            return None, "品項不存在"
        cur.execute(
            f"""
            update product_categories
            set addon_price_twd = %s, updated_at = %s
            where slug = %s
            returning {_CATEGORY_SELECT}
            """,
            (amount, datetime.now(timezone.utc), slug),
        )
        row = cur.fetchone()
    except Exception as exc:
        msg = str(exc).strip().split("\n", 1)[0][:200]
        return None, f"更新品項加價失敗：{msg}" if msg else "更新品項加價失敗"
    if not row:
        return None, "品項不存在"
    return _serialize_row(dict(row)), None


def update_category_ring_size(
    cur, slug: str, ring_size_config: Any
) -> tuple[dict | None, str | None]:
    """Save ringSizeConfig on category (ring only). None clears."""
    slug = (slug or "").strip()
    if slug != "ring":
        return None, "僅戒指品項可設定戒圍"
    parsed, err = parse_ring_size_config(ring_size_config)
    if err:
        return None, err
    try:
        ensure_product_categories_schema(cur)
        if slug not in valid_category_slugs(cur):
            return None, "品項不存在"
        cur.execute(
            f"""
            update product_categories
            set ring_size_config = %s, updated_at = %s
            where slug = %s
            returning {_CATEGORY_SELECT}
            """,
            (_as_jsonb(parsed), datetime.now(timezone.utc), slug),
        )
        row = cur.fetchone()
    except Exception as exc:
        msg = str(exc).strip().split("\n", 1)[0][:200]
        return None, f"更新戒圍設定失敗：{msg}" if msg else "更新戒圍設定失敗"
    if not row:
        return None, "品項不存在"
    return _serialize_row(dict(row)), None


def update_category_fields(
    cur,
    slug: str,
    *,
    addon_price_twd: Any = ...,
    ring_size_config: Any = ...,
) -> tuple[dict | None, str | None]:
    """Patch addon and/or ringSizeConfig. Ellipsis means leave unchanged."""
    slug = (slug or "").strip()
    category: dict | None = None
    if addon_price_twd is not ...:
        category, err = update_category_addon(cur, slug, addon_price_twd)
        if err:
            return None, err
    if ring_size_config is not ...:
        category, err = update_category_ring_size(cur, slug, ring_size_config)
        if err:
            return None, err
    if category is None:
        return None, "缺少更新欄位"
    return category, None


def overwrite_variant_addons(cur, slug: str, amount: int) -> tuple[int, str | None]:
    """Force-set every product_variants.addon_price_twd in category to amount."""
    slug = (slug or "").strip()
    try:
        cur.execute(
            """
            update product_variants
            set addon_price_twd = %s
            where product_id in (
              select id from products where category = %s
            )
            """,
            (amount, slug),
        )
        count = cur.rowcount if cur.rowcount is not None else 0
        return max(0, int(count)), None
    except Exception as exc:
        msg = str(exc).strip().split("\n", 1)[0][:200]
        return 0, f"覆蓋款式加價失敗：{msg}" if msg else "覆蓋款式加價失敗"


def force_overwrite_category_addon(
    cur, slug: str, addon_price_twd: int
) -> tuple[dict | None, int, str | None]:
    """Save category 品項加價 and overwrite all variant rows in that category."""
    category, err = update_category_addon(cur, slug, addon_price_twd)
    if err or not category:
        return None, 0, err or "品項不存在"
    amount = int(category["addon_price_twd"])
    count, err = overwrite_variant_addons(cur, slug, amount)
    if err:
        return None, 0, err
    return category, count, None
