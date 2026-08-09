"""Ensure shop-media page-images/ has per-tab English folder prefixes.

Creates ``page-images/{folder}/.keep`` (upsert) for every folder in
PAGE_IMAGE_STORAGE_FOLDERS. Optionally deletes unreferenced flat orphans
``page-images/{file}`` (never nested keys).

Usage:
  python scripts/ensure_page_image_storage_folders.py --dry-run
  SUPABASE_ALLOW_LIVE_MIGRATE=1 python scripts/ensure_page_image_storage_folders.py --apply
  SUPABASE_ALLOW_LIVE_PURGE=1 python scripts/ensure_page_image_storage_folders.py --apply --purge-orphans
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.content import ensure_page_images_schema  # noqa: E402
from app.database import get_connection  # noqa: E402
from app.page_image_slots import PAGE_IMAGE_STORAGE_FOLDERS  # noqa: E402
from app.storage import (  # noqa: E402
    StorageNotConfiguredError,
    StorageUploadError,
    delete_by_url,
    is_flat_page_image_object_key,
    object_path_from_public_url,
    public_url_for_object,
    upload_bytes,
)
from config.settings import settings  # noqa: E402

PAGE_IMAGES_PREFIX = "page-images/"
KEEP_NAME = ".keep"
_LIST_LIMIT = 1000
_URL_COLUMNS = (
    "image_url",
    "image_webp",
    "default_image_url",
    "default_image_webp",
)

REQUIRED_FOLDERS = sorted(set(PAGE_IMAGE_STORAGE_FOLDERS.values()))


def _normalize_listed_key(prefix: str, name: str) -> str:
    name = (name or "").strip().strip("/")
    if not name:
        return ""
    if name.startswith(PAGE_IMAGES_PREFIX):
        return name
    base = prefix.rstrip("/")
    return f"{base}/{name}".replace("//", "/")


def _is_folder_list_entry(item: dict) -> bool:
    if item.get("id") is None and not item.get("metadata"):
        return True
    name = (item.get("name") or "").strip()
    return name.endswith("/")


def list_page_image_entries(*, limit: int = _LIST_LIMIT) -> tuple[list[str], set[str]]:
    """Return (file_keys, folder_prefixes) under page-images/."""
    import httpx

    from app.storage import _require_config, _storage_headers

    base, key, bucket = _require_config()
    url = f"{base}/storage/v1/object/list/{bucket}"
    headers = _storage_headers(key, content_type="application/json")
    keys: list[str] = []
    folders: set[str] = set()
    seen: set[str] = set()

    def walk(client: httpx.Client, prefix: str) -> None:
        offset = 0
        while True:
            payload = {
                "prefix": prefix,
                "limit": limit,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"},
            }
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                print(
                    f"  warn: list failed ({resp.status_code}): "
                    f"{(resp.text or '')[:160]}"
                )
                return
            batch = resp.json() or []
            if not batch:
                return
            for item in batch:
                name = (item.get("name") or "").strip()
                if not name or name in {".emptyFolderPlaceholder"}:
                    continue
                full = _normalize_listed_key(prefix, name)
                if not full or full in seen:
                    continue
                if _is_folder_list_entry(item):
                    seen.add(full)
                    folder = full.rstrip("/").removeprefix(PAGE_IMAGES_PREFIX.rstrip("/")).strip("/")
                    # Only first-level folders under page-images/
                    if folder and "/" not in folder:
                        folders.add(folder)
                    walk(client, full.rstrip("/") + "/")
                    continue
                seen.add(full)
                keys.append(full)
                # Nested file implies its folder prefix exists
                rest = full.removeprefix(PAGE_IMAGES_PREFIX)
                parts = [p for p in rest.split("/") if p]
                if len(parts) >= 2:
                    folders.add(parts[0])
            if len(batch) < limit:
                return
            offset += limit

    with httpx.Client(timeout=60.0) as client:
        walk(client, PAGE_IMAGES_PREFIX)
    keys.sort()
    return keys, folders


def referenced_page_image_keys(cur) -> set[str]:
    ensure_page_images_schema(cur)
    cur.execute(
        """
        select image_url, image_webp, default_image_url, default_image_webp
        from page_images
        """
    )
    found: set[str] = set()
    for row in cur.fetchall():
        for col in _URL_COLUMNS:
            raw = str(row.get(col) or "").strip()
            if not raw:
                continue
            obj = object_path_from_public_url(raw)
            if obj and obj.startswith(PAGE_IMAGES_PREFIX):
                found.add(obj)
    return found


def flat_orphan_keys(storage_keys: list[str], referenced: set[str]) -> list[str]:
    orphans: list[str] = []
    for key in storage_keys:
        if not is_flat_page_image_object_key(key):
            continue
        # Never treat folder markers as purge targets unless flat + unreferenced
        if key.endswith(f"/{KEEP_NAME}") or key.endswith("/.emptyFolderPlaceholder"):
            continue
        if key not in referenced:
            orphans.append(key)
    return orphans


def ensure_folders(*, dry_run: bool, missing: list[str]) -> int:
    created = 0
    for folder in missing:
        rel = f"{folder}/{KEEP_NAME}"
        obj = f"{PAGE_IMAGES_PREFIX}{rel}"
        label = "would create" if dry_run else "create"
        print(f"  {label}: {obj}")
        if dry_run:
            created += 1
            continue
        try:
            upload_bytes(
                "page-images",
                rel,
                b"\n",
                "text/plain",
                upsert=True,
            )
            created += 1
        except (StorageNotConfiguredError, StorageUploadError) as exc:
            print(f"  fail {obj}: {exc}")
    return created


def purge_flat_orphans(*, dry_run: bool, orphans: list[str]) -> int:
    deleted = 0
    for key in orphans:
        label = "would delete" if dry_run else "delete"
        print(f"  {label}: {key}")
        if dry_run:
            deleted += 1
            continue
        try:
            url = public_url_for_object(key)
        except Exception as exc:
            print(f"  skip bad key {key}: {exc}")
            continue
        if delete_by_url(url):
            deleted += 1
        else:
            print(f"  warn: delete failed: {key}")
    return deleted


def _summarize(keys: list[str], folders: set[str]) -> None:
    flat = [k for k in keys if is_flat_page_image_object_key(k)]
    nested = [k for k in keys if not is_flat_page_image_object_key(k)]
    print(f"  files: {len(keys)} (flat={len(flat)}, nested={len(nested)})")
    print(f"  folder prefixes present: {sorted(folders) or '(none)'}")
    missing = [f for f in REQUIRED_FOLDERS if f not in folders]
    print(f"  required folders: {REQUIRED_FOLDERS}")
    print(f"  missing folders: {missing or '(none)'}")
    if flat:
        print(f"  flat sample ({min(10, len(flat))}):")
        for k in flat[:10]:
            print(f"    {k}")


def _live_allowed(*, purge: bool) -> bool:
    migrate = os.environ.get("SUPABASE_ALLOW_LIVE_MIGRATE", "").strip() == "1"
    live_purge = os.environ.get("SUPABASE_ALLOW_LIVE_PURGE", "").strip() == "1"
    if purge:
        return migrate or live_purge
    return migrate or live_purge


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only (default when --apply omitted)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Upload .keep placeholders (and purge if flagged)",
    )
    parser.add_argument(
        "--purge-orphans",
        action="store_true",
        help="Also delete unreferenced flat page-images/{file} keys",
    )
    args = parser.parse_args()
    dry_run = not args.apply
    if args.dry_run and args.apply:
        print("ERROR: use either --dry-run or --apply, not both")
        return 1

    print("=== ensure Supabase page-images folder prefixes ===")
    if dry_run:
        print("DRY RUN — no Storage writes or deletes\n")

    try:
        from app.storage import _require_config

        base, _, bucket = _require_config()
        print(f"target: {base}/storage/v1/object/public/{bucket}/\n")
    except StorageNotConfiguredError as exc:
        print(f"ERROR: {exc}")
        return 1

    host = (settings.supabase_url or "").lower()
    remote = host and "localhost" not in host and "127.0.0.1" not in host
    if not dry_run and remote and not _live_allowed(purge=args.purge_orphans):
        print(
            "Refusing live Storage writes against remote Supabase.\n"
            "Re-run without --apply (dry-run default), or set "
            "SUPABASE_ALLOW_LIVE_MIGRATE=1 (placeholders) and/or "
            "SUPABASE_ALLOW_LIVE_PURGE=1 (orphan deletes) with --apply."
        )
        return 2

    print("--- BEFORE ---")
    keys_before, folders_before = list_page_image_entries()
    _summarize(keys_before, folders_before)
    missing = [f for f in REQUIRED_FOLDERS if f not in folders_before]

    print("\n--- ENSURE FOLDERS ---")
    created = ensure_folders(dry_run=dry_run, missing=missing)
    print(f"placeholders: {created}")

    purged = 0
    if args.purge_orphans:
        print("\n--- PURGE FLAT ORPHANS ---")
        with get_connection() as conn, conn.cursor() as cur:
            referenced = referenced_page_image_keys(cur)
        # Re-list after creates when applying so we don't confuse state
        keys_for_purge = keys_before if dry_run else list_page_image_entries()[0]
        orphans = flat_orphan_keys(keys_for_purge, referenced)
        print(f"referenced page-images keys: {len(referenced)}")
        print(f"flat orphans: {len(orphans)}")
        purged = purge_flat_orphans(dry_run=dry_run, orphans=orphans)

    print("\n--- AFTER ---")
    if dry_run:
        folders_after = set(folders_before) | set(missing)
        keys_after = list(keys_before)
        for folder in missing:
            keys_after.append(f"{PAGE_IMAGES_PREFIX}{folder}/{KEEP_NAME}")
        if args.purge_orphans:
            with get_connection() as conn, conn.cursor() as cur:
                referenced = referenced_page_image_keys(cur)
            drop = set(flat_orphan_keys(keys_before, referenced))
            keys_after = [k for k in keys_after if k not in drop]
        _summarize(sorted(keys_after), folders_after)
        print("(projected — dry-run)")
    else:
        keys_after, folders_after = list_page_image_entries()
        _summarize(keys_after, folders_after)

    still_missing = [f for f in REQUIRED_FOLDERS if f not in folders_after]
    print(
        f"\ncreated/would-create {created}; "
        f"purged/would-purge {purged}; "
        f"still missing {still_missing or '(none)'}"
    )
    return 1 if still_missing and not dry_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
