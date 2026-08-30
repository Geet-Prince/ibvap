"""
Virtual Fence Module - Integrated with IBVAP AlarmManager pipeline
"""
import json
import numpy as np
import cv2
from pathlib import Path
from contracts.schema import DetectionResult, DetectedObject

class VirtualFence:
    def __init__(self, roi_path: str = None, frame_w: int = 1280, frame_h: int = 720):
        if roi_path is None:
            roi_path = Path(__file__).parent / "roi_config.json"
        
        self.polygon = []
        if Path(roi_path).exists():
            with open(roi_path, "r") as f:
                config = json.load(f)
            cal_w = config["frame_width"]
            cal_h = config["frame_height"]
            raw_points = config["polygon"]
            
            sx = frame_w / cal_w
            sy = frame_h / cal_h
            self.polygon = [(int(x * sx), int(y * sy)) for (x, y) in raw_points]
            self.contour = np.array(self.polygon, dtype="int32")
        else:
            print(f"Warning: ROI config not found at {roi_path}")
            self.contour = None

    def _get_foot_point(self, bbox: list) -> tuple:
        x1, y1, x2, y2 = bbox
        foot_x = int((x1 + x2) / 2)
        foot_y = int(y2)
        return foot_x, foot_y

    def is_inside(self, foot_point: tuple) -> bool:
        if self.contour is None or len(self.contour) < 3:
            return False
        result = cv2.pointPolygonTest(self.contour, foot_point, measureDist=False)
        return result >= 0

    def process(self, result: DetectionResult) -> DetectionResult:
        """Process tracking results and check for fence breaches."""
        if self.contour is None:
            return result

        for obj in result.objects:
            if obj.object_type == "human":
                foot_point = self._get_foot_point(obj.bbox)
                
                if self.is_inside(foot_point):
                    obj.attributes["zone_state"] = "inside"
                    obj.attributes["zone_id"] = "border_fence"
        
        return result

    def draw_fence(self, frame: np.ndarray, breach_active: bool = False):
        """Helper to draw the fence on the frame."""
        if self.contour is None or len(self.contour) < 3:
            return

        overlay = frame.copy()
        fill_color = (0, 0, 255) if breach_active else (0, 0, 120)
        cv2.fillPoly(overlay, [self.contour], fill_color)
        cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)
        cv2.polylines(frame, [self.contour], isClosed=True, color=(0, 0, 255), thickness=3)
