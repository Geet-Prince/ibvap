import cv2
import time
import os
import torch
from ultralytics import YOLO
from core_contracts import FrameState, Track, BoundingBox, ObjectType
from loitering_detector import SuspiciousActivityDetector

def run_live_test(video_path="test_video.mp4"):
    if not os.path.exists(video_path):
        print(f"Error: Could not find '{video_path}'.")
        print("Please download a video and save it as 'test_video.mp4' in this folder.")
        return

    # Check for GPU (CUDA) availability with automatic CPU fallback
    if torch.cuda.is_available():
        device = 0
        device_name = torch.cuda.get_device_name(0)
        print(f"[ACCELERATION] GPU Detected: {device_name} -> Using CUDA device:0")
    else:
        device = "cpu"
        device_name = "CPU"
        print("[ACCELERATION] No GPU/CUDA detected -> Running on CPU mode")

    print("Loading YOLO model... (This will download the yolov8n.pt model if not present)")
    model = YOLO("yolov8n.pt")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open {video_path}.")
        return

    # Initialize the detector. 
    # Note: We lowered the time_threshold to 5.0 seconds so you don't have to wait 
    # too long while watching the video to see the loitering event trigger!
    detector = SuspiciousActivityDetector(
        time_threshold=5.0, 
        distance_threshold=150.0,
        crowd_distance_threshold=150.0,
        crowd_min_people=3,
        speed_threshold=150.0  # Pixels per second
    )

    prev_positions = {}
    active_alerts = {}  # Stores {track_id: (alert_subtype, timestamp)}

    frame_count = 0
    fps_time = time.time()
    fps_display = 0.0

    print("Starting video processing... Press 'q' on the video window to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        current_time = time.time()
        
        # Calculate real-time FPS
        if current_time - fps_time >= 0.5:
            fps_display = 1.0 / max(current_time - prev_time, 0.001) if 'prev_time' in locals() else 30.0
            fps_time = current_time
        prev_time = current_time
        
        # 1. Run YOLO tracking with chosen device (GPU or CPU)
        results = model.track(frame, persist=True, classes=[0], device=device, verbose=False)
        
        tracks_for_frame = []
        
        # 2. Extract bounding boxes and IDs
        if results and results[0].boxes and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            
            for box, track_id, conf in zip(boxes, track_ids, confidences):
                x1, y1, x2, y2 = box
                track_id_str = f"human_{int(track_id)}"
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                
                # Calculate velocity manually since YOLO doesn't provide it
                vx, vy = 0.0, 0.0
                if track_id_str in prev_positions:
                    px, py, pt = prev_positions[track_id_str]
                    dt = current_time - pt
                    if dt > 0:
                        vx = (cx - px) / dt
                        vy = (cy - py) / dt
                        
                prev_positions[track_id_str] = (cx, cy, current_time)
                
                tracks_for_frame.append(
                    Track(
                        track_id=track_id_str,
                        object_type=ObjectType.HUMAN,
                        bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                        confidence=conf,
                        velocity_x=vx,
                        velocity_y=vy
                    )
                )

        # 3. Create the standard IBVAP FrameState contract
        frame_state = FrameState(
            camera_id="cam_01",
            timestamp=current_time,
            frame_id=frame_count,
            tracks=tracks_for_frame
        )
        
        # 4. Feed it into Omkar's logic module!
        events = detector.process_frame(frame_state)
        
        # 5. Process events for visualization
        for event in events:
            subtype = event.metadata['subtype']
            print(f"\n[ALERT FIRED] {subtype.upper()}! ID: {event.event_id}")
            for tid in event.track_ids:
                active_alerts[tid] = (subtype, current_time)
                
        # 6. Draw the results on the video frame
        for track in tracks_for_frame:
            tid = track.track_id
            x1, y1, x2, y2 = map(int, [track.bbox.x1, track.bbox.y1, track.bbox.x2, track.bbox.y2])
            
            color = (0, 255, 0)  # Default Green
            label = tid
            
            if tid in active_alerts:
                alert_type, alert_time = active_alerts[tid]
                color = (0, 0, 255)  # Red for Suspicious!
                label = f"{tid} [ALERT: {alert_type.upper()}]"
            
            # Draw Box and Label
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
        # Draw HUD status overlay (Device mode & FPS)
        hud_text = f"Hardware: {device_name} | FPS: {fps_display:.1f}"
        cv2.putText(frame, hud_text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        # Optional: Resize video if it's massive so it fits on your screen
        display_frame = cv2.resize(frame, (1280, 720)) if frame.shape[1] > 1280 else frame
        
        cv2.imshow("IBVAP - Suspicious Activity Live Test", display_frame)
        
        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()
    print("Finished processing video.")

if __name__ == "__main__":
    run_live_test("test_video.mp4")
