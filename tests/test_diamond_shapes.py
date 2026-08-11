"""Diamond cut registry: Asscher seed + custom cuts."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "app" / "diamond_shapes.py"
    spec = importlib.util.spec_from_file_location("diamond_shapes_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_asscher_in_default_shapes():
    ds = _load()
    ids = {s["id"] for s in ds.DEFAULT_SHAPES}
    assert "asscher" in ids
    asscher = next(s for s in ds.DEFAULT_SHAPES if s["id"] == "asscher")
    assert asscher["label_zh"] == "阿斯切"
    assert asscher["label_en"] == "Asscher"


def test_allowed_shape_id_accepts_custom_slug():
    ds = _load()
    assert ds.is_allowed_shape_id("asscher")
    assert ds.is_allowed_shape_id("old-mine")
    assert not ds.is_allowed_shape_id("other")
    assert not ds.is_allowed_shape_id("white")
    assert not ds.is_allowed_shape_id("")
    assert not ds.is_allowed_shape_id("Bad_Case")


def test_create_shape_persists_custom_cut():
    ds = _load()

    class FakeCur:
        def __init__(self):
            self.rows = {
                s["id"]: {
                    "id": s["id"],
                    "label_zh": s["label_zh"],
                    "label_en": s.get("label_en"),
                    "sort_order": s["sort_order"],
                    "is_builtin": True,
                    "created_at": None,
                }
                for s in ds.DEFAULT_SHAPES
            }
            self._last = None
            self.rowcount = 0

        def execute(self, sql, params=None):
            sql_l = " ".join(str(sql).lower().split())
            if "create table" in sql_l:
                return
            if sql_l.startswith("insert into diamond_shapes") and "on conflict" in sql_l:
                return
            if "coalesce(max(sort_order)" in sql_l:
                self._last = {"next": max(r["sort_order"] for r in self.rows.values()) + 1}
                return
            if sql_l.startswith("insert into diamond_shapes") and "returning" in sql_l:
                sid, label_zh, label_en, sort_order = params
                row = {
                    "id": sid,
                    "label_zh": label_zh,
                    "label_en": label_en,
                    "sort_order": sort_order,
                    "is_builtin": False,
                    "created_at": None,
                }
                self.rows[sid] = row
                self._last = row
                return
            if "from diamond_shapes order by" in sql_l:
                self._last = sorted(self.rows.values(), key=lambda r: (r["sort_order"], r["id"]))
                return
            self._last = None

        def fetchone(self):
            return self._last if isinstance(self._last, dict) else None

        def fetchall(self):
            return self._last if isinstance(self._last, list) else []

    cur = FakeCur()
    shape, err = ds.create_shape(cur, label_zh="舊礦工", label_en="Old Mine")
    assert err is None
    assert shape is not None
    assert shape["id"] == "old-mine"
    assert shape["labelZh"] == "舊礦工"
    ids = ds.valid_shape_ids(cur)
    assert "old-mine" in ids
    assert "asscher" in ids


def test_matrix_payload_includes_asscher():
    ds = _load()
    payload = ds.matrix_shapes_payload()
    assert any(s["id"] == "asscher" and s["labelZh"] == "阿斯切" for s in payload)
