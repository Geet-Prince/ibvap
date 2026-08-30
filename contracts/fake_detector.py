"""
Mock / FakeDetector — for unblocking parallel development
=========================================================
Any module owner (or the Alarm Manager / Website owner) can use FakeDetector
to replay a recorded DetectionResult JSON fixture at a set rate without needing
any real model to exist yet.

Usage:
    fake = FakeDetector("tests/fixtures/scenarios/human_detection_sample.json", fps=5.0)
    fake.run(alarm_manager)

Owner: Prince (available to all teammates)
"""

import json
import time
from pathlib import Path
from typing import Union

from contracts.schema import DetectionResult


class FakeDetector:
    """
    Replays a recorded fixture JSON at a configurable frame rate.
    Implements the same interface as a real detector module.

    Args:
        fixture_path: Path to a JSON file containing a DetectionResult or
                      a list of DetectionResults.
        fps:          Replay speed in frames-per-second (default 5.0).
        loop:         If True, replay indefinitely (useful for live-demo mode).
    """

    def __init__(self, fixture_path: Union[str, Path], fps: float = 5.0, loop: bool = False):
        self.fixture_path = Path(fixture_path)
        self.fps = fps
        self.loop = loop
        self._results = self._load()

    def _load(self) -> list[DetectionResult]:
        raw = json.loads(self.fixture_path.read_text())
        if isinstance(raw, list):
            return [DetectionResult(**r) for r in raw]
        return [DetectionResult(**raw)]

    def run(self, alarm_manager) -> None:
        """
        Submit each fixture result to the AlarmManager at self.fps rate.
        Blocks until the fixture is exhausted (or forever if loop=True).
        """
        interval = 1.0 / self.fps
        while True:
            for result in self._results:
                alarm_manager.submit(result)
                time.sleep(interval)
            if not self.loop:
                break
