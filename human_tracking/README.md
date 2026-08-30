# Human Tracking — Module README

**Owner:** Prince  
**Status:** Phase 1 — In Development

---

## Purpose
Assign stable `track_id`s to detected humans across frames and emit enriched results
(centroid, velocity) consumed by Virtual Fence and Suspicious Activity.

**Critical rule:** `track_id` is the correlation key for the entire system.
Every downstream module MUST pass it through unchanged.

## Input
`DetectionResult` from Human Detection (BBoxes, no track IDs yet).

## Output
`DetectionResult` with `module = "human_tracking"`, same bboxes, stable `track_id`s,
and centroid/velocity in `attributes`.

```json
{
  "module": "human_tracking",
  "objects": [
    {
      "object_type": "human",
      "track_id": "track-001",
      "confidence": 0.91,
      "bbox": [120, 80, 260, 400],
      "attributes": {
        "centroid": [190, 240],
        "velocity_px_per_s": [2.1, 0.5]
      }
    }
  ]
}
```

## Tech Stack
- ByteTrack or DeepSORT (configurable via `configs/system.yaml → models.human_tracking.tracker`)
- Ultralytics built-in tracker support

## Running Tests
```bash
pytest human_tracking/testing/ -v
pytest tests/contract/ -v
```
