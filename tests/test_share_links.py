"""Short share links for the calculator's 分享摘要 (no DB, no network)."""

from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from unittest.mock import MagicMock

import psycopg
import pytest

from app import share_links as sl
from app.controllers import share_controller as sc

CONFIG = {
    "category": "pendant",
    "type": "d9954688-2d57-4c2c-a0cd-a1b532d43543",
    "gold": "14k",
    "color": "rose",
    "carat": "0.3",
    "includeChain": True,
    "chainLength": 36,
    "diamondShape": "round",
    "summaryZh": "Raphael十字架墜鍊",
}


# ── what gets stored ─────────────────────────────────────────────────────

def test_sanitize_keeps_known_fields_and_drops_the_rest():
    raw = {
        **CONFIG,
        "clientPricing": {"total": 1},
        "total": 1,
        "evil": "<script>",
        "nested": {"a": 1},
        "ringSize": None,
    }
    out = sl.sanitize_config(raw)
    assert out == {**CONFIG, "ringSize": None}
    assert "clientPricing" not in out and "evil" not in out and "nested" not in out


def test_sanitize_requires_category_and_type():
    assert sl.sanitize_config({"category": "ring"}) is None
    assert sl.sanitize_config({"type": "x"}) is None
    assert sl.sanitize_config("nope") is None
    assert sl.sanitize_config(None) is None
    assert sl.sanitize_config({}) is None


def test_sanitize_bounds_every_value():
    assert sl.sanitize_config({**CONFIG, "summaryZh": "x" * 500}).get("summaryZh") is None
    assert "gold" not in sl.sanitize_config({**CONFIG, "gold": "x" * 100})
    assert "chainLength" not in sl.sanitize_config({**CONFIG, "chainLength": 10**9})
    assert "chainLength" not in sl.sanitize_config({**CONFIG, "chainLength": float("inf")})
    assert "includeChain" not in sl.sanitize_config({**CONFIG, "includeChain": "yes"})
    assert "chainLength" not in sl.sanitize_config({**CONFIG, "chainLength": True})
    assert sl.sanitize_config({**CONFIG, "carat": 0.5})["carat"] == 0.5
    assert sl.sanitize_config({**CONFIG, "gold": ["14k"]}).get("gold") is None


def test_preview_images_must_be_our_own_media(monkeypatch):
    monkeypatch.setattr(sl, "_allowed_hosts", lambda: {"www.imprint-diamond.com"})
    good = [
        "/static/images/x.png",
        "https://www.imprint-diamond.com/a.png",
        "https://erobemoojyptyxvnyvuf.supabase.co/storage/v1/object/public/x.png",
    ]
    bad = [
        "https://evil.example.com/a.png",
        "//evil.example.com/a.png",
        "javascript:alert(1)",
        "http://www.imprint-diamond.com/a.png",
        "data:image/png;base64,AAAA",
        "https://evil.com/?https://www.imprint-diamond.com",
        "",
    ]
    for url in good:
        assert sl.sanitize_config({**CONFIG, "previewImage": url})["previewImage"] == url
    for url in bad:
        assert "previewImage" not in sl.sanitize_config({**CONFIG, "previewImage": url}), url


def test_same_configuration_hashes_the_same_regardless_of_order():
    a = sl.sanitize_config(CONFIG)
    b = sl.sanitize_config(dict(reversed(list(CONFIG.items()))))
    assert sl.config_hash(a) == sl.config_hash(b)
    assert sl.config_hash(a) != sl.config_hash({**a, "gold": "18k"})


# ── the short code ───────────────────────────────────────────────────────

def test_codes_are_short_random_and_readable():
    codes = {sl.generate_code() for _ in range(3000)}
    assert len(codes) == 3000  # 32^8 combinations: no repeats in a sample
    for code in codes:
        assert len(code) == sl.CODE_LENGTH == 8
        assert set(code) <= set(sl.CODE_ALPHABET)
        assert not set(code) & set("IO01")
        assert sl.is_valid_code(code)
    assert len(sl.CODE_ALPHABET) == 32


def test_code_validation():
    for ok in ("K7M29QXA", "k7m29qxa", "ABCDEF"):
        assert sl.is_valid_code(ok)
    for bad in ("", None, "ab", "K7M2-9QXA", "x" * 13, "../etc", "K7M29QXA/"):
        assert not sl.is_valid_code(bad)


# ── storage ──────────────────────────────────────────────────────────────

