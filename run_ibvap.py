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
from suspicious_activity.loitering_detector import SuspiciousActivityDetector
from virtual_fence.fence_detector import VirtualFence
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

    import argparse
    parser = argparse.ArgumentParser(description="Run IBVAP Pipeline")
    parser.add_argument("--source", type=str, default="0", help="Video source (0 for webcam, or path to video file)")
    args = parser.parse_args()

    # Determine video source
    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"ERROR: Cannot open video source: {source}")
        return
        
    ret, test_frame = cap.read()
    if not ret:
        print("ERROR: Cannot read video frame.")
        return
    frame_h, frame_w = test_frame.shape[:2]

    detector      = HumanDetector()
    tracker       = HumanTracker()
    suspicious    = SuspiciousActivityDetector()
    fence         = VirtualFence(frame_w=frame_w, frame_h=frame_h)
    alarm_manager = AlarmManager()

    print(f"  Video source open: {source}. Press 'q' in the video window to stop.\n")
    frame_id = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("End of video stream or cannot read the frame.")
                break
            frame_id += 1
            ts = datetime.now(timezone.utc)

            # Step 1: Detect
            det = detector.detect(frame, "CAM_LIVE", frame_id, ts)

            # Step 2: Track
            tracked = tracker.track(det)
            
            # Step 3: Suspicious Activity (Omkar) & Virtual Fence (Abhilasha)
            analyzed = suspicious.process(tracked)
            analyzed = fence.process(analyzed)

            # Step 4: Alarm Manager (snapshot + scoring + broadcast)
            alarm_manager.submit(analyzed, frame=frame)

            # Step 5: Draw visuals on frame
            breach_active = any(obj.attributes.get("zone_state") == "inside" for obj in analyzed.objects)
            fence.draw_fence(frame, breach_active=breach_active)
            
            for obj in analyzed.objects:
                x1, y1, x2, y2 = obj.bbox
                activity = obj.attributes.get("activity")
                is_breaching = (obj.attributes.get("zone_state") == "inside")
                
                # Red if breaching or suspicious, green otherwise
                color = (0, 0, 255) if (activity or is_breaching) else (0, 255, 0)
                
                human_num = obj.track_id.split('-')[-1]
                base_label = f"Human {human_num}"
                
                tags = []
                if activity: tags.append(activity.upper())
                if is_breaching: tags.append("BREACH")
                
                label = f"{base_label} [{','.join(tags)}]" if tags else base_label

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # Draw centroid
                if "centroid" in obj.attributes:
                    cx, cy = obj.attributes["centroid"]
                    cv2.circle(frame, (int(cx), int(cy)), 5, (0, 0, 255), -1)

            cv2.putText(frame,
                f"IBVAP | Humans: {len(analyzed.objects)} | Frame: {frame_id}",
                (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (4, 195, 247), 2)

            # Step 6: Push frame to MJPEG buffer (for website live view)
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
