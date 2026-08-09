"""Seed real WebPs into shop-media page-images/{folder}/ from local or site-images.

For each page_images slot:
  - Skip when image_url already points at nested page-images/{folder}/{file}
    (not .keep) — e.g. home / dna-diamond customs already migrated.
  - Else resolve bytes from local /static path OR existing site-images/ Storage URL
    (image_url / image_webp / default_* , first non-empty srcset entry).
  - ensure_webp → upload page-images/{english-folder}/{original-stem}.webp
  - Rewrite image_url / image_webp; also default_* when they pointed at the
    same source asset being migrated.
  - Empty defaults with no file: leave alone (no invented stock).

Does NOT delete .keep or purge anything.

Usage:
  python scripts/seed_page_images_from_defaults.py --dry-run
  SUPABASE_ALLOW_LIVE_MIGRATE=1 python scripts/seed_page_images_from_defaults.py --apply
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import httpx
import psycopg
from psycopg.rows import dict_row

from app.image_convert import ImageConvertError, ensure_webp
from app.page_image_slots import PAGE_IMAGE_STORAGE_FOLDERS, page_image_storage_folder
from app.storage import (
    StorageNotConfiguredError,
    StorageUploadError,
    is_nested_page_image_object_key,
    is_supabase_storage_url,
    object_path_from_public_url,
    public_url_for_object,
    upload_bytes,
)
from config.settings import settings
_URL_COLUMNS = (
    "image_url",
    "image_webp",
    "default_image_url",
    "default_image_webp",
)
_SRCSET_SPLIT = re.compile(r"\s*,\s*")
_FIRST_URL = re.compile(r"^\s*(\S+)")


def _db_connect():
    dsn = (os.environ.get("DATABASE_URL") or "").strip()
    if not dsn:
        raise SystemExit("DATABASE_URL not set")
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=False)


def _first_url(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    # srcset: "url 800w, url2 1200w" or comma-only lists
    part = _SRCSET_SPLIT.split(text)[0]
    m = _FIRST_URL.match(part)
    if not m:
        return ""
    return unquote(m.group(1).split("?", 1)[0].strip())


def _stem(url_or_path: str) -> str:
    name = PurePosixPath(url_or_path.replace("\\", "/")).name
    if not name or name in {".keep", ".emptyFolderPlaceholder"}:
        return ""
    return PurePosixPath(name).stem


def _local_disk(url: str) -> Path | None:
    path = _first_url(url)
    if not path:
        return None
    if path.startswith("/static/"):
        disk = settings.static_dir / path[len("/static/") :]
    elif path.startswith("static/"):
        disk = settings.static_dir / path[len("static/") :]
    else:
        return None
    return disk if disk.is_file() else None


def _site_images_object(url: str) -> str | None:
    raw = _first_url(url)
    if not raw or not is_supabase_storage_url(raw):
        # allow bare path-style if someone stored full public URL with query already stripped
        if raw.startswith("https://") and "/storage/v1/object/public/" in raw:
            obj = object_path_from_public_url(raw)
        else:
            return None
    else:
        obj = object_path_from_public_url(raw)
    if obj and obj.startswith("site-images/"):
        return obj
    return None


def _is_working_nested_page_image(url: str) -> bool:
    raw = _first_url(url)
    if not raw or not is_supabase_storage_url(raw):
        return False
    obj = object_path_from_public_url(raw)
    if not obj or not is_nested_page_image_object_key(obj):
        return False
    return not obj.endswith("/.keep") and not obj.endswith("/.emptyFolderPlaceholder")


def _download_storage_object(object_path: str) -> bytes:
    from app.storage import _require_config, _storage_headers, _encoded_object_path

    base, key, bucket = _require_config()
    auth_url = (
        f"{base}/storage/v1/object/authenticated/"
        f"{bucket}/{_encoded_object_path(object_path)}"
    )
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(auth_url, headers=_storage_headers(key))
        if resp.status_code != 200:
            # public fallback
            pub = public_url_for_object(object_path, bucket=bucket)
            resp = client.get(pub)
        if resp.status_code != 200:
            raise StorageUploadError(
                f"download failed {object_path} ({resp.status_code})"
            )
        return resp.content


def _static_rel(url: str) -> str | None:
    if url.startswith("/static/"):
        return url[len("/static/") :]
    if url.startswith("static/"):
        return url[len("static/") :]
    return None


def _resolve_source(row: dict) -> tuple[str, bytes, str, set[str]] | None:
    """Return (source_label, bytes, original_stem, identity_keys) or None."""
    for col in (
        "image_webp",
        "image_url",
        "default_image_webp",
        "default_image_url",
    ):
        raw = str(row.get(col) or "").strip()
        if not raw:
            continue
        url = _first_url(raw)
        if not url:
            continue
        disk = _local_disk(url)
        if disk:
            stem = _stem(disk.name)
            if stem:
                keys = _asset_keys_for_url(url) | {
                    disk.resolve().as_posix().lower(),
                    stem.lower(),
                }
                return f"local:{disk.as_posix()}", disk.read_bytes(), stem, keys
        rel = _static_rel(url)
        if rel:
            webp_sib = (settings.static_dir / rel).with_suffix(".webp")
            if webp_sib.is_file():
                stem = _stem(webp_sib.name)
                if stem:
                    keys = _asset_keys_for_url(url) | {
                        webp_sib.resolve().as_posix().lower(),
                        stem.lower(),
                        _stem(url).lower(),
                    }
                    return f"local:{webp_sib.as_posix()}", webp_sib.read_bytes(), stem, keys

        si = _site_images_object(url)
        if si:
            candidates = [si]
            if not si.lower().endswith(".webp"):
                candidates.insert(0, PurePosixPath(si).with_suffix(".webp").as_posix())
            for obj in candidates:
                try:
                    data = _download_storage_object(obj)
                except StorageUploadError:
                    continue
                stem = _stem(obj)
                if stem:
                    keys = _asset_keys_for_url(url) | {obj, stem.lower(), _stem(si).lower()}
                    return f"storage:{obj}", data, stem, keys
    return None


def _asset_keys_for_url(url: str) -> set[str]:
    """Identity keys so default_* matching same asset can be rewritten."""
    keys: set[str] = set()
    raw = _first_url(url)
    if not raw:
        return keys
    keys.add(raw)
    disk = _local_disk(raw)
    if disk:
        keys.add(disk.resolve().as_posix().lower())
        keys.add(disk.name.lower())
        keys.add(_stem(disk.name).lower())
    si = _site_images_object(raw)
    if si:
        keys.add(si)
        keys.add(PurePosixPath(si).name.lower())
        keys.add(_stem(si).lower())
    # static path normalized
    if raw.startswith("/static/images/"):
        keys.add("site-images/" + raw[len("/static/images/") :])
        keys.add(_stem(raw).lower())
    return {k for k in keys if k}


def _list_page_image_entries() -> tuple[list[str], set[str]]:
    # Local import avoids treating scripts/ as a package.
    from ensure_page_image_storage_folders import list_page_image_entries

    return list_page_image_entries()


def _real_file_counts(keys: list[str]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for k in keys:
        rest = k.removeprefix("page-images/")
        parts = [p for p in rest.split("/") if p]
        if len(parts) < 2:
            continue
        folder, name = parts[0], parts[-1]
        if name in {".keep", ".emptyFolderPlaceholder"}:
            continue
        counts[folder] += 1
    return dict(counts)


def _sample_http(urls: list[str], *, limit: int = 6) -> None:
    print("\n--- HTTP sample ---")
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for url in urls[:limit]:
            try:
                resp = client.head(url)
                code = resp.status_code
                if code >= 400:
                    resp = client.get(url)
                    code = resp.status_code
                print(f"  {code} {url}")
            except httpx.HTTPError as exc:
                print(f"  ERR {url}: {exc}")


def migrate(*, dry_run: bool) -> tuple[int, int, int]:
    """Return (uploaded_or_would, db_rows_updated, skipped)."""
    uploaded = 0
    db_updated = 0
    skipped = 0
    # (folder, stem) → public URL
    cache: dict[tuple[str, str], str] = {}
    sample_urls: list[str] = []

    with _db_connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select page_key, slot_key, image_url, image_webp,
                   default_image_url, default_image_webp
            from page_images
            order by page_key, sort_order, slot_key
            """
        )
        rows = [dict(r) for r in cur.fetchall()]

        for row in rows:
            page_key = str(row.get("page_key") or "")
            slot_key = str(row.get("slot_key") or "")
            folder = page_image_storage_folder(page_key)

            if _is_working_nested_page_image(str(row.get("image_url") or "")):
                print(f"  skip nested: {folder}/{slot_key}")
                skipped += 1
                continue

            resolved = _resolve_source(row)
            if not resolved:
                print(f"  leave empty/no-source: {folder}/{slot_key}")
                skipped += 1
                continue

            source_label, data, stem, source_keys = resolved
            dest_rel = f"{folder}/{stem}.webp"
            dest_key = f"page-images/{dest_rel}"
            cache_key = (folder, stem)

            if cache_key in cache:
                new_url = cache[cache_key]
            else:
                print(f"  {'would upload' if dry_run else 'upload'}: {source_label} -> {dest_key}")
                if dry_run:
                    new_url = public_url_for_object(dest_key)
                else:
                    try:
                        webp_data, webp_name, _ext = ensure_webp(
                            data, f"{stem}.webp", ".webp"
                        )
                        # ensure_webp may keep stem; force folder-relative name
                        final_name = PurePosixPath(webp_name).name
                        if PurePosixPath(final_name).stem != stem:
                            final_name = f"{stem}.webp"
                        new_url = upload_bytes(
                            "page-images",
                            f"{folder}/{final_name}",
                            webp_data,
                            "image/webp",
                            upsert=True,
                        )
                    except (ImageConvertError, StorageNotConfiguredError, StorageUploadError) as exc:
                        print(f"  fail {dest_key}: {exc}")
                        skipped += 1
                        continue
                cache[cache_key] = new_url
                uploaded += 1
                sample_urls.append(new_url)

            sets: list[str] = []
            params: list[str] = []
            for col in ("image_url", "image_webp"):
                sets.append(f"{col} = %s")
                params.append(new_url)
            for col in ("default_image_url", "default_image_webp"):
                raw = str(row.get(col) or "").strip()
                if not raw:
                    continue
                keys = _asset_keys_for_url(raw)
                # Same asset only — never rewrite a mismatched default_* (e.g. home
                # series-first-love defaults still point at a different hero stem).
                if keys & source_keys:
                    sets.append(f"{col} = %s")
                    params.append(new_url)

            print(
                f"    update {page_key} {slot_key}: "
                f"{', '.join(s.split(' =')[0] for s in sets)}"
            )
            if dry_run:
                db_updated += 1
                continue
            params.extend([page_key, slot_key])
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

    if sample_urls and not dry_run:
        _sample_http(sample_urls)
    elif dry_run and sample_urls:
        print("\n(dry-run: skip HTTP sample)")

    return uploaded, db_updated, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dry_run = not args.apply
    if args.dry_run and args.apply:
        print("ERROR: use either --dry-run or --apply, not both")
        return 1

    print("=== seed page-images WebPs from local / site-images ===")
    if dry_run:
        print("DRY RUN — no Storage writes or DB updates\n")

    try:
        from app.storage import _require_config

        base, _, bucket = _require_config()
        print(f"storage: {base}/storage/v1/object/public/{bucket}/")
    except StorageNotConfiguredError as exc:
        print(f"ERROR: {exc}")
        return 1

    host = (settings.supabase_url or "").lower()
    remote = host and "localhost" not in host and "127.0.0.1" not in host
    if not dry_run and remote and os.environ.get("SUPABASE_ALLOW_LIVE_MIGRATE", "").strip() != "1":
        print(
            "Refusing live migrate against remote Supabase.\n"
            "Set SUPABASE_ALLOW_LIVE_MIGRATE=1 with --apply."
        )
        return 2

    # allow `from ensure_page_image_storage_folders import ...`
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    print("\n--- BEFORE (real webps per folder) ---")
    keys_before, _ = _list_page_image_entries()
    before = _real_file_counts(keys_before)
    required = sorted(set(PAGE_IMAGE_STORAGE_FOLDERS.values()))
    for folder in required:
        print(f"  {folder}: {before.get(folder, 0)}")

    uploaded, db_updated, skipped = migrate(dry_run=dry_run)

    print("\n--- AFTER (real webps per folder) ---")
    if dry_run:
        print("  (re-list after --apply)")
        after = before
    else:
        keys_after, _ = _list_page_image_entries()
        after = _real_file_counts(keys_after)
        for folder in required:
            print(
                f"  {folder}: {before.get(folder, 0)} -> {after.get(folder, 0)}"
            )

    print(
        f"\n{'would upload' if dry_run else 'uploaded'} {uploaded}; "
        f"{'would update' if dry_run else 'updated'} {db_updated} row(s); "
        f"skipped {skipped}"
    )
    if not dry_run:
        print("before→after real files:", {f: (before.get(f, 0), after.get(f, 0)) for f in required})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