class _Cur:
    def __init__(self, existing=None, collisions=0, race=False):
        self.existing = existing
        self.collisions = collisions
        self.race = race
        self.inserted: list = []
        self._last = None

    def execute(self, sql, params=None):
        text = " ".join(sql.split())
        if text.startswith("select code from share_links"):
            self._last = {"code": self.existing} if self.existing else None
            if self.race and self.inserted == [] and self.collisions == 0:
                pass
        elif text.startswith("insert into share_links"):
            if self.collisions > 0:
                self.collisions -= 1
                raise psycopg.errors.UniqueViolation("code taken")
            if self.race:
                self.existing = "RACEWON2"
                self._last = None  # on conflict do nothing -> no row returned
                return
            self.inserted.append(params[0])
            self._last = {"code": params[0]}
        elif text.startswith("select config from share_links"):
            self._last = self.existing

    def fetchone(self):
        return self._last


def test_existing_configuration_reuses_its_code():
    cur = _Cur(existing="EXISTING")
    assert sl.get_or_create_code(cur, sl.sanitize_config(CONFIG)) == "EXISTING"
    assert cur.inserted == []


def test_new_configuration_gets_a_new_random_code():
    cur = _Cur()
    code = sl.get_or_create_code(cur, sl.sanitize_config(CONFIG))
    assert sl.is_valid_code(code) and len(code) == 8
    assert cur.inserted == [code]


def test_taken_code_is_redrawn():
    cur = _Cur(collisions=3)
    code = sl.get_or_create_code(cur, sl.sanitize_config(CONFIG))
    assert cur.inserted == [code]


def test_gives_up_after_too_many_collisions():
    with pytest.raises(RuntimeError):
        sl.get_or_create_code(_Cur(collisions=99), sl.sanitize_config(CONFIG))


def test_simultaneous_identical_share_returns_the_winners_code():
    cur = _Cur(race=True)
    assert sl.get_or_create_code(cur, sl.sanitize_config(CONFIG)) == "RACEWON2"


def test_fetch_config():
    stored = sl.sanitize_config(CONFIG)
    assert sl.fetch_config(_Cur(existing={"config": stored}), "K7M29QXA") == stored
    assert sl.fetch_config(_Cur(), "K7M29QXA") is None
    assert sl.fetch_config(_Cur(existing={"config": stored}), "bad code!") is None


def test_schema_enables_row_level_security():
    seen: list[str] = []

    class Cur:
        def execute(self, sql, params=None):
            seen.append(" ".join(sql.split()))

    sl.ensure_share_links_schema(Cur())
    joined = " ".join(seen)
    assert "create table if not exists share_links" in joined
    assert "config_hash text not null unique" in joined
    assert "enable row level security" in joined


# ── the public API ───────────────────────────────────────────────────────

def _request(body: bytes = b""):
    req = MagicMock()

    async def _body():
        return body

    req.body = _body
    return req


def _json(resp):
    return json.loads(resp.body)


@contextmanager
def _conn(cur):
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    yield conn


def _create(body: bytes):
    return asyncio.run(sc.create_share_link(_request(body)))


def test_create_is_rate_limited(monkeypatch):
    monkeypatch.setattr(sc, "enforce_rate_limit", lambda *a, **k: False)
    resp = _create(json.dumps(CONFIG).encode())
    assert resp.status_code == 429 and resp.headers["cache-control"] == "no-store"


def test_create_rejects_bad_input(monkeypatch):
    monkeypatch.setattr(sc, "enforce_rate_limit", lambda *a, **k: True)
    assert _create(b"x" * (sl.MAX_BODY_BYTES + 1)).status_code == 413
    assert _create(b"{not json").status_code == 400
    assert _create(b"\xff\xfe").status_code == 400
    assert _create(json.dumps({"category": "ring"}).encode()).status_code == 400
    assert _create(json.dumps([1, 2]).encode()).status_code == 400


def test_create_returns_a_short_code(monkeypatch):
    stored = {}

    def fake_get_or_create(cur, config):
        stored["config"] = config
        return "K7M29QXA"

    monkeypatch.setattr(sc, "enforce_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr(sc, "get_connection", lambda: _conn(object()))
    monkeypatch.setattr(sc.sl, "get_or_create_code", fake_get_or_create)
    resp = _create(json.dumps({**CONFIG, "clientPricing": {"total": 1}}).encode())
    assert resp.status_code == 200
    assert _json(resp) == {"code": "K7M29QXA", "path": "/s/K7M29QXA"}
    assert "clientPricing" not in stored["config"]  # never stored


def test_read_returns_config_or_404(monkeypatch):
    stored = sl.sanitize_config(CONFIG)
    monkeypatch.setattr(sc, "get_connection", lambda: _conn(object()))
    monkeypatch.setattr(sc.sl, "fetch_config", lambda cur, code: stored if code == "K7M29QXA" else None)
    ok = sc.read_share_link("K7M29QXA")
    assert ok.status_code == 200 and _json(ok) == {"config": stored}
    assert "max-age" in ok.headers["cache-control"]
    assert sc.read_share_link("ZZZZZZZZ").status_code == 404
    assert sc.read_share_link("../etc").status_code == 404
