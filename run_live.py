"""
run_live.py  — IBVAP Full Pipeline
===================================
Runs: YOLO Detection → Tracking → AlarmManager → WebSocket Dashboard

Usage:
    Terminal 1:  python run_live.py        (camera + detection pipeline)
    Terminal 2:  python start_server.py    (FastAPI server + dashboard)
    Browser:     http://localhost:8000/ui
"""
import sys
import cv2
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))

from human_detection.inference.detector import HumanDetector
from human_tracking.inference.tracker import HumanTracker
from alarm_manager.src.core import AlarmManager

def main():
    print("=" * 55)
    print("  IBVAP Border Intelligence — Live Pipeline")
    print("  Dashboard: http://localhost:8000/ui")
    print("=" * 55)

    detector     = HumanDetector()
    tracker      = HumanTracker()
    alarm_manager = AlarmManager()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Cannot open webcam.")
        return

    print("Camera open. Press 'q' to stop.")
    frame_id = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_id += 1
            timestamp = datetime.now(timezone.utc)

            # Step 1: Detect humans with YOLO
            det_result = detector.detect(frame, "CAM_LIVE", frame_id, timestamp)

            # Step 2: Track with DeepSORT
            track_result = tracker.track(det_result)

            # Step 3: Submit to AlarmManager (also crops snapshot from frame)
            alarm_manager.submit(track_result, frame=frame)

            # Step 4: Draw visuals
            for obj in track_result.objects:
                x1, y1, x2, y2 = obj.bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, obj.track_id, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
                if "centroid" in obj.attributes:
                    cx, cy = obj.attributes["centroid"]
                    cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

            # Step 5: Show HUD
            cv2.putText(frame,
                f"Humans: {len(track_result.objects)}  Frame: {frame_id}",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (4, 195, 247), 2)

            cv2.imshow("IBVAP Live — Press q to stop", frame)
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
