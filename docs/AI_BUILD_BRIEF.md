# AI Build Brief — IBVAP
# ======================
# Paste THIS ENTIRE FILE as context into whichever AI tool you use
# (Claude, ChatGPT, Copilot, Gemini, Cursor — doesn't matter).
# Do this EVERY TIME you start a new coding session on your module.

## Project
IBVAP — Intelligent Border Video Analytics Platform.
SIH 2026 submission for SSB border surveillance using AI on existing CCTV.

## Your Module
[FILL IN: e.g. "Virtual Fence Intrusion Detection — Owner: Abhilasha"]

## The Contract (FROZEN — do not change)

```python
from datetime import datetime
from typing import Dict, List, Literal, Tuple
from pydantic import BaseModel, Field

class DetectedObject(BaseModel):
    object_type: Literal["human", "vehicle"]
    track_id: str       # MUST be passed through unchanged from upstream
    confidence: float   # 0.0 to 1.0
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    attributes: Dict = {}  # module-specific extras

class DetectionResult(BaseModel):
    schema_version: str = "1.0"
    module: str         # your module name, e.g. "virtual_fence"
    camera_id: str
    frame_id: int
    timestamp_utc: datetime
    objects: List[DetectedObject] = []
```

## The One Rule
Your module's job ends the moment it produces a `DetectionResult` and calls:
```python
alarm_manager.submit(result)
```
Never write alerts, snapshots, DB writes, or UI code inside your module.

## Your Module Spec
[FILL IN: copy the relevant row from the architecture document Section 3,
 and any specific requirements from Sections 22 A–T that apply to your module]

## Input Your Module Receives
[FILL IN: e.g. "A DetectionResult from human_tracking — use FakeDetector
 replaying tests/fixtures/scenarios/human_tracking_sample.json to develop
 without needing the real tracking model"]

## Output Your Module Must Produce
A `DetectionResult` with `module` set to your module's name, and the
`attributes` dict populated as shown in contracts/schema.py docstring.

## Module Folder Structure
```
your_module/
├── data/         # raw + prepared samples — never mix with training data
├── training/     # training scripts and notebooks
├── models/       # versioned weights: v1/, v2/, + current -> vN symlink/pointer
├── inference/    # THE ONLY FILE OTHER PEOPLE IMPORT — your public API
├── testing/      # module-level tests (pytest + fixture frames)
├── evaluation/   # eval scripts, metrics, reports
├── configs/      # module-specific config (inherits from configs/system.yaml)
└── README.md     # purpose, owner, input/output contract, known limitations
```

## Constraints
- Python + OpenCV + Ultralytics YOLO (v8/v11) for CV work
- Pydantic for the contract (already in requirements.txt)
- Your output must pass: `pytest tests/contract/ -v`
- Do not edit contracts/schema.py — if you think it needs changing, raise it
  with Prince for full-team sign-off first
- Do not import from another module's folder directly
- Pre-commit hooks enforce black + ruff formatting automatically

## How to Prove Your Module Works
1. Drop a sample output JSON in `tests/fixtures/scenarios/<your_module>_sample.json`
2. Run `pytest tests/contract/ -v` — it auto-discovers and validates your fixture
3. Write your own module tests in `your_module/testing/`
