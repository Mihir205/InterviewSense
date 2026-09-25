import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import dlib
import mediapipe as mp
import numpy as np

logger = logging.getLogger(__name__)

# Model paths
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
DLIB_LANDMARK_PATH = MODELS_DIR / "shape_predictor_68_face_landmarks.dat"
YUNET_MODEL_PATH = MODELS_DIR / "face_detection_yunet_2023mar.onnx"

@dataclass
class CalibrationBaseline:
    """
    Holds baseline metrics computed from the first 10 seconds of video.
    """
    mean_ear: float = 0.21
    mean_head_yaw: float = 0.0
    mean_head_pitch: float = 0.0
    mean_head_roll: float = 0.0
    mean_shoulder_y: float = 0.0
    mean_shoulder_tilt: float = 0.0
    mean_nose_to_shoulder: float = 0.0

class CVPipeline:
    """
    Core CV Pipeline for Phase 2.
    Handles Face Detection, 68-point landmarks, and Body Pose.
    """
    def __init__(self):
        # 1. Primary Face Detector (dlib HOG)
        self.dlib_detector = dlib.get_frontal_face_detector()
        
        # 2. Fallback Face Detector (YuNet)
        self.yunet_detector = None
        if YUNET_MODEL_PATH.exists():
            self.yunet_detector = cv2.FaceDetectorYN.create(
                model=str(YUNET_MODEL_PATH),
                config="",
                input_size=(320, 320),
                score_threshold=0.6,
                nms_threshold=0.3,
                top_k=5000
            )
        else:
            logger.warning(f"YuNet model not found at {YUNET_MODEL_PATH}. Fallback disabled.")
            
        self.dlib_failures = 0
        self.max_dlib_failures = 5

        # 3. Facial Landmark Predictor (68 points)
        if not DLIB_LANDMARK_PATH.exists():
            raise FileNotFoundError(f"dlib landmark model not found at {DLIB_LANDMARK_PATH}")
        self.shape_predictor = dlib.shape_predictor(str(DLIB_LANDMARK_PATH))

        # 4. Body Pose (MediaPipe)
        self.mp_pose = mp.solutions.pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5
        )

    def _detect_face(self, frame_bgr: np.ndarray) -> Optional[dlib.rectangle]:
        """
        Detect face using dlib. Fallback to YuNet if dlib fails for N consecutive frames.
        Returns the bounding box of the largest face as a dlib.rectangle, or None.
        """
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        
        # Try dlib primary if failures are below threshold
        if self.dlib_failures < self.max_dlib_failures:
            faces = self.dlib_detector(gray, 0)
            if len(faces) > 0:
                self.dlib_failures = 0
                # Get the largest face
                largest_face = max(faces, key=lambda rect: rect.width() * rect.height())
                return largest_face
            else:
                self.dlib_failures += 1
                logger.debug(f"dlib failed to find a face. Failure count: {self.dlib_failures}")
        
        # If dlib failed or we've switched to YuNet fallback
        if self.yunet_detector is not None:
            height, width = frame_bgr.shape[:2]
            self.yunet_detector.setInputSize((width, height))
            _, yunet_faces = self.yunet_detector.detect(frame_bgr)
            
            if yunet_faces is not None and len(yunet_faces) > 0:
                # Get the largest face
                # YuNet returns faces as [x, y, w, h, x_re, y_re, ...]
                largest_face = max(yunet_faces, key=lambda f: f[2] * f[3])
                x, y, w, h = map(int, largest_face[:4])
                # Reset dlib failures occasionally to see if dlib recovered
                if self.dlib_failures > self.max_dlib_failures * 2:
                    self.dlib_failures = 0 
                return dlib.rectangle(x, y, x + w, y + h)
                
        # Both failed
        return None

    def process_frame(self, frame_bgr: np.ndarray) -> Dict:
        """
        Process a single frame to extract face bounding box, 68 landmarks, and body pose.
        Returns a dictionary with the raw extractions.
        """
        results = {
            "face_bbox": None,
            "landmarks_68": None,
            "body_pose": None
        }

        # 1 & 2. Face Detection
        bbox = self._detect_face(frame_bgr)
        if bbox is None:
            logger.warning("No face detected in frame.")
            return results
        
        results["face_bbox"] = bbox

        # 3. Landmark Detection
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        shape = self.shape_predictor(gray, bbox)
        
        # Convert dlib shape to numpy array of (x, y) coordinates
        coords = np.zeros((68, 2), dtype=int)
        for i in range(68):
            coords[i] = (shape.part(i).x, shape.part(i).y)
        results["landmarks_68"] = coords

        # 4. Body Pose Detection (MediaPipe)
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pose_results = self.mp_pose.process(frame_rgb)
        
        if pose_results.pose_landmarks:
            h, w = frame_bgr.shape[:2]
            # Extract key landmarks we care about (0: nose, 11: left shoulder, 12: right shoulder)
            # MediaPipe returns normalized coordinates [0.0, 1.0], convert to pixel coordinates
            lm = pose_results.pose_landmarks.landmark
            results["body_pose"] = {
                "nose": (int(lm[0].x * w), int(lm[0].y * h)),
                "left_shoulder": (int(lm[11].x * w), int(lm[11].y * h)),
                "right_shoulder": (int(lm[12].x * w), int(lm[12].y * h))
            }
        else:
            results["body_pose"] = None

        return results
