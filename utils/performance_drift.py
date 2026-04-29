import numpy as np

class PerformanceDriftTracker:
    """
    Tracks biomechanical performance over time to identify trends and fatigue.
    """
    def __init__(self, set_duration_frames: int = 3000):
        self.set_duration_frames = set_duration_frames
        self.sets = {} # track_id -> {set_idx -> {metric -> [values]}}

    def update(self, track_id: int, frame_idx: int, metrics: dict):
        if track_id not in self.sets:
            self.sets[track_id] = {}
            
        set_idx = frame_idx // self.set_duration_frames
        if set_idx not in self.sets[track_id]:
            self.sets[track_id][set_idx] = {
                'jump_height_normalised': [],
                'arm_cock_angle': [],
                'vy_peak': []
            }
            
        set_data = self.sets[track_id][set_idx]
        
        # We only store valid (non-None) metrics
        if metrics.get('jump_height_normalised') is not None:
            set_data['jump_height_normalised'].append(metrics['jump_height_normalised'])
            
        if metrics.get('arm_cock_angle') is not None:
            set_data['arm_cock_angle'].append(metrics['arm_cock_angle'])
            
        if metrics.get('avg_jump_height_px') is not None:
            # We'll use this as a proxy if normalized is missing or for vy_peak logic
            # The prompt asks for vy_peak specifically. 
            # vy_peak should be the max vy seen. vy itself isn't in metrics usually.
            # But we can assume it's passed or we use a proxy.
            # Let's check if 'vy' is in metrics.
            pass
        
        if 'vy' in metrics:
            set_data['vy_peak'].append(abs(metrics['vy']))

    def get_drift_report(self, track_id: int) -> dict:
        if track_id not in self.sets:
            return {"sets_analysed": 0, "error": "No data for track_id"}
            
        player_sets = self.sets[track_id]
        sorted_set_indices = sorted(player_sets.keys())
        
        per_set_data = []
        for idx in sorted_set_indices:
            data = player_sets[idx]
            per_set_data.append({
                "set_idx": idx,
                "jump_height_mean": np.mean(data['jump_height_normalised']) if data['jump_height_normalised'] else 0,
                "arm_cock_mean": np.mean(data['arm_cock_angle']) if data['arm_cock_angle'] else 0,
                "vy_peak": np.max(data['vy_peak']) if data['vy_peak'] else 0
            })
            
        if not per_set_data:
            return {"sets_analysed": 0}

        # Trend analysis (Compare first vs last)
        first = per_set_data[0]
        last = per_set_data[-1]
        
        def calc_trend(f_val, l_val):
            if f_val == 0: return "stable"
            diff_ratio = (l_val - f_val) / f_val
            if diff_ratio > 0.05: return "improving"
            if diff_ratio < -0.05: return "declining"
            return "stable"

        jump_trend = calc_trend(first["jump_height_mean"], last["jump_height_mean"])
        arm_trend = calc_trend(first["arm_cock_mean"], last["arm_cock_mean"])
        
        # Fatigue flag: jump height drops > 15%
        fatigue_flag = False
        if first["jump_height_mean"] > 0:
            drop_ratio = (first["jump_height_mean"] - last["jump_height_mean"]) / first["jump_height_mean"]
            if drop_ratio > 0.15:
                fatigue_flag = True

        return {
            "sets_analysed": len(per_set_data),
            "jump_trend": jump_trend,
            "arm_trend": arm_trend,
            "fatigue_flag": fatigue_flag,
            "per_set_data": per_set_data
        }
