"""Content CMS helpers — FAQ + testimonials + home banners + page images + journal."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

TESTIMONIAL_CATEGORIES = (
    "寵物鑽石",
    "結髮鑽石",
    "生命鑽石",
    "毛髮鑽石",
    "全家福鑽石",
    "初生鑽石",
)

TAIWAN_CITIES = (
    "台北市",
    "新北市",
    "桃園市",
    "台中市",
    "台南市",
    "高雄市",
    "基隆市",
    "新竹市",
    "新竹縣",
    "苗栗縣",
    "彰化縣",
    "南投縣",
    "雲林縣",
    "嘉義市",
    "嘉義縣",
    "屏東縣",
    "宜蘭縣",
    "花蓮縣",
    "台東縣",
    "澎湖縣",
    "金門縣",
    "連江縣",
    "其他",
)


def location_label_for_testimonial(city: str, country: str = "") -> str:
    """Public location: Taiwan city as-is;「其他」shows typed country."""
    cty = (city or "").strip()
    ctry = (country or "").strip()
    if cty == "其他" and ctry:
        return ctry
    return cty


def build_testimonial_role(category: str, city: str, country: str = "") -> str:
    cat = (category or "").strip()
    loc = location_label_for_testimonial(city, country)
    if cat and loc:
        return f"{cat}・{loc}"
    return cat or loc


def split_display_name(full: str) -> tuple[str, str]:
    name = (full or "").strip()
    if name.endswith("先生"):
        return name[:-2].strip(), "先生"
    if name.endswith("小姐"):
        return name[:-2].strip(), "小姐"
    return name, "小姐"


def combine_display_name(name_part: str, honorific: str) -> str:
    part = (name_part or "").strip()
    honor = (honorific or "小姐").strip()
    if honor not in ("先生", "小姐"):
        honor = "小姐"
    if not part:
        return ""
    return f"{part}{honor}"


def parse_testimonial_payload(body: dict | None) -> tuple[dict | None, str | None]:
    body = body or {}
    name_part = str(body.get("name") or body.get("namePart") or "").strip()
    honorific = str(body.get("honorific") or "小姐").strip()
    name = combine_display_name(name_part, honorific)
    category = str(body.get("category") or "").strip()
    city = str(body.get("city") or "").strip().replace("臺", "台")
    country = str(body.get("country") or "").strip()
    text = str(body.get("text") or "").strip()
    image_url = str(body.get("imageUrl") or body.get("image_url") or "").strip()
    is_published = bool(body.get("isPublished") if body.get("isPublished") is not None else True)

    if city != "其他":
        country = ""

    errors: list[str] = []
    if not name_part:
        errors.append("請填寫姓名")
    if not category:
        errors.append("請選擇分類")
    if not city:
        errors.append("請選擇城市")
    elif city not in TAIWAN_CITIES:
        errors.append("請從清單選擇城市（縣市）")
    if city == "其他" and not country:
        errors.append("請填寫國家 / 地區")
    if len(country) > 40:
        errors.append("國家 / 地區過長")
    if not text:
        errors.append("請填寫見證內容")
    if not image_url:
        errors.append("請上傳圖片")
    if errors:
        return None, "；".join(errors)

    cleaned = {
        "name": name,
        "role": build_testimonial_role(category, city, country),
        "category": category,
        "city": city,
        "country": country,
        "text": text,
        "image_url": image_url,
        "rating": 5,
        "is_published": is_published,
    }
    if body.get("sortOrder") not in (None, ""):
        try:
            cleaned["sort_order"] = max(0, int(body.get("sortOrder")))
        except (TypeError, ValueError):
            return None, "排序無效"
    return cleaned, None


def next_testimonial_sort_order(cur) -> int:
    cur.execute("select coalesce(max(sort_order), -1) + 1 as next from testimonials")
    return int(cur.fetchone()["next"])


def renormalize_testimonial_sort(cur) -> None:
    cur.execute("select id from testimonials order by sort_order asc, created_at asc")
    for index, row in enumerate(cur.fetchall()):
        cur.execute(
            "update testimonials set sort_order = %s where id = %s",
            (index, row["id"]),
        )


def apply_testimonial_sort_order(cur, testimonial_id: str, target_order: int) -> None:
    """Insert/move to target_order (0-based); shift others down (順延)."""
    target_order = max(0, int(target_order))
    cur.execute("select sort_order from testimonials where id = %s", (testimonial_id,))
    row = cur.fetchone()
    if not row:
        return
    cur.execute(
        """
        update testimonials
        set sort_order = sort_order + 1
        where sort_order >= %s and id != %s
        """,
        (target_order, testimonial_id),
    )
    cur.execute(
        "update testimonials set sort_order = %s where id = %s",
        (target_order, testimonial_id),
    )
    renormalize_testimonial_sort(cur)


def move_testimonial(cur, testimonial_id: str, direction: str) -> bool:
    cur.execute("select id, sort_order from testimonials order by sort_order asc, created_at asc")
    rows = cur.fetchall()
    ids = [str(r["id"]) for r in rows]
    tid = str(testimonial_id)
    if tid not in ids:
        return False
    idx = ids.index(tid)
    if direction == "up" and idx > 0:
        other = rows[idx - 1]
    elif direction == "down" and idx < len(rows) - 1:
        other = rows[idx + 1]
    else:
        return False
    a = rows[idx]
    b = other
    cur.execute("update testimonials set sort_order = %s where id = %s", (b["sort_order"], a["id"]))
    cur.execute("update testimonials set sort_order = %s where id = %s", (a["sort_order"], b["id"]))
    renormalize_testimonial_sort(cur)
    return True


def serialize_testimonial(row: dict) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    if "is_published" in out:
        out["is_published"] = bool(out["is_published"])
    if out.get("rating") is not None:
        out["rating"] = int(out["rating"])
    if out.get("sort_order") is not None:
        out["sort_order"] = int(out["sort_order"])
    if out.get("country") is None:
        out["country"] = ""
    else:
        out["country"] = str(out.get("country") or "").strip()
    out["role"] = build_testimonial_role(
        out.get("category") or "",
        out.get("city") or "",
        out.get("country") or "",
    )
    name_part, honorific = split_display_name(out.get("name") or "")
    out["name_part"] = name_part
    out["honorific"] = honorific
    return out


def serialize_faq_category(row: dict) -> dict:
    out = dict(row)
    if out.get("sort_order") is not None:
        out["sort_order"] = int(out["sort_order"])
    return out


def serialize_faq_item(row: dict) -> dict:
    out = dict(row)
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    for key in ("is_published", "show_in_teaser"):
        if key in out:
            out[key] = bool(out[key])
    if out.get("sort_order") is not None:
        out["sort_order"] = int(out["sort_order"])
    return out


def fetch_published_testimonials(cur) -> list[dict]:
    cur.execute(
        """
        select * from testimonials
        where is_published = true
        order by sort_order asc, created_at asc
        """
    )
    return [serialize_testimonial(r) for r in cur.fetchall()]


def fetch_all_testimonials(cur) -> list[dict]:
    cur.execute("select * from testimonials order by sort_order asc, created_at asc")
    return [serialize_testimonial(r) for r in cur.fetchall()]


def _parse_posted_at(value: Any) -> tuple[str | None, str | None]:
    raw = str(value or "").strip()
    if not raw:
        return None, "請填寫日期"
    try:
        parsed = date.fromisoformat(raw[:10])
    except ValueError:
        return None, "日期格式無效（YYYY-MM-DD）"
    return parsed.isoformat(), None


def parse_journal_post_payload(body: dict | None) -> tuple[dict | None, str | None]:
    body = body or {}
    title = str(body.get("title") or "").strip()
    body_text = str(body.get("body") or "").strip()
    image_raw = body.get("imageUrl") if "imageUrl" in body else body.get("image_url")
    image_url = str(image_raw or "").strip() or None
    is_archived = bool(
        body.get("isArchived") if body.get("isArchived") is not None
        else body.get("is_archived") if body.get("is_archived") is not None
        else False
    )
    is_published = bool(
        body.get("isPublished") if body.get("isPublished") is not None
        else body.get("is_published") if body.get("is_published") is not None
        else True
    )
    posted_at, date_err = _parse_posted_at(body.get("postedAt") or body.get("posted_at"))
    errors: list[str] = []
    if not title:
        errors.append("請填寫標題")
    if date_err:
        errors.append(date_err)
    if errors:
        return None, "；".join(errors)

    cleaned = {
        "title": title,
        "body": body_text,
        "posted_at": posted_at,
        "image_url": image_url,
        "is_archived": is_archived,
        "is_published": is_published,
    }
    if body.get("sortOrder") not in (None, "") or body.get("sort_order") not in (None, ""):
        raw_sort = body.get("sortOrder") if body.get("sortOrder") not in (None, "") else body.get("sort_order")
        try:
            cleaned["sort_order"] = max(0, int(raw_sort))
        except (TypeError, ValueError):
            return None, "排序無效"
    return cleaned, None


def next_journal_post_sort_order(cur) -> int:
    cur.execute("select coalesce(max(sort_order), -1) + 1 as next from journal_posts")
    return int(cur.fetchone()["next"])


def serialize_journal_post(row: dict) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    posted = out.get("posted_at")
    if isinstance(posted, date) and not isinstance(posted, datetime):
        out["posted_at"] = posted.isoformat()
    elif isinstance(posted, datetime):
        out["posted_at"] = posted.date().isoformat()
    elif posted is not None:
        out["posted_at"] = str(posted)[:10]
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    for key in ("is_archived", "is_published"):
        if key in out:
            out[key] = bool(out[key])
    if out.get("sort_order") is not None:
        out["sort_order"] = int(out["sort_order"])
    if out.get("image_url") == "":
        out["image_url"] = None
    return out


def fetch_published_journal_posts(cur) -> list[dict]:
    cur.execute(
        """
        select * from journal_posts
        where is_published = true
        order by posted_at desc, sort_order asc, created_at desc
        """
    )
    return [serialize_journal_post(r) for r in cur.fetchall()]


def fetch_all_journal_posts(cur) -> list[dict]:
    cur.execute(
        """
        select * from journal_posts
        order by posted_at desc, sort_order asc, created_at desc
        """
    )
    return [serialize_journal_post(r) for r in cur.fetchall()]


def sanitize_faq_plain_text(value: str) -> str:
    """Strip HTML tags from FAQ fields on write (plain text + safe link revive on read)."""
    import re
    from html import unescape

    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]*>", "", text)
    return text.strip()


def format_faq_answer_html(answer: str) -> str:
    """Escape FAQ answer text and revive known public links."""
    from html import escape

    text = escape(sanitize_faq_plain_text(answer or ""))
    # Longer paths first so shorter tokens do not split them.
    for path, label in (
        ("/shop/calculator/", "客製試算頁"),
        ("/what-is-dna-diamond", "什麼是 DNA 鑽石"),
        ("/diamond-comparison", "天然 vs 培育／DNA"),
        ("/lab-grown-diamond", "什麼是培育鑽石"),
        ("/diamond-4c", "鑽石 4C"),
        ("/price", "價格試算・價格總覽"),
    ):
        text = text.replace(path, f'<a href="{path}">{label}</a>')
    text = text.replace(
        "GIA",
        '<a href="https://www.gia.edu/" target="_blank" rel="noopener">GIA</a>',
    )
    text = text.replace(
        "IGI",
        '<a href="https://www.igi.org/" target="_blank" rel="noopener">IGI</a>',
    )
    return text


def _faq_public_payload(categories: list[dict], items: list[dict]) -> dict[str, Any]:
    by_cat: dict[str, list] = {c["id"]: [] for c in categories}
    for item in items:
        by_cat.setdefault(item["category_id"], []).append(item)
    nested = []
    for cat in categories:
        cat_items = by_cat.get(cat["id"]) or []
        if not cat_items:
            continue
        nested.append(
            {
                "id": cat["id"],
                "title": cat["title"],
                "items": [
                    {
                        "id": i["id"],
                        "question": i["question"],
                        "answer": i["answer"],
                        "answer_html": format_faq_answer_html(i.get("answer") or ""),
                    }
                    for i in cat_items
                ],
            }
        )
    teaser = [
        {
            "id": i["id"],
            "question": i["question"],
            "answer": i["answer"],
            "answer_html": format_faq_answer_html(i.get("answer") or ""),
        }
        for i in items
        if i.get("show_in_teaser")
    ]
    return {"categories": nested, "teaser": teaser, "items": items}


def fetch_faq_public(cur) -> dict[str, Any]:
    cur.execute("select * from faq_categories order by sort_order asc, id asc")
    categories = [serialize_faq_category(r) for r in cur.fetchall()]
    cur.execute(
        """
        select * from faq_items
        where is_published = true
        order by sort_order asc, id asc
        """
    )
    items = [serialize_faq_item(r) for r in cur.fetchall()]
    return _faq_public_payload(categories, items)


def faq_public_from_seed() -> dict[str, Any]:
    """Offline fallback when DB has no FAQ rows."""
    seed_path = Path(__file__).resolve().parent / "data" / "content-seed.json"
    try:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"categories": [], "teaser": [], "items": []}
    categories = list(data.get("faq_categories") or [])
    items = []
    for row in data.get("faq_items") or []:
        item = dict(row)
        item.setdefault("is_published", True)
        items.append(item)
    return _faq_public_payload(categories, items)


def fetch_faq_admin(cur) -> dict[str, Any]:
    cur.execute("select * from faq_categories order by sort_order asc, id asc")
    categories = [serialize_faq_category(r) for r in cur.fetchall()]
    cur.execute("select * from faq_items order by sort_order asc, id asc")
    items = [serialize_faq_item(r) for r in cur.fetchall()]
    return {"categories": categories, "items": items}


def new_faq_id(prefix: str = "faq") -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def serialize_banner(row: dict) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    if "is_published" in out:
        out["is_published"] = bool(out["is_published"])
    if out.get("sort_order") is not None:
        out["sort_order"] = int(out["sort_order"])
    return out


def fetch_published_banners(cur) -> list[dict]:
    cur.execute(
        """
        select * from home_banners
        where is_published = true
        order by sort_order asc, created_at asc
        """
    )
    return [serialize_banner(r) for r in cur.fetchall()]


def fetch_all_banners(cur) -> list[dict]:
    cur.execute("select * from home_banners order by sort_order asc, created_at asc")
    return [serialize_banner(r) for r in cur.fetchall()]


def ensure_banner_mobile_column(cur) -> None:
    """Idempotent: add image_url_mobile to home_banners if it doesn't exist yet."""
    cur.execute(
        "alter table home_banners add column if not exists image_url_mobile text not null default ''"
    )


