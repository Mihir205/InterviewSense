# InterviewSense — Phase Plan

> **Communication analytics using facial landmark geometry and behavioral vision**
>
> This document breaks the project into **6 phases** for structured development.
> Tick each checkbox as work is completed and update the progress table as each phase moves forward.

---

## Progress Overview

| Phase | Title | Status | Progress |
|-------|-------|--------|----------|
| 1 | Project Setup & Infrastructure | ✅ Completed | 100% |
| 2 | Computer Vision Pipeline | 🔲 Not Started | 0% |
| 3 | Behavioral Metrics Engine | 🔲 Not Started | 0% |
| 4 | Behavior Engine & Engagement Scoring | 🔲 Not Started | 0% |
| 5 | FastAPI Backend & Data Persistence | 🔲 Not Started | 0% |
| 6 | Next.js Frontend & Report UI | 🔲 Not Started | 0% |

> **Status key:** 🔲 Not Started | 🔄 In Progress | ✅ Completed

---

## Phase 1 — Project Setup & Infrastructure

> **Goal:** Stand up the full project skeleton, install all dependencies, and prepare the database schema so every later phase has a stable base to build on.

### 1.1 Repository & Directory Structure

- [x] Initialise Git repository
- [x] Create top-level directory layout:
  ```
  InterviewSense/
  ├── backend/        # FastAPI Python app
  ├── frontend/       # Next.js app
  ├── models/         # dlib .dat model files
  ├── uploads/        # Temporary video uploads (gitignored)
  ├── db/             # SQLite database file
  └── docs/           # Documentation
  ```
- [x] Add `.gitignore` covering Python, Node.js, model weights, and uploaded videos
- [x] Write `README.md` with a short project description and local-run instructions

### 1.2 Python Backend Environment

- [x] Create Python virtual environment (`python -m venv venv`)
- [x] Pin all dependencies in `requirements.txt`:
  - `fastapi`
  - `uvicorn`
  - `python-multipart` (file uploads)
  - `opencv-python`
  - `dlib` (use conda or a prebuilt wheel on Windows — non-commercial licence for the 68-point model is fine for a university project)
  - `mediapipe`
  - `numpy`
  - `ffmpeg-python`
  - `sqlalchemy`
- [x] Confirm clean install on a CPU-only machine
- [x] Download and place pretrained model files inside `models/`:
  - [x] `shape_predictor_68_face_landmarks.dat`
  - [x] `mmod_human_face_detector.dat` (optional, for alternate HOG fallback)
  - [x] `face_detection_yunet_2023mar.onnx` (YuNet fallback)

### 1.3 Next.js Frontend Environment

- [x] Scaffold the frontend:
  ```bash
  npx create-next-app@latest ./frontend
  ```
- [x] Configure TypeScript if the team prefers it
- [x] Set up the folder layout inside `frontend/`:
  ```
  frontend/
  ├── app/           # App Router pages
  ├── components/    # Shared UI components
  ├── lib/           # API helpers and utilities
  └── public/        # Static assets
  ```
- [x] Add `.env.local` with `NEXT_PUBLIC_API_URL` pointing at the local FastAPI server
- [x] Install `recharts` for timeline charts

### 1.4 FFmpeg

- [x] Install FFmpeg on the development machine (or bundle the binary alongside the backend)
- [x] Verify `ffmpeg` is callable from the Python environment
- [x] Write a small `ffmpeg_utils.py` helper that converts a given file to MP4 using `ffmpeg-python`

### 1.5 SQLite Schema & SQLAlchemy Models

- [x] Design the database tables:
  - **`sessions`**: `id`, `created_at`, `duration_seconds`, `video_filename`
  - **`frame_metrics`**: `id`, `session_id`, `frame_number`, `timestamp_sec`, `head_yaw`, `head_pitch`, `head_roll`, `ear_left`, `ear_right`, `mar`, `gaze_x`, `gaze_y`, `shoulder_tilt`, `is_eye_contact`
  - **`moments`**: `id`, `session_id`, `timestamp_sec`, `type` (strong / weak), `label`, `description`
  - **`session_summary`**: `id`, `session_id`, `eye_contact_pct`, `blink_rate`, `avg_head_stability`, `avg_mouth_activity`, `avg_posture_score`, `engagement_score`
- [x] Write SQLAlchemy ORM models in `backend/models/db_models.py`
- [x] Write `backend/database.py` that creates the DB file and all tables on startup

---

## Phase 2 — Computer Vision Pipeline

