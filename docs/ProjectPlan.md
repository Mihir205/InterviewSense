# InterviewSense: Project Plan

## Communication analytics using facial landmark geometry and behavioral vision

## 1. Problem Statement

Mock interview platforms today judge a candidate only on what they say: pauses, filler words, and fluency. They ignore non-verbal cues like eye contact, head movement, and facial engagement, even though these strongly affect how confident and credible a candidate looks to an interviewer.

So candidates who practice on these platforms get feedback on only half of what an interviewer notices.

**Objective:** build a system that uses a normal webcam recording of a mock interview and, once the interview is finished, gives the candidate a report on their non-verbal communication.

The report should:

- Cover eye contact, gaze direction, head pose stability, blink rate, and mouth movement.
- Give an overall confidence and engagement score for the interview.
- Include a timeline that points to specific good and bad moments (for example, losing eye contact), not just one overall score.

## 2. System Architecture

The system works in two stages. First, the candidate does the mock interview while the browser records the webcam. After the interview ends, the video is uploaded and analyzed, and the candidate gets a report. Nothing is shown live.

| Layer | Parts | What it does |
|---|---|---|
| Recording | Webcam, browser recording | The Next.js app records the webcam during the interview and uploads the video when the candidate finishes. |
| Backend job | FastAPI, FFmpeg, OpenCV | Receives the video, converts it if needed, and reads it frame by frame for analysis. |
| Computer vision | Face detection, 68-point landmark localization, body pose | Finds the face in each frame, then 68 points on it (eyes, mouth, face outline). Body pose finds the shoulders. |
| Behavior measures | Head pose, Eye gaze, Blink, Mouth, Body pose | Each one turns landmark positions (or shoulder positions) into its own number for every frame. |
| Behavior engine | Feature fusion, Temporal analysis, Engagement index | Combines the measures, tracks them over time, and produces the score and the flagged moments. |
| Storage | SQLite | Saves the metrics and flagged moments. The video is deleted after analysis. |
| Report | Next.js report page | Shows the overall score, a summary of each metric, the session timeline, and the list of key moments. |

### How data flows

1. The candidate does the mock interview in the Next.js app, and the browser records the webcam.
2. When the interview ends, the video is uploaded to the FastAPI backend.
3. The backend converts the video if needed and reads frames from it (about 10 to 15 per second is enough).
4. For every frame, it finds the face and the 68 landmarks, and the shoulders for body pose.
5. The measure modules calculate head pose, gaze, blink, mouth, and body pose values.
6. The first 10 seconds are used as a calibration baseline for that person.
7. The behavior engine combines the measures, smooths them over time, calculates the engagement score, and flags strong and weak moments.
8. Metrics and moments are saved to SQLite, and the video is deleted.
9. The report page shows a "processing" message until the analysis finishes, then displays the report.

Everything runs locally: the Next.js app and the Python backend both run on the candidate's machine, so the video never leaves the computer.

## 3. Tech Stack

### 3.1 Computer vision: models and methods

