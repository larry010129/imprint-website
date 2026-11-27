"""Foreign-currency price estimates (no network)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import fx_rates

GOOD = {
    "result": "success",
    "base_code": "TWD",
    "conversion_rates": {"TWD": 1, "USD": 0.03, "JPY": 4.8, "KRW": 40.7},
}


@pytest.fixture(autouse=True)
def _fresh_cache(monkeypatch):
    monkeypatch.setattr(fx_rates, "_rates", None)
    monkeypatch.setattr(fx_rates, "_fetched_at", 0.0)
    monkeypatch.setattr(fx_rates, "_next_try", 0.0)
    monkeypatch.setenv("EXCHANGE_RATE_API_KEY", "test-key")


def test_parse_keeps_only_the_wanted_currencies() -> None:
    assert fx_rates.parse_rates(GOOD) == {"USD": 0.03, "JPY": 4.8, "KRW": 40.7}


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {**GOOD, "result": "error"},
        {**GOOD, "base_code": "USD"},
        {**GOOD, "conversion_rates": {"USD": 0.03, "JPY": 4.8}},
        {**GOOD, "conversion_rates": {"USD": 0.03, "JPY": 0, "KRW": 40.7}},
        {**GOOD, "conversion_rates": {"USD": "0.03", "JPY": 4.8, "KRW": 40.7}},
    ],
)
def test_parse_rejects_bad_payloads(payload) -> None:
    assert fx_rates.parse_rates(payload) is None


def test_rates_are_cached_and_survive_a_failed_refresh(monkeypatch) -> None:
    clock = [1000.0]
    calls = []

    def download(key):
        calls.append(key)
        if len(calls) > 1:
            raise OSError("offline")
        return GOOD

    monkeypatch.setattr(fx_rates.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(fx_rates, "_download", download)

    assert fx_rates.get_rates()["JPY"] == 4.8
    assert fx_rates.get_rates()["JPY"] == 4.8
    assert len(calls) == 1

    clock[0] += 13 * 60 * 60  # refresh fails: keep the last good rates
    assert fx_rates.get_rates()["JPY"] == 4.8
    assert len(calls) == 2

    clock[0] += 4 * 24 * 60 * 60  # too old: hide the estimates
    assert fx_rates.get_rates() is None


def test_no_key_means_no_request_and_no_rates(monkeypatch) -> None:
    def download(key):
        raise AssertionError("must not call the service without a key")

    monkeypatch.setenv("EXCHANGE_RATE_API_KEY", "")
    monkeypatch.setattr(fx_rates, "_download", download)
    assert fx_rates.get_rates() is None


def test_key_is_sent_in_a_header_not_the_address(monkeypatch) -> None:
    seen = []

    def fake_urlopen(request, timeout):
        seen.append(request)
        raise OSError("stop here")

    monkeypatch.setattr(fx_rates, "urlopen", fake_urlopen)
    assert fx_rates.get_rates() is None
    assert seen[0].get_header("Authorization") == "Bearer test-key"
    assert "test-key" not in seen[0].full_url


def test_rates_route(monkeypatch) -> None:
    from main import app

    client = TestClient(app)
    monkeypatch.setattr(fx_rates, "get_rates", lambda: {"JPY": 4.8})
    response = client.get("/i18n/fx.json")
    assert response.json() == {"base": "TWD", "rates": {"JPY": 4.8}}
    assert response.headers["cache-control"] == "public, max-age=3600"

    monkeypatch.setattr(fx_rates, "get_rates", lambda: None)
    response = client.get("/i18n/fx.json")
    assert response.json() == {"base": "TWD", "rates": None}
    assert response.headers["cache-control"] == "no-store"
