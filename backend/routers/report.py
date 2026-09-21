"""
routers/report.py
-----------------
Endpoints for retrieving analysis results for the frontend report page.

Phase 1 stub — routes are defined but logic will be filled in Phase 5.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/{session_id}/summary")
def get_summary(session_id: str):
    """Return the session summary (scores and percentages). (Phase 5)"""
    return {"detail": "Not implemented yet — coming in Phase 5."}


@router.get("/{session_id}/timeline")
def get_timeline(session_id: str):
    """Return frame-level metrics sampled at ~1 FPS for chart rendering. (Phase 5)"""
    return {"detail": "Not implemented yet — coming in Phase 5."}


@router.get("/{session_id}/moments")
def get_moments(session_id: str):
    """Return all strong/weak moments sorted by timestamp. (Phase 5)"""
    return {"detail": "Not implemented yet — coming in Phase 5."}
