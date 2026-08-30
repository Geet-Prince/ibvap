"""
contracts/schema.py — THE FROZEN CONTRACT
==========================================
This is the single shared contract for ALL modules in IBVAP.

Rules:
  - This file is FROZEN after Phase 0 sign-off.
  - Any change MUST have full-team sign-off + passing tests/contract/ run.
  - Every module imports from here. Nobody copies or re-implements it.
  - No module ever calls another module's code, saves a file, writes to a DB,
    or touches the UI. A module's job ends when it calls AlarmManager.submit(result).

Owner: Prince (architecture coordination)
"""

from datetime import datetime
from typing import Dict, List, Literal, Tuple
from pydantic import BaseModel, Field


SCHEMA_VERSION = "1.0"

VALID_MODULES = Literal[
    "human_detection",
    "human_tracking",
    "vehicle_detection",
    "anpr",
    "virtual_fence",
    "suspicious_activity",
    "face_analysis",
]

VALID_OBJECT_TYPES = Literal["human", "vehicle"]


class DetectedObject(BaseModel):
    """
    Represents a single detected object within a frame.

    The `track_id` is the stable ID from the tracker and MUST be carried
    through unchanged by every downstream module. It is the correlation key
    end-to-end (see architecture doc Section 22, item K).

    The `attributes` dict is module-specific:
      - Virtual Fence:        {"zone_id": "north-fence", "zone_state": "inside"}
      - ANPR:                 {"plate_no": "DL01AB1234", "watchlist_match": False}
      - Suspicious Activity:  {"activity": "loitering"}
      - Vehicle Detection:    {"vehicle_class": "truck"}
    """

    object_type: VALID_OBJECT_TYPES
    track_id: str = Field(
        ...,
        description="Stable tracker ID. Must be passed through unchanged by every module.",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: Tuple[int, int, int, int] = Field(
        ..., description="Bounding box as (x1, y1, x2, y2) in pixel coordinates."
    )
    attributes: Dict = Field(
        default_factory=dict,
        description="Module-specific metadata. See docstring for examples.",
    )


class DetectionResult(BaseModel):
    """
    The single payload shape produced by EVERY module and handed to AlarmManager.submit().

    This envelope is what makes 'one alarm reused by every method' real —
    every module calls exactly one function with this exact shape.
    What happens next is decided by rules.yaml, not by code inside each module.
    """

    schema_version: str = Field(default=SCHEMA_VERSION)
    module: VALID_MODULES
    camera_id: str = Field(..., description="Unique camera identifier, e.g. 'CAM_01'")
    frame_id: int = Field(..., description="Monotonically increasing frame counter.")
    timestamp_utc: datetime = Field(
        ..., description="UTC timestamp of when this frame was processed."
    )
    objects: List[DetectedObject] = Field(
        default_factory=list,
        description="All detected objects in this frame. Can be empty.",
    )
