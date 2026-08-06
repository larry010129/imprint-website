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

# Admin image slots: white | yellow | rose (compound slots like white-pink → white).
PRODUCT_METAL_FOLDERS = frozenset({"white", "yellow", "rose"})
# Admin category tabs → Storage type folder (項墜/戒指/耳環/手鍊/鏈條).
PRODUCT_CATEGORY_KEYS = frozenset(
    {"diamond", "pendant", "ring", "earring", "bracelet", "chain"}
)
_PENDING_PREFIX = "products/_pending/"
_PENDING_FOLDER = "_pending"
PRODUCT_FOLDER_MAX_LEN = 80
_UNSAFE_SEGMENT = re.compile(r"[^a-zA-Z0-9._-]")
_UNSAFE_FOLDER_CHAR = re.compile(r"[^\w.\-]", re.UNICODE)
_MULTI_DASH = re.compile(r"[-_]{2,}")
_HEX_ONLY = re.compile(r"[^a-fA-F0-9]")
_STORAGE_ASCII_SAFE = re.compile(r"^[A-Za-z0-9._-]+$")
_UUID_FOLDER = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)


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
        return bool(
            re.match(
                r"^https://[^/]+\.supabase\.co/storage/v1/object/public/",
                path,
            )
        )


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
            if resp.status_code == 409 or "KeyAlreadyExists" in detail:
                raise StorageUploadError(
                    "圖片已存在且無法覆寫，請稍後再試或換檔名上傳"
                )
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
    upsert: bool = True,
) -> str:
    """Upload image bytes; upsert=True overwrites same object key (admin replace)."""
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


def metal_color_from_slot(slot: str | None) -> str | None:
    """Metal folder from admin slot: white-pink → white; yellow → yellow."""
    if not slot:
        return None
    first = str(slot).strip().lower().split("-", 1)[0]
    return first if first in PRODUCT_METAL_FOLDERS else None


def _safe_path_segment(value: str, *, label: str) -> str:
    raw = (value or "").strip().strip("/")
    if not raw or "/" in raw or "\\" in raw or raw in {".", ".."}:
        raise StorageUploadError(f"invalid {label} for Storage path")
    if _UNSAFE_SEGMENT.search(raw):
        raise StorageUploadError(f"invalid {label} for Storage path")
    return raw


def _safe_folder_segment(value: str, *, label: str = "folder") -> str:
    raw = (value or "").strip().strip("/")
    if (
        not raw
        or "/" in raw
        or "\\" in raw
        or raw in {".", ".."}
        or raw == _PENDING_FOLDER
    ):
        raise StorageUploadError(f"invalid {label} for Storage path")
    if _UNSAFE_FOLDER_CHAR.search(raw):
        raise StorageUploadError(f"invalid {label} for Storage path")
    return raw


def short_product_id_segment(product_id: str) -> str:
    """First 8 hex chars of a UUID (dashes stripped); stable empty-name fallback."""
    cleaned = _HEX_ONLY.sub("", str(product_id or ""))
    if len(cleaned) >= 8:
        return cleaned[:8].lower()
    fallback = sanitize_product_name_slug(str(product_id or ""), max_len=36)
    return fallback or "product"


def sanitize_product_name_slug(
    name: str,
    *,
    max_len: int = PRODUCT_FOLDER_MAX_LEN,
) -> str:
    """ASCII folder slug from English name: lowercase, spaces→`-`, strip unsafe, max ~80."""
    raw = (name or "").strip().lower()
    if not raw:
        return ""
    s = raw.replace(" ", "-").replace("/", "-").replace("\\", "-")
    s = re.sub(r"[^a-z0-9._-]+", "-", s)
    s = _MULTI_DASH.sub("-", s)
    # "_pending" / "pending" reserved — never a product folder slug.
    if s.strip("-_") == "pending":
        return ""
    s = s.strip("-_")
    if len(s) > max_len:
        s = s[:max_len].rstrip("-_")
    if not s or s in {".", ".."} or s == _PENDING_FOLDER or s == "pending":
        return ""
    if not _STORAGE_ASCII_SAFE.fullmatch(s):
        return ""
    return s


