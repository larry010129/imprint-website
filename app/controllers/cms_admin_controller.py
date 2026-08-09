"""Admin APIs for modular CMS pages, copy slots, media, FAQ categories."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from app.auth import log_admin_action, require_admin
from app.auth_totp_service import step_up_from_body
from app.database import get_connection
from app.paging import page_meta, parse_paging_from_mapping
from config.settings import settings

router = APIRouter(prefix="/admin", tags=["admin-cms"])

_ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
_ALLOWED_IMAGE_MIME = {"image/png", "image/jpeg", "image/webp"}
_MAX_IMAGE_BYTES = 1 * 1024 * 1024


def _require_admin(request: Request) -> str:
    return require_admin(request)


def _step_up_response(admin_id: str, body: dict | None) -> JSONResponse | None:
    step = step_up_from_body(admin_id, body)
    if not step:
        return None
    status, message = step
    return JSONResponse(status_code=status, content={"error": message})


def _actor_email(user_id: str) -> str | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select email from users where id = %s", (user_id,))
        row = cur.fetchone()
    return row["email"] if row else None


def _valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _image_signature_matches(data: bytes, ext: str) -> bool:
    if ext == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if ext == ".webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


def _image_upload_error(file: UploadFile, data: bytes, ext: str) -> str | None:
    if ext not in _ALLOWED_IMAGE_EXT:
        return "僅支援 JPG / PNG / WEBP"
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct and ct not in _ALLOWED_IMAGE_MIME and ct not in {
        "application/octet-stream",
        "binary/octet-stream",
    }:
        return "僅支援 JPG / PNG / WEBP"
    if not data:
        return "empty file"
    if len(data) > _MAX_IMAGE_BYTES:
        return "來源圖片需小於 1MB"
    if not _image_signature_matches(data, ext):
        return "圖片內容與副檔名不符"
    return None


class _ClientImageError(str):
    """ensure_webp / client image failure — HTTP 400 (not storage 503)."""


def _upload_err_response(upload_err: str) -> JSONResponse:
    code = 400 if isinstance(upload_err, _ClientImageError) else 503
    return JSONResponse(status_code=code, content={"error": str(upload_err)})


def _storage_upload(kind: str, name: str, data: bytes, ext: str) -> tuple[str | None, str | None]:
    from app.image_convert import ImageConvertError, ensure_webp
    from app.storage import StorageNotConfiguredError, StorageUploadError, upload_image

    try:
        data, name, ext = ensure_webp(data, name, ext)
        return upload_image(kind, name, data, ext, upsert=True), None
    except ImageConvertError as exc:
        return None, _ClientImageError(str(exc))
    except StorageNotConfiguredError as exc:
        return None, str(exc)
    except StorageUploadError as exc:
        return None, str(exc)


_CMS_SCHEMA_READY = False


def _ensure_all(cur) -> None:
    """Run schema/seed once per process. Hot create/update must not re-seed.

    Startup lifespan already seeds; repeating every copy-slot upsert + legacy
    delete on each admin request was a major source of ~20s section-create latency.
    """
    global _CMS_SCHEMA_READY
    if _CMS_SCHEMA_READY:
        return
    from app.cms_copy_slots import ensure_page_copy_slots_schema, seed_page_copy_slots
    from app.cms_media import ensure_cms_media_schema
    from app.cms_pages import ensure_cms_pages_schema
    from app.cms_seed import remove_legacy_seeded_pages

    ensure_cms_pages_schema(cur)
    ensure_page_copy_slots_schema(cur)
    ensure_cms_media_schema(cur)
    seed_page_copy_slots(cur)
    remove_legacy_seeded_pages(cur)
    _CMS_SCHEMA_READY = True


# ── CMS pages ────────────────────────────────────────────────────────────────


@router.get("/cms-pages")
async def cms_pages_list(request: Request) -> dict:
    _require_admin(request)
    from app.cms_copy_slot_specs import EDITABLE_SITE_PAGES
    from app.cms_pages import count_all_pages, fetch_all_pages

    page, page_size, limit, offset = parse_paging_from_mapping(request.query_params)
    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        total = count_all_pages(cur)
        pages = fetch_all_pages(cur, limit=limit, offset=offset)
        for row in pages:
            slug = str(row.get("slug") or "")
            row["cms_path"] = f"/p/{slug}"
            # Keep DB site_route (host pages); modular pages stay null.
            if not row.get("site_route"):
                row["site_route"] = None
        out = {"pages": pages, "site_pages": list(EDITABLE_SITE_PAGES)}
        out.update(page_meta(page=page, page_size=page_size, total=total))
        return out


@router.get("/cms-site-page")
async def cms_site_page_get(request: Request) -> JSONResponse:
    """Ensure host page for a fixed site route; return page + sections."""
    _require_admin(request)
    route = str(request.query_params.get("route") or "").strip()
    from app.cms_copy_slot_specs import EDITABLE_SITE_PAGES
    from app.cms_pages import ensure_site_route_page, fetch_sections

    title_map = {item["route"]: item["title"] for item in EDITABLE_SITE_PAGES}
    if route not in title_map:
        return JSONResponse(status_code=400, content={"error": "route 無效或不可編輯"})
    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        try:
            page = ensure_site_route_page(cur, route, title_map[route])
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        sections = fetch_sections(cur, page["id"], visible_only=False)
    page["cms_path"] = f"/p/{page['slug']}"
    return JSONResponse(content={"page": page, "sections": sections})


@router.post("/cms-section-page-image")
async def cms_section_page_image_sync(request: Request) -> JSONResponse:
    """Upsert or clear page_images row for a CMS section media slot."""
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    section_id = str(body.get("sectionId") or body.get("section_id") or "").strip()
    action = str(body.get("action") or "upsert").strip()
    if not _valid_uuid(section_id) or action not in {"upsert", "delete", "hide"}:
        return JSONResponse(status_code=400, content={"error": "invalid sectionId/action"})
    from app.cms_pages import (
        delete_section_page_image,
        fetch_page_by_id,
        page_key_for_cms_page,
        serialize_section,
        upsert_section_page_image,
    )
    from app.controllers.web_controller import clear_page_image_cache

    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        cur.execute("select * from cms_page_sections where id = %s", (section_id,))
        section_row = cur.fetchone()
        if not section_row:
            return JSONResponse(status_code=404, content={"error": "找不到區塊"})
        section = serialize_section(section_row)
        page = fetch_page_by_id(cur, str(section["page_id"]))
        if not page:
            return JSONResponse(status_code=404, content={"error": "找不到頁面"})
        page_key = page_key_for_cms_page(page)
        if not page_key:
            return JSONResponse(status_code=400, content={"error": "page_key 無效"})
        try:
            if action in {"delete", "hide"}:
                ok = delete_section_page_image(
                    cur, page_key=page_key, section_id=section_id, hide=action == "hide"
                )
                clear_page_image_cache()
                log_admin_action(
                    _actor_email(user_id),
                    f"cms_section_page_image_{action}",
                    {"section_id": section_id, "page_key": page_key},
                )
                return JSONResponse(content={"ok": ok})
            props = section.get("props") or {}
            image_url = body.get("imageUrl") if "imageUrl" in body else body.get("image_url")
            if image_url is None:
                image_url = props.get("image_url") or ""
            image_alt = body.get("imageAlt") if "imageAlt" in body else body.get("image_alt")
            if image_alt is None:
                image_alt = props.get("image_alt") or ""
            image_webp = body.get("imageWebp") if "imageWebp" in body else body.get("image_webp")
            row = upsert_section_page_image(
                cur,
                page_key=page_key,
                section_id=section_id,
                section_type=str(section.get("type") or ""),
                image_url=str(image_url or ""),
                image_alt=str(image_alt or ""),
                image_webp=None if image_webp is None else str(image_webp or ""),
            )
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
    clear_page_image_cache()
    log_admin_action(
        _actor_email(user_id),
        "cms_section_page_image_upsert",
        {"section_id": section_id, "page_key": page_key},
    )
    return JSONResponse(content={"ok": True, "pageImage": row})


@router.post("/cms-pages")
async def cms_pages_create(request: Request) -> JSONResponse:
    """Create campaign pages disabled — admin only edits finished site pages."""
    _require_admin(request)
    return JSONResponse(
        status_code=410,
        content={"error": "已停用新建頁面，僅可編輯現有官網頁面的文字與圖片"},
    )


@router.get("/cms-pages/{page_id}")
async def cms_pages_get(request: Request, page_id: str) -> JSONResponse:
    """Admin JSON for Next SSR — page + ordered sections + full normalized props."""
    _require_admin(request)
    if not _valid_uuid(page_id):
        return JSONResponse(status_code=400, content={"error": "id 無效"})
    from app.cms_pages import fetch_page_with_sections

    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        page = fetch_page_with_sections(cur, page_id=page_id)
    if not page:
        return JSONResponse(status_code=404, content={"error": "找不到頁面"})
    sections = page.get("sections") or []
    page["cms_path"] = f"/p/{page['slug']}"
    return JSONResponse(content={"page": page, "sections": sections})


@router.post("/cms-page-update")
async def cms_pages_update(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    page_id = str(body.get("id") or "").strip()
    if not _valid_uuid(page_id):
        return JSONResponse(status_code=400, content={"error": "id 無效"})
    from app.cms_pages import parse_page_payload, update_page

    fields, err = parse_page_payload(body, partial=True)
    if err:
        return JSONResponse(status_code=400, content={"error": err})
    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        try:
            page = update_page(cur, page_id, fields or {})
        except Exception as exc:
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                return JSONResponse(status_code=409, content={"error": "slug 已存在"})
            raise
    if not page:
        return JSONResponse(status_code=404, content={"error": "找不到頁面"})
    log_admin_action(_actor_email(user_id), "cms_page_updated", {"id": page_id})
    return JSONResponse(content={"page": page})


@router.post("/cms-page-action")
async def cms_page_action(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    step_resp = _step_up_response(user_id, body)
    if step_resp:
        return step_resp
    page_id = str(body.get("id") or "").strip()
    action = str(body.get("action") or "").strip()
    if not _valid_uuid(page_id) or action not in {"publish", "unpublish", "delete"}:
        return JSONResponse(status_code=400, content={"error": "invalid id/action"})
    from app.cms_pages import delete_page, update_page

    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        if action == "delete":
            ok = delete_page(cur, page_id)
            if not ok:
                return JSONResponse(status_code=404, content={"error": "找不到頁面"})
        else:
            status = "published" if action == "publish" else "draft"
            page = update_page(cur, page_id, {"status": status})
            if not page:
                return JSONResponse(status_code=404, content={"error": "找不到頁面"})
    log_admin_action(_actor_email(user_id), f"cms_page_{action}", {"id": page_id})
    return JSONResponse(content={"ok": True})


# ── Sections ─────────────────────────────────────────────────────────────────


@router.post("/cms-pages/{page_id}/sections")
async def cms_section_create(request: Request, page_id: str) -> JSONResponse:
    user_id = _require_admin(request)
    if not _valid_uuid(page_id):
        return JSONResponse(status_code=400, content={"error": "page id 無效"})
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    from app.cms_pages import create_section, fetch_page_by_id, parse_section_payload

    fields, err = parse_section_payload(body)
    if err:
        return JSONResponse(status_code=400, content={"error": err})
    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        if not fetch_page_by_id(cur, page_id):
            return JSONResponse(status_code=404, content={"error": "找不到頁面"})
        section = create_section(cur, page_id, fields)  # type: ignore[arg-type]
    log_admin_action(
        _actor_email(user_id),
        "cms_section_created",
        {"page_id": page_id, "type": section["type"]},
    )
    return JSONResponse(content={"section": section})


@router.get("/cms-sections/{section_id}/html")
async def cms_section_html(request: Request, section_id: str) -> JSONResponse:
    """JSON section payload for preview sync (HTML Jinja removed — Next owns render)."""
    _require_admin(request)
    if not _valid_uuid(section_id):
        return JSONResponse(status_code=400, content={"error": "id 無效"})
    from app.cms_pages import SECTION_TYPES, serialize_section

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select * from cms_page_sections where id = %s", (section_id,))
        row = cur.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "找不到區塊"})
        section = serialize_section(row)
        if section.get("type") not in SECTION_TYPES:
            return JSONResponse(status_code=400, content={"error": "不支援的區塊類型"})
    # Soft HTML patch retired; editor falls back to hard iframe refresh.
    return JSONResponse(content={"section": section, "html": None})


@router.post("/cms-section-update")
async def cms_section_update(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    section_id = str(body.get("id") or "").strip()
    if not _valid_uuid(section_id):
        return JSONResponse(status_code=400, content={"error": "id 無效"})
    from app.cms_pages import (
        fetch_page_by_id,
        parse_section_payload,
        sync_section_page_image_from_props,
        update_section,
    )
    from app.controllers.web_controller import clear_page_image_cache

    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        cur.execute("select type, page_id from cms_page_sections where id = %s", (section_id,))
        existing = cur.fetchone()
        if not existing:
            return JSONResponse(status_code=404, content={"error": "找不到區塊"})
        section_type = str(body.get("type") or existing["type"])
        props = body.get("props") if "props" in body else None
        payload = {"type": section_type}
        if props is not None:
            payload["props"] = props
        if "isVisible" in body or "is_visible" in body:
            payload["isVisible"] = body.get("isVisible", body.get("is_visible"))
        fields, err = parse_section_payload(payload)
        if err:
            return JSONResponse(status_code=400, content={"error": err})
        assert fields
        patch = {}
        if "type" in body:
            patch["type"] = fields["type"]
        if props is not None:
            patch["props"] = fields["props"]
        if "isVisible" in body or "is_visible" in body:
            patch["is_visible"] = fields["is_visible"]
        section = update_section(cur, section_id, patch)
        if section and props is not None:
            page = fetch_page_by_id(cur, str(existing["page_id"]))
            if page:
                sync_section_page_image_from_props(cur, section, page)
                clear_page_image_cache()
    if not section:
        return JSONResponse(status_code=404, content={"error": "找不到區塊"})
    log_admin_action(_actor_email(user_id), "cms_section_updated", {"id": section_id})
    return JSONResponse(content={"section": section})


@router.post("/cms-section-action")
async def cms_section_action(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    section_id = str(body.get("id") or "").strip()
    action = str(body.get("action") or "").strip()
    if not _valid_uuid(section_id) or action not in {"delete", "show", "hide"}:
        return JSONResponse(status_code=400, content={"error": "invalid id/action"})
    if action == "delete":
        step_resp = _step_up_response(user_id, body)
        if step_resp:
            return step_resp
    from app.cms_pages import (
        delete_section,
        delete_section_page_image,
        fetch_page_by_id,
        page_key_for_cms_page,
        update_section,
    )
    from app.controllers.web_controller import clear_page_image_cache

    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        if action == "delete":
            cur.execute(
                "select page_id, type from cms_page_sections where id = %s",
                (section_id,),
            )
            existing = cur.fetchone()
            if not existing:
                return JSONResponse(status_code=404, content={"error": "找不到區塊"})
            page = fetch_page_by_id(cur, str(existing["page_id"]))
            ok = delete_section(cur, section_id)
            if not ok:
                return JSONResponse(status_code=404, content={"error": "找不到區塊"})
            if page:
                page_key = page_key_for_cms_page(page)
                if page_key:
                    delete_section_page_image(
                        cur, page_key=page_key, section_id=section_id, hide=False
                    )
                    clear_page_image_cache()
        else:
            section = update_section(cur, section_id, {"is_visible": action == "show"})
            if not section:
                return JSONResponse(status_code=404, content={"error": "找不到區塊"})
    log_admin_action(_actor_email(user_id), f"cms_section_{action}", {"id": section_id})
    return JSONResponse(content={"ok": True})


@router.patch("/cms-pages/{page_id}/sections/reorder")
async def cms_sections_reorder(request: Request, page_id: str) -> JSONResponse:
    user_id = _require_admin(request)
    if not _valid_uuid(page_id):
        return JSONResponse(status_code=400, content={"error": "page id 無效"})
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    ordered = body.get("sectionIds") or body.get("section_ids") or body.get("ids") or []
    if not isinstance(ordered, list) or not ordered:
        return JSONResponse(status_code=400, content={"error": "缺少 sectionIds"})
    from app.cms_pages import fetch_page_by_id, reorder_sections

    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        if not fetch_page_by_id(cur, page_id):
            return JSONResponse(status_code=404, content={"error": "找不到頁面"})
        try:
            sections = reorder_sections(cur, page_id, [str(x) for x in ordered])
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
    log_admin_action(_actor_email(user_id), "cms_sections_reordered", {"page_id": page_id})
    return JSONResponse(content={"sections": sections})


# ── Copy slots (Phase 1) ─────────────────────────────────────────────────────


@router.get("/page-copy-slots")
async def page_copy_slots_list(request: Request) -> dict:
    _require_admin(request)
    from app.cms_copy_slots import fetch_all_copy_slots
    from app.cms_copy_slot_specs import EDITABLE_SITE_PAGES

    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        return {
            "slots": fetch_all_copy_slots(cur),
            "pages": list(EDITABLE_SITE_PAGES),
        }


@router.post("/page-copy-slot-update")
async def page_copy_slot_update(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    from app.cms_copy_slots import parse_copy_slot_payload, update_copy_slot
    from app.controllers.web_controller import clear_page_copy_cache

    fields, err = parse_copy_slot_payload(body)
    if err:
        return JSONResponse(status_code=400, content={"error": err})
    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        row = update_copy_slot(cur, fields)  # type: ignore[arg-type]
    if not row:
        return JSONResponse(status_code=404, content={"error": "找不到文案區塊"})
    clear_page_copy_cache()
    log_admin_action(
        _actor_email(user_id),
        "page_copy_slot_updated",
        {"page_key": fields["page_key"], "slot_key": fields["slot_key"]},  # type: ignore[index]
    )
    return JSONResponse(content={"slot": row})


# ── Media library ────────────────────────────────────────────────────────────


@router.get("/cms-media")
async def cms_media_list(request: Request) -> dict:
    _require_admin(request)
    from app.cms_media import count_media, fetch_media

    page, page_size, limit, offset = parse_paging_from_mapping(request.query_params)
    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        total = count_media(cur)
        media = fetch_media(cur, limit=limit, offset=offset)
        out = {"media": media}
        out.update(page_meta(page=page, page_size=page_size, total=total))
        return out


@router.post("/cms-media-upload")
async def cms_media_upload(request: Request, file: UploadFile = File(...)) -> JSONResponse:
    user_id = _require_admin(request)
    if not file.filename:
        return JSONResponse(status_code=400, content={"error": "missing file"})
    ext = Path(file.filename).suffix.lower()
    data = await file.read()
    err = _image_upload_error(file, data, ext)
    if err:
        return JSONResponse(status_code=400, content={"error": err})
    name = f"{uuid.uuid4().hex}{ext}"
    url, upload_err = _storage_upload("cms-media", name, data, ext)
    if upload_err:
        return _upload_err_response(upload_err)
    from app.cms_media import create_media

    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        item = create_media(cur, url=url, filename=file.filename or name)
    log_admin_action(_actor_email(user_id), "cms_media_uploaded", {"id": item["id"]})
    return JSONResponse(content={"media": item, "url": url})


@router.post("/cms-media-action")
async def cms_media_action(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    media_id = str((body or {}).get("id") or "").strip()
    action = str((body or {}).get("action") or "").strip()
    if not _valid_uuid(media_id) or action != "delete":
        return JSONResponse(status_code=400, content={"error": "invalid id/action"})
    from app.cms_media import delete_media

    with get_connection() as conn, conn.cursor() as cur:
        _ensure_all(cur)
        url = delete_media(cur, media_id)
    if not url:
        return JSONResponse(status_code=404, content={"error": "找不到媒體"})
    from app.storage import delete_by_url

    delete_by_url(url)
    if url.startswith("/static/uploads/cms-media/"):
        legacy = settings.static_dir / "uploads" / "cms-media" / Path(url).name
        legacy.unlink(missing_ok=True)
    log_admin_action(_actor_email(user_id), "cms_media_deleted", {"id": media_id})
    return JSONResponse(content={"ok": True})


# ── FAQ category CRUD (Phase 4) ──────────────────────────────────────────────


@router.post("/faq-categories")
async def faq_category_create(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    from app.content import new_faq_id, serialize_faq_category

    title = str(body.get("title") or "").strip()
    if not title:
        return JSONResponse(status_code=400, content={"error": "請填寫分類名稱"})
    cat_id = str(body.get("id") or "").strip() or new_faq_id("faq-cat")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", cat_id):
        return JSONResponse(status_code=400, content={"error": "分類 id 無效"})
    try:
        sort_order = int(body.get("sortOrder") if body.get("sortOrder") not in (None, "") else 0)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"error": "排序無效"})
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id from faq_categories where id = %s", (cat_id,))
        if cur.fetchone():
            return JSONResponse(status_code=409, content={"error": "分類 id 已存在"})
        cur.execute(
            "insert into faq_categories (id, title, sort_order) values (%s, %s, %s) returning *",
            (cat_id, title, sort_order),
        )
        row = serialize_faq_category(cur.fetchone())
    log_admin_action(_actor_email(user_id), "faq_category_created", {"id": cat_id})
    return JSONResponse(content={"category": row})


@router.post("/faq-category-update")
async def faq_category_update(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    from app.content import serialize_faq_category

    cat_id = str(body.get("id") or "").strip()
    title = str(body.get("title") or "").strip()
    if not cat_id or not title:
        return JSONResponse(status_code=400, content={"error": "請填寫分類 id 與名稱"})
    try:
        sort_order = int(body.get("sortOrder") if body.get("sortOrder") not in (None, "") else 0)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"error": "排序無效"})
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            update faq_categories set title = %s, sort_order = %s
            where id = %s returning *
            """,
            (title, sort_order, cat_id),
        )
        row = cur.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "找不到分類"})
        out = serialize_faq_category(row)
    log_admin_action(_actor_email(user_id), "faq_category_updated", {"id": cat_id})
    return JSONResponse(content={"category": out})


@router.post("/faq-category-action")
async def faq_category_action(request: Request) -> JSONResponse:
    user_id = _require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    step_resp = _step_up_response(user_id, body)
    if step_resp:
        return step_resp
    cat_id = str(body.get("id") or "").strip()
    action = str(body.get("action") or "").strip()
    if not cat_id or action != "delete":
        return JSONResponse(status_code=400, content={"error": "invalid id/action"})
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select count(*) as c from faq_items where category_id = %s", (cat_id,))
        count = int(cur.fetchone()["c"])
        if count > 0:
            return JSONResponse(
                status_code=400,
                content={"error": f"此分類尚有 {count} 則 FAQ，請先移動或刪除"},
            )
        cur.execute("delete from faq_categories where id = %s returning id", (cat_id,))
        if not cur.fetchone():
            return JSONResponse(status_code=404, content={"error": "找不到分類"})
    log_admin_action(_actor_email(user_id), "faq_category_deleted", {"id": cat_id})
    return JSONResponse(content={"ok": True})
