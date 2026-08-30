from pydantic import BaseModel, Field
from typing import List, Dict, Any
from enum import Enum

class ObjectType(str, Enum):
    HUMAN = "human"
    VEHICLE = "vehicle"

class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class Track(BaseModel):
    track_id: str
    object_type: ObjectType
    bbox: BoundingBox
    confidence: float
    velocity_x: float = 0.0
    velocity_y: float = 0.0

class FrameState(BaseModel):
    camera_id: str
    timestamp: float
    frame_id: int
    tracks: List[Track]

class EventSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Event(BaseModel):
    event_id: str
    event_type: str  # e.g., "SUSPICIOUS_ACTIVITY", "ZONE_INTRUSION"
    timestamp: float
    camera_id: str
    track_ids: List[str]
    severity: EventSeverity
    metadata: Dict[str, Any] = Field(default_factory=dict)
