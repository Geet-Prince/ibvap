# 📋 IBVAP — Project Status Board

> **Last Updated:** 2026-08-31 01:46 IST  
> **Owner:** Prince (`geet-prince`)  
> **Email:** prince.raj.ds@gmail.com  
> **Repo:** https://github.com/Geet-Prince/ibvap  
> **Phase:** Phase 1 Complete + All Team Modules Integrated + System Audit 13/13 ✅

---

## 🧭 Quick Summary

IBVAP (**Intelligent Border Video Analytics Platform**) is an AI-powered CCTV analytics system for SSB border outposts. It detects humans and vehicles, tracks them with stable IDs, evaluates threat levels using a scoring engine, detects suspicious behavior and fence breaches, captures adaptive snapshots, logs everything to a centralized database, and displays real-time alerts on a web dashboard.

---

## ✅ Work Done — Checklist

### Phase 0 — Foundations (Prince)
- [x] Frozen contract schema (`contracts/schema.py`, `contracts/__init__.py`)
- [x] Repo skeleton with all module folders
- [x] Pre-commit config (`.pre-commit-config.yaml`)
- [x] `requirements.txt` with all dependencies
- [x] Module READMEs written

### Phase 1 — Human Detection (Prince)
- [x] `HumanDetector` class using YOLOv8n (`human_detection/inference/detector.py`)
- [x] `VideoInputLayer` for RTSP/webcam input (`human_detection/inference/video_input.py`)
- [x] Config file (`human_detection/configs/config.yaml`)
- [x] 14 unit tests — all passing ✅ (`human_detection/testing/test_detector.py`)

### Phase 1 — Human Tracking (Prince)
- [x] `HumanTracker` class using DeepSORT (`human_tracking/inference/tracker.py`)
- [x] Outputs stable `track_id`, `centroid`, `velocity_px_per_s` per tracked human
- [x] Config file (`human_tracking/configs/config.yaml`)
- [x] Unit tests (`human_tracking/testing/test_tracker.py`)

### Alarm Manager (Prince)
- [x] `AlarmManager.submit()` — single ingestion point for all modules
- [x] Threat scoring engine via `rules.yaml` (no code changes needed to add rules)
- [x] **Adaptive snapshot rate** — score 20→2s, 40→1s, 60→0.5s, 80+→0.2s
- [x] Human snapshot cropper — crops bbox + 15% padding for face detection quality
- [x] SQLite database — `activity_log` + `events` tables (`storage/events.db`)
- [x] FastAPI server with REST API (`/api/events`, `/api/incidents`) and WebSocket (`/ws/alerts`)
- [x] **MJPEG live stream** — `/stream/live` endpoint for browser webcam view
- [x] **Incident folder system** — each tracked object gets `storage/incidents/<id>/`
- [x] **Incident JSON metadata** — humans, vehicles, weapons, zones, activities, plates, snapshots, faces
- [x] Threat rules fully configurable in `alarm_manager/configs/rules.yaml`

### Website Dashboard v2 (Prince)
- [x] **3-panel layout** — Live Cam | Alerts + Incidents | Detail View
- [x] **Live webcam feed** via MJPEG stream (real-time, no plugin needed)
- [x] Dark theme UI with live alert feed (auto-animates on new event)
- [x] **Incidents tab** — folder-based cards with snapshot gallery, metadata stats
- [x] Threat score meter (colour-coded: Green/Yellow/Orange/Red)
- [x] **Snapshot gallery** per incident — click to preview full image
- [x] Stats bar (Total / Humans / Medium / High / Critical / Incidents)
- [x] Auto-reconnect WebSocket
- [x] Historical event + incident loader on page open
- [x] Module tags, zone breach tags, activity tags per incident
- [x] **Search bar** — search by incident ID, camera, activity tag, vehicle type
- [x] **Filter dropdown** — filter by Humans / Faces / Vehicles / Weapons / High Threat

### Team Integrations
- [x] **Suspicious Activity — Omkar** (`suspicious_activity/loitering_detector.py`)
  - Loitering detection (person stays in same area > 3 seconds)
  - Erratic movement (speed > threshold)
  - Crowd formation (3+ people grouped together)
  - Fully rewired to use unified `DetectionResult` contract
