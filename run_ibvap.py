"""
run_ibvap.py â€” IBVAP Single Entry Point (V8 Multi-Camera Architecture)
=============================================================================
Changes from V7:
1. Multi-Camera AI: ALL cameras get YOLO detection, not just one.
2. Per-Camera IOU Tracking: Simple IOU tracker per camera (no ByteTrack
   cross-camera contamination).
3. Per-Camera Virtual Fence: Each camera loads its own fence polygon.
4. ANPR Integration: Automatic plate reading on detected vehicles.
5. Better error handling for bad/black video files.
"""
import sys
import queue
import threading
import time
import cv2
import uvicorn
import numpy as np
import torch
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ultralytics import YOLO
from suspicious_activity.loitering_detector import SuspiciousActivityDetector
from virtual_fence.fence_detector import VirtualFence
from alarm_manager.src.core import AlarmManager
from alarm_manager.src.frame_buffer import CAMERA_REGISTRY
from contracts.schema import DetectionResult, DetectedObject

# Try to import ANPR (optional â€” needs easyocr)
try:
    from anpr.plate_reader import PlateReader
    _ANPR_AVAILABLE = True
except Exception:
    _ANPR_AVAILABLE = False


# â”€â”€ Simple IOU Tracker â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class SimpleIOUTracker:
    """Per-camera IOU-based tracker for assigning stable track IDs.

    Replaces ByteTrack when multiple cameras are batched through a single
    YOLO model, avoiding cross-camera track-ID contamination that occurs
    when ``model.track(persist=True)`` receives frames from different sources.
    """

    def __init__(self, iou_thresh: float = 0.25, max_lost: int = 15):
        self.tracks: dict[int, dict] = {}   # tid â†’ {"bbox", "lost"}
        self.next_id: int = 1
        self.iou_thresh = iou_thresh
        self.max_lost = max_lost

    # ------------------------------------------------------------------ #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _iou_matrix(t_bboxes, d_bboxes):
        """Vectorized IOU matrix."""
        if len(t_bboxes) == 0 or len(d_bboxes) == 0:
            return np.zeros((len(t_bboxes), len(d_bboxes)), dtype=np.float32)
        t = np.asarray(t_bboxes, dtype=np.float32)
        d = np.asarray(d_bboxes, dtype=np.float32)
        x1 = np.maximum(t[:, 0:1], d[None, :, 0])
        y1 = np.maximum(t[:, 1:2], d[None, :, 1])
        x2 = np.minimum(t[:, 2:3], d[None, :, 2])
        y2 = np.minimum(t[:, 3:4], d[None, :, 3])
        inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
        area_t = ((t[:, 2] - t[:, 0]) * (t[:, 3] - t[:, 1]))[:, None]
        area_d = ((d[:, 2] - d[:, 0]) * (d[:, 3] - d[:, 1]))[None, :]
        union = area_t + area_d - inter
        return np.where(union > 0, inter / union, 0.0).astype(np.float32)

    # ------------------------------------------------------------------ #
    def update(self, detections):
        """Assign track_id to each detection dict.
        Vectorized with NumPy; no per-pair Python IOU loops.
        """
        for v in self.tracks.values():
            v["lost"] += 1

        matched = {}
        unmatched = list(range(len(detections)))

        if self.tracks and detections:
            tids = sorted(self.tracks.keys())
            t_bboxes = [self.tracks[tid]["bbox"] for tid in tids]
            d_bboxes = [det["bbox"] for det in detections]
            iou_mat = self._iou_matrix(t_bboxes, d_bboxes)

            remaining = list(range(len(detections)))
            for t_i, tid in enumerate(tids):
                if not remaining:
                    break
                best_di = max(remaining, key=lambda di: iou_mat[t_i, di])
                if float(iou_mat[t_i, best_di]) >= self.iou_thresh:
                    matched[best_di] = tid
                    remaining.remove(best_di)
                    self.tracks[tid]["bbox"] = detections[best_di]["bbox"]
                    self.tracks[tid]["lost"] = 0
            unmatched = remaining

        for di in unmatched:
            tid = self.next_id; self.next_id += 1
            matched[di] = tid
            self.tracks[tid] = {"bbox": detections[di]["bbox"], "lost": 0}

        dead = [t for t, v in self.tracks.items() if v["lost"] > self.max_lost]
        for t in dead:
            del self.tracks[t]

        for i, det in enumerate(detections):
            det["track_id"] = matched.get(i, 0)
        return detections


