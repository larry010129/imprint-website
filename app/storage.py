"""Supabase Storage upload/delete for admin-uploaded media."""

from __future__ import annotations

import re
from urllib.parse import quote, unquote

import httpx

from config.settings import settings

_EXT_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

_STORAGE_PUBLIC_PATH = re.compile(
    r"/storage/v1/object/public/([^/]+)/(.+)$",
    re.I,
)

UPLOAD_KIND_PREFIXES: dict[str, str] = {
    "/static/uploads/products/": "products",
    "/static/uploads/categories/": "categories",
    "/static/uploads/banners/": "banners",
    "/static/uploads/testimonials/": "testimonials",
    "/static/uploads/page-images/": "page-images",
    "/static/uploads/cms-media/": "cms-media",
}


class StorageNotConfiguredError(Exception):
    """Required Supabase Storage env vars are missing."""


class StorageUploadError(Exception):
    """Supabase Storage upload failed."""


def _require_config() -> tuple[str, str, str]:
    base = settings.supabase_url.rstrip("/")
    key = settings.supabase_service_role_key
    bucket = settings.supabase_storage_bucket
    if not base or not key:
        raise StorageNotConfiguredError(
            "Supabase Storage 未設定：請設定 SUPABASE_URL 與 "
            "SUPABASE_SERVICE_ROLE_KEY 或 SUPABASE_SECRET_KEY"
        )
    return base, key, bucket


def _storage_headers(
    key: str,
    *,
    content_type: str | None = None,
    upsert: bool = False,
) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {key}",
        "apikey": key,
    }
    if content_type:
        headers["Content-Type"] = content_type
    if upsert:
        headers["x-upsert"] = "true"
    return headers


def _object_path(kind: str, filename: str) -> str:
    """Build Storage object key `kind/filename`; reject empty/invalid keys.

    Supabase returns InvalidKey with an empty message when the URL path after
    the bucket is blank or only slashes (e.g. `/object/shop-media/`).
    """
    kind_part = (kind or "").strip().strip("/")
    # Match storage-js _removeEmptyFolders: drop empties, keep nested segments.
    segments = [
        part
        for part in (filename or "").strip().replace("\\", "/").split("/")
        if part and part != "."
    ]
    if not kind_part or not segments or any(part == ".." for part in segments):
        raise StorageUploadError(
            "Storage upload failed: empty object path (InvalidKey)"
        )
    return f"{kind_part}/{'/'.join(segments)}"


def _encoded_object_path(object_path: str) -> str:
    """Percent-encode each path segment (storage-js encodeURIComponent style)."""
    return "/".join(quote(part, safe="") for part in object_path.split("/") if part)


def _object_api_url(base: str, bucket: str, object_path: str) -> str:
    return f"{base}/storage/v1/object/{bucket}/{_encoded_object_path(object_path)}"


def public_url_for_object(object_path: str, *, bucket: str | None = None) -> str:
    base, _, default_bucket = _require_config()
    b = bucket or default_bucket
    path = (object_path or "").strip().lstrip("/")
    if not path:
        raise StorageUploadError(
            "Storage upload failed: empty object path (InvalidKey)"
        )
    return f"{base}/storage/v1/object/public/{b}/{path}"


def is_supabase_storage_url(url: str | None) -> bool:
    if not url:
        return False
    path = unquote(str(url).strip().split("?", 1)[0])
    if not path.startswith("https://") or "/storage/v1/object/public/" not in path:
        return False
    try:
        base, _, bucket = _require_config()
        return path.startswith(f"{base}/storage/v1/object/public/{bucket}/")
    except StorageNotConfiguredError:
        return bool(re.match(r"^https://[^/]+\.supabase\.co/storage/v1/object/public/", path))


def object_path_from_public_url(url: str) -> str | None:
    path = unquote(str(url).strip().split("?", 1)[0])
    match = _STORAGE_PUBLIC_PATH.search(path)
    if not match:
        return None
    bucket, obj = match.group(1), unquote(match.group(2))
    try:
        expected = settings.supabase_storage_bucket
    except Exception:
        expected = "shop-media"
    if bucket != expected:
        return None
    return obj


def local_upload_to_object_key(local_url: str) -> tuple[str, str] | None:
    """Map /static/uploads/{kind}/file → (kind, file)."""
    path = unquote(str(local_url or "").strip().split("?", 1)[0]).replace("\\", "/")
    if not path.startswith("/"):
        path = f"/{path}"
    for prefix, kind in UPLOAD_KIND_PREFIXES.items():
        if path.startswith(prefix):
            rest = path[len(prefix) :].lstrip("/")
            if rest:
                return kind, rest
    return None


def upload_bytes(
    kind: str,
    filename: str,
    data: bytes,
    content_type: str,
    *,
    upsert: bool = True,
) -> str:
    base, key, bucket = _require_config()
    object_path = _object_path(kind, filename)
    api_url = _object_api_url(base, bucket, object_path)
    headers = _storage_headers(key, content_type=content_type, upsert=upsert)
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(api_url, content=data, headers=headers)
        if resp.status_code not in (200, 201):
            detail = (resp.text or "")[:200]
            raise StorageUploadError(
                f"Storage upload failed ({resp.status_code}): {detail}"
            )
        # NoSuchKey is a GET/download miss — verify object exists before returning URL.
        auth_url = (
            f"{base}/storage/v1/object/authenticated/"
            f"{bucket}/{_encoded_object_path(object_path)}"
        )
        check = client.get(auth_url, headers=_storage_headers(key))
        if check.status_code != 200:
            detail = (check.text or "")[:200]
            raise StorageUploadError(
                f"Storage upload wrote but object not readable "
                f"({check.status_code}): {detail}"
            )
    return public_url_for_object(object_path, bucket=bucket)


def upload_image(
    kind: str,
    filename: str,
    data: bytes,
    ext: str,
    *,
    upsert: bool = False,
) -> str:
    mime = _EXT_MIME.get(ext.lower(), "application/octet-stream")
    return upload_bytes(kind, filename, data, mime, upsert=upsert)


def delete_by_url(url: str | None) -> bool:
    """Best-effort delete from Storage. Returns True when deleted or URL is not Storage."""
    if not url or not is_supabase_storage_url(url):
        return False
    object_path = object_path_from_public_url(url)
    if not object_path:
        return False
    try:
        base, key, bucket = _require_config()
    except StorageNotConfiguredError:
        return False
    api_url = _object_api_url(base, bucket, object_path)
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.delete(api_url, headers=_storage_headers(key))
        return resp.status_code in (200, 204, 404)
    except httpx.HTTPError:
        return False
