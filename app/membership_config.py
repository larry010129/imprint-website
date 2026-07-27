"""Admin-editable membership ladder config (membership_settings singleton)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from psycopg.types.json import Jsonb

MEMBER_TIER_IDS = ("ice", "platinum", "rose", "star", "imprint")
PARTNER_TIER_IDS = (
    "partner_entry",
    "partner_platinum",
    "partner_rose",
    "partner_star",
    "partner_imprint",
)

DEFAULT_MEMBER_BENEFITS: list[dict[str, Any]] = [
    {
        "section": "訂製服務",
        "features": [
            {"label": "線上客製試算", "values": [True, True, True, True, True]},
            {"label": "訂單進度查詢", "values": [True, True, True, True, True]},
            {"label": "購物車儲存配置", "values": [True, True, True, True, True]},
            {"label": "腰圍刻字選項", "values": [True, True, True, True, True]},
            {
                "label": "完整設計客製",
                "values": ["線上試算", "線上試算", "半客製化", "優先設計諮詢", "專屬全案設計"],
            },
        ],
    },
    {
        "section": "會員禮遇",
        "features": [
            {"label": "會員活動通知", "values": [True, True, True, True, True]},
            {"label": "生日驚喜禮", "values": [False, False, "即將推出", "即將推出", "即將推出"]},
            {"label": "專屬顧問服務", "values": [False, False, False, True, True]},
            {"label": "培育鑽石優惠劵", "values": [False, False, "即將推出", "即將推出", "即將推出"]},
        ],
    },
    {
        "section": "服務保障",
        "features": [
            {"label": "鑑定協助", "values": ["基本", "基本", "優先", "優先", "專人"]},
            {"label": "售後保固諮詢", "values": [True, True, True, True, True]},
            {"label": "VIP 預約通道", "values": [False, False, False, False, "即將推出"]},
        ],
    },
]

DEFAULT_PARTNER_BENEFITS: list[dict[str, Any]] = [
    {
        "section": "合作服務",
        "features": [
            {"label": "合作廠商身份", "values": [True, True, True, True, True]},
            {"label": "批量下單協助", "values": [False, True, True, True, True]},
            {"label": "優先產能協調", "values": [False, False, True, True, True]},
            {"label": "專屬業務窗口", "values": [False, False, False, True, True]},
            {"label": "品牌聯合露出", "values": [False, False, False, False, "邀請制"]},
        ],
    },
]


def default_config() -> dict[str, Any]:
    return {
        # Master switch: when false, account/profile hide membership ladder UI.
        "enabled": True,
        "member": {
            "tiers": [
                {
                    "id": "ice",
                    "name": "冰藍卡",
                    "minOrders": 0,
                    "minSpendTwd": 0,
                    "minInvites": 0,
                    "inviteOnly": False,
                },
                {
                    "id": "platinum",
                    "name": "白金卡",
                    "minOrders": 1,
                    "minSpendTwd": 50000,
                    "minInvites": 3,
                    "inviteOnly": False,
                },
                {
                    "id": "rose",
                    "name": "玫瑰金",
                    "minOrders": 2,
                    "minSpendTwd": 120000,
                    "minInvites": 5,
                    "inviteOnly": False,
                },
                {
                    "id": "star",
                    "name": "星鑽卡",
                    "minOrders": 3,
                    "minSpendTwd": 280000,
                    "minInvites": 10,
                    "inviteOnly": False,
                },
                {
                    "id": "imprint",
                    "name": "銘鑽卡",
                    "minOrders": 0,
                    "minSpendTwd": 0,
                    "minInvites": 0,
                    "inviteOnly": True,
                },
            ],
            "benefitGroups": deepcopy(DEFAULT_MEMBER_BENEFITS),
        },
        "partner": {
            "tiers": [
                {
                    "id": "partner_entry",
                    "name": "合作入門",
                    "minOrdersPerMonth": 0,
                    "minOrdersPerYear": 0,
                    "inviteOnly": False,
                },
                {
                    "id": "partner_platinum",
                    "name": "合作白金",
                    "minOrdersPerMonth": 10,
                    "minOrdersPerYear": 120,
                    "inviteOnly": False,
                },
                {
                    "id": "partner_rose",
                    "name": "合作玫瑰金",
                    "minOrdersPerMonth": 30,
                    "minOrdersPerYear": 360,
                    "inviteOnly": False,
                },
                {
                    "id": "partner_star",
                    "name": "合作星鑽",
                    "minOrdersPerMonth": 50,
                    "minOrdersPerYear": 600,
                    "inviteOnly": False,
                },
                {
                    "id": "partner_imprint",
                    "name": "合作銘鑽",
                    "minOrdersPerMonth": 0,
                    "minOrdersPerYear": 0,
                    "inviteOnly": True,
                },
            ],
            "benefitGroups": deepcopy(DEFAULT_PARTNER_BENEFITS),
        },
    }


def ensure_membership_schema(cur) -> None:
    for stmt in (
        "alter table profiles add column if not exists referral_code text",
        "alter table profiles add column if not exists referred_by uuid",
        "alter table profiles add column if not exists referred_at timestamptz",
        "alter table profiles add column if not exists imprint_invited boolean not null default false",
        "alter table profiles add column if not exists partner_imprint_invited boolean not null default false",
        """
        create table if not exists membership_settings (
          id integer primary key,
          config_json jsonb not null default '{}'::jsonb,
          updated_at timestamptz not null default now(),
          constraint membership_settings_singleton check (id = 1)
        )
        """,
    ):
        cur.execute(stmt)
    cur.execute(
        """
        insert into membership_settings (id, config_json)
        values (1, %s)
        on conflict (id) do nothing
        """,
        (Jsonb(default_config()),),
    )


def _as_int(value: Any, default: int = 0) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, n)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _traditional_zh(name: str) -> str:
    """Prefer Traditional Chinese forms for display names (蓝→藍)."""
    return name.replace("\u84dd", "\u85cd")  # 蓝 → 藍


def _normalize_cell(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    return str(value).strip() or False


def _normalize_benefits(raw: Any, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        return deepcopy(fallback)
    out: list[dict[str, Any]] = []
    for group in raw:
        if not isinstance(group, dict):
            continue
        section = str(group.get("section") or "").strip() or "權益"
        features_in = group.get("features")
        if not isinstance(features_in, list):
            continue
        features: list[dict[str, Any]] = []
        for feat in features_in:
            if not isinstance(feat, dict):
                continue
            label = str(feat.get("label") or "").strip()
            if not label:
                continue
            values_raw = feat.get("values")
            if not isinstance(values_raw, list):
                values_raw = []
            values = [_normalize_cell(values_raw[i] if i < len(values_raw) else False) for i in range(5)]
            features.append({"label": label, "values": values})
        if features:
            out.append({"section": section, "features": features})
    return out or deepcopy(fallback)


def _normalize_member_tiers(raw: Any) -> list[dict[str, Any]]:
    by_id = {t["id"]: t for t in default_config()["member"]["tiers"]}
    if isinstance(raw, list):
        for row in raw:
            if not isinstance(row, dict):
                continue
            tid = str(row.get("id") or "")
            if tid not in by_id:
                continue
            base = by_id[tid]
            name = _traditional_zh(str(row.get("name") or base["name"]).strip() or base["name"])
            by_id[tid] = {
                "id": tid,
                "name": name,
                "minOrders": _as_int(row.get("minOrders"), base["minOrders"]),
                "minSpendTwd": _as_int(row.get("minSpendTwd"), base["minSpendTwd"]),
                "minInvites": _as_int(row.get("minInvites"), base["minInvites"]),
                "inviteOnly": _as_bool(row.get("inviteOnly")) if "inviteOnly" in row else base["inviteOnly"],
            }
    return [by_id[tid] for tid in MEMBER_TIER_IDS]


def _normalize_partner_tiers(raw: Any) -> list[dict[str, Any]]:
    by_id = {t["id"]: t for t in default_config()["partner"]["tiers"]}
    if isinstance(raw, list):
        for row in raw:
            if not isinstance(row, dict):
                continue
            tid = str(row.get("id") or "")
            if tid not in by_id:
                continue
            base = by_id[tid]
            name = _traditional_zh(str(row.get("name") or base["name"]).strip() or base["name"])
            month = _as_int(row.get("minOrdersPerMonth"), base["minOrdersPerMonth"])
            year_raw = row.get("minOrdersPerYear")
            year = _as_int(year_raw, month * 12) if year_raw is not None else month * 12
            by_id[tid] = {
                "id": tid,
                "name": name,
                "minOrdersPerMonth": month,
                "minOrdersPerYear": year,
                "inviteOnly": _as_bool(row.get("inviteOnly")) if "inviteOnly" in row else base["inviteOnly"],
            }
    return [by_id[tid] for tid in PARTNER_TIER_IDS]


def normalize_config(raw: Any) -> dict[str, Any]:
    base = default_config()
    if not isinstance(raw, dict):
        return base
    member = raw.get("member") if isinstance(raw.get("member"), dict) else {}
    partner = raw.get("partner") if isinstance(raw.get("partner"), dict) else {}
    # Missing key → keep default (on). Explicit false turns program off.
    if "enabled" in raw:
        enabled = _as_bool(raw.get("enabled"))
    else:
        enabled = bool(base["enabled"])
    return {
        "enabled": enabled,
        "member": {
            "tiers": _normalize_member_tiers(member.get("tiers")),
            "benefitGroups": _normalize_benefits(member.get("benefitGroups"), DEFAULT_MEMBER_BENEFITS),
        },
        "partner": {
            "tiers": _normalize_partner_tiers(partner.get("tiers")),
            "benefitGroups": _normalize_benefits(partner.get("benefitGroups"), DEFAULT_PARTNER_BENEFITS),
        },
    }


def validate_config(config: dict[str, Any]) -> str | None:
    member_tiers = config.get("member", {}).get("tiers") or []
    partner_tiers = config.get("partner", {}).get("tiers") or []
    if not any(str(t.get("name") or "").strip() for t in member_tiers):
        return "一般會員至少需要一個等級名稱"
    if not any(str(t.get("name") or "").strip() for t in partner_tiers):
        return "合作廠商至少需要一個等級名稱"
    for t in partner_tiers:
        if t.get("inviteOnly"):
            continue
        month = _as_int(t.get("minOrdersPerMonth"))
        year = _as_int(t.get("minOrdersPerYear"))
        if year and month and year < month:
            name = t.get("name") or t.get("id")
            return f"{name} 年門檻不可低於月門檻"
    return None


def load_config(cur) -> dict[str, Any]:
    ensure_membership_schema(cur)
    cur.execute("select config_json from membership_settings where id = 1")
    row = cur.fetchone()
    raw = (row or {}).get("config_json") if row else None
    if not raw or raw == {}:
        cfg = default_config()
        cur.execute(
            """
            update membership_settings
            set config_json = %s, updated_at = now()
            where id = 1 and (config_json = '{}'::jsonb or config_json is null)
            """,
            (Jsonb(cfg),),
        )
        return cfg
    return normalize_config(raw)


def save_config(cur, config: dict[str, Any]) -> dict[str, Any]:
    ensure_membership_schema(cur)
    clean = normalize_config(config)
    err = validate_config(clean)
    if err:
        raise ValueError(err)
    cur.execute(
        """
        insert into membership_settings (id, config_json, updated_at)
        values (1, %s, now())
        on conflict (id) do update
        set config_json = excluded.config_json, updated_at = now()
        """,
        (Jsonb(clean),),
    )
    return clean
