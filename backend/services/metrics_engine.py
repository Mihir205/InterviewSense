import math
from typing import Dict, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np

from backend.services.cv_pipeline import CalibrationBaseline

class MetricsEngine:
    """
    Computes behavioral metrics from raw CV pipeline outputs.
    """
    def __init__(self):
        # 3D generic face model points for PnP
        # Coordinates roughly correspond to a generic human face
        self.model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip 33
            (0.0, -330.0, -65.0),        # Chin 8
            (-225.0, 170.0, -135.0),     # Left eye left corner 36
            (225.0, 170.0, -135.0),      # Right eye right corner 45
            (-150.0, -150.0, -125.0),    # Left Mouth corner 48
            (150.0, -150.0, -125.0)      # Right mouth corner 54
        ])
        
        # Initialize MediaPipe Face Mesh for gaze fallback if needed
        self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        self.gaze_fallback_mode = False
        self.gaze_failures = 0

    def compute_all_metrics(self, frame_bgr: np.ndarray, cv_results: Dict, baseline: Optional[CalibrationBaseline] = None) -> Dict:
        """
        Computes all Phase 3 metrics for a single frame.
        """
        metrics = {
            "head_yaw": 0.0,
            "head_pitch": 0.0,
            "head_roll": 0.0,
            "ear": 0.0,
            "mar": 0.0,
            "shoulder_tilt": 0.0,
            "head_offset": 0.0,
            "is_eye_contact": False
        }

        landmarks = cv_results.get("landmarks_68")
        body_pose = cv_results.get("body_pose")

        if landmarks is not None:
            # 1. Head Pose
            h, w = frame_bgr.shape[:2]
            yaw, pitch, roll = self._compute_head_pose(landmarks, w, h)
            
            if baseline:
                yaw -= baseline.mean_head_yaw
                pitch -= baseline.mean_head_pitch
                roll -= baseline.mean_head_roll
                
            metrics["head_yaw"] = yaw
            metrics["head_pitch"] = pitch
            metrics["head_roll"] = roll

            # 2. EAR
            metrics["ear"] = self._compute_ear(landmarks)

            # 3. MAR
            metrics["mar"] = self._compute_mar(landmarks)

            # 4. Gaze / Eye Contact
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            is_contact = self._compute_eye_contact(gray, landmarks, yaw, pitch, frame_bgr)
            metrics["is_eye_contact"] = is_contact

        if body_pose is not None:
            # 5. Posture
            tilt, offset = self._compute_posture(body_pose)
            if baseline:
                tilt -= baseline.mean_shoulder_tilt
                # head offset is absolute, compare to baseline later
            metrics["shoulder_tilt"] = tilt
            metrics["head_offset"] = offset

        return metrics

    def _compute_head_pose(self, landmarks: np.ndarray, frame_width: int, frame_height: int) -> Tuple[float, float, float]:
        """
        Computes head pose using solvePnP. Returns (yaw, pitch, roll) in degrees.
        """
        image_points = np.array([
            landmarks[33],  # Nose tip
            landmarks[8],   # Chin
            landmarks[36],  # Left eye left corner
            landmarks[45],  # Right eye right corner
            landmarks[48],  # Left mouth corner
            landmarks[54]   # Right mouth corner
        ], dtype="double")

        focal_length = frame_width
        center = (frame_width / 2, frame_height / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype="double")

        dist_coeffs = np.zeros((4, 1))

        success, rotation_vector, translation_vector = cv2.solvePnP(
            self.model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return 0.0, 0.0, 0.0

        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        # Decompose rotation matrix into Euler angles
        sy = math.sqrt(rotation_matrix[0, 0] * rotation_matrix[0, 0] + rotation_matrix[1, 0] * rotation_matrix[1, 0])
        singular = sy < 1e-6

        if not singular:
            pitch = math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
            yaw = math.atan2(-rotation_matrix[2, 0], sy)
            roll = math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
        else:
            pitch = math.atan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
            yaw = math.atan2(-rotation_matrix[2, 0], sy)
            roll = 0

        # Convert to degrees
        pitch = math.degrees(pitch)
        yaw = math.degrees(yaw)
        roll = math.degrees(roll)

        return yaw, pitch, roll

    def _compute_ear(self, landmarks: np.ndarray) -> float:
        """
        Computes Eye Aspect Ratio (EAR).
        """
        def eye_aspect_ratio(eye_pts):
            A = np.linalg.norm(eye_pts[1] - eye_pts[5])
            B = np.linalg.norm(eye_pts[2] - eye_pts[4])
            C = np.linalg.norm(eye_pts[0] - eye_pts[3])
            return (A + B) / (2.0 * C)

        left_eye = landmarks[36:42]
        right_eye = landmarks[42:48]

        ear_left = eye_aspect_ratio(left_eye)
        ear_right = eye_aspect_ratio(right_eye)
        return (ear_left + ear_right) / 2.0

    def _compute_mar(self, landmarks: np.ndarray) -> float:
        """
        Computes Mouth Aspect Ratio (MAR) using inner lip (60-67).
        """
        inner_lip = landmarks[60:68]
        # 60=left, 64=right. Top: 61, 62, 63. Bottom: 67, 66, 65
        A = np.linalg.norm(inner_lip[1] - inner_lip[7])
        B = np.linalg.norm(inner_lip[2] - inner_lip[6])
        C = np.linalg.norm(inner_lip[3] - inner_lip[5])
        D = np.linalg.norm(inner_lip[0] - inner_lip[4])
        
        if D == 0:
            return 0.0
        return (A + B + C) / (2.0 * D)

    def _compute_eye_contact(self, gray: np.ndarray, landmarks: np.ndarray, yaw: float, pitch: float, frame_bgr: np.ndarray) -> bool:
        """
        Estimates if the user is looking at the camera.
        Uses MediaPipe Face Mesh as a robust fallback.
        """
        if self.gaze_fallback_mode:
            return self._mediapipe_gaze(frame_bgr, yaw, pitch)

        # Iris localization (Primary)
        try:
            is_contact = True
            for eye_indices in [range(36, 42), range(42, 48)]:
                eye_pts = landmarks[eye_indices]
                x_min = max(0, np.min(eye_pts[:, 0]) - 5)
                x_max = min(gray.shape[1], np.max(eye_pts[:, 0]) + 5)
                y_min = max(0, np.min(eye_pts[:, 1]) - 5)
                y_max = min(gray.shape[0], np.max(eye_pts[:, 1]) + 5)
                
                eye_crop = gray[y_min:y_max, x_min:x_max]
                if eye_crop.size == 0:
                    continue
                
                # Simple adaptive threshold
                _, thresh = cv2.threshold(eye_crop, 40, 255, cv2.THRESH_BINARY_INV)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if not contours:
                    self.gaze_failures += 1
                    continue
                    
                largest_contour = max(contours, key=cv2.contourArea)
                M = cv2.moments(largest_contour)
                if M["m00"] == 0:
                    self.gaze_failures += 1
                    continue
                    
                cx = int(M["m10"] / M["m00"])
                # Compare centroid cx to center of eye crop
                center_offset = (cx / eye_crop.shape[1]) - 0.5
                
                # Combine with head pose (naive gaze estimation)
                # If head is turned, iris needs to be offset in opposite direction to maintain contact
                gaze_yaw = center_offset + (yaw / 100.0)
                
                if abs(gaze_yaw) > 0.3 or abs(pitch) > 20.0:
                    is_contact = False
            
            if self.gaze_failures > 30:
                self.gaze_fallback_mode = True
                
            return is_contact
        except Exception:
            self.gaze_failures += 1
            if self.gaze_failures > 30:
                self.gaze_fallback_mode = True
            return False

    def _mediapipe_gaze(self, frame_bgr: np.ndarray, yaw: float, pitch: float) -> bool:
        """Fallback gaze logic using MediaPipe face mesh (iris landmarks)"""
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.mp_face_mesh.process(frame_rgb)
        
        if not results.multi_face_landmarks:
            return False
            
        landmarks = results.multi_face_landmarks[0].landmark
        
        # simplified check using iris center vs eye corners
        left_iris = landmarks[468] 
        left_eye_inner = landmarks[133]
        left_eye_outer = landmarks[33]
        
        eye_width = abs(left_eye_outer.x - left_eye_inner.x)
        if eye_width == 0: return False
        
        iris_pos = (left_iris.x - left_eye_outer.x) / eye_width
        
        # Compensate for head pose
        gaze_yaw = (iris_pos - 0.5) + (yaw / 100.0)
        
        return abs(gaze_yaw) < 0.2 and abs(pitch) < 15.0

    def _compute_posture(self, body_pose: Dict) -> Tuple[float, float]:
        """
        Computes shoulder tilt and head vertical offset.
        Returns (tilt_degrees, head_offset_ratio)
        """
        ls = body_pose["left_shoulder"]
        rs = body_pose["right_shoulder"]
        nose = body_pose["nose"]

        dx = rs[0] - ls[0]
        dy = rs[1] - ls[1]
        
        # Shoulder tilt in degrees
        tilt = math.degrees(math.atan2(dy, dx))
        # Usually shoulders are horizontal, so tilt near 0 or 180 depending on order.
        # Ensure it's around 0
        if tilt > 90: tilt -= 180
        elif tilt < -90: tilt += 180

        # Head offset ratio: distance from nose to midpoint of shoulders, normalized by shoulder width
        shoulder_width = math.hypot(dx, dy)
        midpoint_y = (ls[1] + rs[1]) / 2.0
        
        if shoulder_width == 0:
            offset = 0.0
        else:
            offset = (midpoint_y - nose[1]) / shoulder_width
            
        return tilt, offset
