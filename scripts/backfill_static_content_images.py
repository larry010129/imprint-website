"""Move admin-editable /static image rows into Supabase Storage. DRY RUN by default.

Scope is deliberately narrow — only columns an admin can replace through the CMS:

    home_banners.image_url / image_url_mobile / image_webp
    testimonials.image_url
    page_images.image_url / image_webp
    product_images.file_path

Explicitly NOT touched:

    product_images.previous_file_path  one-deep restore target; rewriting it kills the undo
    page_images.default_image_*        deploy-shipped fallbacks, versioned by the release
    product_categories.thumb_path      category thumbs keep their {slug}{ext} upsert key
    cms_media.url                      media library, not a rendered slot

DATABASE_URL points at production, so nothing is written unless --apply is passed.

    python scripts/backfill_static_content_images.py                      # preview only
    python scripts/backfill_static_content_images.py --apply              # upload + rewrite
    python scripts/backfill_static_content_images.py --skip product_images
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.database import get_connection  # noqa: E402
from app.storage import (  # noqa: E402
    StorageNotConfiguredError,
    StorageUploadError,
    is_supabase_storage_url,
    page_image_upload_relative_path,
    product_upload_relative_path,
    public_url_for_object,
    upload_image,
)
from config.settings import settings  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# Product folder for the diamond shape/colour renders, which are shared by every
# diamond product rather than owned by one, so no product name slug fits.
MATRIX_STATIC_PREFIX = "images/diamonds/matrix/"
MATRIX_PRODUCT_FOLDER = "diamond-matrix"

# (table, identity columns, url columns, storage kind) — page_images has no id;
# its natural key is (page_key, slot_key). Kind "page-images" resolves a per-page
# subfolder from page_key so keys match what the admin uploader writes.
TARGETS: tuple[tuple[str, tuple[str, ...], tuple[str, ...], str], ...] = (
    ("home_banners", ("id",), ("image_url", "image_url_mobile", "image_webp"), "banners"),
    ("testimonials", ("id",), ("image_url",), "testimonials"),
    ("page_images", ("page_key", "slot_key"), ("image_url", "image_webp"), "page-images"),
    ("product_images", ("id",), ("file_path",), "products"),
)


class Planned:
    """One column rewrite, resolved but not executed."""

    def __init__(
        self,
        table: str,
        identity: dict[str, str],
        column: str,
        old: str,
        disk: Path,
        key: str,
        touch_updated_at: bool,
    ):
        self.table = table
        self.identity = identity
        self.column = column
        self.old = old
        self.disk = disk
        self.key = key
        self.touch_updated_at = touch_updated_at

    @property
    def label(self) -> str:
        return " ".join(f"{k}={v}" for k, v in self.identity.items())

    def describe(self) -> str:
        return (
            f"  {self.table} [{self.label}] .{self.column}\n"
            f"      from {self.old}\n"
            f"      file {self.disk}\n"
            f"      key  {self.key}"
        )


def _local_disk_path(url: str) -> Path | None:
    """Resolve /static/... to a file on disk, refusing traversal."""
    path = unquote(str(url or "").strip().split("?", 1)[0]).replace("\\", "/")
    if not path.startswith("/static/"):
        return None
    rel = path[len("/static/") :].lstrip("/")
    if not rel or ".." in rel.split("/"):
        return None
    disk = (settings.static_dir / rel).resolve()
    if settings.static_dir.resolve() not in disk.parents:
        return None
    return disk if disk.is_file() else None


def _product_folder(disk: Path) -> str | None:
    """Folder segment for a product image; None lands it in products/_pending/."""
    matrix_dir = (settings.static_dir / MATRIX_STATIC_PREFIX).resolve()
    return MATRIX_PRODUCT_FOLDER if disk.parent == matrix_dir else None


def _relative_key(kind: str, disk: Path, page_key: str | None) -> str:
    if kind == "page-images":
        return page_image_upload_relative_path(disk.name, page_key=page_key)
    if kind == "products":
        return product_upload_relative_path(disk.name, folder=_product_folder(disk))
    return disk.name


def _plan_row(
    table: str,
    row: dict,
    identity_columns: tuple[str, ...],
    columns: tuple[str, ...],
    kind: str,
    touch_updated_at: bool,
) -> list[Planned]:
    planned: list[Planned] = []
    identity = {name: str(row.get(name) or "") for name in identity_columns}
    tag = " ".join(f"{k}={v}" for k, v in identity.items())
    page_key = row.get("page_key")
    for column in columns:
        value = str(row.get(column) or "").strip()
        if not value:
            continue
        if is_supabase_storage_url(value):
            continue
        disk = _local_disk_path(value)
        if disk is None:
            print(f"  SKIP {table} [{tag}] .{column}: no local file for {value}")
            continue
        if disk.suffix.lower() not in IMAGE_EXTS:
            print(f"  SKIP {table} [{tag}] .{column}: unsupported type {disk.suffix}")
            continue
        relative = _relative_key(kind, disk, page_key)
        planned.append(
            Planned(
                table, identity, column, value, disk, f"{kind}/{relative}", touch_updated_at
            )
        )
    return planned


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        select count(*)::int as c from information_schema.columns
        where table_schema = 'public' and table_name = %s and column_name = %s
        """,
        (table, column),
    )
    return bool(int((cur.fetchone() or {}).get("c") or 0))