def ensure_testimonial_country_column(cur) -> None:
    """Idempotent: add country for「其他」city free-text region."""
    cur.execute(
        "alter table testimonials add column if not exists country text not null default ''"
    )


def ensure_page_images_schema(cur) -> None:
    cur.execute(
        """
        create table if not exists page_images (
          page_key text not null,
          slot_key text not null default 'hero',
          label text not null,
          slot_label text not null default '主視覺',
          group_key text not null default 'brand',
          image_url text not null default '',
          image_webp text,
          image_alt text not null default '',
          default_image_url text not null default '',
          default_image_webp text,
          target_w int not null,
          target_h int not null,
          sort_order int not null default 0,
          is_published boolean not null default true,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          primary key (page_key, slot_key)
        )
        """
    )
    cur.execute("alter table page_images add column if not exists slot_key text")
    cur.execute("update page_images set slot_key = 'hero' where slot_key is null or btrim(slot_key) = ''")
    cur.execute(
        "update page_images set slot_key = 'cinema' "
        "where page_key in ('/about', '/about.html') and slot_key = 'hero'"
    )
    # Extensionless public URLs: migrate legacy *.html page_key rows when free.
    cur.execute(
        """
        update page_images as p
        set page_key = left(page_key, length(page_key) - 5),
            updated_at = now()
        where page_key like '%%.html'
          and page_key not like '/admin%%'
          and not exists (
            select 1 from page_images x
            where x.page_key = left(p.page_key, length(p.page_key) - 5)
              and x.slot_key = p.slot_key
          )
        """
    )
    cur.execute(
        """
        delete from page_images
        where page_key like '%%.html'
          and page_key not like '/admin%%'
        """
    )
    cur.execute("alter table page_images alter column slot_key set default 'hero'")
    cur.execute("alter table page_images alter column slot_key set not null")
    cur.execute("alter table page_images add column if not exists slot_label text")
    cur.execute("update page_images set slot_label = label where slot_label is null or btrim(slot_label) = ''")
    cur.execute("alter table page_images alter column slot_label set default '主視覺'")
    cur.execute("alter table page_images alter column slot_label set not null")
    cur.execute(
        """
        do $$
        declare current_pk text;
        declare key_count int;
        begin
          select conname, cardinality(conkey) into current_pk, key_count
          from pg_constraint
          where conrelid = 'page_images'::regclass and contype = 'p';
          if current_pk is not null and key_count = 1 then
            execute format('alter table page_images drop constraint %I', current_pk);
            current_pk := null;
          end if;
          if current_pk is null then
            alter table page_images
              add constraint page_images_pkey primary key (page_key, slot_key);
          end if;
        end $$;
        """
    )
    cur.execute(
        """
        create index if not exists page_images_group_sort_idx
          on page_images (group_key, sort_order, page_key, slot_key)
        """
    )
    # Product / calculator imagery lives in 商品上架 — never in this CMS.
    cur.execute(
        """
        delete from page_images
        where page_key like '/shop/%'
           or page_key like '/jewelry/%'
           or page_key = '/jewelry/'
           or group_key = 'jewelry'
        """
    )