def storage_safe_folder_segment(slug: str) -> str:
    """Ensure folder segment is ASCII-safe for Supabase Storage keys.

    Folder names come from 英文名稱 (`name_en`) via `sanitize_product_name_slug`.
    Non-ASCII / empty input → empty string (caller uses short product id).
    """
    raw = (slug or "").strip()
    if not raw:
        return ""
    if _STORAGE_ASCII_SAFE.fullmatch(raw):
        return raw[:PRODUCT_FOLDER_MAX_LEN].lower()
    return sanitize_product_name_slug(raw)


def english_label_for_folder(
    name_en: str | None,
    name_zh: str | None = None,
) -> str:
    """Return name_en when it yields an ASCII slug; else \"\".

    ``name_zh`` ignored — admin 英文名稱 (`name_en`) is source of truth.
    """
    _ = name_zh
    en = (name_en or "").strip()
    if sanitize_product_name_slug(en):
        return en
    return ""


def product_folder_with_id_suffix(
    base_slug: str,
    product_id: str,
    *,
    max_len: int = PRODUCT_FOLDER_MAX_LEN,
) -> str:
    """Append `-{first8}` when slugs collide."""
    suffix = short_product_id_segment(product_id)
    room = max_len - len(suffix) - 1
    if room < 1:
        return suffix
    head = (base_slug or "")[:room].rstrip("-_")
    return f"{head}-{suffix}" if head else suffix


def product_folder_segment(
    name_en: str | None,
    product_id: str,
    *,
    name_zh: str | None = None,
    collide: bool = False,
) -> str:
    """Storage folder from name_en slug; else short id.

    Collision → append `-{first8}` of id. Never uses pinyin or zh→en translate.
    ``name_zh`` ignored (API compat).
    """
    label = english_label_for_folder(name_en, name_zh)
    folder = sanitize_product_name_slug(label)
    if not folder:
        return short_product_id_segment(product_id)
    if collide:
        return product_folder_with_id_suffix(folder, product_id)
    return folder


def is_uuid_product_folder(segment: str | None) -> bool:
    """True when folder looks like a legacy product-id UUID."""
    return bool(segment and _UUID_FOLDER.match(str(segment).strip()))


def normalize_product_category(category: str | None) -> str | None:
    """Map products.category to a Storage type folder key."""
    cat = (category or "").strip().lower()
    if cat in PRODUCT_CATEGORY_KEYS:
        return cat
    return None


def _product_key_segments(object_path: str | None) -> list[str]:
    return [p for p in (object_path or "").strip().strip("/").split("/") if p]


def _product_key_body_index(parts: list[str]) -> int | None:
    """Index of product slug folder in `products/…` keys; None if not a product key."""
    if len(parts) < 3 or parts[0] != "products" or parts[1] == _PENDING_FOLDER:
        return None
    idx = 1
    if parts[idx] in PRODUCT_CATEGORY_KEYS:
        idx += 1
    if idx >= len(parts):
        return None
    return idx


def product_category_from_object_key(object_path: str | None) -> str | None:
    """Return type folder when present (`pendant`, `ring`, …); else None."""
    parts = _product_key_segments(object_path)
    if len(parts) < 3 or parts[0] != "products" or parts[1] == _PENDING_FOLDER:
        return None
    if parts[1] in PRODUCT_CATEGORY_KEYS:
        return parts[1]
    return None


def product_object_key(
    folder_segment: str,
    metal_color: str | None,
    filename: str,
    *,
    category: str | None = None,
) -> str:
    """Build `products/{type}/{folder}/{metal}/{file}` (type/metal optional)."""
    folder = _safe_folder_segment(folder_segment, label="product_folder")
    file_part = _safe_path_segment(filename, label="filename")
    cat = normalize_product_category(category)
    metal = (metal_color or "").strip().lower()
    if metal and metal not in PRODUCT_METAL_FOLDERS:
        raise StorageUploadError(f"invalid metal_color for Storage path: {metal}")
    segments = ["products"]
    if cat:
        segments.append(cat)
    segments.append(folder)
    if metal:
        segments.append(metal)
    segments.append(file_part)
    return "/".join(segments)


def pending_product_object_key(
    metal_color: str | None,
    filename: str,
    *,
    category: str | None = None,
) -> str:
    """Build `products/_pending/{type}/{metal}/{file}` (type/metal optional)."""
    file_part = _safe_path_segment(filename, label="filename")
    cat = normalize_product_category(category)
    metal = (metal_color or "").strip().lower()
    if metal and metal not in PRODUCT_METAL_FOLDERS:
        raise StorageUploadError(f"invalid metal_color for Storage path: {metal}")
    segments = ["products", _PENDING_FOLDER]
    if cat:
        segments.append(cat)
    if metal:
        segments.append(metal)
    segments.append(file_part)
    return "/".join(segments)


