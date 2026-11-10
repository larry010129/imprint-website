from __future__ import annotations
"""Website to ERP Inbound Event Emitter & Authentication.

Implements durable outbox enqueuing and HMAC-SHA256 request verification
as specified in WEBSITE_TO_ERP_INTEGRATION.md and WEBSITE_TO_ERP_SECURITY.md.
"""


import hashlib
import hmac
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from app.database import get_connection

from app.auth import enforce_rate_limit

log = logging.getLogger(__name__)

ENV_INBOUND_ENABLED = "ERP_INBOUND_ENABLED"
ENV_EVENTS_ENABLED = "ERP_EVENTS_ENABLED"
ENV_EVENTS_HMAC_KEYS = "ERP_EVENTS_HMAC_KEYS"
ENV_SYNC_HMAC_KEYS = "ERP_SYNC_HMAC_KEYS"

HEADER_KEY_ID = "X-Erp-Key-Id"
HEADER_TIMESTAMP = "X-Erp-Timestamp"
HEADER_NONCE = "X-Erp-Nonce"
HEADER_SIGNATURE = "X-Erp-Signature"

MAX_CLOCK_SKEW_SEC = 300
AUTH_ERROR_RESPONSE = {"error": "unauthorized"}

# Canonical allow-listed event types (WEBSITE_TO_ERP_SECURITY.md §4)
ALLOWED_EVENT_TYPES = frozenset({
    "order.created",
    "order.status_changed",
    "order.payment_changed",
    "inquiry.submitted",
    "quote.requested",
    "booking.created",
    "customer.signed_up",
    "customer.profile_updated",
    "customer.deletion_requested",
    # Backward-compatible aliases
    "inquiry.created",
    "contact.submitted",
    "website.contact.submitted",
    "website.quote.requested",
    "account.created",
    "website.account.created",
    "profile.updated",
    "website.profile.updated",
    "payment.changed",
    "website.order.created",
    "website.order.status_changed",
    "website.order.payment_changed",
})

CANONICAL_EVENT_TYPES = {
    "inquiry.created": "inquiry.submitted",
    "contact.submitted": "inquiry.submitted",
    "website.contact.submitted": "inquiry.submitted",
    "website.quote.requested": "quote.requested",
    "account.created": "customer.signed_up",
    "website.account.created": "customer.signed_up",
    "profile.updated": "customer.profile_updated",
    "website.profile.updated": "customer.profile_updated",
    "payment.changed": "order.payment_changed",
    "website.order.created": "order.created",
    "website.order.status_changed": "order.status_changed",
    "website.order.payment_changed": "order.payment_changed",
}

# Forbidden keys in outbox payloads (WEBSITE_TO_ERP_SECURITY.md §6 IN-12)
FORBIDDEN_PII_KEYS = frozenset({
    "password",
    "password_hash",
    "hashed_password",
    "password_digest",
    "totp_secret",
    "totp",
    "session_token",
    "access_token",
    "refresh_token",
    "token",
    "jwt",
    "ip",
    "ip_address",
    "remote_ip",
    "client_ip",
    "g-recaptcha-response",
    "recaptchatoken",
    "captcha",
    "captcha_token",
    "card_number",
    "cvv",
    "cvc",
    "credit_card",
})



def mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return "***"
    user, domain = email.strip().split("@", 1)
    if len(user) <= 1:
        return f"{user}***@{domain}"
    return f"{user[0]}***@{domain}"


def mask_phone(phone: str | None) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 4:
        return "***"
    return f"***{digits[-4:]}"


def build_customer_block(
    user_id: str | None = None,
    name: str = "",
    email: str = "",
    phone: str = "",
    locale: str = "zh-TW",
) -> dict[str, Any]:
    return {
        "website_user_id": str(user_id) if user_id else None,
        "email": mask_email(email) if email else "",
        "email_full": email or "",
        "display_name": name or "",
        "phone_masked": mask_phone(phone) if phone else "",
        "phone_full": phone or "",
        "locale": locale or "zh-TW",
    }

def _assert_no_forbidden_pii(data: Any) -> None:
    """Recursively ensure no passwords, tokens, hashes, or IPs are in payload (IN-12)."""
    if isinstance(data, dict):
        for k, v in data.items():
            k_clean = str(k).lower().replace("_", "").replace("-", "")
            for forbidden in FORBIDDEN_PII_KEYS:
                f_clean = forbidden.replace("_", "").replace("-", "")
                if k_clean == f_clean or k_clean.startswith("password"):
                    raise ValueError(f"Forbidden PII key detected in ERP event payload: {k}")
            _assert_no_forbidden_pii(v)
    elif isinstance(data, list):
        for item in data:
            _assert_no_forbidden_pii(item)


