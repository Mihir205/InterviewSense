"""
ffmpeg_utils.py
---------------
Thin helper around the ffmpeg-python library for video conversion tasks.

The backend receives uploads in WebM (Chrome/Firefox default) or MP4 (Safari).
All downstream analysis code expects MP4 (H.264), so conversion is applied when
the input format differs.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

import ffmpeg

logger = logging.getLogger(__name__)


def get_video_duration(input_path: str | Path) -> float:
    """
    Return the duration of a video file in seconds using ffprobe.

    Raises
    ------
    RuntimeError
        If ffprobe cannot read the file or the duration field is missing.
    """
    try:
        probe = ffmpeg.probe(str(input_path))
        duration = float(probe["format"]["duration"])
        return duration
    except (ffmpeg.Error, KeyError, ValueError) as exc:
        raise RuntimeError(
            f"Could not determine duration of {input_path}: {exc}"
        ) from exc


def convert_to_mp4(input_path: str | Path, output_path: str | Path) -> Path:
    """
    Convert *input_path* to MP4 (H.264 video, AAC audio) at *output_path*.

    If the input is already an MP4 the streams are copied without re-encoding
    (fast, lossless).  Otherwise the video is re-encoded with libx264.

    Parameters
    ----------
    input_path:
        Path to the source video (e.g. a .webm file from the browser).
    output_path:
        Destination path for the converted file (should end with .mp4).

    Returns
    -------
    Path
        The resolved output path on success.

    Raises
    ------
    RuntimeError
        If FFmpeg exits with a non-zero status code.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    is_mp4 = input_path.suffix.lower() == ".mp4"

    try:
        stream = ffmpeg.input(str(input_path))

        if is_mp4:
            # Stream-copy — no re-encoding, very fast
            logger.info("Input is already MP4 — copying streams: %s", input_path)
            out = ffmpeg.output(
                stream,
                str(output_path),
                vcodec="copy",
                acodec="copy",
            )
        else:
            # Re-encode to H.264 + AAC
            logger.info(
                "Converting %s → %s (libx264)", input_path.suffix, output_path
            )
            out = ffmpeg.output(
                stream,
                str(output_path),
                vcodec="libx264",
                acodec="aac",
                crf=23,          # Constant rate factor — 18 (best) to 28 (worst)
                preset="fast",   # Encoding speed vs compression trade-off
                movflags="+faststart",  # Optimise for streaming / web playback
            )

        ffmpeg.run(out, overwrite_output=True, quiet=True)
        logger.info("Conversion complete: %s", output_path)
        return output_path

    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        raise RuntimeError(
            f"FFmpeg conversion failed for {input_path}:\n{stderr}"
        ) from exc


def verify_ffmpeg_available() -> bool:
    """
    Return True if the `ffmpeg` CLI binary is accessible on PATH.

    Call this during application startup to give an early, clear error rather
    than a confusing failure during analysis.
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
