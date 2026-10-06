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


# ── the protected page itself (/admin/release-notes) ────────────────────

def _page_client(monkeypatch, *, admin=True, user_id=ADMIN):
    from fastapi.testclient import TestClient

    from app import create_app

    monkeypatch.setattr("app.auth.get_user_id", lambda request: user_id)
    monkeypatch.setattr("app.auth.request_is_admin", lambda request: admin)
    # No lifespan (no `with`): nothing touches the database.
    return TestClient(create_app(), follow_redirects=False)


def _is_prompt_page(resp) -> bool:
    """The code prompt — and nothing from the protected editor."""
    return (
        resp.status_code == 200
        and 'id="unlockForm"' in resp.text
        and "輸入通行碼" in resp.text
        and "data-rn-tab" not in resp.text
        and "admin-nav-visibility-root" not in resp.text
        and resp.headers["cache-control"] == "no-store"
    )


def test_admin_without_the_password_gets_the_code_prompt(monkeypatch):
    client = _page_client(monkeypatch)
    for url in ("/admin/release-notes", "/admin/release-notes?x=1"):
        assert _is_prompt_page(client.get(url))


def test_another_admins_unlock_only_gets_the_prompt(monkeypatch):
    client = _page_client(monkeypatch, user_id="admin-2")
    client.cookies.set(rn.UNLOCK_COOKIE_NAME, rn.sign_unlock(ADMIN))  # signed for admin-1
    assert _is_prompt_page(client.get("/admin/release-notes"))


def test_expired_or_garbage_unlock_gets_the_prompt(monkeypatch):
    client = _page_client(monkeypatch)
    client.cookies.set(rn.UNLOCK_COOKIE_NAME, "not-a-token")
    assert _is_prompt_page(client.get("/admin/release-notes"))


def test_protected_page_opens_only_with_own_unlock(monkeypatch):
    client = _page_client(monkeypatch)
    client.cookies.set(rn.UNLOCK_COOKIE_NAME, rn.sign_unlock(ADMIN))
    resp = client.get("/admin/release-notes")
    assert resp.status_code == 200 and "data-rn-tab=\"plugins\"" in resp.text
    assert 'id="unlockForm"' not in resp.text
    assert resp.headers["cache-control"] == "no-store"


def test_protected_page_sends_non_admins_to_login(monkeypatch):
    client = _page_client(monkeypatch, admin=False)
    resp = client.get("/admin/release-notes")
    assert resp.status_code == 302 and resp.headers["location"].startswith("/login")


def test_old_plugin_page_url_now_redirects_into_the_protected_page(monkeypatch):
    client = _page_client(monkeypatch)
    resp = client.get("/admin/plugins")
    assert resp.status_code == 302 and resp.headers["location"] == "/admin/release-notes#plugins"


# ── every visit asks for the code: short unlock, kept alive, locked on leave ──

def test_unlock_window_is_short():
    assert rn.UNLOCK_MINUTES == 5


def test_unlock_cookie_is_short_lived(monkeypatch):
    monkeypatch.setattr(rnc, "_require_admin", lambda r: ADMIN)
    monkeypatch.setattr(rn, "release_notes_password", lambda: "abc123")
    monkeypatch.setattr(rnc, "enforce_rate_limit", lambda *a, **k: True)
    resp = asyncio.run(rnc.unlock(_request({"code": "abc123"})))
    cookie = resp.headers["set-cookie"].lower()
    assert "max-age=300" in cookie and "httponly" in cookie


def test_keepalive_only_renews_an_existing_unlock(monkeypatch):
    monkeypatch.setattr(rnc, "_require_admin", lambda r: ADMIN)
    locked = asyncio.run(rnc.keepalive(_request()))
    assert locked.status_code == 403 and "set-cookie" not in locked.headers
    other = asyncio.run(rnc.keepalive(_request(unlocked_for="someone-else")))
    assert other.status_code == 403
    renewed = asyncio.run(rnc.keepalive(_request(unlocked_for=ADMIN)))
    assert renewed.status_code == 200
    assert "max-age=300" in renewed.headers["set-cookie"].lower()


def test_lock_clears_the_unlock_cookie(monkeypatch):
    monkeypatch.setattr(rnc, "_require_admin", lambda r: ADMIN)
    resp = asyncio.run(rnc.lock(_request(unlocked_for=ADMIN)))
    assert resp.status_code == 200
    cookie = resp.headers["set-cookie"].lower()
    assert rn.UNLOCK_COOKIE_NAME in cookie
    assert "max-age=0" in cookie or "expires=thu, 01 jan 1970" in cookie

    def deny(_r):
        raise HTTPException(status_code=401, detail="no")

    monkeypatch.setattr(rnc, "_require_admin", deny)
    with pytest.raises(HTTPException):
        asyncio.run(rnc.lock(_request()))
    with pytest.raises(HTTPException):
        asyncio.run(rnc.keepalive(_request()))


def test_protected_page_loads_the_lock_on_leave_script(monkeypatch):
    client = _page_client(monkeypatch)
    client.cookies.set(rn.UNLOCK_COOKIE_NAME, rn.sign_unlock(ADMIN))
    assert "/js/admin-lock-on-leave.js" in client.get("/admin/release-notes").text
