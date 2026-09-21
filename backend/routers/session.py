"""
routers/session.py
------------------
Endpoints for creating sessions, uploading videos, and triggering analysis.

Phase 1 stub — routes are defined but logic will be filled in Phase 5.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/upload")
def upload_video():
    """Upload a webcam recording for analysis. (Phase 5)"""
    return {"detail": "Not implemented yet — coming in Phase 5."}


@router.post("/{session_id}/analyze")
def analyze_session(session_id: str):
    """Trigger analysis for an uploaded session. (Phase 5)"""
    return {"detail": "Not implemented yet — coming in Phase 5."}


@router.get("/{session_id}/status")
def get_status(session_id: str):
    """Return the current processing status of a session. (Phase 5)"""
    return {"detail": "Not implemented yet — coming in Phase 5."}
