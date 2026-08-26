"""Embed-page playability checks (oEmbed alone is not enough)."""

from __future__ import annotations

import app.youtube_channel as yt


def test_embed_page_indicates_playable_ok():
    html = (
        r'{\"previewPlayabilityStatus\":{\"status\":\"OK\",'
        r'\"playableInEmbed\":true,\"contextParams\":\"x\"}}'
    )
    assert yt.embed_page_indicates_playable(html) is True


def test_embed_page_indicates_blocked_unplayable():
    html = (
        r'{\"previewPlayabilityStatus\":{\"status\":\"UNPLAYABLE\",'
        r'\"reason\":\"Video unavailable\"}}'
    )
    assert yt.embed_page_indicates_playable(html) is False


def test_embed_page_indicates_blocked_disabled_snippet():
    html = "Playback on other websites has been disabled by the video owner."
    assert yt.embed_page_indicates_playable(html) is False


def test_embed_page_indicates_blocked_playable_false():
    html = (
        '{"previewPlayabilityStatus":{"status":"OK","playableInEmbed":false}}'
    )
    assert yt.embed_page_indicates_playable(html) is False


def test_is_youtube_embeddable_oembed_404_skips(monkeypatch):
    yt._embed_memory.clear()
    monkeypatch.setattr(yt, "_oembed_available", lambda *_a, **_k: False)
    monkeypatch.setattr(
        yt, "_fetch_embed_page_html", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError)
    )
    monkeypatch.setattr(yt, "_write_embed_disk_cache", lambda *_a, **_k: None)
    assert yt.is_youtube_embeddable("blockedVid01", referer="https://www.imprint-diamond.com/") is False


def test_is_youtube_embeddable_oembed_ok_but_embed_blocked(monkeypatch):
    yt._embed_memory.clear()
    monkeypatch.setattr(yt, "_oembed_available", lambda *_a, **_k: True)
    monkeypatch.setattr(
        yt,
        "_fetch_embed_page_html",
        lambda *_a, **_k: (
            r'{\"previewPlayabilityStatus\":{\"status\":\"UNPLAYABLE\",'
            r'\"reason\":\"Video unavailable\"}}'
        ),
    )
    monkeypatch.setattr(yt, "_read_embed_disk_cache", lambda *_a, **_k: None)
    monkeypatch.setattr(yt, "_write_embed_disk_cache", lambda *_a, **_k: None)
    assert yt.is_youtube_embeddable("IFa_5chXdJ4", referer="http://127.0.0.1:8000/") is False


def test_is_youtube_embeddable_oembed_ok_and_embed_playable(monkeypatch):
    yt._embed_memory.clear()
    monkeypatch.setattr(yt, "_oembed_available", lambda *_a, **_k: True)
    monkeypatch.setattr(
        yt,
        "_fetch_embed_page_html",
        lambda *_a, **_k: (
            r'{\"previewPlayabilityStatus\":{\"status\":\"OK\",'
            r'\"playableInEmbed\":true}}'
        ),
    )
    monkeypatch.setattr(yt, "_read_embed_disk_cache", lambda *_a, **_k: None)
    monkeypatch.setattr(yt, "_write_embed_disk_cache", lambda *_a, **_k: None)
    assert yt.is_youtube_embeddable("EdYQTJfD2hE", referer="https://www.imprint-diamond.com/") is True


def test_is_youtube_embeddable_network_fail_not_cached(monkeypatch):
    yt._embed_memory.clear()
    monkeypatch.setattr(yt, "_oembed_available", lambda *_a, **_k: True)
    monkeypatch.setattr(yt, "_fetch_embed_page_html", lambda *_a, **_k: None)
    monkeypatch.setattr(yt, "_read_embed_disk_cache", lambda *_a, **_k: None)
    wrote = []
    monkeypatch.setattr(
        yt, "_write_embed_disk_cache", lambda *a, **k: wrote.append((a, k))
    )
    assert yt.is_youtube_embeddable("EdYQTJfD2hE") is False
    assert wrote == []
    assert yt._embed_memory == {}


def test_filter_uses_referer_wrapper(monkeypatch):
    seen = []

    def fake(vid, *, referer=None, **_k):
        seen.append((vid, referer))
        return vid != "badVideo000"

    monkeypatch.setattr(yt, "is_youtube_embeddable", fake)
    out = yt.filter_embeddable_videos(
        [
            {"youtubeId": "badVideo000", "title": "x"},
            {"youtubeId": "goodVideo01", "title": "y"},
        ],
        limit=6,
        referer="http://127.0.0.1:8000/",
    )
    assert [v["youtubeId"] for v in out] == ["goodVideo01"]
    assert seen[0][1] == "http://127.0.0.1:8000/"
