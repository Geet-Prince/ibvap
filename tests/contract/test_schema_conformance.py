"""
tests/contract/test_schema_conformance.py
==========================================
THE CI GATE — runs on every PR for every module.

If this passes, it doesn't matter which AI tool wrote the module or
what the internals look like. The contract is what matters.

Run with:  pytest tests/contract/
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from pydantic import ValidationError

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from contracts.schema import DetectionResult, DetectedObject


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_result(**overrides) -> dict:
    """Returns a valid DetectionResult payload dict, with optional overrides."""
    base = {
        "schema_version": "1.0",
        "module": "human_detection",
        "camera_id": "CAM_01",
        "frame_id": 42,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "objects": [
            {
                "object_type": "human",
                "track_id": "track-001",
                "confidence": 0.92,
                "bbox": [100, 200, 300, 400],
                "attributes": {},
            }
        ],
    }
    base.update(overrides)
    return base


# ─── Schema conformance tests ─────────────────────────────────────────────────

class TestDetectionResultSchema:

    def test_valid_human_detection_result(self):
        result = DetectionResult(**make_result(module="human_detection"))
        assert result.module == "human_detection"
        assert result.schema_version == "1.0"

    def test_valid_vehicle_detection_result(self):
        result = DetectionResult(**make_result(
            module="vehicle_detection",
            objects=[{
                "object_type": "vehicle",
                "track_id": "v-001",
                "confidence": 0.88,
                "bbox": [50, 60, 400, 350],
                "attributes": {"vehicle_class": "truck"},
            }]
        ))
        assert result.objects[0].attributes["vehicle_class"] == "truck"

    def test_valid_virtual_fence_result(self):
        result = DetectionResult(**make_result(
            module="virtual_fence",
            objects=[{
                "object_type": "human",
                "track_id": "track-007",
                "confidence": 0.95,
                "bbox": [120, 80, 300, 300],
                "attributes": {"zone_id": "north-fence", "zone_state": "inside"},
            }]
        ))
        assert result.objects[0].attributes["zone_state"] == "inside"

    def test_valid_anpr_result(self):
        result = DetectionResult(**make_result(
            module="anpr",
            objects=[{
                "object_type": "vehicle",
                "track_id": "v-002",
                "confidence": 0.78,
                "bbox": [10, 10, 200, 100],
                "attributes": {"plate_no": "DL01AB1234", "watchlist_match": False},
            }]
        ))
        assert result.objects[0].attributes["plate_no"] == "DL01AB1234"

    def test_valid_suspicious_activity_result(self):
        result = DetectionResult(**make_result(
            module="suspicious_activity",
            objects=[{
                "object_type": "human",
                "track_id": "track-003",
                "confidence": 0.80,
                "bbox": [100, 100, 200, 300],
                "attributes": {"activity": "loitering"},
            }]
        ))
        assert result.objects[0].attributes["activity"] == "loitering"

    def test_empty_objects_is_valid(self):
        """A frame with no detections is a valid result."""
        result = DetectionResult(**make_result(objects=[]))
        assert result.objects == []

    def test_track_id_is_present(self):
        """track_id must always be present — it's the correlation key."""
        with pytest.raises(ValidationError):
            DetectionResult(**make_result(objects=[{
                "object_type": "human",
                # track_id intentionally missing
                "confidence": 0.9,
                "bbox": [0, 0, 100, 100],
            }]))

    def test_invalid_module_name_rejected(self):
        with pytest.raises(ValidationError):
            DetectionResult(**make_result(module="unknown_module_xyz"))

    def test_invalid_object_type_rejected(self):
        with pytest.raises(ValidationError):
            DetectionResult(**make_result(objects=[{
                "object_type": "drone",   # not a valid type
                "track_id": "t-1",
                "confidence": 0.9,
                "bbox": [0, 0, 100, 100],
            }]))

    def test_confidence_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            DetectionResult(**make_result(objects=[{
                "object_type": "human",
                "track_id": "t-1",
                "confidence": 1.5,   # > 1.0 — invalid
                "bbox": [0, 0, 100, 100],
            }]))

    def test_missing_camera_id_rejected(self):
        data = make_result()
        del data["camera_id"]
        with pytest.raises(ValidationError):
            DetectionResult(**data)


# ─── Fixture-based conformance (for module owners to add their own fixtures) ───

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "scenarios"

def get_fixture_files():
    return list(FIXTURES_DIR.glob("*.json"))

@pytest.mark.parametrize("fixture_file", get_fixture_files())
def test_fixture_conforms_to_schema(fixture_file):
    """
    Every JSON fixture in tests/fixtures/scenarios/ must be a valid DetectionResult.
    Module owners: drop your sample output here to prove your module is contract-compliant.
    """
    data = json.loads(fixture_file.read_text())
    # Fixtures may be a single result or a list of results
    if isinstance(data, list):
        for item in data:
            DetectionResult(**item)
    else:
        DetectionResult(**data)
