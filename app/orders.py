"""Shared order helpers — json snapshot storage + API hydration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.admin_products import CATEGORY_LABELS
from app.image_urls import config_image_url, is_uuid, order_product_id, resolve_product_image_url

_TAIPEI = ZoneInfo("Asia/Taipei")


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def order_summary_from_config(config: dict) -> str:
    if config.get("summaryZh"):
        return str(config["summaryZh"])
    category = config.get("category") or ""
    style = config.get("type") or ""
    return f"{category} {style}".strip() or "訂製品項"


_GOLD_ZH = {"9k": "9K", "14k": "14K", "18k": "18K", "pt950": "PT950", "s925": "925銀"}
_COLOR_ZH = {"white": "白金", "yellow": "黃金", "rose": "玫瑰金"}
_FANCY_ZH = {"yellow": "黃", "pink": "粉", "blue": "藍"}
_SHAPE_ZH = {
    "round": "圓形",
    "marquise": "馬眼型",
    "oval": "橢圓形",
    "princess": "公主方",
    "trilliant": "三角形",
    "emerald": "祖母綠形",
    "heart": "心形",
    "radiant": "雷地恩形",
    "pear": "梨形",
    "cushion": "枕形",
}


def _material_label(gold: Any, color: Any) -> str:
    key = str(gold or "").strip().lower()
    if not key:
        return ""
    g = _GOLD_ZH.get(key, str(gold))
    if key in ("pt950", "s925"):
        return g
    c = _COLOR_ZH.get(str(color or "white").strip().lower(), _COLOR_ZH["white"])
    return f"{g}{c}"


def _carat_label(carat: Any) -> str:
    raw = str(carat or "").strip()
    if not raw:
        return ""
    if raw == "3fen":
        return "3分"
    if raw == "4fen":
        return "4分"
    if raw.endswith(("ct", "mm", "分")):
        return raw
    return f"{raw}ct"


def _diamond_label(config: dict) -> str:
    if str(config.get("category") or "") == "chain":
        return ""
    if config.get("diamondKind") == "fancy":
        fancy = str(config.get("fancyColor") or "").strip().lower()
        color = _FANCY_ZH.get(fancy, fancy)
        return f"彩鑽（{color}）" if color else "彩鑽"
    if config.get("carat") or config.get("diamondKind") == "white":
        return "白鑽"
    return ""


def _size_chain_parts(cfg: dict) -> list[str]:
    parts: list[str] = []
    category = str(cfg.get("category") or "").strip().lower()
    if category == "ring" and cfg.get("ringSize") not in (None, ""):
        parts.append(f"戒圍 {cfg['ringSize']}")
    if cfg.get("lengthCm") not in (None, ""):
        parts.append(f"{cfg['lengthCm']} cm")
    if cfg.get("chainLength") not in (None, "") and category != "chain":
        parts.append(f"鍊長 {cfg['chainLength']} cm")
    if cfg.get("includeChain"):
        chain = _material_label(cfg.get("chainGold"), cfg.get("chainColor")) or "是"
        parts.append(f"搭配鍊條 {chain}")
    return parts


def _engraving_parts(cfg: dict) -> list[str]:
    parts: list[str] = []
    if cfg.get("engravingBand"):
        parts.append(f"戒圈刻字 {cfg['engravingBand']}")
    if cfg.get("engravingRemark"):
        parts.append(f"金屬刻字 {cfg['engravingRemark']}")
    if cfg.get("engravingGirdle"):
        parts.append(f"腰圍刻字 {cfg['engravingGirdle']}")
    return parts


def cart_details_from_config(config: dict | None) -> str:
    """Compact Traditional Chinese line: metal · carat · diamond · size · chain · engraving."""
    cfg = _as_dict(config)
    parts: list[str] = []
    for value in (
        _material_label(cfg.get("gold"), cfg.get("color")),
        _carat_label(cfg.get("carat")),
        _diamond_label(cfg),
    ):
        if value:
            parts.append(value)
    shape = str(cfg.get("diamondShape") or "").strip()
    if shape and shape != "round":
        parts.append(_SHAPE_ZH.get(shape, shape))
    try:
        stones = int(cfg.get("stoneCount") or 0)
    except (TypeError, ValueError):
        stones = 0
    if stones > 1:
        parts.append(f"{stones}顆")
    if str(cfg.get("category") or "") == "earring":
        try:
            qty = int(cfg.get("quantity") or 1)
        except (TypeError, ValueError):
            qty = 1
        if qty >= 1:
            parts.append(f"×{qty}")
    parts.extend(_size_chain_parts(cfg))
    parts.extend(_engraving_parts(cfg))
    return " · ".join(parts)


# Same pipeline admin sets (admin-orders.js STATUS_OPTIONS + cancelled).
ORDER_STATUS_FLOW = (
    "received",
    "order_confirming",
    "deposit_confirmed",
    "dna_lab",
    "in_production",
    "quality_check",
    "shipped",
    "completed",
)

ORDER_STATUS_LABELS_ZH = {
    "received": "已收到申請",
    "order_confirming": "訂單已確認",
    "dna_lab": "DNA 萃取鑑定中",
    "deposit_confirmed": "訂金已確認",
    "in_production": "製作中",
    "quality_check": "品管檢驗中",
    "shipped": "已出貨",
    "completed": "已完成",
    "cancelled": "已取消",
}

ORDER_STATUS_COLORS = {
    "received": "#e0a458",
    "order_confirming": "#e09a6a",
    "dna_lab": "#6c9bd1",
    "deposit_confirmed": "#5bc0de",
    "in_production": "#9cefef",
    "quality_check": "#5ecfcf",
    "shipped": "#9b7fd4",
    "completed": "#4caf7d",
    "cancelled": "#8a817b",
}

_FULFILLMENT_ZH = {"pickup": "門市自取", "delivery": "宅配到府"}


def _stamp_iso(when: datetime | str) -> str:
    if isinstance(when, datetime):
        dt = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return str(when)


def format_status_date(iso: Any) -> str:
    """Format stamp as unpadded M/D in Asia/Taipei; empty if missing/invalid."""
    if iso is None or iso == "":
        return ""
    if isinstance(iso, datetime):
        dt = iso
    else:
        raw = str(iso).strip()
        if not raw:
            return ""
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(_TAIPEI)
    return f"{local.month}/{local.day}"


def merge_status_timestamps(
    existing: Any,
    old_status: str | None,
    new_status: str | None,
    when: datetime | str,
) -> dict[str, str]:
    """Stamp unstamped flow steps from old+1 through new; never overwrite."""
    out: dict[str, str] = {}
    for key, value in _as_dict(existing).items():
        if value is None or value == "":
            continue
        out[str(key)] = _stamp_iso(value) if isinstance(value, datetime) else str(value)

    new_code = (new_status or "").strip().lower()
    if new_code not in ORDER_STATUS_FLOW:
        return out

    new_idx = ORDER_STATUS_FLOW.index(new_code)
    old_code = (old_status or "").strip().lower()
    if old_code in ORDER_STATUS_FLOW:
        start = ORDER_STATUS_FLOW.index(old_code) + 1
    else:
        start = 0
    if start > new_idx:
        start = new_idx

    stamp = _stamp_iso(when)
    for i in range(start, new_idx + 1):
        key = ORDER_STATUS_FLOW[i]
        if key not in out:
            out[key] = stamp
    return out


def order_status_steps(
    status: str | None,
    timestamps: Any = None,
) -> list[dict[str, str]]:
    """Progress steps for member/admin pipeline; empty when cancelled."""
    code = (status or "").strip().lower()
    if code in {"cancelled", "canceled"}:
        return []
    idx = ORDER_STATUS_FLOW.index(code) if code in ORDER_STATUS_FLOW else 0
    stamps = _as_dict(timestamps)
    steps: list[dict[str, str]] = []
    for i, step in enumerate(ORDER_STATUS_FLOW):
        if i < idx:
            state = "complete"
        elif i == idx:
            state = "current"
        else:
            state = "incomplete"
        date = ""
        if state in {"complete", "current"}:
            date = format_status_date(stamps.get(step))
        steps.append(
            {
                "code": step,
                "label": ORDER_STATUS_LABELS_ZH[step],
                "state": state,
                "color": ORDER_STATUS_COLORS[step],
                "date": date,
            }
        )
    return steps


def ensure_order_status_timestamps_column(cur) -> None:
    """Idempotent column + one-shot backfill for existing rows."""
    cur.execute(
        """
        alter table orders
          add column if not exists status_timestamps jsonb not null default '{}'::jsonb
        """
    )
    cur.execute(
        """
        update orders
        set status_timestamps = status_timestamps
          || jsonb_build_object('received', to_jsonb(created_at))
        where not (status_timestamps ? 'received')
        """
    )
    cur.execute(
        """
        update orders
        set status_timestamps = status_timestamps
          || jsonb_build_object(status, to_jsonb(updated_at))
        where status = any(%s)
          and status <> 'received'
          and not (status_timestamps ? status)
        """,
        (list(ORDER_STATUS_FLOW),),
    )


def enrich_member_order(order: dict) -> dict:
    """Attach member-facing labels, details_zh, and status progress steps."""
    if not order:
        return order
    status = (order.get("status") or "").strip().lower()
    order["status"] = status
    order["status_label"] = ORDER_STATUS_LABELS_ZH.get(status, status or "—")
    order["status_cancelled"] = status in {"cancelled", "canceled"}
    stamps = _as_dict(order.get("status_timestamps"))
    order["status_timestamps"] = stamps
    order["status_steps"] = order_status_steps(status, stamps)
    config = _as_dict(order.get("config_json"))
    order["details_zh"] = cart_details_from_config(config)
    method = order.get("fulfillment_method")
    order["fulfillment_label"] = _FULFILLMENT_ZH.get(method or "", method or "—")
    if method == "delivery":
        order["shipping_line"] = " ".join(
            part
            for part in (
                order.get("shipping_city"),
                order.get("shipping_postal"),
                order.get("shipping_address"),
            )
            if part
        )
    else:
        order["shipping_line"] = ""
    name = (
        order.get("product_name")
        or order.get("summary_zh")
        or order.get("summary")
        or "訂製品項"
    )
    order["display_name"] = name
    return order


def track_order_public_row(order: dict) -> dict:
    """Non-PII status DTO for public track-order (phone match stays server-side)."""
    enrich_member_order(order)
    created = order.get("created_at")
    updated = order.get("updated_at")
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    if hasattr(updated, "isoformat"):
        updated = updated.isoformat()
    stamps = order.get("status_timestamps") or {}
    if not isinstance(stamps, dict):
        stamps = {}
    return {
        "order_number": order.get("order_number"),
        "status": order.get("status"),
        "status_label": order.get("status_label"),
        "summary_zh": order.get("summary_zh"),
        "created_at": created,
        "updated_at": updated,
        "status_timestamps": stamps,
        "status_cancelled": bool(order.get("status_cancelled")),
    }


def pack_order_config(config: dict[str, Any]) -> tuple[dict, dict, str | None, str, float | None]:
    """Split shop config into persisted config_json, pricing_json, summary, total."""
    cfg = dict(config)
    pricing = _as_dict(cfg.pop("clientPricing", None))
    if not pricing:
        pricing = _as_dict(cfg.get("clientPricing"))
    summary = order_summary_from_config(cfg)
    total = pricing.get("total")
    product_id = cfg.get("type") if is_uuid(cfg.get("type")) else None
    return cfg, pricing, product_id, summary, total


def hydrate_order(order: dict) -> dict:
    """Expand config_json + pricing_json onto order for legacy API fields."""
    if not order:
        return order

    config = _as_dict(order.get("config_json"))
    pricing = _as_dict(order.get("pricing_json"))
    if not pricing:
        pricing = _as_dict(config.get("clientPricing"))

    if config:
        order.setdefault("category", config.get("category"))
        order.setdefault(
            "product_type",
            config.get("summaryZh") or config.get("type"),
        )
        order.setdefault("carat", config.get("carat"))
        order.setdefault("gold_purity", config.get("gold"))
        order.setdefault("color", config.get("color"))
        order.setdefault("diamond_kind", config.get("diamondKind") or "white")
        order.setdefault("fancy_color", config.get("fancyColor"))
        order.setdefault("stone_count", config.get("stoneCount"))
        order.setdefault("diamond_shape", config.get("diamondShape") or "round")
        order.setdefault("ring_size", config.get("ringSize"))
        order.setdefault("engraving_band", config.get("engravingBand"))
        order.setdefault("engraving_remark", config.get("engravingRemark"))
        order.setdefault("engraving_girdle", config.get("engravingGirdle"))
        order.setdefault("include_chain", bool(config.get("includeChain")))
        order.setdefault("chain_gold", config.get("chainGold"))
        order.setdefault("chain_color", config.get("chainColor"))
        if config.get("category") == "chain":
            order.setdefault("chain_length_cm", config.get("lengthCm"))
        else:
            order.setdefault("chain_length_cm", config.get("chainLength"))
        order.setdefault("series", config.get("series"))
        if not order.get("product_id") and is_uuid(config.get("type")):
            order["product_id"] = str(config["type"])

    if pricing:
        order.setdefault("weight_grams", pricing.get("weightGrams"))
        order.setdefault("diamond_price_twd", pricing.get("diamondPrice"))
        order.setdefault("taijin_price_twd", pricing.get("taijinPrice"))
        order.setdefault("labor_price_twd", pricing.get("laborPrice"))
        order.setdefault("tax_amount_twd", None)
        order.setdefault("total_price", order.get("total_price") or pricing.get("total"))
        order.setdefault("gold_rate_per_gram", pricing.get("goldRatePerGram"))
        order.setdefault("price_source", pricing.get("priceSource") or "client")

    order.setdefault("summary_zh", order.get("summary_zh") or order_summary_from_config(config))
    return order


def attach_order_items(cur, orders: list[dict]) -> None:
    """Load product snapshots from order_items onto order dicts."""
    if not orders:
        return
    ids = [str(o["id"]) for o in orders if o.get("id")]
    if not ids:
        return
    cur.execute(
        """
        select order_id, product_id, config_json, pricing_json, summary_zh
        from order_items
        where order_id = any(%s)
        order by sort_order, created_at
        """,
        (ids,),
    )
    by_order: dict[str, dict] = {}
    for row in cur.fetchall():
        oid = str(row["order_id"])
        if oid not in by_order:
            by_order[oid] = row
    for order in orders:
        item = by_order.get(str(order.get("id")))
        if not item:
            continue
        if item.get("product_id") is not None:
            order["product_id"] = str(item["product_id"])
        if item.get("config_json") is not None:
            order["config_json"] = item["config_json"]
        if item.get("pricing_json") is not None:
            order["pricing_json"] = item["pricing_json"]
        if item.get("summary_zh"):
            order["summary_zh"] = item["summary_zh"]


def attach_order_contacts(cur, orders: list[dict]) -> None:
    if not orders:
        return
    ids = [str(o["id"]) for o in orders if o.get("id")]
    if not ids:
        return
    cur.execute(
        """
        select order_id, customer_name, customer_phone, customer_email
        from order_contacts where order_id = any(%s)
        """,
        (ids,),
    )
    by_order = {str(r["order_id"]): r for r in cur.fetchall()}
    for order in orders:
        row = by_order.get(str(order.get("id")))
        if not row:
            continue
        order["customer_name"] = row["customer_name"]
        order["customer_phone"] = row["customer_phone"]
        order["customer_email"] = row.get("customer_email")


def attach_order_fulfillment(cur, orders: list[dict]) -> None:
    if not orders:
        return
    ids = [str(o["id"]) for o in orders if o.get("id")]
    if not ids:
        return
    cur.execute(
        """
        select order_id, fulfillment_method, shipping_address, shipping_city,
               shipping_postal, order_note
        from order_fulfillment where order_id = any(%s)
        """,
        (ids,),
    )
    by_order = {str(r["order_id"]): r for r in cur.fetchall()}
    for order in orders:
        row = by_order.get(str(order.get("id")))
        if not row:
            continue
        order["fulfillment_method"] = row["fulfillment_method"]
        order["shipping_address"] = row.get("shipping_address")
        order["shipping_city"] = row.get("shipping_city")
        order["shipping_postal"] = row.get("shipping_postal")
        order["order_note"] = row.get("order_note")


def attach_order_relations(cur, orders: list[dict]) -> None:
    """Join child tables (contacts, fulfillment, items) onto order rows."""
    attach_order_contacts(cur, orders)
    attach_order_fulfillment(cur, orders)
    attach_order_items(cur, orders)


def hydrate_orders(orders: list[dict]) -> None:
    for order in orders:
        hydrate_order(order)


def product_display_name(order: dict, products_by_id: dict[str, dict]) -> str:
    pid = order_product_id(order)
    if pid and pid in products_by_id:
        row = products_by_id[pid]
        return row.get("name_zh") or row.get("name_en") or "訂製品項"
    product_type = (order.get("product_type") or order.get("summary_zh") or "").strip()
    if product_type and not is_uuid(product_type):
        return product_type
    category = order.get("category")
    return CATEGORY_LABELS.get(category, category) or "訂製品項"


def attach_order_display(cur, orders: list[dict]) -> None:
    """Resolve product names, summary labels, thumbnails, and display dates."""
    attach_order_relations(cur, orders)
    hydrate_orders(orders)

    product_ids: list[str] = []
    for order in orders:
        pid = order_product_id(order)
        if pid:
            product_ids.append(pid)

    products_by_id: dict[str, dict] = {}
    if product_ids:
        cur.execute(
            "select id, name_zh, name_en, category, sort_order from products where id = any(%s)",
            (list(set(product_ids)),),
        )
        for row in cur.fetchall():
            products_by_id[str(row["id"])] = row

    images_by_product: dict[str, list] = {}
    if product_ids:
        cur.execute(
            "select * from product_images where product_id = any(%s) order by sort_order",
            (list(set(product_ids)),),
        )
        for image in cur.fetchall():
            images_by_product.setdefault(str(image["product_id"]), []).append(image)

    for order in orders:
        if order.get("id") is not None:
            order["id"] = str(order["id"])
        if order.get("product_id") is not None:
            order["product_id"] = str(order["product_id"])

        name = product_display_name(order, products_by_id)
        order["product_name"] = name
        series = order.get("series")
        order["summary"] = f"{series} · {name}" if series else name
        if is_uuid(order.get("product_type")):
            order["product_type"] = name

        url = ""
        pid = order_product_id(order)
        if pid and pid in images_by_product:
            imgs = images_by_product[pid]
            color = order.get("color") or "white"
            match = next((i for i in imgs if i["color"] == color), None)
            if not match and imgs:
                match = imgs[0]
            if match:
                url = resolve_product_image_url(match["file_path"])

        config = _as_dict(order.get("config_json"))
        if not config:
            config = {
                "category": order.get("category"),
                # product_type may be display name (summaryZh) — prefer product_id / letter type
                "type": order.get("product_id") or order.get("product_type"),
                "color": order.get("color") or "white",
                "diamondKind": order.get("diamond_kind"),
                "fancyColor": order.get("fancy_color"),
            }
        # Never pass hydrated product_type (often summaryZh) — breaks style_key lookup
        style_ref = config.get("type") or order.get("product_id")
        order["image_url"] = config_image_url(
            cur,
            config,
            style_type=str(style_ref) if style_ref else None,
            category=order.get("category") or config.get("category"),
            product_id=pid,
            images=images_by_product.get(pid or "", []) if pid else None,
            products_by_id=products_by_id,
        ) or url

        created = order.get("created_at")
        if created is not None:
            order["created_at_display"] = created.strftime("%Y/%m/%d")
