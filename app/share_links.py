"""Short share links for the calculator's 分享摘要 (``/s/K7M29QXA``).

The calculator used to put the whole configuration in the URL (hundreds of
characters). Now the server stores the configuration once and hands out a short
random code. Same configuration -> same code, so pressing 分享 repeatedly does
not fill the table. Only whitelisted fields are kept (no price: the share page
asks the server to price it).
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import secrets
from urllib.parse import urlparse

import psycopg

# A-Z without I and O, plus 2-9: nothing that looks like another character.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
_CODE_RE = re.compile(r"^[A-Za-z0-9]{6,12}$")
MAX_BODY_BYTES = 8192
_MAX_INSERT_TRIES = 6
# A link nobody opens for a year is deleted (re-sharing the same selection just
# makes a new code). Opening a link renews it, written at most once a day.
SHARE_LINK_TTL_DAYS = 365
TOUCH_INTERVAL_DAYS = 1
# Cleanup piggybacks on link creation (the table only grows then): about 1 in 50
# creations trims a batch, so no scheduler is needed.
CLEANUP_CHANCE = 0.02
CLEANUP_BATCH = 500

# field -> (kind, max length / limit)
_FIELDS: dict[str, tuple[str, int]] = {
    "category": ("str", 40),
    "type": ("str", 80),
    "gold": ("str", 16),
    "color": ("str", 24),
    "carat": ("strnum", 16),
    "ringSize": ("strnum", 16),
    "engravingBand": ("str", 60),
    "engravingRemark": ("str", 60),
    "engravingGirdle": ("str", 60),
    "lengthCm": ("num", 0),
    "includeChain": ("bool", 0),
    "chainProductId": ("str", 80),
    "chainGold": ("str", 16),
    "chainColor": ("str", 24),
    "chainThickness": ("str", 16),
    "chainLength": ("num", 0),
    "diamondKind": ("str", 24),
    "fancyColor": ("str", 32),
    "stoneCount": ("num", 0),
    "diamondShape": ("str", 32),
    "quantity": ("num", 0),
    "summaryZh": ("str", 80),
    "styleKey": ("str", 80),
    "defaultColor": ("str", 24),
    "diamondColor": ("str", 32),
    "previewImage": ("url", 600),
    "previewChainImage": ("url", 600),
}
_REQUIRED = ("category", "type")


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def is_valid_code(code: str | None) -> bool:
    return bool(code and _CODE_RE.fullmatch(code))


def _allowed_hosts() -> set[str]:
    from config.settings import settings

    hosts: set[str] = set()
    for raw in (settings.supabase_url, settings.public_base_url):
        host = (urlparse(raw or "").hostname or "").lower()
        if host:
            hosts.add(host)
    return hosts


def _safe_url(value: str, limit: int) -> str | None:
    """Our own media only: a site-relative path, or https on our own hosts.

    The share page shows this image, and anyone can create a link — so it must
    not be a way to show arbitrary pictures under our domain."""
    text = value.strip()
    if not text or len(text) > limit:
        return None
    if text.startswith("/") and not text.startswith("//"):
        return text
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        return None
    if host in _allowed_hosts() or host.endswith(".supabase.co"):
        return text
    return None


def sanitize_config(raw) -> dict | None:
    """Keep only known fields with plain, bounded values; None if unusable."""
    if not isinstance(raw, dict):
        return None
    clean: dict = {}
    for key, (kind, limit) in _FIELDS.items():
        if key not in raw:
            continue
        value = raw[key]
        if value is None:
            clean[key] = None
        elif kind == "bool":
            if isinstance(value, bool):
                clean[key] = value
        elif kind == "num":
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and abs(value) <= 1_000_000:
                clean[key] = value
        elif kind == "strnum":
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                if math.isfinite(value) and abs(value) <= 1_000_000:
                    clean[key] = value
            elif isinstance(value, str) and len(value.strip()) <= limit:
                clean[key] = value.strip()
        elif kind == "str":
            if isinstance(value, str) and len(value.strip()) <= limit:
                clean[key] = value.strip()
        elif kind == "url":
            if isinstance(value, str):
                safe = _safe_url(value, limit)
                if safe:
                    clean[key] = safe
    if any(not clean.get(field) for field in _REQUIRED):
        return None
    return clean


def config_hash(config: dict) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ensure_share_links_schema(cur) -> None:
    cur.execute(
        """
        create table if not exists share_links (
          code text primary key,
          config jsonb not null,
          config_hash text not null unique,
          created_at timestamptz not null default now()
        )
        """
    )
    cur.execute("alter table share_links enable row level security")
    # Expiry: when a link was last opened (null = never since it was made).
    cur.execute("alter table share_links add column if not exists last_opened_at timestamptz")
    cur.execute(
        """
        create index if not exists share_links_last_seen_idx
          on share_links ((coalesce(last_opened_at, created_at)))
        """
    )


def touch_link(cur, code: str) -> None:
    """Remember that a link was opened, at most once a day per link."""
    if not is_valid_code(code):
        return
    cur.execute(
        """
        update share_links set last_opened_at = now()
        where code = %s
          and (last_opened_at is null
               or last_opened_at < now() - make_interval(days => %s))
        """,
        (code.upper(), TOUCH_INTERVAL_DAYS),
    )


def should_cleanup(rand=random.random) -> bool:
    return rand() < CLEANUP_CHANCE


def delete_expired(cur) -> int:
    """Delete up to CLEANUP_BATCH links nobody has opened for SHARE_LINK_TTL_DAYS."""
    cur.execute(
        """
        delete from share_links where code in (
          select code from share_links
          where coalesce(last_opened_at, created_at) < now() - make_interval(days => %s)
          limit %s
        )
        """,
        (SHARE_LINK_TTL_DAYS, CLEANUP_BATCH),
    )
    return int(cur.rowcount or 0)


def get_or_create_code(cur, config: dict) -> str:
    """Code for this configuration: the existing one, or a new random one."""
    digest = config_hash(config)
    cur.execute("select code from share_links where config_hash = %s", (digest,))
    row = cur.fetchone()
    if row:
        return row["code"]
    from psycopg.types.json import Jsonb

    for _ in range(_MAX_INSERT_TRIES):
        code = generate_code()
        try:
            cur.execute(
                """
                insert into share_links (code, config, config_hash) values (%s, %s, %s)
                on conflict (config_hash) do nothing
                returning code
                """,
                (code, Jsonb(config), digest),
            )
        except psycopg.errors.UniqueViolation:
            continue  # the random code was taken: draw another
        row = cur.fetchone()
        if row:
            return row["code"]
        # Same configuration saved by someone else a moment ago.
        cur.execute("select code from share_links where config_hash = %s", (digest,))
        existing = cur.fetchone()
        if existing:
            return existing["code"]
    raise RuntimeError("could not allocate a share code")


def fetch_config(cur, code: str) -> dict | None:
    if not is_valid_code(code):
        return None
    cur.execute("select config from share_links where code = %s", (code.upper(),))
    row = cur.fetchone()
    if not row:
        return None
    config = row["config"]
    return config if isinstance(config, dict) else None
