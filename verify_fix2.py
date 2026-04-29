import sys
import os
import json

# Add root to path for imports
sys.path.append(os.getcwd())

from utils.recruiter_output import RecruiterOutputBuilder

def verify_schema():
    print("Verifying Recruiter Output JSON Schema...")
    builder = RecruiterOutputBuilder("test_video")
    
    # Simulate a player with:
    # 45 frames analysed
    # jump_event_count = 5
    # spike_event_count = 4
    # avg_spike_elbow_flexion = 168
    # jump_height_normalised = 0.42
    # role = 'hitter'
    
    bio = {
        'arm_cock_angle': 168,
        'jump_height_normalised': 0.42,
        'avg_jump_height_px': 120,
        'avg_standing_height_px': 300
    }
    
    # Update player over 45 frames
    for i in range(45):
        # Trigger events on some frames
        e_flags = {
            'is_jumping': i < 5,
            'is_spiking': i < 4
        }
        builder.update_player(101, 'hitter', bio, e_flags)
    
    # Compute scores and get dict
    builder.compute_fivb_scores()
    player_data = builder.players["101"]
    
    print(f"Player Data: {json.dumps(player_data, indent=2)}")
    
    # Checks
    assert "fivb_score" in player_data
    assert "recruiter_flags" in player_data
    assert "scoring_notes" in player_data
    assert "normalised_scoring" in player_data
    assert player_data["jump_event_count"] == 5
    assert player_data["spike_event_count"] == 4
    assert player_data["normalised_scoring"] is True
    assert "elite_arm_swing" in player_data["recruiter_flags"]
    assert "high_jumper" in player_data["recruiter_flags"]
    
    print("Schema Verification PASSED!")

if __name__ == "__main__":
    verify_schema()
