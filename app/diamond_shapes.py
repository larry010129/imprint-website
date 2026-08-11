"""Diamond cut / shape registry — built-ins + admin-created cuts.

Memorial diamond image slots and shop matrix picker read from this table.
Built-ins (incl. Asscher) seed on ensure; admins can add more via API.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

# Built-in matrix cuts. Asscher is first extension beyond the original ten.
DEFAULT_SHAPES: list[dict[str, Any]] = [
    {"id": "round", "label_zh": "圓形", "label_en": "Round", "sort_order": 0},
    {"id": "marquise", "label_zh": "馬眼型", "label_en": "Marquise", "sort_order": 1},
    {"id": "oval", "label_zh": "橢圓形", "label_en": "Oval", "sort_order": 2},
    {"id": "princess", "label_zh": "公主方", "label_en": "Princess", "sort_order": 3},
    {"id": "trilliant", "label_zh": "三角形", "label_en": "Trilliant", "sort_order": 4},
    {"id": "emerald", "label_zh": "祖母綠形", "label_en": "Emerald", "sort_order": 5},
    {"id": "heart", "label_zh": "心形", "label_en": "Heart", "sort_order": 6},
    {"id": "radiant", "label_zh": "雷地恩形", "label_en": "Radiant", "sort_order": 7},
    {"id": "pear", "label_zh": "梨形", "label_en": "Pear", "sort_order": 8},
    {"id": "cushion", "label_zh": "枕形", "label_en": "Cushion", "sort_order": 9},
    {"id": "asscher", "label_zh": "阿斯切", "label_en": "Asscher", "sort_order": 10},
]

SHAPE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,40}$")
_RESERVED_IDS = frozenset(
    {
        "other",
        "white",
        "yellow",
        "blue",
        "pink",
        "rose",
        "new",
        "custom",
    }
)
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_SHAPE_SELECT = "id, label_zh, label_en, sort_order, is_builtin, created_at"


def builtin_shape_ids() -> frozenset[str]:
    return frozenset(str(s["id"]) for s in DEFAULT_SHAPES)


def is_allowed_shape_id(shape_id: str | None) -> bool:
    """Accept built-in or custom cut slug (not reserved metal/gem/UI tokens)."""
    key = str(shape_id or "").strip().lower()
    if not key or key in _RESERVED_IDS:
        return False
    return bool(SHAPE_ID_RE.match(key))


def ensure_diamond_shapes_schema(cur) -> None:
    """Create diamond_shapes + seed built-ins (Asscher included)."""
    cur.execute(
        """
        create table if not exists diamond_shapes (
          id text primary key,
          label_zh text not null,
          label_en text,
          sort_order int not null default 0,
          is_builtin boolean not null default false,
          created_at timestamptz not null default now()
        )
        """
    )
    for shape in DEFAULT_SHAPES:
        cur.execute(
            """
            insert into diamond_shapes (id, label_zh, label_en, sort_order, is_builtin)
            values (%s, %s, %s, %s, true)
            on conflict (id) do update set
              label_zh = excluded.label_zh,
              label_en = coalesce(diamond_shapes.label_en, excluded.label_en),
              sort_order = excluded.sort_order,
              is_builtin = true
            """,
            (
                shape["id"],
                shape["label_zh"],
                shape.get("label_en"),
                int(shape["sort_order"]),
            ),
        )


def _serialize_row(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "labelZh": row.get("label_zh") or str(row["id"]),
        "labelEn": row.get("label_en") or str(row["id"]),
        "label_zh": row.get("label_zh") or str(row["id"]),
        "label_en": row.get("label_en") or str(row["id"]),
        "sortOrder": int(row.get("sort_order") or 0),
        "sort_order": int(row.get("sort_order") or 0),
        "isBuiltin": bool(row.get("is_builtin")),
        "is_builtin": bool(row.get("is_builtin")),
    }


def fetch_shapes(cur) -> list[dict]:
    ensure_diamond_shapes_schema(cur)
    cur.execute(
        f"select {_SHAPE_SELECT} from diamond_shapes order by sort_order asc, id asc"
    )
    rows = cur.fetchall()
    if rows:
        return [_serialize_row(dict(r)) for r in rows]
    return [
        _serialize_row(
            {
                "id": s["id"],
                "label_zh": s["label_zh"],
                "label_en": s.get("label_en"),
                "sort_order": s["sort_order"],
                "is_builtin": True,
            }
        )
        for s in DEFAULT_SHAPES
    ]


def valid_shape_ids(cur) -> set[str]:
    return {row["id"] for row in fetch_shapes(cur)}


def shape_label_map(cur) -> dict[str, str]:
    return {row["id"]: row["labelZh"] for row in fetch_shapes(cur)}


def matrix_shapes_payload(cur=None, rows: list[dict] | None = None) -> list[dict]:
    """Shop / admin picker rows: {id, labelZh, labelEn}."""
    if rows is None:
        if cur is None:
            rows = [
                _serialize_row(
                    {
                        "id": s["id"],
                        "label_zh": s["label_zh"],
                        "label_en": s.get("label_en"),
                        "sort_order": s["sort_order"],
                        "is_builtin": True,
                    }
                )
                for s in DEFAULT_SHAPES
            ]
        else:
            rows = fetch_shapes(cur)
    return [
        {
            "id": row["id"],
            "labelZh": row["labelZh"],
            "labelEn": row["labelEn"],
        }
        for row in rows
    ]


def make_shape_id(
    *,
    label_zh: str,
    label_en: str | None,
    preferred_id: str | None,
    existing: set[str],
) -> str:
    candidates: list[str] = []
    if preferred_id:
        candidates.append(str(preferred_id).strip().lower())
    if label_en:
        candidates.append(_SLUG_RE.sub("-", label_en.strip().lower()).strip("-"))
    ascii_zh = _SLUG_RE.sub("-", (label_zh or "").lower()).strip("-")
    if ascii_zh:
        candidates.append(ascii_zh)
    for base in candidates:
        if not base or not SHAPE_ID_RE.match(base) or base in _RESERVED_IDS:
            continue
        slug = base[:40]
        if slug not in existing:
            return slug
        for n in range(2, 50):
            cand = f"{slug[:36]}-{n}"
            if cand not in existing and SHAPE_ID_RE.match(cand):
                return cand
    for _ in range(12):
        slug = f"cut-{uuid.uuid4().hex[:8]}"
        if slug not in existing:
            return slug
    raise ValueError("could not generate shape id")


def create_shape(
    cur,
    *,
    label_zh: str,
    label_en: str | None = None,
    shape_id: str | None = None,
) -> tuple[dict | None, str | None]:
    label_zh = (label_zh or "").strip()
    if not label_zh:
        return None, "請填寫切工名稱"
    if len(label_zh) > 50:
        return None, "切工名稱過長"
    label_en = (label_en or "").strip() or None
    if label_en and len(label_en) > 80:
        return None, "英文名稱過長"

    ensure_diamond_shapes_schema(cur)
    existing = valid_shape_ids(cur)
    if shape_id:
        sid = str(shape_id).strip().lower()
        if not is_allowed_shape_id(sid):
            return None, "切工代號格式無效"
        if sid in existing:
            return None, "切工已存在"
    else:
        sid = make_shape_id(
            label_zh=label_zh,
            label_en=label_en,
            preferred_id=None,
            existing=existing,
        )

    cur.execute("select coalesce(max(sort_order), -1) + 1 as next from diamond_shapes")
    sort_order = int(cur.fetchone()["next"])
    cur.execute(
        f"""
        insert into diamond_shapes (id, label_zh, label_en, sort_order, is_builtin)
        values (%s, %s, %s, %s, false)
        returning {_SHAPE_SELECT}
        """,
        (sid, label_zh, label_en or sid.title(), sort_order),
    )
    row = cur.fetchone()
    return _serialize_row(dict(row)), None
