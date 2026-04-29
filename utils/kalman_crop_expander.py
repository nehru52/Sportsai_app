import cv2
import numpy as np

class AthleteTrack:
    """
    Kalman filter wrapper for tracking athlete bounding boxes.
    State: [cx, cy, w, h, vx, vy, vw, vh]
    Measurement: [cx, cy, w, h]
    """
    def __init__(self, bbox, vy_threshold=5.0):
        # 8 state variables, 4 measurements
        self.kf = cv2.KalmanFilter(8, 4)
        
        # Transition matrix (F)
        # cx = cx + vx, cy = cy + vy, etc.
        self.kf.transitionMatrix = np.eye(8, dtype=np.float32)
        for i in range(4):
            self.kf.transitionMatrix[i, i+4] = 1.0
            
        # Measurement matrix (H)
        self.kf.measurementMatrix = np.eye(4, 8, dtype=np.float32)
        
        # Process noise covariance (Q)
        self.kf.processNoiseCov = np.eye(8, dtype=np.float32) * 1e-1
        self.kf.processNoiseCov[:4, :4] *= 0.1 # Position noise lower
        
        # Measurement noise covariance (R)
        self.kf.measurementNoiseCov = np.eye(4, dtype=np.float32) * 1e-1
        
        # Initial state
        cx, cy, w, h = self._bbox_to_cwh(bbox)
        self.kf.statePost = np.array([cx, cy, w, h, 0, 0, 0, 0], dtype=np.float32).reshape(-1, 1)
        self.kf.errorCovPost = np.eye(8, dtype=np.float32)
        
        self.vy_threshold = vy_threshold
        self.last_bbox = bbox
        self.frames_missing = 0

    def _bbox_to_cwh(self, bbox):
        x1, y1, x2, y2 = bbox
        w, h = x2 - x1, y2 - y1
        cx, cy = x1 + w/2, y1 + h/2
        return cx, cy, w, h

    def _cwh_to_bbox(self, cx, cy, w, h):
        x1, y1 = cx - w/2, cy - h/2
        x2, y2 = x1 + w, y1 + h
        return [x1, y1, x2, y2]

    def predict(self):
        prediction = self.kf.predict()
        cx, cy, w, h = prediction[:4, 0]
        return self._cwh_to_bbox(cx, cy, w, h)

    def update(self, bbox):
        cx, cy, w, h = self._bbox_to_cwh(bbox)
        measurement = np.array([cx, cy, w, h], dtype=np.float32).reshape(-1, 1)
        self.kf.correct(measurement)
        self.last_bbox = bbox
        self.frames_missing = 0

    @property
    def is_jumping(self):
        # vertical velocity is at index 5
        return abs(self.kf.statePost[5, 0]) > self.vy_threshold

class KalmanCropExpander:
    """
    Manages multiple athlete tracks and provides expanded crop regions.
    """
    def __init__(self, base_pad=0.30, jump_pad=0.55, vy_jump_threshold=5.0, max_frames_missing=5, frame_w=1920, frame_h=1080):
        self.tracks = {} # track_id -> AthleteTrack
        self.base_pad = base_pad
        self.jump_pad = jump_pad
        self.vy_threshold = vy_jump_threshold
        self.max_frames_missing = max_frames_missing
        self.frame_w = frame_w
        self.frame_h = frame_h

    def process_frame(self, detections):
        """
        detections: dict[track_id -> [x1, y1, x2, y2]]
        Returns: dict[track_id -> (x1, y1, x2, y2)]
        """
        results = {}
        
        # 1. Update existing tracks and create new ones
        for tid, bbox in detections.items():
            if tid not in self.tracks:
                self.tracks[tid] = AthleteTrack(bbox, self.vy_threshold)
            
            # Predict then update
            predicted_bbox = self.tracks[tid].predict()
            self.tracks[tid].update(bbox)
            
            # Use union of predicted and detected for crop
            union_bbox = [
                min(bbox[0], predicted_bbox[0]),
                min(bbox[1], predicted_bbox[1]),
                max(bbox[2], predicted_bbox[2]),
                max(bbox[3], predicted_bbox[3])
            ]
            
            # Expand based on jumping state
            pad = self.jump_pad if self.tracks[tid].is_jumping else self.base_pad
            w, h = union_bbox[2] - union_bbox[0], union_bbox[3] - union_bbox[1]
            
            crop = [
                max(0, union_bbox[0] - w * pad),
                max(0, union_bbox[1] - h * pad),
                min(self.frame_w, union_bbox[2] + w * pad),
                min(self.frame_h, union_bbox[3] + h * pad)
            ]
            results[tid] = tuple(map(int, crop))

        # 2. Handle missing tracks
        dead_tracks = []
        for tid, track in self.tracks.items():
            if tid not in detections:
                track.frames_missing += 1
                if track.frames_missing > self.max_frames_missing:
                    dead_tracks.append(tid)
                else:
                    # Still predict and provide a crop
                    predicted_bbox = track.predict()
                    w, h = predicted_bbox[2] - predicted_bbox[0], predicted_bbox[3] - predicted_bbox[1]
                    pad = self.jump_pad if track.is_jumping else self.base_pad
                    crop = [
                        max(0, predicted_bbox[0] - w * pad),
                        max(0, predicted_bbox[1] - h * pad),
                        min(self.frame_w, predicted_bbox[2] + w * pad),
                        min(self.frame_h, predicted_bbox[3] + h * pad)
                    ]
                    results[tid] = tuple(map(int, crop))
        
        for tid in dead_tracks:
            del self.tracks[tid]
            
        return results
