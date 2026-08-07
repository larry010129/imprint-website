"""Unit tests for featured YouTube gallery JSON + ID parsing."""

from __future__ import annotations

import json
from pathlib import Path

from app.featured_video import (
    MAX_VIDEOS,
    admin_featured_payload,
    load_featured_video,
    parse_youtube_id,
    public_featured_payload,
    save_featured_video_file,
    validate_admin_body,
    videos_from_payload,
)


def test_parse_youtube_id_raw_and_urls():
    vid = "eBLOrvHosR4"
    assert parse_youtube_id(vid) == vid
    assert parse_youtube_id(f"https://www.youtube.com/watch?v={vid}") == vid
    assert parse_youtube_id(f"https://youtu.be/{vid}") == vid
    assert parse_youtube_id(f"https://www.youtube.com/embed/{vid}") == vid
    assert parse_youtube_id(f"https://www.youtube-nocookie.com/embed/{vid}?autoplay=1") == vid
    assert parse_youtube_id(f"https://www.youtube.com/shorts/{vid}") == vid
    assert parse_youtube_id("too-short") is None
    assert parse_youtube_id("has spaces!!") is None
    assert parse_youtube_id("") is None


def test_videos_from_legacy_single_id():
    videos = videos_from_payload(
        {
            "enabled": True,
            "youtube_id": "eBLOrvHosR4",
            "title": "Legacy title",
        }
    )
    assert len(videos) == 1
    assert videos[0]["youtubeId"] == "eBLOrvHosR4"
    assert videos[0]["title"] == "Legacy title"


