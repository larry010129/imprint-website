"""CMS admin schema ensure must stay out of the hot create path."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import app.controllers.cms_admin_controller as cms_admin


def test_ensure_all_runs_seed_once_per_process():
    cms_admin._CMS_SCHEMA_READY = False
    cur = MagicMock()
    with (
        patch("app.cms_pages.ensure_cms_pages_schema") as ensure_pages,
        patch("app.cms_copy_slots.ensure_page_copy_slots_schema") as ensure_slots,
        patch("app.cms_media.ensure_cms_media_schema") as ensure_media,
        patch("app.cms_copy_slots.seed_page_copy_slots") as seed,
        patch("app.cms_seed.remove_legacy_seeded_pages") as remove_legacy,
    ):
        cms_admin._ensure_all(cur)
        cms_admin._ensure_all(cur)
        assert ensure_pages.call_count == 1
        assert ensure_slots.call_count == 1
        assert ensure_media.call_count == 1
        assert seed.call_count == 1
        assert remove_legacy.call_count == 1
        assert cms_admin._CMS_SCHEMA_READY is True
