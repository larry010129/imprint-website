"""Move shop-media product keys into products/{name_slug}/{metal}/ and rewrite DB URLs.

Migrates:
  - legacy flat `products/{file}`
  - legacy nested `products/{product_uuid}/…`
  - short-id folders when name_en was empty
  - any nested folder that does not match the current name slug

Folder slug: from `name_en` (admin 英文名稱). Empty/CJK → short product id.
Does not auto-translate or fill `name_en`.

Leaves `products/_pending/…`, page-images/, site-images/, and local shop-product
disk stock alone. Shared URLs (multiple product_images rows) are copied; unshared
URLs are moved.

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
    copy_object,
    english_label_for_folder,
    is_flat_product_object_key,
    is_nested_product_object_key,
    is_pending_product_object_key,
    metal_color_from_slot,
    move_object,
    object_path_from_public_url,
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
    cur.execute("select id, name_en, name_zh from products")
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


def _print_folder_plan(
    products: dict[str, dict],
    folders: dict[str, str],
    image_rows: list[dict],
) -> list[tuple[str, str, str, str]]:
    """Print and return (old_folder, new_folder, name_zh, english_label) unique moves."""
    old_by_pid: dict[str, set[str]] = defaultdict(set)
    for row in image_rows:
        obj = object_path_from_public_url(str(row.get("file_path") or "").strip())
        if not obj or is_pending_product_object_key(obj):
            continue
        current = product_folder_from_object_key(obj)
        if current:
            old_by_pid[str(row["product_id"])].add(current)

    plan: list[tuple[str, str, str, str]] = []
    print("-- folder plan (old → new | name_zh | english)")
    for pid, new_folder in sorted(folders.items(), key=lambda x: x[1]):
        row = products.get(pid) or {}
        zh = (row.get("name_zh") or "").strip()
        label = english_label_for_folder(row.get("name_en"))
        olds = sorted(old_by_pid.get(pid) or [])
        if not olds:
            print(f"  (no images) → {new_folder} | {zh} | {label}")
            continue
        for old in olds:
            if old == new_folder:
                continue
            plan.append((old, new_folder, zh, label))
            print(f"  {old} → {new_folder} | {zh} | {label}")
    return plan


def migrate_product_image_folders(*, dry_run: bool) -> tuple[int, int]:
    """Return (moved_or_would_move, skipped)."""
    moved = 0
    skipped = 0
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
            if not obj or is_pending_product_object_key(obj):
                skipped += 1
                continue

            product_id = str(row["product_id"])
            prow = products.get(product_id) or {}
            folder = folders.get(product_id) or product_folder_segment(
                prow.get("name_en"),
                product_id,
            )
            metal = metal_color_from_slot(row.get("color"))

            if is_flat_product_object_key(obj):
                filename = obj.rsplit("/", 1)[-1]
            elif is_nested_product_object_key(obj):
                current = product_folder_from_object_key(obj)
                if current == folder:
                    skipped += 1
                    continue
                parts = [p for p in obj.split("/") if p]
                filename = parts[-1]
                if len(parts) == 4 and parts[2] in {"white", "yellow", "rose"}:
                    metal = metal or parts[2]
            else:
                skipped += 1
                continue

            try:
                dest = product_object_key(folder, metal, filename)
            except StorageUploadError as exc:
                print(f"  skip bad dest for row {row['id']}: {exc}")
                skipped += 1
                continue
            if dest == obj:
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
            # After rewrite, old URL has one fewer ref for later shared decisions.
            refcounts[url] = max(0, refcounts.get(url, 1) - 1)
            refcounts[new_url] = refcounts.get(new_url, 0) + 1
            moved += 1
        if not dry_run:
            conn.commit()
    return moved, skipped


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


def count_orphan_flat_keys() -> int:
    """Count flat products/{file} keys in Storage with no product_images URL."""
    try:
        keys = _list_product_prefix_keys("products/")
    except StorageNotConfiguredError:
        return 0
    db_keys = _db_object_keys()
    orphan = 0
    seen: set[str] = set()
    for key in keys:
        parts = [p for p in key.strip("/").split("/") if p]
        if len(parts) == 2 and parts[0] == "products" and parts[1] != "_pending":
            flat = f"products/{parts[1]}"
        elif is_flat_product_object_key(key):
            flat = key.strip("/")
        else:
            continue
        if flat in seen or flat in db_keys:
            continue
        seen.add(flat)
        orphan += 1
        print(f"  orphan flat (left in place): {flat}")
    return orphan


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

    print("=== reorganize Supabase product images (name slug folders) ===")
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

    moved, skipped = migrate_product_image_folders(dry_run=args.dry_run)
    label = "would move/copy" if args.dry_run else "moved/copied"
    print(f"\n{label} {moved} image(s); skipped {skipped}")

    if not args.skip_orphan_scan:
        print("\n-- orphan flat products/* scan (leave in place)")
        orphans = count_orphan_flat_keys()
        print(f"orphan flat keys: {orphans}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
