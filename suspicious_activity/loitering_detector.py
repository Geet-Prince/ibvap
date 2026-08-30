import json
import math
import os
import time
import uuid
from typing import List, Optional, Set, FrozenSet

from core_contracts import FrameState, Track, Event, EventSeverity, ObjectType

class SuspiciousActivityDetector:
    def __init__(self, 
                 time_threshold=10.0, 
                 distance_threshold=200.0, 
                 cleanup_threshold=5.0,
                 crowd_distance_threshold=150.0,
                 crowd_min_people=3,
                 speed_threshold=80.0):
        """
        :param time_threshold: Minimum time (in seconds) an object must remain to be considered loitering.
        :param distance_threshold: Maximum distance (in pixels) an object can move from its starting point for loitering.
        :param cleanup_threshold: Time (in seconds) to wait before dropping a track.
        :param crowd_distance_threshold: Maximum distance (in pixels) between people to be considered a crowd.
        :param crowd_min_people: Minimum number of people to trigger a crowd event.
        :param speed_threshold: Speed (pixels/sec approximation) above which movement is considered erratic/running.
        """
        self.time_threshold = time_threshold
        self.distance_threshold = distance_threshold
        self.cleanup_threshold = cleanup_threshold
        
        # Crowd and Erratic thresholds
        self.crowd_distance_threshold = crowd_distance_threshold
        self.crowd_min_people = crowd_min_people
        self.speed_threshold = speed_threshold
        
        self.track_history = {}
        self.alerted_crowds: Set[FrozenSet[str]] = set()
    
    def get_center(self, bbox) -> tuple:
        """Calculate the center coordinates of a bounding box."""
        return ((bbox.x1 + bbox.x2) / 2, (bbox.y1 + bbox.y2) / 2)

    def calculate_distance(self, p1, p2) -> float:
        """Calculate the Euclidean distance between two points."""
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

    def process_frame(self, frame_state: FrameState) -> List[Event]:
        """Process a FrameState and return any generated Events."""
        events_generated = []
        timestamp = frame_state.timestamp
        camera_id = frame_state.camera_id
        
        active_human_tracks = [t for t in frame_state.tracks if t.object_type == ObjectType.HUMAN]

        # 1. INDIVIDUAL HEURISTICS (Loitering & Erratic Movement)
        for track in active_human_tracks:
            track_id = track.track_id
            center_pos = self.get_center(track.bbox)
            
            # Calculate speed based on velocity provided by the tracker
            speed = math.sqrt(track.velocity_x**2 + track.velocity_y**2)

            if track_id not in self.track_history:
                # Initialize new track
                self.track_history[track_id] = {
                    'first_seen_timestamp': timestamp,
                    'initial_position': center_pos,
                    'last_seen_timestamp': timestamp,
                    'loitering_alerted': False,
                    'erratic_alerted': False
                }
            else:
                # Update existing track
                self.track_history[track_id]['last_seen_timestamp'] = timestamp
                history = self.track_history[track_id]
                
                time_elapsed = timestamp - history['first_seen_timestamp']
                distance_moved = self.calculate_distance(history['initial_position'], center_pos)

                # --- Loitering Condition ---
                if time_elapsed >= self.time_threshold and distance_moved <= self.distance_threshold:
                    if not history['loitering_alerted']:
                        events_generated.append(self._create_event(
                            camera_id, [track_id], timestamp, EventSeverity.MEDIUM, 
                            "loitering", {"duration_seconds": round(time_elapsed, 2)}
                        ))
                        history['loitering_alerted'] = True
                
                # --- Erratic Movement Condition ---
                if speed > self.speed_threshold:
                    if not history['erratic_alerted']:
                        events_generated.append(self._create_event(
                            camera_id, [track_id], timestamp, EventSeverity.HIGH, 
                            "erratic_movement", {"speed": round(speed, 2)}
                        ))
                        history['erratic_alerted'] = True

        # 2. GROUP HEURISTICS (Crowd Formation)
        if len(active_human_tracks) >= self.crowd_min_people:
            clusters = self._find_clusters(active_human_tracks)
            for cluster in clusters:
                if len(cluster) >= self.crowd_min_people:
                    cluster_ids = frozenset([t.track_id for t in cluster])
                    # Alert if we haven't alerted for this exact group before
                    if cluster_ids not in self.alerted_crowds:
                        self.alerted_crowds.add(cluster_ids)
                        events_generated.append(self._create_event(
                            camera_id, list(cluster_ids), timestamp, EventSeverity.HIGH, 
                            "crowd_formation", {"people_count": len(cluster_ids)}
                        ))

        # 3. CLEANUP
        self._cleanup_stale_tracks(timestamp)
            
        return events_generated

    def _find_clusters(self, tracks: List[Track]) -> List[List[Track]]:
        """Simple distance-based clustering for crowd detection."""
        clusters = []
        for track in tracks:
            added = False
            for cluster in clusters:
                # If close to any member of the cluster, join the cluster
                for member in cluster:
                    dist = self.calculate_distance(self.get_center(track.bbox), self.get_center(member.bbox))
                    if dist <= self.crowd_distance_threshold:
                        cluster.append(track)
                        added = True
                        break
                if added:
                    break
            if not added:
                clusters.append([track])
        return clusters

    def _cleanup_stale_tracks(self, current_timestamp: float):
        """Remove tracks that haven't been seen recently."""
        lost_tracks = []
        for tid, history in self.track_history.items():
            if current_timestamp - history['last_seen_timestamp'] > self.cleanup_threshold:
                lost_tracks.append(tid)
        for tid in lost_tracks:
            del self.track_history[tid]

    def _create_event(self, camera_id: str, track_ids: List[str], timestamp: float, 
                      severity: EventSeverity, subtype: str, extra_metadata: dict) -> Event:
        """Helper to standardize event creation."""
        metadata = {"subtype": subtype}
        metadata.update(extra_metadata)
        return Event(
            event_id=str(uuid.uuid4()),
            event_type="SUSPICIOUS_ACTIVITY",
            timestamp=timestamp,
            camera_id=camera_id,
            track_ids=track_ids,
            severity=severity,
            metadata=metadata
        )

def main():
    data_path = 'mock_suspicious_data.json'
    
    if not os.path.exists(data_path):
        print(f"Error: Could not find {data_path}")
        return

    print(f"Loading data from {data_path}...")
    with open(data_path, 'r') as f:
        raw_frames = json.load(f)

    frames = [FrameState(**frame_dict) for frame_dict in raw_frames]

    # Initialize the detector
    detector = SuspiciousActivityDetector()
    
    print(f"Starting Suspicious Activity Detection...\n{'-'*60}")
          
    total_events = 0
    for frame in frames:
        events = detector.process_frame(frame)
        for event in events:
            total_events += 1
            print(f"[{event.metadata['subtype'].upper()}] Event Generated:\n{event.model_dump_json(indent=2)}\n")
        
    print(f"{'-'*60}\nProcessing complete. Generated {total_events} events.")


if __name__ == "__main__":
    main()
