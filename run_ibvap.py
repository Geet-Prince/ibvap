"""
run_ibvap.py — IBVAP Single Entry Point
=========================================
Starts the FastAPI server in a background thread AND runs the camera
pipeline in the main thread — so you only need ONE terminal.

Usage:
    python run_ibvap.py
    Then open: http://localhost:8000/ui
"""
import sys
import logging
import threading
import time
import cv2
import uvicorn
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from human_detection.inference.detector import HumanDetector
from human_tracking.inference.tracker import HumanTracker
from suspicious_activity.loitering_detector import SuspiciousActivityDetector
from alarm_manager.src.core import AlarmManager
from alarm_manager.src.frame_buffer import LIVE_FRAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("run_ibvap")


def start_server():
    uvicorn.run("alarm_manager.src.api:app", host="0.0.0.0",
                port=8000, log_level="warning")


def main():
    print("=" * 60)
    print("  IBVAP — Border Intelligence Platform")
    print("  Dashboard: http://localhost:8000/ui")
    print("  API Docs:  http://localhost:8000/docs")
    print("=" * 60)

    # Start FastAPI server in background thread
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    time.sleep(1.5)   # let server boot
    print("  Server ready. Starting camera pipeline...\n")

    detector      = HumanDetector()
    tracker       = HumanTracker()
    suspicious    = SuspiciousActivityDetector()
    alarm_manager = AlarmManager()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Cannot open webcam.")
        return

    print("  Camera open. Press 'q' in the video window to stop.\n")
    frame_id = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_id += 1
            ts = datetime.now(timezone.utc)

            # Step 1: Detect
            det = detector.detect(frame, "CAM_LIVE", frame_id, ts)

            # Step 2: Track
            tracked = tracker.track(det)

            # Log raw detection confidence for the CURRENT frame so we can see
            # whether scores are hovering near the 0.50 threshold. Sampled to
            # avoid log spam.
            if frame_id % 15 == 1:
                confs = [round(o.confidence, 3) for o in det.objects]
                log.info(
                    "frame=%s raw_conf=%s threshold=0.50 tracked=%s detected=%s",
                    frame_id, confs or [], len(tracked.objects), len(det.objects),
                )

            # Live human count comes from the CURRENT frame's tracked objects
            # (computed above from this very frame, never the previous one).
            live_humans = len(tracked.objects)

            # Step 3: Suspicious Activity (Omkar's module)
            analyzed = suspicious.process(tracked)

            # Step 4: Alarm Manager (snapshot + scoring + broadcast)
            alarm_manager.submit(analyzed, frame=frame)

            # Step 4: Draw overlays on a LOCAL preview copy only — NEVER on the
            # frame that gets streamed. The web /stream/live feed stays raw so the
            # dashboard can render HUD text as an HTML/CSS overlay instead.
            display = frame.copy()
            for obj in tracked.objects:
                x1, y1, x2, y2 = obj.bbox
                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(display, obj.track_id, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                if "centroid" in obj.attributes:
                    cx, cy = obj.attributes["centroid"]
                    cv2.circle(display, (cx, cy), 5, (0, 0, 255), -1)

            # Step 4b: Publish the per-frame live count to the shared buffer so
            # the web dashboard's "Live" HUD reads the SAME source as here.
            LIVE_FRAME.set_live(humans=live_humans, frame_id=frame_id)

            cv2.putText(display,
                f"IBVAP | Live Humans: {live_humans} | Frame: {frame_id}",
                (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (4, 195, 247), 2)

            # Step 5: Push the CLEAN raw frame to the MJPEG buffer (web live view)
            LIVE_FRAME.write(frame)

            cv2.imshow("IBVAP Live", display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Pipeline stopped.")

if __name__ == "__main__":
    main()