def build_plan(skip: frozenset[str] = frozenset()) -> list[Planned]:
    plan: list[Planned] = []
    with get_connection() as conn, conn.cursor() as cur:
        for table, identity_columns, columns, kind in TARGETS:
            if table in skip:
                print(f"-- {table}: skipped by --skip")
                continue
            present = tuple(c for c in columns if _column_exists(cur, table, c))
            if not present:
                print(f"-- {table}: no target columns present, skipping")
                continue
            # product_images has no updated_at until migration 20260812140000 lands.
            touch = _column_exists(cur, table, "updated_at")
            selected = list(dict.fromkeys(identity_columns + present))
            print(f"-- {table} ({', '.join(present)})")
            cur.execute(f"select {', '.join(selected)} from {table}")
            for row in cur.fetchall():
                plan.extend(_plan_row(table, row, identity_columns, present, kind, touch))
    return plan


def apply_plan(plan: list[Planned]) -> int:
    uploaded: dict[str, str] = {}
    changed = 0
    with get_connection() as conn, conn.cursor() as cur:
        for item in plan:
            new_url = uploaded.get(item.key)
            if new_url is None:
                kind, relative = item.key.split("/", 1)
                try:
                    new_url = upload_image(
                        kind,
                        relative,
                        item.disk.read_bytes(),
                        item.disk.suffix.lower(),
                        upsert=True,
                    )
                except (StorageNotConfiguredError, StorageUploadError) as exc:
                    print(f"  FAIL upload {item.key}: {exc}")
                    continue
                uploaded[item.key] = new_url
            where = " and ".join(f"{name} = %s" for name in item.identity)
            assignments = f"{item.column} = %s"
            if item.touch_updated_at:
                assignments += ", updated_at = now()"
            cur.execute(
                f"update {item.table} set {assignments} "
                f"where {where} and {item.column} = %s",
                (new_url, *item.identity.values(), item.old),
            )
            changed += cur.rowcount or 0
            print(f"  OK {item.table} [{item.label}] .{item.column} -> {new_url}")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually upload and rewrite. Omit for a dry run (the default).",
    )
    parser.add_argument(
        "--skip",
        default="",
        metavar="TABLES",
        help="Comma-separated target tables to leave untouched, e.g. --skip product_images.",
    )
    args = parser.parse_args()

    skip = frozenset(name.strip() for name in args.skip.split(",") if name.strip())
    known = {table for table, _, _, _ in TARGETS}
    # A typo must not silently migrate a table the caller meant to hold back.
    unknown = sorted(skip - known)
    if unknown:
        print(f"ERROR: --skip names no such target: {', '.join(unknown)}")
        print(f"       known targets: {', '.join(sorted(known))}")
        return 1

    try:
        base, _, bucket = _storage_target()
    except StorageNotConfiguredError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("=== backfill admin /static image rows -> Supabase Storage ===")
    print(f"target: {base}/storage/v1/object/public/{bucket}/")
    print("mode:   APPLY (writes to the live DB)" if args.apply else "mode:   DRY RUN")
    if skip:
        print(f"skip:   {', '.join(sorted(skip))}")
    print()

    plan = build_plan(skip)
    print()
    if not plan:
        print("nothing to migrate")
        return 0

    print(f"{len(plan)} column(s) would change:" if not args.apply else f"{len(plan)} column(s):")
    for item in plan:
        print(item.describe())
        if not args.apply:
            print(f"      to   {public_url_for_object(item.key)}")
    print()

    if not args.apply:
        print("DRY RUN — no uploads, no DB writes. Re-run with --apply to commit.")
        return 0

    changed = apply_plan(plan)
    print(f"\nupdated {changed} row column(s)")
    return 0


def _storage_target() -> tuple[str, str, str]:
    from app.storage import _require_config

    return _require_config()


if __name__ == "__main__":
    raise SystemExit(main())
