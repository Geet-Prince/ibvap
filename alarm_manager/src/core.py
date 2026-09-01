"""
alarm_manager/src/core.py  (v2 — with adaptive snapshot rate + incident folders)
Owner: Prince
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

from contracts.schema import DetectionResult
from alarm_manager.src.database import init_db, log_activity, log_event
from alarm_manager.src import incident_store

logger = logging.getLogger(__name__)

_RULES_PATH = Path(__file__).resolve().parents[1] / "configs" / "rules.yaml"

# Global WebSocket broadcaster
_alert_subscribers: list = []

def register_subscriber(q: asyncio.Queue) -> None:   _alert_subscribers.append(q)
def unregister_subscriber(q: asyncio.Queue) -> None:
    try: _alert_subscribers.remove(q)
    except ValueError: pass


def _load_rules() -> dict:
    with open(_RULES_PATH) as f:
        return yaml.safe_load(f)


def _danger_label(score: int, t: dict) -> str:
    if score >= t["critical"]: return "CRITICAL"
    if score >= t["high"]:     return "HIGH"
    if score >= t["medium"]:   return "MEDIUM"
    return "LOW"


def _snapshot_interval(score: int) -> float:
    """
    Adaptive snapshot rate — the higher the threat, the faster we capture.
    Score 20-39  → every 2.0 s
    Score 40-59  → every 1.0 s
    Score 60-79  → every 0.5 s
    Score 80+    → every 0.2 s  (near-continuous)
    """
    if score >= 80: return 0.2
    if score >= 60: return 0.5
    if score >= 40: return 1.0
    return 2.0


class AlarmManager:
    def __init__(self):
        init_db()
        cfg = _load_rules()
        self._rules      = cfg["rules"]
        self._thresholds = cfg["thresholds"]
        # track_id → last snapshot unix timestamp
        self._last_snap: dict[str, float] = {}
        self._meta_cache: dict[str, dict] = {}
        self._dirty_meta: set[str] = set()
        self._last_alert: dict[str, float] = {}
        self._last_flush = time.time()
        self._last_known_plates: dict[str, str] = {}
        logger.info("AlarmManager v2 ready with %d rules.", len(self._rules))

    # ── Public API ──────────────────────────────────────────────────────
    def submit(self, result: DetectionResult,
               frame: Optional[np.ndarray] = None) -> None:
        for obj in result.objects:
            score, matched_rule = self._score(result.module, obj.attributes)
            label = _danger_label(score, self._thresholds)

            # Always log to activity_log
            log_activity(
                camera_id=result.camera_id, module=result.module,
                track_id=obj.track_id, object_type=obj.object_type,
                confidence=obj.confidence, bbox=obj.bbox,
                attributes=obj.attributes, frame_id=result.frame_id,
                score=score,
            )

            if score == 0:
                continue

            # Stable incident ID tied to this track on this camera
            incident_id = hashlib.md5(
                f"{result.camera_id}-{obj.track_id}".encode()
            ).hexdigest()[:12]

            # Load or create incident metadata
            if incident_id not in self._meta_cache:
                self._meta_cache[incident_id] = incident_store.load_or_create(
                    incident_id, result.camera_id, result.module, score, label)
            meta = self._meta_cache[incident_id]

            # Enrich metadata with all available signal
            incident_store.enrich_meta(
                meta, result.module, obj.attributes,
                obj.object_type, obj.track_id, score, label)

            # Adaptive snapshot: only capture if enough time has passed
            snapshot_file = None
            if frame is not None and score >= 20:
                interval = _snapshot_interval(score)
                last = self._last_snap.get(obj.track_id, 0.0)
                if time.time() - last >= interval:
                    snapshot_file = incident_store.add_snapshot(
                        incident_id, frame, obj.bbox, meta)
                    self._last_snap[obj.track_id] = time.time()

            # Persist incident JSON
            self._dirty_meta.add(incident_id)
            # Flush dirty cache periodically (e.g. every 1.5 seconds)
            now = time.time()
            if now - self._last_flush > 1.5 and self._dirty_meta:
                for iid in list(self._dirty_meta):
                    incident_store.save(iid, self._meta_cache[iid])
                self._dirty_meta.clear()
                self._last_flush = now

            if matched_rule:
                plate_no = obj.attributes.get("plate_no")
                is_new_plate = plate_no and self._last_known_plates.get(incident_id) != plate_no
                time_since_last = now - self._last_alert.get(incident_id, 0)
                
                # Broadcast and log ONLY if: it's a new incident (>3s since last alert), 
                # OR we just captured a new snapshot, OR we just detected a new license plate
                if time_since_last > 3.0 or snapshot_file or is_new_plate:
                    if plate_no:
                        self._last_known_plates[incident_id] = plate_no
                    self._last_alert[incident_id] = now
                    
                    log_event(
                        event_id=incident_id,
                        event_type=matched_rule.get("event_type", module).upper().replace(" ", "_"),
                        severity=matched_rule["severity"],
                        camera_id=result.camera_id,
                        track_id=obj.track_id,
                        danger_score=score,
                        # If no snapshot this frame, don't overwrite with empty in the DB UPSERT, but upsert needs a value.
                        # Wait, we pass the latest snapshot from meta instead of just this frame's snapshot!
                        snapshot_path=meta["snapshots"][-1] if meta["snapshots"] else "",
                        module=result.module,
                        attributes=obj.attributes,
                    )

                    alert = {
                        "incident_id":    incident_id,
                        "event_type":     matched_rule.get("event_type", module),
                        "severity":       matched_rule["severity"],
                        "danger_label":   label,
                        "danger_score":   score,
                        "camera_id":      result.camera_id,
                        "track_id":       obj.track_id,
                        "module":         result.module,
                        "confidence":     obj.confidence,
                        "bbox":           list(obj.bbox),
                        "snapshot":       meta["snapshots"][-1] if meta["snapshots"] else None,
                        "humans_detected": meta["humans_detected"],
                        "zone_breaches":  meta["zone_breaches"],
                        "activities":     meta["activities_detected"],
                        "timestamp":      result.timestamp_utc.isoformat(),
                        "plate_no":       plate_no,
                    }
                    self._broadcast(alert)

    # ── Scoring ─────────────────────────────────────────────────────────
    def _score(self, module: str, attributes: dict) -> tuple[int, Optional[dict]]:
        best_rule, best_score = None, 0
        for rule in self._rules:
            when = rule.get("when", {})
            if when.get("module") != module:
                continue
            if "attribute" in when:
                val = attributes.get(when["attribute"])
                if when.get("equals") is not None and val != when["equals"]:
                    continue
                if when.get("gte") is not None and (val is None or val < when["gte"]):
                    continue
            
            # Map severity to a base score if 'score' isn't provided
            sev = rule.get("severity", "informational").lower()
            score = rule.get("score")
            if score is None:
                if sev == "critical": score = 90
                elif sev == "high": score = 70
                elif sev == "medium": score = 50
                elif sev == "low": score = 30
                else: score = 10
                
            if score > best_score:
                best_score = score
                best_rule  = rule
        return best_score, best_rule

    # ── Broadcast ───────────────────────────────────────────────────────
    def _broadcast(self, alert: dict) -> None:
        for q in list(_alert_subscribers):
            try: q.put_nowait(alert)
            except asyncio.QueueFull: pass
