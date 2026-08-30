import cv2
import numpy as np
import os
from ultralytics import YOLO
import torch

def process_video_realtime(video_path, plate_model_path, vehicle_model_path='yolov8n.pt'):
    # Check for GPU to warn about speed
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device.upper()}")
    
    print(f"Loading vehicle model: {vehicle_model_path}")
    vehicle_model = YOLO(vehicle_model_path)
    
    print(f"Loading plate model: {plate_model_path}")
    plate_model = YOLO(plate_model_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video file: {video_path}")
        return

    # Create a resizable window so it fits on screen
    cv2.namedWindow('Real-time Tracking (Press Q to quit)', cv2.WINDOW_NORMAL)
    
    # Optional: resize window to 720p equivalent to make sure it's not too huge
    cv2.resizeWindow('Real-time Tracking (Press Q to quit)', 1280, 720)
    
    print("Playing video... Click the video window and press 'q' to stop.")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # Track vehicles (classes 2: car, 3: motorcycle, 5: bus, 7: truck)
        results = vehicle_model.track(frame, persist=True, classes=[2, 3, 5, 7], verbose=False)
        
        if results and len(results) > 0 and results[0].boxes and results[0].boxes.id is not None:
            # Extract vehicle bounding boxes and track IDs
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            confidences = results[0].boxes.conf.cpu().numpy()
            
            for box, track_id, conf in zip(boxes, track_ids, confidences):
                x1, y1, x2, y2 = box
                
                # Ensure coordinates are within frame bounds
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
                
                # Draw vehicle box and ID
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, f"ID: {track_id} ({conf:.2f})", (x1, max(0, y1 - 10)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                
                # Crop vehicle region of interest (ROI) for plate detection
                roi = frame[y1:y2, x1:x2]
                if roi.size > 0:
                    plate_results = plate_model(roi, verbose=False)
                    
                    if plate_results and len(plate_results) > 0 and plate_results[0].boxes:
                        plate_boxes = plate_results[0].boxes.xyxy.cpu().numpy().astype(int)
                        plate_confs = plate_results[0].boxes.conf.cpu().numpy()
                        
                        for p_box, p_conf in zip(plate_boxes, plate_confs):
                            px1, py1, px2, py2 = p_box
                            
                            # Shift coordinates to full frame
                            abs_px1 = x1 + px1
                            abs_py1 = y1 + py1
                            abs_px2 = x1 + px2
                            abs_py2 = y1 + py2
                            
                            # Draw plate box
                            cv2.rectangle(frame, (abs_px1, abs_py1), (abs_px2, abs_py2), (0, 255, 0), 2)
                            
                            # Write confidence text
                            conf_text = f"Plate: {p_conf:.2f}"
                            cv2.putText(frame, conf_text, (abs_px1, max(0, abs_py1 - 10)), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Show the frame in the popup window
        cv2.imshow('Real-time Tracking (Press Q to quit)', frame)
        
        # Wait 1ms and check for 'q' to quit (this also refreshes the window)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Playback stopped by user.")
            break
            
    cap.release()
    cv2.destroyAllWindows()
    print("Finished playing video.")

if __name__ == "__main__":
    VIDEO_FILE = "WhatsApp Video 2026-08-30 at 19.07.13.mp4"
    PLATE_MODEL_FILE = "best.pt" 
    
    process_video_realtime(VIDEO_FILE, PLATE_MODEL_FILE)
