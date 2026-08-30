# 🧠 IBVAP — Data Flow & Storage Architecture

> **Author:** Antigravity AI (Project Manager)  
> **Owner:** Prince (geet-prince)  
> **Repo:** https://github.com/Geet-Prince/ibvap  
> **Last Updated:** 2026-08-31

This document explains exactly how data is created, enriched, stored, and accessed across the entire IBVAP system. Every AI assistant on the team must read this before writing any code.

---

## 1. The Universal Data Packet — `DetectionResult`

Every single module in this system communicates using **one and only one** data structure:

```python
# contracts/schema.py
class DetectedObject(BaseModel):
    object_type:  str        # "human" or "vehicle"
    track_id:     str        # Stable ID, e.g. "h-1", "veh-3"
    bbox:         list       # [x1, y1, x2, y2] in pixels
    confidence:   float      # 0.0 – 1.0
    attributes:   dict       # Module-specific data (see below)

class DetectionResult(BaseModel):
    module:        str       # Which module last processed this
    camera_id:     str       # e.g. "CAM_LIVE"
    frame_id:      int
    timestamp_utc: datetime
    objects:       list[DetectedObject]
```

The `attributes` dict is how modules talk to each other without coupling:

| Attribute Key | Set By | Value Example |
|---|---|---|
| `centroid` | HumanTracker | `(320, 240)` |
| `velocity_px_per_s` | HumanTracker | `(12.5, -3.2)` |
| `activity` | SuspiciousDetector | `"loitering"`, `"crowd_formation"`, `"erratic_movement"` |
| `zone_state` | VirtualFence | `"inside"` |
| `zone_id` | VirtualFence | `"border_fence"` |
| `vehicle_type` | VehicleANPR | `"car"`, `"truck"`, `"motorcycle"`, `"bus"` |
| `plate_no` | VehicleANPR | `"DETECTED-87"` |
| `face_captured` | FaceAnalysis (Phase 2) | `True` |
| `watchlist_match` | ANPR (Phase 2) | `True` |

---

## 2. How Data Flows Through the Pipeline

Every video frame is processed by each module **in sequence**. Each module enriches the same result object and passes it forward.

```
┌─────────────────────────────────────────────────────────────────┐
│                     run_ibvap.py  (Main Loop)                   │
└─────────────────────────────────────────────────────────────────┘

Webcam Frame (BGR numpy array)
         │
         ▼
┌─────────────────────┐
│ [1] HumanDetector   │  YOLOv8n — detects humans as bounding boxes
│   (Prince)          │  Output: DetectionResult{objects=[human,...]}
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ [2] HumanTracker    │  DeepSORT — gives each human a stable ID
│   (Prince)          │  Adds: track_id="h-1", centroid, velocity
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ [3] VehicleANPR     │  YOLOv8n — detects cars/trucks/bikes on
│   (Prachi/Mayan)    │  same frame. Adds vehicle DetectedObjects.
└────────┬────────────┘
         │
         ▼   ← Humans + Vehicles now MERGED into one DetectionResult
         │
         ▼
┌─────────────────────┐
│ [4] Suspicious      │  Math-based heuristics on track history.
│   Activity (Omkar)  │  Adds: obj.attributes["activity"] = "loitering"
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ [5] VirtualFence    │  Point-in-polygon check on foot position.
│   (Abhilasha)       │  Adds: obj.attributes["zone_state"] = "inside"
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ [6] AlarmManager    │  The final destination for ALL data.
│   (Prince)          │  Scores, stores, broadcasts.
└─────────────────────┘
```

---

## 3. How the AlarmManager Stores Data

When `AlarmManager.submit(result, frame)` is called, for each detected object it:

### Step A — Score the Object
Reads `alarm_manager/configs/rules.yaml` and calculates a **Danger Score**:
```
human_tracking module fired         → +20
zone_state == "inside"              → +40
activity == "loitering"             → +35
vehicle_detection module fired      → +25
...etc.
Total score → Danger Label (LOW/MEDIUM/HIGH/CRITICAL)
```

### Step B — Create/Update Incident Folder
A **unique 12-character incident ID** is generated from the camera + track_id using MD5 hash. This means:
- The same person/vehicle always maps to the **same incident folder**.
- Data from multiple frames is **accumulated** into one record, not duplicated.

```
storage/
  incidents/
    e4b3f1a9d0c2/          ← Incident ID
      incident.json        ← Master JSON record (updated every frame)
      snapshot_001.jpg     ← First snapshot (score ≥ 20)
      snapshot_002.jpg     ← Second snapshot (adaptive rate)
      snapshot_003.jpg
```