> **Goal:** Build the frame-level CV pipeline that extracts raw measurements from each video frame. Covers video reading, face detection, 68-point landmark detection, body pose, and the calibration baseline.

### 2.1 Video Ingestion & Frame Extraction

- [ ] Implement `VideoProcessor` class (`backend/services/video_service.py`):
  - [ ] Accept a path to an MP4 file (post-FFmpeg conversion)
  - [ ] Open with `cv2.VideoCapture`
  - [ ] Sample frames at ~10–15 FPS by skipping intermediate frames
  - [ ] Yield `(frame_bgr, timestamp_sec)` for each sampled frame
- [ ] Handle edge cases: file not found, corrupt video, duration < 10 seconds

### 2.2 Face Detection

**Primary — dlib HOG + Linear SVM**
- [ ] Load `dlib.get_frontal_face_detector()`
- [ ] Detect the face in each frame and return the largest bounding box
- [ ] Log a warning when no face is detected and skip the frame

**Fallback — YuNet (OpenCV)**
- [ ] Load `cv2.FaceDetectorYN` with the downloaded `.onnx` file
- [ ] Switch to YuNet automatically if dlib fails for N consecutive frames
- [ ] Return the same bounding-box format so the rest of the pipeline stays unchanged

### 2.3 Facial Landmark Detection (68 Points — ERT, Kazemi & Sullivan 2014)

- [ ] Load `dlib.shape_predictor` using `shape_predictor_68_face_landmarks.dat`
- [ ] Run the predictor on the face bounding box for each frame
- [ ] Extract all 68 `(x, y)` coordinates into a NumPy array
- [ ] Map point indices to named landmark groups for use in later phases:
  - Left eye: 36–41 | Right eye: 42–47
  - Outer lip: 48–59 | Inner lip: 60–67
  - Nose tip: 33 | Chin: 8
  - Eye corners for PnP: 36, 45 | Mouth corners for PnP: 48, 54

### 2.4 Body Pose Detection — MediaPipe Pose Landmarker (BlazePose)

- [ ] Initialise MediaPipe Pose in static-image mode, CPU only
- [ ] Run pose on each frame and extract:
  - Left shoulder: landmark 11
  - Right shoulder: landmark 12
  - Nose: landmark 0 (used for head-to-shoulder height)
- [ ] Return `None` gracefully when pose is not detected

### 2.5 Calibration Baseline

- [ ] Collect measurements from the **first 10 seconds** of each recording (the candidate sits normally and looks at the camera)
- [ ] From those frames, compute per-session baseline values:
  - [ ] Mean EAR → personal blink threshold
  - [ ] Mean head yaw, pitch, roll → neutral head pose reference
  - [ ] Mean shoulder positions → neutral posture reference
- [ ] Store baseline in a `CalibrationBaseline` dataclass and pass it to Phase 3 modules

---

## Phase 3 — Behavioral Metrics Engine

> **Goal:** Turn the raw landmarks from Phase 2 into the five behavioral measurements: Head Pose, Blink Rate, Mouth Movement, Eye Gaze / Eye Contact, and Body Posture.

### 3.1 Head Pose — PnP + Rodrigues

- [ ] Define a generic 3D face model (reference points: nose tip, chin, left/right eye corners, left/right mouth corners)
- [ ] For each frame, call `cv2.solvePnP()` (`SOLVEPNP_ITERATIVE`) with the matched 2D landmark points and the camera intrinsics (estimated from image size)
- [ ] Convert the rotation vector with `cv2.Rodrigues()` and decompose to **yaw, pitch, roll** in degrees
- [ ] Compute a **head-stability score**: rolling standard deviation of yaw, pitch, and roll over a ~30-frame window (lower std-dev = more stable)
- [ ] Subtract the calibration baseline neutral angles before scoring

### 3.2 Blink Rate — Eye Aspect Ratio (EAR, Soukupova & Cech 2016)

- [ ] Implement EAR:
  ```
  EAR = (|p2−p6| + |p3−p5|) / (2 × |p1−p4|)
  ```
  where p1–p6 are the six landmarks of one eye
- [ ] Average EAR across left and right eyes each frame
- [ ] Use the calibration-period EAR mean to set a personal closure threshold (default ~0.21 if calibration is unavailable)
- [ ] Detect blinks with a state machine: OPEN → CLOSED → OPEN counts as one blink
- [ ] Compute **blink rate** (blinks per minute) over a rolling 60-second window

### 3.3 Mouth Movement — Mouth Aspect Ratio (MAR)