# â”€â”€ Threaded Video Capture â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ThreadedCamera:
    def __init__(self, src_str: str, cam_id: str, name: str,
                 w: int, h: int, start_active: bool = True):
        self.src_str = src_str
        self.id = cam_id
        self.name = name
        self.w = w
        self.h = h
        self.is_active = start_active
        self.cap = None

        self.suspicious = SuspiciousActivityDetector()
        self.fence = VirtualFence(cam_id=cam_id, video_name=name,
                                  frame_w=w, frame_h=h)
        self.tracker = SimpleIOUTracker()

        self.latest_frame = np.zeros((h, w, 3), dtype=np.uint8)
        self.latest_frame_id = 0
        self.last_analyzed = None
        self.last_raw_vehicles: list = []
        self.running = True
        self.track_history: dict = {}
        self.vehicle_plates: dict = {}         # track_key -> plate string
        self.vehicle_plate_retries: dict = {}   # track_key -> retry count
        self._decode_failures = 0

        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    # â”€â”€ Background reader â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _update(self):
        fps = 25.0
        frame_time = 1.0 / fps

        while self.running:
            if not self.is_active:
                if self.cap is not None:
                    self.cap.release()
                    self.cap = None
                time.sleep(0.5)
                continue

            if self.cap is None:
                self.cap = cv2.VideoCapture(self.src_str)
                if self.cap.isOpened():
                    fps = self.cap.get(cv2.CAP_PROP_FPS)
                    if fps <= 0 or fps > 60:
                        fps = 25.0
                    frame_time = 1.0 / fps
                else:
                    print(f"  [WARN] {self.id}: Failed to open {self.src_str}")
                    self._decode_failures += 1
                    time.sleep(2.0)
                    continue

            loop_start = time.time()
            ret, frame = self.cap.read() if self.cap else (False, None)

            if not ret:
                self._decode_failures += 1
                if self._decode_failures > 100:
                    print(f"  [WARN] {self.id}: Too many decode failures, "
                          f"re-opening sourceâ€¦")
                    if self.cap:
                        self.cap.release()
                        self.cap = None
                    self._decode_failures = 0
                    time.sleep(1.0)
                    continue
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            # Good frame â€” reset failure counter.
            self._decode_failures = 0
            self.latest_frame = frame
            self.latest_frame_id += 1

            elapsed = time.time() - loop_start
            sleep_time = frame_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def release(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()


# â”€â”€ Consolidated Batched AI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ConsolidatedBatchedAI:
    """Runs a single YOLOv8 model on a batch of ALL camera frames using
    ``predict()`` for pure detection (no tracking state to contaminate)."""

    def __init__(self):
        print("  [GPU] Initializing Consolidated YOLOv8 Batchedâ€¦")
        self.model = YOLO("yolov8n.pt")
        self.model.to("cuda")

        # torch.compile fuses CUDA kernels (~20-40% faster inference, PyTorch 2.x)
        try:
            self.model.model = torch.compile(
                self.model.model, mode="reduce-overhead", fullgraph=False
            )
            print("  [GPU] torch.compile enabled")
        except Exception as _e:
            print(f"  [WARN] torch.compile unavailable: {_e}")
        self._anpr = None
        if _ANPR_AVAILABLE:
            try:
                self._anpr = PlateReader()
                print("  [ANPR] Plate reader initialised.")
            except Exception as exc:
                print(f"  [WARN] ANPR init failed: {exc}")

    def warmup(self, n_cams: int = 1) -> None:
        """Warmup with actual batch size and FP16 (avoids cold CUDA compile on first real call)."""
        try:
            for bs in sorted({1, min(n_cams, 4)}):
                dummy = [np.zeros((640, 640, 3), dtype=np.uint8)] * bs
                self.model.predict(dummy, device=0, half=True, verbose=False)
            print(f"  [GPU] Warmup done (bs=1 and bs={min(n_cams,4)})")
        except Exception as exc:
            print(f"Warmup error: {exc}")

    # ------------------------------------------------------------------ #
    def process_batch(
        self,
        frames: list[np.ndarray],
        cam_nodes: list,
        ts: datetime,
    ) -> dict:
        """Run YOLO on every camera frame, then per-camera IOU tracking.

        Returns ``{cam_id: (humans_DR, vehicles_DR)}`` where each value
        is a pair of ``DetectionResult`` objects.
        """
        CLASS_MAP = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
        results_map: dict = {}
        if not frames:
            return results_map

        try:
            with torch.no_grad():
                yolo_results = self.model.predict(
                    source=frames,
                    classes=[0, 2, 3, 5, 7],
                    conf=0.25,
                    imgsz=640,
                    device=0,
                    half=True,
                    verbose=False,
                )

            for i, res in enumerate(yolo_results):
                cam = cam_nodes[i]

                # â”€â”€ Parse raw detections â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                # Batch GPU->CPU tensor transfer (3 transfers vs 3N per detection)
                raw_dets = []
                if res.boxes and len(res.boxes):
                    xyxy  = res.boxes.xyxy.cpu().numpy().astype(int)
                    clses = res.boxes.cls.cpu().numpy().astype(int)
                    confs = res.boxes.conf.cpu().numpy()
                    raw_dets = [
                        {"bbox": tuple(xyxy[j]), "cls": int(clses[j]), "conf": float(confs[j])}
                        for j in range(len(xyxy))
                    ]

                # â”€â”€ Per-camera IOU tracking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                tracked = cam.tracker.update(raw_dets)

                # â”€â”€ Build DetectionResult objects â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                dr_h = DetectionResult(
                    module="human_tracking", camera_id=cam.id,
                    frame_id=cam.latest_frame_id, timestamp_utc=ts,
                    objects=[],
                )
                dr_v = DetectionResult(
                    module="vehicle_detection", camera_id=cam.id,
                    frame_id=cam.latest_frame_id, timestamp_utc=ts,
                    objects=[],
                )

                for det in tracked:
                    x1, y1, x2, y2 = det["bbox"]
                    cls_id = det["cls"]
                    conf = det["conf"]
                    tid = det["track_id"]
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                    if cls_id == 0:
                        # â”€â”€ Human â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                        track_key = f"det-{tid}"
                        attrs: dict = {"centroid": (cx, cy)}

                        if track_key in cam.track_history:
                            pcx, pcy, pt = cam.track_history[track_key]
                            dt = (ts - pt).total_seconds()
                            if dt > 0:
                                attrs["velocity_px_per_s"] = (
                                    (cx - pcx) / dt,
                                    (cy - pcy) / dt,
                                )
                        cam.track_history[track_key] = (cx, cy, ts)

                        dr_h.objects.append(DetectedObject(
                            object_type="human",
                            bbox=(x1, y1, x2, y2),
                            confidence=conf,
                            track_id=track_key,
                            attributes=attrs,
                        ))
                    else:
                        # â”€â”€ Vehicle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                        v_attrs: dict = {
                            "vehicle_type": CLASS_MAP.get(cls_id, "vehicle"),
                            "centroid": (cx, cy),
                        }

                        v_track_key = f"veh-{tid}"
                        
                        # Cache plates to avoid running ANPR every frame
                            
                        if v_track_key in cam.vehicle_plates:
                            v_attrs["plate_no"] = cam.vehicle_plates[v_track_key]
                        elif self._anpr is not None and cam.vehicle_plate_retries.get(v_track_key, 0) < 5:
                            cam.vehicle_plate_retries[v_track_key] = cam.vehicle_plate_retries.get(v_track_key, 0) + 1
                            try:
                                plate = self._anpr.read_plate(
                                    frames[i], (x1, y1, x2, y2))
                                if plate:
                                    v_attrs["plate_no"] = plate
                                    cam.vehicle_plates[v_track_key] = plate
                            except Exception:
                                pass

                        dr_v.objects.append(DetectedObject(
                            object_type="vehicle",
                            bbox=(x1, y1, x2, y2),
                            confidence=conf,
                            track_id=f"veh-{tid}",
                            attributes=v_attrs,
                        ))

                results_map[cam.id] = (dr_h, dr_v)

        except Exception as exc:
            print(f"Batch AI error: {exc}")
            import traceback
            traceback.print_exc()

        return results_map


