# Vehicle Detection & Classification — Module README

**Owner:** Prachi  
**Status:** Phase 1 — In Development

---

## Purpose
Detect and classify vehicles (car, truck, motorcycle, bus) in raw camera frames.
Combined in a single module for MVP — no split needed until scale demands it.

## Input
Raw video frames from the Video Input Layer.

## Output
```json
{
  "module": "vehicle_detection",
  "objects": [
    {
      "object_type": "vehicle",
      "track_id": "v-001",
      "confidence": 0.88,
      "bbox": [50, 60, 400, 350],
      "attributes": {"vehicle_class": "truck"}
    }
  ]
}
```

## Tech Stack
- Ultralytics YOLO v8 (COCO pretrained covers vehicle classes out of the box)

## Running Tests
```bash
pytest vehicle_detection/testing/ -v
pytest tests/contract/ -v
```
