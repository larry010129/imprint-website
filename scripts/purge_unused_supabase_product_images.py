"""Delete unreferenced shop-media objects under products/.

Lists Storage keys under products/, compares to product_images.file_path, and
deletes objects with zero DB references. Never touches page-images/, site-images/,
banners, or other prefixes.

Usage:
  python scripts/purge_unused_supabase_product_images.py --dry-run
  SUPABASE_ALLOW_LIVE_PURGE=1 python scripts/purge_unused_supabase_product_images.py
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

from app.database import get_connection  # noqa: E402
from app.storage import (  # noqa: E402
    StorageNotConfiguredError,
    delete_by_url,
    object_path_from_public_url,
    public_url_for_object,
)
from config.settings import settings  # noqa: E402

PRODUCTS_PREFIX = "products/"
_LIST_LIMIT = 1000


def referenced_product_object_keys(cur) -> set[str]:
    """Object keys under products/ still referenced by product_images."""
    cur.execute(
        "select file_path, previous_file_path from product_images"
    )
    found: set[str] = set()
    for row in cur.fetchall():
        for key in ("file_path", "previous_file_path"):
            raw = str(row.get(key) or "").strip()
            if not raw:
                continue
            obj = object_path_from_public_url(raw)
            if obj and obj.startswith(PRODUCTS_PREFIX):
                found.add(obj)
    return found


def _normalize_listed_key(prefix: str, name: str) -> str:
    name = (name or "").strip().strip("/")
    if not name:
        return ""
    if name.startswith(PRODUCTS_PREFIX):
        return name
    base = prefix.rstrip("/")
    return f"{base}/{name}".replace("//", "/")


def _is_folder_list_entry(item: dict) -> bool:
    """Supabase folders usually have id=null and no metadata."""
    if item.get("id") is None and not item.get("metadata"):
        return True
    name = (item.get("name") or "").strip()
    return name.endswith("/")


def list_product_object_keys(*, limit: int = _LIST_LIMIT) -> list[str]:
    """Recursively list file object keys under products/."""
    import httpx

    from app.storage import _require_config, _storage_headers

    base, key, bucket = _require_config()
    url = f"{base}/storage/v1/object/list/{bucket}"
    headers = _storage_headers(key, content_type="application/json")
    keys: list[str] = []
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
                    walk(client, full.rstrip("/") + "/")
                    continue
                seen.add(full)
                keys.append(full)
            if len(batch) < limit:
                return
            offset += limit

    with httpx.Client(timeout=60.0) as client:
        walk(client, PRODUCTS_PREFIX)
    return keys


def orphan_product_keys(
    storage_keys: list[str] | set[str],
    referenced: set[str],
) -> list[str]:
    """Keys under products/ present in Storage but not in referenced set."""
    orphans: list[str] = []
    seen: set[str] = set()
    for raw in storage_keys:
        key = (raw or "").strip().lstrip("/")
        if not key.startswith(PRODUCTS_PREFIX) or key in seen:
            continue
        # Skip bare folder markers if any slipped through.
        if key.endswith("/") or key == "products":
            continue
        seen.add(key)
        if key not in referenced:
            orphans.append(key)
    orphans.sort()
    return orphans


def purge_unused_product_images(*, dry_run: bool) -> tuple[int, int, int]:
    """Return (would_delete_or_deleted, kept_referenced, list_total)."""
    with get_connection() as conn, conn.cursor() as cur:
        referenced = referenced_product_object_keys(cur)
    storage_keys = list_product_object_keys()
    orphans = orphan_product_keys(storage_keys, referenced)
    kept = len(storage_keys) - len(orphans)
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
    return deleted, kept, len(storage_keys)


def _live_allowed() -> bool:
    migrate = os.environ.get("SUPABASE_ALLOW_LIVE_MIGRATE", "").strip() == "1"
    purge = os.environ.get("SUPABASE_ALLOW_LIVE_PURGE", "").strip() == "1"
    return migrate or purge


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletions without removing Storage objects",
    )
    args = parser.parse_args()

    print("=== purge unused Supabase product images ===")
    if args.dry_run:
        print("DRY RUN — no Storage deletes\n")

    try:
        from app.storage import _require_config

        base, _, bucket = _require_config()
        print(f"target: {base}/storage/v1/object/public/{bucket}/\n")
    except StorageNotConfiguredError as exc:
        print(f"ERROR: {exc}")
        return 1

    host = (settings.supabase_url or "").lower()
    remote = host and "localhost" not in host and "127.0.0.1" not in host
    if not args.dry_run and remote and not _live_allowed():
        print(
            "Refusing live purge against remote Supabase.\n"
            "Re-run with --dry-run, or set SUPABASE_ALLOW_LIVE_PURGE=1 "
            "(or SUPABASE_ALLOW_LIVE_MIGRATE=1) if you intentionally target "
            "this project."
        )
        return 2

    deleted, kept, total = purge_unused_product_images(dry_run=args.dry_run)
    label = "would delete" if args.dry_run else "deleted"
    print(f"\n{label} {deleted}; kept {kept}; listed {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