def is_pending_product_object_key(object_path: str | None) -> bool:
    path = (object_path or "").strip().lstrip("/")
    return path.startswith(_PENDING_PREFIX) or path == "products/_pending"


def is_flat_product_object_key(object_path: str | None) -> bool:
    """True for legacy `products/{file}` (one segment, not `_pending`)."""
    parts = [p for p in (object_path or "").strip().strip("/").split("/") if p]
    return (
        len(parts) == 2
        and parts[0] == "products"
        and parts[1] != _PENDING_FOLDER
    )


def is_nested_product_object_key(object_path: str | None) -> bool:
    """True for nested product keys (legacy and type-scoped)."""
    parts = _product_key_segments(object_path)
    idx = _product_key_body_index(parts)
    if idx is None:
        return False
    tail_len = len(parts) - idx - 1
    if tail_len == 1:
        return True
    return tail_len == 2 and parts[idx + 1] in PRODUCT_METAL_FOLDERS


def product_folder_from_object_key(object_path: str | None) -> str | None:
    """Return slug folder for nested product keys; None for flat/pending."""
    parts = _product_key_segments(object_path)
    idx = _product_key_body_index(parts)
    if idx is None:
        return None
    return parts[idx]


def product_upload_relative_path(
    filename: str,
    *,
    folder: str | None = None,
    product_id: str | None = None,
    color_slot: str | None = None,
    category: str | None = None,
) -> str:
    """Relative key under kind `products` for upload_image / upload_bytes.

    Prefer `folder` (name slug). New uploads: `{type}/{folder}/{metal}/file`.
    """
    name = _safe_path_segment(filename, label="filename")
    folder_seg = (folder or product_id or "").strip()
    folder_seg = _safe_folder_segment(folder_seg) if folder_seg else ""
    cat = normalize_product_category(category)
    metal = metal_color_from_slot(color_slot)
    if folder_seg and cat and metal:
        return f"{cat}/{folder_seg}/{metal}/{name}"
    if folder_seg and cat:
        return f"{cat}/{folder_seg}/{name}"
    if folder_seg and metal:
        return f"{folder_seg}/{metal}/{name}"
    if folder_seg:
        return f"{folder_seg}/{name}"
    if cat and metal:
        return f"{_PENDING_FOLDER}/{cat}/{metal}/{name}"
    if cat:
        return f"{_PENDING_FOLDER}/{cat}/{name}"
    if metal:
        return f"{_PENDING_FOLDER}/{metal}/{name}"
    return f"{_PENDING_FOLDER}/{name}"


def move_object(source_path: str, dest_path: str) -> str:
    """Move object within the bucket; return public URL of destination."""
    src = (source_path or "").strip().lstrip("/")
    dst = (dest_path or "").strip().lstrip("/")
    if not src or not dst:
        raise StorageUploadError("Storage move failed: empty object path")
    if ".." in src.split("/") or ".." in dst.split("/"):
        raise StorageUploadError("Storage move failed: invalid object path")
    if src == dst:
        return public_url_for_object(dst)

    base, key, bucket = _require_config()
    move_url = f"{base}/storage/v1/object/move"
    payload = {
        "bucketId": bucket,
        "sourceKey": src,
        "destinationKey": dst,
    }
    headers = _storage_headers(key, content_type="application/json")
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(move_url, json=payload, headers=headers)
        if resp.status_code not in (200, 201):
            try:
                copy_object(src, dst)
            except StorageUploadError as copy_exc:
                detail = (resp.text or str(copy_exc) or "")[:200]
                raise StorageUploadError(
                    f"Storage move failed ({resp.status_code}): {detail}"
                ) from copy_exc
            del_url = _object_api_url(base, bucket, src)
            client.delete(del_url, headers=_storage_headers(key))
    return public_url_for_object(dst)


