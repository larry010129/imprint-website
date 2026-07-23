"""Resolve latest public video from a YouTube channel RSS feed."""

from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen

from curl_cffi import requests

_CACHE_PATH = Path(__file__).resolve().parent / "data" / ".featured-video-cache.json"
_ATOM = "http://www.w3.org/2005/Atom"
_YT = "http://www.youtube.com/xml/schemas/2015"
_DEFAULT_TTL = 6 * 60 * 60


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


def _parse_latest_from_feed(xml_bytes: bytes) -> dict | None:
    root = ET.fromstring(xml_bytes)
    entry = root.find(f"{{{_ATOM}}}entry")
    if entry is None:
        return None
    video_id_el = entry.find(f"{{{_YT}}}videoId")
    title_el = entry.find(f"{{{_ATOM}}}title")
    if video_id_el is None or not (video_id_el.text or "").strip():
        return None
    return {
        "youtube_id": video_id_el.text.strip(),
        "title": (title_el.text if title_el is not None else "").strip() or "YouTube 影片",
    }


def resolve_channel_id(channel_id: str | None, channel_handle: str | None) -> str | None:
    if channel_id:
        return channel_id.strip()
    handle = (channel_handle or "").strip().lstrip("@")
    if not handle:
        return None
    url = f"https://www.youtube.com/@{handle}"
    resp = requests.get(url, impersonate="chrome", timeout=20)
    resp.raise_for_status()
    patterns = (
        r'"channelId":"(UC[^"]+)"',
        r'"externalId":"(UC[^"]+)"',
        r'"browseId":"(UC[^"]+)"',
        r"channel/(UC[^\"/?]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, resp.text)
        if match:
            return match.group(1)
    return None


def fetch_latest_channel_video(
    channel_id: str,
    *,
    ttl_seconds: int = _DEFAULT_TTL,
) -> dict | None:
    cached = _read_cache(channel_id, ttl_seconds)
    if cached:
        return cached

    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    with urlopen(feed_url, timeout=20) as resp:
        latest = _parse_latest_from_feed(resp.read())
    if not latest:
        return None

    _write_cache(channel_id, latest["youtube_id"], latest["title"])
    return latest
