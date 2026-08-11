"""Unit tests for engagement-page iconic ring slots."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.engagement_rings import (
    SLOT_COUNT,
    normalize_product_ids,
    read_engagement_rings_file,
    resolve_engagement_ring_cards,
    save_engagement_rings_file,
    shop_step2_url,
    validate_admin_body,
)


def test_shop_step2_url():
    pid = "11111111-1111-1111-1111-111111111111"
    assert shop_step2_url("ring", pid) == (
        f"/shop/calculator/?category=ring&product={pid}"
    )


def test_normalize_pads_and_strips_invalid(tmp_path: Path):
    ids = normalize_product_ids(["not-uuid", "11111111-1111-1111-1111-111111111111"])
    assert len(ids) == SLOT_COUNT
    assert ids[0] == ""
    assert ids[1] == "11111111-1111-1111-1111-111111111111"
    assert ids[2] == ""
    assert ids[3] == ""


def test_validate_admin_body_accepts_empty_slots():
    saved, err = validate_admin_body({"productIds": ["", "", "", ""]})
    assert err is None
    assert saved == {"productIds": ["", "", "", ""]}


def test_validate_admin_body_rejects_bad_uuid():
    saved, err = validate_admin_body({"productIds": ["bad", "", "", ""]})
    assert saved is None
    assert err and "invalid product id" in err


def test_save_and_read_roundtrip(tmp_path: Path):
    path = tmp_path / "engagement-rings.json"
    pid = str(uuid4())
    payload = save_engagement_rings_file({"productIds": [pid, "", "", ""]}, path)
    assert payload["productIds"][0] == pid
    loaded = read_engagement_rings_file(path)
    assert loaded["productIds"][0] == pid
    assert path.read_text(encoding="utf-8")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["productIds"][0] == pid


class _FakeCur:
    def __init__(self, products: dict[str, dict], images: dict[str, list[dict]]):
        self.products = products
        self.images = images
        self._last = None
        self._params = None

    def execute(self, sql, params=None):
        self._last = " ".join(str(sql).lower().split())
        self._params = params

    def fetchone(self):
        if "from products" in (self._last or "") and self._params:
            return self.products.get(str(self._params[0]))
        return None

    def fetchall(self):
        if "from product_images" in (self._last or "") and self._params:
            return self.images.get(str(self._params[0]), [])
        return []


def test_resolve_uses_product_and_shop_link(tmp_path: Path):
    path = tmp_path / "engagement-rings.json"
    pid = str(uuid4())
    save_engagement_rings_file({"productIds": [pid, "", "", ""]}, path)
    cur = _FakeCur(
        {
            pid: {
                "id": pid,
                "category": "ring",
                "name_zh": "測試戒指",
                "name_en": "Test Ring",
                "description_zh": "說明文字",
                "is_published": True,
            }
        },
        {
            pid: [
                {
                    "color": "white",
                    "file_path": "https://cdn.example.com/ring.jpg",
                }
            ]
        },
    )
    cards = resolve_engagement_ring_cards(cur, path)
    assert len(cards) == 4
    assert cards[0]["name_zh"] == "測試戒指"
    assert cards[0]["image_url"] == "https://cdn.example.com/ring.jpg"
    assert cards[0]["href"] == shop_step2_url("ring", pid)
    assert cards[1]["href"].startswith("/jewelry/rings/")
