"""
human_detection/testing/test_detector.py
==========================================
Unit tests for HumanDetector.

These tests run WITHOUT a real YOLO model or camera — they mock ultralytics
so CI works in any environment (including GitHub Actions, no GPU).

Run with:  pytest human_detection/testing/ -v
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ── Path setup ──────────────────────────────────────────────────────────────
# Allow running tests from the repo root or from within human_detection/
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from contracts import DetectionResult, DetectedObject
from human_detection.inference import HumanDetector


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def blank_frame() -> np.ndarray:
    """640×480 blank BGR frame — no real image needed for unit tests."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def mock_yolo_result():
    """
    Fake YOLO result mimicking what ultralytics returns.
    Simulates two people detected in a single frame.
    """
    import torch

    box1 = MagicMock()
    box1.xyxy = [torch.tensor([100.0, 80.0, 260.0, 400.0])]
    box1.conf = [torch.tensor(0.93)]

    box2 = MagicMock()
    box2.xyxy = [torch.tensor([380.0, 90.0, 520.0, 390.0])]
    box2.conf = [torch.tensor(0.87)]

    result = MagicMock()
    result.boxes = [box1, box2]
    return [result]


@pytest.fixture
def mock_yolo_empty():
    """Fake YOLO result — no detections (empty frame)."""
    result = MagicMock()
    result.boxes = []
    return [result]


