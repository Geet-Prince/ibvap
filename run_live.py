import cv2
import time
from datetime import datetime, timezone

from human_detection.inference.detector import HumanDetector
from human_tracking.inference.tracker import HumanTracker
from contracts.schema import DetectionResult

class MockAlarmManager:
    def submit(self, result: DetectionResult):
        print(f"[{result.timestamp_utc.strftime('%H:%M:%S')}] Frame: {result.frame_id} | Humans Tracked: {len(result.objects)}")

def main():
    print("Initializing components...")
    detector = HumanDetector()
    tracker = HumanTracker()
    alarm_manager = MockAlarmManager()

    # Try to open webcam (0)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam. Ensure a camera is connected.")
        return

    print("Camera opened successfully. A window should appear on your screen!")
    print("Press 'q' while focused on the video window to stop.")
    
    frame_id = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame.")
                break
            
            frame_id += 1
            timestamp = datetime.now(timezone.utc)
            
            # Step 1: Detect
            det_result = detector.detect(
                frame=frame,
                camera_id="CAM_LIVE",
                frame_id=frame_id,
                timestamp_utc=timestamp
            )
            
            # Step 2: Track
            track_result = tracker.track(det_result)
            
            # Step 3: Submit to Alarm Manager
            alarm_manager.submit(track_result)
            
            # Step 4: Draw visuals on the frame
            for obj in track_result.objects:
                x1, y1, x2, y2 = obj.bbox
                track_id = obj.track_id
                
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw label with ID
                label = f"{track_id}"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Draw centroid
                if "centroid" in obj.attributes:
                    cx, cy = obj.attributes["centroid"]
                    cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)

            # Show the video feed with the visuals
            cv2.imshow("IBVAP Live Tracking", frame)
            
            # Press 'q' to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\nStopping via KeyboardInterrupt...")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Cleaned up camera and windows.")

if __name__ == "__main__":
    main()
