"""
human_detection/inference/video_input.py
==========================================
Video Input Layer — reads frames from a camera or video file and
drives the HumanDetector + AlarmManager pipeline.

This is the entry point for running human detection on a real camera.
It is NOT the detector itself — it handles the stream loop, frame skipping,
and graceful shutdown.

Architecture position: sits between the camera and HumanDetector.
Every other AI module has an equivalent video_input.py or receives its
input from upstream module output (e.g. Virtual Fence reads tracking results).

Owner: Prince
"""

from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

import cv2
import yaml

from .detector import HumanDetector

logger = logging.getLogger(__name__)

_MODULE_DIR = Path(__file__).resolve().parents[1]
_SYS_CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "system.yaml"


def _load_system_config() -> dict:
    with open(_SYS_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


class VideoInputLayer:
    """
    Reads frames from an RTSP stream, video file, or webcam and submits
    DetectionResults to the AlarmManager in a tight loop.

    Parameters
    ----------
    camera_id  : Must match a camera.id in configs/system.yaml
    source     : RTSP URL, video file path, or webcam index (int).
                 If None, the URL is looked up from system.yaml by camera_id.
    alarm_manager : Any object with a .submit(DetectionResult) method.
    frame_skip : Process every (frame_skip + 1)th frame (0 = every frame).
    detector   : Optional pre-constructed HumanDetector (for testing).
    """

    def __init__(
        self,
        camera_id: str,
        alarm_manager,
        source: Optional[Union[str, int]] = None,
        frame_skip: int = 0,
        detector: Optional[HumanDetector] = None,
    ):
        self.camera_id = camera_id
        self.alarm_manager = alarm_manager
        self.frame_skip = frame_skip
        self._detector = detector or HumanDetector()
        self._running = False

        if source is None:
            source = self._lookup_source(camera_id)
        self.source = source

    def _lookup_source(self, camera_id: str) -> str:
        cfg = _load_system_config()
        for cam in cfg.get("cameras", []):
            if cam["id"] == camera_id:
                return cam["rtsp_url"]
        raise ValueError(
            f"camera_id '{camera_id}' not found in configs/system.yaml. "
            "Add it under the 'cameras' list."
        )

    # ── Signal handling ───────────────────────────────────────────────────────

    def _register_shutdown(self) -> None:
        """Gracefully stop on Ctrl+C or SIGTERM."""
        def _handler(sig, frame):
            logger.info("Shutdown signal received — stopping VideoInputLayer.")
            self._running = False

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """
        Open the video source and run the detect → submit loop until stopped.

        Logs a warning (but doesn't crash) if a frame read fails — handles
        the intermittent RTSP hiccups common at remote outposts.
        """
        self._register_shutdown()
        cap = cv2.VideoCapture(self.source)

        if not cap.isOpened():
            raise RuntimeError(
                f"Cannot open video source: {self.source}. "
                "Check the RTSP URL or file path."
            )

        logger.info(
            "VideoInputLayer started | camera=%s | source=%s",
            self.camera_id,
            self.source,
        )

        frame_id = 0
        skip_counter = 0
        self._running = True

        try:
            while self._running:
                ret, frame = cap.read()

                if not ret:
                    logger.warning(
                        "Frame read failed on %s (frame_id=%d) — retrying in 1s.",
                        self.camera_id,
                        frame_id,
                    )
                    time.sleep(1.0)
                    # Re-open the stream — handles RTSP reconnects
                    cap.release()
                    cap = cv2.VideoCapture(self.source)
                    continue

                frame_id += 1

                # Frame skipping — reduces CPU/GPU load without changing the API
                if skip_counter < self.frame_skip:
                    skip_counter += 1
                    continue
                skip_counter = 0

                timestamp = datetime.now(timezone.utc)
                result = self._detector.detect(
                    frame=frame,
                    camera_id=self.camera_id,
                    frame_id=frame_id,
                    timestamp_utc=timestamp,
                )

                self.alarm_manager.submit(result)

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "frame=%d | camera=%s | humans=%d",
                        frame_id,
                        self.camera_id,
                        len(result.objects),
                    )
        finally:
            cap.release()
            logger.info("VideoInputLayer stopped | camera=%s", self.camera_id)

    def run_on_file(self, video_path: Union[str, Path]) -> list:
        """
        Run detection on every frame of a video file and return all results.
        Useful for offline evaluation and integration tests.

        Parameters
        ----------
        video_path : Path to an .mp4 / .avi video file.

        Returns
        -------
        List of DetectionResult, one per processed frame.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video file: {video_path}")

        all_results = []
        frame_id = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_id += 1
                timestamp = datetime.now(timezone.utc)
                result = self._detector.detect(frame, self.camera_id, frame_id, timestamp)
                all_results.append(result)
        finally:
            cap.release()

        logger.info(
            "run_on_file complete | %d frames processed | %s",
            frame_id,
            video_path,
        )
        return all_results
