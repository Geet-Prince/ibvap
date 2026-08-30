# 🚀 IBVAP — Team AI Integration Brief

> **ATTENTION ALL AI ASSISTANTS:**  
> If you are reading this document, you are assisting a team member (Omkar, Abhilasha, Prachi, or others) on the **IBVAP (Intelligent Border Video Analytics Platform)** project. Read this completely before writing any code.

---

## 1. Project Identity & Architecture
- **Repository URL:** `https://github.com/Geet-Prince/ibvap`
- **Project Manager:** **Antigravity** (Google Deepmind AI). My role is to oversee the architecture, build the core integrations (Alarm Manager + Website), and ensure everyone follows the frozen `DetectionResult` JSON contract.
- **Project Owner:** **Prince** (User: `geet-prince`). Prince has built the `human_detection` and `human_tracking` modules.

## 2. How the Data Flows (The Unified System)

```mermaid
flowchart TD
    CAM[Camera Feed] --> YOLO[Human Detection (Prince)]
    YOLO --> DeepSORT[Human Tracking (Prince)]
    
    DeepSORT -- "DetectionResult JSON" --> ALARM_MGR[Alarm Manager (Antigravity)]
    DeepSORT -- "DetectionResult JSON" --> FENCE[Virtual Fence (Abhilasha)]
    DeepSORT -- "DetectionResult JSON" --> ACTIVITY[Suspicious Activity (Omkar)]
    
    FENCE -- "DetectionResult JSON" --> ALARM_MGR
    ACTIVITY -- "DetectionResult JSON" --> ALARM_MGR
    VEHICLE[Vehicle Detection + ANPR (Prachi)] -- "DetectionResult JSON" --> ALARM_MGR
    
    ALARM_MGR --> UI[Live Dashboard Website]
    ALARM_MGR --> DB[(SQLite + Incident Folders)]
```

### The Golden Rule
**No module communicates directly with another module or writes its own files.** 
Every AI module (whether it's Virtual Fence, Suspicious Activity, or ANPR) MUST output its data using the `DetectionResult` schema (located in `contracts/schema.py`) and submit it to the **Alarm Manager**.

## 3. What Has Already Been Built
- **Phase 0 & 1:** Prince built YOLO Human Detection and DeepSORT Human Tracking. 
- **Alarm Manager:** Antigravity built the centralized `AlarmManager` (in `alarm_manager/`). It receives the `DetectionResult`, scores the threat level (via `rules.yaml`), crops snapshots, and stores everything in `storage/incidents/`.
- **Live Website:** A live dashboard (`website/index.html`) is working, fed by the Alarm Manager's WebSocket and MJPEG stream.

## 4. Instructions for Integrating Your Module

### If you are helping OMKAR (Suspicious Activity):
- Your module must consume the output of the Human Tracker. 
- You **do not need a real camera**. We have provided mock tracking data for you at: `suspicious_activity/testing/fixtures/mock_suspicious_data.json`
- Use `suspicious_activity/testing/mock_data_loader.py` to load this data.
- Analyze the track's trajectory/velocity to detect "loitering" or "running". Add `{"activity": "loitering"}` to the `attributes` dictionary of the `DetectedObject`.
- Submit your result to the `AlarmManager`.

### If you are helping ABHILASHA (Virtual Fence):
- Your module consumes the tracking data. You do not need to run YOLO yourself!
- Check if the tracked human's `centroid` (found in `attributes['centroid']`) crosses your defined polygon.
- Add `{"zone_state": "inside", "zone_id": "border_fence"}` to the `attributes`.
- Submit your result to the `AlarmManager`.

### If you are helping PRACHI (Vehicle Detection / ANPR):
- Follow the exact same folder structure as `human_detection`. 
- Output a `DetectionResult` where `object_type="vehicle"`. 
- Put the license plate string in `attributes={"plate_no": "ABC-123"}`.
- Submit to `AlarmManager`.

## 5. How to Test Your Integration
Do not write custom print statements or custom UI. Test your module by piping it into the central system:
1. Initialize your module.
2. Initialize `AlarmManager`.
3. Process a mock frame or JSON data.
4. Call `alarm_manager.submit(your_result)`.
5. Run `python start_server.py` and check `http://localhost:8000/ui` to see your alert pop up automatically!

> **AI Assistant Check:** When you begin chatting with your user, confirm you have read this `TEAM_INTEGRATION_BRIEF.md`, acknowledge that Antigravity is the Project Manager, and confirm you will strictly use `contracts/schema.py` for output.
