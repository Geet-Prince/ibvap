# Human Detection — Module README

**Owner:** Prince  
**Status:** Phase 1 — In Development

---

## Purpose
Detect humans in raw camera frames using YOLO. This is the first stage of the
human analytics pipeline — its output feeds directly into Human Tracking.

## Input
Raw video frames (BGR numpy array from OpenCV / RTSP stream via Video Input Layer).

## Output
A `DetectionResult` with `module = "human_detection"` and one `DetectedObject`
per detected human. No tracking ID is assigned here — that's Human Tracking's job.

```json
{
  "schema_version": "1.0",
  "module": "human_detection",
  "camera_id": "CAM_01",
  "frame_id": 42,
  "timestamp_utc": "2026-08-30T10:00:00Z",
  "objects": [
    {
      "object_type": "human",
      "track_id": "det-0001",
      "confidence": 0.93,
      "bbox": [120, 80, 260, 400],
      "attributes": {}
    }
  ]
}
```

## Tech Stack
- Python + OpenCV
- Ultralytics YOLO v8/v11 (pretrained `yolov8n.pt` as starting point)
- Config: `configs/system.yaml` → `models.human_detection`

## Folder Contents
| Folder | Purpose |
|--------|---------|
| `data/` | Raw frames + annotated datasets |
| `training/` | Fine-tuning scripts |
| `models/current/` | Symlink/pointer to approved weights |
| `inference/` | **Public API — the only file others import** |
| `testing/` | pytest tests with fixture frames |
| `evaluation/` | mAP, precision/recall scripts |
| `configs/` | Module-specific overrides |

## Known Limitations
- Daytime only (Phase 1 scope — night-time is Phase 4)
- Not responsible for track IDs — those come from Human Tracking

## Running Tests
```bash
pytest human_detection/testing/ -v
pytest tests/contract/ -v   # must always pass before PR
```
