"""Upload local public/uploads files to Supabase Storage and rewrite DB URLs."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.database import get_connection  # noqa: E402
from app.storage import (  # noqa: E402
    StorageNotConfiguredError,
    StorageUploadError,
    is_supabase_storage_url,
    local_upload_to_object_key,
    public_url_for_object,
    upload_image,
)
from config.settings import settings  # noqa: E402

DB_URL_COLUMNS: list[tuple[str, str]] = [
    ("product_images", "file_path"),
    ("product_categories", "thumb_path"),
    ("home_banners", "image_url"),
    ("home_banners", "image_url_mobile"),
    ("home_banners", "image_webp"),
    ("testimonials", "image_url"),
    ("page_images", "image_url"),
    ("page_images", "image_webp"),
    ("page_images", "default_image_url"),
    ("page_images", "default_image_webp"),
    ("cms_media", "url"),
]


def _disk_path(kind: str, filename: str) -> Path:
    return settings.static_dir / "uploads" / kind / filename


def _migrate_value(raw: str | None, *, dry_run: bool) -> tuple[str | None, bool]:
    if not raw or not str(raw).strip():
        return raw, False
    value = str(raw).strip()
    if is_supabase_storage_url(value):
        return value, False
    mapped = local_upload_to_object_key(value)
    if not mapped:
        return value, False
    kind, filename = mapped
    disk = _disk_path(kind, filename)
    if not disk.is_file():
        print(f"  skip missing file: {disk}")
        return value, False
    object_path = f"{kind}/{filename}"
    if dry_run:
        print(f"  would upload {disk} -> {object_path}")
        return public_url_for_object(object_path), True
    ext = disk.suffix.lower()
    data = disk.read_bytes()
    try:
        new_url = upload_image(kind, filename, data, ext, upsert=True)
    except (StorageNotConfiguredError, StorageUploadError) as exc:
        print(f"  upload failed for {disk}: {exc}")
        return value, False
    print(f"  uploaded {disk} -> {new_url}")
    return new_url, True


def migrate_db(*, dry_run: bool) -> int:
    updated = 0
    with get_connection() as conn, conn.cursor() as cur:
        for table, column in DB_URL_COLUMNS:
            cur.execute(
                f"""
                select count(*) as c from information_schema.columns
                where table_schema = 'public' and table_name = %s and column_name = %s
                """,
                (table, column),
            )
            if not int(cur.fetchone()["c"]):
                continue
            cur.execute(
                f"select ctid, {column} as val from {table} where {column} is not null and btrim({column}) <> ''"
            )
            rows = cur.fetchall()
            for row in rows:
                new_val, changed = _migrate_value(row["val"], dry_run=dry_run)
                if not changed or new_val == row["val"]:
                    continue
                updated += 1
                if dry_run:
                    continue
                cur.execute(
                    f"update {table} set {column} = %s where ctid = %s",
                    (new_val, row["ctid"]),
                )
        if not dry_run:
            conn.commit()
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading or DB writes")
    args = parser.parse_args()

    print("=== migrate uploads -> Supabase Storage ===")
    if args.dry_run:
        print("DRY RUN — no uploads or DB updates\n")
    try:
        from app.storage import _require_config

        base, _, bucket = _require_config()
        print(f"target: {base}/storage/v1/object/public/{bucket}/\n")
    except StorageNotConfiguredError as exc:
        print(f"ERROR: {exc}")
        return 1

    count = migrate_db(dry_run=args.dry_run)
    print(f"\n{'would update' if args.dry_run else 'updated'} {count} DB URL(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
