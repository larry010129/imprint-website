"""FastAPI app: static Diamond v3 site + GET /api/bot-gold."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from server.bot_gold import fetch_bot_gold_quote

ROOT = Path(__file__).resolve().parent.parent


def _startup_banner() -> None:
    import os

    port = os.environ.get("PORT", "8080")
    is_render = os.environ.get("RENDER") == "true" or bool(os.environ.get("RENDER_SERVICE_ID"))
    base = os.environ.get("RENDER_EXTERNAL_URL") or f"http://127.0.0.1:{port}"
    if is_render and not base.startswith("http"):
        base = f"https://{base}"
    print("")
    print("  Diamond v3 on Render" if is_render else "  Diamond v3 local dev")
    print(f"  Site: {base}/")
    print(f"  Gold: {base}/gold-price.html")
    print(f"  API:  {base}/api/bot-gold")
    print("")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _startup_banner()
    yield


app = FastAPI(title="Imprint Diamond", docs_url=None, redoc_url=None, lifespan=lifespan)


@app.get("/api/bot-gold")
async def bot_gold() -> JSONResponse:
    try:
        payload = await fetch_bot_gold_quote()
    except Exception as err:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(err)) from err
    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "no-store"},
    )


app.mount("/", StaticFiles(directory=str(ROOT), html=True), name="site")
