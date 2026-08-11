"""Admin release notes — JSON store, unlock cookie, draft/publish helpers."""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from fastapi import HTTPException, Request, Response

from app.auth import _is_secure_request, _jwt_secret
from config.settings import settings

STORE_PATH = settings.site_root / "content" / "admin" / "release-notes.json"
HISTORY_CAP = 20
UNLOCK_COOKIE_NAME = "imprint_rn_unlock"
UNLOCK_MINUTES = 120
CODE_RE = re.compile(r"^[0-9A-Za-z]{6}$")
DEFAULT_PASSWORD = "010129"
_MAX_VERSION = 40
_MAX_TITLE = 120
_MAX_NOTE = 500
_MAX_NOTES = 40

ADMIN_NAV_KEYS = (
    "dash",
    "orders",
    "products",
    "accounts",
    "member-search",
    "invites",
    "coupons",
    "leads",
    "pricing",
    "membership",
    "content",
    "featured-video",
    "settings",
    "plugins",
)


def release_notes_password() -> str:
    raw = (settings.admin_release_notes_password or "").strip()
    return raw or DEFAULT_PASSWORD


def normalize_code(code: Any) -> str | None:
    if not isinstance(code, str):
        return None
    value = code.strip()
    if not CODE_RE.fullmatch(value):
        return None
    return value


def codes_match(provided: str, expected: str) -> bool:
    a = provided.encode("utf-8")
    b = expected.encode("utf-8")
    if len(a) != len(b):
        secrets.compare_digest(a, a)
        return False
    return secrets.compare_digest(a, b)


def sign_unlock(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "purpose": "release_notes_unlock",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=UNLOCK_MINUTES),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def verify_unlock_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != "release_notes_unlock":
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None


def set_unlock_cookie(response: Response, user_id: str, request: Request) -> None:
    response.set_cookie(
        key=UNLOCK_COOKIE_NAME,
        value=sign_unlock(user_id),
        path="/",
        httponly=True,
        secure=_is_secure_request(request),
        samesite="lax",
        max_age=UNLOCK_MINUTES * 60,
    )


def unlock_user_id(request: Request) -> str | None:
    token = request.cookies.get(UNLOCK_COOKIE_NAME)
    if not token:
        return None
    return verify_unlock_token(token)


def require_unlock(request: Request, user_id: str) -> bool:
    unlocked = unlock_user_id(request)
    return bool(unlocked and unlocked == user_id)


def _default_store() -> dict[str, Any]:
    return {
        "draft": {"version": "1.0.0", "title": "", "notes": []},
        "published": None,
        "history": [],
        "nav_visibility": default_nav_visibility(),
    }


def default_nav_visibility() -> dict[str, bool]:
    return {key: True for key in ADMIN_NAV_KEYS}


def normalize_nav_visibility(raw: Any) -> dict[str, bool]:
    visibility = default_nav_visibility()
    if isinstance(raw, dict):
        for key in ADMIN_NAV_KEYS:
            if isinstance(raw.get(key), bool):
                visibility[key] = raw[key]
    return visibility


def _normalize_draft(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return _default_store()["draft"]
    notes = raw.get("notes")
    if not isinstance(notes, list):
        notes = []
    return {
        "version": str(raw.get("version") or "").strip(),
        "title": str(raw.get("title") or "").strip(),
        "notes": [str(n).strip() for n in notes if str(n).strip()],
    }


def _normalize_published(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    release_id = str(raw.get("releaseId") or "").strip()
    if not release_id:
        return None
    draft = _normalize_draft(raw)
    return {
        "releaseId": release_id,
        "version": draft["version"],
        "title": draft["title"],
        "notes": draft["notes"],
        "publishedAt": str(raw.get("publishedAt") or "").strip(),
    }


def _normalize_store(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return _default_store()
    history_raw = raw.get("history")
    history: list[dict[str, Any]] = []
    if isinstance(history_raw, list):
        for item in history_raw:
            pub = _normalize_published(item)
            if pub:
                history.append(pub)
    return {
        "draft": _normalize_draft(raw.get("draft")),
        "published": _normalize_published(raw.get("published")),
        "history": history[:HISTORY_CAP],
        "nav_visibility": normalize_nav_visibility(raw.get("nav_visibility")),
    }


_KV_KEY = "release-notes"


def _read_legacy_file(target: Path) -> dict[str, Any] | None:
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def load_store(path: Path | None = None) -> dict[str, Any]:
    """Default path → shared DB (cms_kv, one-time legacy import); explicit
    path → file (tests/tools)."""
    if path is not None:
        data = _read_legacy_file(path)
    else:
        from app.cms_kv_store import kv_get_or_import_file

        data = kv_get_or_import_file(_KV_KEY, lambda: _read_legacy_file(STORE_PATH))
    if not isinstance(data, dict):
        return _default_store()
    return _normalize_store(data)


def save_store(data: dict[str, Any], path: Path | None = None) -> None:
    """Default path → shared DB only (raises on failure); explicit path → file."""
    payload = _normalize_store(data)
    if path is None:
        from app.cms_kv_store import kv_set

        kv_set(_KV_KEY, payload)
        return
    target = path
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=".release-notes-", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def validate_draft_fields(
    body: dict[str, Any] | None,
    *,
    require_notes: bool = False,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(body, dict):
        return None, "invalid draft"
    version = str(body.get("version") or "").strip()
    title = str(body.get("title") or "").strip()
    notes_raw = body.get("notes")
    if not version:
        return None, "version required"
    if len(version) > _MAX_VERSION:
        return None, "version too long"
    if not title:
        return None, "title required"
    if len(title) > _MAX_TITLE:
        return None, "title too long"
    if notes_raw is None:
        notes_raw = []
    if not isinstance(notes_raw, list):
        return None, "notes must be a list"
    notes: list[str] = []
    for item in notes_raw:
        text = str(item).strip()
        if not text:
            continue
        if len(text) > _MAX_NOTE:
            return None, "note too long"
        notes.append(text)
    if len(notes) > _MAX_NOTES:
        return None, "too many notes"
    if require_notes and not notes:
        return None, "notes required"
    return {"version": version, "title": title, "notes": notes}, None


def save_draft(body: dict[str, Any]) -> dict[str, Any]:
    draft, err = validate_draft_fields(body, require_notes=False)
    if err or not draft:
        raise HTTPException(status_code=400, detail=err or "invalid draft")
    store = load_store()
    store["draft"] = draft
    save_store(store)
    return draft


def publish_draft() -> dict[str, Any]:
    store = load_store()
    draft = _normalize_draft(store.get("draft"))
    validated, err = validate_draft_fields(draft, require_notes=True)
    if err or not validated:
        raise HTTPException(status_code=400, detail=err or "invalid draft")
    previous = _normalize_published(store.get("published"))
    history = list(store.get("history") or [])
    if previous:
        history = [
            previous,
            *[h for h in history if h.get("releaseId") != previous["releaseId"]],
        ]
    published = {
        "releaseId": str(uuid.uuid4()),
        "version": validated["version"],
        "title": validated["title"],
        "notes": validated["notes"],
        "publishedAt": datetime.now(timezone.utc).isoformat(),
    }
    next_store = {
        "draft": validated,
        "published": published,
        "history": history[:HISTORY_CAP],
    }
    save_store(next_store)
    return published
