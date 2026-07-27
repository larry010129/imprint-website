"""Google People API — optional phone/address import after GIS sign-in."""

from __future__ import annotations

import re

import requests

PHONE_SCOPE = "https://www.googleapis.com/auth/user.phonenumbers.read"
ADDRESS_SCOPE = "https://www.googleapis.com/auth/user.addresses.read"
REQUIRED_SCOPES = {PHONE_SCOPE, ADDRESS_SCOPE}

TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
PEOPLE_ME_URL = "https://people.googleapis.com/v1/people/me"


def verify_access_token(access_token: str, *, expected_sub: str, expected_email: str) -> dict | None:
    """Validate access token belongs to the logged-in Google-linked user."""
    try:
        resp = requests.get(TOKENINFO_URL, params={"access_token": access_token}, timeout=10)
        if resp.status_code != 200:
            return None
        info = resp.json()
    except Exception:
        return None

    if (info.get("email") or "").strip().lower() != expected_email.strip().lower():
        return None
    if info.get("sub") != expected_sub:
        return None

    scopes = set((info.get("scope") or "").split())
    if not REQUIRED_SCOPES.issubset(scopes):
        return None

    return info


def fetch_people_profile(access_token: str) -> dict | None:
    try:
        resp = requests.get(
            PEOPLE_ME_URL,
            params={"personFields": "phoneNumbers,addresses"},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def parse_phone(people: dict) -> str | None:
    numbers = people.get("phoneNumbers") or []
    if not numbers:
        return None

    preferred: str | None = None
    for entry in numbers:
        val = (entry.get("value") or "").strip()
        if not val:
            continue
        if (entry.get("type") or "").lower() == "mobile":
            preferred = val
            break
        if preferred is None:
            preferred = val

    if not preferred:
        return None

    digits = re.sub(r"\D", "", preferred)
    if digits.startswith("886") and len(digits) >= 11:
        digits = "0" + digits[3:]
    return digits or preferred


def parse_address(people: dict) -> dict[str, str | None]:
    addresses = people.get("addresses") or []
    if not addresses:
        return {"shipping_postal": None, "shipping_city": None, "shipping_address": None}

    chosen = addresses[0]
    for entry in addresses:
        if (entry.get("type") or "").lower() in ("home", "work"):
            chosen = entry
            if (entry.get("type") or "").lower() == "home":
                break

    postal = (chosen.get("postalCode") or "").strip() or None

    city_parts: list[str] = []
    for key in ("locality", "administrativeArea", "city", "region"):
        part = (chosen.get(key) or "").strip()
        if part and part not in city_parts:
            city_parts.append(part)

    street = (chosen.get("streetAddress") or "").strip()
    formatted = (chosen.get("formattedValue") or "").strip()
    shipping_address = street or formatted or None
    shipping_city = "".join(city_parts) if city_parts else None

    return {
        "shipping_postal": postal,
        "shipping_city": shipping_city,
        "shipping_address": shipping_address,
    }


def merge_into_profile(
    existing: dict | None,
    phone: str | None,
    address: dict[str, str | None],
) -> dict[str, str]:
    """Return only fields that are empty on the existing profile."""
    existing = existing or {}
    out: dict[str, str] = {}

    if phone and not str(existing.get("phone") or "").strip():
        out["phone"] = phone

    for key in ("shipping_postal", "shipping_city", "shipping_address"):
        val = address.get(key)
        if val and not str(existing.get(key) or "").strip():
            out[key] = val

    return out
