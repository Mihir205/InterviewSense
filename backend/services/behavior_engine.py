import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)

@dataclass
class Moment:
    timestamp_sec: float
    type: str  # "strong" or "weak"
    label: str
    description: str

class BehaviorEngine:
    """
    Fuses raw metric streams over time to compute engagement scores and detect moments.
    """
    def __init__(self, fps: float = 12.0):
        self.fps = fps
        self.ema_alpha = 0.2  # Smoothing factor

    def _apply_ema(self, series: List[float], alpha: float) -> List[float]:
        """Applies Exponential Moving Average to a sequence of floats."""
        if not series:
            return []
        smoothed = [series[0]]
        for val in series[1:]:
            smoothed.append(alpha * val + (1 - alpha) * smoothed[-1])
        return smoothed

    def _rolling_std(self, series: List[float], window_size: int) -> List[float]:
        """Computes rolling standard deviation."""
        stds = []
        for i in range(len(series)):
            start_idx = max(0, i - window_size + 1)
            window = series[start_idx:i+1]
            if len(window) > 1:
                stds.append(np.std(window))
            else:
                stds.append(0.0)
        return stds

    def analyze_session(self, frames_data: List[Dict], baseline_mean_ear: float = 0.21) -> Dict:
        """
        Process the entire sequence of frame metrics for a session.
        frames_data format: [{"timestamp_sec": float, "metrics": {...}}, ...]
        """
        if not frames_data:
            return {}

        n_frames = len(frames_data)
        window_30 = max(1, int(self.fps * 2)) # ~2 seconds
        
        # 1. Temporal Smoothing (EMA)
        raw_yaw = [f["metrics"]["head_yaw"] for f in frames_data]
        raw_pitch = [f["metrics"]["head_pitch"] for f in frames_data]
        raw_roll = [f["metrics"]["head_roll"] for f in frames_data]
        raw_ear = [f["metrics"]["ear"] for f in frames_data]
        raw_mar = [f["metrics"]["mar"] for f in frames_data]
        raw_tilt = [f["metrics"]["shoulder_tilt"] for f in frames_data]
        raw_contact = [1.0 if f["metrics"]["is_eye_contact"] else 0.0 for f in frames_data]

        smooth_yaw = self._apply_ema(raw_yaw, self.ema_alpha)
        smooth_pitch = self._apply_ema(raw_pitch, self.ema_alpha)
        smooth_roll = self._apply_ema(raw_roll, self.ema_alpha)
        smooth_ear = self._apply_ema(raw_ear, self.ema_alpha)
        smooth_mar = self._apply_ema(raw_mar, self.ema_alpha)
        smooth_tilt = self._apply_ema(raw_tilt, self.ema_alpha)

        # 2. Compute higher-level features per frame
        # Head stability: lower std dev of smoothed angles = more stable (score 1.0)
        std_yaw = self._rolling_std(smooth_yaw, window_30)
        std_pitch = self._rolling_std(smooth_pitch, window_30)
        std_roll = self._rolling_std(smooth_roll, window_30)
        
        head_stability_scores = []
        for sy, sp, sr in zip(std_yaw, std_pitch, std_roll):
            # Normalize: std > 5 degrees is very unstable (0.0), 0 is perfect (1.0)
            avg_std = (sy + sp + sr) / 3.0
            score = max(0.0, 1.0 - (avg_std / 5.0))
            head_stability_scores.append(score)

        # Posture score (1 = upright, 0 = tilted/slouching)
        posture_scores = []
        for t in smooth_tilt:
            score = max(0.0, 1.0 - (abs(t) / 15.0)) # >15 deg tilt = 0
            posture_scores.append(score)

        # Blink rate & Mouth Activity
        # Simple thresholding for mouth
        mouth_activity = [1.0 if m > 0.05 else 0.0 for m in smooth_mar]
        
        # Blinks (state machine on raw or smooth EAR)
        blink_count = 0
        is_closed = False
        blinks_per_frame = [0] * n_frames
        closure_threshold = baseline_mean_ear * 0.8
        
        for i, ear in enumerate(smooth_ear):
            if ear < closure_threshold and not is_closed:
                is_closed = True
            elif ear >= closure_threshold and is_closed:
                is_closed = False
                blink_count += 1
                blinks_per_frame[i] = 1

        duration_min = max(0.1, n_frames / self.fps / 60.0)
        overall_blink_rate = blink_count / duration_min

        # Rolling blink rate (60s window)
        window_60s = int(self.fps * 60)
        rolling_blink_rates = []
        for i in range(n_frames):
            start = max(0, i - window_60s + 1)
            b_count = sum(blinks_per_frame[start:i+1])
            w_min = max(0.1, (i - start + 1) / self.fps / 60.0)
            rolling_blink_rates.append(b_count / w_min)

        # Normalize blink rate to [0, 1] score. Ideal is 15-20. 
        # Punish < 5 or > 30.
        blink_scores = []
        for br in rolling_blink_rates:
            if 10 <= br <= 25: score = 1.0
            elif br < 10: score = max(0.0, br / 10.0)
            else: score = max(0.0, 1.0 - ((br - 25.0) / 25.0))
            blink_scores.append(score)

        # 3. Rule-Based Weighted Engagement Scoring
        # Eye contact 35 %, Head stability 25 %, Posture 20 %, Blink 10 %, Mouth 10 %
        rolling_engagement = []
        for i in range(n_frames):
            score = (
                raw_contact[i] * 35.0 +
                head_stability_scores[i] * 25.0 +
                posture_scores[i] * 20.0 +
                blink_scores[i] * 10.0 +
                mouth_activity[i] * 10.0
            )
            rolling_engagement.append(score)
            
        overall_engagement = float(np.mean(rolling_engagement))

        # 4. Moment Detection
        moments = self._detect_moments(
            frames_data, raw_contact, head_stability_scores, posture_scores, 
            smooth_yaw, smooth_pitch, smooth_tilt, rolling_blink_rates, mouth_activity
        )

        # Store smoothed data back into frames_data for DB persistence
        for i, f in enumerate(frames_data):
            f["smoothed_metrics"] = {
                "head_yaw": smooth_yaw[i],
                "head_pitch": smooth_pitch[i],
                "head_roll": smooth_roll[i],
                "ear": smooth_ear[i],
                "mar": smooth_mar[i],
                "shoulder_tilt": smooth_tilt[i]
            }
            f["scores"] = {
                "head_stability": head_stability_scores[i],
                "posture": posture_scores[i],
                "engagement": rolling_engagement[i]
            }

        # 5. Session Summary
        summary = {
            "eye_contact_pct": float(np.mean(raw_contact)) * 100,
            "blink_rate": overall_blink_rate,
            "avg_head_stability": float(np.mean(head_stability_scores)),
            "avg_mouth_activity": float(np.mean(mouth_activity)),
            "avg_posture_score": float(np.mean(posture_scores)),
            "engagement_score": overall_engagement
        }

        return {
            "frames": frames_data,
            "summary": summary,
            "moments": [m.__dict__ for m in moments]
        }

    def _detect_moments(self, frames, contact, stability, posture, yaw, pitch, tilt, blinks, mouth) -> List[Moment]:
        moments = []
        n = len(frames)
        window_5s = int(self.fps * 5)
        window_3s = int(self.fps * 3)
        
        # Fast way to find contiguous runs
        def get_runs(condition_array, min_len):
            runs = []
            current_start = -1
            for i, val in enumerate(condition_array):
                if val:
                    if current_start == -1: current_start = i
                else:
                    if current_start != -1:
                        if i - current_start >= min_len:
                            runs.append((current_start, i-1))
                        current_start = -1
            if current_start != -1 and n - current_start >= min_len:
                runs.append((current_start, n-1))
            return runs

        # Strong: Eye contact sustained > 90% for > 5s
        contact_runs = get_runs(np.array(contact) > 0, window_5s)
        for s, e in contact_runs:
            moments.append(Moment(frames[s]["timestamp_sec"], "strong", "Great Eye Contact", "Maintained solid eye contact for several seconds."))

        # Strong: Stable head & upright posture > 5s
        stable_runs = get_runs((np.array(stability) > 0.8) & (np.array(posture) > 0.8), window_5s)
        for s, e in stable_runs:
            moments.append(Moment(frames[s]["timestamp_sec"], "strong", "Good Posture", "Showed confident, stable posture."))

        # Weak: Eye contact drops > 3s
        no_contact_runs = get_runs(np.array(contact) == 0, window_3s)
        for s, e in no_contact_runs:
            moments.append(Moment(frames[s]["timestamp_sec"], "weak", "Lost Eye Contact", "Looked away from the camera for an extended period."))
            
        # Weak: Head yaw > 20 or pitch > 15 sustained > 3s
        bad_head_runs = get_runs((np.abs(np.array(yaw)) > 20) | (np.abs(np.array(pitch)) > 15), window_3s)
        for s, e in bad_head_runs:
            moments.append(Moment(frames[s]["timestamp_sec"], "weak", "Distracted Head Pose", "Head was turned significantly away from center."))

        # Weak: Posture tilted (shoulder > 10) > 3s
        bad_posture_runs = get_runs(np.abs(np.array(tilt)) > 10, window_3s)
        for s, e in bad_posture_runs:
            moments.append(Moment(frames[s]["timestamp_sec"], "weak", "Tilted Posture", "Shoulders were visibly leaning or tilted."))

        # Simple NMS: remove overlapping moments of the same type within 5 seconds
        moments.sort(key=lambda x: x.timestamp_sec)
        filtered = []
        for m in moments:
            if not filtered:
                filtered.append(m)
            else:
                last_m = filtered[-1]
                if m.type == last_m.type and (m.timestamp_sec - last_m.timestamp_sec) < 5.0:
                    continue # skip overlap
                filtered.append(m)
                
        return filtered
