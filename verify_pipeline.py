import cv2
import numpy as np
from datetime import datetime, timezone
from human_detection.inference import HumanDetector
from human_tracking.inference import HumanTracker
from contracts.schema import DetectedObject, DetectionResult

def run_test():
    print("Initializing HumanDetector...")
    detector = HumanDetector()
    
    print("Initializing HumanTracker...")
    tracker = HumanTracker()
    
    print("Creating a dummy frame (640x480)...")
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    print("Running detection...")
    # Inject a fake detection object to guarantee the tracker gets something to track
    det_result = detector.detect(
        frame=frame,
        camera_id="CAM_TEST",
        frame_id=1,
        timestamp_utc=datetime.now(timezone.utc)
    )
    
    # If the random frame doesn't yield a human, inject one for testing purposes
    if len(det_result.objects) == 0:
        print("No human detected in random noise (expected). Injecting a mock human detection...")
        det_result.objects.append(DetectedObject(
            object_type="human",
            track_id="det-1-0",
            confidence=0.95,
            bbox=(100, 100, 200, 300),
            attributes={}
        ))
    
    print(f"Detection Result (Objects found: {len(det_result.objects)}):")
    print(det_result.model_dump_json(indent=2))
    
    print("Running tracking...")
    track_result = tracker.track(det_result)
    
    print(f"Tracking Result (Objects tracked: {len(track_result.objects)}):")
    print(track_result.model_dump_json(indent=2))
    
    print("Pipeline executed successfully!")

if __name__ == "__main__":
    run_test()
