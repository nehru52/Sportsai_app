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
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)

class RecruiterOutputBuilder:
    """
    Builds the final recruiter-focused JSON output for analyzed athletes.
    """
    def __init__(self, video_id: str):
        self.video_id = video_id
        self.players = {} # track_id (str) -> player_data

    def update_player(self, track_id: int, role: str, biomechanics: dict, event_flags: dict = {}):
        tid_str = str(track_id)
        if tid_str not in self.players:
            self.players[tid_str] = {
                "role": role,
                "frames_analysed": 0,
                "biomechanics": {},
                "fivb_score": None,
                "recruiter_flags": [],
                "scoring_notes": [],
                "jump_event_count": 0,
                "spike_event_count": 0,
                "normalised_scoring": False
            }
        
        player = self.players[tid_str]
        player["frames_analysed"] += 1
        n = player["frames_analysed"]
        
        # Update event counters
        if event_flags.get('is_jumping'):
            player['jump_event_count'] += 1
        if event_flags.get('is_spiking'):
            player['spike_event_count'] += 1
            
        # Update running mean for biomechanics
        for k, v in biomechanics.items():
            if v is None: continue
            if k not in player["biomechanics"]:
                player["biomechanics"][k] = v
            else:
                old_mean = player["biomechanics"][k]
                player["biomechanics"][k] = old_mean + (v - old_mean) / n
        
        # Role might change as classifier gathers more data
        player["role"] = role

    def compute_fivb_scores(self):
        for tid, player in self.players.items():
            score = 50
            bio = player["biomechanics"]
            notes = []
            
            # Spike mechanics
            elbow_flexion = bio.get("arm_cock_angle", 0)
            if player['spike_event_count'] >= 3:
                if 150 <= elbow_flexion <= 180:
                    score += 15
            else:
                notes.append("insufficient spike events for elbow scoring")
            
            # Jump height (Fix 1: Normalised scoring)
            jump_h_norm = bio.get("jump_height_normalised")
            jump_h_px = bio.get("avg_jump_height_px", 0)
            
            if player['jump_event_count'] >= 3:
                if jump_h_norm is not None:
                    player['normalised_scoring'] = True
                    if jump_h_norm > 0.25: score += 10
                    if jump_h_norm > 0.40: score += 5
                else:
                    player['normalised_scoring'] = False
                    if jump_h_px > 70: score += 10
                    if jump_h_px > 100: score += 5
            else:
                notes.append("insufficient jump events for height scoring")
                
            # Velocity / Dynamicism
            if bio.get("arm_swing_velocity") == "high": 
                score += 10
                
            # Role importance
            if player["role"] in ["hitter", "setter"]:
                score += 5
                
            # Confidence penalty
            if player["frames_analysed"] < 30:
                score -= 10
                
            player["fivb_score"] = int(np.clip(score, 0, 100))
            player["scoring_notes"] = notes
            
            # Generate recruiter flags (Fix 3: Min event gate)
            flags = []
            if player['spike_event_count'] >= 3:
                if elbow_flexion > 165: flags.append("elite_arm_swing")
                if elbow_flexion < 140 and elbow_flexion > 0: flags.append("weak_approach_angle")
            elif player["role"] == 'hitter':
                flags.append("limited_spike_data")
                
            if player['jump_event_count'] >= 3:
                is_high = (jump_h_norm > 0.40) if jump_h_norm is not None else (jump_h_px > 100)
                if is_high: flags.append("high_jumper")
            else:
                flags.append("limited_jump_data")
                
            if player["frames_analysed"] < 30: flags.append("insufficient_data")
            player["recruiter_flags"] = flags

    def save(self, output_dir: str = "data/recruiter_outputs/"):
        self.compute_fivb_scores()
        os.makedirs(output_dir, exist_ok=True)
        
        # Convert all numpy types to Python types recursively
        def convert_numpy(obj):
            if isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            elif isinstance(obj, (np.integer, np.int32, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float32, np.float64)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.bool_):
                return bool(obj)
            else:
                return obj
        
        output_data = {
            "video_id": self.video_id,
            "players": convert_numpy(self.players)
        }
        
        path = os.path.join(output_dir, f"{self.video_id}_recruiter.json")
        with open(path, "w") as f:
            json.dump(output_data, f, indent=2)
        
        print(f"Recruiter output saved: {path}")