| Task | Model or method name | Why we chose it |
|---|---|---|
| Face detection | HOG + Linear SVM detector (Dalal and Triggs), dlib `get_frontal_face_detector`. Fallback: YuNet (OpenCV). | Comes with dlib, which we already use for landmarks. It is fast on CPU, and a candidate faces the camera, so a frontal detector is enough. If it struggles in real lighting, swap to YuNet. |
| Facial landmarks | Ensemble of Regression Trees (ERT), Kazemi and Sullivan 2014, dlib `shape_predictor_68_face_landmarks` | This is the base paper of the project. It finds 68 landmarks in about a millisecond, and the points cover the eyes, mouth, and face shape that our metrics need. |
| Head pose | Perspective-n-Point (PnP), OpenCV `solvePnP`, then Rodrigues conversion to yaw, pitch, roll | Nose tip, chin, eye corners, and mouth corners matched to a generic 3D face give the head angles. Stability is the rolling standard deviation of those angles. |
| Blink and blink rate | Eye Aspect Ratio (EAR), Soukupova and Cech 2016 | A ratio of eye landmark distances that drops when the eye closes. It is cheap, easy to explain, and the threshold can be set per person from calibration. |
| Mouth movement | Mouth Aspect Ratio (MAR) | Uses the inner lip points to measure how much the mouth is moving. Without audio it cannot tell talking from smiling, so it is treated as general facial activity. |
| Eye gaze and eye contact | Iris center localization inside the eye region (OpenCV threshold and contour moments), iris offset relative to eye corners, combined with head pose. Fallback: MediaPipe Face Landmarker (Face Mesh with iris landmarks), for gaze only. | The 68 landmarks outline the eye but do not locate the iris. The iris offset gives eye direction and head pose adds the overall direction. Eye contact is the share of time the gaze is in the looking-at-camera zone. |
| Body pose (posture) | MediaPipe Pose Landmarker (BlazePose), shoulders only | The face landmarks say nothing about posture, so a second model is needed. Shoulder tilt and head-to-shoulder position catch slouching or leaning. It runs on CPU. |

### 3.2 Scoring

| Method | Where it's used | Why we chose it |
|---|---|---|
| Moving average smoothing over rolling windows, rule-based | Feature fusion and temporal analysis | We have no labeled dataset of good and bad interview behavior. Rules are also explainable, so the timeline can say exactly what went wrong. |
| Weighted sum of sub-scores (0 to 100) | Engagement index | Starting weights: eye contact 35, head stability 25, posture 20, blink rate 10, mouth activity 10. These are tuned after testing. A weak moment is a sub-score below its threshold for more than about 3 seconds. |
| Calibration on the first 10 seconds | Start of each recording | The candidate sits normally and looks at the camera. This sets personal thresholds for blink, gaze, head angle, and posture, because faces, cameras, and lighting differ. |

### 3.3 Application and supporting tools

| Technology | Where it's used | Why we chose it |
|---|---|---|
| Python | Backend and all analysis code | dlib, OpenCV, and MediaPipe all work well from Python, and the heavy work runs in C++ underneath, so analysis is fast. |
| Standard webcam | Input | The project is meant to work with no special hardware, so anyone can use the camera they already have. |
| OpenCV | Reading video frames, head pose, iris detection | Reads the uploaded video frame by frame and provides `solvePnP` and the image tools for finding the iris. |
| FFmpeg | Backend, before analysis | Browsers record in WebM or MP4 depending on the browser. FFmpeg converts the video into one format so the analysis code always gets the same input. |
| Next.js (React) | Frontend: recording page, upload, report page | Team preference. One app covers recording, upload, and the report pages, and it works with React chart components. |
| Browser MediaRecorder API | Recording page | Records the webcam directly in the browser, so candidates need no extra software. |
| Recharts | Session timeline in the report | Draws time-series charts in React and can mark specific moments on them. |
| FastAPI | Backend | Receives the video upload, runs the analysis as a background job, and serves the results. It is Python, so it sits next to the vision code. |
| SQLite | Storage | No setup, a single file, and enough for per-session metrics. It can move to PostgreSQL later if the system is hosted for many users. |
| Local deployment | Whole system | The CPU is enough and no GPU is needed. Video never leaves the candidate's machine. |

## Things to keep in mind

- The engagement score is a coaching signal, not a proven measure of confidence. Record a few team practice sessions and check that the flagged moments match what you actually see.
- Webcam gaze can only say whether the candidate is looking at the camera zone, not the exact spot. Glasses and dim light make iris detection worse. Ask candidates to sit in good light with their face and shoulders in the frame.
- dlib can be hard to build on Windows, so use conda or a prebuilt wheel. Its pretrained 68-point model comes from a dataset with a non-commercial license, which is fine for a university project.