@pytest.fixture
def detector(tmp_path) -> HumanDetector:
    """
    HumanDetector with weights path redirected to a temp dir.
    The YOLO model itself is mocked in each test — this just prevents
    config from pointing at a non-existent path.
    """
    return HumanDetector(config_override={
        "model": {
            "weights": str(tmp_path / "best.pt"),
            "device": "cpu",
        }
    })


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestHumanDetectorOutput:

    @patch("human_detection.inference.detector.YOLO")
    def test_detect_returns_detection_result(
        self, MockYOLO, detector, blank_frame, mock_yolo_result
    ):
        """detect() must always return a DetectionResult."""
        MockYOLO.return_value.predict.return_value = mock_yolo_result
        detector._model = MockYOLO.return_value

        result = detector.detect(blank_frame, camera_id="CAM_01", frame_id=1)

        assert isinstance(result, DetectionResult)

    @patch("human_detection.inference.detector.YOLO")
    def test_module_field_is_human_detection(
        self, MockYOLO, detector, blank_frame, mock_yolo_result
    ):
        """The module field must be exactly 'human_detection'."""
        MockYOLO.return_value.predict.return_value = mock_yolo_result
        detector._model = MockYOLO.return_value

        result = detector.detect(blank_frame, camera_id="CAM_01", frame_id=1)

        assert result.module == "human_detection"

    @patch("human_detection.inference.detector.YOLO")
    def test_camera_id_propagated(
        self, MockYOLO, detector, blank_frame, mock_yolo_result
    ):
        MockYOLO.return_value.predict.return_value = mock_yolo_result
        detector._model = MockYOLO.return_value

        result = detector.detect(blank_frame, camera_id="CAM_02", frame_id=5)

        assert result.camera_id == "CAM_02"

    @patch("human_detection.inference.detector.YOLO")
    def test_frame_id_propagated(
        self, MockYOLO, detector, blank_frame, mock_yolo_result
    ):
        MockYOLO.return_value.predict.return_value = mock_yolo_result
        detector._model = MockYOLO.return_value

        result = detector.detect(blank_frame, camera_id="CAM_01", frame_id=42)

        assert result.frame_id == 42

    @patch("human_detection.inference.detector.YOLO")
    def test_two_humans_detected(
        self, MockYOLO, detector, blank_frame, mock_yolo_result
    ):
        """Two detections from YOLO → two DetectedObjects in the result."""
        MockYOLO.return_value.predict.return_value = mock_yolo_result
        detector._model = MockYOLO.return_value

        result = detector.detect(blank_frame, camera_id="CAM_01", frame_id=1)

        assert len(result.objects) == 2

    @patch("human_detection.inference.detector.YOLO")
    def test_all_objects_are_human(
        self, MockYOLO, detector, blank_frame, mock_yolo_result
    ):
        MockYOLO.return_value.predict.return_value = mock_yolo_result
        detector._model = MockYOLO.return_value

        result = detector.detect(blank_frame, camera_id="CAM_01", frame_id=1)

        for obj in result.objects:
            assert obj.object_type == "human"

    @patch("human_detection.inference.detector.YOLO")
    def test_track_ids_have_correct_prefix(
        self, MockYOLO, detector, blank_frame, mock_yolo_result
    ):
        """track_ids must follow 'det-<frame_id>-<idx>' pattern."""
        MockYOLO.return_value.predict.return_value = mock_yolo_result
        detector._model = MockYOLO.return_value

        result = detector.detect(blank_frame, camera_id="CAM_01", frame_id=7)

        assert result.objects[0].track_id == "det-7-0"
        assert result.objects[1].track_id == "det-7-1"

    @patch("human_detection.inference.detector.YOLO")
    def test_confidence_within_range(
        self, MockYOLO, detector, blank_frame, mock_yolo_result
    ):
        MockYOLO.return_value.predict.return_value = mock_yolo_result
        detector._model = MockYOLO.return_value

        result = detector.detect(blank_frame, camera_id="CAM_01", frame_id=1)

        for obj in result.objects:
            assert 0.0 <= obj.confidence <= 1.0

    @patch("human_detection.inference.detector.YOLO")
    def test_bbox_is_four_ints(
        self, MockYOLO, detector, blank_frame, mock_yolo_result
    ):
        MockYOLO.return_value.predict.return_value = mock_yolo_result
        detector._model = MockYOLO.return_value

        result = detector.detect(blank_frame, camera_id="CAM_01", frame_id=1)

        for obj in result.objects:
            assert len(obj.bbox) == 4
            assert all(isinstance(v, int) for v in obj.bbox)

    @patch("human_detection.inference.detector.YOLO")
    def test_empty_frame_returns_no_objects(
        self, MockYOLO, detector, blank_frame, mock_yolo_empty
    ):
        """Empty YOLO result → objects list is empty (not an error)."""
        MockYOLO.return_value.predict.return_value = mock_yolo_empty
        detector._model = MockYOLO.return_value

        result = detector.detect(blank_frame, camera_id="CAM_01", frame_id=1)

        assert result.objects == []

    @patch("human_detection.inference.detector.YOLO")
    def test_timestamp_is_utc_when_not_provided(
        self, MockYOLO, detector, blank_frame, mock_yolo_empty
    ):
        MockYOLO.return_value.predict.return_value = mock_yolo_empty
        detector._model = MockYOLO.return_value

        result = detector.detect(blank_frame, camera_id="CAM_01", frame_id=1)

        assert result.timestamp_utc.tzinfo is not None

    @patch("human_detection.inference.detector.YOLO")
    def test_custom_timestamp_propagated(
        self, MockYOLO, detector, blank_frame, mock_yolo_empty
    ):
        MockYOLO.return_value.predict.return_value = mock_yolo_empty
        detector._model = MockYOLO.return_value

        ts = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)
        result = detector.detect(blank_frame, camera_id="CAM_01", frame_id=1, timestamp_utc=ts)

        assert result.timestamp_utc == ts

    @patch("human_detection.inference.detector.YOLO")
    def test_result_passes_contract_schema(
        self, MockYOLO, detector, blank_frame, mock_yolo_result
    ):
        """The result must be a valid Pydantic model — this is the contract gate."""
        MockYOLO.return_value.predict.return_value = mock_yolo_result
        detector._model = MockYOLO.return_value

        result = detector.detect(blank_frame, camera_id="CAM_01", frame_id=1)

        # Re-serialise and re-parse through the contract to prove conformance
        reparsed = DetectionResult(**result.model_dump())
        assert reparsed == result

    @patch("human_detection.inference.detector.YOLO")
    def test_schema_version_is_correct(
        self, MockYOLO, detector, blank_frame, mock_yolo_result
    ):
        MockYOLO.return_value.predict.return_value = mock_yolo_result
        detector._model = MockYOLO.return_value

        result = detector.detect(blank_frame, camera_id="CAM_01", frame_id=1)

        assert result.schema_version == "1.0"