def serialize_page_image(row: dict) -> dict:
    out = dict(row)
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    if "is_published" in out:
        out["is_published"] = bool(out["is_published"])
    for key in ("target_w", "target_h", "sort_order"):
        if out.get(key) is not None:
            out[key] = int(out[key])
    out["display_url"] = effective_page_image_url(out)
    out["display_webp"] = effective_page_image_webp(out)
    return out


def effective_page_image_url(row: dict | None) -> str:
    if not row:
        return ""
    if row.get("is_published") is False:
        return str(row.get("default_image_url") or "").strip()
    url = str(row.get("image_url") or "").strip()
    if url:
        return url
    return str(row.get("default_image_url") or "").strip()


def effective_page_image_webp(row: dict | None) -> str:
    if not row:
        return ""
    if row.get("is_published") is False:
        return str(row.get("default_image_webp") or "").strip()
    webp = str(row.get("image_webp") or "").strip()
    if webp:
        return webp
    image_url = str(row.get("image_url") or "").strip()
    default_url = str(row.get("default_image_url") or "").strip()
    if image_url and image_url != default_url:
        return ""
    return str(row.get("default_image_webp") or "").strip()


def fetch_all_page_images(cur) -> list[dict]:
    """Admin list: content-page slots only (no shop/calculator or jewelry).

    Includes empty placeholder slots (e.g. DNA 實驗室照片) so they can be uploaded later.
    """
    cur.execute(
        """
        select * from page_images
        where page_key not like '/shop/%'
          and page_key not like '/jewelry/%'
          and page_key <> '/jewelry/'
          and coalesce(group_key, '') <> 'jewelry'
        order by group_key asc, sort_order asc, page_key asc, slot_key asc
        """
    )
    return [serialize_page_image(r) for r in cur.fetchall()]


