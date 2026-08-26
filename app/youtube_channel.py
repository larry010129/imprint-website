"""Resolve latest public video from a YouTube channel RSS feed."""

from __future__ import annotations

import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen

from curl_cffi import requests

_CACHE_PATH = Path(__file__).resolve().parent / "data" / ".featured-video-cache.json"
_EMBED_CACHE_PATH = Path(__file__).resolve().parent / "data" / ".youtube-embed-cache.json"
_ATOM = "http://www.w3.org/2005/Atom"
_YT = "http://www.youtube.com/xml/schemas/2015"
_DEFAULT_TTL = 6 * 60 * 60
_EMBED_TTL = 6 * 60 * 60
_EMBED_CACHE_VERSION = 2
_DEFAULT_EMBED_REFERER = "https://www.imprint-diamond.com/"
# Memory: cache_key -> (checked_at, embeddable)
_embed_memory: dict[str, tuple[float, bool]] = {}
_logger = logging.getLogger(__name__)
_YT_INITIAL_DATA_RE = re.compile(
    r"ytInitialData\s*=\s*(\{.+?\});</script>",
    re.DOTALL,
)
_PREVIEW_STATUS_RE = re.compile(
    r'"previewPlayabilityStatus"\s*:\s*\{([^}]{0,500})\}',
)
_STATUS_IN_BLOCK_RE = re.compile(r'"status"\s*:\s*"([^"]+)"')
_BLOCKED_EMBED_SNIPPETS = (
    "Playback on other websites has been disabled",
    "embedding has been disabled",
    "WATCH_ON_YOUTUBE_CTA",
)


