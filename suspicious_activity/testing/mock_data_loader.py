import json
import sys
from pathlib import Path

# Allow importing from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from datetime import datetime, timezone
from typing import List

from contracts.schema import DetectionResult, DetectedObject

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mock_suspicious_data.json"

def load_mock_tracking_data() -> List[DetectionResult]:
    """
    Loads Omkar's mock_suspicious_data.json and converts it into the strict
    DetectionResult schema expected by the Phase 1 architectural contract.
    
    This allows the Suspicious Activity module to be tested independently 
    before the real HumanTracking module is fully connected.
    """
    with open(_FIXTURE_PATH, "r") as f:
        raw_data = json.load(f)
        
    results = []
    
    for frame_data in raw_data:
        # Convert timestamp float to UTC datetime
        dt = datetime.fromtimestamp(frame_data["timestamp"], tz=timezone.utc)
        
        objects = []
        for track in frame_data.get("tracks", []):
            bbox = track["bbox"]
            x1, y1, x2, y2 = int(bbox["x1"]), int(bbox["y1"]), int(bbox["x2"]), int(bbox["y2"])
            
            # The frozen contract requires velocity in the 'attributes' dict
            vx = track.get("velocity_x", 0.0)
            vy = track.get("velocity_y", 0.0)
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            
            objects.append(DetectedObject(
                object_type=track["object_type"],
                track_id=track["track_id"],
                confidence=track["confidence"],
                bbox=(x1, y1, x2, y2),
                attributes={
                    "velocity_px_per_s": (round(vx, 2), round(vy, 2)),
                    "centroid": (cx, cy)
                }
            ))
            
        result = DetectionResult(
            module="human_tracking",
            camera_id=frame_data["camera_id"],
            frame_id=frame_data["frame_id"],
            timestamp_utc=dt,
            objects=objects
        )
        results.append(result)
        
    return results

if __name__ == "__main__":
    # Quick test to ensure it loads correctly
    data = load_mock_tracking_data()
    print(f"Successfully loaded {len(data)} frames of tracking data.")
    if data:
        print("First frame preview:")
        print(data[0].model_dump_json(indent=2))
