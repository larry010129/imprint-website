"""Tests for WebP upload basename, one-deep replace/restore, and migrate helpers."""

from __future__ import annotations

import asyncio
import importlib.util
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.admin_products import (
    delete_product_image_urls_if_unreferenced,
    replace_product_image,
    restore_product_image,
)
from app.controllers.admin_controller import product_upload
from app.storage import product_object_key
from tests.test_storage import SUPABASE_URL, _png_upload

PUBLIC = f"{SUPABASE_URL}/storage/v1/object/public/shop-media"
_UUID32 = re.compile(r"^[0-9a-f]{32}$", re.I)


def _url(key: str) -> str:
    return f"{PUBLIC}/{key}"


def _load_migrate_module():
    path = Path(__file__).resolve().parents[1] / (
        "scripts/migrate_product_images_to_webp.py"
    )
    spec = importlib.util.spec_from_file_location("migrate_product_images_to_webp", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _storage_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", SUPABASE_URL)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "shop-media")


def test_product_object_key_preserves_chinese_filename_reversibly():
    """Supabase rejects raw Chinese keys — encode as u-<base64url>, decode back."""
    from app.storage import decode_storage_filename

    original = "玫瑰金主圖.webp"
    key = product_object_key("ring-front", "white", original, category="ring")
    name = key.rsplit("/", 1)[-1]
    assert name.endswith(".webp")
    assert name.startswith("u-")
    assert all(ord(ch) < 128 for ch in name)
    assert decode_storage_filename(name) == original


def test_product_upload_keeps_original_stem_webp(monkeypatch):
    monkeypatch.setattr(
        "app.controllers.admin_controller._require_admin",
        lambda _req: "admin-user",
    )
    calls: list[tuple] = []

    def fake_upload_image(kind: str, name: str, data: bytes, ext: str, upsert: bool = False):
        calls.append((kind, name, ext, upsert))
        return f"{PUBLIC}/products/{name}"

    monkeypatch.setattr("app.storage.upload_image", fake_upload_image)

    resp = asyncio.run(
        product_upload(
            MagicMock(),
            file=_png_upload("ring-front.PNG"),
            product_id=None,
            color=None,
        )
    )
    assert resp.status_code == 200
    assert calls and calls[0][0] == "products"
    assert calls[0][1].endswith("ring-front.webp")
    assert Path(calls[0][1]).name == "ring-front.webp"
    assert not _UUID32.fullmatch(Path(calls[0][1]).stem)
    assert calls[0][2] == ".webp"


def test_replace_keeps_previous_and_drops_older(monkeypatch):
    a = _url("products/p/white/a.webp")
    b = _url("products/p/white/b.webp")
    c = _url("products/p/white/c.webp")
    deleted: list[str] = []
    monkeypatch.setattr(
        "app.admin_products.delete_by_url",
        lambda u: deleted.append(u) or True,
    )
    monkeypatch.setattr(
        "app.admin_products.ensure_product_images_previous_column",
        lambda _cur: None,
    )
    monkeypatch.setattr(
        "app.admin_products.normalize_product_image_url",
        lambda url, _color=None: url,
    )

    state = {"file_path": a, "previous_file_path": None}

    class Cur:
        def execute(self, sql, params=None):
            sql_l = str(sql).lower()
            self._sql = sql_l
            self._params = params
            if "update product_images" in sql_l:
                state["file_path"] = params[0]
                state["previous_file_path"] = params[1]
            if "select 1 from product_images" in sql_l:
                # GC: only "referenced" if still current or previous.
                url = params[0]
                self._ref = url in {
                    state["file_path"],
                    state["previous_file_path"],
                }

        def fetchone(self):
            if "select id, file_path" in getattr(self, "_sql", ""):
                return {
                    "id": "img-1",
                    "file_path": state["file_path"],
                    "previous_file_path": state["previous_file_path"],
                }
            if "update product_images" in getattr(self, "_sql", ""):
                return {
                    "id": "img-1",
                    "product_id": "prod-1",
                    "color": "white",
                    "file_path": state["file_path"],
                    "sort_order": 0,
                    "previous_file_path": state["previous_file_path"],
                }
            if "select 1 from product_images" in getattr(self, "_sql", ""):
                return {"ok": 1} if getattr(self, "_ref", False) else None
            return None

    cur = Cur()
    row, err = replace_product_image(cur, "img-1", b)
    assert err is None
    assert row["file_path"] == b
    assert row["previous_file_path"] == a
    assert deleted == []

    row, err = replace_product_image(cur, "img-1", c)
    assert err is None
    assert row["file_path"] == c
    assert row["previous_file_path"] == b
    assert deleted == [a]


def test_restore_swaps_and_gc_current(monkeypatch):
    a = _url("products/p/white/a.webp")
    b = _url("products/p/white/b.webp")
    deleted: list[str] = []
    monkeypatch.setattr(
        "app.admin_products.delete_by_url",
        lambda u: deleted.append(u) or True,
    )
    monkeypatch.setattr(
        "app.admin_products.ensure_product_images_previous_column",
        lambda _cur: None,
    )

    state = {"file_path": b, "previous_file_path": a}

    class Cur:
        def execute(self, sql, params=None):
            sql_l = str(sql).lower()
            self._sql = sql_l
            self._params = params
            if "update product_images" in sql_l:
                state["file_path"] = params[0]
                state["previous_file_path"] = None
            if "select 1 from product_images" in sql_l:
                url = params[0]
                self._ref = url in {
                    state["file_path"],
                    state["previous_file_path"],
                }

        def fetchone(self):
            if "select id, file_path" in getattr(self, "_sql", ""):
                return {
                    "id": "img-1",
                    "file_path": state["file_path"],
                    "previous_file_path": state["previous_file_path"],
                }
            if "update product_images" in getattr(self, "_sql", ""):
                return {
                    "id": "img-1",
                    "product_id": "prod-1",
                    "color": "white",
                    "file_path": state["file_path"],
                    "sort_order": 0,
                    "previous_file_path": state["previous_file_path"],
                }
            if "select 1 from product_images" in getattr(self, "_sql", ""):
                return {"ok": 1} if getattr(self, "_ref", False) else None
            return None

    cur = Cur()
    row, err = restore_product_image(cur, "img-1")
    assert err is None
    assert row["file_path"] == a
    assert row["previous_file_path"] is None
    assert deleted == [b]


def test_gc_keeps_previous_file_path_ref(monkeypatch):
    url = _url("products/p/white/prev.webp")
    monkeypatch.setattr(
        "app.admin_products.delete_by_url",
        lambda _u: (_ for _ in ()).throw(AssertionError("must not delete")),
    )
    monkeypatch.setattr(
        "app.admin_products.ensure_product_images_previous_column",
        lambda _cur: None,
    )
    cur = MagicMock()
    # Referenced via previous_file_path.
    cur.fetchone.return_value = {"ok": 1}
    assert delete_product_image_urls_if_unreferenced(cur, [url]) == 0


def test_migrate_helpers_webp_path_and_non_webp_detect():
    mod = _load_migrate_module()
    assert mod._is_non_webp_url("https://x/y/a.JPG")
    assert not mod._is_non_webp_url("https://x/y/a.webp")
    assert mod._webp_object_path("products/p/white/shot.png") == (
        "products/p/white/shot.webp"
    )


def test_migrate_url_dry_run(monkeypatch):
    mod = _load_migrate_module()
    monkeypatch.setattr(
        mod,
        "object_path_from_public_url",
        lambda url: "products/p/white/old.png"
        if url.endswith("old.png")
        else None,
    )
    monkeypatch.setattr(
        mod,
        "public_url_for_object",
        lambda key: f"{PUBLIC}/{key}",
    )
    old = _url("products/p/white/old.png")
    new_url, changed, old_out = mod.migrate_url(old, dry_run=True)
    assert changed is True
    assert old_out == old
    assert new_url.endswith("old.webp")


# ── upload must never orphan: pid given ⇒ DB row or hard error ──────────

import contextlib  # noqa: E402


class _FakeCur:
    def execute(self, *args, **kwargs):
        self._sql = str(args[0]).lower() if args else ""

    def fetchone(self):
        return None  # product lookup miss → folder falls back to id segment

    def fetchall(self):
        return []


class _FakeConn:
    @contextlib.contextmanager
    def cursor(self):
        yield _FakeCur()


@contextlib.contextmanager
def _fake_conn_cm():
    yield _FakeConn()


def _stub_upload_io(monkeypatch):
    monkeypatch.setattr(
        "app.controllers.admin_controller._require_admin",
        lambda _req: "admin-user",
    )
    monkeypatch.setattr(
        "app.storage.upload_image",
        lambda kind, name, data, ext, upsert=False: f"{PUBLIC}/products/{name}",
    )
    monkeypatch.setattr(
        "app.controllers.admin_controller.get_connection", _fake_conn_cm
    )
    monkeypatch.setattr(
        "app.controllers.admin_controller.get_transaction", _fake_conn_cm
    )
    monkeypatch.setattr(
        "app.controllers.admin_controller.clear_public_catalog_cache",
        lambda: None,
    )


def test_upload_errors_when_insert_skipped(monkeypatch):
    """pid+slot but append returns None → 502, not a bare success that orphans."""
    _stub_upload_io(monkeypatch)
    monkeypatch.setattr(
        "app.controllers.admin_controller.append_product_image",
        lambda cur, pid, slot, url: None,
    )
    resp = asyncio.run(
        product_upload(
            MagicMock(),
            file=_png_upload("shot.png"),
            product_id="2c4d5c52-2b05-4c71-a755-4db19f8c1260",
            color="round",
        )
    )
    assert resp.status_code == 502
    assert "資料庫" in resp.body.decode("utf-8")


def test_upload_requires_slot_when_product_given(monkeypatch):
    """pid without slot would skip the insert silently → 400 instead."""
    _stub_upload_io(monkeypatch)
    resp = asyncio.run(
        product_upload(
            MagicMock(),
            file=_png_upload("shot.png"),
            product_id="2c4d5c52-2b05-4c71-a755-4db19f8c1260",
            color=None,
        )
    )
    assert resp.status_code == 400
    assert "圖片選項" in resp.body.decode("utf-8")


def test_upload_returns_persisted_image_row(monkeypatch):
    """Happy path: response carries the product_images row the admin UI needs."""
    _stub_upload_io(monkeypatch)
    monkeypatch.setattr(
        "app.controllers.admin_controller.append_product_image",
        lambda cur, pid, slot, url: {
            "id": "img-1",
            "product_id": pid,
            "color": slot,
            "file_path": url,
            "sort_order": 0,
            "previous_file_path": None,
        },
    )
    resp = asyncio.run(
        product_upload(
            MagicMock(),
            file=_png_upload("shot.png"),
            product_id="2c4d5c52-2b05-4c71-a755-4db19f8c1260",
            color="round",
        )
    )
    assert resp.status_code == 200
    import json

    payload = json.loads(resp.body.decode("utf-8"))
    assert payload["image"]["id"] == "img-1"
    assert payload["image"]["color"] == "round"
    assert payload["image"]["file_path"] == payload["url"]