# â”€â”€ Server â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def start_server():
    from alarm_manager.src.api import app
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


# â”€â”€ Main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def main():
    print("=" * 60)
    print("  IBVAP â€” Border Intelligence Platform (V8 Multi-Camera)")
    print("  Dashboard: http://localhost:8000/ui")
    print("=" * 60)

    srv = threading.Thread(target=start_server, daemon=True)
    srv.start()
    time.sleep(1.5)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source", type=str,
        default=str(
            (Path(__file__).resolve().parent.parent / "clips").resolve()),
    )
    parser.add_argument("--max-cams", type=int, default=16)
    parser.add_argument("--multi-cam-ai", action="store_true", help="Enable AI processing on all cameras simultaneously")
    args = parser.parse_args()

    source_path = Path(args.source)
    video_sources = (
        sorted(source_path.glob("*.mp4"))[:args.max_cams]
        if source_path.is_dir()
        else [args.source]
    )

    cam_nodes: list[ThreadedCamera] = []
    for i, src in enumerate(video_sources):
        src_str = str(src) if isinstance(src, Path) else src
        cap = cv2.VideoCapture(src_str)
        if not cap.isOpened():
            print(f"  [SKIP] Cannot open: {src_str}")
            continue
        ret, test = cap.read()
        cap.release()
        if not ret:
            print(f"  [SKIP] Cannot read frame from: {src_str}")
            continue

        cam_id = f"CAM_{i + 1:02d}"
        name = src.stem if isinstance(src, Path) else str(src)
        CAMERA_REGISTRY.register(cam_id, name=name, source=src_str)

        # ALL cameras start active.
        cam_nodes.append(
            ThreadedCamera(src_str, cam_id, name,
                           test.shape[1], test.shape[0], start_active=True))

    n_cams = len(cam_nodes)
    if not n_cams:
        print("No cameras found. Exiting.")
        return

    print(f"  âœ“ {n_cams} cameras running â€” ALL active, ALL get AI processing")

    alarm_manager = AlarmManager()

    alarm_queue: queue.Queue = queue.Queue(maxsize=200)

    def alarm_worker():
        while True:
            analyzed, frame_copy = alarm_queue.get()
            try:
                alarm_manager.submit(analyzed, frame=frame_copy)
            except Exception:
                pass

    threading.Thread(target=alarm_worker, daemon=True).start()

    batched_ai = ConsolidatedBatchedAI()
    batched_ai.warmup(n_cams=len(cam_nodes))

    # Store cam_nodes reference so the API layer can access fences, etc.
    CAMERA_REGISTRY._cam_nodes = cam_nodes

    max_grid = min(n_cams, 4)
    cols = 2 if max_grid > 1 else 1
    rows = int(np.ceil(max_grid / cols))
    cell_w, cell_h = 480, 270

    global_frame_count = 0

    try:
        while True:
            t_start = time.time()

            ai_cam_id = CAMERA_REGISTRY.active_ai_cam
            if args.multi_cam_ai:
                for cam in cam_nodes: cam.is_active = True
            elif ai_cam_id == '__grid__':
                for i, cam in enumerate(cam_nodes):
                    cam.is_active = (i < max_grid)
            else:
                for cam in cam_nodes:
                    cam.is_active = (cam.id == ai_cam_id)
                    
            # â”€â”€ STAGE 1: DECODE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # ALL cameras decoded each loop for live MJPEG thumbnails
            all_cams: list = []
            all_frames: list = []
            for cam in cam_nodes:
                if cam.latest_frame is not None:
                    all_cams.append(cam)
                    all_frames.append(cam.latest_frame.copy())

            # active_cams = subset that gets AI this cycle
            active_cams: list[ThreadedCamera] = []
            frames: list[np.ndarray] = []
            for cam, fr in zip(all_cams, all_frames):
                if cam.is_active:
                    active_cams.append(cam)
                    frames.append(fr)

            if not all_cams:
                time.sleep(0.01)
                continue

            global_frame_count += 1
            ts = datetime.now(timezone.utc)

            # Run YOLO every 2nd frame for accuracy/perf balance.
            run_yolo = (global_frame_count % 2 == 0)

            # â”€â”€ STAGE 2: BATCHED INFERENCE ON ALL CAMERAS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            t_infer_start = time.time()
            results_map: dict = {}
            if run_yolo:
                if args.multi_cam_ai:
                    ai_frames = frames
                    ai_cams = active_cams
                else:
                    ai_cam_id = CAMERA_REGISTRY.active_ai_cam
                    ai_frames = []
                    ai_cams = []
                    for f, c in zip(frames, active_cams):
                        if c.id == ai_cam_id:
                            ai_frames.append(f)
                            ai_cams.append(c)
                            break
                    if not ai_cams and active_cams:
                        ai_frames = [frames[0]]
                        ai_cams = [active_cams[0]]
                
                results_map = batched_ai.process_batch(ai_frames, ai_cams, ts)
            t_infer = time.time() - t_infer_start

            # â”€â”€ STAGE 3: TRACKING + SUSPICIOUS + FENCE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            t_track_start = time.time()
            for i, cam in enumerate(active_cams):
                if not args.multi_cam_ai and cam.id != CAMERA_REGISTRY.active_ai_cam:
                    cam.last_analyzed = None
                    continue

                if cam.id in results_map:
                    tracked_humans, tracked_vehicles = results_map[cam.id]
                    cam.last_raw_vehicles = tracked_vehicles.objects

                    # Merge vehicles into the human result for unified
                    # downstream processing (suspicious + fence + alarm).
                    tracked_humans.objects.extend(cam.last_raw_vehicles)

                    # Suspicious activity heuristics.
                    analyzed = cam.suspicious.process(tracked_humans)
                    # Virtual fence breach checks.
                    analyzed = cam.fence.process(analyzed)
                    cam.last_analyzed = analyzed

                    # Submit to alarm system (non-blocking).
                    try:
                        alarm_queue.put_nowait(
                            (analyzed, frames[i].copy()))
                    except queue.Full:
                        pass
                # else: skipped frame â€” keep cam.last_analyzed for render
            t_track = time.time() - t_track_start

            # â”€â”€ STAGE 4: RENDER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            t_render_start = time.time()
            grid = np.zeros(
                (rows * cell_h, cols * cell_w, 3), dtype=np.uint8)

            ai_cam_id = CAMERA_REGISTRY.active_ai_cam
            grid_cams = []
            for cam in active_cams:
                if cam.id == ai_cam_id:
                    grid_cams.append(cam.id)
                    break
            for cam in active_cams:
                if len(grid_cams) >= max_grid:
                    break
                if cam.id not in grid_cams:
                    grid_cams.append(cam.id)

            # Write raw frames to ALL camera MJPEG buffers first (keeps thumbnails live).
            # Then do the full annotated render only for AI-active cameras.
            for cam, raw_fr in zip(all_cams, all_frames):
                if cam not in active_cams:
                    # Non-AI camera: write raw frame + HUD to its MJPEG buffer
                    raw_disp = raw_fr.copy()
                    cam.fence.draw_fence(raw_disp, breach_active=False)
                    cv2.putText(raw_disp, f"{cam.id} [RAW]",
                                (10, 26), cv2.FONT_HERSHEY_SIMPLEX,
                                0.6, (150, 150, 150), 2)
                    buf = CAMERA_REGISTRY.get(cam.id)
                    if buf:
                        buf.write(raw_disp)
                    CAMERA_REGISTRY.update_live(cam.id, 0, cam.latest_frame_id)

            for i, cam in enumerate(active_cams):
                display = frames[i]
                analyzed = cam.last_analyzed

                # Draw fence overlay.
                breach_active = False
                if analyzed:
                    breach_active = any(
                        o.attributes.get("zone_state") == "inside"
                        for o in analyzed.objects
                    )
                cam.fence.draw_fence(display, breach_active=breach_active)

                # Draw detection boxes.
                if analyzed:
                    for obj in analyzed.objects:
                        x1, y1, x2, y2 = obj.bbox
                        activity = obj.attributes.get("activity")
                        is_breach = (
                            obj.attributes.get("zone_state") == "inside")
                        color = (
                            (255, 0, 0) if obj.object_type == "vehicle"
                            else ((0, 0, 255) if (activity or is_breach)
                                  else (0, 255, 0))
                        )

                        track_num = obj.track_id.split("-")[-1]
                        base = f"{obj.object_type.capitalize()} {track_num}"

                        tags: list[str] = []
                        if "vehicle_type" in obj.attributes:
                            tags.append(
                                obj.attributes["vehicle_type"].upper())
                        if "plate_no" in obj.attributes:
                            tags.append(
                                f"[{obj.attributes['plate_no']}]")
                        if activity:
                            tags.append(activity.upper())
                        if is_breach:
                            tags.append("BREACH")

                        label = (f"{base} {' '.join(tags)}"
                                 if tags else base)
                        cv2.rectangle(
                            display, (int(x1), int(y1)),
                            (int(x2), int(y2)), color, 2)
                        cv2.putText(
                            display, label,
                            (int(x1), int(y1) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        if "centroid" in obj.attributes:
                            cx, cy = obj.attributes["centroid"]
                            cv2.circle(
                                display, (int(cx), int(cy)),
                                5, (0, 0, 255), -1)

                obj_count = (len(analyzed.objects)
                             if analyzed else 0)

                # HUD label.
                is_ai = args.multi_cam_ai or cam.id == CAMERA_REGISTRY.active_ai_cam
                status_label = "[AI]" if is_ai else "[RAW]"
                cv2.putText(
                    display,
                    f"{cam.id} {status_label} | Obj: {obj_count}",
                    (10, 26), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 0) if is_ai else (150, 150, 150), 2)

                # Write to per-camera MJPEG buffer.
                buf = CAMERA_REGISTRY.get(cam.id)
                if buf:
                    buf.write(display)
                CAMERA_REGISTRY.update_live(
                    cam.id, obj_count, cam.latest_frame_id)

                # Grid cell.
                if cam.id in grid_cams:
                    g_idx = grid_cams.index(cam.id)
                    r, c = divmod(g_idx, cols)
                    if r < rows:
                        cell = cv2.resize(display, (cell_w, cell_h))
                        grid[r * cell_h:(r + 1) * cell_h,
                             c * cell_w:(c + 1) * cell_w] = cell

            CAMERA_REGISTRY.grid.write(grid)
            t_render = time.time() - t_render_start

            # â”€â”€ FPS Control & Logging â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            elapsed = time.time() - t_start
            fps = 1.0 / elapsed if elapsed > 0 else 0

            if global_frame_count % 30 == 0:
                print(
                    f"[FPS: {fps:.1f}] Cams: {len(active_cams)} | "
                    f"Infer: {t_infer * 1000:.1f}ms | "
                    f"Track: {t_track * 1000:.1f}ms | "
                    f"Render: {t_render * 1000:.1f}ms")

            # Note: torch.cuda.empty_cache() removed from hot loop (causes CUDA stall)

            target_delay = 1.0 / 30.0
            if elapsed < target_delay:
                time.sleep(target_delay - elapsed)

    except KeyboardInterrupt:
        pass
    finally:
        for cam in cam_nodes:
            cam.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        print("Pipeline stopped.")


if __name__ == "__main__":
    main()