def channel_feed_url(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def channel_videos_page_url(channel_id: str) -> str:
    return f"https://www.youtube.com/channel/{channel_id}/videos"


def _read_cache(channel_id: str, ttl_seconds: int) -> dict | None:
    if not _CACHE_PATH.is_file():
        return None
    try:
        payload = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if payload.get("channel_id") != channel_id:
        return None
    if time.time() - float(payload.get("fetched_at", 0)) > ttl_seconds:
        return None
    video_id = payload.get("youtube_id")
    if not video_id:
        return None
    return {"youtube_id": video_id, "title": payload.get("title") or "YouTube 影片"}


def _write_cache(channel_id: str, youtube_id: str, title: str) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(
        json.dumps(
            {
                "channel_id": channel_id,
                "youtube_id": youtube_id,
                "title": title,
                "fetched_at": time.time(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _entry_to_video(entry: ET.Element) -> dict | None:
    video_id_el = entry.find(f"{{{_YT}}}videoId")
    title_el = entry.find(f"{{{_ATOM}}}title")
    published_el = entry.find(f"{{{_ATOM}}}published")
    if video_id_el is None or not (video_id_el.text or "").strip():
        return None
    video = {
        "youtube_id": video_id_el.text.strip(),
        "youtubeId": video_id_el.text.strip(),
        "title": (title_el.text if title_el is not None else "").strip() or "YouTube 影片",
    }
    if published_el is not None and (published_el.text or "").strip():
        video["publishedAt"] = published_el.text.strip()
    return video


def _parse_latest_from_feed(xml_bytes: bytes) -> dict | None:
    root = ET.fromstring(xml_bytes)
    entry = root.find(f"{{{_ATOM}}}entry")
    if entry is None:
        return None
    return _entry_to_video(entry)


def _parse_videos_from_feed(xml_bytes: bytes, limit: int = 6) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    out: list[dict] = []
    for entry in root.findall(f"{{{_ATOM}}}entry"):
        video = _entry_to_video(entry)
        if video:
            out.append(video)
        if len(out) >= limit:
            break
    return out


def resolve_channel_id(channel_id: str | None, channel_handle: str | None) -> str | None:
    if channel_id:
        return channel_id.strip()
    handle = (channel_handle or "").strip().lstrip("@")
    if not handle:
        return None
    url = f"https://www.youtube.com/@{handle}"
    resp = requests.get(url, impersonate="chrome", timeout=20)
    resp.raise_for_status()
    # Prefer externalId/browseId — channel pages often omit bare "channelId".
    patterns = (
        r'"externalId":"(UC[^"]+)"',
        r'"browseId":"(UC[^"]+)"',
        r'"channelId":"(UC[^"]+)"',
        r"channel/(UC[^\"/?]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, resp.text)
        if match:
            return match.group(1)
    return None


def _http_error(url: str, status: int) -> RuntimeError:
    return RuntimeError(f"HTTP {status} for {url}")


def _fetch_feed_bytes(channel_id: str) -> bytes:
    """Fetch Atom RSS via browser-like TLS. Raises RuntimeError with URL on failure."""
    feed_url = channel_feed_url(channel_id)
    resp = requests.get(feed_url, impersonate="chrome", timeout=20)
    if resp.status_code >= 400:
        raise _http_error(feed_url, resp.status_code)
    return resp.content


def _lockup_title(lockup: dict) -> str:
    meta = lockup.get("metadata") or {}
    view = meta.get("lockupMetadataViewModel") or {}
    title = view.get("title") or {}
    if isinstance(title, dict):
        text = (title.get("content") or "").strip()
        if text:
            return text
    return "YouTube 影片"


def _parse_videos_from_yt_initial_data(payload: dict, limit: int) -> list[dict]:
    """Extract newest-first videos from channel /videos ytInitialData."""
    out: list[dict] = []
    seen: set[str] = set()
    stack: list[object] = [payload]
    while stack and len(out) < limit:
        node = stack.pop()
        if isinstance(node, dict):
            lockup = node.get("lockupViewModel")
            if isinstance(lockup, dict):
                if lockup.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO":
                    vid = (lockup.get("contentId") or "").strip()
                    if vid and vid not in seen:
                        seen.add(vid)
                        out.append(
                            {
                                "youtube_id": vid,
                                "youtubeId": vid,
                                "title": _lockup_title(lockup),
                            }
                        )
            # Depth-first reverse so first children stay near page order.
            stack.extend(reversed(list(node.values())))
        elif isinstance(node, list):
            stack.extend(reversed(node))
    return out


def _fetch_videos_from_channel_page(channel_id: str, *, limit: int) -> list[dict]:
    page_url = channel_videos_page_url(channel_id)
    resp = requests.get(page_url, impersonate="chrome", timeout=20)
    if resp.status_code >= 400:
        raise _http_error(page_url, resp.status_code)
    match = _YT_INITIAL_DATA_RE.search(resp.text)
    if not match:
        raise RuntimeError(f"ytInitialData missing on {page_url}")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ytInitialData invalid on {page_url}: {exc}") from exc
    return _parse_videos_from_yt_initial_data(payload, limit)


def fetch_latest_channel_videos(
    channel_id: str,
    *,
    limit: int = 6,
    ttl_seconds: int = 0,
) -> list[dict]:
    """Return up to `limit` newest public videos (RSS order = newest first).

    Tries Atom RSS first; on HTTP failure / empty feed, falls back to the
    public channel /videos page (lockupViewModel). ttl_seconds ignored for
    multi-video sync.
    """
    del ttl_seconds  # sync always refreshes the gallery list
    if limit < 1:
        return []

    feed_url = channel_feed_url(channel_id)
    page_url = channel_videos_page_url(channel_id)
    errors: list[str] = []

    try:
        xml_bytes = _fetch_feed_bytes(channel_id)
        videos = _parse_videos_from_feed(xml_bytes, limit=limit)
        if videos:
            _write_cache(channel_id, videos[0]["youtube_id"], videos[0]["title"])
            return videos
        errors.append(f"empty RSS feed at {feed_url}")
    except Exception as exc:  # noqa: BLE001 — try page fallback
        errors.append(str(exc))
        _logger.info("YouTube RSS unavailable, trying channel page: %s", exc)

    try:
        videos = _fetch_videos_from_channel_page(channel_id, limit=limit)
        if videos:
            _write_cache(channel_id, videos[0]["youtube_id"], videos[0]["title"])
            return videos
        errors.append(f"no videos on {page_url}")
    except Exception as exc:  # noqa: BLE001 — surface both failures
        errors.append(str(exc))

    raise RuntimeError("; ".join(errors))


def public_embed_referer() -> str:
    """Canonical site origin used for sync / admin embed probes."""
    import os

    for key in ("PUBLIC_SITE_URL", "SITE_URL"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            return raw if raw.endswith("/") else f"{raw}/"
    return _DEFAULT_EMBED_REFERER


def _embed_cache_key(video_id: str, referer: str) -> str:
    """Key by video + referer host — domain-restricted embeds differ by origin."""
    from urllib.parse import urlparse

    host = (urlparse(referer).netloc or "none").lower()
    return f"{video_id}@{host}"


def _read_embed_disk_cache(cache_key: str) -> bool | None:
    if not _EMBED_CACHE_PATH.is_file():
        return None
    try:
        payload = json.loads(_EMBED_CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if int(payload.get("version") or 0) != _EMBED_CACHE_VERSION:
        return None
    entry = (payload.get("videos") or {}).get(cache_key)
    if not isinstance(entry, dict):
        return None
    if time.time() - float(entry.get("checked_at", 0)) > _EMBED_TTL:
        return None
    return bool(entry.get("embeddable"))


def _write_embed_disk_cache(cache_key: str, embeddable: bool) -> None:
    payload: dict = {"version": _EMBED_CACHE_VERSION, "videos": {}}
    if _EMBED_CACHE_PATH.is_file():
        try:
            loaded = json.loads(_EMBED_CACHE_PATH.read_text(encoding="utf-8"))
            if (
                isinstance(loaded, dict)
                and int(loaded.get("version") or 0) == _EMBED_CACHE_VERSION
                and isinstance(loaded.get("videos"), dict)
            ):
                payload = loaded
                payload["version"] = _EMBED_CACHE_VERSION
        except (json.JSONDecodeError, OSError):
            pass
    videos = payload.setdefault("videos", {})
    videos[cache_key] = {"embeddable": embeddable, "checked_at": time.time()}
    now = time.time()
    payload["videos"] = {
        key: row
        for key, row in videos.items()
        if isinstance(row, dict) and now - float(row.get("checked_at", 0)) <= _EMBED_TTL
    }
    _EMBED_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _EMBED_CACHE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _oembed_available(video_id: str, *, timeout: float) -> bool | None:
    """oEmbed fast path. False = reject; True = metadata ok (not proof); None = network fail."""
    from urllib.error import HTTPError, URLError

    oembed = (
        "https://www.youtube.com/oembed"
        f"?url=https://www.youtube.com/watch?v={video_id}&format=json"
    )
    try:
        with urlopen(oembed, timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 300
    except HTTPError:
        return False
    except (URLError, TimeoutError, OSError):
        return None


def embed_page_indicates_playable(html: str) -> bool:
    """Parse youtube.com/embed HTML for iframe playability (not oEmbed)."""
    if not html:
        return False
    text = html.replace('\\"', '"')
    for snippet in _BLOCKED_EMBED_SNIPPETS:
        if snippet in text:
            return False
    match = _PREVIEW_STATUS_RE.search(text)
    if not match:
        return False
    block = match.group(1)
    status_match = _STATUS_IN_BLOCK_RE.search(block)
    if not status_match or status_match.group(1) != "OK":
        return False
    compact = re.sub(r"\s+", "", block)
    return '"playableInEmbed":false' not in compact


def _fetch_embed_page_html(
    video_id: str,
    referer: str,
    *,
    timeout: float,
) -> str | None:
    url = f"https://www.youtube.com/embed/{video_id}"
    try:
        resp = requests.get(
            url,
            impersonate="chrome",
            timeout=timeout,
            headers={"Referer": referer},
        )
    except Exception:  # noqa: BLE001 — treat transport errors as unknown
        return None
    if resp.status_code >= 400:
        return None
    return resp.text or ""


def _remember_embed(cache_key: str, embeddable: bool) -> bool:
    _embed_memory[cache_key] = (time.time(), embeddable)
    try:
        _write_embed_disk_cache(cache_key, embeddable)
    except OSError:
        pass
    return embeddable


def is_youtube_embeddable(
    video_id: str,
    *,
    timeout: float = 10,
    referer: str | None = None,
) -> bool:
    """True when the video can play inside an iframe for ``referer``.

    oEmbed 4xx is a fast reject, but oEmbed 200 is not enough — many clips
    still return metadata while ``/embed`` is UNPLAYABLE for the site origin.
    """
    vid = (video_id or "").strip()
    if not vid:
        return False
    ref = (referer or public_embed_referer()).strip() or _DEFAULT_EMBED_REFERER
    cache_key = _embed_cache_key(vid, ref)

    cached = _embed_memory.get(cache_key)
    if cached and time.time() - cached[0] <= _EMBED_TTL:
        return cached[1]

    disk = _read_embed_disk_cache(cache_key)
    if disk is not None:
        _embed_memory[cache_key] = (time.time(), disk)
        return disk

    oembed = _oembed_available(vid, timeout=timeout)
    if oembed is False:
        return _remember_embed(cache_key, False)

    html = _fetch_embed_page_html(vid, ref, timeout=timeout)
    if html is None:
        # Transient network — fail closed for this call, do not poison cache
        return False
    return _remember_embed(cache_key, embed_page_indicates_playable(html))


def filter_embeddable_videos(
    videos: list[dict],
    *,
    limit: int = 6,
    check_embeddable=None,
    referer: str | None = None,
) -> list[dict]:
    """Keep newest-first videos that pass embed check until `limit` filled."""
    if limit < 1:
        return []
    if check_embeddable is not None:
        checker = check_embeddable
    elif referer is not None:
        checker = lambda vid, _r=referer: is_youtube_embeddable(vid, referer=_r)
    else:
        checker = is_youtube_embeddable
    out: list[dict] = []
    for video in videos:
        vid = (video.get("youtubeId") or video.get("youtube_id") or "").strip()
        if not vid:
            continue
        if not checker(vid):
            continue
        out.append(video)
        if len(out) >= limit:
            break
    return out


def fetch_latest_channel_video(
    channel_id: str,
    *,
    ttl_seconds: int = _DEFAULT_TTL,
) -> dict | None:
    cached = _read_cache(channel_id, ttl_seconds)
    if cached:
        return cached

    videos = fetch_latest_channel_videos(channel_id, limit=1, ttl_seconds=0)
    return videos[0] if videos else None
