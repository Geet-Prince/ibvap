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
from suspicious_activity.loitering_detector import SuspiciousActivityDetector
from alarm_manager.src.core import AlarmManager

def main():
    print("=" * 55)
    print("  IBVAP Border Intelligence — Live Pipeline")
    print("  Dashboard: http://localhost:8000/ui")
    print("=" * 55)

    import argparse
    parser = argparse.ArgumentParser(description="Run IBVAP Live Pipeline")
    parser.add_argument("--source", type=str, default="0", help="Video source (0 for webcam, or path to video file)")
    args = parser.parse_args()

    detector       = HumanDetector()
    tracker        = HumanTracker()
    suspicious_det = SuspiciousActivityDetector()
    alarm_manager  = AlarmManager()

    # Determine video source
    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"ERROR: Cannot open video source: {source}")
        return

    print(f"Video source open: {source}. Press 'q' to stop.")
    frame_id = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("End of video stream or cannot read the frame.")
                break

            frame_id += 1
            timestamp = datetime.now(timezone.utc)

            # Step 1: Detect humans with YOLO
            det_result = detector.detect(frame, "CAM_LIVE", frame_id, timestamp)

            # Step 2: Track with DeepSORT
            track_result = tracker.track(det_result)

            # Step 3: Suspicious Activity Detection (Loitering, Erratic movement, Crowds)
            analyzed_result = suspicious_det.process(track_result)

            # Step 4: Submit to AlarmManager (snapshot + scoring + web broadcast)
            alarm_manager.submit(analyzed_result, frame=frame)

            # Step 5: Draw visuals
            for obj in analyzed_result.objects:
                x1, y1, x2, y2 = obj.bbox
                activity = obj.attributes.get("activity")
                color = (0, 0, 255) if activity else (0, 255, 0)
                
                human_num = obj.track_id.split('-')[-1]
                base_label = f"Human {human_num}"
                label = f"{base_label} [{activity.upper()}]" if activity else base_label

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
                if "centroid" in obj.attributes:
                    cx, cy = obj.attributes["centroid"]
                    cv2.circle(frame, (int(cx), int(cy)), 5, (0, 0, 255), -1)

            # Step 6: Show HUD
            cv2.putText(frame,
                f"Humans: {len(analyzed_result.objects)}  Frame: {frame_id}",
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
