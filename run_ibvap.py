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
import threading
import time
import cv2
import uvicorn
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from human_detection.inference.detector import HumanDetector
from human_tracking.inference.tracker import HumanTracker
from alarm_manager.src.core import AlarmManager
from alarm_manager.src.frame_buffer import LIVE_FRAME


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

            # Step 3: Alarm Manager (snapshot + scoring + broadcast)
            alarm_manager.submit(tracked, frame=frame)

            # Step 4: Draw on frame
            for obj in tracked.objects:
                x1, y1, x2, y2 = obj.bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, obj.track_id, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                if "centroid" in obj.attributes:
                    cx, cy = obj.attributes["centroid"]
                    cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

            cv2.putText(frame,
                f"IBVAP | Humans: {len(tracked.objects)} | Frame: {frame_id}",
                (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (4, 195, 247), 2)

            # Step 5: Push frame to MJPEG buffer (for website live view)
            LIVE_FRAME.write(frame)

            cv2.imshow("IBVAP Live", frame)
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
