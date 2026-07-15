"""API routes — JSON endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.bot_gold import fetch_bot_gold_quote
from app.schemas.gold_quote import GoldQuote

router = APIRouter(tags=["api"])


@router.get("/bot-gold", response_model=GoldQuote)
async def bot_gold() -> JSONResponse:
    try:
        payload = await fetch_bot_gold_quote()
    except Exception as err:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(err)) from err
    return JSONResponse(
        content=GoldQuote.model_validate(payload).model_dump(),
        headers={"Cache-Control": "no-store"},
    )