- [x] **Virtual Fence — Abhilasha** (`virtual_fence/fence_detector.py`)
  - Polygon-based restricted zone detection
  - ROI calibration tool (`virtual_fence/roi_calibration.py`)
  - Saved fence coordinates in `virtual_fence/roi_config.json`
  - Fully rewired to use unified `DetectionResult` contract
- [x] **Vehicle Detection + ANPR — Prachi/Mayan** (`vehicle_detection/inference/vehicle_anpr.py`)
  - Detects cars, motorcycles, buses, trucks via YOLOv8n
  - Runs plate detection on cropped vehicle ROI
  - Reports `vehicle_type` + `plate_no` in attributes
  - Fully rewired to use unified `DetectionResult` contract

### Integration & Tooling
- [x] Unified single-script runner (`run_ibvap.py`) — one command starts everything
- [x] All 5 AI modules chained in correct order in `run_ibvap.py`
- [x] Git configured for Prince (`geet-prince` / `prince.raj.ds@gmail.com`)
- [x] GitHub repo created and all code pushed (`https://github.com/Geet-Prince/ibvap`)
- [x] `system_audit.py` — verifies all 13 system checks pass ✅
- [x] `docs/TEAM_INTEGRATION_BRIEF.md` — master AI instructions for team
- [x] Threat scoring rules now cover all modules (vehicle, loitering, crowd, erratic, fence)

---

## 🔄 In Progress / Pending

### Upcoming Work
- [ ] Face Analysis module (triggered by fence breach event)
- [ ] Watchlist database integration (known-threat face matching)
- [ ] Continuous video buffer (rolling 30s clip storage)
- [ ] Alert acknowledge/close buttons on dashboard
- [ ] Night-time detection variant (low-light YOLO model)
- [ ] Hash-chain tamper-evidence on events table
- [ ] Multi-camera support testing
- [ ] Phase 2 — Pairwise integration tests
- [ ] Phase 3 — End-to-end test on real border camera

---

## 🏗️ Architecture Overview

```
Webcam / CCTV
      │
      ▼
[1] HumanDetector (YOLOv8n)      → DetectionResult (humans + bbox)
      │
      ▼
[2] HumanTracker (DeepSORT)      → Attaches stable track_id, centroid, velocity
      │
      ▼
[3] VehicleANPR (Prachi/Mayan)   → DetectionResult (vehicle_type, plate_no)
      │
      MERGE both results into ONE unified DetectionResult
      │
      ▼
[4] SuspiciousActivity (Omkar)   → Attaches activity="loitering"/"crowd_formation"/"erratic"
      │
      ▼
[5] VirtualFence (Abhilasha)     → Attaches zone_state="inside", zone_id="border_fence"
      │
      ▼
[6] AlarmManager.submit()
      │
      ├──► Threat Scoring (rules.yaml)  → Calculates danger score + label
      ├──► Incident JSON saved to        storage/incidents/<id>/incident.json
      ├──► Snapshot saved to             storage/incidents/<id>/snapshot_XXX.jpg
      ├──► SQLite DB logged              storage/events.db
      └──► WebSocket broadcast  →  Website live update
                                        http://localhost:8000/ui
```

---

## 📦 Module Status

| Module | Owner | GitHub User | Status | Output |
|--------|-------|-------------|--------|--------|
| Human Detection | Prince | geet-prince | ✅ Done & Tested | `DetectionResult` (humans + bbox) |
| Human Tracking | Prince | geet-prince | ✅ Done | `DetectionResult` (stable IDs + velocity) |
| Alarm Manager | Prince | geet-prince | ✅ Done | Alerts, Snapshots, DB, WebSocket |
| Website Dashboard | Prince | geet-prince | ✅ Done | Live UI at `localhost:8000/ui` |
| Virtual Fence | Abhilasha | abhilashajha052dev | ✅ Integrated | zone_state injected per object |
| Suspicious Activity | Omkar | omkarmishra07 | ✅ Integrated | activity injected per object |
| Vehicle Detection + ANPR | Prachi/Mayan | mayan | ✅ Integrated | vehicle_type, plate_no per vehicle |
| Face Analysis | Phase 2 | — | 🔵 Not started | `DetectionResult` (face match) |

---

## 🚀 How to Run the Project

### Prerequisites
```bash
pip install -r requirements.txt
pip install deep-sort-realtime
```

### Run Everything (single command)
```bash
cd E:\Prince\sih2026\ibvap
python run_ibvap.py
```

### Run System Audit First (to verify all modules work)
```bash
python system_audit.py
```

