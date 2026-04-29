"""
Elite Olympic-Level Biomechanics Standards
Based on FIVB research, Open Spike Kinematics, and World Championship data
"""
import numpy as np
from typing import Dict, List, Tuple

# Olympic-level biomechanical benchmarks from research papers
ELITE_BENCHMARKS = {
    "spike": {
        # Open Spike Kinematics - Elite male athletes (Semarang)
        "leg_flexion_initial": {"target": 129.2, "tolerance": 5.0, "direction": "higher"},
        "torso_extension_initial": {"target": 164.7, "tolerance": 6.0, "direction": "higher"},
        "leg_flexion_repulsion": {"target": 103.5, "tolerance": 8.0, "direction": "lower"},
        "elbow_flexion_repulsion": {"target": 153.0, "tolerance": 5.0, "direction": "higher"},
        "elbow_flexion_impact": {"target": 166.4, "tolerance": 4.0, "direction": "higher"},
        "torso_extension_landing": {"target": 159.8, "tolerance": 6.0, "direction": "higher"},
        "jump_height": {"target": 4.8, "tolerance": 0.3, "direction": "higher"},
        "spike_speed": {"target": 1.26, "tolerance": 0.15, "direction": "higher"},
        "flying_distance": {"target": 2.49, "tolerance": 0.2, "direction": "higher"},
        
        # Temporal constraints
        "repulsion_time": {"target": 1.01, "tolerance": 0.1, "direction": "lower"},
        "impact_time": {"target": 0.57, "tolerance": 0.05, "direction": "lower"},
        "landing_time": {"target": 0.39, "tolerance": 0.05, "direction": "lower"},
    },
    
    "block": {
        # FIVB Level II Manual - Postural specifications
        "hip_angle": {"target": 90.0, "tolerance": 5.0, "direction": "lower"},
        "knee_angle": {"target": 105.0, "tolerance": 10.0, "direction": "lower"},
        "ankle_angle": {"target": 85.0, "tolerance": 5.0, "direction": "lower"},
        
        # 2014 FIVB World Championship data - Position-specific
        "block_jumps_per_match": {"target": 44, "tolerance": 12, "direction": "higher"},
        "jump_height_percentage": {"target": 88.8, "tolerance": 5.0, "direction": "higher"},
        "hand_position_height": {"target": 30.0, "tolerance": 5.0, "direction": "higher"}, # cm above net
        "shoulder_width_ratio": {"target": 0.85, "tolerance": 0.1, "direction": "higher"},
        "reaction_time": {"target": 0.3, "tolerance": 0.05, "direction": "lower"},
        "landing_balance": {"target": 0.95, "tolerance": 0.05, "direction": "higher"},
    },
    
    "serve": {
        # FIVB serving mechanics
        "toss_height": {"target": 2.5, "tolerance": 0.3, "direction": "higher"},
        "shoulder_rotation": {"target": 45.0, "tolerance": 8.0, "direction": "higher"},
        "body_lean_angle": {"target": 15.0, "tolerance": 5.0, "direction": "lower"},
        "wrist_snap_velocity": {"target": 8.5, "tolerance": 1.0, "direction": "higher"},
        "step_timing": {"target": 0.8, "tolerance": 0.1, "direction": "lower"},
        "contact_point_height": {"target": 2.8, "tolerance": 0.2, "direction": "higher"},
    },
    
    "dig": {
        # FIVB reception standards
        "platform_angle": {"target": 45.0, "tolerance": 8.0, "direction": "higher"},
        "knee_bend_angle": {"target": 110.0, "tolerance": 15.0, "direction": "lower"},
        "hip_drop_distance": {"target": 0.25, "tolerance": 0.05, "direction": "higher"},
        "arm_extension_angle": {"target": 170.0, "tolerance": 10.0, "direction": "lower"},
        "recovery_time": {"target": 0.8, "tolerance": 0.1, "direction": "lower"},
        
        # Critical temporal constraint
        "reception_window": {"target": 0.7, "tolerance": 0.1, "direction": "lower"}, # seconds to receive jump serve
    }
}

