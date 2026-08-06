"""Focused tests for gold scrape interval env + shared lock throttle."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app import gold_scrape_job as job


@pytest.fixture(autouse=True)
def _reset_scrape_throttle() -> None:
    job._last_scrape_mono = 0.0
    yield
    job._last_scrape_mono = 0.0


def test_scrape_interval_sec_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOLD_SCRAPE_INTERVAL_SEC", raising=False)
    assert job.scrape_interval_sec() == job.DEFAULT_INTERVAL_SEC


def test_scrape_interval_sec_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOLD_SCRAPE_INTERVAL_SEC", "120")
    assert job.scrape_interval_sec() == 120


def test_scrape_interval_sec_invalid_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOLD_SCRAPE_INTERVAL_SEC", "nope")
    assert job.scrape_interval_sec() == job.DEFAULT_INTERVAL_SEC


def test_scrape_interval_sec_min_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOLD_SCRAPE_INTERVAL_SEC", "0")
    assert job.scrape_interval_sec() == 1


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", True),
        ("true", True),
        ("0", False),
        ("false", False),
        ("off", False),
        ("no", False),
    ],
)
def test_scrape_on_startup_enabled(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool
) -> None:
    monkeypatch.setenv("GOLD_SCRAPE_ON_STARTUP", raw)
    assert job.scrape_on_startup_enabled() is expected


def test_scrape_and_persist_throttles_within_min_interval() -> None:
    payload = {
        "quote": {"sell": 4000.0, "source": "allbeauty"},
        "metals": {"XAU": 4000.0, "XPT": 1000.0, "XAG": 60.0},
    }
    fetch = AsyncMock(return_value=payload)
    with (
        patch.object(job, "fetch_bot_gold_quote", fetch),
        patch.object(job, "persist_gold_price_cache") as persist,
        patch.object(job, "invalidate_bot_gold_memory_cache"),
    ):
        first = asyncio.run(job.scrape_and_persist_gold(force=True))
        second = asyncio.run(job.scrape_and_persist_gold(force=True))
    assert first is payload
    assert second is None
    assert fetch.await_count == 1
    persist.assert_called_once()
