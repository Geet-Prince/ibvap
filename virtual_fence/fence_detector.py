import json
import numpy as np
import cv2
from pathlib import Path
from contracts.schema import DetectionResult, DetectedObject


class VirtualFence:
    def __init__(self, roi_path=None, frame_w=1280, frame_h=720, cam_id=None, video_name=None):
        self.cam_id = cam_id
        self.video_name = video_name
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.roi_path = roi_path
        if self.roi_path is None:
            if cam_id:
                cam_path = Path(__file__).parent / f"{cam_id}_roi.json"
                if cam_path.exists():
                    self.roi_path = str(cam_path)
            if self.roi_path is None and video_name:
                base_path = Path(__file__).parent / f"{video_name}_roi.json"
                if base_path.exists():
                    self.roi_path = str(base_path)
            if self.roi_path is None:
                if cam_id:
                    self.roi_path = str(Path(__file__).parent / f"{cam_id}_roi.json")
                else:
                    self.roi_path = str(Path(__file__).parent / "roi_config.json")
        self.polygon = []
        self.contour = None
        self.load_config()
        self._inside_frames = {}
        self._enter_threshold = 2
        self._grace_frames = 6

    def load_config(self):
        if self.roi_path and Path(self.roi_path).exists():
            with open(self.roi_path, "r") as f:
                config = json.load(f)
            cal_w = config["frame_width"]
            cal_h = config["frame_height"]
            raw_points = config["polygon"]
            sx = self.frame_w / cal_w
            sy = self.frame_h / cal_h
            self.polygon = [(int(x * sx), int(y * sy)) for (x, y) in raw_points]
            self.contour = np.array(self.polygon, dtype="int32")
        else:
            print(f"Warning: ROI config not found at {self.roi_path}")
            self.contour = None

    def update_polygon(self, raw_points):
        if self.roi_path:
            config = {"frame_width": self.frame_w, "frame_height": self.frame_h, "polygon": raw_points}
            with open(self.roi_path, "w") as f:
                json.dump(config, f, indent=2)
        self.polygon = raw_points
        self.contour = np.array(self.polygon, dtype="int32") if self.polygon else None
        self._inside_frames.clear()

    def _get_foot_point(self, bbox):
        x1, y1, x2, y2 = bbox
        return int((x1 + x2) / 2), int(y2)

    def _get_centroid(self, bbox):
        x1, y1, x2, y2 = bbox
        return int((x1 + x2) / 2), int((y1 + y2) / 2)

    def _point_inside(self, pt):
        if self.contour is None or len(self.contour) < 3:
            return False
        result = cv2.pointPolygonTest(self.contour, (float(pt[0]), float(pt[1])), measureDist=False)
        return result >= 0

    def is_inside(self, bbox):
        return self._point_inside(self._get_foot_point(bbox)) or self._point_inside(self._get_centroid(bbox))

    def process(self, result):
        if self.contour is None:
            return result
        current_ids = set()
        for obj in result.objects:
            if obj.object_type not in ("human", "vehicle"):
                continue
            track_id = obj.track_id
            current_ids.add(track_id)
            physically_inside = self.is_inside(obj.bbox)
            prev = self._inside_frames.get(track_id, 0)
            if physically_inside:
                new_val = min(prev + 1, self._enter_threshold + 20)
            else:
                new_val = max(prev - 1, -(self._grace_frames + 1))
            self._inside_frames[track_id] = new_val
            if new_val >= self._enter_threshold or (new_val < 0 and new_val >= -self._grace_frames):
                obj.attributes["zone_state"] = "inside"
                obj.attributes["zone_id"] = "border_fence"
        expired = [tid for tid, v in self._inside_frames.items()
                   if tid not in current_ids and v <= -(self._grace_frames + 1)]
        for tid in expired:
            del self._inside_frames[tid]
        return result

    def draw_fence(self, frame, breach_active=False):
        if self.contour is None or len(self.contour) < 3:
            return
        overlay = frame.copy()
        fill_color = (0, 0, 255) if breach_active else (0, 0, 120)
        cv2.fillPoly(overlay, [self.contour], fill_color)
        cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)
        cv2.polylines(frame, [self.contour], isClosed=True, color=(0, 0, 255), thickness=3)
        for pt in self.contour:
            cv2.circle(frame, (int(pt[0]), int(pt[1])), 5, (0, 80, 255), -1)
        if breach_active:
            cx = int(self.contour[:, 0].mean())
            cy = int(self.contour[:, 1].mean())
            cv2.putText(frame, "RESTRICTED ZONE", (cx - 80, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2, cv2.LINE_AA)
