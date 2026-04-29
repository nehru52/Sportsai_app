import json
import os
import glob

class PlayerAggregator:
    """
    Aggregates athlete performance data across multiple video clips and sessions.
    Uses weighted means for biomechanical metrics based on frame counts.
    """
    def __init__(self):
        self.players = {} # track_id (str) -> player_profile

    def ingest_recruiter_json(self, path: str):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            new_players = data.get('players', {})
            for tid, new_data in new_players.items():
                if tid not in self.players:
                    self.players[tid] = new_data.copy()
                    # Ensure counts are explicitly tracked as totals
                    self.players[tid]['total_frames_analysed'] = new_data.get('frames_analysed', 0)
                    self.players[tid]['total_jump_events'] = new_data.get('jump_event_count', 0)
                    self.players[tid]['total_spike_events'] = new_data.get('spike_event_count', 0)
                else:
                    curr = self.players[tid]
                    old_f = curr.get('total_frames_analysed', 1)
                    new_f = new_data.get('frames_analysed', 1)
                    total_f = old_f + new_f
                    
                    # 1. Weighted Mean for Biomechanics
                    old_bio = curr.get('biomechanics', {})
                    new_bio = new_data.get('biomechanics', {})
                    
                    merged_bio = {}
                    all_keys = set(old_bio.keys()) | set(new_bio.keys())
                    
                    for k in all_keys:
                        v_old = old_bio.get(k)
                        v_new = new_bio.get(k)
                        
                        if v_old is not None and v_new is not None:
                            merged_bio[k] = (v_old * old_f + v_new * new_f) / total_f
                        elif v_old is not None:
                            merged_bio[k] = v_old
                        else:
                            merged_bio[k] = v_new
                            
                    curr['biomechanics'] = merged_bio
                    
                    # 2. Weighted Mean for Score
                    old_score = curr.get('fivb_score', 50)
                    new_score = new_data.get('fivb_score', 50)
                    curr['fivb_score'] = (old_score * old_f + new_score * new_f) / total_f
                    
                    # 3. Accumulate Totals
                    curr['total_frames_analysed'] = total_f
                    curr['total_jump_events'] += new_data.get('jump_event_count', 0)
                    curr['total_spike_events'] += new_data.get('spike_event_count', 0)
                    
                    # 4. Merge Flags and Notes
                    curr['recruiter_flags'] = list(set(curr.get('recruiter_flags', [])) | set(new_data.get('recruiter_flags', [])))
                    curr['scoring_notes'] = list(set(curr.get('scoring_notes', [])) | set(new_data.get('scoring_notes', [])))
                    
        except Exception as e:
            print(f"Error ingesting {path}: {e}")

    def ingest_all(self, directory: str = 'data/recruiter_outputs/'):
        files = glob.glob(os.path.join(directory, '*_recruiter.json'))
        for f in files:
            self.ingest_recruiter_json(f)
        print(f"Ingested {len(files)} files, {len(self.players)} unique players found")

    def get_player_profile(self, track_id: str) -> dict:
        return self.players.get(str(track_id), {})

    def rank_players(self, role: str = None, metric: str = 'fivb_score', top_n: int = 10) -> list:
        ranked = []
        for tid, p in self.players.items():
            if role and p.get('role') != role:
                continue
            
            # Extract metric value (either from top level or nested bio)
            val = p.get(metric)
            if val is None:
                val = p.get('biomechanics', {}).get(metric, 0)
            
            ranked.append({
                "track_id": tid,
                "role": p.get('role'),
                "metric_value": round(float(val), 2) if val is not None else 0,
                "total_frames_analysed": p.get('total_frames_analysed', 0),
                "fivb_score": round(p.get('fivb_score', 0), 1),
                "recruiter_flags": p.get('recruiter_flags', [])
            })
            
        ranked.sort(key=lambda x: x['metric_value'], reverse=True)
        return ranked[:top_n]