def fetch_page_images(cur, page_key: str) -> list[dict]:
    from app.cms_boundary import page_key_aliases

    for key in page_key_aliases(page_key):
        cur.execute(
            "select * from page_images where page_key = %s order by sort_order, slot_key",
            (key,),
        )
        rows = cur.fetchall()
        if rows:
            return [serialize_page_image(r) for r in rows]
    return []


def fetch_page_image(cur, page_key: str, slot_key: str = "hero") -> dict | None:
    """Backward-compatible single-slot lookup."""
    from app.cms_boundary import page_key_aliases

    for key in page_key_aliases(page_key):
        cur.execute(
            "select * from page_images where page_key = %s and slot_key = %s",
            (key, slot_key),
        )
        row = cur.fetchone()
        if row:
            return serialize_page_image(row)
    return None


def parse_page_image_payload(body: dict | None) -> tuple[dict | None, str | None]:
    from app.cms_boundary import assert_content_page_key

    body = body or {}
    page_key, key_err = assert_content_page_key(
        str(body.get("pageKey") or body.get("page_key") or "")
    )
    if key_err:
        return None, key_err
    slot_key = str(body.get("slotKey") or body.get("slot_key") or "").strip()
    if not slot_key:
        return None, "缺少 slot_key"
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", slot_key):
        return None, "slot_key 無效"

    image_url = str(body.get("imageUrl") or body.get("image_url") or "").strip()
    image_webp_raw = body.get("imageWebp") if "imageWebp" in body else body.get("image_webp")
    image_alt = str(body.get("imageAlt") or body.get("image_alt") or "").strip()
    is_published = bool(
        body.get("isPublished") if body.get("isPublished") is not None else body.get("is_published", True)
    )

    cleaned: dict[str, Any] = {
        "page_key": page_key,
        "slot_key": slot_key,
        "image_url": image_url,
        "image_alt": image_alt,
        "is_published": is_published,
    }
    if image_webp_raw is not None:
        cleaned["image_webp"] = str(image_webp_raw or "").strip() or None
    return cleaned, None