def copy_object(source_path: str, dest_path: str) -> str:
    """Copy object within the bucket; return public URL of destination."""
    src = (source_path or "").strip().lstrip("/")
    dst = (dest_path or "").strip().lstrip("/")
    if not src or not dst:
        raise StorageUploadError("Storage copy failed: empty object path")
    if ".." in src.split("/") or ".." in dst.split("/"):
        raise StorageUploadError("Storage copy failed: invalid object path")
    if src == dst:
        return public_url_for_object(dst)

    base, key, bucket = _require_config()
    copy_url = f"{base}/storage/v1/object/copy"
    payload = {
        "bucketId": bucket,
        "sourceKey": src,
        "destinationKey": dst,
    }
    headers = _storage_headers(key, content_type="application/json")
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(copy_url, json=payload, headers=headers)
        if resp.status_code not in (200, 201):
            detail = (resp.text or "")[:200]
            raise StorageUploadError(
                f"Storage copy failed ({resp.status_code}): {detail}"
            )
    return public_url_for_object(dst)


def _pending_key_parts(object_path: str) -> tuple[str | None, str | None, str | None]:
    """Parse pending key → (category, metal, filename)."""
    parts = _product_key_segments(object_path)
    if len(parts) < 3 or parts[0] != "products" or parts[1] != _PENDING_FOLDER:
        return None, None, None
    idx = 2
    cat: str | None = None
    if idx < len(parts) and parts[idx] in PRODUCT_CATEGORY_KEYS:
        cat = parts[idx]
        idx += 1
    if idx >= len(parts):
        return cat, None, None
    if idx == len(parts) - 1:
        return cat, None, parts[idx]
    if parts[idx] in PRODUCT_METAL_FOLDERS and idx == len(parts) - 2:
        return cat, parts[idx], parts[idx + 1]
    return cat, None, parts[-1]


def _nested_product_tail_parts(object_path: str) -> tuple[str | None, str | None]:
    """Parse nested product key tail → (metal, filename)."""
    parts = _product_key_segments(object_path)
    idx = _product_key_body_index(parts)
    if idx is None:
        return None, None
    tail = parts[idx + 1 :]
    if len(tail) == 1:
        return None, tail[0]
    if len(tail) == 2 and tail[0] in PRODUCT_METAL_FOLDERS:
        return tail[0], tail[1]
    return None, tail[-1] if tail else None


def relocate_product_object_url(
    url: str,
    old_folder: str,
    new_folder: str,
    *,
    category: str | None = None,
    shared: bool = False,
) -> str:
    """Move/copy object from old product folder to new; return new public URL.

    When `shared` is True, copy (leave source for other product refs). Best-effort:
    on Storage errors return the original URL.
    """
    if not url or old_folder == new_folder:
        return url
    if not is_supabase_storage_url(url):
        return url
    obj = object_path_from_public_url(url)
    if not obj:
        return url
    current = product_folder_from_object_key(obj)
    if current != old_folder:
        return url
    metal, filename = _nested_product_tail_parts(obj)
    if not filename:
        return url
    dest_cat = normalize_product_category(category) or product_category_from_object_key(obj)
    try:
        dest = product_object_key(new_folder, metal, filename, category=dest_cat)
    except StorageUploadError:
        return url
    if dest == obj:
        return url
    try:
        if shared:
            return copy_object(obj, dest)
        return move_object(obj, dest)
    except (StorageNotConfiguredError, StorageUploadError, httpx.HTTPError):
        return url


def promote_pending_product_url(
    url: str,
    folder_segment: str,
    metal: str | None = None,
    *,
    category: str | None = None,
) -> str:
    """Move `products/_pending/…` into `products/{type}/{folder}/{metal}/…`.

    Non-pending or non-Storage URLs are returned unchanged. On Storage errors
    the original URL is kept (best-effort, same spirit as delete_by_url).
    """
    if not url or not is_supabase_storage_url(url):
        return url
    obj = object_path_from_public_url(url)
    if not obj or not is_pending_product_object_key(obj):
        return url

    pending_cat, pending_metal, filename = _pending_key_parts(obj)
    if not filename:
        return url

    dest_metal = (metal or "").strip().lower() or pending_metal
    if dest_metal and dest_metal not in PRODUCT_METAL_FOLDERS:
        dest_metal = pending_metal
    dest_cat = normalize_product_category(category) or pending_cat
    try:
        dest = product_object_key(folder_segment, dest_metal, filename, category=dest_cat)
    except StorageUploadError:
        return url
    if dest == obj:
        return url
    try:
        return move_object(obj, dest)
    except (StorageNotConfiguredError, StorageUploadError, httpx.HTTPError):
        return url
