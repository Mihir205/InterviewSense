"""
db_models.py
------------
SQLAlchemy ORM models for InterviewSense.

Tables
------
sessions        — one row per recorded interview session
frame_metrics   — one row per sampled video frame (raw + smoothed measurements)
moments         — strong and weak behavioural moments detected in the session
session_summary — single aggregated row per session (scores shown in the report)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


# ── Helper ─────────────────────────────────────────────────────────────────────
def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── sessions ───────────────────────────────────────────────────────────────────
class Session(Base):
    """
    Represents a single mock-interview recording session.

    created_at       — UTC timestamp when the session was created
    duration_seconds — total length of the recording in seconds (set after analysis)
    video_filename   — original uploaded filename (cleared after analysis)
    status           — queued | processing | complete | error
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    video_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("queued", "processing", "complete", "error", name="session_status"),
        default="queued",
        nullable=False,
    )

    # Relationships
    frame_metrics: Mapped[list["FrameMetric"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    moments: Mapped[list["Moment"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    summary: Mapped["SessionSummary | None"] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} status={self.status}>"


# ── frame_metrics ──────────────────────────────────────────────────────────────
class FrameMetric(Base):
    """
    Stores raw measurements computed for a single sampled video frame.

    Columns
    -------
    frame_number    — index of the sampled frame (0-based)
    timestamp_sec   — position in the video in seconds
    head_yaw        — estimated head yaw angle in degrees
    head_pitch      — estimated head pitch angle in degrees
    head_roll       — estimated head roll angle in degrees
    ear_left        — Eye Aspect Ratio for the left eye
    ear_right       — Eye Aspect Ratio for the right eye
    mar             — Mouth Aspect Ratio
    gaze_x          — horizontal gaze offset (iris relative to eye corners)
    gaze_y          — vertical gaze offset
    shoulder_tilt   — shoulder tilt angle in degrees (from BlazePose)
    posture_score   — per-frame posture score 0–1 (1 = upright)
    is_eye_contact  — True when estimated gaze falls in the camera-facing zone
    engagement_score— rolling engagement score 0–100 for this frame's window
    """

    __tablename__ = "frame_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_sec: Mapped[float] = mapped_column(Float, nullable=False)

    # Head pose (degrees)
    head_yaw: Mapped[float | None] = mapped_column(Float, nullable=True)
    head_pitch: Mapped[float | None] = mapped_column(Float, nullable=True)
    head_roll: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Blink (EAR)
    ear_left: Mapped[float | None] = mapped_column(Float, nullable=True)
    ear_right: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Mouth (MAR)
    mar: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Gaze
    gaze_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    gaze_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_eye_contact: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Posture
    shoulder_tilt: Mapped[float | None] = mapped_column(Float, nullable=True)
    posture_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Derived
    engagement_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="frame_metrics")

    def __repr__(self) -> str:
        return f"<FrameMetric session={self.session_id} t={self.timestamp_sec:.2f}s>"


# ── moments ────────────────────────────────────────────────────────────────────
class Moment(Base):
    """
    A flagged strong or weak behavioural moment in the session timeline.

    type        — 'strong' or 'weak'
    label       — short name (e.g. 'Eye contact lost', 'Great eye contact')
    description — one-sentence explanation of why this moment was flagged
    """

    __tablename__ = "moments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    timestamp_sec: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(
        Enum("strong", "weak", name="moment_type"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    session: Mapped["Session"] = relationship(back_populates="moments")

    def __repr__(self) -> str:
        return f"<Moment [{self.type}] t={self.timestamp_sec:.1f}s — {self.label}>"


# ── session_summary ────────────────────────────────────────────────────────────
class SessionSummary(Base):
    """
    Aggregated per-session scores written at the end of analysis.

    eye_contact_pct     — percentage of frames where eye contact was detected (0–100)
    blink_rate          — overall blinks per minute
    avg_head_stability  — mean head-stability score across the session (0–1)
    avg_mouth_activity  — mean active-mouth fraction (0–1)
    avg_posture_score   — mean per-frame posture score (0–1)
    engagement_score    — final weighted engagement score (0–100)
    """

    __tablename__ = "session_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    eye_contact_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    blink_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_head_stability: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_mouth_activity: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_posture_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="summary")

    def __repr__(self) -> str:
        return (
            f"<SessionSummary session={self.session_id} "
            f"engagement={self.engagement_score}>"
        )
