"""Backward-compatible re-export — prefer `from config.settings import settings`."""

from config.settings import ROOT, Settings, settings

__all__ = ["ROOT", "Settings", "settings"]
