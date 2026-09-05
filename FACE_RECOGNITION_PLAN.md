# 🛡️ Face Recognition Integration Plan for IBVAP
**Target:** Add full-accuracy face detection and recognition to the existing pipeline to filter out authorized personnel (preventing false alarms for loitering/patrolling), without sacrificing real-time 30+ FPS edge performance.

---

## 1. AI Models Selected for Full Accuracy
*   **Model:** **InsightFace (ArcFace)**
*   **Why:** Standard `haarcascades` or `face_recognition` libraries struggle with side profiles, poor lighting, and varied angles. InsightFace provides robust face detection (RetinaFace/SCRFD) and highly accurate 512-dimensional facial embeddings, natively optimized for GPU execution.

## 2. The Asynchronous Architecture (Zero FPS Drop)
Face recognition is computationally heavy. Running it inline on the main video thread for every detected human will crash the system FPS. We will use the **Asynchronous Decoupled Worker** pattern (similar to the existing ANPR approach).

### Step A: Identity Cache & Bounded Queue
*   Create a background thread (`FaceRecognitionWorker`).
*   Create a task queue: `Queue(maxsize=50)`.
*   Maintain a dictionary `identity_cache = {}` that maps DeepSORT `track_id`s to known identities (e.g., `{'trk-5': 'Authorized_Staff'}`).

### Step B: Main Thread Extraction (Zero Latency)
In the main `run_live.py` loop, after YOLO detects humans and DeepSORT assigns a `track_id`:
1.  Check if the `track_id` is already in the `identity_cache`.
2.  If not, crop the human's bounding box (`frame[y1:y2, x1:x2]`) with a 15% padding margin to ensure the head is fully visible.
3.  Push this crop and the `track_id` to the background queue.
4.  **The Persistent Advantage:** Because DeepSORT maintains the `track_id` over time, we only need to successfully recognize the face *once*. The system will remember the identity of that track for its entire lifespan.

### Step C: Background Worker Processing
The background thread continuously pulls crops from the queue:
1.  Runs InsightFace to detect a face within the crop.
2.  Extracts the 512D face embedding vector.
3.  Compares the vector against the local database of known personnel using **Cosine Similarity**.
4.  If the similarity exceeds the strict threshold (e.g., `> 0.60`), it updates the cache: `identity_cache['trk-5'] = 'Authorized_Staff'`.
5.  If a face is found but doesn't match, it logs it as unknown: `identity_cache['trk-5'] = 'Unknown_Threat'`.

## 3. Override Logic in Suspicious Activity Detector
In `loitering_detector.py`, the system currently processes every tracked human for loitering, erratic movement, and crowd formation. We will inject a bypass rule for authorized personnel:

```python
for track in active_human_tracks:
    # Inject the identity from the cache (default to Unknown)
    identity = track.attributes.get("identity", "Unknown_Threat")
    
    # 🚨 The Bypass Rule 🚨
    if identity == "Authorized_Staff":
        # Skip this person entirely. Guards/Staff are allowed to loiter or patrol.
        continue 
    
    # ... proceed with normal loitering, fence breach & threat logic for Unknowns ...
```

## 4. Database Strategy for Lightning-Fast Matching
*   Instead of querying a traditional SQL database for image matching (which is slow), pre-compute the 512D embeddings of known personnel at system boot.
*   Load them into **FAISS (Facebook AI Similarity Search)** or a vectorized NumPy matrix.
*   FAISS allows the background worker to compare a live face against thousands of known faces in less than 2 milliseconds ($O(1)$ time complexity), ensuring the background queue never backs up.

## Summary of Impact
1.  **Guaranteed 30 FPS:** The main video loop never waits for the neural network to finish face processing.
2.  **High Accuracy at Distance:** The system continuously samples unknown tracks. If someone approaches from a distance, the background thread keeps trying until they are close enough for a high-confidence match, then permanently tags their ID.
3.  **Eliminates False Positives:** Security guards patrolling the border will naturally trigger loitering and virtual fence alarms. This architecture filters them out automatically at the behavioral logic layer, ensuring the Alarm Manager only scores actual threats.
