"""Move shop-media product keys into type-scoped folders and rewrite DB URLs.

Target layout:
  products/{category}/{name_slug}/{metal}/file
  products/_pending/{category}/{metal}/file

Categories: pendant, ring, earring, bracelet, chain (products.category).

Migrates:
  - legacy flat `products/{file}`
  - legacy nested `products/{product_uuid}/…` or `products/{slug}/…`
  - legacy pending `products/_pending/{metal}/file`
  - slug-only nested keys missing the category prefix
  - short-id folders when name_en was empty

Folder slug: from `name_en` (admin 英文名稱). Empty/CJK → short product id.
Does not auto-translate or fill `name_en`.

Leaves page-images/, site-images/, and local shop-product disk stock alone.
Shared URLs (multiple product_images rows) are copied; unshared URLs are moved.
DB rows update only after a successful Storage copy/move.

Usage:
  python scripts/reorganize_supabase_product_images.py --dry-run
  SUPABASE_ALLOW_LIVE_MIGRATE=1 python scripts/reorganize_supabase_product_images.py
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.database import get_connection  # noqa: E402
from app.storage import (  # noqa: E402
    StorageNotConfiguredError,
    StorageUploadError,
    _nested_product_tail_parts,
    _pending_key_parts,
    copy_object,
    english_label_for_folder,
    is_flat_product_object_key,
    is_nested_product_object_key,
    is_pending_product_object_key,
    metal_color_from_slot,
    move_object,
    normalize_product_category,
    object_path_from_public_url,
    pending_product_object_key,
    product_category_from_object_key,
    product_folder_from_object_key,
    product_folder_segment,
    product_object_key,
)
from config.settings import settings  # noqa: E402


def _list_product_prefix_keys(prefix: str = "products/", *, limit: int = 1000) -> list[str]:
    """List object names under prefix via Storage list API (best-effort)."""
    import httpx

    from app.storage import _require_config, _storage_headers

    base, key, bucket = _require_config()
    url = f"{base}/storage/v1/object/list/{bucket}"
    headers = _storage_headers(key, content_type="application/json")
    keys: list[str] = []
    offset = 0
    with httpx.Client(timeout=60.0) as client:
        while True:
            payload = {
                "prefix": prefix,
                "limit": limit,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"},
            }
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                print(f"  warn: list failed ({resp.status_code}): {(resp.text or '')[:160]}")
                break
            batch = resp.json() or []
            if not batch:
                break
            for item in batch:
                name = (item.get("name") or "").strip()
                if not name:
                    continue
                if name.startswith("products/"):
                    keys.append(name)
                else:
                    keys.append(f"{prefix.rstrip('/')}/{name}".replace("//", "/"))
            if len(batch) < limit:
                break
            offset += limit
    return keys


def _load_products(cur) -> dict[str, dict]:
    cur.execute("select id, name_en, name_zh, category from products")
    return {str(row["id"]): dict(row) for row in cur.fetchall()}


def _folder_map(products: dict[str, dict]) -> dict[str, str]:
    """product_id → folder segment with collision suffixes."""
    tentative: dict[str, str] = {
        pid: product_folder_segment(row.get("name_en"), pid, collide=False)
        for pid, row in products.items()
    }
    by_folder: dict[str, list[str]] = defaultdict(list)
    for pid, folder in tentative.items():
        by_folder[folder].append(pid)
    folders: dict[str, str] = {}
    for pid, row in products.items():
        collide = len(by_folder[tentative[pid]]) > 1
        folders[pid] = product_folder_segment(
            row.get("name_en"),
            pid,
            collide=collide,
        )
    return folders


def _url_refcount(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        url = str(row.get("file_path") or "").strip()
        if url:
            counts[url] += 1
    return counts


def _product_category(products: dict[str, dict], product_id: str) -> str | None:
    prow = products.get(product_id) or {}
    return normalize_product_category(prow.get("category"))


def _dest_for_row(
    obj: str,
    *,
    products: dict[str, dict],
    folders: dict[str, str],
    product_id: str,
    color_slot: str | None,
) -> str | None:
    """Compute target Storage key for a product_images row; None → skip."""
    prow = products.get(product_id) or {}
    folder = folders.get(product_id) or product_folder_segment(
        prow.get("name_en"),
        product_id,
    )
    category = _product_category(products, product_id)
    slot_metal = metal_color_from_slot(color_slot)

    if is_pending_product_object_key(obj):
        pending_cat, pending_metal, filename = _pending_key_parts(obj)
        if not filename:
            return None
        metal = slot_metal or pending_metal
        dest_cat = category or pending_cat
        try:
            return pending_product_object_key(metal, filename, category=dest_cat)
        except StorageUploadError:
            return None

    metal = slot_metal
    filename: str | None = None

    if is_flat_product_object_key(obj):
        filename = obj.rsplit("/", 1)[-1]
    elif is_nested_product_object_key(obj):
        current_folder = product_folder_from_object_key(obj)
        current_cat = product_category_from_object_key(obj)
        tail_metal, tail_file = _nested_product_tail_parts(obj)
        if not tail_file:
            return None
        filename = tail_file
        metal = metal or tail_metal
        if current_folder == folder and current_cat == category:
            return obj
    else:
        return None

    if not filename:
        return None
    try:
        return product_object_key(folder, metal, filename, category=category)
    except StorageUploadError:
        return None


def _print_folder_plan(
    products: dict[str, dict],
    folders: dict[str, str],
    image_rows: list[dict],
) -> list[tuple[str, str, str, str, str | None]]:
    """Print and return (old_key, new_key, name_zh, english_label, category) moves."""
    plan: list[tuple[str, str, str, str, str | None]] = []
    seen: set[tuple[str, str]] = set()
    print("-- path plan (old → new | category | name_zh | english)")
    for row in image_rows:
        url = str(row.get("file_path") or "").strip()
        obj = object_path_from_public_url(url)
        if not obj:
            continue
        pid = str(row["product_id"])
        dest = _dest_for_row(
            obj,
            products=products,
            folders=folders,
            product_id=pid,
            color_slot=row.get("color"),
        )
        if not dest or dest == obj:
            continue
        key = (obj, dest)
        if key in seen:
            continue
        seen.add(key)
        prow = products.get(pid) or {}
        zh = (prow.get("name_zh") or "").strip()
        label = english_label_for_folder(prow.get("name_en"))
        cat = _product_category(products, pid)
        plan.append((obj, dest, zh, label, cat))
        print(f"  {obj} → {dest} | {cat or '?'} | {zh} | {label}")
    return plan


def migrate_product_image_folders(*, dry_run: bool) -> tuple[int, int, int]:
    """Return (moved_or_would_move, db_updated, skipped)."""
    moved = 0
    skipped = 0
    db_updated = 0
    with get_connection() as conn, conn.cursor() as cur:
        products = _load_products(cur)
        folders = _folder_map(products)
        cur.execute(
            """
            select id, product_id, color, file_path
            from product_images
            where file_path is not null and btrim(file_path) <> ''
            """
        )
        rows = [dict(r) for r in cur.fetchall()]
        _print_folder_plan(products, folders, rows)
        print()
        refcounts = _url_refcount(rows)

        for row in rows:
            url = str(row["file_path"]).strip()
            obj = object_path_from_public_url(url)
            if not obj:
                skipped += 1
                continue

            product_id = str(row["product_id"])
            dest = _dest_for_row(
                obj,
                products=products,
                folders=folders,
                product_id=product_id,
                color_slot=row.get("color"),
            )
            if not dest or dest == obj:
                skipped += 1
                continue

            shared = refcounts.get(url, 0) > 1
            action = "copy" if shared else "move"
            print(f"  {action}: {obj} -> {dest}")
            if dry_run:
                moved += 1
                continue
            try:
                if shared:
                    new_url = copy_object(obj, dest)
                else:
                    new_url = move_object(obj, dest)
            except (StorageNotConfiguredError, StorageUploadError) as exc:
                print(f"  {action} failed {obj}: {exc}")
                skipped += 1
                continue
            cur.execute(
                "update product_images set file_path = %s where id = %s",
                (new_url, row["id"]),
            )
            refcounts[url] = max(0, refcounts.get(url, 1) - 1)
            refcounts[new_url] = refcounts.get(new_url, 0) + 1
            moved += 1
            db_updated += 1
        if not dry_run:
            conn.commit()
    return moved, db_updated, skipped


def _db_object_keys() -> set[str]:
    found: set[str] = set()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select file_path from product_images "
            "where file_path is not null and btrim(file_path) <> ''"
        )
        for row in cur.fetchall():
            obj = object_path_from_public_url(str(row["file_path"]).strip())
            if obj:
                found.add(obj)
    return found


def _is_legacy_product_key(key: str) -> bool:
    """True when key is not yet type-scoped (missing category segment)."""
    if is_flat_product_object_key(key):
        return True
    if is_pending_product_object_key(key):
        _cat, _metal, filename = _pending_key_parts(key)
        return bool(filename) and _cat is None
    if is_nested_product_object_key(key):
        return product_category_from_object_key(key) is None
    return False


def count_legacy_storage_keys() -> tuple[int, int]:
    """Count legacy Storage keys with no DB ref (flat + slug-only nested/pending)."""
    try:
        keys = _list_product_prefix_keys("products/")
    except StorageNotConfiguredError:
        return 0, 0
    db_keys = _db_object_keys()
    orphan = 0
    legacy_in_db = 0
    seen: set[str] = set()
    for key in keys:
        norm = key.strip("/")
        if norm in seen:
            continue
        seen.add(norm)
        if not _is_legacy_product_key(key):
            continue
        if norm in db_keys:
            legacy_in_db += 1
            continue
        orphan += 1
        print(f"  orphan legacy (left in place): {norm}")
    return orphan, legacy_in_db


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview moves and URL rewrites without changing Storage or DB",
    )
    parser.add_argument(
        "--skip-orphan-scan",
        action="store_true",
        help="Do not list Storage for unreferenced flat products/* keys",
    )
    args = parser.parse_args()

    print("=== reorganize Supabase product images (type + slug folders) ===")
    if args.dry_run:
        print("DRY RUN — no Storage moves or DB updates\n")

    try:
        from app.storage import _require_config

        base, _, bucket = _require_config()
        print(f"target: {base}/storage/v1/object/public/{bucket}/\n")
    except StorageNotConfiguredError as exc:
        print(f"ERROR: {exc}")
        return 1

    host = (settings.supabase_url or "").lower()
    if not args.dry_run and host and "localhost" not in host and "127.0.0.1" not in host:
        if os.environ.get("SUPABASE_ALLOW_LIVE_MIGRATE", "").strip() != "1":
            print(
                "Refusing live migrate against remote Supabase.\n"
                "Re-run with --dry-run, or set SUPABASE_ALLOW_LIVE_MIGRATE=1 "
                "if you intentionally target this project."
            )
            return 2

    moved, db_updated, skipped = migrate_product_image_folders(dry_run=args.dry_run)
    label = "would move/copy" if args.dry_run else "moved/copied"
    print(f"\n{label} {moved} image(s); skipped {skipped}")
    if not args.dry_run:
        print(f"DB rows updated: {db_updated}")

    if not args.skip_orphan_scan:
        print("\n-- legacy products/* scan (no category prefix)")
        orphans, legacy_db = count_legacy_storage_keys()
        print(f"orphan legacy keys (no DB ref): {orphans}")
        print(f"legacy keys still referenced in DB (re-run if >0): {legacy_db}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