def build_canonical_string(method: str, path_and_query: str, timestamp: str, nonce: str, body: bytes) -> str:
    """SEC-0 canonical string: METHOD\nPATH?QUERY\nTIMESTAMP\nNONCE\nhex(SHA256(body))."""
    body_hex_sha256 = hashlib.sha256(body).hexdigest().lower()
    return f"{method.upper()}\n{path_and_query}\n{timestamp}\n{nonce}\n{body_hex_sha256}"


def is_erp_events_enabled() -> bool:
    """Check if ERP inbound events feature flag is enabled (default 0 -> 404)."""
    val1 = (os.environ.get(ENV_INBOUND_ENABLED) or "").strip().lower()
    val2 = (os.environ.get(ENV_EVENTS_ENABLED) or "").strip().lower()
    return val1 in ("1", "true", "yes", "on") or val2 in ("1", "true", "yes", "on")


def is_erp_inbound_enabled() -> bool:
    return is_erp_events_enabled()


def get_erp_events_hmac_keys() -> dict[str, str]:
    """Parse dedicated events HMAC keys: 'kid1:secret1,kid2:secret2'."""
    raw = (
        os.environ.get(ENV_EVENTS_HMAC_KEYS)
        or os.environ.get(ENV_SYNC_HMAC_KEYS)
        or ""
    ).strip()
    keys: dict[str, str] = {}
    if not raw:
        return keys
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        kid, secret = pair.split(":", 1)
        kid = kid.strip()
        secret = secret.strip()
        if kid and len(secret) >= 32:
            keys[kid] = secret
    return keys


def get_erp_hmac_keys() -> dict[str, str]:
    return get_erp_events_hmac_keys()


def ensure_erp_events_schema(cur: Any) -> None:
    """Idempotently ensure outbox tables and indexes exist in Postgres."""
    cur.execute("""
    CREATE TABLE IF NOT EXISTS erp_inbound_events (
        id UUID PRIMARY KEY,
        event_type TEXT NOT NULL,
        idempotency_key TEXT NOT NULL UNIQUE,
        occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        entity_ref TEXT,
        schema_version INT NOT NULL DEFAULT 1,
        payload JSONB NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        attempts INT NOT NULL DEFAULT 0,
        last_error TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        acked_at TIMESTAMPTZ,
        seq BIGSERIAL
    );
    CREATE INDEX IF NOT EXISTS erp_inbound_events_status_seq_idx
        ON erp_inbound_events (status, seq);
    CREATE INDEX IF NOT EXISTS erp_inbound_events_created_at_idx
        ON erp_inbound_events (created_at);
    CREATE INDEX IF NOT EXISTS erp_inbound_events_type_created_idx
        ON erp_inbound_events (event_type, created_at);

    CREATE TABLE IF NOT EXISTS erp_inbound_nonces (
        key_id TEXT NOT NULL,
        nonce TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (key_id, nonce)
    );
    CREATE INDEX IF NOT EXISTS erp_inbound_nonces_created_at_idx
        ON erp_inbound_nonces (created_at);
    """)


def check_and_burn_nonce(cur: Any, key_id: str, nonce: str) -> bool:
    """Validate nonce length and record single-use in PostgreSQL (IN-03)."""
    if not (16 <= len(nonce) <= 128):
        return False

    if cur is not None:
        try:
            # Purge nonces older than 10 minutes (600s)
            cur.execute("DELETE FROM erp_inbound_nonces WHERE created_at < NOW() - INTERVAL '600 seconds'")
            cur.execute(
                """
                INSERT INTO erp_inbound_nonces (key_id, nonce, created_at)
                VALUES (%s, %s, NOW())
                """,
                (key_id, nonce),
            )
            return True
        except Exception as e:
            log.warning("DB nonce replay or conflict detected: %s", e)
            return False
    return False


