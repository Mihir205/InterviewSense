from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend.models.db_models import Session as DbSession, FrameMetric, Moment, SessionSummary
from backend.schemas.response import SummaryResponse, ReportTimelineResponse, TimelinePoint, MomentResponse

router = APIRouter(prefix="/api/report", tags=["Report"])

@router.get("/{session_id}/summary", response_model=SummaryResponse)
def get_summary(session_id: str, db: Session = Depends(get_db)):
    """Returns the session summary."""
    summary = db.query(SessionSummary).filter(SessionSummary.session_id == session_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found for this session.")
    
    return summary

@router.get("/{session_id}/timeline", response_model=ReportTimelineResponse)
def get_timeline(session_id: str, db: Session = Depends(get_db)):
    """Returns frame metrics sampled roughly at 1 FPS for chart rendering."""
    # M2 fix: Fetch all and sample roughly 1 per second
    metrics = db.query(FrameMetric).filter(
        FrameMetric.session_id == session_id
    ).order_by(FrameMetric.timestamp_sec).all()

    timeline = []
    last_sec = -1
    for m in metrics:
        current_sec = int(m.timestamp_sec)
        if current_sec > last_sec:
            timeline.append(TimelinePoint(
                timestamp_sec=m.timestamp_sec,
                engagement_score=m.engagement_score,
                is_eye_contact=m.is_eye_contact,
                posture_score=m.posture_score
            ))
            last_sec = current_sec

    return ReportTimelineResponse(timeline=timeline)

@router.get("/{session_id}/moments", response_model=List[MomentResponse])
def get_moments(session_id: str, db: Session = Depends(get_db)):
    """Returns all flagged moments sorted by time."""
    moments = db.query(Moment).filter(Moment.session_id == session_id).order_by(Moment.timestamp_sec).all()
    return moments