def test_public_payload_gallery_and_primary(tmp_path: Path):
    path = tmp_path / "featured-video.json"
    path.write_text(
        json.dumps(
            {
                "enabled": True,
                "eyebrow": "VIDEO",
                "videos": [
                    {
                        "youtubeId": "eBLOrvHosR4",
                        "title": "DNA 鑽石製作流程影片",
                        "label": "DNA 鑽石製作流程",
                    },
                    {
                        "youtubeId": "eBLOrvHosR4",
                        "title": "品牌影片 2",
                        "label": "品牌影片 2",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    payload = load_featured_video(
        path,
        check_embeddable=lambda _vid: True,
        fetch_candidates=lambda: [],
    )
    assert payload is not None
    assert payload["youtube_id"] == "eBLOrvHosR4"
    assert payload["primary"]["youtubeId"] == "eBLOrvHosR4"
    assert len(payload["videos"]) == 2
    assert payload["eyebrow"] == "VIDEO"


def test_legacy_shape_still_loads():
    payload = public_featured_payload(
        {
            "enabled": True,
            "youtube_id": "eBLOrvHosR4",
            "title": "DNA 鑽石製作流程影片",
            "heading": "親見",
        }
    )
    assert payload is not None
    assert payload["youtube_id"] == "eBLOrvHosR4"
    assert len(payload["videos"]) == 1
    assert payload["heading"] == "親見"


def test_disabled_or_empty_returns_none():
    assert public_featured_payload({"enabled": False, "youtube_id": "eBLOrvHosR4"}) is None
    assert public_featured_payload({"enabled": True, "videos": []}) is None


def test_validate_admin_body_accepts_watch_url():
    body = {
        "enabled": True,
        "videos": [
            {
                "youtubeId": "https://www.youtube.com/watch?v=eBLOrvHosR4",
                "title": "A",
                "label": "A",
            }
        ],
    }
    saved, err = validate_admin_body(body, check_embeddable=lambda _vid: True)
    assert err is None
    assert saved is not None
    assert saved["videos"][0]["youtubeId"] == "eBLOrvHosR4"


def test_validate_admin_body_rejects_bad_id_and_overflow():
    bad, err = validate_admin_body(
        {"enabled": True, "videos": [{"youtubeId": "bad", "title": "x"}]},
        check_embeddable=lambda _vid: True,
    )
    assert bad is None
    assert err and "無效" in err

    overflow = [
        {"youtubeId": "eBLOrvHosR4", "title": f"t{i}", "label": f"l{i}"}
        for i in range(MAX_VIDEOS + 1)
    ]
    # Same ID repeats — after FIFO truncate we still accept (newest-first keep first 6)
    saved2, err2 = validate_admin_body(
        {"enabled": True, "videos": overflow},
        check_embeddable=lambda _vid: True,
    )
    assert err2 is None
    assert saved2 is not None
    assert len(saved2["videos"]) == MAX_VIDEOS


def test_validate_admin_body_rejects_non_embeddable():
    body = {
        "enabled": True,
        "videos": [
            {"youtubeId": "eBLOrvHosR4", "title": "good"},
            {"youtubeId": "blockedVid0", "title": "bad"},
        ],
    }
    saved, err = validate_admin_body(
        body, check_embeddable=lambda vid: vid != "blockedVid0"
    )
    assert saved is None
    assert err is not None
    assert "無法嵌入" in err
    assert "blockedVid0" in err


def test_load_featured_video_skips_non_embeddable_primary(tmp_path: Path):
    path = tmp_path / "featured-video.json"
    path.write_text(
        json.dumps(
            {
                "enabled": True,
                "eyebrow": "VIDEO",
                "videos": [
                    {"youtubeId": "blockedVid0", "title": "Blocked", "label": "Blocked"},
                    {"youtubeId": "eBLOrvHosR4", "title": "Good", "label": "Good"},
                    {"youtubeId": "alsoBlocked", "title": "Nope", "label": "Nope"},
                    {"youtubeId": "dQw4w9WgXcQ", "title": "Also good", "label": "Also good"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    bad = {"blockedVid0", "alsoBlocked"}
    payload = load_featured_video(
        path,
        check_embeddable=lambda vid: vid not in bad,
        fetch_candidates=lambda: [],
    )
    assert payload is not None
    assert payload["youtube_id"] == "eBLOrvHosR4"
    ids = [v["youtubeId"] for v in payload["videos"]]
    assert ids == ["eBLOrvHosR4", "dQw4w9WgXcQ"]
    assert all(vid not in bad for vid in ids)


def test_load_featured_video_all_blocked_returns_none(tmp_path: Path):
    path = tmp_path / "featured-video.json"
    path.write_text(
        json.dumps(
            {
                "enabled": True,
                "videos": [
                    {"youtubeId": "blockedVid0", "title": "Blocked", "label": "Blocked"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert (
        load_featured_video(
            path,
            check_embeddable=lambda _vid: False,
            fetch_candidates=lambda: [],
        )
        is None
    )


def test_load_featured_video_backfills_to_six(tmp_path: Path):
    """JSON has 6; 1 blocked → channel candidates fill gallery back to 6."""
    path = tmp_path / "featured-video.json"
    stored = [
        {"youtubeId": "goodVideo00", "title": "G0", "label": "G0"},
        {"youtubeId": "blockedVid0", "title": "Bad", "label": "Bad"},
        {"youtubeId": "goodVideo01", "title": "G1", "label": "G1"},
        {"youtubeId": "goodVideo02", "title": "G2", "label": "G2"},
        {"youtubeId": "goodVideo03", "title": "G3", "label": "G3"},
        {"youtubeId": "goodVideo04", "title": "G4", "label": "G4"},
    ]
    path.write_text(
        json.dumps({"enabled": True, "eyebrow": "VIDEO", "videos": stored}, ensure_ascii=False),
        encoding="utf-8",
    )
    # Extra channel uploads beyond the stored list (newest-first).
    channel = [
        {"youtubeId": "blockedVid0", "title": "Bad again"},
        {"youtubeId": "goodVideo00", "title": "already kept"},
        {"youtubeId": "fillVideo05", "title": "F5"},
        {"youtubeId": "alsoBlock01", "title": "skip"},
        {"youtubeId": "fillVideo06", "title": "F6"},
        {"youtubeId": "fillVideo07", "title": "F7"},
    ]
    bad = {"blockedVid0", "alsoBlock01"}

    payload = load_featured_video(
        path,
        check_embeddable=lambda vid: vid not in bad,
        fetch_candidates=lambda: channel,
    )
    assert payload is not None
    ids = [v["youtubeId"] for v in payload["videos"]]
    assert len(ids) == MAX_VIDEOS
    assert "blockedVid0" not in ids
    assert "alsoBlock01" not in ids
    assert ids == [
        "goodVideo00",
        "goodVideo01",
        "goodVideo02",
        "goodVideo03",
        "goodVideo04",
        "fillVideo05",
    ]
    # Persisted so later loads stay at 6 without re-filtering blocked primary.
    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert [v["youtubeId"] for v in reloaded["videos"]] == ids
    assert reloaded.get("eyebrow") == "VIDEO"


def test_repair_persist_keeps_channel_head_id(tmp_path: Path):
    """Embed repair must not drop channelHeadId (lazy head-diff depends on it)."""
    path = tmp_path / "featured-video.json"
    path.write_text(
        json.dumps(
            {
                "enabled": True,
                "syncedAt": "2026-08-07T10:00:00Z",
                "channelHeadId": "rawHeadVid0",
                "source": "fixed",
                "eyebrow": "VIDEO",
                "videos": [
                    {"youtubeId": "blockedVid0", "title": "Bad", "label": "Bad"},
                    {"youtubeId": "goodVideo00", "title": "G0", "label": "G0"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    payload = load_featured_video(
        path,
        check_embeddable=lambda vid: vid != "blockedVid0",
        fetch_candidates=lambda: [
            {"youtubeId": "blockedVid0", "title": "Bad"},
            {"youtubeId": "goodVideo00", "title": "G0"},
            {"youtubeId": "fillVideo01", "title": "F1"},
        ],
    )
    assert payload is not None
    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert reloaded.get("channelHeadId") == "rawHeadVid0"
    assert reloaded.get("syncedAt") == "2026-08-07T10:00:00Z"
    assert reloaded.get("source") == "fixed"
    assert "blockedVid0" not in [v["youtubeId"] for v in reloaded["videos"]]


def test_save_and_admin_payload_roundtrip(tmp_path: Path):
    path = tmp_path / "featured-video.json"
    data = {
        "enabled": True,
        "source": "fixed",
        "videos": [
            {"youtubeId": "eBLOrvHosR4", "title": "T1", "label": "L1"},
            {"youtubeId": "dQw4w9WgXcQ", "title": "T2", "label": "L2"},
        ],
    }
    out = save_featured_video_file(data, path)
    assert out["enabled"] is True
    assert len(out["videos"]) == 2
    assert out["videos"][1]["youtubeId"] == "dQw4w9WgXcQ"
    reloaded = admin_featured_payload(json.loads(path.read_text(encoding="utf-8")))
    assert reloaded["videos"][0]["label"] == "L1"


def test_seed_file_has_six_videos():
    """Seed gallery is enabled with exactly MAX_VIDEOS unique ids (channel-sync may refresh ids)."""
    from app.featured_video import read_featured_video_file

    data = read_featured_video_file()
    videos = videos_from_payload(data)
    assert data.get("enabled") is True
    assert len(videos) == MAX_VIDEOS
    ids = [v["youtubeId"] for v in videos]
    assert len(set(ids)) == MAX_VIDEOS
    assert all(len(vid) == 11 for vid in ids)


def test_fifo_keeps_newest_six():
    from app.featured_video import apply_fifo_videos

    existing = [
        {"youtubeId": "aaaaaaaaaa0", "title": "old0", "label": "old0"},
        {"youtubeId": "aaaaaaaaaa1", "title": "old1", "label": "old1"},
        {"youtubeId": "aaaaaaaaaa2", "title": "old2", "label": "old2"},
        {"youtubeId": "aaaaaaaaaa3", "title": "old3", "label": "old3"},
        {"youtubeId": "aaaaaaaaaa4", "title": "old4", "label": "old4"},
        {"youtubeId": "aaaaaaaaaa5", "title": "old5", "label": "old5"},
    ]
    incoming = [{"youtubeId": "IFa_5chXdJ4", "title": "new", "label": "new"}]
    out = apply_fifo_videos(existing, incoming, replace=False)
    assert len(out) == 6
    assert out[0]["youtubeId"] == "IFa_5chXdJ4"
    assert out[-1]["youtubeId"] == "aaaaaaaaaa4"
    assert "aaaaaaaaaa5" not in {v["youtubeId"] for v in out}


def test_sync_from_channel_replace(tmp_path: Path):
    from app.featured_video import sync_featured_videos_from_channel, read_featured_video_file

    seed = tmp_path / "featured-video.json"
    seed.write_text(
        json.dumps(
            {
                "enabled": True,
                "eyebrow": "VIDEO",
                "heading": "H",
                "lead": "L",
                "videos": [{"youtubeId": "eBLOrvHosR4", "title": "old", "label": "old"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    channel = [
        {
            "youtubeId": "IFa_5chXdJ4",
            "title": "A",
            "publishedAt": "2026-07-24T05:20:49+00:00",
        },
        {"youtubeId": "EdYQTJfD2hE", "title": "B"},
    ]
    payload = sync_featured_videos_from_channel(channel, path=seed)
    assert payload["videos"][0]["youtubeId"] == "IFa_5chXdJ4"
    assert payload["videos"][0].get("publishedAt") == "2026-07-24T05:20:49+00:00"
    reloaded = read_featured_video_file(seed)
    assert reloaded["eyebrow"] == "VIDEO"
    assert reloaded["heading"] == "H"
    assert len(reloaded["videos"]) == 2
    assert reloaded.get("syncedAt")
    assert reloaded.get("channelHeadId") == "IFa_5chXdJ4"


def _write_gallery(path: Path, *, synced_at: str | None, youtube_id: str = "eBLOrvHosR4"):
    data = {
        "enabled": True,
        "videos": [{"youtubeId": youtube_id, "title": "T", "label": "T"}],
    }
    if synced_at is not None:
        data["syncedAt"] = synced_at
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_ensure_fresh_skips_when_synced_at_recent(tmp_path: Path):
    from app.featured_video import ensure_featured_video_fresh

    path = tmp_path / "featured-video.json"
    _write_gallery(path, synced_at="2099-01-01T00:00:00Z")
    calls: list[int] = []

    def boom(**_kwargs):
        calls.append(1)
        return None, "should not run", None

    assert (
        ensure_featured_video_fresh(
            path, sync_fn=boom, head_diverged_fn=lambda: False
        )
        is False
    )
    assert calls == []
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["videos"][0]["youtubeId"] == "eBLOrvHosR4"


def test_ensure_fresh_forces_when_channel_head_differs(tmp_path: Path):
    """Inside daily TTL, new channel head still triggers full replace sync."""
    from app.featured_video import ensure_featured_video_fresh

    path = tmp_path / "featured-video.json"
    _write_gallery(path, synced_at="2099-01-01T00:00:00Z", youtube_id="oldPrimary01")
    calls: list[str] = []

    def fake_sync(*, path: Path, **_kwargs):
        calls.append("sync")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["syncedAt"] = "2099-01-01T00:00:00Z"
        data["videos"] = [
            {"youtubeId": "IFa_5chXdJ4", "title": "new head", "label": "new head"},
            {"youtubeId": "EdYQTJfD2hE", "title": "B", "label": "B"},
        ]
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return {"videos": data["videos"]}, None, "UC_test"

    assert (
        ensure_featured_video_fresh(
            path,
            sync_fn=fake_sync,
            head_diverged_fn=lambda: True,
        )
        is True
    )
    assert calls == ["sync"]
    assert json.loads(path.read_text(encoding="utf-8"))["videos"][0]["youtubeId"] == (
        "IFa_5chXdJ4"
    )


def test_gallery_needs_channel_refresh_primary_and_membership(tmp_path: Path):
    from app.featured_video import gallery_needs_channel_refresh

    path = tmp_path / "featured-video.json"
    path.write_text(
        json.dumps(
            {
                "enabled": True,
                "videos": [
                    {"youtubeId": "primaryVid0", "title": "P"},
                    {"youtubeId": "secondVid01", "title": "S"},
                ],
            }
        ),
        encoding="utf-8",
    )
    # Legacy (no channelHeadId): primary / membership heuristic
    assert gallery_needs_channel_refresh(path, head_id="primaryVid0") is False
    assert gallery_needs_channel_refresh(path, head_id="brandNewVid") is True
    assert gallery_needs_channel_refresh(path, head_id="secondVid01") is True
    assert gallery_needs_channel_refresh(path, head_id="") is False

    # After sync: unplayable raw head stored — same peek must not force again
    path.write_text(
        json.dumps(
            {
                "enabled": True,
                "channelHeadId": "blockedHead0",
                "videos": [
                    {"youtubeId": "primaryVid0", "title": "P"},
                    {"youtubeId": "secondVid01", "title": "S"},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert gallery_needs_channel_refresh(path, head_id="blockedHead0") is False
    assert gallery_needs_channel_refresh(path, head_id="brandNewVid") is True


def test_sync_replace_newest_first_drops_sticky_old(tmp_path: Path):
    """replace=True full replace — no merge that keeps stale tops / source:fixed."""
    from app.featured_video import sync_featured_videos_from_channel, read_featured_video_file

    seed = tmp_path / "featured-video.json"
    sticky = [
        {"youtubeId": f"oldSticky00{i}", "title": f"old{i}", "label": f"old{i}"}
        for i in range(6)
    ]
    seed.write_text(
        json.dumps(
            {
                "enabled": True,
                "source": "fixed",
                "eyebrow": "VIDEO",
                "videos": sticky,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    channel = [
        {"youtubeId": "IFa_5chXdJ4", "title": "newest"},
        {"youtubeId": "EdYQTJfD2hE", "title": "2"},
        {"youtubeId": "4NgOHK064Jc", "title": "3"},
        {"youtubeId": "ZGSmmOGH7Ec", "title": "4"},
        {"youtubeId": "S0dcVT_v2kQ", "title": "5"},
        {"youtubeId": "K6jhW-F52hs", "title": "6"},
        {"youtubeId": "extraShould0", "title": "7 ignored by max"},
    ]
    payload = sync_featured_videos_from_channel(
        channel, path=seed, channel_head_id="IFa_5chXdJ4"
    )
    ids = [v["youtubeId"] for v in payload["videos"]]
    assert ids == [
        "IFa_5chXdJ4",
        "EdYQTJfD2hE",
        "4NgOHK064Jc",
        "ZGSmmOGH7Ec",
        "S0dcVT_v2kQ",
        "K6jhW-F52hs",
    ]
    assert all(not vid.startswith("oldSticky") for vid in ids)
    reloaded = read_featured_video_file(seed)
    assert reloaded.get("source") == "fixed"  # meta preserved, does not block
    assert reloaded.get("channelHeadId") == "IFa_5chXdJ4"
    assert [v["youtubeId"] for v in reloaded["videos"]] == ids


def test_featured_video_ttl_is_one_day():
    from app.featured_video import FEATURED_VIDEO_TTL_SECONDS

    assert FEATURED_VIDEO_TTL_SECONDS == 24 * 60 * 60


def test_ensure_fresh_triggers_when_missing_or_stale(tmp_path: Path):
    from app.featured_video import ensure_featured_video_fresh, FEATURED_VIDEO_TTL_SECONDS

    path = tmp_path / "featured-video.json"
    _write_gallery(path, synced_at=None)
    calls: list[str] = []

    def fake_sync(*, path: Path, **_kwargs):
        calls.append("sync")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["syncedAt"] = "2026-08-07T00:00:00Z"
        data["videos"] = [
            {"youtubeId": "IFa_5chXdJ4", "title": "new", "label": "new"},
        ]
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return {"videos": data["videos"]}, None, "UC_test"

    assert (
        ensure_featured_video_fresh(
            path, sync_fn=fake_sync, head_diverged_fn=lambda: False
        )
        is True
    )
    assert calls == ["sync"]
    assert json.loads(path.read_text(encoding="utf-8"))["videos"][0]["youtubeId"] == (
        "IFa_5chXdJ4"
    )

    calls.clear()
    _write_gallery(path, synced_at="2000-01-01T00:00:00Z")
    assert (
        ensure_featured_video_fresh(
            path,
            ttl_seconds=FEATURED_VIDEO_TTL_SECONDS,
            sync_fn=fake_sync,
            head_diverged_fn=lambda: False,
        )
        is True
    )
    assert calls == ["sync"]


def test_ensure_fresh_error_keeps_existing_file(tmp_path: Path):
    from app.featured_video import ensure_featured_video_fresh, load_featured_video

    path = tmp_path / "featured-video.json"
    _write_gallery(path, synced_at=None, youtube_id="eBLOrvHosR4")
    before = path.read_text(encoding="utf-8")

    def fail_sync(**_kwargs):
        return None, "network down", "UC_test"

    assert (
        ensure_featured_video_fresh(
            path, sync_fn=fail_sync, head_diverged_fn=lambda: False
        )
        is False
    )
    assert path.read_text(encoding="utf-8") == before
    payload = load_featured_video(
        path,
        check_embeddable=lambda _vid: True,
        fetch_candidates=lambda: [],
    )
    assert payload is not None
    assert payload["youtube_id"] == "eBLOrvHosR4"


def test_filter_embeddable_fills_six_from_longer_list():
    from app.youtube_channel import filter_embeddable_videos

    candidates = [{"youtubeId": f"aaaaaaaaaa{i}", "title": f"t{i}"} for i in range(15)]
    # IDs must be 11 chars for real YouTube; our checker ignores format.
    # Make every 3rd candidate non-embeddable so we skip some and still fill 6.
    bad_indexes = {0, 3, 6, 9, 12}
    bad = {candidates[i]["youtubeId"] for i in bad_indexes}

    out = filter_embeddable_videos(
        candidates,
        limit=6,
        check_embeddable=lambda vid: vid not in bad,
    )
    assert len(out) == 6
    assert all(v["youtubeId"] not in bad for v in out)
    assert out[0]["youtubeId"] == candidates[1]["youtubeId"]


def test_run_sync_helper_skips_non_embeddable(tmp_path: Path, monkeypatch):
    """Sync fetches ~15 candidates and fills MAX_VIDEOS after embed skips."""
    from app import featured_video as fv
    from app import youtube_channel as yt

    seed = tmp_path / "featured-video.json"
    seed.write_text(
        json.dumps(
            {
                "enabled": True,
                "eyebrow": "VIDEO",
                "videos": [{"youtubeId": "eBLOrvHosR4", "title": "old", "label": "old"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    candidates = [
        {"youtubeId": "badVideo000", "title": "skip"},
        {"youtubeId": "IFa_5chXdJ4", "title": "A"},
        {"youtubeId": "alsoBad0001", "title": "skip2"},
        {"youtubeId": "EdYQTJfD2hE", "title": "B"},
        {"youtubeId": "4NgOHK064Jc", "title": "C"},
        {"youtubeId": "TKFsNU4Au9w", "title": "D"},
        {"youtubeId": "RwvlWZeFgTA", "title": "E"},
        {"youtubeId": "ZGSmmOGH7Ec", "title": "F"},
        {"youtubeId": "extraGood01", "title": "G"},
    ]
    bad = {"badVideo000", "alsoBad0001"}
    fetch_limits: list[int] = []

    def fake_fetch(_cid: str, *, limit: int = 6, **_k):
        fetch_limits.append(limit)
        return candidates[:limit]

    monkeypatch.setattr(yt, "resolve_channel_id", lambda *_a, **_k: "UC_test_channel")
    monkeypatch.setattr(yt, "fetch_latest_channel_videos", fake_fetch)
    monkeypatch.setattr(
        yt, "is_youtube_embeddable", lambda vid, **_k: vid not in bad
    )

    payload, error, channel_id = fv.run_featured_video_channel_sync(path=seed)
    assert error is None
    assert channel_id == "UC_test_channel"
    assert payload is not None
    ids = [v["youtubeId"] for v in payload["videos"]]
    assert len(ids) == MAX_VIDEOS
    assert fetch_limits and fetch_limits[0] >= MAX_VIDEOS
    assert "badVideo000" not in ids
    assert "alsoBad0001" not in ids
    assert ids[0] == "IFa_5chXdJ4"
    assert ids[-1] == "ZGSmmOGH7Ec"
    reloaded = fv.read_featured_video_file(seed)
    assert len(reloaded["videos"]) == MAX_VIDEOS
    assert all(v["youtubeId"] not in bad for v in reloaded["videos"])
    # Raw channel head (even if unplayable) recorded for stale-vs-head checks
    assert reloaded.get("channelHeadId") == "badVideo000"


def test_channel_feed_url_includes_channel_id():
    from app.youtube_channel import channel_feed_url, channel_videos_page_url

    cid = "UCiI_Xayu0OrUT2swTeV6zTw"
    assert channel_feed_url(cid).endswith(f"channel_id={cid}")
    assert channel_videos_page_url(cid) == (
        f"https://www.youtube.com/channel/{cid}/videos"
    )


def test_parse_videos_from_yt_initial_data_lockups():
    from app.youtube_channel import _parse_videos_from_yt_initial_data

    payload = {
        "contents": {
            "richGridRenderer": {
                "contents": [
                    {
                        "richItemRenderer": {
                            "content": {
                                "lockupViewModel": {
                                    "contentId": "IFa_5chXdJ4",
                                    "contentType": "LOCKUP_CONTENT_TYPE_VIDEO",
                                    "metadata": {
                                        "lockupMetadataViewModel": {
                                            "title": {"content": "回家-DNA鑽石"}
                                        }
                                    },
                                }
                            }
                        }
                    },
                    {
                        "richItemRenderer": {
                            "content": {
                                "lockupViewModel": {
                                    "contentId": "EdYQTJfD2hE",
                                    "contentType": "LOCKUP_CONTENT_TYPE_VIDEO",
                                    "metadata": {
                                        "lockupMetadataViewModel": {
                                            "title": {"content": "有些愛不會消失"}
                                        }
                                    },
                                }
                            }
                        }
                    },
                    {
                        "richItemRenderer": {
                            "content": {
                                "lockupViewModel": {
                                    "contentId": "notAVideo",
                                    "contentType": "LOCKUP_CONTENT_TYPE_PLAYLIST",
                                }
                            }
                        }
                    },
                ]
            }
        }
    }
    videos = _parse_videos_from_yt_initial_data(payload, limit=6)
    assert [v["youtubeId"] for v in videos] == ["IFa_5chXdJ4", "EdYQTJfD2hE"]
    assert videos[0]["title"] == "回家-DNA鑽石"


def test_fetch_latest_falls_back_when_rss_404(monkeypatch):
    from app import youtube_channel as yt

    page_videos = [
        {
            "youtube_id": "IFa_5chXdJ4",
            "youtubeId": "IFa_5chXdJ4",
            "title": "回家",
        }
    ]

    def boom_rss(_cid: str) -> bytes:
        raise RuntimeError(
            "HTTP 404 for https://www.youtube.com/feeds/videos.xml"
            "?channel_id=UC_test_channel"
        )

    monkeypatch.setattr(yt, "_fetch_feed_bytes", boom_rss)
    monkeypatch.setattr(
        yt,
        "_fetch_videos_from_channel_page",
        lambda _cid, *, limit: page_videos[:limit],
    )
    monkeypatch.setattr(yt, "_write_cache", lambda *_a, **_k: None)

    out = yt.fetch_latest_channel_videos("UC_test_channel", limit=6)
    assert out == page_videos


def test_fetch_latest_error_names_urls(monkeypatch):
    from app import youtube_channel as yt

    feed = yt.channel_feed_url("UC_test_channel")
    page = yt.channel_videos_page_url("UC_test_channel")

    monkeypatch.setattr(
        yt,
        "_fetch_feed_bytes",
        lambda _cid: (_ for _ in ()).throw(RuntimeError(f"HTTP 404 for {feed}")),
    )
    monkeypatch.setattr(
        yt,
        "_fetch_videos_from_channel_page",
        lambda _cid, *, limit: (_ for _ in ()).throw(
            RuntimeError(f"HTTP 404 for {page}")
        ),
    )

    try:
        yt.fetch_latest_channel_videos("UC_test_channel", limit=3)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        msg = str(exc)
        assert feed in msg
        assert page in msg


def test_run_sync_error_includes_failed_url(monkeypatch, tmp_path: Path):
    from app import featured_video as fv
    from app import youtube_channel as yt

    feed = yt.channel_feed_url("UC_test_channel")

    monkeypatch.setattr(yt, "resolve_channel_id", lambda *_a, **_k: "UC_test_channel")
    monkeypatch.setattr(
        yt,
        "fetch_latest_channel_videos",
        lambda *_a, **_k: (_ for _ in ()).throw(
            RuntimeError(f"HTTP 404 for {feed}")
        ),
    )

    payload, error, channel_id = fv.run_featured_video_channel_sync(path=tmp_path / "f.json")
    assert payload is None
    assert channel_id == "UC_test_channel"
    assert error is not None
    assert "無法取得頻道影片" in error
    assert feed in error
