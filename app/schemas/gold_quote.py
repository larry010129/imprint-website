"""Response schema for GET /api/bot-gold."""

from __future__ import annotations

from pydantic import BaseModel


class GoldQuoteDetail(BaseModel):
    available: bool
    sell: float
    source: str
    bot_posted_at: str | None
    fetched_at: str
    fetched_at_display: str
    is_stale: bool
    source_url: str


class GoldQuote(BaseModel):
    refreshed: bool
    quote: GoldQuoteDetail
    alloyRates: dict[str, float]
