import os
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.db_models import Session as DbSession, FrameMetric, Moment, SessionSummary
from backend.schemas.response import UploadResponse, AnalyzeResponse, StatusResponse
from backend.services.ffmpeg_utils import convert_to_mp4, get_video_duration
from backend.services.video_service import VideoProcessor
from backend.services.cv_pipeline import CVPipeline, CalibrationBaseline
from backend.services.metrics_engine import MetricsEngine
from backend.services.behavior_engine import BehaviorEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session", tags=["Session"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Uploads a video for analysis."""
    allowed_extensions = {".webm", ".mp4", ".mov"}
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type. Only WebM, MP4, MOV allowed.")

    session_id = str(uuid.uuid4())
    video_path = UPLOAD_DIR / f"{session_id}{ext}"
    
    with open(video_path, "wb") as f:
        f.write(await file.read())

    new_session = DbSession(id=session_id, video_filename=str(video_path), status="queued")
    db.add(new_session)
    db.commit()

    return {"session_id": session_id, "status": "queued"}

@router.get("/{session_id}/status", response_model=StatusResponse)
def get_status(session_id: str, db: Session = Depends(get_db)):
    """Returns the current processing status."""
    db_session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": db_session.status}

def process_analysis_task(session_id: str, db_generator):
    """Background task to run the full analysis pipeline."""
    db = next(db_generator())
    db_session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not db_session or not db_session.video_filename:
        logger.error(f"Session {session_id} not found or missing video.")
        return

    db_session.status = "processing"
    db.commit()

    try:
        input_path = Path(db_session.video_filename)
        if not input_path.exists():
            raise FileNotFoundError(f"Video file missing: {input_path}")
            
        mp4_path = UPLOAD_DIR / f"{session_id}.mp4"
        convert_to_mp4(input_path, mp4_path)
        
        duration = get_video_duration(mp4_path)
        db_session.duration_seconds = duration
        db.commit()

        # Phases 2 & 3: CV Pipeline & Raw Metrics
        video_proc = VideoProcessor(mp4_path, target_fps=12.0)
        cv = CVPipeline()
        metrics_eng = MetricsEngine()
        
        raw_frames_data = []
        calibration = None
        calibration_window_sec = 10.0
        
        # Pass 1: Extract all landmarks & body pose
        # We also compute metrics without baseline to gather first 10s stats
        first_10s_ears = []
        first_10s_yaw = []
        first_10s_pitch = []
        first_10s_roll = []
        first_10s_tilt = []
        first_10s_offset = []
        
        for frame_bgr, t_sec, f_idx in video_proc.process_frames():
            cv_results = cv.process_frame(frame_bgr)
            metrics = metrics_eng.compute_all_metrics(frame_bgr, cv_results, baseline=None)
            
            # Save raw data for pass 2
            raw_frames_data.append({
                "timestamp_sec": t_sec,
                "frame_idx": f_idx,
                "metrics": metrics
            })
            
            # Accumulate calibration stats
            if t_sec <= calibration_window_sec:
                if metrics["ear"] > 0: first_10s_ears.append(metrics["ear"])
                first_10s_yaw.append(metrics["head_yaw"])
                first_10s_pitch.append(metrics["head_pitch"])
                first_10s_roll.append(metrics["head_roll"])
                first_10s_tilt.append(metrics["shoulder_tilt"])
                if metrics["head_offset"] != 0: first_10s_offset.append(metrics["head_offset"])
        
        # Compute baseline
        def safe_mean(lst, default=0.0): return sum(lst)/len(lst) if lst else default
        baseline = CalibrationBaseline(
            mean_ear=safe_mean(first_10s_ears, 0.21),
            mean_head_yaw=safe_mean(first_10s_yaw),
            mean_head_pitch=safe_mean(first_10s_pitch),
            mean_head_roll=safe_mean(first_10s_roll),
            mean_shoulder_tilt=safe_mean(first_10s_tilt),
            mean_nose_to_shoulder=safe_mean(first_10s_offset)
        )
        
        # Re-adjust metrics using baseline
        for f in raw_frames_data:
            m = f["metrics"]
            m["head_yaw"] -= baseline.mean_head_yaw
            m["head_pitch"] -= baseline.mean_head_pitch
            m["head_roll"] -= baseline.mean_head_roll
            m["shoulder_tilt"] -= baseline.mean_shoulder_tilt
            
        # Phase 4: Behavior Engine (Smoothing, Scoring, Moments)
        behav_eng = BehaviorEngine(fps=video_proc.target_fps)
        result = behav_eng.analyze_session(raw_frames_data, baseline.mean_ear)
        
        if not result:
            raise ValueError("No frames were processed.")
            
        # Save to DB
        frames_to_insert = []
        for i, f in enumerate(result["frames"]):
            frames_to_insert.append(FrameMetric(
                session_id=session_id,
                frame_number=f["frame_idx"],
                timestamp_sec=f["timestamp_sec"],
                head_yaw=f["smoothed_metrics"]["head_yaw"],
                head_pitch=f["smoothed_metrics"]["head_pitch"],
                head_roll=f["smoothed_metrics"]["head_roll"],
                ear_left=f["smoothed_metrics"]["ear"], 
                ear_right=f["smoothed_metrics"]["ear"], # stored same for simplicity here
                mar=f["smoothed_metrics"]["mar"],
                gaze_x=0.0, gaze_y=0.0, # detailed gaze offset not returned individually in Phase 3
                shoulder_tilt=f["smoothed_metrics"]["shoulder_tilt"],
                posture_score=f["scores"]["posture"],
                is_eye_contact=f["metrics"]["is_eye_contact"],
                engagement_score=f["scores"]["engagement"]
            ))
            
        db.bulk_save_objects(frames_to_insert)
        
        moments_to_insert = []
        for m in result["moments"]:
            moments_to_insert.append(Moment(
                session_id=session_id,
                timestamp_sec=m["timestamp_sec"],
                type=m["type"],
                label=m["label"],
                description=m["description"]
            ))
            
        db.bulk_save_objects(moments_to_insert)
        
        summary_data = result["summary"]
        summary_row = SessionSummary(
            session_id=session_id,
            eye_contact_pct=summary_data["eye_contact_pct"],
            blink_rate=summary_data["blink_rate"],
            avg_head_stability=summary_data["avg_head_stability"],
            avg_mouth_activity=summary_data["avg_mouth_activity"],
            avg_posture_score=summary_data["avg_posture_score"],
            engagement_score=summary_data["engagement_score"]
        )
        db.add(summary_row)
        
        db_session.status = "complete"
        db.commit()
        
        # Cleanup videos
        if input_path.exists(): os.remove(input_path)
        if mp4_path.exists() and str(input_path) != str(mp4_path): os.remove(mp4_path)
        
    except Exception as e:
        logger.exception("Analysis failed.")
        db_session.status = "error"
        db.commit()
        
    finally:
        db.close()


@router.post("/{session_id}/analyze", response_model=AnalyzeResponse)
def analyze(session_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Triggers the asynchronous analysis pipeline."""
    db_session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if db_session.status in ["processing", "complete"]:
        return {"session_id": session_id, "status": db_session.status}

    background_tasks.add_task(process_analysis_task, session_id, get_db)
    
    return {"session_id": session_id, "status": "processing"}