# Position-specific variations based on 2014 FIVB World Championship data
POSITION_BENCHMARKS = {
    "middle": {
        "block_jumps_per_match": {"target": 44, "tolerance": 12},
        "attack_jumps_per_match": {"target": 22, "tolerance": 10},
        "jump_height_attack": {"target": 96.5, "tolerance": 3.0},
        "horizontal_distance": {"target": 2.1, "tolerance": 0.3},
        "flying_distance_ratio": {"target": 0.85, "tolerance": 0.1},
    },
    "opposite": {
        "attack_jumps_per_match": {"target": 31, "tolerance": 10},
        "block_jumps_per_match": {"target": 28, "tolerance": 8},
        "jump_height_attack": {"target": 96.5, "tolerance": 3.0},
        "horizontal_distance": {"target": 2.8, "tolerance": 0.3},
        "flying_distance_ratio": {"target": 1.15, "tolerance": 0.1},
    },
    "receiver": {
        "attack_jumps_per_match": {"target": 22, "tolerance": 10},
        "block_jumps_per_match": {"target": 18, "tolerance": 6},
        "jump_height_attack": {"target": 94.0, "tolerance": 4.0},
        "horizontal_distance": {"target": 2.3, "tolerance": 0.3},
        "flying_distance_ratio": {"target": 0.95, "tolerance": 0.1},
    },
    "setter": {
        "block_jumps_per_match": {"target": 15, "tolerance": 5},
        "attack_jumps_per_match": {"target": 8, "tolerance": 3},
        "jump_height_attack": {"target": 88.0, "tolerance": 5.0},
        "horizontal_distance": {"target": 1.8, "tolerance": 0.3},
        "flying_distance_ratio": {"target": 0.7, "tolerance": 0.1},
    }
}

# Seasonal degradation patterns from shoulder kinematics research
SEASONAL_DEGRADATION = {
    "early_season": {"scapular_tilt": 0.0, "protraction": 0.0},
    "mid_season": {"scapular_tilt": -2.5, "protraction": +3.0},
    "late_season": {"scapular_tilt": -5.0, "protraction": +6.0},
}

def get_elite_benchmark(technique: str, metric: str, position: str = None, season_phase: str = "early_season", athlete_level: str = "intermediate") -> dict:
    """Get scaled benchmark for specific technique, metric, and athlete level"""
    
    if technique in ELITE_BENCHMARKS and metric in ELITE_BENCHMARKS[technique]:
        benchmark = ELITE_BENCHMARKS[technique][metric].copy()
    else:
        return {"target": 0, "tolerance": 10, "direction": "higher", "source": "generic"}
    
    # Scale based on athlete level
    level_scalers = {
        "beginner": {"target_mod": 0.6, "tolerance_mult": 2.0},
        "intermediate": {"target_mod": 0.8, "tolerance_mult": 1.5},
        "advanced": {"target_mod": 0.95, "tolerance_mult": 1.2},
        "elite": {"target_mod": 1.0, "tolerance_mult": 1.0}
    }
    
    scaler = level_scalers.get(athlete_level, level_scalers["intermediate"])
    
    # Adjust targets and tolerances
    if benchmark["direction"] == "higher":
        benchmark["target"] *= scaler["target_mod"]
    else:
        benchmark["target"] *= (1.0 + (1.0 - scaler["target_mod"])) 
        
    benchmark["tolerance"] *= scaler["tolerance_mult"]
    
    # Apply position-specific adjustments
    if position and position in POSITION_BENCHMARKS and metric in POSITION_BENCHMARKS[position]:
        pos_benchmark = POSITION_BENCHMARKS[position][metric]
        benchmark["target"] = pos_benchmark["target"] * scaler["target_mod"]
        benchmark["tolerance"] = pos_benchmark["tolerance"] * scaler["tolerance_mult"]
        benchmark["position"] = position
    
    benchmark["source"] = f"scaled_{athlete_level}"
    return benchmark

def evaluate_against_elite(measured_value: float, benchmark: dict) -> dict:
    """Evaluate measured value against Olympic benchmark"""
    
    target = benchmark["target"]
    tolerance = benchmark["tolerance"]
    direction = benchmark["direction"]
    
    deviation = measured_value - target
    
    if direction == "higher":
        is_elite = measured_value >= (target - tolerance)
        performance_score = min(1.0, max(0.0, (measured_value - (target - tolerance)) / (tolerance * 2)))
    else:
        is_elite = measured_value <= (target + tolerance)
        performance_score = min(1.0, max(0.0, ((target + tolerance) - measured_value) / (tolerance * 2)))
    
    if abs(deviation) <= tolerance:
        percentile = 90 + (abs(deviation) / tolerance) * 10 
    else:
        percentile = max(0, 90 - (abs(deviation) - tolerance) / tolerance * 30)
    
    return {
        "measured": measured_value,
        "target": target,
        "deviation": deviation,
        "is_elite": is_elite,
        "performance_score": performance_score,
        "percentile": percentile,
        "benchmark_source": benchmark.get("source", "unknown"),
        "position": benchmark.get("position"),
        "seasonal_adjustment": benchmark.get("seasonal_adjustment", 0)
    }

