# 📋 IBVAP — Project Status Board
> **Last Updated:** 2026-08-30 21:27 IST  
> **Owner:** Prince (geet-prince)  
> **Repo:** https://github.com/Geet-Prince/ibvap  
> **Phase:** Phase 1 Done → Alarm Manager + Full Dashboard v2 Live

---

## 🧭 Quick Summary
IBVAP (Intelligent Border Video Analytics Platform) is an AI-powered CCTV analytics system for SSB border outposts. It detects humans/vehicles, tracks them, evaluates threat levels, captures snapshots, logs everything to a database, and displays live alerts on a web dashboard.

---

## ✅ Work Done — Checklist

### Phase 0 — Foundations
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
- [x] **Incident folder system** — each tracked human gets `storage/incidents/<id>/`
- [x] **Incident JSON metadata** — humans, vehicles, weapons, zones, activities, plates, snapshots
- [x] Threat rules configurable in `alarm_manager/configs/rules.yaml`

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

### Integration & Tooling
- [x] End-to-end pipeline runner (`run_live.py`) — Webcam → YOLO → Track → Alarm → Dashboard
- [x] Server startup script (`start_server.py`)
- [x] Mock data loader for Omkar (`suspicious_activity/testing/mock_data_loader.py`)
- [x] Mock suspicious data fixtures (`suspicious_activity/testing/fixtures/mock_suspicious_data.json`)
- [x] Git configured for Prince (`geet-prince` / `prince.raj.ds@gmail.com`)
- [x] GitHub repo created and all code pushed (`https://github.com/Geet-Prince/ibvap`)

---

## 🔄 In Progress / Pending

### Team Modules (Waiting for teammates)
- [ ] **Virtual Fence** — Abhilasha (consumes tracking JSON)
- [ ] **Suspicious Activity** — Omkar (has mock data, can start now)
- [ ] **Vehicle Detection + ANPR** — Prachi

### Upcoming Work
- [ ] Face Analysis module (triggered by fence breach event)
- [ ] Watchlist database integration (known-threat face matching)
- [ ] Continuous video buffer (rolling 30s clip storage)
- [ ] Alert acknowledge/close buttons on dashboard
- [ ] Night-time detection variant (low-light YOLO model)
- [ ] Hash-chain tamper-evidence on events table
- [ ] Multi-camera support testing
- [ ] Phase 2 — Pairwise integration tests
- [ ] Phase 3 — End-to-end test on real camera

---

## 🏗️ Architecture Overview

```
CCTV/Webcam
    │
    ▼
VideoInputLayer (run_live.py)
    │
    ├──► HumanDetector (YOLOv8n) ──► HumanTracker (DeepSORT)
    │                                        │
    │                                        ▼
    │                               AlarmManager.submit()
    │                                        │
    │                    ┌──────────────────┼───────────────────┐
    │                    ▼                  ▼                   ▼
    │             Threat Scoring      Snapshot Crop       SQLite DB
    │             (rules.yaml)        (storage/)         (events.db)
    │                    │
    │                    ▼
    │             WebSocket Broadcast
    │                    │
    │                    ▼
    │             Dashboard (website/index.html)
    │             http://localhost:8000/ui
    │
    └──► VehicleDetector (Prachi — pending)
```

---

## 📦 Module Status

| Module | Owner | Status | Output |
|--------|-------|--------|--------|
| Human Detection | Prince | ✅ Done & Tested | `DetectionResult` (humans + bbox) |
| Human Tracking | Prince | ✅ Done | `DetectionResult` (stable IDs + velocity) |
| Alarm Manager | Prince | ✅ Done | Alerts, Snapshots, DB logs |
| Website Dashboard | Prince | ✅ Done | Live UI at `localhost:8000/ui` |
| Virtual Fence | Abhilasha | ⏳ Pending | `DetectionResult` (zone breach) |
| Suspicious Activity | Omkar | ⏳ Has mock data | `DetectionResult` (activity type) |
| Vehicle Detection | Prachi | ⏳ Pending | `DetectionResult` (vehicles) |
| ANPR | Prachi | ⏳ Pending | `DetectionResult` (plate number) |
| Face Analysis | Phase 2 | 🔵 Not started | `DetectionResult` (face match) |

---

## 🚀 How to Run the Project

### Prerequisites
```bash
pip install -r requirements.txt
pip install deep-sort-realtime
```

### Start the server (Terminal 1)
```bash
cd E:\Prince\sih2026\ibvap
python start_server.py
```

### Start the live camera pipeline (Terminal 2)
```bash
cd E:\Prince\sih2026\ibvap
python run_live.py
```

### Open the dashboard
```
http://localhost:8000/ui
```

---

## 🎯 Threat Scoring System

| Rule | Triggered By | Score | Severity |
|------|-------------|-------|----------|
| Human Detected | `human_detection` module | +20 | Informational |
| Human Tracked | `human_tracking` module | +20 | Informational |
| Virtual Fence Breach | `zone_state = inside` | +40 | High |
| Suspicious Activity | `suspicious_activity` module | +35 | Medium |
| ANPR Watchlist Hit | `watchlist_match = true` | +50 | Critical |

**Danger Thresholds:**
- 🟢 0–19 = LOW
- 🟡 20–39 = MEDIUM  
- 🟠 40–59 = HIGH  
- 🔴 60–100 = CRITICAL

---

## 📁 Key Files Reference

| File | Purpose |
|------|---------|
| `contracts/schema.py` | **Frozen** shared data contract |
| `alarm_manager/configs/rules.yaml` | Threat scoring rules (edit freely) |
| `configs/system.yaml` | Camera and system settings |
| `storage/events.db` | SQLite database (auto-created) |
| `storage/media/snapshots/` | Cropped human snapshots |
| `run_live.py` | Full pipeline runner |
| `start_server.py` | FastAPI server startup |
| `website/index.html` | Dashboard UI |

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
