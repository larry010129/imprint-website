"""Content CMS helpers — FAQ + testimonials + home banners."""

from __future__ import annotations

from datetime import datetime
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
)


def build_testimonial_role(category: str, city: str) -> str:
    cat = (category or "").strip()
    cty = (city or "").strip()
    if cat and cty:
        return f"{cat}・{cty}"
    return cat or cty


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
    city = str(body.get("city") or "").strip()
    text = str(body.get("text") or "").strip()
    image_url = str(body.get("imageUrl") or body.get("image_url") or "").strip()
    is_published = bool(body.get("isPublished") if body.get("isPublished") is not None else True)

    errors: list[str] = []
    if not name_part:
        errors.append("請填寫姓名")
    if not category:
        errors.append("請選擇分類")
    if not city:
        errors.append("請選擇城市")
    if not text:
        errors.append("請填寫見證內容")
    if not image_url:
        errors.append("請上傳圖片")
    if errors:
        return None, "；".join(errors)

    cleaned = {
        "name": name,
        "role": build_testimonial_role(category, city),
        "category": category,
        "city": city,
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
    role = (out.get("role") or "").strip()
    if not role:
        out["role"] = build_testimonial_role(out.get("category") or "", out.get("city") or "")
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
                    {"id": i["id"], "question": i["question"], "answer": i["answer"]}
                    for i in cat_items
                ],
            }
        )
    teaser = [
        {"id": i["id"], "question": i["question"], "answer": i["answer"]}
        for i in items
        if i.get("show_in_teaser")
    ]
    return {"categories": nested, "teaser": teaser, "items": items}


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
