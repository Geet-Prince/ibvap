"""
human_tracking/testing/test_tracker.py
Unit tests for HumanTracker.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from contracts import DetectedObject, DetectionResult
from human_tracking.inference import HumanTracker

@pytest.fixture
def sample_detection_result():
    return DetectionResult(
        module="human_detection",
        camera_id="CAM_01",
        frame_id=1,
        timestamp_utc=datetime.now(timezone.utc),
        objects=[
            DetectedObject(
                object_type="human",
                track_id="det-1-0",
                confidence=0.9,
                bbox=(100, 100, 200, 300),
                attributes={}
            )
        ]
    )

def test_tracker_assigns_stable_id(sample_detection_result):
    tracker = HumanTracker(config_override={"tracker": {"max_age": 1, "n_init": 1}})
    
    # Run once
    res1 = tracker.track(sample_detection_result)
    assert res1.module == "human_tracking"
    assert len(res1.objects) == 1
    assert res1.objects[0].track_id.startswith("trk-")
    assert "centroid" in res1.objects[0].attributes
    
    # Run twice with slightly moved bbox
    res2_input = sample_detection_result.model_copy(deep=True)
    res2_input.frame_id = 2
    res2_input.objects[0].bbox = (102, 105, 202, 305)
    
    res2 = tracker.track(res2_input)
    assert len(res2.objects) == 1
    assert res2.objects[0].track_id == res1.objects[0].track_id # Should maintain same ID
    
    vel = res2.objects[0].attributes["velocity_px_per_s"]
    assert len(vel) == 2
