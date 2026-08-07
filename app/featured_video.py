"""Home / About featured YouTube gallery — JSON store + validation."""

from __future__ import annotations

import json
import logging
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

MAX_VIDEOS = 6
CHANNEL_CANDIDATE_LIMIT = 15
FEATURED_VIDEO_TTL_SECONDS = 24 * 60 * 60
# Cheap RSS/page peek so home load can detect a new upload inside the daily TTL.
CHANNEL_HEAD_CHECK_TTL_SECONDS = 20 * 60
_STAMPEDE_LOCK_SECONDS = 120
IMPRINT_CHANNEL_ID = "UCiI_Xayu0OrUT2swTeV6zTw"
IMPRINT_CHANNEL_HANDLE = "@imprintdiamond"
IMPRINT_CHANNEL_URL = "https://www.youtube.com/@imprintdiamond"
_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_DEFAULT_PATH = Path(__file__).resolve().parent / "data" / "featured-video.json"
# About copy only — never gates channel sync / gallery replace.
_META_KEYS = ("source", "eyebrow", "heading", "lead")
_logger = logging.getLogger(__name__)


def parse_youtube_id(value: str | None) -> str | None:
    """Extract an 11-char YouTube ID from watch / youtu.be / embed / shorts / raw."""
    raw = (value or "").strip()
    if not raw:
        return None
    if _YOUTUBE_ID_RE.fullmatch(raw):
        return raw

    candidate = raw
    if "://" not in candidate and candidate.startswith(("www.", "youtube.", "youtu.be")):
        candidate = f"https://{candidate}"

    try:
        parsed = urlparse(candidate)
    except ValueError:
        return None

    host = (parsed.netloc or "").lower().removeprefix("www.")
    path = (parsed.path or "").strip("/")

    if host in {"youtu.be", "m.youtu.be"} and path:
        vid = path.split("/")[0]
        return vid if _YOUTUBE_ID_RE.fullmatch(vid) else None

    if host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        qs = parse_qs(parsed.query)
        if "v" in qs and qs["v"]:
            vid = qs["v"][0].strip()
            if _YOUTUBE_ID_RE.fullmatch(vid):
                return vid
        parts = path.split("/")
        if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live", "v"}:
            vid = parts[1]
            if _YOUTUBE_ID_RE.fullmatch(vid):
                return vid

    return None


def _video_dict(
    youtube_id: str,
    title: str,
    label: str,
    published_at: str | None = None,
) -> dict[str, str]:
    row: dict[str, str] = {
        "youtubeId": youtube_id,
        "title": title,
        "label": label,
        "youtube_id": youtube_id,
    }
    if published_at:
        row["publishedAt"] = published_at
    return row


def normalize_video_item(item: Any, *, index: int = 0) -> dict[str, str] | None:
    """Normalize one video row; accept youtubeId / youtube_id / url fields."""
    if not isinstance(item, dict):
        return None
    raw_id = (
        item.get("youtubeId")
        or item.get("youtube_id")
        or item.get("url")
        or item.get("youtubeUrl")
        or item.get("youtube_url")
        or ""
    )
    youtube_id = parse_youtube_id(str(raw_id))
    if not youtube_id:
        return None
    default_label = f"品牌影片 {index + 1}"
    title = str(item.get("title") or default_label).strip() or default_label
    label = str(item.get("label") or title).strip() or title
    published_at = str(item.get("publishedAt") or item.get("published_at") or "").strip() or None
    return _video_dict(youtube_id, title, label, published_at)


def videos_from_payload(data: dict[str, Any]) -> list[dict[str, str]]:
    """Build up to 6 videos from new `videos` list or legacy single youtube_id."""
    raw_videos = data.get("videos")
    if isinstance(raw_videos, list) and raw_videos:
        out: list[dict[str, str]] = []
        for i, item in enumerate(raw_videos[:MAX_VIDEOS]):
            normalized = normalize_video_item(item, index=i)
            if normalized:
                out.append(normalized)
        return out

    legacy_id = parse_youtube_id(
        str(data.get("youtube_id") or data.get("youtubeId") or "")
    )
    if not legacy_id:
        return []
    title = str(data.get("title") or "DNA 鑽石製作流程影片").strip()
    label = str(data.get("label") or title).strip() or title
    return [_video_dict(legacy_id, title, label)]


