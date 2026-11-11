"""Shared pytest fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _clear_process_caches():
    """Process-local caches must not leak state between tests."""
    from app.auth import invalidate_user_cache

    invalidate_user_cache()
    yield
    invalidate_user_cache()
