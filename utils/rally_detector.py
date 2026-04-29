import numpy as np

class RallyDetector:
    """
    Detects rally state, spikes, and serving team based on athlete movement patterns.
    """
    def __init__(self, fps: float, vy_threshold: float = 5.0):
        self.fps = fps
        self.vy_threshold = vy_threshold
        
        self.rally_active = False
        self.start_frame = 0
        self.spike_count = 0
        self.serving_team = "unknown"
        self.last_movement_frame = 0
        
        self.rallies = [] # List of completed rally summaries

    def process_frame(self, frame_idx: int, track_roles: dict, track_states: dict) -> dict:
        """
        track_states: dict[track_id -> {vy, court_zone, bbox}]
        """
        spike_detected = False
        any_movement = False
        
        # 1. Update movement status
        for tid, state in track_states.items():
            if abs(state.get('vy', 0)) > 1.0:
                any_movement = True
                self.last_movement_frame = frame_idx
                break
        
        # 2. Check for Rally Start
        if not self.rally_active:
            for tid, state in track_states.items():
                role = track_roles.get(tid, 'unknown')
                if role == 'setter' and abs(state.get('vy', 0)) > 2.0:
                    self.rally_active = True
                    self.start_frame = frame_idx
                    self.spike_count = 0
                    # Left half (ratio < 0.5) is home, right half (ratio > 0.5) is away
                    # Note: get_court_zone uses 0.35/0.65 for zones, but here we just need side
                    bx, by, bw, bh = state.get('bbox', [0, 0, 1, 1])
                    cx = (bx + bw/2) # This assumes bbox is [x, y, w, h] or [x1, y1, x2, y2]?
                    # In pose_extractor, bboxes are xyxy. So cx = (x1 + x2) / 2
                    # Let's assume normalized ratio is better.
                    # We'll use a dummy frame_w of 1.0 if not provided in state.
                    self.serving_team = "home" if state.get('court_zone') == 'back' else "away"
                    break
        
        # 3. Check for Spike Event
        if self.rally_active:
            for tid, state in track_states.items():
                role = track_roles.get(tid, 'unknown')
                if role == 'hitter' and state.get('vy', 0) > self.vy_threshold:
                    if state.get('court_zone') in ['front', 'mid']:
                        spike_detected = True
                        self.spike_count += 1
                        break
        
        # 4. Check for Rally End (2 seconds of inactivity)
        if self.rally_active:
            if (frame_idx - self.last_movement_frame) > (self.fps * 2):
                self.rally_active = False
                end_frame = frame_idx
                duration_frames = end_frame - self.start_frame
                self.rallies.append({
                    "start_frame": self.start_frame,
                    "end_frame": end_frame,
                    "duration_seconds": round(duration_frames / self.fps, 2),
                    "spike_count": self.spike_count,
                    "serving_team": self.serving_team
                })

        return {
            "rally_active": self.rally_active,
            "spike_detected": spike_detected,
            "rally_duration_frames": frame_idx - self.start_frame if self.rally_active else 0,
            "serving_team": self.serving_team if self.rally_active else "none"
        }

    def get_rally_summary(self) -> list:
        return self.rallies
