"""Shared pytest fixtures."""

import os

import pytest

# Many test files load .env, which holds the real staff webhook. Blank it before
# they are imported (load_dotenv never overrides an existing key) so no test can
# post there; tests that need a URL set a fake one themselves.
os.environ["DISCORD_BOOKING_WEBHOOK_URL"] = ""
os.environ["DISCORD_REPORT_WEBHOOK_URL"] = ""


@pytest.fixture(autouse=True)
def _clear_process_caches():
    """Process-local caches must not leak state between tests."""
    from app.auth import invalidate_user_cache

    invalidate_user_cache()
    yield
    invalidate_user_cache()
