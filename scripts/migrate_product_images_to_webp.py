"""Convert legacy shop-media product/category images to WebP.

Keeps the same basename stem (no UUID rewrite). Updates product_images.file_path /
previous_file_path and product_categories.thumb_path. Deletes old non-WebP objects
when unreferenced. Also reports Storage products/ orphans that are not .webp.

Usage:
  python scripts/migrate_product_images_to_webp.py
  python scripts/migrate_product_images_to_webp.py --dry-run
  SUPABASE_ALLOW_LIVE_MIGRATE=1 python scripts/migrate_product_images_to_webp.py --live
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.database import get_connection, get_transaction  # noqa: E402
from app.image_convert import ImageConvertError, ensure_webp  # noqa: E402
from app.storage import (  # noqa: E402
    StorageNotConfiguredError,
    delete_by_url,
    object_path_from_public_url,
    public_url_for_object,
    upload_image,
)
from config.settings import settings  # noqa: E402

PRODUCTS_PREFIX = "products/"
CATEGORIES_PREFIX = "categories/"
_NON_WEBP = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff"}
_LIST_LIMIT = 1000


def _is_non_webp_url(url: str | None) -> bool:
    path = str(url or "").strip().split("?", 1)[0].lower()
    if not path:
        return False
    return Path(path).suffix in _NON_WEBP


def _webp_object_path(object_path: str) -> str:
    posix = PurePosixPath(object_path)
    return str(posix.with_suffix(".webp"))


def _download_object_bytes(object_path: str) -> bytes:
    import httpx

    from app.storage import _encoded_object_path, _require_config, _storage_headers

    base, key, bucket = _require_config()
    api_url = (
        f"{base}/storage/v1/object/authenticated/"
        f"{bucket}/{_encoded_object_path(object_path)}"
    )
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(api_url, headers=_storage_headers(key))
        if resp.status_code != 200:
            raise RuntimeError(
                f"download failed ({resp.status_code}): {(resp.text or '')[:160]}"
            )
        return resp.content


def _convert_and_upload(object_path: str, data: bytes) -> str:
    """Return new public URL for same-folder stem.webp object."""
    filename = PurePosixPath(object_path).name
    ext = PurePosixPath(filename).suffix.lower() or ".bin"
    webp_data, webp_name, webp_ext = ensure_webp(data, filename, ext)
    parent = PurePosixPath(object_path).parent
    if str(parent) in (".", ""):
        rel = webp_name
        kind = "products"
    else:
        parts = object_path.strip("/").split("/")
        kind = parts[0]
        rel = "/".join(parts[1:-1] + [webp_name]) if len(parts) > 1 else webp_name
    return upload_image(kind, rel, webp_data, webp_ext, upsert=True)


def migrate_url(url: str, *, dry_run: bool) -> tuple[str, bool, str | None]:
    """Return (new_url, changed, old_url_to_delete_or_none)."""
    raw = str(url or "").strip()
    if not raw or not _is_non_webp_url(raw):
        return raw, False, None
    obj = object_path_from_public_url(raw)
    if not obj:
        return raw, False, None
    new_obj = _webp_object_path(obj)
    if dry_run:
        print(f"  would convert {obj} -> {new_obj}")
        try:
            return public_url_for_object(new_obj), True, raw
        except Exception:
            return raw, False, None
    data = _download_object_bytes(obj)
    new_url = _convert_and_upload(obj, data)
    print(f"  converted {obj} -> {object_path_from_public_url(new_url) or new_obj}")
    return new_url, True, raw


def _collect_db_targets(cur) -> list[tuple[str, str, str]]:
    """Rows as (table, id, column) that need WebP conversion."""
    targets: list[tuple[str, str, str]] = []
    cur.execute(
        "select id, file_path, previous_file_path from product_images"
    )
    for row in cur.fetchall():
        image_id = str(row["id"])
        if _is_non_webp_url(row.get("file_path")):
            targets.append(("product_images", image_id, "file_path"))
        if _is_non_webp_url(row.get("previous_file_path")):
            targets.append(("product_images", image_id, "previous_file_path"))
    cur.execute("select slug, thumb_path from product_categories")
    for row in cur.fetchall():
        if _is_non_webp_url(row.get("thumb_path")):
            targets.append(("product_categories", str(row["slug"]), "thumb_path"))
    return targets


def _update_db_url(cur, table: str, row_id: str, column: str, new_url: str) -> None:
    if table == "product_images":
        cur.execute(
            f"update product_images set {column} = %s where id = %s",
            (new_url, row_id),
        )
    elif table == "product_categories":
        cur.execute(
            f"update product_categories set {column} = %s where slug = %s",
            (new_url, row_id),
        )


def _url_still_referenced(cur, url: str) -> bool:
    cur.execute(
        """
        select 1 from product_images
        where file_path = %s or previous_file_path = %s
        limit 1
        """,
        (url, url),
    )
    if cur.fetchone():
        return True
    cur.execute(
        "select 1 from product_categories where thumb_path = %s limit 1",
        (url,),
    )
    return cur.fetchone() is not None


def list_storage_keys(prefix: str, *, limit: int = _LIST_LIMIT) -> list[str]:
    import httpx

    from app.storage import _require_config, _storage_headers

    base, key, bucket = _require_config()
    url = f"{base}/storage/v1/object/list/{bucket}"
    headers = _storage_headers(key, content_type="application/json")
    keys: list[str] = []
    seen: set[str] = set()

    def normalize(listed_prefix: str, name: str) -> str:
        name = (name or "").strip().strip("/")
        if not name:
            return ""
        if name.startswith(prefix.rstrip("/") + "/") or name.startswith(prefix):
            return name.lstrip("/")
        base_p = listed_prefix.rstrip("/")
        return f"{base_p}/{name}".replace("//", "/")

    def is_folder(item: dict) -> bool:
        if item.get("id") is None and not item.get("metadata"):
            return True
        return (item.get("name") or "").strip().endswith("/")

    def walk(client: httpx.Client, listed_prefix: str) -> None:
        offset = 0
        while True:
            payload = {
                "prefix": listed_prefix,
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
                full = normalize(listed_prefix, name)
                if not full or full in seen:
                    continue
                if is_folder(item):
                    seen.add(full)
                    walk(client, full.rstrip("/") + "/")
                    continue
                seen.add(full)
                keys.append(full)
            if len(batch) < limit:
                return
            offset += limit

    with httpx.Client(timeout=60.0) as client:
        walk(client, prefix)
    return keys


def referenced_keys(cur) -> set[str]:
    found: set[str] = set()
    cur.execute("select file_path, previous_file_path from product_images")
    for row in cur.fetchall():
        for key in ("file_path", "previous_file_path"):
            obj = object_path_from_public_url(str(row.get(key) or "").strip())
            if obj:
                found.add(obj)
    cur.execute("select thumb_path from product_categories")
    for row in cur.fetchall():
        obj = object_path_from_public_url(str(row.get("thumb_path") or "").strip())
        if obj:
            found.add(obj)
    return found


def migrate(*, dry_run: bool) -> tuple[int, int, int]:
    """Return (converted, deleted_old, orphan_non_webp_reported)."""
    converted = 0
    deleted_old = 0
    to_delete: list[str] = []

    with get_connection() as conn, conn.cursor() as cur:
        targets = _collect_db_targets(cur)

    for table, row_id, column in targets:
        with get_connection() as conn, conn.cursor() as cur:
            if table == "product_images":
                cur.execute(
                    f"select {column} as url from product_images where id = %s",
                    (row_id,),
                )
            else:
                cur.execute(
                    f"select {column} as url from product_categories where slug = %s",
                    (row_id,),
                )
            row = cur.fetchone() or {}
            old_url = str(row.get("url") or "").strip()
        if not old_url:
            continue
        try:
            new_url, changed, old = migrate_url(old_url, dry_run=dry_run)
        except (ImageConvertError, RuntimeError, Exception) as exc:
            print(f"  skip {table}.{column} {row_id}: {exc}")
            continue
        if not changed:
            continue
        converted += 1
        if dry_run:
            if old:
                to_delete.append(old)
            continue
        with get_transaction() as conn, conn.cursor() as cur:
            _update_db_url(cur, table, row_id, column, new_url)
            if old and not _url_still_referenced(cur, old):
                if delete_by_url(old):
                    deleted_old += 1
                    print(f"  deleted old {object_path_from_public_url(old) or old}")
                else:
                    print(f"  warn: could not delete old {old}")

    # Orphan / leftover non-webp under products/ (and categories/) after DB migrate.
    orphan_report = 0
    try:
        with get_connection() as conn, conn.cursor() as cur:
            refs = referenced_keys(cur)
        for prefix in (PRODUCTS_PREFIX, CATEGORIES_PREFIX):
            for key in list_storage_keys(prefix):
                if Path(key).suffix.lower() not in _NON_WEBP:
                    continue
                if key in refs:
                    continue
                orphan_report += 1
                label = "would delete orphan" if dry_run else "delete orphan"
                print(f"  {label}: {key}")
                if dry_run:
                    continue
                try:
                    url = public_url_for_object(key)
                except Exception as exc:
                    print(f"  skip bad key {key}: {exc}")
                    continue
                if delete_by_url(url):
                    deleted_old += 1
                else:
                    print(f"  warn: delete failed: {key}")
    except StorageNotConfiguredError:
        pass

    if dry_run:
        deleted_old = len(to_delete) + orphan_report
    return converted, deleted_old, orphan_report


def _live_allowed() -> bool:
    return os.environ.get("SUPABASE_ALLOW_LIVE_MIGRATE", "").strip() == "1"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=None,
        help="Preview conversions (default when --live not set)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Apply uploads/DB updates/deletes (requires SUPABASE_ALLOW_LIVE_MIGRATE=1 for remote)",
    )
    args = parser.parse_args()
    dry_run = True if args.dry_run else (not args.live)

    print("=== migrate product images to WebP ===")
    if dry_run:
        print("DRY RUN — no Storage/DB writes\n")
    else:
        print("LIVE — will upload WebP, update DB, delete old non-WebP\n")

    try:
        from app.storage import _require_config

        base, _, bucket = _require_config()
        print(f"target: {base}/storage/v1/object/public/{bucket}/\n")
    except StorageNotConfiguredError as exc:
        print(f"ERROR: {exc}")
        return 1

    host = (settings.supabase_url or "").lower()
    remote = host and "localhost" not in host and "127.0.0.1" not in host
    if not dry_run and remote and not _live_allowed():
        print(
            "Refusing live migrate against remote Supabase.\n"
            "Re-run with --dry-run (default), or set "
            "SUPABASE_ALLOW_LIVE_MIGRATE=1 with --live."
        )
        return 2

    converted, deleted, orphans = migrate(dry_run=dry_run)
    label_c = "would convert" if dry_run else "converted"
    label_d = "would delete" if dry_run else "deleted"
    print(
        f"\n{label_c} {converted}; {label_d} {deleted}; "
        f"orphan non-webp reported {orphans}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
