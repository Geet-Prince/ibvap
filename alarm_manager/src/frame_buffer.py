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


# Singleton — imported by both api.py and run_ibvap.py
LIVE_FRAME = FrameBuffer()
