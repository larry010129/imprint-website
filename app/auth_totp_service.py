"""TOTP enroll, verify, and disable — shared by JSON API and HTMX."""

from __future__ import annotations

import json
from typing import Any

from app.auth import (
    TOTP_VERIFY_LOCKOUT_SECONDS,
    TOTP_VERIFY_MAX_ATTEMPTS,
    bump_token_version,
    hash_password,
    record_failures,
    record_successes,
    verify_password,
)
from app.database import get_connection
from app.totp import (
    burn_backup_code,
    generate_backup_codes,
    generate_secret,
    hash_backup_codes,
    provisioning_uri,
    qr_data_url,
    verify_backup_code,
    verify_totp,
)


def _json_backup_codes(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return [str(x) for x in parsed] if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _store_backup_codes(codes: list[str] | None) -> str | None:
    if not codes:
        return None
    return json.dumps(codes)


def fetch_totp_user(user_id: str) -> dict | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select id, email, token_version, totp_secret, totp_enabled, totp_backup_codes
            from users where id = %s
            """,
            (user_id,),
        )
        return cur.fetchone()


def verify_second_factor(
    user_id: str,
    code: str,
    *,
    lockout_key: str | list[str] | None = None,
) -> tuple[bool, str]:
    user = fetch_totp_user(user_id)
    if not user or not user.get("totp_enabled") or not user.get("totp_secret"):
        return False, "雙因素驗證未啟用"

    secret = user["totp_secret"]
    backup_hashes = _json_backup_codes(user.get("totp_backup_codes"))

    if verify_totp(secret, code):
        record_successes(lockout_key)
        return True, ""

    backup_idx = verify_backup_code(code, backup_hashes)
    if backup_idx is None:
        record_failures(lockout_key, TOTP_VERIFY_MAX_ATTEMPTS, TOTP_VERIFY_LOCKOUT_SECONDS)
        return False, "驗證碼不正確"

    remaining = burn_backup_code(backup_hashes, backup_idx)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "update users set totp_backup_codes = %s where id = %s",
            (_store_backup_codes(remaining), user_id),
        )
    record_successes(lockout_key)
    return True, ""


def start_totp_setup(user_id: str, email: str) -> dict:
    secret = generate_secret()
    uri = provisioning_uri(secret, email)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "update users set totp_secret = %s, totp_enabled = false where id = %s",
            (secret, user_id),
        )
    return {
        "otpauthUri": uri,
        "qrDataUrl": qr_data_url(uri),
        "secret": secret,
        "issuer": "銘印鑽石",
    }


def confirm_totp_setup(user_id: str, code: str) -> tuple[list[str] | None, str | None]:
    user = fetch_totp_user(user_id)
    if not user or not user.get("totp_secret"):
        return None, "請先開始設定雙因素驗證"
    if user.get("totp_enabled"):
        return None, "雙因素驗證已啟用"

    if not verify_totp(user["totp_secret"], code):
        return None, "驗證碼不正確，請確認 Authenticator 時間同步"

    plain_codes = generate_backup_codes()
    hashed = hash_backup_codes(plain_codes)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            update users set totp_enabled = true, totp_backup_codes = %s
            where id = %s
            """,
            (_store_backup_codes(hashed), user_id),
        )
    return plain_codes, None


NO_TOTP_ENROLLED_MSG = "請先於帳戶安全設定驗證器，或聯絡管理員重設密碼"
PWRESET_GENERIC_ERR = "Email 或驗證碼不正確。"


def verify_totp_for_pwreset(
    email: str,
    code: str,
    *,
    lockout_key: str | list[str] | None = None,
) -> tuple[str | None, str | None]:
    """Verify TOTP/backup for password reset. Returns (user_id, error).

    Always returns the same generic error for unknown email / no TOTP / bad code
    so the reset path cannot enumerate enrolled accounts.
    """
    normalized = email.strip().lower()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select id, totp_secret, totp_enabled, totp_backup_codes, is_active
            from users where email = %s
            """,
            (normalized,),
        )
        user = cur.fetchone()

    if not user or not user.get("is_active"):
        return None, PWRESET_GENERIC_ERR
    if not user.get("totp_enabled") or not user.get("totp_secret"):
        return None, PWRESET_GENERIC_ERR

    user_id = str(user["id"])
    ok, _err = verify_second_factor(user_id, code, lockout_key=lockout_key)
    if not ok:
        return None, PWRESET_GENERIC_ERR
    return user_id, None


def complete_password_reset(user_id: str, new_password: str) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "update users set password_hash = %s where id = %s",
            (hash_password(new_password), user_id),
        )
    bump_token_version(user_id)


def reset_password_with_totp(
    email: str,
    code: str,
    new_password: str,
    *,
    lockout_key: str | list[str] | None = None,
) -> str | None:
    """Verify TOTP/backup and set a new password. Returns error message or None."""
    user_id, err = verify_totp_for_pwreset(email, code, lockout_key=lockout_key)
    if err:
        return err
    complete_password_reset(user_id, new_password)
    return None


def verify_step_up_password(
    user_id: str,
    password: str,
    totp_code: str | None = None,
) -> str | None:
    """Require current password (+ TOTP when enrolled) for destructive actions."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select password_hash, totp_enabled from users where id = %s",
            (user_id,),
        )
        user = cur.fetchone()
    if not user or not verify_password(password, user["password_hash"]):
        return "密碼不正確"
    if user.get("totp_enabled"):
        code = (totp_code or "").strip()
        if not code:
            return "請輸入 Authenticator 驗證碼"
        ok, err = verify_second_factor(user_id, code)
        if not ok:
            return err or "驗證碼不正確"
    return None


def step_up_from_body(user_id: str, body: dict | None) -> tuple[int, str] | None:
    """Extract password/TOTP from an admin JSON body. Returns (status, error) or None."""
    payload = body if isinstance(body, dict) else {}
    password = str(payload.get("password") or payload.get("adminPassword") or "")
    totp = str(payload.get("totpCode") or payload.get("code") or "").strip()
    if not password:
        return 400, "請輸入您的管理員密碼以確認"
    err = verify_step_up_password(str(user_id), password, totp or None)
    if err:
        return 401, err
    return None


def disable_totp(user_id: str, password: str, code: str) -> str | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select password_hash, totp_secret, totp_enabled, totp_backup_codes from users where id = %s",
            (user_id,),
        )
        user = cur.fetchone()
    if not user or not user.get("totp_enabled"):
        return "雙因素驗證未啟用"
    if not verify_password(password, user["password_hash"]):
        return "密碼不正確"

    secret = user["totp_secret"] or ""
    backup_hashes = _json_backup_codes(user.get("totp_backup_codes"))
    ok = verify_totp(secret, code) or verify_backup_code(code, backup_hashes) is not None
    if not ok:
        return "驗證碼不正確"

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            update users set totp_enabled = false, totp_secret = null, totp_backup_codes = null
            where id = %s
            """,
            (user_id,),
        )
    return None
