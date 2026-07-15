"""Application entry point — instantiates FastAPI."""

from pathlib import Path

from dotenv import load_dotenv

# Explicit path (not the default cwd-based search) — this must find .env
# regardless of the working directory the server happens to be launched
# from. Local dev only; Render sets real env vars directly.
load_dotenv(Path(__file__).resolve().parent / ".env")

from app import create_app  # noqa: E402

app = create_app()
