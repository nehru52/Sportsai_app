import numpy as np

class RoleClassifier:
    """
    Classifies athlete roles based on their movement history and court positioning.
    """
    def __init__(self):
        self.role_history = {} # track_id -> list of classifications

    def classify(self, track_history):
        """
        track_history: list[dict] with keys 'bbox', 'frame_idx', 'court_zone'
        court_zone values: 'front', 'back', 'mid'
        """
        if not track_history or len(track_history) < 5:
            return "unknown"

        # 1. Vertical velocity check
        # Extract y-coordinates of bbox centers
        y_centers = []
        for h in track_history:
            b = h['bbox']
            y_centers.append((b[1] + b[3]) / 2)
        
        y_centers = np.array(y_centers)
        # Vertical velocity (negative is up)
        v_y = np.diff(y_centers)
        
        # Mean vertical velocity of last 10 frames (upward)
        recent_v_y = v_y[-10:] if len(v_y) >= 10 else v_y
        mean_upward_v = -np.mean(recent_v_y[recent_v_y < 0]) if any(recent_v_y < 0) else 0
        
        # Get court zone distribution
        zones = [h.get('court_zone', 'mid') for h in track_history]
        front_count = zones.count('front')
        back_count = zones.count('back')
        mid_count = zones.count('mid')
        total = len(zones)
        
        # Classification rules
        if mean_upward_v > 5.0 and (zones[-1] in ['front', 'mid']):
            return 'hitter'
            
        if (front_count / total) > 0.70 and mean_upward_v < 2.0:
            return 'setter'
            
        if (back_count / total) > 0.60:
            return 'libero'
            
        return 'blocker'
