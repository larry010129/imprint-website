"""TOTP (RFC 6238) helpers — secret generation, verify, backup codes, QR."""

from __future__ import annotations

import base64
import io
import re
import secrets

import bcrypt
import pyotp
import qrcode

TOTP_ISSUER = "銘印鑽石"
BACKUP_CODE_COUNT = 8
_CODE_RE = re.compile(r"^\d{6}$")
_BACKUP_RE = re.compile(r"^[A-Z0-9]{4}-[A-Z0-9]{4}$")


def ensure_totp_columns() -> None:
    from app.database import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("alter table users add column if not exists totp_secret text")
        cur.execute(
            "alter table users add column if not exists totp_enabled boolean not null default false"
        )
        cur.execute("alter table users add column if not exists totp_backup_codes jsonb")


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=TOTP_ISSUER)


def qr_data_url(otpauth_uri: str) -> str:
    img = qrcode.make(otpauth_uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def normalize_code(code: str) -> str:
    return re.sub(r"\s+", "", (code or "").strip())


def normalize_backup_code(code: str) -> str:
    raw = (code or "").strip().upper().replace(" ", "")
    if len(raw) == 8 and "-" not in raw:
        raw = f"{raw[:4]}-{raw[4:]}"
    return raw


def verify_totp(secret: str, code: str, *, valid_window: int = 1) -> bool:
    normalized = normalize_code(code)
    if not _CODE_RE.match(normalized):
        return False
    return bool(pyotp.TOTP(secret).verify(normalized, valid_window=valid_window))


def generate_backup_codes(count: int = BACKUP_CODE_COUNT) -> list[str]:
    codes: list[str] = []
    for _ in range(count):
        part = secrets.token_hex(4).upper()
        codes.append(f"{part[:4]}-{part[4:8]}")
    return codes


def hash_backup_codes(codes: list[str]) -> list[str]:
    return [bcrypt.hashpw(c.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8") for c in codes]


def verify_backup_code(code: str, hashed_codes: list[str] | None) -> int | None:
    """Return index of matched hash, or None."""
    normalized = normalize_backup_code(code)
    if not _BACKUP_RE.match(normalized) or not hashed_codes:
        return None
    for idx, hashed in enumerate(hashed_codes):
        if bcrypt.checkpw(normalized.encode("utf-8"), hashed.encode("utf-8")):
            return idx
    return None


def burn_backup_code(hashed_codes: list[str] | None, index: int) -> list[str]:
    codes = list(hashed_codes or [])
    if 0 <= index < len(codes):
        codes.pop(index)
    return codes
