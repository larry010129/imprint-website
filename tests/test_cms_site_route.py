"""Host page site_route + section→page_images sync helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.cms_pages import (
    DEFAULT_PROPS,
    ensure_site_route_page,
    page_key_for_cms_page,
    section_page_image_slot_key,
    site_route_to_slug,
    sync_section_page_image_from_props,
    upsert_section_page_image,
)


def test_site_route_to_slug_stable():
    assert site_route_to_slug("/") == "site-home"
    assert site_route_to_slug("/about.html") == "site-about-html"
    assert site_route_to_slug("/series/first-love/") == "site-series-first-love"
    assert site_route_to_slug("/about.html") == site_route_to_slug("/about.html")


def test_page_key_prefers_site_route():
    assert page_key_for_cms_page({"site_route": "/", "slug": "site-home"}) == "/"
    assert page_key_for_cms_page({"site_route": None, "slug": "promo"}) == "/p/promo"
    sid = str(uuid4())
    assert section_page_image_slot_key(sid) == f"cms-section-{sid}"


def test_ensure_site_route_page_find_or_create():
    store: dict = {"pages": {}, "by_route": {}}

    class FakeCursor:
        def __init__(self):
            self._one = None
            self._query = ""

        def execute(self, query, params=None):
            self._query = " ".join(query.split())
            q = self._query.lower()
            if "where site_route" in q and "select" in q:
                route = params[0]
                self._one = store["by_route"].get(route)
            elif "where slug" in q and "select" in q:
                slug = params[0]
                self._one = store["pages"].get(slug)
            elif q.startswith("insert into cms_pages"):
                page_id, slug, title, _meta, site_route = params
                row = {
                    "id": page_id,
                    "slug": slug,
                    "title": title,
                    "meta_description": "",
                    "status": "published",
                    "site_route": site_route,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
                store["pages"][slug] = row
                store["by_route"][site_route] = row
                self._one = row
            elif q.startswith("update cms_pages"):
                page_id = params[-1]
                for row in store["pages"].values():
                    if str(row["id"]) == str(page_id):
                        if "status" in q:
                            row["status"] = params[0]
                        self._one = row
                        return
                self._one = None
            else:
                self._one = None

        def fetchone(self):
            return self._one

    cur = FakeCursor()
    page = ensure_site_route_page(cur, "/", "首頁")
    assert page["site_route"] == "/"
    assert page["slug"] == "site-home"
    assert page["status"] == "published"
    assert page["title"] == "首頁"

    again = ensure_site_route_page(cur, "/", "首頁")
    assert again["id"] == page["id"]

    about = ensure_site_route_page(cur, "/about.html", "品牌故事")
    assert about["slug"] == "site-about-html"
    assert about["title"] == "品牌故事"


def test_upsert_section_page_image_writes_slot():
    rows: dict = {}

    class FakeCursor:
        def __init__(self):
            self._one = None

        def execute(self, query, params=None):
            q = " ".join(query.split()).lower()
            if "create table if not exists page_images" in q or q.startswith("alter table"):
                self._one = None
                return
            if "create index" in q or q.startswith("do $$") or q.startswith("delete from page_images"):
                self._one = None
                return
            if "insert into page_images" in q:
                page_key, slot_key, label, slot_label, url, webp, alt, tw, th = params
                row = {
                    "page_key": page_key,
                    "slot_key": slot_key,
                    "label": label,
                    "slot_label": slot_label,
                    "group_key": "cms-section",
                    "image_url": url,
                    "image_webp": webp,
                    "image_alt": alt,
                    "default_image_url": "",
                    "default_image_webp": None,
                    "target_w": tw,
                    "target_h": th,
                    "sort_order": 900,
                    "is_published": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
                rows[(page_key, slot_key)] = row
                self._one = row
                return
            if "update page_images" in q and "is_published = false" in q:
                key = (params[0], params[1])
                row = rows.get(key)
                if row:
                    row["is_published"] = False
                    row["image_url"] = ""
                    row["image_webp"] = None
                self._one = {"page_key": params[0]} if row else None
                return
            if "delete from page_images" in q:
                key = (params[0], params[1])
                existed = key in rows
                rows.pop(key, None)
                self._one = {"page_key": params[0]} if existed else None
                return
            self._one = None

        def fetchone(self):
            return self._one

    cur = FakeCursor()
    section_id = str(uuid4())
    out = upsert_section_page_image(
        cur,
        page_key="/",
        section_id=section_id,
        section_type="image_text",
        image_url="/static/uploads/x.jpg",
        image_alt="圖文",
    )
    assert out is not None
    assert out["slot_key"] == f"cms-section-{section_id}"
    assert out["label"] == "圖文區塊"
    assert out["image_url"] == "/static/uploads/x.jpg"

    section = {
        "id": section_id,
        "type": "hero",
        "props": {**DEFAULT_PROPS["hero"], "image_url": "/static/h.jpg", "image_alt": "Hero"},
    }
    page = {"site_route": "/", "slug": "site-home"}
    synced = sync_section_page_image_from_props(cur, section, page)
    assert synced is not None
    assert synced["label"] == "Hero 區塊"
