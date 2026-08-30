import cv2
import numpy as np
import os
from ultralytics import YOLO

def process_video(video_path, output_path, plate_model_path, vehicle_model_path='yolov8n.pt'):
    # Load vehicle model
    print(f"Loading vehicle model: {vehicle_model_path}")
    vehicle_model = YOLO(vehicle_model_path)
    
    # Check if plate model exists
    plate_model = None
    if os.path.exists(plate_model_path):
        print(f"Loading plate model: {plate_model_path}")
        try:
            plate_model = YOLO(plate_model_path)
        except Exception as e:
            print(f"Error loading plate model: {e}")
    else:
        print(f"WARNING: Plate model '{plate_model_path}' not found!")
        print("Vehicle tracking will proceed, but number plates will NOT be detected.")

    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video file: {video_path}")
        return

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print("Processing video...")
    
    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"Processed {frame_count} frames...")

        # Track vehicles (classes 2: car, 3: motorcycle, 5: bus, 7: truck for COCO)
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
                x2, y2 = min(width, x2), min(height, y2)
                
                # Draw vehicle box and ID
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, f"Vehicle ID: {track_id} ({conf:.2f})", (x1, max(0, y1 - 10)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                
                # Crop vehicle region of interest (ROI) for plate detection
                if plate_model is not None:
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
                else:
                    # Warn visually if missing plate model
                    cv2.putText(frame, "Waiting for best.pt...", (x1, y2 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Write the frame
        out.write(frame)
        
    cap.release()
    out.release()
    print(f"Processing complete! Saved to {output_path}")

if __name__ == "__main__":
    VIDEO_FILE = "WhatsApp Video 2026-08-30 at 19.07.13.mp4"
    OUTPUT_FILE = "output_tracked.mp4"
    PLATE_MODEL_FILE = "best.pt" 
    
    process_video(VIDEO_FILE, OUTPUT_FILE, PLATE_MODEL_FILE)
