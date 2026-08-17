"""Focused tests for gold scrape interval env + shared lock throttle."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app import gold_scrape_job as job

_ROOT = Path(__file__).resolve().parents[1]


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


def test_scrape_on_startup_default_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOLD_SCRAPE_ON_STARTUP", raising=False)
    assert job.scrape_on_startup_enabled() is True


def test_render_skips_startup_scrape_and_raises_gunicorn_timeout() -> None:
    start = (_ROOT / "scripts" / "render-start.sh").read_text(encoding="utf-8")
    assert "--timeout 120" in start
    assert '0.0.0.0:${PORT:-8080}' in start
    yaml = (_ROOT / "render.yaml").read_text(encoding="utf-8")
    idx = yaml.index("key: GOLD_SCRAPE_ON_STARTUP")
    assert 'value: "0"' in yaml[idx : idx + 80]


def test_gold_scrape_loop_skips_startup_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOLD_SCRAPE_ON_STARTUP", "0")
    monkeypatch.setenv("GOLD_SCRAPE_INTERVAL_SEC", "100")
    sleeps: list[float] = []

    async def fake_sleep(sec: float) -> None:
        sleeps.append(sec)
        raise asyncio.CancelledError

    scrape = AsyncMock()

    async def run() -> None:
        with (
            patch.object(job, "scrape_and_persist_gold", scrape),
            patch.object(asyncio, "sleep", fake_sleep),
        ):
            with pytest.raises(asyncio.CancelledError):
                await job.gold_scrape_loop()

    asyncio.run(run())
    assert sleeps == [100]
    scrape.assert_not_awaited()


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
