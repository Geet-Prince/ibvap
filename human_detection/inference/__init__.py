"""
human_detection/inference/__init__.py
Public API surface for the Human Detection module.

Other modules (and tests) should ONLY import from here:
    from human_detection.inference import HumanDetector

Never import from human_detection internals directly.
"""

from .detector import HumanDetector

__all__ = ["HumanDetector"]
