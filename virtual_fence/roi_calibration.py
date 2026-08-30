"""
roi_calibration.py
-------------------
Run this ONCE per camera/video source to define the restricted-area polygon
by clicking directly on the real video frame. This replaces guessed
coordinates with coordinates measured from your actual footage.

Controls:
    Left click   -> add a polygon point
    Right click  -> remove the last point
    'r'          -> reset all points
    's'          -> save points to roi_config.json and exit
    'q'          -> quit without saving

Usage:
    python roi_calibration.py --source video.mp4
    python roi_calibration.py --source 0        # webcam
"""

import cv2
import json
import argparse

points = []


def mouse_callback(event, x, y, flags, param):
    global points
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(f"Added point: ({x}, {y})")
    elif event == cv2.EVENT_RBUTTONDOWN:
        if points:
            removed = points.pop()
            print(f"Removed point: {removed}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="video.mp4",
                         help="Video file path or webcam index (e.g. 0)")
    parser.add_argument("--output", default="roi_config.json",
                         help="Where to save the calibrated polygon")
    args = parser.parse_args()

    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {source}")

    ret, frame = cap.read()
    if not ret:
        raise RuntimeError("Could not read a frame from the source.")

    h, w = frame.shape[:2]
    print(f"Frame size: {w}x{h}")
    print("Click to add polygon points around the RESTRICTED area "
          "(follow the fence line). Press 's' to save, 'q' to quit.")

    window_name = "ROI Calibration - click fence points, s=save, r=reset, q=quit"
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback)

    while True:
        display = frame.copy()

        # Draw points and connecting lines as you click
        for i, pt in enumerate(points):
            cv2.circle(display, pt, 5, (0, 0, 255), -1)
            cv2.putText(display, str(i), (pt[0] + 8, pt[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            if i > 0:
                cv2.line(display, points[i - 1], pt, (0, 0, 255), 2)

        if len(points) > 2:
            cv2.line(display, points[-1], points[0], (0, 0, 255), 1)

        cv2.imshow(window_name, display)
        key = cv2.waitKey(20) & 0xFF

        if key == ord('r'):
            points.clear()
            print("Points reset.")
        elif key == ord('s'):
            if len(points) < 3:
                print("Need at least 3 points to form a polygon. Keep clicking.")
                continue
            config = {"frame_width": w, "frame_height": h, "polygon": points}
            with open(args.output, "w") as f:
                json.dump(config, f, indent=2)
            print(f"Saved {len(points)} points to {args.output}")
            break
        elif key == ord('q'):
            print("Quit without saving.")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()