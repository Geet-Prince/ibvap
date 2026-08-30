# Suspicious Activity — Module README

**Owner:** Omkar  
**Status:** Phase 1 — In Development

---

## Purpose
Detect suspicious behavior (loitering, speed anomalies) from human trajectory data.
Consumes tracking results — **no raw video, no GPU required for MVP**.

## Input
`DetectionResult` from Human Tracking (centroid + velocity in `attributes`).

**To develop without the real tracking model:**
```python
from contracts.fake_detector import FakeDetector
fake = FakeDetector("tests/fixtures/scenarios/human_tracking_sample.json")
fake.run(alarm_manager)
```

## Output
`DetectionResult` with `module = "suspicious_activity"` and `activity` in `attributes`:

```json
{
  "module": "suspicious_activity",
  "objects": [
    {
      "object_type": "human",
      "track_id": "track-001",
      "confidence": 0.82,
      "bbox": [120, 80, 260, 400],
      "attributes": {"activity": "loitering"}
    }
  ]
}
```

## Behavior Rules (configurable via system.yaml)
- `loitering_threshold_seconds`: flag a track that stays in a small area for too long
- `speed_anomaly_factor`: flag a track moving N× faster than the scene average

## Running Tests
```bash
pytest suspicious_activity/testing/ -v
pytest tests/contract/ -v
```