- [ ] Implement MAR using inner lip landmarks 60–67 (same ratio style as EAR)
- [ ] Compute MAR per frame and apply a rolling average to smooth noise
- [ ] Flag a frame as **active mouth movement** when smoothed MAR exceeds its calibration-period mean by a set margin
- [ ] Treat this as general facial activity — without audio, talking and smiling cannot be separated

### 3.4 Eye Gaze & Eye Contact

**Iris localisation (primary)**
- [ ] Crop each eye region from the frame using bounding boxes derived from eye landmarks
- [ ] Convert crop to greyscale; apply `cv2.adaptiveThreshold` to isolate the dark iris
- [ ] Find contours with `cv2.findContours`; pick the largest blob as the iris candidate
- [ ] Use `cv2.moments` to compute the iris centroid; derive the iris offset relative to the eye-corner landmarks
- [ ] Combine iris offset + head yaw/pitch to produce a **gaze direction vector**
- [ ] A frame counts as **eye contact** when the gaze vector falls within a defined camera-facing zone
- [ ] Compute **eye-contact percentage** = (frames with eye contact) / (total frames)

**Fallback — MediaPipe Face Landmarker (Face Mesh + iris landmarks)**
- [ ] Initialise MediaPipe Face Landmarker
- [ ] Switch to MediaPipe gaze when iris contour detection fails for N consecutive frames (e.g. glasses, dim light)

> Note: webcam gaze only indicates whether the candidate is looking at the camera zone, not the exact spot. Performance degrades with glasses and poor lighting.

### 3.5 Body Posture — BlazePose Shoulders

- [ ] Compute **shoulder tilt angle**: `atan2(right_y − left_y, right_x − left_x)`
- [ ] Compute **head vertical offset**: nose landmark y vs shoulder-midpoint y, normalised by shoulder width
- [ ] Detect posture events per frame:
  - **Slouching** — head drops significantly below calibration baseline vertical offset
  - **Leaning** — sustained lateral head movement beyond a threshold
  - **Tilted shoulders** — shoulder tilt angle held above threshold for several seconds
- [ ] Produce a **per-frame posture score** from 0 to 1 (1 = upright and centred)

---

## Phase 4 — Behavior Engine & Engagement Scoring

> **Goal:** Fuse the five metric streams over time with smoothing, apply the rule-based weighted scoring (eye contact 35 %, head stability 25 %, posture 20 %, blink rate 10 %, mouth activity 10 %), detect strong and weak moments, and produce the session summary. All scoring is rule-based because there is no labeled dataset and rules are fully explainable.

### 4.1 Temporal Smoothing

- [ ] Apply exponential moving average (EMA) to each raw metric stream to remove frame-level noise
- [ ] Smoothing window: ~15–30 frames (roughly 1–2 seconds at 15 FPS)
- [ ] Apply independently to: EAR, MAR, gaze vector, head yaw/pitch/roll, posture score
- [ ] Persist both raw and smoothed values per frame in the `frame_metrics` table

### 4.2 Feature Fusion & Normalisation

- [ ] After smoothing, assemble a per-frame feature vector:
  ```
  [eye_contact_bool, head_stability_score, blink_rate, mouth_activity, posture_score]
  ```
- [ ] Normalise each component to [0, 1] using calibration baselines and empirical reference ranges

### 4.3 Rule-Based Weighted Engagement Scoring

- [ ] Compute a **rolling engagement score** over 5-second windows using these starting weights (tune after testing):

  | Metric | Weight |
  |--------|--------|
  | Eye contact % | 35% |
  | Head stability | 25% |
  | Posture | 20% |
  | Blink rate | 10% |
  | Mouth activity | 10% |

- [ ] Compute the **overall engagement score** (0–100) as the session-average of the rolling scores

### 4.4 Moment Detection

**Strong moments** — flag a window when:
- [ ] Eye contact is sustained above 90 % for > 5 seconds
- [ ] Head is stable and posture is upright simultaneously

**Weak moments** — flag a window when (sub-score below threshold for > ~3 seconds):
- [ ] Eye contact drops out for > 3 seconds
- [ ] Head yaw > 20 ° or pitch > 15 ° sustained
- [ ] Slouching or leaning detected continuously
- [ ] Blink rate is very high (> 30 bpm) or very low (< 5 bpm)
- [ ] No mouth movement detected for an extended period

- [ ] Each moment record: `timestamp_sec`, `type` (strong / weak), `label`, `description`
- [ ] Remove overlapping moments with a simple NMS-style suppression pass

### 4.5 Session Summary

