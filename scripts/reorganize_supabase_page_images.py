"""Move flat shop-media page-images keys into per-page English folders.

Target layout:
  page-images/{english-folder}/{file}.webp

Folders map from admin「內容與頁面圖片」→「頁面圖片」tab labels
(see PAGE_IMAGE_STORAGE_FOLDERS in app/page_image_slots.py).

Migrates:
  - legacy flat ``page-images/{uuid}.webp`` (and other flat filenames)
  - rewrites page_images URL columns after successful Storage move/copy

Leaves products/, banners/, cms-media/, and already-nested page-images alone.
Shared URLs (multiple columns/rows) are copied; unshared URLs are moved.
DB rows update only after a successful Storage copy/move.

Usage:
  python scripts/reorganize_supabase_page_images.py
  python scripts/reorganize_supabase_page_images.py --dry-run
  SUPABASE_ALLOW_LIVE_MIGRATE=1 python scripts/reorganize_supabase_page_images.py --apply
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

from app.content import ensure_page_images_schema  # noqa: E402
from app.database import get_connection  # noqa: E402
from app.page_image_slots import page_image_storage_folder  # noqa: E402
from app.storage import (  # noqa: E402
    StorageNotConfiguredError,
    StorageUploadError,
    copy_object,
    is_flat_page_image_object_key,
    move_object,
    object_path_from_public_url,
    page_image_object_key,
    public_url_for_object,
)
from config.settings import settings  # noqa: E402

_URL_COLUMNS = (
    "image_url",
    "image_webp",
    "default_image_url",
    "default_image_webp",
)


def _basename(object_path: str) -> str:
    parts = [p for p in object_path.strip().strip("/").split("/") if p]
    return parts[-1] if parts else ""


def _dest_for_flat(obj: str, page_key: str) -> str | None:
    if not is_flat_page_image_object_key(obj):
        return None
    filename = _basename(obj)
    if not filename:
        return None
    folder = page_image_storage_folder(page_key)
    return page_image_object_key(folder, filename)


def _url_refcount(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        for col in _URL_COLUMNS:
            url = str(row.get(col) or "").strip()
            if url:
                counts[url] += 1
    return counts


def migrate_page_image_folders(*, dry_run: bool) -> tuple[int, int, int]:
    """Return (moved_or_would_move, db_updated, skipped)."""
    moved = 0
    skipped = 0
    db_updated = 0
    with get_connection() as conn, conn.cursor() as cur:
        ensure_page_images_schema(cur)
        cur.execute(
            """
            select page_key, slot_key, image_url, image_webp,
                   default_image_url, default_image_webp
            from page_images
            """
        )
        rows = [dict(r) for r in cur.fetchall()]
        refcounts = _url_refcount(rows)
        # (source_url, dest_key) → new public URL after move/copy
        done: dict[tuple[str, str], str] = {}
        # Track sources already moved (not copied) so later refs must copy.
        moved_sources: set[str] = set()

        for row in rows:
            page_key = str(row.get("page_key") or "")
            folder = page_image_storage_folder(page_key)
            sets: list[str] = []
            params: list[str] = []
            for col in _URL_COLUMNS:
                url = str(row.get(col) or "").strip()
                if not url:
                    continue
                obj = object_path_from_public_url(url)
                if not obj or not is_flat_page_image_object_key(obj):
                    continue
                dest = _dest_for_flat(obj, page_key)
                if not dest or dest == obj:
                    continue
                cache_key = (url, dest)
                if cache_key in done:
                    new_url = done[cache_key]
                else:
                    # Move only when unshared and source still present; else copy.
                    can_move = refcounts.get(url, 0) <= 1 and url not in moved_sources
                    action = "move" if can_move else "copy"
                    print(f"  {action}: {obj} -> {dest} | {page_key} | {folder}")
                    if dry_run:
                        new_url = public_url_for_object(dest)
                    else:
                        try:
                            if can_move:
                                new_url = move_object(obj, dest)
                                moved_sources.add(url)
                            else:
                                new_url = copy_object(obj, dest)
                        except (StorageNotConfiguredError, StorageUploadError) as exc:
                            print(f"  {action} failed {obj}: {exc}")
                            skipped += 1
                            continue
                    done[cache_key] = new_url
                    moved += 1
                    refcounts[url] = max(0, refcounts.get(url, 1) - 1)
                if new_url != url:
                    sets.append(f"{col} = %s")
                    params.append(new_url)
            if not sets:
                continue
            if dry_run:
                db_updated += 1
                continue
            params.extend([row["page_key"], row["slot_key"]])
            cur.execute(
                f"""
                update page_images
                set {", ".join(sets)}, updated_at = now()
                where page_key = %s and slot_key = %s
                """,
                params,
            )
            db_updated += 1

        if not dry_run:
            conn.commit()
    return moved, db_updated, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only (default when --apply is omitted)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform Storage moves and DB URL rewrites (requires live gate)",
    )
    args = parser.parse_args()
    dry_run = not args.apply
    if args.dry_run and args.apply:
        print("ERROR: use either --dry-run or --apply, not both")
        return 1

    print("=== reorganize Supabase page-images (per-page English folders) ===")
    if dry_run:
        print("DRY RUN — no Storage moves or DB updates\n")

    try:
        from app.storage import _require_config

        base, _, bucket = _require_config()
        print(f"target: {base}/storage/v1/object/public/{bucket}/\n")
    except StorageNotConfiguredError as exc:
        print(f"ERROR: {exc}")
        return 1

    host = (settings.supabase_url or "").lower()
    if not dry_run and host and "localhost" not in host and "127.0.0.1" not in host:
        if os.environ.get("SUPABASE_ALLOW_LIVE_MIGRATE", "").strip() != "1":
            print(
                "Refusing live migrate against remote Supabase.\n"
                "Re-run without --apply (dry-run default), or set "
                "SUPABASE_ALLOW_LIVE_MIGRATE=1 with --apply if you "
                "intentionally target this project."
            )
            return 2

    moved, db_updated, skipped = migrate_page_image_folders(dry_run=dry_run)
    label = "would move/copy" if dry_run else "moved/copied"
    print(f"\n{label} {moved} object(s); skipped {skipped}")
    print(
        f"{'would update' if dry_run else 'updated'} {db_updated} page_images row(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
