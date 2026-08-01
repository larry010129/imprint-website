"""Membership tier resolution + display helpers (mirrors frontend membership-tiers.ts)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.membership_config import default_config

ELIGIBLE_ORDER_STATUSES = frozenset({"shipped", "completed"})

_MEMBER_ACCENTS: dict[str, dict[str, str]] = {
    "ice": {
        "from": "#f4fbfb",
        "to": "#9CEFEF",
        "text": "#2b2320",
        "muted": "#3a7a7a",
        "line": "#dcf2f2",
        "chip": "#5ecfcf",
    },
    "platinum": {
        "from": "#f7f8fa",
        "to": "#d4dae6",
        "text": "#2b2320",
        "muted": "#5c6578",
        "line": "#c5ccd8",
        "chip": "#8b95a8",
    },
    "rose": {
        "from": "#faf0ec",
        "to": "#e8b4a2",
        "text": "#2b2320",
        "muted": "#8a5a4a",
        "line": "#e0c4b8",
        "chip": "#c4785a",
    },
    "star": {
        "from": "#1c2430",
        "to": "#2a3340",
        "text": "#faf8f6",
        "muted": "#b8c4d4",
        "line": "#3a4555",
        "chip": "#9cb4d4",
    },
    "imprint": {
        "from": "#141210",
        "to": "#2b2320",
        "text": "#f5efe6",
        "muted": "#d4c4a8",
        "line": "#b8956c",
        "chip": "#b8956c",
    },
}

_PARTNER_ACCENTS: dict[str, dict[str, str]] = {
    "partner_entry": {
        "from": "#f7f5f2",
        "to": "#e8e0d4",
        "text": "#2b2320",
        "muted": "#6b5e52",
        "line": "#d8cfc3",
        "chip": "#a89078",
    },
    "partner_platinum": {
        "from": "#f4f6f8",
        "to": "#c8d0dc",
        "text": "#2b2320",
        "muted": "#4a5568",
        "line": "#b0bac8",
        "chip": "#718096",
    },
    "partner_rose": {
        "from": "#f8ece8",
        "to": "#d9a090",
        "text": "#2b2320",
        "muted": "#7a4a3c",
        "line": "#d0b0a4",
        "chip": "#b06850",
    },
    "partner_star": {
        "from": "#161c28",
        "to": "#243040",
        "text": "#faf8f6",
        "muted": "#a8b8cc",
        "line": "#3a4860",
        "chip": "#7a9cc0",
    },
    "partner_imprint": {
        "from": "#120f0c",
        "to": "#2a2018",
        "text": "#f5efe6",
        "muted": "#d0b890",
        "line": "#a07848",
        "chip": "#c4a06a",
    },
}

_TAIPEI = ZoneInfo("Asia/Taipei")


def accent_for_tier(tier_id: str) -> dict[str, str]:
    if tier_id.startswith("partner_"):
        return _PARTNER_ACCENTS.get(tier_id, _PARTNER_ACCENTS["partner_entry"])
    return _MEMBER_ACCENTS.get(tier_id, _MEMBER_ACCENTS["ice"])


def is_dark_tier(tier_id: str) -> bool:
    return tier_id in {"star", "imprint", "partner_star", "partner_imprint"}


def derive_member_display_number(member_id: str) -> str:
    """Stable 12-digit numeric display id from internal user id (UUID)."""
    compact = member_id.replace("-", "").replace(" ", "").strip()
    if not compact:
        return ""
    try:
        value = int(compact, 16) % 10**12
    except ValueError:
        digest = hashlib.sha256(compact.encode("utf-8")).hexdigest()
        value = int(digest, 16) % 10**12
    return f"{value:012d}"


def format_member_id_groups(member_id: str) -> str:
    number = derive_member_display_number(member_id)
    if not number:
        return "———— ————"
    return " ".join(number[i : i + 4] for i in range(0, len(number), 4))


def format_spend(amount: int) -> str:
    return f"NT${amount:,}"


def membership_track(profile: dict[str, Any] | None, *, is_admin: bool) -> str:
    if is_admin and not (profile or {}).get("is_partner"):
        return "member"
    if (profile or {}).get("is_partner"):
        return "partner"
    return "member"


def _parse_order_date(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value is None:
        return None
    try:
        if isinstance(value, str):
            text = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(text)
        else:
            parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _taipei_ymd(when: datetime) -> tuple[int, int, int]:
    local = when.astimezone(_TAIPEI)
    return local.year, local.month, local.day


def rolling_two_year_cutoff(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now - timedelta(days=730)


def filter_eligible_orders(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for order in orders:
        status = str(order.get("status") or "").strip().lower()
        if status in ELIGIBLE_ORDER_STATUSES:
            out.append(order)
    return out


def member_window_stats(orders: list[dict[str, Any]], now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    cutoff = rolling_two_year_cutoff(now)
    eligible = [
        o
        for o in filter_eligible_orders(orders)
        if (d := _parse_order_date(o.get("created_at"))) and d >= cutoff
    ]
    spend = 0
    for order in eligible:
        try:
            n = float(order.get("total_price") or 0)
        except (TypeError, ValueError):
            continue
        if n > 0:
            spend += int(round(n))
    return {"order_count": len(eligible), "spend": spend}


def partner_window_stats(orders: list[dict[str, Any]], now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    y, m, _ = _taipei_ymd(now)
    month_count = 0
    year_count = 0
    for order in filter_eligible_orders(orders):
        d = _parse_order_date(order.get("created_at"))
        if not d:
            continue
        oy, om, _ = _taipei_ymd(d)
        if oy == y:
            year_count += 1
            if om == m:
                month_count += 1
    return {"month_count": month_count, "year_count": year_count}


def _member_qualifies(tier: dict[str, Any], order_count: int, spend: int, invites: int) -> bool:
    if tier.get("inviteOnly"):
        return False
    if tier.get("id") == "ice":
        return True
    return (
        order_count >= int(tier.get("minOrders") or 0)
        or spend >= int(tier.get("minSpendTwd") or 0)
        or (int(tier.get("minInvites") or 0) > 0 and invites >= int(tier.get("minInvites") or 0))
    )


def _partner_qualifies(tier: dict[str, Any], month_count: int, year_count: int) -> bool:
    if tier.get("inviteOnly"):
        return False
    if tier.get("id") == "partner_entry":
        return True
    return month_count >= int(tier.get("minOrdersPerMonth") or 0) or year_count >= int(
        tier.get("minOrdersPerYear") or 0
    )


def resolve_tier_id(
    *,
    profile: dict[str, Any] | None,
    orders: list[dict[str, Any]],
    invite_count: int,
    is_admin: bool,
    config: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> str:
    cfg = config or default_config()
    track = membership_track(profile, is_admin=is_admin)
    profile = profile or {}

    if track == "partner":
        if is_admin or profile.get("partner_imprint_invited"):
            return "partner_imprint"
        stats = partner_window_stats(orders, now)
        best = "partner_entry"
        for tier in cfg.get("partner", {}).get("tiers") or []:
            if _partner_qualifies(tier, stats["month_count"], stats["year_count"]):
                best = str(tier.get("id") or best)
        return best

    if is_admin or profile.get("imprint_invited"):
        return "imprint"
    stats = member_window_stats(orders, now)
    best = "ice"
    for tier in cfg.get("member", {}).get("tiers") or []:
        if _member_qualifies(tier, stats["order_count"], stats["spend"], invite_count):
            best = str(tier.get("id") or best)
    return best


def tier_name(tier_id: str, config: dict[str, Any] | None = None) -> str:
    cfg = config or default_config()
    track = "partner" if tier_id.startswith("partner_") else "member"
    for tier in cfg.get(track, {}).get("tiers") or []:
        if tier.get("id") == tier_id:
            return str(tier.get("name") or tier_id)
    return tier_id


def display_label(
    tier_id: str,
    *,
    profile: dict[str, Any] | None,
    is_admin: bool,
    config: dict[str, Any] | None = None,
) -> str:
    profile = profile or {}
    if is_admin and not profile.get("is_partner"):
        return "管理員"
    return tier_name(tier_id, config)


def _member_price_line(tier: dict[str, Any]) -> str:
    if tier.get("inviteOnly"):
        return "僅限邀請"
    if tier.get("id") == "ice":
        return "免費"
    bits: list[str] = []
    if int(tier.get("minOrders") or 0) > 0:
        bits.append(f"{int(tier['minOrders'])} 筆")
    if int(tier.get("minSpendTwd") or 0) > 0:
        bits.append(format_spend(int(tier["minSpendTwd"])))
    return " or ".join(bits) or "—"


def _member_cadence_line(tier: dict[str, Any]) -> str:
    if tier.get("inviteOnly"):
        return "僅限邀請"
    if tier.get("id") == "ice":
        return "永久"
    bits: list[str] = []
    if int(tier.get("minSpendTwd") or 0) > 0:
        bits.append(format_spend(int(tier["minSpendTwd"])))
    if int(tier.get("minOrders") or 0) > 0:
        bits.append(f"{int(tier['minOrders'])} 筆")
    if int(tier.get("minInvites") or 0) > 0:
        bits.append(f"{int(tier['minInvites'])} 邀請")
    return " or ".join(bits) or "—"


def _partner_price_line(tier: dict[str, Any]) -> str:
    if tier.get("inviteOnly"):
        return "僅限邀請"
    if tier.get("id") == "partner_entry":
        return "合作身份"
    month = int(tier.get("minOrdersPerMonth") or 0)
    year = int(tier.get("minOrdersPerYear") or 0)
    return f"每月 {month} or 每年 {year}"


def plans_for_track(track: str, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = config or default_config()
    if track == "partner":
        tiers = cfg.get("partner", {}).get("tiers") or []
        return [
            {
                "id": t.get("id"),
                "name": t.get("name"),
                "price": _partner_price_line(t),
                "cadence": "僅限邀請"
                if t.get("inviteOnly")
                else ("永久（合作身份）" if t.get("id") == "partner_entry" else "每月 or 每年重計"),
                "accent": accent_for_tier(str(t.get("id") or "")),
            }
            for t in tiers
        ]
    tiers = cfg.get("member", {}).get("tiers") or []
    return [
        {
            "id": t.get("id"),
            "name": t.get("name"),
            "price": _member_price_line(t),
            "cadence": _member_cadence_line(t),
            "accent": accent_for_tier(str(t.get("id") or "")),
        }
        for t in tiers
    ]


def feature_groups_for_track(track: str, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = config or default_config()
    key = "partner" if track == "partner" else "member"
    return list(cfg.get(key, {}).get("benefitGroups") or [])


def _best_ratio_label(candidates: list[tuple[int, int]]) -> str:
    best: tuple[int, int] | None = None
    best_pct = -1.0
    for cur, mx in candidates:
        if mx <= 0:
            continue
        pct = cur / mx
        if pct > best_pct:
            best_pct = pct
            best = (cur, mx)
    if not best:
        return "—"
    return f"{max(0, best[0]):,}/{max(0, best[1]):,}"


def progress_toward_next(
    tier_id: str,
    *,
    track: str,
    order_count: int = 0,
    spend: int = 0,
    invites: int = 0,
    month_count: int = 0,
    year_count: int = 0,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or default_config()
    plans = plans_for_track(track, cfg)
    idx = next((i for i, p in enumerate(plans) if p["id"] == tier_id), 0)
    current = (cfg.get(track if track == "partner" else "member", {}).get("tiers") or [])[idx]
    next_tier = (
        (cfg.get(track if track == "partner" else "member", {}).get("tiers") or [])[idx + 1]
        if idx + 1
        < len(cfg.get(track if track == "partner" else "member", {}).get("tiers") or [])
        else None
    )

    if not next_tier:
        detail = (
            f"本月 {month_count} 筆 · 本年 {year_count} 筆"
            if track == "partner"
            else f"消費 {format_spend(spend)} · 完成訂單 {order_count} 筆"
        )
        invite_only = bool(current.get("inviteOnly")) or "imprint" in tier_id
        return {
            "percent": 100,
            "label": "邀請制最高等級" if invite_only else "已達最高等級",
            "detail": detail,
            "ratio_label": "邀請制" if invite_only else "滿級",
        }

    if next_tier.get("inviteOnly"):
        return {
            "percent": 100,
            "label": f"「{next_tier.get('name')}」僅限邀請",
            "detail": f"本月 {month_count} 筆 · 本年 {year_count} 筆"
            if track == "partner"
            else f"消費 {format_spend(spend)} · 完成訂單 {order_count} 筆",
            "ratio_label": "邀請制",
        }

    if track == "partner":
        min_m = int(next_tier.get("minOrdersPerMonth") or 0)
        min_y = int(next_tier.get("minOrdersPerYear") or 0)
        month_pct = min(1.0, month_count / min_m) if min_m > 0 else 1.0
        year_pct = min(1.0, year_count / min_y) if min_y > 0 else 1.0
        return {
            "percent": int(round(max(month_pct, year_pct) * 100)),
            "label": f"升級「{next_tier.get('name')}」",
            "detail": f"本月 {month_count}/{min_m} · 本年 {year_count}/{min_y}",
            "ratio_label": _best_ratio_label([(month_count, min_m), (year_count, min_y)]),
        }

    min_o = int(next_tier.get("minOrders") or 0)
    min_s = int(next_tier.get("minSpendTwd") or 0)
    min_i = int(next_tier.get("minInvites") or 0)
    order_pct = min(1.0, order_count / min_o) if min_o > 0 else 1.0
    spend_pct = min(1.0, spend / min_s) if min_s > 0 else 1.0
    invite_pct = min(1.0, invites / min_i) if min_i > 0 else 0.0
    cands = [(spend, min_s), (order_count, min_o)]
    if min_i > 0:
        cands.append((invites, min_i))
    return {
        "percent": int(round(max(order_pct, spend_pct, invite_pct) * 100)),
        "label": f"升級「{next_tier.get('name')}」",
        "detail": f"消費 {format_spend(spend)} · 完成訂單 {order_count} 筆",
        "ratio_label": _best_ratio_label(cands),
    }


def keep_progress(
    tier_id: str,
    *,
    track: str,
    order_count: int = 0,
    spend: int = 0,
    invites: int = 0,
    month_count: int = 0,
    year_count: int = 0,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or default_config()
    tiers = cfg.get(track if track == "partner" else "member", {}).get("tiers") or []
    current = next((t for t in tiers if t.get("id") == tier_id), tiers[0] if tiers else {})

    if current.get("inviteOnly") or "imprint" in tier_id:
        return {"percent": 100, "label": "續卡進度", "detail": "邀請制", "ratio_label": "邀請制"}

    if track == "partner":
        if current.get("id") == "partner_entry":
            return {"percent": 100, "label": "續卡進度", "detail": "永久（合作身份）", "ratio_label": "永久"}
        min_m = int(current.get("minOrdersPerMonth") or 0)
        min_y = int(current.get("minOrdersPerYear") or 0)
        month_pct = min(1.0, month_count / min_m) if min_m > 0 else 1.0
        year_pct = min(1.0, year_count / min_y) if min_y > 0 else 1.0
        return {
            "percent": int(round(max(month_pct, year_pct) * 100)),
            "label": "續卡進度",
            "detail": f"本月 {month_count}/{min_m} · 本年 {year_count}/{min_y}",
            "ratio_label": _best_ratio_label([(month_count, min_m), (year_count, min_y)]),
        }

    if current.get("id") == "ice":
        return {"percent": 100, "label": "續卡進度", "detail": "永久", "ratio_label": "永久"}

    min_o = int(current.get("minOrders") or 0)
    min_s = int(current.get("minSpendTwd") or 0)
    min_i = int(current.get("minInvites") or 0)
    order_pct = min(1.0, order_count / min_o) if min_o > 0 else 0.0
    spend_pct = min(1.0, spend / min_s) if min_s > 0 else 0.0
    invite_pct = min(1.0, invites / min_i) if min_i > 0 else 0.0
    cands = [(spend, min_s), (order_count, min_o)]
    if min_i > 0:
        cands.append((invites, min_i))
    bits: list[str] = []
    if min_s > 0:
        bits.append(f"{format_spend(spend)}/{format_spend(min_s)}")
    if min_o > 0:
        bits.append(f"{order_count}/{min_o} 筆")
    if min_i > 0:
        bits.append(f"{invites}/{min_i} 邀請")
    return {
        "percent": int(round(max(order_pct, spend_pct, invite_pct) * 100)),
        "label": "續卡進度",
        "detail": " · ".join(bits) or f"消費 {format_spend(spend)} · 完成訂單 {order_count} 筆",
        "ratio_label": _best_ratio_label(cands),
    }


def upgrade_hint(
    tier_id: str,
    *,
    track: str,
    order_count: int = 0,
    spend: int = 0,
    invites: int = 0,
    month_count: int = 0,
    year_count: int = 0,
    config: dict[str, Any] | None = None,
) -> str | None:
    cfg = config or default_config()
    tiers = cfg.get(track if track == "partner" else "member", {}).get("tiers") or []
    idx = next((i for i, t in enumerate(tiers) if t.get("id") == tier_id), -1)
    if idx < 0 or idx + 1 >= len(tiers):
        return None
    nxt = tiers[idx + 1]
    if nxt.get("inviteOnly"):
        return f"「{nxt.get('name')}」僅限品牌邀請"

    if track == "partner":
        month_left = max(0, int(nxt.get("minOrdersPerMonth") or 0) - month_count)
        year_left = max(0, int(nxt.get("minOrdersPerYear") or 0) - year_count)
        if month_left <= 0 or year_left <= 0:
            return None
        return f"本月再完成 {month_left} 筆 or 本年再完成 {year_left} 筆，可升級「{nxt.get('name')}」"

    orders_left = max(0, int(nxt.get("minOrders") or 0) - order_count)
    spend_left = max(0, int(nxt.get("minSpendTwd") or 0) - spend)
    invite_left = max(0, int(nxt.get("minInvites") or 0) - invites)
    if orders_left <= 0 or spend_left <= 0 or (int(nxt.get("minInvites") or 0) > 0 and invite_left <= 0):
        return None
    invite_bit = (
        f" or 邀請滿 {int(nxt['minInvites'])} 位好友（目前 {invites}）"
        if int(nxt.get("minInvites") or 0) > 0
        else ""
    )
    return (
        f"再完成 {orders_left} 筆 or 累計消費滿 {format_spend(int(nxt.get('minSpendTwd') or 0))}"
        f"{invite_bit}，即可升級「{nxt.get('name')}」"
    )


def build_account_membership(
    *,
    profile: dict[str, Any] | None,
    orders: list[dict[str, Any]],
    invite_count: int,
    is_admin: bool,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or default_config()
    enabled = cfg.get("enabled") is not False
    track = membership_track(profile, is_admin=is_admin)
    tier_id = resolve_tier_id(
        profile=profile,
        orders=orders,
        invite_count=invite_count,
        is_admin=is_admin,
        config=cfg,
    )
    member_stats = member_window_stats(orders)
    partner_stats = partner_window_stats(orders)
    order_count = member_stats["order_count"]
    spend = member_stats["spend"]
    month_count = partner_stats["month_count"]
    year_count = partner_stats["year_count"]
    progress_ctx = {
        "track": track,
        "order_count": order_count,
        "spend": spend,
        "invites": invite_count,
        "month_count": month_count,
        "year_count": year_count,
        "config": cfg,
    }
    return {
        "enabled": enabled,
        "track": track,
        "tier_id": tier_id,
        "tier_name": tier_name(tier_id, cfg),
        "role_label": display_label(tier_id, profile=profile, is_admin=is_admin, config=cfg)
        if enabled
        else (
            "管理員"
            if is_admin
            else ("合作廠商" if (profile or {}).get("is_partner") else "會員")
        ),
        "accent": accent_for_tier(tier_id),
        "is_dark": is_dark_tier(tier_id),
        "partner_chip": track == "partner",
        "order_count": order_count,
        "spend": spend,
        "invites": invite_count,
        "month_count": month_count,
        "year_count": year_count,
        "progress": progress_toward_next(tier_id, **progress_ctx),
        "keep_progress": keep_progress(tier_id, **progress_ctx),
        "upgrade_hint": upgrade_hint(tier_id, **progress_ctx) if enabled else None,
        "plans": plans_for_track(track, cfg),
        "feature_groups": feature_groups_for_track(track, cfg),
    }
