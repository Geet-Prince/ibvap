# ANPR — Automatic Number Plate Recognition

**Owner:** Prachi  
**Status:** Phase 1 — In Development

---

## Purpose
Read license plates from detected vehicles and check against a watchlist.

## Input
Vehicle Detection result (cropped vehicle region via bbox) + optional watchlist file.

## Output
```json
{
  "module": "anpr",
  "objects": [
    {
      "object_type": "vehicle",
      "track_id": "v-001",
      "confidence": 0.78,
      "bbox": [10, 10, 200, 100],
      "attributes": {
        "plate_no": "DL01AB1234",
        "watchlist_match": false
      }
    }
  ]
}
```

## Tech Stack
- PaddleOCR or EasyOCR (pretrained, no custom training needed for demo)
- Watchlist: plain text file, one plate per line (`configs/watchlist_plates.txt`)

## Running Tests
```bash
pytest anpr/testing/ -v
pytest tests/contract/ -v
```
