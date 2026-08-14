"""Content CMS helpers — FAQ + testimonials + home banners + page images + journal."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

# Match nav 六大系列 order (content/site/templates/partials/nav.html).
TESTIMONIAL_CATEGORIES = (
    "滿月鑽石",
    "寵物鑽石",
    "結髮鑽石",
    "全家福鑽石",
    "生命鑽石",
    "真我鑽石",
)

# Old dropdown labels → current series names.
LEGACY_TESTIMONIAL_CATEGORY_MAP = {
    "初生鑽石": "滿月鑽石",  # /series/first-love/
    "毛髮鑽石": "真我鑽石",  # /series/signature/ (self hair)
}

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


def normalize_testimonial_category(category: str) -> str:
    """Map legacy labels to current 六大系列; leave unknown values unchanged."""
    cat = (category or "").strip()
    return LEGACY_TESTIMONIAL_CATEGORY_MAP.get(cat, cat)


def build_testimonial_role(category: str, city: str, country: str = "") -> str:
    cat = normalize_testimonial_category(category)
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
    from app.image_urls import strip_cache_buster

    body = body or {}
    name_part = str(body.get("name") or body.get("namePart") or "").strip()
    honorific = str(body.get("honorific") or "小姐").strip()
    name = combine_display_name(name_part, honorific)
    category = normalize_testimonial_category(str(body.get("category") or ""))
    city = str(body.get("city") or "").strip().replace("臺", "台")
    country = str(body.get("country") or "").strip()
    text = str(body.get("text") or "").strip()
    image_url = strip_cache_buster(body.get("imageUrl") or body.get("image_url"))
    is_published = bool(body.get("isPublished") if body.get("isPublished") is not None else True)

    if city != "其他":
        country = ""

    errors: list[str] = []
    if not name_part:
        errors.append("請填寫姓名")
    if not category:
        errors.append("請選擇分類")
    elif category not in TESTIMONIAL_CATEGORIES:
        errors.append("請選擇有效分類（六大系列）")
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


def remap_legacy_testimonial_categories(cur) -> int:
    """Rewrite legacy category/role labels to current 六大系列. Idempotent."""
    updated = 0
    for old, new in LEGACY_TESTIMONIAL_CATEGORY_MAP.items():
        cur.execute(
            """
            update testimonials
            set category = %s,
                role = regexp_replace(role, %s, %s)
            where category = %s
            """,
            (new, f"^{old}", new, old),
        )
        updated += cur.rowcount or 0
    return updated


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


_TESTIMONIAL_IMG_PREFIX = "/static/images/testimonials/"
# Migrated seed art lives under site-images/… (see scripts/migrate_uploads_to_supabase_storage.py).
# Admin uploads use kind "testimonials" → object key testimonials/{uuid}.webp.
_TESTIMONIAL_SITE_IMAGES_PREFIX = "site-images/testimonials/"


def _prefer_webp_object_key(rel: str) -> str:
    """Admin uploads are stored as WebP via ensure_webp."""
    lower = rel.lower()
    if lower.endswith((".jpg", ".jpeg", ".png")):
        return rel.rsplit(".", 1)[0] + ".webp"
    return rel


def _prefer_site_images_object_key(rel: str) -> str:
    """Migrated seed art in Storage is JPEG (see site-images/testimonials/*)."""
    lower = rel.lower()
    if lower.endswith(".webp"):
        return rel[:-5] + ".jpg"
    if lower.endswith((".jpeg", ".png")):
        return rel.rsplit(".", 1)[0] + ".jpg"
    return rel


def _testimonial_storage_object_path(url: str) -> str | None:
    """Map local /static testimonial paths → Storage object key (no network)."""
    from app.storage import local_upload_to_object_key

    mapped = local_upload_to_object_key(url)
    if mapped:
        kind, rest = mapped
        return f"{kind}/{_prefer_webp_object_key(rest)}"
    path = url.replace("\\", "/").split("?", 1)[0]
    if path.startswith(_TESTIMONIAL_IMG_PREFIX):
        rel = path[len(_TESTIMONIAL_IMG_PREFIX) :]
    elif path.startswith("static/images/testimonials/"):
        rel = path[len("static/images/testimonials/") :]
    else:
        return None
    rel = rel.lstrip("/")
    if not rel or ".." in rel.split("/"):
        return None
    return f"{_TESTIMONIAL_SITE_IMAGES_PREFIX}{_prefer_site_images_object_key(rel)}"


def _testimonial_public_storage_url(object_path: str) -> str | None:
    """Build absolute Storage public URL from SUPABASE_URL + bucket (no secrets)."""
    from config.settings import settings

    base = (settings.supabase_url or "").rstrip("/")
    bucket = (settings.supabase_storage_bucket or "shop-media").strip() or "shop-media"
    path = (object_path or "").strip().lstrip("/")
    if not base or not path:
        return None
    return f"{base}/storage/v1/object/public/{bucket}/{path}"


def normalize_testimonial_image_url(url: str | None) -> str:
    """Return a browser-loadable testimonial image URL for localhost + prod.

    - Absolute Supabase Storage public URLs pass through unchanged.
    - /static/uploads/testimonials/* → shop-media/testimonials/* (admin uploads).
    - /static/images/testimonials/* → shop-media/site-images/testimonials/*
      (migrated seed art; same mapping as migrate_uploads_to_supabase_storage).
    Never rewrite a Supabase URL back to /static/.
    """
    u = (url or "").strip()
    if not u:
        return u
    if u.startswith("https://") and (
        ".supabase.co/" in u or "/storage/v1/object/public/" in u
    ):
        return u
    object_path = _testimonial_storage_object_path(u)
    if object_path:
        absolute = _testimonial_public_storage_url(object_path)
        if absolute:
            return absolute
    return u


def classify_testimonial_image_url(url: str | None) -> str:
    """Bucket for diagnostics: supabase | static | empty | other (no secrets)."""
    u = (url or "").strip()
    if not u:
        return "empty"
    if u.startswith("https://") and ".supabase.co/" in u:
        return "supabase"
    if u.startswith(_TESTIMONIAL_IMG_PREFIX) or u.startswith("/static/"):
        return "static"
    return "other"


def summarize_testimonial_image_urls(rows: list[dict]) -> dict[str, int]:
    """Count image_url origins across testimonial rows (safe for logs)."""
    counts = {"total": 0, "supabase": 0, "static": 0, "empty": 0, "other": 0}
    for row in rows:
        counts["total"] += 1
        key = classify_testimonial_image_url(row.get("image_url"))
        counts[key] = counts.get(key, 0) + 1
    return counts


def serialize_testimonial(row: dict) -> dict:
    from app.image_urls import with_cache_buster

    out = dict(row)
    if out.get("image_url"):
        out["image_url"] = with_cache_buster(
            normalize_testimonial_image_url(out["image_url"]), out.get("updated_at")
        )
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
    # Public display always uses 六大系列 — even if DB row still has legacy label.
    out["category"] = normalize_testimonial_category(out.get("category") or "")
    out["role"] = build_testimonial_role(
        out["category"],
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


def _apply_limit_offset(
    sql: str,
    params: list[Any] | None,
    *,
    limit: int | None,
    offset: int = 0,
) -> tuple[str, list[Any] | None]:
    """Append SQL LIMIT/OFFSET when limit is set; otherwise leave query unchanged."""
    if limit is None:
        return sql, params
    bound = list(params or [])
    bound.extend([max(0, int(limit)), max(0, int(offset))])
    return sql + " limit %s offset %s", bound


def count_published_testimonials(cur) -> int:
    from app.paging import sql_count_total

    return sql_count_total(
        cur,
        "select count(*)::int as n from testimonials where is_published = true",
    )


def fetch_published_testimonials(
    cur,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    sql = """
        select * from testimonials
        where is_published = true
        order by sort_order asc, created_at asc
    """
    sql, params = _apply_limit_offset(sql, None, limit=limit, offset=offset)
    cur.execute(sql, params)
    return [serialize_testimonial(r) for r in cur.fetchall()]


def count_all_testimonials(cur) -> int:
    cur.execute("select count(*)::int as n from testimonials")
    row = cur.fetchone() or {}
    return int(row.get("n") or 0)


def fetch_all_testimonials(
    cur,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    sql = "select * from testimonials order by sort_order asc, created_at asc"
    sql, params = _apply_limit_offset(sql, None, limit=limit, offset=offset)
    cur.execute(sql, params)
    return [serialize_testimonial(r) for r in cur.fetchall()]


def ensure_journal_posts_schema(cur) -> None:
    """Create the journal storage used by both public SSR and admin posts."""
    cur.execute(
        """
        create table if not exists journal_posts (
          id uuid primary key default gen_random_uuid(),
          title text not null,
          body text not null default '',
          posted_at date not null,
          image_url text,
          is_archived boolean not null default false,
          is_published boolean not null default true,
          sort_order int not null default 0,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    cur.execute(
        """
        create index if not exists journal_posts_published_posted_idx
          on journal_posts (is_published, posted_at desc, sort_order)
        """
    )


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


JOURNAL_BODY_PREVIEW_CHARS = 120


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


def serialize_journal_post_list(row: dict) -> dict:
    """Admin list row: body_preview only, never full body."""
    src = dict(row)
    body = src.pop("body", None)
    preview = src.get("body_preview")
    if preview is None and body is not None:
        preview = str(body)[:JOURNAL_BODY_PREVIEW_CHARS]
    out = serialize_journal_post(src)
    out.pop("body", None)
    out["body_preview"] = str(preview or "")[:JOURNAL_BODY_PREVIEW_CHARS]
    return out


def count_published_journal_posts(cur) -> int:
    from app.paging import sql_count_total

    return sql_count_total(
        cur,
        "select count(*)::int as n from journal_posts where is_published = true",
    )


def fetch_published_journal_posts(
    cur,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    sql = """
        select * from journal_posts
        where is_published = true
        order by posted_at desc, sort_order asc, created_at desc
    """
    sql, params = _apply_limit_offset(sql, None, limit=limit, offset=offset)
    cur.execute(sql, params)
    return [serialize_journal_post(r) for r in cur.fetchall()]


def fetch_published_journal_post(cur, post_id) -> dict | None:
    """Fetch one published journal post for its public detail page."""
    cur.execute(
        """
        select * from journal_posts
        where id = %s and is_published = true
        limit 1
        """,
        (post_id,),
    )
    row = cur.fetchone()
    return serialize_journal_post(row) if row else None


def count_all_journal_posts(cur) -> int:
    cur.execute("select count(*)::int as n from journal_posts")
    row = cur.fetchone() or {}
    return int(row.get("n") or 0)


def fetch_all_journal_posts(
    cur,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Admin list: omit full body; expose body_preview only."""
    sql = f"""
        select
          id, title,
          left(coalesce(body, ''), {JOURNAL_BODY_PREVIEW_CHARS}) as body_preview,
          posted_at, image_url, is_archived, is_published, sort_order,
          created_at, updated_at
        from journal_posts
        order by posted_at desc, sort_order asc, created_at desc
    """
    sql, params = _apply_limit_offset(sql, None, limit=limit, offset=offset)
    cur.execute(sql, params)
    return [serialize_journal_post_list(r) for r in cur.fetchall()]


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


FAQ_PUBLIC_ITEM_LIMIT = 200


def fetch_faq_public(cur) -> dict[str, Any]:
    cur.execute("select * from faq_categories order by sort_order asc, id asc")
    categories = [serialize_faq_category(r) for r in cur.fetchall()]
    cur.execute(
        """
        select * from faq_items
        where is_published = true
        order by sort_order asc, id asc
        limit %s
        """,
        (FAQ_PUBLIC_ITEM_LIMIT,),
    )
    items = [serialize_faq_item(r) for r in cur.fetchall()]
    return _faq_public_payload(categories, items)


def faq_public_from_seed() -> dict[str, Any]:
    """Build FAQ payload from content-seed.json (seed tooling only; not live SSR)."""
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


def count_faq_items(cur) -> int:
    cur.execute("select count(*)::int as n from faq_items")
    row = cur.fetchone() or {}
    return int(row.get("n") or 0)


def fetch_faq_admin(
    cur,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    cur.execute("select * from faq_categories order by sort_order asc, id asc")
    categories = [serialize_faq_category(r) for r in cur.fetchall()]
    sql = "select * from faq_items order by sort_order asc, id asc"
    sql, params = _apply_limit_offset(sql, None, limit=limit, offset=offset)
    cur.execute(sql, params)
    items = [serialize_faq_item(r) for r in cur.fetchall()]
    return {"categories": categories, "items": items}


def new_faq_id(prefix: str = "faq") -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def serialize_banner(row: dict) -> dict:
    from app.image_urls import with_cache_buster

    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    for key in ("image_url", "image_url_mobile", "image_webp"):
        if out.get(key):
            out[key] = with_cache_buster(out[key], out.get("updated_at"))
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    if "is_published" in out:
        out["is_published"] = bool(out["is_published"])
    if out.get("sort_order") is not None:
        out["sort_order"] = int(out["sort_order"])
    # Legacy rows / partial selects: fall back to single tone for all three.
    tone = str(out.get("tone") or "white").strip() or "white"
    for key in ("eyebrow_color", "title_color", "lead_color"):
        val = str(out.get(key) or "").strip()
        out[key] = val or tone
    return out


def serialize_banner_list(row: dict) -> dict:
    """Admin list: URLs + titles; omit per-field color blobs (tone kept)."""
    out = serialize_banner(row)
    for key in ("eyebrow_color", "title_color", "lead_color"):
        out.pop(key, None)
    return out


BANNERS_PUBLIC_LIMIT = 20


def fetch_published_banners(
    cur,
    *,
    limit: int = BANNERS_PUBLIC_LIMIT,
) -> list[dict]:
    cap = max(1, int(limit))
    cur.execute(
        """
        select * from home_banners
        where is_published = true
        order by sort_order asc, created_at asc
        limit %s
        """,
        (cap,),
    )
    return [serialize_banner(r) for r in cur.fetchall()]


def count_all_banners(cur) -> int:
    cur.execute("select count(*)::int as n from home_banners")
    row = cur.fetchone() or {}
    return int(row.get("n") or 0)


def fetch_all_banners(
    cur,
    *,
    limit: int | None = None,
    offset: int = 0,
    slim: bool = True,
) -> list[dict]:
    sql = "select * from home_banners order by sort_order asc, created_at asc"
    sql, params = _apply_limit_offset(sql, None, limit=limit, offset=offset)
    cur.execute(sql, params)
    rows = cur.fetchall()
    if slim:
        return [serialize_banner_list(r) for r in rows]
    return [serialize_banner(r) for r in rows]


def ensure_banner_mobile_column(cur) -> None:
    """Idempotent: add image_url_mobile to home_banners if it doesn't exist yet."""
    cur.execute(
        "alter table home_banners add column if not exists image_url_mobile text not null default ''"
    )


def ensure_banner_align_column(cur) -> None:
    """Idempotent: add the per-banner desktop copy alignment setting."""
    cur.execute(
        """
        select exists (
          select 1 from information_schema.columns
          where table_name = 'home_banners' and column_name = 'align'
        ) as present
        """
    )
    had_column = bool((cur.fetchone() or {}).get("present"))
    cur.execute(
        "alter table home_banners add column if not exists align text not null default 'left'"
    )
    cur.execute(
        "update home_banners set align = 'left' where align is null or align not in ('left', 'right')"
    )
    if not had_column:
        cur.execute(
            "update home_banners set align = 'right' where sort_order = 3 and align = 'left'"
        )


def ensure_banner_text_color_columns(cur) -> None:
    """Idempotent: per-role text colors; backfill from legacy tone once."""
    cur.execute(
        """
        select exists (
          select 1 from information_schema.columns
          where table_name = 'home_banners' and column_name = 'eyebrow_color'
        ) as present
        """
    )
    had_column = bool((cur.fetchone() or {}).get("present"))
    cur.execute(
        "alter table home_banners add column if not exists eyebrow_color text not null default 'white'"
    )
    cur.execute(
        "alter table home_banners add column if not exists title_color text not null default 'white'"
    )
    cur.execute(
        "alter table home_banners add column if not exists lead_color text not null default 'white'"
    )
    if not had_column:
        cur.execute(
            """
            update home_banners
            set
              eyebrow_color = coalesce(nullif(trim(tone), ''), 'white'),
              title_color = coalesce(nullif(trim(tone), ''), 'white'),
              lead_color = coalesce(nullif(trim(tone), ''), 'white')
            """
        )


_TESTIMONIAL_COUNTRY_READY = False


def ensure_testimonial_country_column(cur) -> None:
    """Idempotent ALTER — once per process (startup lifespan / first write)."""
    global _TESTIMONIAL_COUNTRY_READY
    if _TESTIMONIAL_COUNTRY_READY:
        return
    cur.execute(
        "alter table testimonials add column if not exists country text not null default ''"
    )
    _TESTIMONIAL_COUNTRY_READY = True


def _sync_page_image_labels_from_registry(cur) -> None:
    """Push SlotSpec page_label / slot_label into existing page_images rows."""
    from app.page_image_slots import page_image_slot_specs

    for spec in page_image_slot_specs():
        cur.execute(
            """
            update page_images
            set label = %s,
                slot_label = %s
            where page_key = %s
              and slot_key = %s
              and (label is distinct from %s or slot_label is distinct from %s)
            """,
            (
                spec.page_label,
                spec.slot_label,
                spec.page_key,
                spec.slot_key,
                spec.page_label,
                spec.slot_label,
            ),
        )


_PAGE_IMAGES_SCHEMA_READY = False


def ensure_page_images_schema(cur) -> None:
    """CREATE/ALTER/label-sync — once per process (not on every list GET)."""
    global _PAGE_IMAGES_SCHEMA_READY
    if _PAGE_IMAGES_SCHEMA_READY:
        return
    _ensure_page_images_schema_impl(cur)
    _PAGE_IMAGES_SCHEMA_READY = True


def _ensure_page_images_schema_impl(cur) -> None:
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
    # Keep admin labels in sync with code registry (e.g. 真我→銘印 rename).
    _sync_page_image_labels_from_registry(cur)
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
    ensure_page_images_previous_columns(cur)


def ensure_page_images_previous_columns(cur) -> None:
    """Add page_images.previous_image_url / previous_image_webp if missing."""
    cur.execute(
        "alter table page_images "
        "add column if not exists previous_image_url text"
    )
    cur.execute(
        "alter table page_images "
        "add column if not exists previous_image_webp text"
    )


def _is_page_images_storage_url(url: str | None) -> bool:
    """True for Supabase Storage objects under page-images/ (not .keep)."""
    from app.storage import is_supabase_storage_url, object_path_from_public_url

    if not url or not is_supabase_storage_url(url):
        return False
    raw = str(url).strip()
    if "/static/" in raw:
        return False
    obj = object_path_from_public_url(raw)
    if not obj or not obj.startswith("page-images/"):
        return False
    name = obj.rsplit("/", 1)[-1]
    return name != ".keep"


def delete_page_image_urls_if_unreferenced(cur, urls) -> int:
    """Delete page-images Storage objects when no page_images row references them.

    Live refs: image_url, image_webp, default_image_url, default_image_webp,
    previous_image_url, previous_image_webp. Only Supabase URLs under
    page-images/ (skips .keep and /static/). Dedupes. Best-effort: Storage
    failures do not raise. Returns how many delete_by_url calls reported success.
    """
    from app.storage import delete_by_url

    candidates: list[str] = []
    seen: set[str] = set()
    for raw in urls or []:
        url = str(raw or "").strip()
        if not url or url in seen or not _is_page_images_storage_url(url):
            continue
        seen.add(url)
        candidates.append(url)

    if not candidates:
        return 0

    ensure_page_images_previous_columns(cur)
    deleted = 0
    for url in candidates:
        cur.execute(
            """
            select 1 from page_images
            where image_url = %s
               or image_webp = %s
               or default_image_url = %s
               or default_image_webp = %s
               or previous_image_url = %s
               or previous_image_webp = %s
            limit 1
            """,
            (url, url, url, url, url, url),
        )
        if cur.fetchone():
            continue
        try:
            if delete_by_url(url):
                deleted += 1
        except Exception:
            continue
    return deleted


def _page_img_str(val: Any) -> str:
    return str(val or "").strip()


def reset_page_image_row(cur, existing: dict) -> dict:
    """Clear previous; set current to defaults; GC custom Storage URLs."""
    ensure_page_images_previous_columns(cur)
    page_key = existing["page_key"]
    slot_key = existing["slot_key"]
    default_url = _page_img_str(existing.get("default_image_url"))
    default_webp = _page_img_str(existing.get("default_image_webp")) or None
    gc = [
        u
        for u in (
            _page_img_str(existing.get("image_url")),
            _page_img_str(existing.get("image_webp")),
            _page_img_str(existing.get("previous_image_url")),
            _page_img_str(existing.get("previous_image_webp")),
        )
        if u and u != default_url and u != default_webp
    ]
    cur.execute(
        """
        update page_images
        set image_url = default_image_url,
            image_webp = default_image_webp,
            previous_image_url = null,
            previous_image_webp = null,
            is_published = true,
            updated_at = now()
        where page_key = %s and slot_key = %s
        returning *
        """,
        (page_key, slot_key),
    )
    row = cur.fetchone()
    delete_page_image_urls_if_unreferenced(cur, gc)
    return row


def restore_page_image_row(cur, existing: dict) -> tuple[dict | None, str | None]:
    """Swap previous_* back to current; GC discarded current when unreferenced."""
    ensure_page_images_previous_columns(cur)
    prev_url = _page_img_str(existing.get("previous_image_url"))
    prev_webp = _page_img_str(existing.get("previous_image_webp")) or None
    if not prev_url:
        return None, "沒有可還原的圖片"
    page_key = existing["page_key"]
    slot_key = existing["slot_key"]
    current_url = _page_img_str(existing.get("image_url"))
    current_webp = _page_img_str(existing.get("image_webp")) or None
    default_url = _page_img_str(existing.get("default_image_url"))
    default_webp = _page_img_str(existing.get("default_image_webp")) or None
    cur.execute(
        """
        update page_images
        set image_url = %s,
            image_webp = %s,
            previous_image_url = null,
            previous_image_webp = null,
            updated_at = now()
        where page_key = %s and slot_key = %s
        returning *
        """,
        (prev_url, prev_webp, page_key, slot_key),
    )
    row = cur.fetchone()
    gc = []
    if current_url and current_url != prev_url and current_url != default_url:
        gc.append(current_url)
    if current_webp and current_webp != prev_webp and current_webp != default_webp:
        gc.append(current_webp)
    delete_page_image_urls_if_unreferenced(cur, gc)
    return row, None


def apply_page_image_replace_stack(
    cur,
    existing: dict,
    *,
    new_url: str,
    new_webp: str | None,
    image_alt: str,
    is_published: bool,
    webp_provided: bool,
) -> dict:
    """Update current image with one-deep previous stack; GC older previous."""
    ensure_page_images_previous_columns(cur)
    page_key = existing["page_key"]
    slot_key = existing["slot_key"]
    old_url = _page_img_str(existing.get("image_url"))
    old_webp = _page_img_str(existing.get("image_webp")) or None
    old_prev_url = _page_img_str(existing.get("previous_image_url")) or None
    old_prev_webp = _page_img_str(existing.get("previous_image_webp")) or None
    default_url = _page_img_str(existing.get("default_image_url"))
    default_webp = _page_img_str(existing.get("default_image_webp")) or None

    url = _page_img_str(new_url)
    webp = (_page_img_str(new_webp) or None) if webp_provided else old_webp
    url_changed = url != old_url
    webp_changed = webp_provided and webp != old_webp

    if not url_changed and not webp_changed:
        cur.execute(
            """
            update page_images
            set image_alt = %s, is_published = %s, updated_at = now()
            where page_key = %s and slot_key = %s
            returning *
            """,
            (image_alt, is_published, page_key, slot_key),
        )
        return cur.fetchone()

    # New URL equals site default → reset path (never stack defaults).
    if url == default_url and webp == default_webp:
        return reset_page_image_row(cur, existing)

    if not url_changed and webp_changed:
        cur.execute(
            """
            update page_images
            set image_webp = %s,
                image_alt = %s,
                is_published = %s,
                updated_at = now()
            where page_key = %s and slot_key = %s
            returning *
            """,
            (webp, image_alt, is_published, page_key, slot_key),
        )
        row = cur.fetchone()
        if old_webp and old_webp != webp and old_webp != default_webp:
            delete_page_image_urls_if_unreferenced(cur, [old_webp])
        return row

    # A→B: previous=A; B→C: GC A, previous=B. Never stash defaults as previous.
    if old_url and old_url != url and old_url != default_url:
        next_prev_url = old_url
        next_prev_webp = old_webp if old_webp and old_webp != default_webp else None
    else:
        next_prev_url = None
        next_prev_webp = None

    cur.execute(
        """
        update page_images
        set image_url = %s,
            image_webp = %s,
            image_alt = %s,
            is_published = %s,
            previous_image_url = %s,
            previous_image_webp = %s,
            updated_at = now()
        where page_key = %s and slot_key = %s
        returning *
        """,
        (
            url,
            webp,
            image_alt,
            is_published,
            next_prev_url,
            next_prev_webp,
            page_key,
            slot_key,
        ),
    )
    row = cur.fetchone()
    gc = [
        u
        for u in (old_prev_url, old_prev_webp)
        if u
        and u != url
        and u != webp
        and u != next_prev_url
        and u != next_prev_webp
        and u != default_url
        and u != default_webp
    ]
    delete_page_image_urls_if_unreferenced(cur, gc)
    return row


def serialize_page_image(row: dict) -> dict:
    from app.image_urls import with_cache_buster

    out = dict(row)
    # Prefer live registry labels so renames show in admin without reseed.
    try:
        from app.page_image_slots import page_image_slot_specs

        specs = getattr(serialize_page_image, "_spec_labels", None)
        if specs is None:
            specs = {
                (spec.page_key, spec.slot_key): (spec.page_label, spec.slot_label)
                for spec in page_image_slot_specs()
            }
            serialize_page_image._spec_labels = specs  # type: ignore[attr-defined]
        labels = specs.get((str(out.get("page_key") or ""), str(out.get("slot_key") or "hero")))
        if labels:
            out["label"], out["slot_label"] = labels
    except Exception:
        pass
    for key in ("created_at", "updated_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    if "is_published" in out:
        out["is_published"] = bool(out["is_published"])
    for key in ("target_w", "target_h", "sort_order"):
        if out.get(key) is not None:
            out[key] = int(out[key])
    # Defaults ship with the deploy; only admin-set URLs need the ?v= buster.
    stamp = out.get("updated_at")
    display_url = effective_page_image_url(out)
    display_webp = effective_page_image_webp(out)
    default_url = str(out.get("default_image_url") or "").strip()
    default_webp = str(out.get("default_image_webp") or "").strip()
    raw_image_url = str(out.get("image_url") or "").strip()
    out["display_url"] = (
        display_url if display_url == default_url else with_cache_buster(display_url, stamp)
    )
    out["display_webp"] = (
        display_webp if display_webp == default_webp else with_cache_buster(display_webp, stamp)
    )
    # Admin thumbs ignore publish: show uploaded asset even when unpublished.
    admin_src = raw_image_url or display_url or default_url
    out["admin_preview_url"] = (
        admin_src
        if (not admin_src or admin_src == default_url)
        else with_cache_buster(admin_src, stamp)
    )
    prev_url = _page_img_str(out.get("previous_image_url")) or None
    prev_webp = _page_img_str(out.get("previous_image_webp")) or None
    out["previous_image_url"] = prev_url
    out["previous_image_webp"] = prev_webp
    out["previousImageUrl"] = prev_url
    out["previousImageWebp"] = prev_webp
    return out


def serialize_page_image_list(row: dict) -> dict:
    """Admin list: display URLs + labels; no previous_* or default blobs."""
    out = serialize_page_image(row)
    for key in (
        "previous_image_url",
        "previous_image_webp",
        "previousImageUrl",
        "previousImageWebp",
        "default_image_url",
        "default_image_webp",
    ):
        out.pop(key, None)
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


_PAGE_IMAGES_ADMIN_WHERE = """
    page_key not like %s
      and page_key not like %s
      and page_key <> %s
      and coalesce(group_key, '') <> %s
"""
_PAGE_IMAGES_ADMIN_PARAMS = ("/shop/%", "/jewelry/%", "/jewelry/", "jewelry")


def count_all_page_images(cur, *, page_key: str | None = None) -> int:
    sql = f"select count(*)::int as n from page_images where {_PAGE_IMAGES_ADMIN_WHERE}"
    params: list[Any] = list(_PAGE_IMAGES_ADMIN_PARAMS)
    if page_key:
        sql += " and page_key = %s"
        params.append(page_key)
    cur.execute(sql, params)
    row = cur.fetchone() or {}
    return int(row.get("n") or 0)


def fetch_all_page_images(
    cur,
    *,
    limit: int | None = None,
    offset: int = 0,
    page_key: str | None = None,
    slim: bool = True,
) -> list[dict]:
    """Admin list: content-page slots only (no shop/calculator or jewelry).

    Includes empty placeholder slots (e.g. DNA 實驗室照片) so they can be uploaded later.
    """
    sql = f"""
        select * from page_images
        where {_PAGE_IMAGES_ADMIN_WHERE}
    """
    params: list[Any] = list(_PAGE_IMAGES_ADMIN_PARAMS)
    if page_key:
        sql += " and page_key = %s"
        params.append(page_key)
    sql += " order by group_key asc, sort_order asc, page_key asc, slot_key asc"
    sql, params = _apply_limit_offset(sql, params, limit=limit, offset=offset)
    cur.execute(sql, params)
    rows = cur.fetchall()
    if slim:
        return [serialize_page_image_list(r) for r in rows]
    return [serialize_page_image(r) for r in rows]


def fetch_page_image_keys(cur) -> list[dict]:
    """Distinct page_key + label for admin filter chips (not full rows)."""
    from app.page_image_slots import page_image_slot_specs

    label_by_key: dict[str, str] = {}
    for spec in page_image_slot_specs():
        label_by_key.setdefault(spec.page_key, spec.page_label)

    sql = f"""
        select distinct page_key, label
        from page_images
        where {_PAGE_IMAGES_ADMIN_WHERE}
        order by page_key asc
    """
    cur.execute(sql, list(_PAGE_IMAGES_ADMIN_PARAMS))
    seen: set[str] = set()
    out: list[dict] = []
    for row in cur.fetchall():
        key = str(row.get("page_key") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "page_key": key,
                "label": label_by_key.get(key) or str(row.get("label") or key),
            }
        )
    for key, label in label_by_key.items():
        if key in seen:
            continue
        if key.startswith("/shop/") or key.startswith("/jewelry"):
            continue
        seen.add(key)
        out.append({"page_key": key, "label": label})
    out.sort(key=lambda item: item["page_key"])
    return out


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


def get_page_image_row(cur, page_key: str, slot_key: str = "hero") -> dict | None:
    """Raw page_images row via page_key_aliases (slash / *.html)."""
    from app.cms_boundary import page_key_aliases

    for key in page_key_aliases(page_key):
        cur.execute(
            "select * from page_images where page_key = %s and slot_key = %s",
            (key, slot_key),
        )
        row = cur.fetchone()
        if row:
            return row
    return None


def fetch_page_image(cur, page_key: str, slot_key: str = "hero") -> dict | None:
    """Backward-compatible single-slot lookup."""
    row = get_page_image_row(cur, page_key, slot_key)
    return serialize_page_image(row) if row else None


def parse_page_image_payload(body: dict | None) -> tuple[dict | None, str | None]:
    from app.cms_boundary import assert_content_page_key
    from app.image_urls import strip_cache_buster

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

    image_url = strip_cache_buster(body.get("imageUrl") or body.get("image_url"))
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
        cleaned["image_webp"] = strip_cache_buster(image_webp_raw) or None
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


def _page_image_registry_entry(page_key: str, slot_key: str) -> dict | None:
    """Seed row, or SlotSpec fallback, matching page_key_aliases."""
    from app.cms_boundary import page_key_aliases
    from app.page_image_slots import build_page_image_seed, page_image_slot_specs

    aliases = set(page_key_aliases(page_key))
    for row in build_page_image_seed():
        if row["page_key"] in aliases and row["slot_key"] == slot_key:
            return row
    for order, spec in enumerate(page_image_slot_specs(), 1):
        if spec.page_key in aliases and spec.slot_key == slot_key:
            return {
                "page_key": spec.page_key,
                "slot_key": spec.slot_key,
                "label": spec.page_label,
                "slot_label": spec.slot_label,
                "group_key": spec.group_key,
                "image_url": spec.default_url or "",
                "image_webp": spec.default_webp or None,
                "image_alt": spec.image_alt or "",
                "default_image_url": spec.default_url or "",
                "default_image_webp": spec.default_webp or None,
                "target_w": spec.target_w,
                "target_h": spec.target_h,
                "sort_order": order,
            }
    return None


def create_page_image_from_registry(
    cur, page_key: str, slot_key: str
) -> tuple[dict | None, str | None]:
    entry = _page_image_registry_entry(page_key, slot_key)
    if not entry or not _is_content_page_image_row(entry):
        return None, "找不到此頁面圖片區塊"
    if get_page_image_row(cur, page_key, slot_key):
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


def ensure_page_image_row(
    cur, page_key: str, slot_key: str
) -> tuple[dict | None, str | None]:
    """Alias lookup; create from registry when the slot is valid but unseeded."""
    existing = get_page_image_row(cur, page_key, slot_key)
    if existing:
        return existing, None
    _created, err = create_page_image_from_registry(cur, page_key, slot_key)
    if err == "此區塊已存在":
        existing = get_page_image_row(cur, page_key, slot_key)
        return (existing, None) if existing else (None, "找不到頁面圖片設定")
    if err:
        return None, "找不到頁面圖片設定" if err == "找不到此頁面圖片區塊" else err
    existing = get_page_image_row(cur, page_key, slot_key)
    if not existing:
        return None, "找不到頁面圖片設定"
    return existing, None


def apply_page_image_to_html(html: str, row: dict | None) -> str:
    """Backward-compatible wrapper for explicit slot rendering."""
    if not html or not row or not row.get("page_key"):
        return html
    from app.page_image_slots import apply_page_image_slots

    return apply_page_image_slots(html, str(row["page_key"]), [row])
