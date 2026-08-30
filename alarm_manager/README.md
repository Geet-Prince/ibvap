# Alarm Manager — Service README

**Owner:** New Member #5  
**Status:** Phase 1 — In Development

---

## Purpose
The single ingestion point for ALL module outputs. Decides (via rules.yaml) whether
a detection becomes a logged event, and if so, captures evidence and alerts locally
and queues for the center.

## The One API
```python
alarm_manager.submit(result: DetectionResult) -> None
```

## Five Steps on Every Submit
1. Validate payload against contracts/schema.py
2. Dedup/correlate via (camera_id, track_id, module) within cooldown window
3. Evaluate rules.yaml — severity + evidence decision
4. Capture evidence if rule says so (snapshot + clip from ring buffer)
5. Persist to activity_log (always) + events table + publish to local display + sync queue (if rule matched)

## Tech Stack
- FastAPI (native WebSocket for live alerts, auto-generates OpenAPI spec)
- SQLite (edge) / Postgres (center)
- Redis pub/sub (event transport)

## Starting Immediately (no real models needed)
```python
from contracts.fake_detector import FakeDetector
# Replay all six modules' fixture data against this service from day one
```

## Running Tests
```bash
pytest alarm_manager/tests/ -v
pytest tests/contract/ -v
```
