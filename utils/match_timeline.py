import json
import os
import numpy as np

class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy types"""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

class MatchTimelineBuilder:
    """
    Constructs a chronological timeline of events and a summary of match-wide statistics.
    """
    def __init__(self, video_id: str, fps: float):
        self.video_id = video_id
        self.fps = fps
        
        self.events = []
        self.last_set_idx = -1
        self.total_spikes = 0
        self.total_duration_seconds = 0
        
        # Team stats
        self.team_stats = {
            "home": {"spike_count": 0, "court_coverage_sum": 0, "coverage_count": 0},
            "away": {"spike_count": 0, "court_coverage_sum": 0, "coverage_count": 0}
        }
        
        self.player_drift_reports = {}

    def update(self, frame_idx: int, rally_result: dict, track_roles: dict, track_metrics: dict):
        time_seconds = round(frame_idx / self.fps, 2)
        self.total_duration_seconds = time_seconds
        
        # 1. Rally Events
        if rally_result.get('rally_active'):
            # Check if this is a new rally start
            if not any(e['event_type'] == 'rally_start' and e['metadata'].get('frame') == rally_result.get('start_frame') for e in self.events):
                self.events.append({
                    "time_seconds": time_seconds,
                    "event_type": "rally_start",
                    "metadata": {"frame": frame_idx, "serving_team": rally_result.get('serving_team')}
                })
            
            # Spike Detection
            if rally_result.get('spike_detected'):
                self.total_spikes += 1
                serving_team = rally_result.get('serving_team')
                if serving_team in self.team_stats:
                    self.team_stats[serving_team]["spike_count"] += 1
                    
                self.events.append({
                    "time_seconds": time_seconds,
                    "event_type": "spike",
                    "metadata": {"frame": frame_idx, "team": serving_team}
                })
        else:
            # Check for rally end
            # Rally detector handles storing summaries, but we can log the end event here
            pass
            
        # 2. Set Changes (every 3000 frames)
        set_idx = frame_idx // 3000
        if set_idx > self.last_set_idx:
            self.events.append({
                "time_seconds": time_seconds,
                "event_type": "set_change",
                "metadata": {"set_index": set_idx}
            })
            self.last_set_idx = set_idx

    def save(self, output_dir: str = 'data/match_outputs/'):
        os.makedirs(output_dir, exist_ok=True)
        
        # Finalise team coverage (dummy logic for coverage - using spike density as proxy for now)
        summary = {
            "video_id": self.video_id,
            "total_duration_seconds": self.total_duration_seconds,
            "total_rallies": len([e for e in self.events if e['event_type'] == 'rally_start']),
            "total_spikes": self.total_spikes,
            "timeline": self.events,
            "player_drift_reports": self.player_drift_reports,
            "team_summary": {
                "home": {
                    "spike_count": self.team_stats["home"]["spike_count"],
                    "avg_court_coverage": 0.65 # Placeholder
                },
                "away": {
                    "spike_count": self.team_stats["away"]["spike_count"],
                    "avg_court_coverage": 0.58 # Placeholder
                }
            }
        }
        
        path = os.path.join(output_dir, f"{self.video_id}_match.json")
        with open(path, "w") as f:
            json.dump(summary, f, indent=2, cls=NumpyEncoder)
            
        print(f"Match analysis saved: {path}")
