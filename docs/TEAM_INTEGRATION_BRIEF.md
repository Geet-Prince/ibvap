# 👥 IBVAP — Team Integration Brief
> **Read this before writing a single line of code.**  
> This document is maintained by Antigravity AI on behalf of Prince (Project Owner).  
> **Repo:** https://github.com/Geet-Prince/ibvap

---

## Who is Who

| Name | Role | GitHub | Module |
|------|------|--------|--------|
| **Prince** | Project Owner & Core AI | `geet-prince` | Human Detection, Tracking, Alarm Manager, Website |
| **Omkar** | Suspicious Activity AI | `omkarmishra07` | Loitering, Crowd, Erratic Movement |
| **Abhilasha** | Virtual Fence AI | `abhilashajha052dev` | ROI-based restricted zone detection |
| **Prachi / Mayan** | Vehicle & ANPR AI | `mayan` | Car/Truck/Bike detection + license plate reading |

**Project AI Manager:** Antigravity (AI assistant to Prince)

---

## The Golden Rule

> **Every module communicates through one and only one shared data structure: `DetectionResult`.**  
> No module writes files directly. No module saves to a database. No module sends alerts.  
> **Your job ends when you return an enriched `DetectionResult`.** The AlarmManager handles everything else.

---

## The Shared Contract (DO NOT MODIFY)

```python
# contracts/schema.py — FROZEN
from pydantic import BaseModel
from typing import List
from datetime import datetime

class DetectedObject(BaseModel):
    object_type:  str    # "human" or "vehicle"
    track_id:     str    # Stable ID from tracker, e.g. "h-1", "veh-3"
    bbox:         list   # [x1, y1, x2, y2] in pixels
    confidence:   float  # 0.0 – 1.0
    attributes:   dict   # Your module-specific data goes here

class DetectionResult(BaseModel):
    module:        str
    camera_id:     str
    frame_id:      int
    timestamp_utc: datetime
    objects:       List[DetectedObject]
```

---

## How to Write Your Module

Every module must follow this exact function signature:

```python
def process(self, result: DetectionResult) -> DetectionResult:
    for obj in result.objects:
        # Do your analysis on obj.bbox, obj.track_id, obj.attributes
        # Inject your findings into obj.attributes
        obj.attributes["your_key"] = "your_value"
    return result  # Always return the same result object
```

**Correct ✅**
```python
obj.attributes["activity"] = "loitering"   # Omkar injects here
obj.attributes["zone_state"] = "inside"    # Abhilasha injects here
obj.attributes["vehicle_type"] = "truck"   # Prachi injects here
```

**Wrong ❌**
```python
import cv2
cv2.imwrite("snapshot.jpg", frame)  # NEVER — AlarmManager handles this
json.dump(data, open("output.json", "w"))  # NEVER — AlarmManager handles this
requests.post("http://...", data=alert)     # NEVER — WebSocket handles this
```

---

## Module-Specific Attribute Keys

Use exactly these keys so the AlarmManager and website pick them up correctly:

### Omkar — Suspicious Activity
```python
obj.attributes["activity"] = "loitering"         # or:
obj.attributes["activity"] = "crowd_formation"    # or:
obj.attributes["activity"] = "erratic_movement"
```

### Abhilasha — Virtual Fence
```python
obj.attributes["zone_state"] = "inside"    # person is in restricted zone
obj.attributes["zone_id"]    = "border_fence"  # name of the zone
```

### Prachi / Mayan — Vehicle & ANPR
```python
obj.attributes["vehicle_type"] = "car"      # car/truck/bus/motorcycle
obj.attributes["plate_no"]     = "MH12AB1234"
```

---

## Current Threat Scoring Rules

Scoring happens in `alarm_manager/configs/rules.yaml`. Current rules:

| Event | Score | Danger Threshold |
|---|---|---|
| Human Tracked | +20 | LOW (20+) |
| Vehicle Detected | +25 | |
| Loitering | +35 | MEDIUM (40+) |
| Erratic Movement | +30 | |
| Crowd Formation | +35 | |
| Virtual Fence Breach | +40 | HIGH (60+) |
| ANPR Watchlist Hit | +50 | CRITICAL (80+) |

If you need a new rule, ask Prince to add it to `rules.yaml`. No Python code needed.

---

## Current System Status (as of 2026-08-31)

- ✅ Human Detection (YOLO)
- ✅ Human Tracking (DeepSORT)
- ✅ Alarm Manager (full — snapshot, DB, WebSocket)
- ✅ Website Dashboard (live camera, incidents, search, filters)
- ✅ Suspicious Activity — Omkar (integrated)
- ✅ Virtual Fence — Abhilasha (integrated)
- ✅ Vehicle Detection + ANPR — Prachi/Mayan (integrated)
- 🔵 Face Analysis — Phase 2 (not started)

---

## How to Pull and Run Latest Code

```bash
# Pull all latest changes from the team
git pull origin master

# Verify your system works
python system_audit.py

# Run the full pipeline
python run_ibvap.py

# Open the dashboard
# http://localhost:8000/ui
```

---

## What to Do When You Push Your Code

1. **Do NOT push your AI model files** (`.pt` files > 50MB). Add them to `.gitignore`.
2. **Do NOT push video test files** (`.mp4`). Add them to `.gitignore`.
3. **Always push to `master` branch.**
4. After pushing, tell Prince so the AI can integrate your module into `run_ibvap.py`.

---

## AI Agent Instructions

If you are an AI assistant reading this document on behalf of a team member, follow these steps:

1. Read `docs/DATA_FLOW.md` to understand how data flows through the system.
2. Confirm your understanding: **"I understand. My module must return a `DetectionResult`. I will not write files, databases, or alerts directly. I will only inject into `obj.attributes`."**
3. Tell the user your name and what module you are responsible for.
4. Pull the latest code: `git pull origin master`
5. Run `python system_audit.py` and confirm all checks pass.
6. Only then start writing or modifying code in your module's folder.
7. After completing, push to `master` and notify Prince.