- [ ] After full-video processing, aggregate:
  - `eye_contact_pct` — overall eye-contact percentage
  - `blink_rate` — overall blinks per minute
  - `avg_head_stability` — mean stability score
  - `avg_mouth_activity` — mean active-mouth fraction
  - `avg_posture_score` — mean per-frame posture score
  - `engagement_score` — final 0–100 weighted score
- [ ] Write to `session_summary` table in SQLite

---

## Phase 5 — FastAPI Backend & Data Persistence

> **Goal:** Build the FastAPI server that accepts video uploads, runs the analysis pipeline (Phases 2–4), persists results to SQLite, and exposes the endpoints the frontend needs. Everything runs as a local Python process — no cloud calls.

### 5.1 Project Structure

- [ ] Lay out the backend folder:
  ```
  backend/
  ├── main.py               # App entry point, CORS, router registration
  ├── database.py           # SQLite engine, session factory, table init
  ├── routers/
  │   ├── session.py        # Upload + analyse endpoints
  │   └── report.py         # Summary / timeline / moments endpoints
  ├── services/
  │   ├── video_service.py  # FFmpeg conversion + VideoProcessor (Phase 2)
  │   ├── cv_pipeline.py    # Face detection + landmarks + body pose (Phase 2)
  │   ├── metrics.py        # Head pose, EAR, MAR, gaze, posture (Phase 3)
  │   └── engine.py         # Smoothing, scoring, moment detection (Phase 4)
  ├── models/
  │   └── db_models.py      # SQLAlchemy ORM models
  └── schemas/
      └── response.py       # Pydantic response schemas
  ```

### 5.2 Video Upload Endpoint

- [ ] `POST /api/session/upload`
  - Accept `multipart/form-data` with a video file field
  - Validate MIME type / extension (WebM, MP4, MOV)
  - Save to `uploads/<uuid>.<ext>`
  - Create a new `sessions` row; return `{ "session_id": "...", "status": "queued" }`
- [ ] Set maximum upload size (e.g. 500 MB) in Uvicorn / FastAPI config

### 5.3 Analysis Orchestration Endpoint

- [ ] `POST /api/session/{session_id}/analyze`
  1. Run FFmpeg conversion to MP4 if the source is WebM
  2. Run `VideoProcessor` to iterate frames
  3. For each frame: face detection → 68 landmarks → body pose (Phase 2)
  4. Compute all five metrics per frame (Phase 3)
  5. Run calibration on first-10-second frames before scoring
  6. Run behavior engine: smooth → fuse → score → detect moments (Phase 4)
  7. Bulk-insert `frame_metrics` rows; insert `moments` rows; insert `session_summary` row
  8. Delete the uploaded video file
  9. Return `{ "status": "complete", "session_id": "..." }`
- [ ] `GET /api/session/{session_id}/status` — returns current status (`queued`, `processing`, `complete`, `error`)
- [ ] Return meaningful HTTP error codes on failure

### 5.4 Report Endpoints

- [ ] `GET /api/report/{session_id}/summary` — returns the `session_summary` row as JSON
- [ ] `GET /api/report/{session_id}/timeline` — returns `frame_metrics` sampled at ~1 FPS (one row per second) for chart rendering
- [ ] `GET /api/report/{session_id}/moments` — returns all rows from `moments` sorted by `timestamp_sec`
- [ ] Validate all responses with Pydantic schemas

### 5.5 CORS, Config & Health Check

- [ ] Add `CORSMiddleware` allowing the Next.js dev origin (`http://localhost:3000`)
- [ ] Read settings from `.env`:
  - `DATABASE_URL`
  - `UPLOAD_DIR`
  - `MAX_UPLOAD_SIZE_MB`
  - `PROCESSING_FPS`
- [ ] `GET /health` — returns `{ "status": "ok" }` for quick liveness checks

---

## Phase 6 — Next.js Frontend & Report UI

> **Goal:** Build the three main pages — recording, processing, and report — using Next.js (React). The reporting view must show the engagement score, per-metric cards, interactive timeline charts (Recharts), and the key moments panel.

### 6.1 Recording Page (`/interview`)

- [ ] Request webcam access via `navigator.mediaDevices.getUserMedia`
- [ ] Record with **MediaRecorder API**:
  - [ ] Start on "Begin Interview" button click
  - [ ] Buffer video chunks into an array
  - [ ] Stop on "Stop & Analyse" button click; assemble chunks into a `Blob` (WebM)
- [ ] Show live webcam preview only — no analysis happens here
- [ ] Display a running timer while recording
- [ ] On stop: `POST /api/session/upload` with the video `Blob`; navigate to `/processing?session=<id>`

