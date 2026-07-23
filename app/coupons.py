"""Checkout coupon validation, discount math, and redemption."""

from __future__ import annotations

import math
import secrets
import string
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4


def normalize_code(code: str | None) -> str:
    return str(code or "").strip().upper()


def generate_coupon_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    # Avoid ambiguous chars
    alphabet = alphabet.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _num(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def compute_discount_amount(*, discount_type: str, discount_value: float, subtotal: float) -> int:
    """Return whole-TWD discount, never exceeding subtotal."""
    subtotal = max(0.0, float(subtotal))
    if subtotal <= 0:
        return 0
    if discount_type == "percent":
        pct = max(0.0, min(100.0, float(discount_value)))
        amount = math.floor(subtotal * pct / 100.0)
    else:
        amount = math.floor(max(0.0, float(discount_value)))
    return int(min(amount, math.floor(subtotal)))


def apply_discount_split(item_totals: list[float], discount: int) -> list[int]:
    """Split whole-TWD discount across items (largest remainder)."""
    n = len(item_totals)
    if n == 0 or discount <= 0:
        return [0] * n
    totals = [max(0.0, float(t)) for t in item_totals]
    subtotal = sum(totals)
    if subtotal <= 0:
        return [0] * n
    discount = int(min(discount, math.floor(subtotal)))

    raw = [(totals[i] / subtotal) * discount for i in range(n)]
    floors = [math.floor(x) for x in raw]
    rem = discount - sum(floors)
    # Assign leftover TWD to items with largest fractional parts
    order = sorted(range(n), key=lambda i: (raw[i] - floors[i], totals[i]), reverse=True)
    shares = floors[:]
    for i in order:
        if rem <= 0:
            break
        # Don't exceed item total
        room = math.floor(totals[i]) - shares[i]
        if room <= 0:
            continue
        shares[i] += 1
        rem -= 1
    # If still remainder (tiny items), dump on largest item
    if rem > 0:
        j = max(range(n), key=lambda i: totals[i])
        shares[j] += rem
    return shares


def validate_coupon(
    cur,
    *,
    code: str,
    user_id: str,
    subtotal: float,
    lock: bool = False,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return (result_dict, error_message).

    Pass lock=True inside the checkout write transaction: it takes a row lock on
    the coupon (SELECT ... FOR UPDATE) so two concurrent checkouts of a
    single-use (or per-user-capped) code can't both pass the used_count check
    before either increments it. On an autocommit read (the /coupon/validate
    preview) leave lock=False — the lock would be released instantly and only
    adds contention."""
    normalized = normalize_code(code)
    if not normalized:
        return None, "請輸入優惠碼"

    cur.execute(
        "select * from coupons where code = %s" + (" for update" if lock else ""),
        (normalized,),
    )
    coupon = cur.fetchone()
    if not coupon:
        return None, "優惠碼不存在"

    if not coupon.get("is_active"):
        return None, "此優惠碼已停用"

    now = datetime.now(timezone.utc)
    starts = coupon.get("starts_at")
    expires = coupon.get("expires_at")
    if starts and starts > now:
        return None, "此優惠碼尚未開始"
    if expires and expires < now:
        return None, "此優惠碼已過期"

    min_order = coupon.get("min_order_amount")
    if min_order is not None and subtotal < _num(min_order):
        return None, f"未達最低消費金額 NT${int(_num(min_order)):,}"

    max_uses = coupon.get("max_uses")
    used = int(coupon.get("used_count") or 0)
    if max_uses is not None and used >= int(max_uses):
        return None, "此優惠碼已達使用上限"

    max_per_user = coupon.get("max_uses_per_user")
    if max_per_user is not None:
        cur.execute(
            """
            select count(distinct checkout_batch_id) as n
            from coupon_redemptions
            where coupon_id = %s and user_id = %s
            """,
            (coupon["id"], user_id),
        )
        row = cur.fetchone() or {}
        if int(row.get("n") or 0) >= int(max_per_user):
            return None, "您已達此優惠碼使用次數上限"

    discount_type = str(coupon.get("discount_type") or "")
    discount_value = _num(coupon.get("discount_value"))
    if discount_type not in ("percent", "fixed"):
        return None, "優惠碼設定無效"

    discount = compute_discount_amount(
        discount_type=discount_type,
        discount_value=discount_value,
        subtotal=subtotal,
    )
    if discount <= 0:
        return None, "此優惠碼目前無法折抵"

    return {
        "coupon": coupon,
        "code": normalized,
        "discountType": discount_type,
        "discountValue": discount_value,
        "discountAmount": discount,
        "subtotal": int(math.floor(subtotal)),
        "total": int(math.floor(subtotal)) - discount,
        "label": coupon.get("label"),
    }, None


def record_redemptions(
    cur,
    *,
    coupon_id: Any,
    user_id: str,
    code: str,
    order_rows: list[dict[str, Any]],
) -> str:
    """Insert one redemption per order; increment used_count once. Returns batch id."""
    batch_id = str(uuid4())
    for row in order_rows:
        cur.execute(
            """
            insert into coupon_redemptions (
              coupon_id, user_id, order_id, checkout_batch_id, code,
              discount_amount, order_subtotal, order_total
            ) values (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                coupon_id,
                user_id,
                row["order_id"],
                batch_id,
                code,
                row["discount_amount"],
                row["order_subtotal"],
                row["order_total"],
            ),
        )
    cur.execute(
        """
        update coupons
        set used_count = used_count + 1, updated_at = now()
        where id = %s
        """,
        (coupon_id,),
    )
    return batch_id
