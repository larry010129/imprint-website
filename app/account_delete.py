"""Shared hard-delete helpers for member self-delete and admin account delete."""

from __future__ import annotations

from app.auth import is_admin


def staff_admin_count(cur) -> int:
    cur.execute("select count(*)::int as n from staff_admins")
    row = cur.fetchone() or {}
    return int(row.get("n") or 0)


def delete_blocked_reason(cur, user_id: str) -> str | None:
    """Return Chinese error if delete blocked; None if allowed."""
    if not is_admin(user_id):
        return None
    if staff_admin_count(cur) <= 1:
        return "無法刪除：這是唯一管理員，請先指定其他管理員。"
    return None


def hard_delete_user(cur, user_id: str) -> None:
    """FK cascade clears profiles/staff_admins/sessions dependents."""
    try:
        from app.erp_inbound import enqueue_event
        enqueue_event(
            cur,
            event_type="customer.deletion_requested",
            entity_ref=str(user_id),
            idempotency_key=f"customer:deleted:{user_id}",
            payload={"user_id": str(user_id)},
        )
    except Exception:
        pass
    cur.execute("delete from users where id = %s", (user_id,))