### 6.2 Processing Page (`/processing`)

- [ ] Show an upload progress bar while the file uploads
- [ ] Once upload completes, call `POST /api/session/{session_id}/analyze`
- [ ] Poll `GET /api/session/{session_id}/status` every 2–3 seconds
- [ ] Show an animated "Analysing…" state while the backend works
- [ ] On `status === "complete"`, redirect to `/report/{session_id}`
- [ ] On `status === "error"`, show an error message with a retry option

### 6.3 Report Page — Summary (`/report/[sessionId]`)

- [ ] Fetch `GET /api/report/{session_id}/summary` on page load
- [ ] Display a large **Overall Engagement Score** gauge (circular / radial)
- [ ] Display a metric card for each of the five measures:
  - Eye Contact %
  - Blink Rate (bpm)
  - Head Stability
  - Mouth Activity
  - Posture Score
- [ ] Each card shows its numeric value and a short contextual label ("Good", "Needs Work", etc.)

### 6.4 Report Page — Timeline Charts

- [ ] Fetch `GET /api/report/{session_id}/timeline`
- [ ] Render line / area charts using **Recharts** for:
  - Eye contact (rolling %)
  - Head yaw, pitch, roll
  - EAR (blink activity)
  - MAR (mouth activity)
  - Posture score
- [ ] Charts should be interactive: hover shows exact timestamp and value
- [ ] Overlay coloured markers at moment timestamps (green = strong, red = weak)

### 6.5 Report Page — Key Moments Panel

- [ ] Fetch `GET /api/report/{session_id}/moments`
- [ ] Render a scrollable chronological list:
  - 🟢 Strong moments — green indicator, timestamp, label, one-line description
  - 🔴 Weak moments — red indicator, timestamp, label, one-line description
- [ ] Clicking a moment scrolls the timeline charts to that timestamp and highlights the marker

### 6.6 Home / Landing Page (`/`)

- [ ] Explain what InterviewSense does in plain language
- [ ] CTA button: **"Start Mock Interview"** → `/interview`
- [ ] Short bullet list of what is analysed (eye contact, head pose, posture, etc.)
- [ ] Privacy note: "Everything runs locally — your video never leaves your computer"

### 6.7 UI & Polish

- [ ] Consistent dark-mode design across all pages
- [ ] Typography: **Inter** from Google Fonts
- [ ] Colour palette: indigo/blue primary accent; green for strong moments; red for weak moments
- [ ] Responsive layout (desktop-first; minimum usable on a tablet)
- [ ] Add loading skeletons, error boundaries, and empty states
- [ ] Smooth page transitions

---

## Tech Stack Reference (Do Not Change)

| Layer | Technology |
|-------|------------|
| Frontend framework | Next.js (React) |
| Webcam recording | Browser MediaRecorder API (`getUserMedia`) |
| Frontend charts | Recharts |
| Backend framework | FastAPI (Python) |
| Backend server | Uvicorn |
| Video conversion | FFmpeg |
| Face detection (primary) | dlib HOG + Linear SVM (`get_frontal_face_detector`) |
| Face detection (fallback) | YuNet via OpenCV (`FaceDetectorYN`) |
| Facial landmarks | dlib ERT — `shape_predictor_68_face_landmarks.dat` (Kazemi & Sullivan 2014) |
| Head pose | OpenCV `solvePnP` + `Rodrigues` → yaw / pitch / roll |
| Blink detection | Eye Aspect Ratio — EAR (Soukupova & Cech 2016) |
| Mouth movement | Mouth Aspect Ratio — MAR |
| Eye gaze (primary) | OpenCV adaptive threshold + contour moments + head pose |
| Eye gaze (fallback) | MediaPipe Face Landmarker (Face Mesh with iris landmarks) |
| Body pose | MediaPipe Pose Landmarker — BlazePose (shoulders only) |
| Database | SQLite |
| ORM | SQLAlchemy |
| Scoring method | Rule-based weighted sum (no ML model) |
| Deployment | Fully local — CPU only, no cloud |

---

## Things to Keep in Mind

- The engagement score is a **coaching signal**, not a proven confidence measure. Run a few practice sessions and check that flagged moments match what you observe.
- Webcam gaze only reports whether the candidate is looking at the camera zone, not the exact spot. Glasses and dim light degrade iris detection — ask candidates to use good lighting and keep their face and shoulders in frame.
- **dlib on Windows** can be tricky to build from source. Use `conda` or a prebuilt wheel. The 68-point model has a non-commercial licence, which is acceptable for a university project.
