"""
alarm_manager/src/frame_buffer.py
Thread-safe global frame store — shared between camera loop and MJPEG stream.
Owner: Prince
"""
from __future__ import annotations
import threading
import time
import cv2
import numpy as np
from typing import Optional

class FrameBuffer:
    """Stores the latest JPEG frame bytes from the camera for MJPEG streaming."""
    def __init__(self):
        self._lock = threading.Lock()
        self._frame_bytes: Optional[bytes] = None
        self._updated_at: float = 0.0
        # Live per-frame telemetry, fed by the camera loop each frame.
        self._humans: int = 0
        self._frame_id: int = 0
        self._live_updated_at: float = 0.0

    def write(self, frame: np.ndarray) -> None:
        """Call this from the camera loop with every raw BGR frame."""
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        with self._lock:
            self._frame_bytes = buf.tobytes()
            self._updated_at = time.time()

    def read(self) -> Optional[bytes]:
        with self._lock:
            return self._frame_bytes

    def is_fresh(self, max_age_s: float = 3.0) -> bool:
        return (time.time() - self._updated_at) < max_age_s

    def set_live(self, humans: int, frame_id: int) -> None:
        """Camera loop pushes the CURRENT frame's inferred human count here."""
        with self._lock:
            self._humans = int(humans)
            self._frame_id = int(frame_id)
            self._live_updated_at = time.time()

    def live(self, max_age_s: float = 3.0) -> dict:
        """Best-effort read of the latest per-frame count. If no pipeline
        (or none recently) this reports live=False so callers can show an
        unknown state instead of a silent, misleading 0."""
        with self._lock:
            humans = self._humans
            frame_id = self._frame_id
            updated = self._live_updated_at
        live = updated > 0 and (time.time() - updated) < max_age_s
        return {
            "humans": humans,
            "frame_id": frame_id,
            "updated_at": updated,
            "live": live,
        }


# Singleton — imported by both api.py and run_ibvap.py
LIVE_FRAME = FrameBuffer()
