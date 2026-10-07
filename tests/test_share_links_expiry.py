"""Share links: links nobody opens for a year expire; opening a link renews it.

Offline (fake cursors, no DB). Complements tests/test_share_links.py.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app import share_links as sl
from app.controllers import share_controller as sc

CONFIG = {"category": "ring", "type": "style-1", "gold": "14k", "carat": "0.3"}


class _Cur:
    def __init__(self, rowcount=0):
        self.calls: list[tuple[str, tuple]] = []
        self.rowcount = rowcount

    def execute(self, sql, params=None):
        self.calls.append((" ".join(sql.split()), tuple(params or ())))


# ── settings ─────────────────────────────────────────────────────────────

def test_expiry_settings():
    assert sl.SHARE_LINK_TTL_DAYS == 365
    assert sl.TOUCH_INTERVAL_DAYS == 1
    assert sl.CLEANUP_BATCH == 500
    assert 0 < sl.CLEANUP_CHANCE < 0.1


def test_should_cleanup_follows_the_chance():
    assert sl.should_cleanup(lambda: 0.0) is True
    assert sl.should_cleanup(lambda: sl.CLEANUP_CHANCE - 0.001) is True
    assert sl.should_cleanup(lambda: sl.CLEANUP_CHANCE) is False
    assert sl.should_cleanup(lambda: 0.99) is False


# ── schema ───────────────────────────────────────────────────────────────

def test_schema_adds_last_opened_column_and_index_safely():
    cur = _Cur()
    sl.ensure_share_links_schema(cur)
    joined = " ".join(sql for sql, _ in cur.calls)
    # Idempotent: it must work on a table that already exists on the live database.
    assert "add column if not exists last_opened_at timestamptz" in joined
    assert "create index if not exists share_links_last_seen_idx" in joined
    assert "coalesce(last_opened_at, created_at)" in joined


# ── touch (opening a link renews it) ─────────────────────────────────────

def test_touch_updates_at_most_once_a_day_and_uppercases_the_code():
    cur = _Cur()
    sl.touch_link(cur, "k7m29qxa")
    (sql, params), = cur.calls
    assert sql.startswith("update share_links set last_opened_at = now()")
    assert "last_opened_at is null or last_opened_at < now() - make_interval(days => %s)" in sql
    assert params == ("K7M29QXA", sl.TOUCH_INTERVAL_DAYS)


def test_touch_ignores_invalid_codes():
    cur = _Cur()
    sl.touch_link(cur, "../etc")
    sl.touch_link(cur, "")
    assert cur.calls == []


# ── cleanup ──────────────────────────────────────────────────────────────

def test_delete_expired_uses_last_open_else_creation_and_a_batch_limit():
    cur = _Cur(rowcount=7)
    assert sl.delete_expired(cur) == 7
    (sql, params), = cur.calls
    assert sql.startswith("delete from share_links where code in (")
    assert "coalesce(last_opened_at, created_at) < now() - make_interval(days => %s)" in sql
    assert "limit %s" in sql
    assert params == (365, 500)


def test_delete_expired_handles_missing_rowcount():
    assert sl.delete_expired(_Cur(rowcount=None)) == 0


# ── controller wiring ────────────────────────────────────────────────────

@contextmanager
def _conn(cur):
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    yield conn


def _request(body: bytes):
    req = MagicMock()

    async def _body():
        return body

    req.body = _body
    return req


def _create(monkeypatch, cur, *, cleanup: bool, cleanup_raises=False):
    deleted = []

    def fake_delete(c):
        deleted.append(True)
        if cleanup_raises:
            raise RuntimeError("db hiccup")
        return 3

    monkeypatch.setattr(sc, "enforce_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr(sc, "get_connection", lambda: _conn(cur))
    monkeypatch.setattr(sc.sl, "get_or_create_code", lambda c, config: "K7M29QXA")
    monkeypatch.setattr(sc.sl, "should_cleanup", lambda *a, **k: cleanup)
    monkeypatch.setattr(sc.sl, "delete_expired", fake_delete)
    resp = asyncio.run(sc.create_share_link(_request(json.dumps(CONFIG).encode())))
    return resp, deleted


def test_creating_a_link_sometimes_trims_old_ones(monkeypatch):
    resp, deleted = _create(monkeypatch, object(), cleanup=True)
    assert resp.status_code == 200 and deleted == [True]
    resp, deleted = _create(monkeypatch, object(), cleanup=False)
    assert resp.status_code == 200 and deleted == []


def test_a_failing_cleanup_never_blocks_sharing(monkeypatch):
    resp, deleted = _create(monkeypatch, object(), cleanup=True, cleanup_raises=True)
    assert deleted == [True]
    assert resp.status_code == 200
    assert json.loads(resp.body)["path"] == "/s/K7M29QXA"


def _read(monkeypatch, code, *, config, touch_raises=False):
    touched = []

    def fake_touch(cur, c):
        touched.append(c)
        if touch_raises:
            raise RuntimeError("db hiccup")

    monkeypatch.setattr(sc, "get_connection", lambda: _conn(object()))
    monkeypatch.setattr(sc.sl, "fetch_config", lambda cur, c: config)
    monkeypatch.setattr(sc.sl, "touch_link", fake_touch)
    return sc.read_share_link(code), touched


def test_opening_a_link_renews_it(monkeypatch):
    resp, touched = _read(monkeypatch, "K7M29QXA", config={"category": "ring", "type": "x"})
    assert resp.status_code == 200 and touched == ["K7M29QXA"]


def test_unknown_or_expired_link_is_a_404_and_not_renewed(monkeypatch):
    resp, touched = _read(monkeypatch, "K7M29QXA", config=None)
    assert resp.status_code == 404 and touched == []
    resp, touched = _read(monkeypatch, "../etc", config={"category": "ring", "type": "x"})
    assert resp.status_code == 404 and touched == []


def test_a_failing_renewal_never_blocks_viewing(monkeypatch):
    resp, _ = _read(monkeypatch, "K7M29QXA", config={"category": "ring", "type": "x"}, touch_raises=True)
    assert resp.status_code == 200


# ── the share page script (runs in node) ─────────────────────────────────

NODE = shutil.which("node")
SCRIPT = Path(__file__).resolve().parents[1] / "public" / "js" / "share-summary.js"


def _run_page(pathname: str, fetch_status: int) -> dict:
    harness = f"""
    const mounts = []; const fetches = []; let ready = null;
    const root = {{ innerHTML: '' }};
    global.window = {{
      location: {{ pathname: {json.dumps(pathname)}, search: '' }},
      ShopConfigToken: {{
        fromPath: () => ({{ fromLongToken: true }}),
        fromQuery: () => null
      }},
      ShopQuoteRender: {{ mount: (r, config, mode) => mounts.push({{ config, mode }}) }}
    }};
    global.document = {{
      getElementById: () => root,
      addEventListener: (name, fn) => {{ if (name === 'DOMContentLoaded') ready = fn; }}
    }};
    global.fetch = (url) => {{
      fetches.push(url);
      const ok = {fetch_status} === 200;
      return Promise.resolve({{ ok, status: {fetch_status}, json: () => Promise.resolve({{ config: {{ fromServer: true }} }}) }});
    }};
    eval(require('fs').readFileSync({json.dumps(str(SCRIPT))}, 'utf8'));
    ready();
    setTimeout(() => console.log(JSON.stringify({{ mounts, fetches, html: root.innerHTML }})), 50);
    """
    out = subprocess.run(
        [NODE, "-e", harness], capture_output=True, text=True, encoding="utf-8", timeout=60
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_share_page_loads_a_short_code_from_the_server():
    result = _run_page("/s/K7M29QXA", 200)
    assert result["fetches"] == ["/api/share/K7M29QXA"]
    assert result["mounts"] == [{"config": {"fromServer": True}, "mode": "share"}]


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_share_page_decodes_an_old_long_link_locally():
    long_token = "e" * 300
    result = _run_page(f"/s/{long_token}", 200)
    assert result["fetches"] == []
    assert result["mounts"] == [{"config": {"fromLongToken": True}, "mode": "share"}]


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_share_page_explains_an_expired_link():
    result = _run_page("/s/K7M29QXA", 404)
    assert result["mounts"] == []
    assert "不存在或已失效" in result["html"]
