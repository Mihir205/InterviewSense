from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class UploadResponse(BaseModel):
    session_id: str
    status: str

class AnalyzeResponse(BaseModel):
    status: str
    session_id: str

class StatusResponse(BaseModel):
    status: str

class MomentResponse(BaseModel):
    timestamp_sec: float
    type: str
    label: str
    description: str

class SummaryResponse(BaseModel):
    eye_contact_pct: Optional[float]
    blink_rate: Optional[float]
    avg_head_stability: Optional[float]
    avg_mouth_activity: Optional[float]
    avg_posture_score: Optional[float]
    engagement_score: Optional[float]

class TimelinePoint(BaseModel):
    timestamp_sec: float
    engagement_score: Optional[float]
    is_eye_contact: Optional[bool]
    posture_score: Optional[float]

class ReportTimelineResponse(BaseModel):
    timeline: List[TimelinePoint]
