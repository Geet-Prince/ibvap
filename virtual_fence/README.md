# Virtual Fence — Module README

**Owner:** Abhilasha  
**Status:** Phase 1 — In Development

---

## Purpose
Detect when a tracked human enters a configured zone polygon (virtual fence).
This is **pure geometry** — point-in-polygon on track centroids.
No CV model, no GPU required.

## Input
`DetectionResult` from Human Tracking (must contain `centroid` in `attributes`).

**To develop without the real tracking model:**
```python
from contracts.fake_detector import FakeDetector
fake = FakeDetector("tests/fixtures/scenarios/human_tracking_sample.json")
fake.run(alarm_manager)
```

## Output
`DetectionResult` with `module = "virtual_fence"`. Objects that are INSIDE a zone get:

```json
{
  "module": "virtual_fence",
  "objects": [
    {
      "object_type": "human",
      "track_id": "track-001",
      "confidence": 0.91,
      "bbox": [120, 80, 260, 400],
      "attributes": {
        "zone_id": "north-fence",
        "zone_state": "inside"
      }
    }
  ]
}
```

## Zone Config
Zones are defined in `configs/system.yaml → cameras[n].zones`.
No hardcoding of coordinates in code.

## Running Tests
```bash
pytest virtual_fence/testing/ -v
pytest tests/contract/ -v
```
