"""
alarm_manager/src/core.py
The central AlarmManager — receives DetectionResults from every module,
scores threat level, crops snapshots, logs to DB, and broadcasts alerts.

Owner: Prince
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import yaml

from contracts.schema import DetectionResult
from alarm_manager.src.database import init_db, log_activity, log_event

logger = logging.getLogger(__name__)

_RULES_PATH = Path(__file__).resolve().parents[1] / "configs" / "rules.yaml"
_SNAPSHOT_DIR = Path(__file__).resolve().parents[2] / "storage" / "media" / "snapshots"

# Global broadcaster — FastAPI server registers here
_alert_subscribers: list = []


def register_subscriber(queue: asyncio.Queue) -> None:
    _alert_subscribers.append(queue)


def unregister_subscriber(queue: asyncio.Queue) -> None:
    _alert_subscribers.remove(queue)


def _load_rules() -> dict:
    with open(_RULES_PATH) as f:
        return yaml.safe_load(f)


def _get_danger_label(score: int, thresholds: dict) -> str:
    if score >= thresholds["critical"]:
        return "CRITICAL"
    elif score >= thresholds["high"]:
        return "HIGH"
    elif score >= thresholds["medium"]:
        return "MEDIUM"
    else:
        return "LOW"


def _crop_snapshot(frame: Optional[np.ndarray], bbox: tuple,
                   camera_id: str, track_id: str, event_id: str) -> Optional[str]:
    """Crop the human from the frame and save as JPEG snapshot."""
    if frame is None:
        return None
    _SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    x1, y1, x2, y2 = bbox

    # Add 15% padding around the bbox for better face detection quality
    h, w = frame.shape[:2]
    pad_x = int((x2 - x1) * 0.15)
    pad_y = int((y2 - y1) * 0.15)
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(w, x2 + pad_x)
    y2 = min(h, y2 + pad_y)

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    filename = f"{camera_id}_{track_id}_{event_id}.jpg"
    path = _SNAPSHOT_DIR / filename
    cv2.imwrite(str(path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
    logger.info("Snapshot saved: %s", path)
    return str(path)


class AlarmManager:
    """
    Central hub — every module calls alarm_manager.submit(result).
    This class scores threats, crops snapshots, logs to DB,
    and broadcasts real-time alerts over WebSocket.
    """

    def __init__(self):
        init_db()
        self._config = _load_rules()
        self._rules = self._config["rules"]
        self._thresholds = self._config["thresholds"]
        logger.info("AlarmManager initialized with %d rules.", len(self._rules))

    def submit(self, result: DetectionResult,
               frame: Optional[np.ndarray] = None) -> None:
        """
        Call this with every DetectionResult from every module.
        Optionally pass the raw frame for snapshot cropping.
        """
        for obj in result.objects:
            score, matched_rule = self._score(result.module, obj.attributes)

            # Always log to activity_log
            log_activity(
                camera_id=result.camera_id,
                module=result.module,
                track_id=obj.track_id,
                object_type=obj.object_type,
                confidence=obj.confidence,
                bbox=obj.bbox,
                attributes=obj.attributes,
                frame_id=result.frame_id,
                score=score,
            )

            if matched_rule is None:
                continue

            danger_label = _get_danger_label(score, self._thresholds)
            event_id = hashlib.md5(
                f"{result.camera_id}-{obj.track_id}-{result.frame_id}".encode()
            ).hexdigest()[:12]

            # Crop snapshot if rule requires it
            snapshot_path = None
            if matched_rule.get("capture_snapshot") and frame is not None:
                snapshot_path = _crop_snapshot(
                    frame, obj.bbox, result.camera_id, obj.track_id, event_id
                )

            # Log to events table
            log_event(
                event_id=event_id,
                event_type=matched_rule["name"].upper().replace(" ", "_"),
                severity=matched_rule["severity"],
                camera_id=result.camera_id,
                track_id=obj.track_id,
                danger_score=score,
                snapshot_path=snapshot_path or "",
                module=result.module,
                attributes=obj.attributes,
            )

            # Build alert payload
            alert = {
                "event_id": event_id,
                "event_type": matched_rule["name"],
                "severity": matched_rule["severity"],
                "danger_label": danger_label,
                "danger_score": score,
                "camera_id": result.camera_id,
                "track_id": obj.track_id,
                "module": result.module,
                "confidence": obj.confidence,
                "bbox": list(obj.bbox),
                "snapshot_path": snapshot_path or "",
                "timestamp": result.timestamp_utc.isoformat(),
            }

            logger.warning(
                "[ALERT] %s | Camera: %s | Track: %s | Score: %d (%s)",
                matched_rule["name"], result.camera_id,
                obj.track_id, score, danger_label,
            )

            # Broadcast to all connected WebSocket clients
            self._broadcast(alert)

    def _score(self, module: str, attributes: dict) -> tuple[int, Optional[dict]]:
        """Return (total_score, best_matched_rule)."""
        best_rule = None
        best_score = 0

        for rule in self._rules:
            if rule["module"] != module:
                continue

            # Check attribute condition if present
            if "attribute" in rule:
                attr_val = attributes.get(rule["attribute"])
                if rule.get("equals") is not None and attr_val != rule["equals"]:
                    continue
                if rule.get("gte") is not None and (attr_val is None or attr_val < rule["gte"]):
                    continue

            score = rule["score"]
            if score > best_score:
                best_score = score
                best_rule = rule

        return best_score, best_rule

    def _broadcast(self, alert: dict) -> None:
        """Push alert to all connected WebSocket clients."""
        for queue in list(_alert_subscribers):
            try:
                queue.put_nowait(alert)
            except asyncio.QueueFull:
                pass
