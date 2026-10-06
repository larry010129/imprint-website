"""Plugin switches behind the admin password (no DB, no network)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app import admin_plugins as plugins
from app import consult_bookings as cb
from app import release_notes as rn
from app.controllers import booking_controller as bc
from app.controllers import plugin_controller as pc
from app.controllers import release_notes_controller as rnc

ADMIN = "admin-1"


@pytest.fixture(autouse=True)
def _kv(monkeypatch):
    """In-memory cms_kv + a JWT secret so unlock cookies can be signed."""
    store: dict = {}
    monkeypatch.setattr("app.cms_kv_store.kv_get", lambda key: store.get(key))
    monkeypatch.setattr("app.cms_kv_store.kv_set", lambda key, value: store.__setitem__(key, dict(value)))
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    return store


def _request(body=None, unlocked_for=None):
    req = MagicMock()

    async def _json():
        return body

    req.json = _json
    req.cookies = {rn.UNLOCK_COOKIE_NAME: rn.sign_unlock(unlocked_for)} if unlocked_for else {}
    return req


def _body(resp):
    return json.loads(resp.body)


# ── state store ──────────────────────────────────────────────────────────

def test_booking_defaults_to_on_and_normalises():
    assert plugins.get_states() == {"booking": "on"}
    assert plugins.normalize_states({"booking": "weird", "ghost": "on"}) == {"booking": "on"}
    assert plugins.is_on("booking") is True


def test_lifecycle_transitions():
    assert plugins.set_state("booking", "off") == ("on", "off")
    assert plugins.is_on("booking") is False
    assert plugins.set_state("booking", "disabled") == ("off", "disabled")
    with pytest.raises(plugins.PluginError):  # disabled -> on must go through off
        plugins.set_state("booking", "on")
    assert plugins.set_state("booking", "off") == ("disabled", "off")
    assert plugins.set_state("booking", "on") == ("off", "on")
    assert plugins.set_state("booking", "on") == ("on", "on")  # no-op


def test_rejects_unknown_slug_and_state():
    with pytest.raises(plugins.PluginError):
        plugins.set_state("ghost", "on")
    with pytest.raises(plugins.PluginError):
        plugins.set_state("booking", "maybe")


# ── API: viewing is open to admins, changing needs the password ─────────

def test_get_requires_admin_but_not_password(monkeypatch):
    monkeypatch.setattr(pc, "_require_admin", lambda r: ADMIN)
    out = pc.plugins_get(_request())
    assert out["plugins"] == {"booking": "on"}
    assert out["labels"]["booking"] == "預約諮詢日曆"

    def deny(_r):
        raise HTTPException(status_code=401, detail="no")

    monkeypatch.setattr(pc, "_require_admin", deny)
    with pytest.raises(HTTPException) as err:
        pc.plugins_get(_request())
    assert err.value.status_code == 401
    with pytest.raises(HTTPException):
        asyncio.run(pc.plugins_set(_request({"state": "off"}), "booking"))


def test_change_without_password_is_refused_and_state_unchanged(monkeypatch, _kv):
    monkeypatch.setattr(pc, "_require_admin", lambda r: ADMIN)
    resp = asyncio.run(pc.plugins_set(_request({"state": "off"}), "booking"))
    assert resp.status_code == 403 and _body(resp)["error"] == "unlock required"
    # a cookie signed for a different admin does not unlock this one
    other = asyncio.run(pc.plugins_set(_request({"state": "off"}, unlocked_for="someone-else"), "booking"))
    assert other.status_code == 403
    assert plugins.is_on("booking") is True
    assert "admin-plugins" not in _kv


def test_change_with_password_works_and_is_audited(monkeypatch):
    audits = []
    monkeypatch.setattr(pc, "_require_admin", lambda r: ADMIN)
    monkeypatch.setattr(pc, "_audit", lambda admin_id, detail: audits.append((admin_id, detail)))
    out = asyncio.run(pc.plugins_set(_request({"state": "off"}, unlocked_for=ADMIN), "booking"))
    assert out["ok"] is True and out["plugins"] == {"booking": "off"}
    assert audits == [(ADMIN, {"slug": "booking", "from": "on", "to": "off"})]


def test_change_validation_errors(monkeypatch):
    monkeypatch.setattr(pc, "_require_admin", lambda r: ADMIN)
    monkeypatch.setattr(pc, "_audit", lambda *a, **k: None)
    skip = asyncio.run(pc.plugins_set(_request({"state": "disabled"}, unlocked_for=ADMIN), "booking"))
    assert skip["ok"] is True  # on -> disabled shortcut is allowed
    bad_jump = asyncio.run(pc.plugins_set(_request({"state": "on"}, unlocked_for=ADMIN), "booking"))
    assert bad_jump.status_code == 400
    assert asyncio.run(pc.plugins_set(_request({"state": "off"}, unlocked_for=ADMIN), "ghost")).status_code == 404
    assert asyncio.run(pc.plugins_set(_request(None, unlocked_for=ADMIN), "booking")).status_code == 400


# ── a paused plugin is really off ────────────────────────────────────────

def test_booking_admin_routes_blocked_when_not_on(monkeypatch):
    monkeypatch.setattr(bc, "require_admin", lambda r: ADMIN)
    assert bc._require_admin(_request()) == ADMIN
    for state in ("off", "disabled"):
        monkeypatch.setattr(plugins, "is_on", lambda slug: False)
        with pytest.raises(HTTPException) as err:
            bc._require_admin(_request())
        assert err.value.status_code == 403 and err.value.detail == "plugin_disabled"


def test_public_form_falls_back_when_not_on(monkeypatch):
    monkeypatch.setattr(bc, "enforce_rate_limit", lambda *a, **k: True)
    monkeypatch.setattr(plugins, "is_on", lambda slug: False)
    resp = bc.booking_availability(_request())
    assert resp.status_code == 200 and _body(resp) == {"enabled": False}
    assert resp.headers["cache-control"] == "no-store"

    class Cur:
        sql: list = []

        def execute(self, *a, **k):
            self.sql.append(a)

        def fetchall(self):
            return []

    cur = Cur()
    monkeypatch.setattr(cb, "load_settings", lambda: cb.default_settings())
    # Even a slot that would be refused is accepted (and nothing is queried).
    assert cb.check_requested_slots(cur, [("2020-01-01", "上午 10:00～11:00")]) is None
    assert cur.sql == []


# ── hardening of the existing password endpoints ─────────────────────────

def test_nav_visibility_patch_needs_the_password(monkeypatch):
    saved = []
    monkeypatch.setattr(rnc, "_require_admin", lambda r: ADMIN)
    monkeypatch.setattr(rn, "load_store", lambda: {"nav_visibility": {}})
    monkeypatch.setattr(rn, "save_store", lambda store: saved.append(store))
    body = {"visibility": {"booking": False}}
    locked = asyncio.run(rnc.update_nav_visibility(_request(body)))
    assert locked.status_code == 403 and saved == []
    ok = asyncio.run(rnc.update_nav_visibility(_request(body, unlocked_for=ADMIN)))
    assert ok.status_code == 200 and saved and saved[0]["nav_visibility"]["booking"] is False


def test_unlock_is_rate_limited_and_checks_the_code(monkeypatch):
    monkeypatch.setattr(rnc, "_require_admin", lambda r: ADMIN)
    monkeypatch.setattr(rn, "release_notes_password", lambda: "abc123")
    monkeypatch.setattr(rnc, "enforce_rate_limit", lambda *a, **k: False)
    assert asyncio.run(rnc.unlock(_request({"code": "abc123"}))).status_code == 429

    monkeypatch.setattr(rnc, "enforce_rate_limit", lambda *a, **k: True)
    assert asyncio.run(rnc.unlock(_request({"code": "zzz999"}))).status_code == 401
    good = asyncio.run(rnc.unlock(_request({"code": "abc123"})))
    assert good.status_code == 200
    assert rn.UNLOCK_COOKIE_NAME in good.headers.get("set-cookie", "")
