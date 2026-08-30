import json
import time
import random
from core_contracts import FrameState, Track, BoundingBox, ObjectType

def generate_suspicious_scenario(output_file: str, duration_seconds: int = 30, fps: int = 5):
    """
    Generates mock tracking data simulating:
    1. A person loitering.
    2. A crowd forming.
    3. A person running erratically.
    """
    camera_id = "cam_border_01"
    start_time = time.time()
    frames = []
    
    total_frames = duration_seconds * fps
    
    # 1. Loitering Person (Present from start to end)
    loiter_center = (200.0, 300.0)
    
    # 2. Crowd (3 people appear around 5 seconds in, close together)
    crowd_center = (600.0, 400.0)
    crowd_start_frame = 5 * fps
    
    # 3. Runner (Appears around 15 seconds in, moves very fast across screen)
    runner_start_x = 0.0
    runner_y = 500.0
    runner_speed_per_frame = 25.0  # At 5 FPS, this is 125 pixels/sec (Triggers > 80 threshold)
    runner_start_frame = 15 * fps
    
    for frame_id in range(total_frames):
        current_time = start_time + (frame_id * (1.0 / fps))
        tracks = []
        
        # --- TRACK 1: Loiterer ---
        # Stays mostly still, slight jitter
        j_x, j_y = random.uniform(-5, 5), random.uniform(-5, 5)
        tracks.append(create_track(
            "human_loiterer", 
            loiter_center[0] + j_x, 
            loiter_center[1] + j_y, 
            j_x * fps, j_y * fps
        ))
        
        # --- TRACK 2, 3, 4: Crowd Formation ---
        if frame_id >= crowd_start_frame:
            for i, offset in enumerate([(0,0), (20, 10), (-15, 20)]):
                j_x, j_y = random.uniform(-2, 2), random.uniform(-2, 2)
                tracks.append(create_track(
                    f"human_crowd_{i+1}",
                    crowd_center[0] + offset[0] + j_x,
                    crowd_center[1] + offset[1] + j_y,
                    j_x * fps, j_y * fps
                ))
                
        # --- TRACK 5: Erratic Runner ---
        if frame_id >= runner_start_frame:
            frames_active = frame_id - runner_start_frame
            current_x = runner_start_x + (frames_active * runner_speed_per_frame)
            vel_x = runner_speed_per_frame * fps
            
            # They stay on screen until they pass x=1920
            if current_x < 1920:
                tracks.append(create_track(
                    "human_runner",
                    current_x, runner_y,
                    vel_x, 0.0
                ))
        
        frame_state = FrameState(
            camera_id=camera_id,
            timestamp=current_time,
            frame_id=frame_id,
            tracks=tracks
        )
        frames.append(frame_state.model_dump())
        
    with open(output_file, 'w') as f:
        json.dump(frames, f, indent=2)
        
    print(f"Successfully generated {total_frames} frames of mock data in '{output_file}'")
    print("Scenario includes: Loitering, Crowd Formation, and Erratic Running.")

def create_track(track_id: str, x: float, y: float, vx: float, vy: float) -> dict:
    """Helper to generate a Track object with a fixed size box."""
    box_w, box_h = 50.0, 120.0
    return Track(
        track_id=track_id,
        object_type=ObjectType.HUMAN,
        bbox=BoundingBox(
            x1=x - box_w/2, y1=y - box_h/2,
            x2=x + box_w/2, y2=y + box_h/2
        ),
        confidence=0.98,
        velocity_x=vx,
        velocity_y=vy
    )

if __name__ == "__main__":
    generate_suspicious_scenario("mock_suspicious_data.json")
