# InterviewSense

> **Communication analytics using facial landmark geometry and behavioral vision**

InterviewSense is a **fully local**, webcam-based mock interview analysis system. It records a candidate's webcam during a mock interview and — after the session ends — analyses the video to generate a detailed report on non-verbal communication behaviour.

No video leaves the candidate's machine.

---

## What it analyses

| Metric | Method |
|--------|--------|
| Eye contact & gaze | Iris localisation (OpenCV) + head pose; MediaPipe fallback |
| Head pose stability | PnP solver → yaw / pitch / roll (OpenCV `solvePnP`) |
| Blink rate | Eye Aspect Ratio — EAR (Soukupova & Cech 2016) |
| Mouth movement | Mouth Aspect Ratio — MAR |
| Body posture | MediaPipe BlazePose — shoulder tilt & slouch detection |

Overall engagement is scored 0–100 using a rule-based weighted sum (eye contact 35 %, head stability 25 %, posture 20 %, blink 10 %, mouth 10 %).

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js (React) + Recharts |
| Webcam recording | Browser MediaRecorder API |
| Backend | FastAPI + Uvicorn (Python) |
| CV models | dlib ERT 68-pt landmarks, OpenCV, MediaPipe BlazePose |
| Video conversion | FFmpeg |
| Storage | SQLite + SQLAlchemy |

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- FFmpeg installed and on `PATH`
- dlib — use `conda` or a prebuilt wheel on Windows

---

## Local setup

### 1. Clone & create folders

```bash
git clone <repo-url> InterviewSense
cd InterviewSense
```

### 2. Backend

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r backend/requirements.txt
```

Download the dlib model weights and place them in `models/`:

- `shape_predictor_68_face_landmarks.dat` — [dlib model zoo](http://dlib.net/files/)
- `face_detection_yunet_2023mar.onnx` — [OpenCV Zoo](https://github.com/opencv/opencv_zoo)

### 3. Frontend

```bash
cd frontend
npm install
```

Copy `.env.local.example` to `.env.local` and set `NEXT_PUBLIC_API_URL=http://localhost:8000`.

### 4. Run locally

**Terminal 1 — backend**

```bash
# from repo root, with venv active
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — frontend**

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Notes

- The engagement score is a coaching signal, not a proven confidence measure.
- Webcam gaze only indicates whether the candidate is looking at the camera zone, not the exact spot. Good lighting and an unobstructed face improve accuracy.
- The dlib 68-point model has a non-commercial licence — fine for a university project.