def enqueue_event(
    cur: Any,
    event_type: str,
    entity_ref: str | None = None,
    payload: dict[str, Any] | None = None,
    *,
    idempotency_key: str | None = None,
    occurred_at: datetime | None = None,
    **kwargs: Any,
) -> str | None:
    """Enqueue an event into erp_inbound_events.

    Outbox is written in the same transaction as the business write.
    Writes continue even when ERP_EVENTS_ENABLED=0 (Tech Lead locked requirement).
    Enforces payload hygiene (IN-12) and per-type daily cap (Security §3).
    """
    if payload is None:
        payload = kwargs.get("payload") or {}
    if entity_ref is None:
        entity_ref = kwargs.get("entity_ref")

    canonical_type = CANONICAL_EVENT_TYPES.get(event_type, event_type)
    if canonical_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"Event type '{event_type}' is not in the allow-list.")
    event_type = canonical_type

    _assert_no_forbidden_pii(payload)

    # Per-type daily outbox cap (e.g. 500 contact/quote events/day) to prevent floods
    if any(k in event_type for k in ("inquiry", "contact", "quote")):
        cur.execute(
            """
            SELECT COUNT(*) AS cnt FROM erp_inbound_events
            WHERE event_type = %s AND created_at > NOW() - INTERVAL '1 day'
            """,
            (event_type,),
        )
        row = cur.fetchone()
        cnt = row["cnt"] if row and isinstance(row, dict) else (row[0] if row else 0)
        if cnt >= 500:
            log.warning("ERP outbox cap reached for %s (count=%s); dropping overflow", event_type, cnt)
            return None

    event_id = str(uuid.uuid4())
    ts = occurred_at or datetime.now(timezone.utc)
    idemp_key = idempotency_key or f"{event_type}:{entity_ref or event_id}:{event_id}"
    payload_str = json.dumps(payload, ensure_ascii=False, default=str)

    cur.execute(
        """
        INSERT INTO erp_inbound_events (
            id, event_type, idempotency_key, occurred_at, entity_ref, schema_version,
            payload, status, created_at
        ) VALUES (
            %s, %s, %s, %s, %s, 1, %s::jsonb, 'pending', NOW()
        )
        ON CONFLICT (idempotency_key) DO NOTHING
        RETURNING id
        """,
        (event_id, event_type, idemp_key, ts, entity_ref, payload_str),
    )
    res = cur.fetchone()
    if res:
        # Log event_id and type ONLY; NEVER log payload body or customer PII (IN-14)
        log.info("Enqueued ERP event id=%s type=%s", event_id, event_type)
        return event_id
    return None


enqueue_erp_event = enqueue_event


def verify_erp_request(request: Request, body_bytes: bytes, cur: Any = None) -> tuple[bool, str | None, int]:
    """Verify request HMAC signature, timestamp skew, replay nonce, and rate limit.

    Returns: (is_valid, key_id, status_code)
    """
    key_id = request.headers.get(HEADER_KEY_ID, "").strip()
    timestamp = request.headers.get(HEADER_TIMESTAMP, "").strip()
    nonce = request.headers.get(HEADER_NONCE, "").strip()
    signature = request.headers.get(HEADER_SIGNATURE, "").strip().lower()

    def _record_bad_sig() -> tuple[bool, str | None, int]:
        try:
            if not enforce_rate_limit(request, action="erp-events-badsig", limit=20, window_seconds=600):
                return False, None, 429
        except Exception:
            pass
        return False, None, 401

    if not key_id or not timestamp or not nonce or not signature:
        return _record_bad_sig()

    if not (16 <= len(nonce) <= 128):
        return _record_bad_sig()

    keys = get_erp_events_hmac_keys()
    if not keys or key_id not in keys:
        return _record_bad_sig()
    secret = keys[key_id]

    try:
        ts = int(timestamp)
    except ValueError:
        return _record_bad_sig()

    now_unix = int(datetime.now(timezone.utc).timestamp())
    if abs(now_unix - ts) > MAX_CLOCK_SKEW_SEC:
        return _record_bad_sig()

    path = request.url.path
    query = request.url.query
    path_and_query = f"{path}?{query}" if query else path

    canonical = build_canonical_string(request.method, path_and_query, timestamp, nonce, body_bytes)
    computed_sig = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest().lower()

    if not hmac.compare_digest(computed_sig, signature):
        return _record_bad_sig()

    # Check and consume nonce in DB (IN-03)
    if not check_and_burn_nonce(cur, key_id, nonce):
        return _record_bad_sig()

    # Throttle valid pull/ack requests: 120 req / 10 min per key and per IP (Security §3)
    try:
        if not enforce_rate_limit(request, action="erp-events", limit=120, window_seconds=600, subject=key_id):
            return False, key_id, 429
    except Exception:
        pass

    return True, key_id, 200


def purge_old_events(cur: Any, acked_retention_days: int = 30, unacked_retention_days: int = 90) -> tuple[int, int]:
    """Purge acked rows older than 30d, unacked older than 90d (Security §6)."""
    cur.execute(
        """
        DELETE FROM erp_inbound_events
        WHERE status = 'acked' AND acked_at < NOW() - (%s || ' days')::INTERVAL
        """,
        (acked_retention_days,),
    )
    acked_count = getattr(cur, "rowcount", 0)

    cur.execute(
        """
        DELETE FROM erp_inbound_events
        WHERE status = 'pending' AND created_at < NOW() - (%s || ' days')::INTERVAL
        """,
        (unacked_retention_days,),
    )
    unacked_count = getattr(cur, "rowcount", 0)

    log.info("Purged ERP events: acked=%s unacked=%s", acked_count, unacked_count)
    return acked_count, unacked_count
