"""App configuration and route registry."""

from config.routes import ALL_PAGES, PAGE_404, STANDALONE_PAGES, PageMeta
from config.settings import ROOT, Settings, settings

__all__ = [
    "ALL_PAGES",
    "PAGE_404",
    "PageMeta",
    "ROOT",
    "STANDALONE_PAGES",
    "Settings",
    "settings",
]
