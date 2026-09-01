"""
human_tracking/inference/tracker.py
=======================================
THE PUBLIC API for the Human Tracking module.

Owner: Prince
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Tuple

import yaml

from contracts import DetectedObject, DetectionResult

logger = logging.getLogger(__name__)

_MODULE_DIR = Path(__file__).resolve().parents[1]
_CONFIG_PATH = _MODULE_DIR / "configs" / "config.yaml"


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


class HumanTracker:
    """
    Consumes DetectionResults from Human Detection and assigns stable track IDs.
    """

    def __init__(self, config_override: Optional[dict] = None):
        cfg = _load_config()
        if config_override:
            for key, value in config_override.items():
                if isinstance(value, dict) and key in cfg:
                    cfg[key].update(value)
                else:
                    cfg[key] = value

        self._cfg = cfg
        self._tracker = None
        self._track_history: Dict[str, Tuple[int, int]] = {}
        self._last_timestamp: Optional[datetime] = None
        self._init_tracker()

    def _init_tracker(self):
        try:
            from deep_sort_realtime.deepsort_tracker import DeepSort
            self._tracker = DeepSort(
                max_age=self._cfg["tracker"]["max_age"],
                n_init=self._cfg["tracker"]["n_init"],
                nms_max_overlap=self._cfg["tracker"]["nms_max_overlap"],
                embedder=None,  # CRITICAL FIX: Disables CPU-heavy ReID CNN (saves 400ms!)
            )
        except ImportError:
            logger.warning("deep-sort-realtime not installed. Run: pip install deep-sort-realtime")

    def track(self, detection_result: DetectionResult) -> DetectionResult:
        """
        Process a DetectionResult and assign stable track IDs.
        """
        if detection_result.module != "human_detection":
            raise ValueError("Tracker expects DetectionResult from 'human_detection'")

        if not self._tracker:
            self._init_tracker()
            if not self._tracker:
                return detection_result # Fallback, return as is if no tracker

        # Format detections for deep_sort_realtime:
        # [ [ [left,top,w,h], confidence, detection_class ], ... ]
        bbs = []
        for obj in detection_result.objects:
            x1, y1, x2, y2 = obj.bbox
            w = x2 - x1
            h = y2 - y1
            bbs.append(([x1, y1, w, h], obj.confidence, obj.object_type))
            
        # Provide identical dummy embeddings so ReID distance is always 0.
        # This forces the Hungarian algorithm to match purely based on bounding box IoU/Kalman distance!
        import numpy as np
        dummy_embeds = [np.ones(128, dtype=np.float32)] * len(bbs)
        
        tracks = self._tracker.update_tracks(bbs, embeds=dummy_embeds)

        current_timestamp = detection_result.timestamp_utc
        dt = 0.0
        if self._last_timestamp:
            dt = (current_timestamp - self._last_timestamp).total_seconds()
        self._last_timestamp = current_timestamp

        tracked_objects = []
        prefix = self._cfg["output"]["track_id_prefix"]

        for track in tracks:
            if not track.is_confirmed():
                continue
            
            track_id = f"{prefix}-{track.track_id}"
            ltrb = track.to_ltrb()
            x1, y1, x2, y2 = int(ltrb[0]), int(ltrb[1]), int(ltrb[2]), int(ltrb[3])
            
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            
            vx, vy = 0.0, 0.0
            if track_id in self._track_history and dt > 0:
                prev_cx, prev_cy = self._track_history[track_id]
                vx = (cx - prev_cx) / dt
                vy = (cy - prev_cy) / dt
            
            self._track_history[track_id] = (cx, cy)
            
            tracked_objects.append(
                DetectedObject(
                    object_type="human",
                    track_id=track_id,
                    confidence=track.det_conf if track.det_conf is not None else 1.0,
                    bbox=(x1, y1, x2, y2),
                    attributes={
                        "centroid": (cx, cy),
                        "velocity_px_per_s": (round(vx, 2), round(vy, 2))
                    }
                )
            )

        return DetectionResult(
            module="human_tracking",
            camera_id=detection_result.camera_id,
            frame_id=detection_result.frame_id,
            timestamp_utc=detection_result.timestamp_utc,
            objects=tracked_objects,
        )

    def predict_only(self, camera_id: str, frame_id: int, timestamp_utc: datetime) -> DetectionResult:
        """
        Advances the Kalman filter state (extrapolating bounding boxes) 
        without matching new detections. Used on skipped frames for smooth video.
        """
        if not self._tracker or not hasattr(self._tracker, 'tracker'):
            return DetectionResult("human_tracking", camera_id, frame_id, timestamp_utc, [])
            
        # Advance kalman filters
        self._tracker.tracker.predict()
        
        tracked_objects = []
        prefix = self._cfg["output"]["track_id_prefix"]
        
        dt = 0.0
        if self._last_timestamp:
            dt = (timestamp_utc - self._last_timestamp).total_seconds()
        self._last_timestamp = timestamp_utc
        
        # We manually extract the extrapolated tracks
        for track in self._tracker.tracker.tracks:
            if not track.is_confirmed() or track.time_since_update > 1:
                continue
                
            track_id = f"{prefix}-{track.track_id}"
            ltrb = track.to_ltrb()
            x1, y1, x2, y2 = int(ltrb[0]), int(ltrb[1]), int(ltrb[2]), int(ltrb[3])
            
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            
            vx, vy = 0.0, 0.0
            if track_id in self._track_history and dt > 0:
                prev_cx, prev_cy = self._track_history[track_id]
                vx = (cx - prev_cx) / dt
                vy = (cy - prev_cy) / dt
                
            self._track_history[track_id] = (cx, cy)
            
            tracked_objects.append(
                DetectedObject(
                    object_type="human",
                    track_id=track_id,
                    confidence=1.0,
                    bbox=(x1, y1, x2, y2),
                    attributes={
                        "centroid": (cx, cy),
                        "velocity_px_per_s": (round(vx, 2), round(vy, 2))
                    }
                )
            )
            
        return DetectionResult(
            module="human_tracking",
            camera_id=camera_id,
            frame_id=frame_id,
            timestamp_utc=timestamp_utc,
            objects=tracked_objects,
        )