def _meta_from_data(data: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for key in _META_KEYS:
        if key in data and data[key] is not None:
            meta[key] = data[key]
    return meta


def public_featured_payload(data: dict[str, Any]) -> dict[str, Any] | None:
    """Shape for Jinja: gallery list + primary fields (legacy youtube_id)."""
    if not data.get("enabled"):
        return None
    videos = videos_from_payload(data)
    if not videos:
        return None
    primary = videos[0]
    payload: dict[str, Any] = {
        "enabled": True,
        "youtube_id": primary["youtubeId"],
        "youtubeId": primary["youtubeId"],
        "title": primary["title"],
        "label": primary["label"],
        "videos": videos,
        "primary": {
            "youtubeId": primary["youtubeId"],
            "youtube_id": primary["youtubeId"],
            "title": primary["title"],
            "label": primary["label"],
        },
    }
    payload.update(_meta_from_data(data))
    return payload


def admin_featured_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Normalized admin read model (enabled may be false; videos padded empty OK)."""
    videos = videos_from_payload(data)
    payload: dict[str, Any] = {
        "enabled": bool(data.get("enabled")),
        "videos": [
            {
                **{
                    "youtubeId": v["youtubeId"],
                    "title": v["title"],
                    "label": v["label"],
                },
                **({"publishedAt": v["publishedAt"]} if v.get("publishedAt") else {}),
            }
            for v in videos
        ],
    }
    payload.update(_meta_from_data(data))
    if videos:
        payload["youtube_id"] = videos[0]["youtubeId"]
        payload["title"] = videos[0]["title"]
    elif data.get("youtube_id") or data.get("youtubeId"):
        payload["youtube_id"] = data.get("youtube_id") or data.get("youtubeId")
        if data.get("title"):
            payload["title"] = data["title"]
    return payload


def read_featured_video_file(path: Path | None = None) -> dict[str, Any]:
    target = path or _DEFAULT_PATH
    if not target.is_file():
        return {"enabled": False, "videos": []}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"enabled": False, "videos": []}
    if not isinstance(data, dict):
        return {"enabled": False, "videos": []}
    return data


def _fetch_channel_candidates(
    *,
    limit: int = CHANNEL_CANDIDATE_LIMIT,
) -> list[dict]:
    """Newest channel uploads for gallery backfill / sync. Empty on failure."""
    from app.youtube_channel import fetch_latest_channel_videos, resolve_channel_id

    channel_id = resolve_channel_id(IMPRINT_CHANNEL_ID, IMPRINT_CHANNEL_HANDLE)
    if not channel_id:
        return []
    try:
        return fetch_latest_channel_videos(channel_id, limit=max(limit, MAX_VIDEOS))
    except Exception as exc:  # noqa: BLE001 — never break page render
        _logger.warning("featured video channel backfill fetch failed: %s", exc)
        return []


def backfill_embeddable_gallery(
    kept: list[dict[str, str]],
    *,
    skip_ids: set[str],
    limit: int = MAX_VIDEOS,
    check_embeddable=None,
    referer: str | None = None,
    fetch_candidates: Callable[[], list[dict]] | None = None,
) -> list[dict[str, str]]:
    """Fill gaps from newest-first channel candidates (skip unplayable / known ids).

    Does not reshuffle ``kept`` — callers that need a full newest-6 replace should
    run ``run_featured_video_channel_sync`` / ``ensure_featured_video_fresh`` first.
    Candidates are walked in channel order; only the next embeddable ids after
    ``skip_ids`` are appended (never random older picks).
    """
    if len(kept) >= limit:
        return kept

    from app.youtube_channel import filter_embeddable_videos

    try:
        raw = fetch_candidates() if fetch_candidates else _fetch_channel_candidates()
    except Exception as exc:  # noqa: BLE001 — keep partial gallery
        _logger.warning("featured video backfill candidates failed: %s", exc)
        return kept

    extras: list[dict[str, str]] = []
    seen = set(skip_ids)
    for i, item in enumerate(raw or []):
        normalized = normalize_video_item(item, index=i)
        if not normalized:
            continue
        vid = normalized["youtubeId"]
        if vid in seen:
            continue
        seen.add(vid)
        extras.append(normalized)

    need = limit - len(kept)
    filled = filter_embeddable_videos(
        extras,
        limit=need,
        check_embeddable=check_embeddable,
        referer=referer,
    )
    return kept + filled


def _gallery_ids(videos: list[dict[str, str]]) -> list[str]:
    return [v["youtubeId"] for v in videos]


def _persist_repaired_gallery(
    data: dict[str, Any],
    videos: list[dict[str, str]],
    path: Path | None,
) -> None:
    """Write repaired embeddable gallery; preserve about meta + enabled."""
    saved: dict[str, Any] = {
        "enabled": bool(data.get("enabled", True)),
        "videos": [
            {k: v for k, v in row.items() if k != "youtube_id"} for row in videos
        ],
    }
    if data.get("syncedAt") or data.get("synced_at"):
        saved["syncedAt"] = data.get("syncedAt") or data.get("synced_at")
    for key in _META_KEYS:
        if key in data:
            saved[key] = data[key]
    if videos:
        saved["youtube_id"] = videos[0]["youtubeId"]
        saved["title"] = videos[0]["title"]
    try:
        save_featured_video_file(saved, path)
    except OSError as exc:
        _logger.warning("featured video repair persist failed: %s", exc)


def load_featured_video(
    path: Path | None = None,
    *,
    check_embeddable=None,
    embed_referer: str | None = None,
    fetch_candidates: Callable[[], list[dict]] | None = None,
    persist_repair: bool = True,
) -> dict[str, Any] | None:
    """Public loader used by web_controller for home / about Jinja context.

    Drops non-embeddable IDs (embed-page check) so stale JSON cannot surface a
    blocked primary or gallery thumb. When filtering leaves fewer than
    ``MAX_VIDEOS``, backfills from channel candidates (same embed check +
    referer) and optionally persists the repaired list. Pass
    ``check_embeddable`` / ``fetch_candidates`` in tests to avoid network.
    ``embed_referer`` should be the page origin (request base URL) so
    domain-restricted clips are filtered for the viewer host.
    """
    data = read_featured_video_file(path)
    if not data.get("enabled"):
        return None
    videos = videos_from_payload(data)
    if not videos:
        return None

    from app.youtube_channel import filter_embeddable_videos

    embeddable = filter_embeddable_videos(
        videos,
        limit=MAX_VIDEOS,
        check_embeddable=check_embeddable,
        referer=embed_referer,
    )
    if len(embeddable) < MAX_VIDEOS:
        embeddable = backfill_embeddable_gallery(
            embeddable,
            skip_ids={v["youtubeId"] for v in videos},
            limit=MAX_VIDEOS,
            check_embeddable=check_embeddable,
            referer=embed_referer,
            fetch_candidates=fetch_candidates,
        )
    if not embeddable:
        return None

    if persist_repair and _gallery_ids(embeddable) != _gallery_ids(videos):
        _persist_repaired_gallery(data, embeddable, path)

    filtered = dict(data)
    filtered["videos"] = embeddable
    filtered["youtube_id"] = embeddable[0]["youtubeId"]
    filtered["title"] = embeddable[0]["title"]
    return public_featured_payload(filtered)


def validate_admin_body(
    body: dict[str, Any],
    *,
    check_embeddable=None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate PUT body; returns (normalized_file_dict, error).

    Non-embeddable YouTube IDs are rejected (embed-page check) so admin cannot
    persist blocked videos. Pass ``check_embeddable`` in tests to avoid network.
    """
    if not isinstance(body, dict):
        return None, "invalid body"

    existing = read_featured_video_file()
    enabled = body["enabled"] if "enabled" in body else existing.get("enabled", True)
    if not isinstance(enabled, bool):
        return None, "enabled 必須是布林值"

    if "videos" not in body:
        return None, "videos 必須是陣列"
    raw_videos = body.get("videos")
    if not isinstance(raw_videos, list):
        return None, "videos 必須是陣列"
    # Newest-first FIFO: keep index 0..MAX_VIDEOS-1, drop oldest (tail)
    if len(raw_videos) > MAX_VIDEOS:
        raw_videos = raw_videos[:MAX_VIDEOS]

    videos: list[dict[str, str]] = []
    for i, item in enumerate(raw_videos):
        if not isinstance(item, dict):
            return None, f"videos[{i}] 格式錯誤"
        raw_id = (
            item.get("youtubeId")
            or item.get("youtube_id")
            or item.get("url")
            or item.get("youtubeUrl")
            or item.get("youtube_url")
            or ""
        )
        if not str(raw_id).strip():
            return None, f"videos[{i}] 缺少 YouTube ID 或網址"
        youtube_id = parse_youtube_id(str(raw_id))
        if not youtube_id:
            return None, f"videos[{i}] YouTube ID 無效"
        default_label = f"品牌影片 {i + 1}"
        title = str(item.get("title") or default_label).strip() or default_label
        label = str(item.get("label") or title).strip() or title
        row: dict[str, str] = {"youtubeId": youtube_id, "title": title, "label": label}
        published_at = str(item.get("publishedAt") or item.get("published_at") or "").strip()
        if published_at:
            row["publishedAt"] = published_at
        videos.append(row)

    if videos:
        from app.youtube_channel import is_youtube_embeddable

        checker = check_embeddable or is_youtube_embeddable
        blocked = [v["youtubeId"] for v in videos if not checker(v["youtubeId"])]
        if blocked:
            shown = ", ".join(blocked[:3])
            extra = f" 等 {len(blocked)} 支" if len(blocked) > 3 else ""
            return None, f"無法嵌入（YouTube 禁止嵌入）：{shown}{extra}"

    if enabled and not videos:
        return None, "啟用時至少需要一支影片"

    saved: dict[str, Any] = {"enabled": enabled, "videos": videos}
    for key in _META_KEYS:
        if key in body and body[key] is not None:
            saved[key] = body[key]
        elif key in existing:
            saved[key] = existing[key]

    if videos:
        saved["youtube_id"] = videos[0]["youtubeId"]
        saved["title"] = videos[0]["title"]
    return saved, None


def save_featured_video_file(
    data: dict[str, Any],
    path: Path | None = None,
) -> dict[str, Any]:
    """Atomically write featured-video.json; return admin payload."""
    target = path or _DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=target.parent,
        delete=False,
        suffix=".tmp",
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    tmp_path.replace(target)
    return admin_featured_payload(data)


def apply_fifo_videos(
    existing: list[dict[str, str]],
    incoming: list[dict[str, str]],
    *,
    replace: bool = False,
) -> list[dict[str, str]]:
    """Newest at front. Max MAX_VIDEOS; drop oldest (tail) when over capacity.

    replace=True: use incoming as the full list (channel sync).
    replace=False: unshift each new id onto existing, then truncate.
    """
    if replace:
        return incoming[:MAX_VIDEOS]

    merged = list(existing)
    seen = {v.get("youtubeId") for v in merged}
    for item in reversed(incoming):
        vid = item.get("youtubeId")
        if not vid:
            continue
        if vid in seen:
            # move existing match to front with updated metadata
            merged = [v for v in merged if v.get("youtubeId") != vid]
        merged.insert(0, item)
        seen.add(vid)
    return merged[:MAX_VIDEOS]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sync_lock_path(path: Path) -> Path:
    return path.parent / f".{path.stem}.sync.lock"


def parse_synced_at(value: Any) -> float | None:
    """Parse ``syncedAt`` ISO timestamp to epoch seconds; None if missing/invalid."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return None


def featured_video_age_seconds(
    path: Path | None = None,
    *,
    now: float | None = None,
) -> float | None:
    """Seconds since ``syncedAt``. None means missing / never synced."""
    target = path or _DEFAULT_PATH
    data = read_featured_video_file(target)
    synced = parse_synced_at(data.get("syncedAt") or data.get("synced_at"))
    if synced is None:
        return None
    return max(0.0, (now if now is not None else time.time()) - synced)


def featured_video_is_stale(
    path: Path | None = None,
    *,
    ttl_seconds: int = FEATURED_VIDEO_TTL_SECONDS,
    now: float | None = None,
) -> bool:
    """True when ``syncedAt`` missing or age >= TTL."""
    age = featured_video_age_seconds(path, now=now)
    if age is None:
        return True
    return age >= ttl_seconds


def peek_channel_head_id(
    *,
    ttl_seconds: int = CHANNEL_HEAD_CHECK_TTL_SECONDS,
    fetch_head: Callable[..., dict | None] | None = None,
) -> str | None:
    """Newest channel upload id (RSS/page head). Cached briefly via fetch_head TTL."""
    try:
        if fetch_head is not None:
            head = fetch_head(ttl_seconds=ttl_seconds)
        else:
            from app.youtube_channel import (
                fetch_latest_channel_video,
                resolve_channel_id,
            )

            channel_id = resolve_channel_id(IMPRINT_CHANNEL_ID, IMPRINT_CHANNEL_HANDLE)
            if not channel_id:
                return None
            head = fetch_latest_channel_video(channel_id, ttl_seconds=ttl_seconds)
    except Exception as exc:  # noqa: BLE001 — head peek must not break render
        _logger.warning("featured video channel head peek failed: %s", exc)
        return None
    if not isinstance(head, dict):
        return None
    return (head.get("youtube_id") or head.get("youtubeId") or "").strip() or None


def gallery_needs_channel_refresh(
    path: Path | None = None,
    *,
    head_id: str | None = None,
    fetch_head: Callable[..., dict | None] | None = None,
    head_ttl_seconds: int = CHANNEL_HEAD_CHECK_TTL_SECONDS,
) -> bool:
    """True when channel head moved since last sync (or gallery empty).

    Compares peek head to stored ``channelHeadId`` (raw RSS/page head at last
    sync). Falls back to gallery primary / membership when ``channelHeadId``
    missing (legacy JSON). ``source: fixed`` never suppresses this. Returns
    False when head cannot be resolved (rely on daily TTL).
    """
    data = read_featured_video_file(path)
    videos = videos_from_payload(data)
    if not videos:
        return True
    primary = videos[0]["youtubeId"]
    gallery_ids = {v["youtubeId"] for v in videos}
    resolved = head_id if head_id is not None else peek_channel_head_id(
        ttl_seconds=head_ttl_seconds,
        fetch_head=fetch_head,
    )
    if not resolved:
        return False
    last_head = str(data.get("channelHeadId") or data.get("channel_head_id") or "").strip()
    if last_head:
        return resolved != last_head
    # Legacy files without channelHeadId: primary / membership heuristic.
    return resolved != primary or resolved not in gallery_ids


def _refresh_in_progress(path: Path, *, now: float | None = None) -> bool:
    lock = _sync_lock_path(path)
    if not lock.is_file():
        return False
    try:
        age = (now if now is not None else time.time()) - lock.stat().st_mtime
    except OSError:
        return False
    return age < _STAMPEDE_LOCK_SECONDS


def _begin_refresh_lock(path: Path) -> bool:
    """Touch stampede lock. False if another refresh started recently."""
    if _refresh_in_progress(path):
        return False
    lock = _sync_lock_path(path)
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        return False
    return True


def _clear_refresh_lock(path: Path) -> None:
    try:
        _sync_lock_path(path).unlink(missing_ok=True)
    except OSError:
        pass


def ensure_featured_video_fresh(
    path: Path | None = None,
    *,
    ttl_seconds: int = FEATURED_VIDEO_TTL_SECONDS,
    force: bool = False,
    sync_fn: Callable[..., tuple[dict[str, Any] | None, str | None, str | None]]
    | None = None,
    fetch_head: Callable[..., dict | None] | None = None,
    head_ttl_seconds: int = CHANNEL_HEAD_CHECK_TTL_SECONDS,
    head_diverged_fn: Callable[[], bool] | None = None,
) -> bool:
    """Lazy sync for homepage load. Returns True if a sync ran successfully.

    Triggers ``run_featured_video_channel_sync`` when:
    - ``force`` is True, or
    - ``syncedAt`` missing / older than ``ttl_seconds``, or
    - channel head id differs from gallery primary / is absent from gallery
      (peek cached ``head_ttl_seconds`` so pageviews do not hit RSS every time).

    ``source: fixed`` never blocks refresh. Sync errors leave existing JSON
    untouched. Concurrent callers skip when a refresh lock is recent
    (``_STAMPEDE_LOCK_SECONDS``). Success clears the lock; failure keeps it
    briefly as backoff.
    """
    target = path or _DEFAULT_PATH
    needs_sync = force or featured_video_is_stale(target, ttl_seconds=ttl_seconds)
    if not needs_sync:
        if head_diverged_fn is not None:
            try:
                needs_sync = bool(head_diverged_fn())
            except Exception as exc:  # noqa: BLE001 — fall back to TTL-only
                _logger.warning("featured video head check failed: %s", exc)
                needs_sync = False
        else:
            needs_sync = gallery_needs_channel_refresh(
                target,
                fetch_head=fetch_head,
                head_ttl_seconds=head_ttl_seconds,
            )
    if not needs_sync:
        return False
    if not force and not _begin_refresh_lock(target):
        return False

    runner = sync_fn or run_featured_video_channel_sync
    try:
        payload, error, _channel_id = runner(path=target)
    except Exception as exc:  # noqa: BLE001 — never break page render
        _logger.warning("featured video lazy sync failed: %s", exc)
        return False

    if error or payload is None:
        _logger.warning("featured video lazy sync error: %s", error or "unknown")
        return False
    _clear_refresh_lock(target)
    return True


def sync_featured_videos_from_channel(
    channel_videos: list[dict],
    *,
    path: Path | None = None,
    channel_head_id: str | None = None,
) -> dict:
    """Full-replace gallery with channel latest (newest-first, max 6).

    Always ``replace=True`` — never merge/unshift sticky older JSON tops.
    Preserves about meta (eyebrow/heading/lead/source) but ``source`` does not
    gate replacement; videos always become the newest embeddable pull.
    ``channel_head_id`` records the raw channel feed head (may be unplayable)
    so lazy refresh can detect a new upload without re-syncing every pageview.
    """
    existing = read_featured_video_file(path)
    videos: list[dict[str, str]] = []
    for i, item in enumerate(channel_videos[:MAX_VIDEOS]):
        normalized = normalize_video_item(item, index=i)
        if normalized:
            videos.append(normalized)
    # Empty existing + replace — drop any prior sticky ids.
    videos = apply_fifo_videos([], videos, replace=True)

    head = (channel_head_id or "").strip()
    if not head and channel_videos:
        first = normalize_video_item(channel_videos[0], index=0)
        if first:
            head = first["youtubeId"]
    if not head and videos:
        head = videos[0]["youtubeId"]

    saved: dict = {
        "enabled": bool(existing.get("enabled", True)),
        "syncedAt": _utc_now_iso(),
        "videos": [
            {k: v for k, v in row.items() if k != "youtube_id"}
            for row in videos
        ],
    }
    if head:
        saved["channelHeadId"] = head
    for key in _META_KEYS:
        if key in existing:
            saved[key] = existing[key]
    if videos:
        saved["youtube_id"] = videos[0]["youtubeId"]
        saved["title"] = videos[0]["title"]
    return save_featured_video_file(saved, path)


def run_featured_video_channel_sync(
    *,
    path: Path | None = None,
    candidate_limit: int = CHANNEL_CANDIDATE_LIMIT,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """Fetch channel RSS, embed-filter to MAX_VIDEOS, write gallery.

    Returns ``(admin_payload, error_message, channel_id)``. On failure payload
    is None and error_message is set for a 502 response.
    """
    from app.youtube_channel import (
        fetch_latest_channel_videos,
        filter_embeddable_videos,
        public_embed_referer,
        resolve_channel_id,
    )

    channel_id = resolve_channel_id(IMPRINT_CHANNEL_ID, IMPRINT_CHANNEL_HANDLE)
    if not channel_id:
        return None, "無法解析 YouTube 頻道", None

    try:
        candidates = fetch_latest_channel_videos(
            channel_id, limit=max(candidate_limit, MAX_VIDEOS)
        )
    except Exception as exc:  # noqa: BLE001 — surface feed/page errors to callers
        # Exception text already names the failing URL(s).
        _logger.warning(
            "featured video channel fetch failed channel_id=%s: %s",
            channel_id,
            exc,
        )
        return None, f"無法取得頻道影片：{exc}", channel_id

    if not candidates:
        return None, "頻道尚無公開影片", channel_id

    raw_head = ""
    first = normalize_video_item(candidates[0], index=0)
    if first:
        raw_head = first["youtubeId"]

    embeddable = filter_embeddable_videos(
        candidates,
        limit=MAX_VIDEOS,
        referer=public_embed_referer(),
    )
    if not embeddable:
        return None, "頻道尚無可嵌入的公開影片", channel_id

    payload = sync_featured_videos_from_channel(
        embeddable,
        path=path,
        channel_head_id=raw_head or None,
    )
    return payload, None, channel_id

