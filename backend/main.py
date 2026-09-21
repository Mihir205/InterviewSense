"""
main.py
-------
FastAPI application entry point for InterviewSense.

Startup tasks
-------------
- Verify FFmpeg is available on PATH
- Initialise the SQLite database (create tables if missing)
- Register routers

Run with::

    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.services.ffmpeg_utils import verify_ffmpeg_available

logger = logging.getLogger(__name__)

# ── Application factory ────────────────────────────────────────────────────────
app = FastAPI(
    title="InterviewSense API",
    description=(
        "Backend for InterviewSense — non-verbal communication analytics "
        "from webcam interview recordings."
    ),
    version="0.1.0",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# Allow the Next.js dev server (and any configured production origin) to call
# the API.  Update ALLOWED_ORIGINS in .env for production.
_allowed_origins_raw: str = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
)
allowed_origins: list[str] = [o.strip() for o in _allowed_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup() -> None:
    # 1. Ensure uploads directory exists
    upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory: %s", upload_dir.resolve())

    # 2. Check FFmpeg
    if not verify_ffmpeg_available():
        logger.warning(
            "FFmpeg not found on PATH. Video conversion will fail. "
            "Install FFmpeg and ensure it is accessible from this environment."
        )
    else:
        logger.info("FFmpeg is available.")

    # 3. Initialise database
    init_db()
    logger.info("Database initialised.")


# ── Routers ────────────────────────────────────────────────────────────────────
# Imported here (after app is created) to avoid circular imports.
from backend.routers import session as session_router  # noqa: E402
from backend.routers import report as report_router    # noqa: E402

app.include_router(session_router.router, prefix="/api/session", tags=["session"])
app.include_router(report_router.router, prefix="/api/report", tags=["report"])


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness probe — returns 200 OK when the server is running."""
    return {"status": "ok"}