### Step C — Write `incident.json`
```json
{
  "incident_id": "e4b3f1a9d0c2",
  "camera_id": "CAM_LIVE",
  "started_at": "2026-08-31T01:30:00+00:00",
  "last_updated": "2026-08-31T01:30:45+00:00",
  "danger_score": 95,
  "danger_label": "CRITICAL",
  "modules_triggered": ["human_tracking", "vehicle_detection"],
  "humans_detected": 2,
  "faces_captured": 1,
  "vehicles_detected": 1,
  "vehicle_types": ["car"],
  "weapons_detected": 0,
  "track_ids": ["h-1", "h-2"],
  "zone_breaches": ["border_fence"],
  "activities_detected": ["loitering"],
  "plate_numbers": ["DETECTED-87"],
  "snapshot_count": 3,
  "snapshots": ["snapshot_001.jpg", "snapshot_002.jpg", "snapshot_003.jpg"],
  "last_snapshot_at": "2026-08-31T01:30:43+00:00"
}
```

### Step D — Log to SQLite Database
Two tables in `storage/events.db`:
- **`activity_log`** — Every single frame detection (all objects, all modules, timestamp)
- **`events`** — Only when a scoring rule is triggered (incident-level events)

### Step E — Save Snapshot
If `danger_score ≥ 20`, the object's bounding box is cropped from the raw frame (with 15% padding for better face capture quality) and saved as a JPEG at 95% quality.

**Adaptive rate:**
- Score 20–39 → one snapshot every **2.0 seconds**
- Score 40–59 → one snapshot every **1.0 second**
- Score 60–79 → one snapshot every **0.5 seconds**
- Score 80+ → one snapshot every **0.2 seconds** (near-continuous)

### Step F — Broadcast via WebSocket
An alert JSON is pushed to every connected browser tab on `/ws/alerts`:
```json
{
  "incident_id": "e4b3f1a9d0c2",
  "event_type": "Virtual Fence Breach",
  "danger_label": "HIGH",
  "danger_score": 60,
  "camera_id": "CAM_LIVE",
  "track_id": "h-1",
  "humans_detected": 1,
  "zone_breaches": ["border_fence"],
  "activities": ["loitering"],
  "timestamp": "2026-08-31T01:30:00+00:00"
}
```

---

## 4. How the Website Accesses the Data

The FastAPI server (`alarm_manager/src/api.py`) exposes these endpoints:

| Endpoint | Method | What it returns |
|---|---|---|
| `/ui` | GET | Serves `website/index.html` dashboard |
| `/stream/live` | GET | MJPEG live webcam stream (for `<img>` tag) |
| `/api/incidents` | GET | All incidents JSON list (for Incidents tab) |
| `/api/incidents/{id}` | GET | Single incident detail JSON |
| `/api/events` | GET | Recent events from SQLite |
| `/ws/alerts` | WebSocket | Real-time push of new alerts |
| `/storage/incidents/{id}/{file}` | GET | Direct access to snapshots |

**Website data flow:**
```
Page Load
  → fetch /api/incidents  → populates Incidents tab
  → fetch /api/events     → populates Live Alerts tab (history)
  → <img src="/stream/live">  → shows live MJPEG camera feed
  → WebSocket /ws/alerts  → receives new alerts in real-time, updates all counts
```

---

## 5. The Centralized File System Layout

```
ibvap/
├── run_ibvap.py              ← SINGLE ENTRY POINT — run this
├── system_audit.py           ← Run to verify all modules work
├── contracts/
│   └── schema.py             ← FROZEN contract — do not modify without sign-off
├── alarm_manager/
│   ├── configs/
│   │   └── rules.yaml        ← Edit this to change scoring rules
│   └── src/
│       ├── core.py           ← AlarmManager — main intelligence hub
│       ├── api.py            ← FastAPI server (REST + WebSocket + MJPEG)
│       ├── incident_store.py ← Writes incident.json + snapshots
│       ├── database.py       ← SQLite read/write
│       └── frame_buffer.py   ← Thread-safe MJPEG buffer
├── human_detection/
│   └── inference/detector.py ← YOLOv8 (Prince)
├── human_tracking/
│   └── inference/tracker.py  ← DeepSORT (Prince)
├── suspicious_activity/
│   └── loitering_detector.py ← Loitering/Crowd/Erratic (Omkar)
├── virtual_fence/
│   ├── fence_detector.py     ← Pipeline-integrated fence (Abhilasha)
│   ├── roi_calibration.py    ← Tool to draw fence polygon
│   └── roi_config.json       ← Saved fence coordinates
├── vehicle_detection/
│   └── inference/
│       └── vehicle_anpr.py   ← Vehicle tracking + ANPR (Prachi/Mayan)
├── website/
│   └── index.html            ← Dashboard UI
├── storage/
│   ├── events.db             ← SQLite (auto-created)
│   └── incidents/
│       └── <incident_id>/
│           ├── incident.json
│           └── snapshot_XXX.jpg
└── docs/
    ├── TEAM_INTEGRATION_BRIEF.md
    ├── DATA_FLOW.md           ← This file
    └── ARCHITECTURE.md        ← System architecture reference
```