def _is_content_page_image_row(row: dict) -> bool:
    from app.cms_boundary import is_reserved_page_key

    page_key = str(row.get("page_key") or "")
    group_key = str(row.get("group_key") or "")
    if is_reserved_page_key(page_key):
        return False
    return group_key != "jewelry"


def fetch_missing_page_image_slots(cur) -> list[dict]:
    """Registry slots not yet present in page_images (content CMS only)."""
    from app.page_image_slots import build_page_image_seed

    cur.execute("select page_key, slot_key from page_images")
    existing = {(r["page_key"], r["slot_key"]) for r in cur.fetchall()}
    missing: list[dict] = []
    for row in build_page_image_seed():
        if not _is_content_page_image_row(row):
            continue
        key = (row["page_key"], row["slot_key"])
        if key in existing:
            continue
        missing.append(
            {
                "page_key": row["page_key"],
                "page_label": row["label"],
                "slot_key": row["slot_key"],
                "slot_label": row["slot_label"],
                "target_w": row["target_w"],
                "target_h": row["target_h"],
            }
        )
    return missing


def create_page_image_from_registry(
    cur, page_key: str, slot_key: str
) -> tuple[dict | None, str | None]:
    from app.page_image_slots import build_page_image_seed

    entry = next(
        (
            row
            for row in build_page_image_seed()
            if row["page_key"] == page_key and row["slot_key"] == slot_key
        ),
        None,
    )
    if not entry or not _is_content_page_image_row(entry):
        return None, "找不到此頁面圖片區塊"
    cur.execute(
        "select page_key from page_images where page_key = %s and slot_key = %s",
        (page_key, slot_key),
    )
    if cur.fetchone():
        return None, "此區塊已存在"
    cur.execute(
        """
        insert into page_images (
          page_key, slot_key, label, slot_label, group_key,
          image_url, image_webp, image_alt,
          default_image_url, default_image_webp,
          target_w, target_h, sort_order, is_published
        ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true)
        returning *
        """,
        (
            entry["page_key"],
            entry["slot_key"],
            entry["label"],
            entry["slot_label"],
            entry["group_key"],
            entry["image_url"],
            entry.get("image_webp"),
            entry.get("image_alt") or "",
            entry["default_image_url"],
            entry.get("default_image_webp"),
            entry["target_w"],
            entry["target_h"],
            entry["sort_order"],
        ),
    )
    return serialize_page_image(cur.fetchone()), None


def apply_page_image_to_html(html: str, row: dict | None) -> str:
    """Backward-compatible wrapper for explicit slot rendering."""
    if not html or not row or not row.get("page_key"):
        return html
    from app.page_image_slots import apply_page_image_slots

    return apply_page_image_slots(html, str(row["page_key"]), [row])