### Open the Dashboard
```
http://localhost:8000/ui
```

### Video File instead of Webcam
```bash
python run_ibvap.py --source path/to/video.mp4
```

---

## 🎯 Threat Scoring System

| Rule | Triggered When | Score | Severity |
|------|---------------|-------|----------|
| Human Detected | `human_detection` module fires | +20 | Informational |
| Human Tracked | `human_tracking` module fires | +20 | Informational |
| Virtual Fence Breach | `zone_state = inside` | +40 | High |
| Loitering | `activity = loitering` | +35 | Medium |
| Erratic Movement | `activity = erratic_movement` | +30 | Medium |
| Crowd Formation | `activity = crowd_formation` | +35 | Medium |
| Vehicle Detected | `vehicle_detection` module fires | +25 | Informational |
| ANPR Watchlist Hit | `watchlist_match = true` | +50 | Critical |

**Danger Thresholds:**
- 🟢 **LOW** — score < 40
- 🟡 **MEDIUM** — score 40–59
- 🟠 **HIGH** — score 60–79
- 🔴 **CRITICAL** — score 80+

---

## 📁 Key Files Reference

| File | Purpose |
|------|---------|
| `run_ibvap.py` | **Single entry point** — starts server + full AI pipeline |
| `system_audit.py` | Verifies all 13 system checks pass |
| `contracts/schema.py` | **Frozen** shared data contract for all modules |
| `alarm_manager/configs/rules.yaml` | Threat scoring rules (edit freely, no code changes) |
| `alarm_manager/src/core.py` | AlarmManager — master intelligence hub |
| `alarm_manager/src/api.py` | FastAPI server — REST + WebSocket + MJPEG |
| `alarm_manager/src/incident_store.py` | Centralized incident folder + JSON writer |
| `alarm_manager/src/database.py` | SQLite DB setup and queries |
| `alarm_manager/src/frame_buffer.py` | Thread-safe JPEG buffer for MJPEG stream |
| `human_detection/inference/detector.py` | YOLOv8 human detection |
| `human_tracking/inference/tracker.py` | DeepSORT tracking |
| `suspicious_activity/loitering_detector.py` | Omkar — Loitering/Crowd/Erratic detector |
| `virtual_fence/fence_detector.py` | Abhilasha — ROI polygon breach detector |
| `vehicle_detection/inference/vehicle_anpr.py` | Prachi — Vehicle tracking + plate detection |
| `website/index.html` | Dashboard UI |
| `storage/events.db` | SQLite database (auto-created) |
| `storage/incidents/<id>/incident.json` | Per-intrusion master JSON record |
| `storage/incidents/<id>/snapshot_XXX.jpg` | Per-intrusion photos |
| `docs/TEAM_INTEGRATION_BRIEF.md` | Instructions for AI agents of all teammates |

---

## 🗂️ Change History

| Date | What Changed |
|------|-------------|
| 2026-08-30 | Phase 0: Repo skeleton, contracts, CI, module READMEs |
| 2026-08-30 | Phase 1: Human Detection (YOLO) — 14 tests passing |
| 2026-08-30 | Phase 1: Human Tracking (DeepSORT) — stable IDs + velocity |
| 2026-08-30 | Alarm Manager: threat scoring, snapshot cropper, SQLite, WebSocket API |
| 2026-08-30 | Website: live dashboard with alerts, snapshots, threat meter |
| 2026-08-30 | Added mock data fixtures for Omkar's Suspicious Activity module |
| 2026-08-30 | Full pipeline wired: Webcam → YOLO → Track → Alarm → Dashboard |
| 2026-08-30 | Created `docs/TEAM_INTEGRATION_BRIEF.md` for AI agents to follow architecture |
| 2026-08-30 | Fixed MJPEG stream CORS/404 issues and added automatic camera retry to UI |
| 2026-08-30 | Upgraded Website Incidents tab to full File Management System (Search, Filter, Meta) |
| 2026-08-30 | Integrated Omkar's Suspicious Activity detector into unified pipeline |
| 2026-08-30 | Pulled and integrated Abhilasha's Virtual Fence into unified pipeline |
| 2026-08-31 | Integrated Prachi/Mayan's Vehicle Detection + ANPR into unified pipeline |
| 2026-08-31 | Fixed scoring rules to cover all modules correctly |
| 2026-08-31 | System audit script written — 13/13 checks passing |
