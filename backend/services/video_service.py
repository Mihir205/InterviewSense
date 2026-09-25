import logging
import os
from pathlib import Path
from typing import Iterator, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

class VideoProcessor:
    """
    Handles reading an MP4 video file and yielding frames at a target FPS.
    """
    def __init__(self, video_path: str | Path, target_fps: float = 12.0):
        self.video_path = Path(video_path)
        self.target_fps = target_fps

        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        self.cap = cv2.VideoCapture(str(self.video_path))
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video file: {self.video_path}")

        self.original_fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.original_fps <= 0:
            self.original_fps = 30.0  # fallback

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.total_frames / self.original_fps

        if self.duration < 5.0:
            logger.warning(f"Video duration is very short: {self.duration:.2f}s")

        # Compute how many original frames to skip to match target_fps
        # E.g., original=30, target=10 -> frame_interval = 3
        if self.target_fps > self.original_fps:
            self.target_fps = self.original_fps
            self.frame_interval = 1
        else:
            self.frame_interval = int(round(self.original_fps / self.target_fps))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cap and self.cap.isOpened():
            self.cap.release()
        return False  # don't suppress exceptions

    def process_frames(self) -> Iterator[Tuple[np.ndarray, float, int]]:
        """
        Yields (frame_bgr, timestamp_sec, original_frame_index)
        """
        frame_idx = 0
        extracted_count = 0

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            if frame_idx % self.frame_interval == 0:
                timestamp_sec = frame_idx / self.original_fps
                yield frame, timestamp_sec, frame_idx
                extracted_count += 1

            frame_idx += 1

        self.cap.release()
        logger.info(f"Finished extracting {extracted_count} frames from {self.video_path.name}")