def get_temporal_constraints(technique: str, phase: str) -> dict:
    temporal_data = {
        "spike": {
            "repulsion": {"duration": 1.01, "window_start": 0.0, "window_end": 1.2},
            "impact": {"duration": 0.57, "window_start": 0.8, "window_end": 1.4},
            "landing": {"duration": 0.39, "window_start": 1.2, "window_end": 2.0},
        },
        "serve": {
            "toss": {"duration": 0.3, "window_start": 0.0, "window_end": 0.5},
            "approach": {"duration": 0.8, "window_start": 0.2, "window_end": 1.2},
            "contact": {"duration": 0.1, "window_start": 0.8, "window_end": 1.0},
        },
        "block": {
            "reaction": {"duration": 0.3, "window_start": 0.0, "window_end": 0.4},
            "penultimate": {"duration": 0.4, "window_start": 0.2, "window_end": 0.8},
            "jump": {"duration": 0.5, "window_start": 0.4, "window_end": 1.0},
        },
        "dig": {
            "reception": {"duration": 0.7, "window_start": 0.0, "window_end": 0.8}, 
            "platform": {"duration": 0.2, "window_start": 0.5, "window_end": 0.9},
            "recovery": {"duration": 0.8, "window_start": 0.7, "window_end": 1.5},
        }
    }
    
    return temporal_data.get(technique, {}).get(phase, {"duration": 0.5, "window_start": 0.0, "window_end": 1.0})

def detect_position_from_movement(pose_sequence: np.ndarray, technique_counts: dict) -> str:
    total_jumps = sum(technique_counts.values())
    if total_jumps == 0:
        return "unknown"
    
    block_ratio = technique_counts.get("block", 0) / total_jumps
    attack_ratio = technique_counts.get("spike", 0) / total_jumps
    
    if len(pose_sequence) > 0:
        hip_y = (pose_sequence[:, 11, 1] + pose_sequence[:, 12, 1]) / 2
        jump_height = (hip_y.max() - hip_y.min()) / 100  
    else:
        jump_height = 0
    
    if block_ratio > 0.6 and total_jumps > 35: 
        return "middle"
    elif attack_ratio > 0.5 and total_jumps > 25: 
        return "opposite"
    elif attack_ratio > 0.4 and block_ratio > 0.3:
        return "receiver"
    elif total_jumps < 20 and block_ratio > 0.6:
        return "setter"
    else:
        return "receiver" 

def get_seasonal_context(session_count: int, tournament_phase: str = None) -> str:
    if tournament_phase:
        return tournament_phase.lower()
    
    if session_count < 5:
        return "early_season"
    elif session_count < 15:
        return "mid_season"
    else:
        return "late_season"

ELITE_COACHING_CUES = {
    "spike": {
        "elbow_flexion_impact": "Feel your elbow reaching full extension at contact - like a whip cracking",
        "leg_flexion_repulsion": "Load your hips like a coiled spring on the penultimate step",
        "torso_extension_initial": "Create a bow-and-arrow position with your torso and hitting arm",
        "repulsion_time": "Accelerate through the approach - don't rush the penultimate step",
    },
    "block": {
        "hip_angle": "Drop your hips to 90° - like sitting in a chair",
        "knee_angle": "Keep knees at 100-110° for optimal power absorption",
        "hand_position_height": "Penetrate 30cm over the net with your hands",
        "reaction_time": "React within 0.3 seconds - train with random cues",
    },
    "serve": {
        "toss_height": "Toss to 2.5m height - let the ball hang at its peak",
        "shoulder_rotation": "Rotate through 45° - drive your back shoulder forward",
        "body_lean_angle": "Lean 15° forward - transfer weight into the serve",
        "contact_point_height": "Contact at 2.8m - reach up and forward",
    },
    "dig": {
        "platform_angle": "Create 45° platform angle - thumbs pointing down",
        "knee_bend_angle": "Drop to 110° knee bend - get under the ball",
        "reception_window": "Receive within 0.7 seconds - no hesitation",
        "arm_extension_angle": "Keep arms at 170° - elbows locked straight",
    }
}

def get_elite_coaching_cue(technique: str, metric: str) -> str:
    return ELITE_COACHING_CUES.get(technique, {}).get(metric, "Focus on proper technique execution")
