"""Upload local static/upload images to Supabase Storage and rewrite DB URLs."""
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

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Cache kind/filename → public URL so duplicate DB rows upload once.
_UPLOAD_CACHE: dict[tuple[str, str], str] = {}


def _static_images_to_object_key(local_url: str) -> tuple[str, str] | None:
    """Map /static/images/... or images/... → (site-images, relative path)."""
    path = str(local_url or "").strip().split("?", 1)[0].replace("\\", "/")
    if path.startswith("https://") or path.startswith("http://"):
        return None
    if path.startswith("/static/images/"):
        rest = path[len("/static/images/") :].lstrip("/")
    elif path.startswith("static/images/"):
        rest = path[len("static/images/") :].lstrip("/")
    elif path.startswith("/images/"):
        rest = path[len("/images/") :].lstrip("/")
    elif path.startswith("images/"):
        rest = path[len("images/") :].lstrip("/")
    else:
        return None
    if not rest or ".." in rest.split("/"):
        return None
    return "site-images", rest


def _disk_for_mapped(kind: str, filename: str) -> Path | None:
    if kind == "site-images":
        disk = settings.static_dir / "images" / Path(filename)
    else:
        disk = settings.static_dir / "uploads" / kind / filename
    return disk if disk.is_file() else None


def _map_local_url(value: str) -> tuple[str, str] | None:
    return local_upload_to_object_key(value) or _static_images_to_object_key(value)


def _migrate_value(raw: str | None, *, dry_run: bool) -> tuple[str | None, bool]:
    if not raw or not str(raw).strip():
        return raw, False
    value = str(raw).strip()
    if is_supabase_storage_url(value):
        return value, False
    mapped = _map_local_url(value)
    if not mapped:
        return value, False
    kind, filename = mapped
    disk = _disk_for_mapped(kind, filename)
    if disk is None:
        print(f"  skip missing file: {kind}/{filename}")
        return value, False
    object_path = f"{kind}/{filename}"
    cache_key = (kind, filename)
    if dry_run:
        print(f"  would upload {disk} -> {object_path}")
        return public_url_for_object(object_path), True
    if cache_key in _UPLOAD_CACHE:
        return _UPLOAD_CACHE[cache_key], True
    ext = disk.suffix.lower()
    data = disk.read_bytes()
    try:
        new_url = upload_image(kind, filename, data, ext, upsert=True)
    except (StorageNotConfiguredError, StorageUploadError) as exc:
        print(f"  upload failed for {disk}: {exc}")
        return value, False
    _UPLOAD_CACHE[cache_key] = new_url
    print(f"  uploaded {disk.name} -> {new_url}")
    return new_url, True


def migrate_db(*, dry_run: bool) -> int:
    updated = 0
    with get_connection() as conn, conn.cursor() as cur:
        for table, column in DB_URL_COLUMNS:
            cur.execute(
                """
                select count(*) as c from information_schema.columns
                where table_schema = 'public' and table_name = %s and column_name = %s
                """,
                (table, column),
            )
            if not int(cur.fetchone()["c"]):
                continue
            print(f"-- {table}.{column}")
            cur.execute(
                f"select ctid, {column} as val from {table} "
                f"where {column} is not null and btrim({column}) <> ''"
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


def migrate_orphan_uploads(*, dry_run: bool) -> int:
    """Upload leftover files under public/uploads even if not referenced in DB."""
    root = settings.static_dir / "uploads"
    if not root.is_dir():
        return 0
    print("-- orphan public/uploads files")
    count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            continue
        rel = path.relative_to(root).as_posix()
        parts = rel.split("/", 1)
        if len(parts) != 2:
            print(f"  skip (no kind folder): {rel}")
            continue
        kind, filename = parts[0], parts[1]
        if dry_run:
            print(f"  would upload orphan {path} -> {kind}/{filename}")
            count += 1
            continue
        try:
            url = upload_image(kind, filename, path.read_bytes(), path.suffix.lower(), upsert=True)
            print(f"  uploaded orphan {rel} -> {url}")
            count += 1
        except (StorageNotConfiguredError, StorageUploadError) as exc:
            print(f"  upload failed orphan {rel}: {exc}")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading or DB writes")
    parser.add_argument(
        "--orphans-only",
        action="store_true",
        help="Only upload unreferenced public/uploads files",
    )
    parser.add_argument(
        "--skip-orphans",
        action="store_true",
        help="Skip orphan public/uploads upload pass",
    )
    args = parser.parse_args()

    print("=== migrate images -> Supabase Storage ===")
    if args.dry_run:
        print("DRY RUN — no uploads or DB updates\n")
    try:
        from app.storage import _require_config

        base, _, bucket = _require_config()
        print(f"target: {base}/storage/v1/object/public/{bucket}/\n")
    except StorageNotConfiguredError as exc:
        print(f"ERROR: {exc}")
        return 1

    db_count = 0
    if not args.orphans_only:
        db_count = migrate_db(dry_run=args.dry_run)
        print(f"\n{'would update' if args.dry_run else 'updated'} {db_count} DB URL(s)")

    orphan_count = 0
    if not args.skip_orphans:
        orphan_count = migrate_orphan_uploads(dry_run=args.dry_run)
        print(f"{'would upload' if args.dry_run else 'uploaded'} {orphan_count} orphan upload file(s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
