"""
Elite Olympic-Level Volleyball Analysis Engine
Integrates FIVB standards, position-specific benchmarks, and temporal constraints
"""
import numpy as np
import json
from typing import Dict, List, Optional, Tuple
from elite_biomechanics import (
    get_elite_benchmark, evaluate_against_elite, detect_position_from_movement,
    get_elite_coaching_cue, get_seasonal_context
)
from temporal_analyzer import analyze_temporal_phases, calculate_joint_angle

# Olympic-level technique configurations with phase-specific analysis
ELITE_TECHNIQUE_CONFIG = {
    "spike": {
        "phases": ["APPROACH", "REPULSION", "IMPACT", "LANDING"],
        "critical_metrics": [
            "elbow_flexion_impact", "leg_flexion_repulsion", "torso_extension_initial",
            "jump_height", "spike_speed", "flying_distance"
        ],
        "temporal_windows": {
            "repulsion": {"duration": 1.01, "tolerance": 0.1},
            "impact": {"duration": 0.57, "tolerance": 0.05},
            "landing": {"duration": 0.39, "tolerance": 0.05}
        }
    },
    "block": {
        "phases": ["REACTION", "PENULTIMATE", "JUMP", "LANDING"],
        "critical_metrics": [
            "hip_angle", "knee_angle", "ankle_angle", "hand_position_height",
            "reaction_time", "landing_balance", "shoulder_width_ratio"
        ],
        "temporal_windows": {
            "reaction": {"duration": 0.3, "tolerance": 0.05},
            "penultimate": {"duration": 0.4, "tolerance": 0.1},
            "jump": {"duration": 0.5, "tolerance": 0.1}
        }
    },
    "serve": {
        "phases": ["TOSS", "LOADING", "CONTACT", "FOLLOW_THROUGH"],
        "critical_metrics": [
            "toss_height", "shoulder_rotation", "body_lean_angle", "wrist_snap_velocity",
            "contact_point_height", "step_timing"
        ],
        "temporal_windows": {
            "toss": {"duration": 0.3, "tolerance": 0.05},
            "loading": {"duration": 0.8, "tolerance": 0.1},
            "contact": {"duration": 0.1, "tolerance": 0.02}
        }
    },
    "dig": {
        "phases": ["READ", "PLATFORM", "CONTACT", "RECOVERY"],
        "critical_metrics": [
            "platform_angle", "knee_bend_angle", "hip_drop_distance", "arm_extension_angle",
            "reception_window", "recovery_time"
        ],
        "temporal_windows": {
            "reception": {"duration": 0.7, "tolerance": 0.1},  # Critical for jump serves
            "platform": {"duration": 0.2, "tolerance": 0.05},
            "recovery": {"duration": 0.8, "tolerance": 0.1}
        }
    }
}

# Position-specific elite standards from FIVB World Championship data
POSITION_ELITE_STANDARDS = {
    "middle": {
        "block_jumps_per_match": {"target": 44, "tolerance": 12, "priority": "high"},
        "attack_jumps_per_match": {"target": 22, "tolerance": 10, "priority": "medium"},
        "jump_height_attack": {"target": 96.5, "tolerance": 3.0, "priority": "high"},
        "horizontal_distance": {"target": 2.1, "tolerance": 0.3, "priority": "medium"},
        "flying_distance_ratio": {"target": 0.85, "tolerance": 0.1, "priority": "low"},
        "movement_pattern": "explosive_vertical",
        "key_characteristics": ["quick_reaction", "high_block_touch", "explosive_movement"]
    },
    "opposite": {
        "attack_jumps_per_match": {"target": 31, "tolerance": 10, "priority": "high"},
        "block_jumps_per_match": {"target": 28, "tolerance": 8, "priority": "medium"},
        "jump_height_attack": {"target": 96.5, "tolerance": 3.0, "priority": "high"},
        "horizontal_distance": {"target": 2.8, "tolerance": 0.3, "priority": "high"},
        "flying_distance_ratio": {"target": 1.15, "tolerance": 0.1, "priority": "medium"},
        "movement_pattern": "powerful_horizontal",
        "key_characteristics": ["powerful_approach", "long_flying_distance", "high_contact_point"]
    },
    "receiver": {
        "attack_jumps_per_match": {"target": 22, "tolerance": 10, "priority": "medium"},
        "block_jumps_per_match": {"target": 18, "tolerance": 6, "priority": "medium"},
        "jump_height_attack": {"target": 94.0, "tolerance": 4.0, "priority": "medium"},
        "horizontal_distance": {"target": 2.3, "tolerance": 0.3, "priority": "medium"},
        "flying_distance_ratio": {"target": 0.95, "tolerance": 0.1, "priority": "low"},
        "movement_pattern": "balanced_all_around",
        "key_characteristics": ["consistent_performance", "good_reception", "solid_attack"]
    },
    "setter": {
        "block_jumps_per_match": {"target": 15, "tolerance": 5, "priority": "low"},
        "attack_jumps_per_match": {"target": 8, "tolerance": 3, "priority": "low"},
        "jump_height_attack": {"target": 88.0, "tolerance": 5.0, "priority": "low"},
        "horizontal_distance": {"target": 1.8, "tolerance": 0.3, "priority": "low"},
        "flying_distance_ratio": {"target": 0.7, "tolerance": 0.1, "priority": "low"},
        "movement_pattern": "efficient_positioning",
        "key_characteristics": ["quick_movement", "precise_positioning", "efficient_jumping"]
    }
}

# Elite coaching knowledge from FIVB manuals and Olympic coaches
ELITE_COACHING_KNOWLEDGE = {
    "universal_principles": {
        "body_alignment": "Maintain vertical alignment of hips, knees, and ankles during takeoff",
        "core_stability": "Engage core throughout movement to prevent energy leaks",
        "sequential_coordination": "Generate power from ground up: legs → hips → torso → shoulder → arm",
        "visual_focus": "Keep eyes on ball until contact, then track target",
        "breathing_pattern": "Exhale during power phase, inhale during preparation"
    },
    
    "spike_optimization": {
        "approach_timing": "4-step rhythm: 1-2-3-4 with acceleration on step 3",
        "penultimate_step": "Long penultimate step creates horizontal momentum conversion",
        "arm_coordination": "Opposite arm drives up simultaneously with takeoff leg",
        "contact_physics": "Contact at peak of jump with fully extended hitting arm",
        "follow_through": "Complete follow-through across body to opposite hip",
        "error_patterns": {
            "early_contact": "Contacting ball on way down reduces power by 30-40%",
            "late_approach": "Rushed approach reduces jump height by 15-20%",
            "poor_timing": "Mistimed arm swing reduces ball speed by 25-35%"
        }
    },
    
    "block_optimization": {
        "ready_position": "Weight on balls of feet, knees at 100-110°, hips at 90°",
        "reaction_timing": "React within 0.3 seconds of setter contact",
        "penetration": "Hands penetrate 30cm over net with thumbs forward",
        "shoulder_position": "Shoulders parallel to net, not square to attacker",
        "landing_technique": "Land on both feet simultaneously with bent knees",
        "common_errors": {
            "late_read": "Reading attacker too late reduces block success by 45%",
            "poor_penetration": "Insufficient penetration reduces block effectiveness by 60%",
            "incorrect_timing": "Early/late jump timing reduces block touch by 20-25%"
        }
    },
    
    "serve_optimization": {
        "toss_consistency": "Toss to 2.5m height, 30cm in front of hitting shoulder",
        "body_mechanics": "Rotate through 45° shoulder rotation with 15° forward lean",
        "contact_physics": "Contact at peak of toss with fully extended hitting arm",
        "wrist_snap": "Accelerate wrist through contact for topspin generation",
        "follow_through": "Complete follow-through across body to opposite hip",
        "velocity_targets": {
            "float_serve": "18-22 m/s with minimal spin",
            "jump_serve": "25-30 m/s with heavy topspin",
            "topspin_serve": "22-26 m/s with 8-12 revolutions per second"
        }
    },
    
    "dig_optimization": {
        "ready_position": "Weight forward on balls of feet, hips at 110° knee bend",
        "platform_formation": "Forearms parallel, 45° angle to floor, thumbs pointing down",
        "hip_drop": "Drop hips 25cm to get under fast serves",
        "arm_extension": "Extend arms fully with locked elbows",
        "recovery_position": "Return to ready position within 0.8 seconds",
        "reception_windows": {
            "float_serve": "0.9-1.1 seconds to read and react",
            "topspin_serve": "0.7-0.9 seconds for reception",
            "jump_serve": "0.5-0.7 seconds maximum reaction time"
        }
    }
}

def analyze_elite_biomechanics(pose_sequence: np.ndarray, technique: str, position: str = None, 
                              session_context: dict = None) -> dict:
    """Analyze biomechanics against Olympic-level standards"""
    
    results = {
        "technique": technique,
        "position": position or "unknown",
        "phase_analysis": {},
        "position_specific_metrics": {},
        "temporal_accuracy": {},
        "elite_comparisons": {},
        "coaching_insights": [],
        "performance_percentile": 0,
        "olympic_readiness_score": 0
    }
    
    # Get technique configuration
    tech_config = ELITE_TECHNIQUE_CONFIG.get(technique, {})
    
    # Analyze temporal phases
    temporal_results = analyze_temporal_phases(pose_sequence, 30.0, technique)  # Assuming 30fps
    results["temporal_accuracy"] = temporal_results.get("timing_analysis", {})
    results["phase_analysis"] = temporal_results.get("phases", [])
    
    # Calculate elite biomechanical metrics
    elite_metrics = calculate_elite_metrics(pose_sequence, technique)
    results["elite_metrics"] = elite_metrics
    
    # Position-specific analysis
    if position and position in POSITION_ELITE_STANDARDS:
        position_metrics = analyze_position_specific_metrics(elite_metrics, position, technique)
        results["position_specific_metrics"] = position_metrics
    
    # Compare against Olympic benchmarks
    elite_comparisons = compare_against_olympic_standards(elite_metrics, technique, position)
    results["elite_comparisons"] = elite_comparisons
    
    # Generate coaching insights
    coaching_insights = generate_elite_coaching_insights(results, technique, position)
    results["coaching_insights"] = coaching_insights
    
    # Calculate overall scores
    results["performance_percentile"] = calculate_performance_percentile(elite_comparisons)
    results["olympic_readiness_score"] = calculate_olympic_readiness(elite_comparisons, temporal_results)
    
    return results

def calculate_elite_metrics(pose_sequence: np.ndarray, technique: str) -> dict:
    """Calculate elite-level biomechanical metrics"""
    
    metrics = {}
    
    if technique == "spike":
        # Calculate phase-specific angles from Open Spike Kinematics
        if len(pose_sequence) >= 10:
            # Initial phase metrics
            initial_frame = len(pose_sequence) // 4
            metrics["leg_flexion_initial"] = calculate_joint_angle(pose_sequence[initial_frame], [13, 11, 15])
            metrics["torso_extension_initial"] = calculate_joint_angle(pose_sequence[initial_frame], [11, 5, 0])
            
            # Repulsion phase metrics
            repulsion_frame = len(pose_sequence) // 2
            metrics["leg_flexion_repulsion"] = calculate_joint_angle(pose_sequence[repulsion_frame], [13, 11, 15])
            metrics["elbow_flexion_repulsion"] = calculate_joint_angle(pose_sequence[repulsion_frame], [7, 5, 9])
            
            # Impact phase metrics
            impact_frame = 3 * len(pose_sequence) // 4
            metrics["elbow_flexion_impact"] = calculate_joint_angle(pose_sequence[impact_frame], [7, 5, 9])
            
            # Landing phase metrics
            landing_frame = -1 if len(pose_sequence) > 1 else 0
            metrics["torso_extension_landing"] = calculate_joint_angle(pose_sequence[landing_frame], [11, 5, 0])
            
            # Calculate jump height: Displacement + Estimated Reach
            # This prevents the "Harsh Critique" by comparing like-for-like
            hip_y = (pose_sequence[:, 11, 1] + pose_sequence[:, 12, 1]) / 2
            displacement = (hip_y.max() - hip_y.min()) / 100
            
            # Estimate reach (Shoulder to Wrist at peak)
            shoulder_y = pose_sequence[impact_frame, 6, 1]
            wrist_y = pose_sequence[impact_frame, 10, 1]
            reach = (shoulder_y - wrist_y) / 100
            
            # Total Spike Height (Target ~4.8m for elite)
            metrics["jump_height"] = 2.43 + displacement + reach # 2.43 is net height
            
            # Calculate spike speed from wrist velocity
            wrist_positions = pose_sequence[:, 10, :2] # Use right wrist
            wrist_velocities = np.linalg.norm(np.diff(wrist_positions, axis=0), axis=1)
            metrics["spike_speed"] = np.max(wrist_velocities) if len(wrist_velocities) > 0 else 0
            
            # Calculate flying distance
            ankle_positions = pose_sequence[:, 15, :2]
            metrics["flying_distance"] = np.linalg.norm(ankle_positions[-1] - ankle_positions[0]) / 100
    
    elif technique == "block":
        # FIVB Level II Manual specifications
        if len(pose_sequence) >= 5:
            # Postural specifications
            block_frame = len(pose_sequence) // 2
            metrics["hip_angle"] = calculate_joint_angle(pose_sequence[block_frame], [11, 12, 13])
            metrics["knee_angle"] = calculate_joint_angle(pose_sequence[block_frame], [11, 13, 15])
            metrics["ankle_angle"] = calculate_joint_angle(pose_sequence[block_frame], [13, 15, 16])
            
            # Hand position height (relative to hip)
            wrist_y = pose_sequence[block_frame, 9, 1]
            hip_y = pose_sequence[block_frame, 11, 1]
            metrics["hand_position_height"] = (hip_y - wrist_y) / 100 * 100  # Convert to cm
            
            # Shoulder width ratio
            shoulder_distance = np.linalg.norm(pose_sequence[block_frame, 5, :2] - pose_sequence[block_frame, 6, :2])
            body_height = np.linalg.norm(pose_sequence[block_frame, 5, :2] - pose_sequence[block_frame, 15, :2])
            metrics["shoulder_width_ratio"] = shoulder_distance / body_height if body_height > 0 else 0
            
            # Landing balance (stability of last 5 frames)
            ankle_y_positions = pose_sequence[-5:, 15, 1]
            metrics["landing_balance"] = 1.0 - (np.std(ankle_y_positions) / np.mean(ankle_y_positions)) if np.mean(ankle_y_positions) > 0 else 0
    
    elif technique == "serve":
        # Serve-specific metrics
        if len(pose_sequence) >= 5:
            # Toss height (wrist vertical travel)
            wrist_y = pose_sequence[:, 9, 1]
            metrics["toss_height"] = (wrist_y.max() - wrist_y.min()) / 100  # Convert to meters
            
            # Shoulder rotation (mid-serve)
            mid_frame = len(pose_sequence) // 2
            metrics["shoulder_rotation"] = calculate_joint_angle(pose_sequence[mid_frame], [5, 11, 6])
            
            # Body lean angle
            metrics["body_lean_angle"] = calculate_joint_angle(pose_sequence[mid_frame], [0, 11, 15])
            
            # Wrist snap velocity (standard deviation of wrist x-position)
            metrics["wrist_snap_velocity"] = np.std(pose_sequence[:, 9, 0]) / 100
            
            # Contact point height
            contact_frame = 3 * len(pose_sequence) // 4
            metrics["contact_point_height"] = (pose_sequence[contact_frame, 9, 1] - pose_sequence[contact_frame, 11, 1]) / 100
            
            # Step timing (total duration)
            metrics["step_timing"] = len(pose_sequence) / 30.0  # Assuming 30fps
    
    elif technique == "dig":
        # Dig-specific metrics
        if len(pose_sequence) >= 5:
            # Platform angle (forearm angle)
            platform_frame = len(pose_sequence) // 3
            metrics["platform_angle"] = calculate_joint_angle(pose_sequence[platform_frame], [9, 7, 5])
            
            # Knee bend angle
            metrics["knee_bend_angle"] = calculate_joint_angle(pose_sequence[platform_frame], [11, 13, 15])
            
            # Hip drop distance
            hip_y = pose_sequence[:, 11, 1]
            metrics["hip_drop_distance"] = (hip_y.max() - hip_y.min()) / 100
            
            # Arm extension angle
            metrics["arm_extension_angle"] = calculate_joint_angle(pose_sequence[platform_frame], [5, 7, 9])
            
            # Recovery time (last third of sequence)
            recovery_frames = len(pose_sequence) // 3
            metrics["recovery_time"] = recovery_frames / 30.0
            
            # Reception window (critical for jump serves)
            metrics["reception_window"] = len(pose_sequence) / 30.0
    
    return metrics

def analyze_position_specific_metrics(elite_metrics: dict, position: str, technique: str) -> dict:
    """Analyze metrics specific to player position"""
    
    position_analysis = {
        "position": position,
        "movement_pattern": POSITION_ELITE_STANDARDS[position]["movement_pattern"],
        "key_characteristics": POSITION_ELITE_STANDARDS[position]["key_characteristics"],
        "position_specific_metrics": {},
        "suitability_score": 0,
        "recommendations": []
    }
    
    # Compare against position-specific standards
    position_standards = POSITION_ELITE_STANDARDS[position]
    suitability_scores = []
    
    for metric, standard in position_standards.items():
        if metric in elite_metrics and isinstance(standard, dict) and "target" in standard:
            measured_value = elite_metrics[metric]
            target = standard["target"]
            tolerance = standard["tolerance"]
            priority = standard.get("priority", "medium")
            
            # Calculate position-specific score
            deviation = abs(measured_value - target)
            if deviation <= tolerance:
                score = 1.0 - (deviation / tolerance) * 0.3  # 0.7-1.0 for within tolerance
            else:
                score = max(0.0, 1.0 - (deviation - tolerance) / target)
            
            # Apply priority weighting
            priority_weights = {"high": 1.5, "medium": 1.0, "low": 0.7}
            weighted_score = score * priority_weights.get(priority, 1.0)
            suitability_scores.append(weighted_score)
            
            position_analysis["position_specific_metrics"][metric] = {
                "measured": measured_value,
                "target": target,
                "deviation": measured_value - target,
                "score": score,
                "priority": priority,
                "within_tolerance": deviation <= tolerance
            }
    
    # Calculate overall suitability score
    position_analysis["suitability_score"] = np.mean(suitability_scores) if suitability_scores else 0
    
    # Generate position-specific recommendations
    if position_analysis["suitability_score"] < 0.8:
        if position == "middle":
            position_analysis["recommendations"].extend([
                "Focus on explosive vertical jumping for quick blocks",
                "Work on reaction time - practice reading setter cues",
                "Develop fast-twitch muscle fibers for rapid takeoffs"
            ])
        elif position == "opposite":
            position_analysis["recommendations"].extend([
                "Emphasize powerful horizontal approach for long flying distance",
                "Work on arm swing mechanics for maximum spike speed",
                "Practice high-contact point hitting over block"
            ])
        elif position == "receiver":
            position_analysis["recommendations"].extend([
                "Develop consistent all-around skills",
                "Focus on reception technique and platform stability",
                "Work on transition from reception to attack"
            ])
    
    return position_analysis

def compare_against_olympic_standards(elite_metrics: dict, technique: str, position: str = None) -> dict:
    """Compare metrics against Olympic benchmarks"""
    
    comparisons = {
        "technique": technique,
        "position": position,
        "metric_comparisons": {},
        "overall_elite_score": 0,
        "olympic_readiness": "unknown",
        "critical_violations": [],
        "strengths": [],
        "improvement_areas": []
    }
    
    scores = []
    
    # Compare each metric against Olympic benchmarks
    for metric, measured_value in elite_metrics.items():
        benchmark = get_elite_benchmark(technique, metric, position)
        
        if benchmark and "target" in benchmark:
            evaluation = evaluate_against_elite(measured_value, benchmark)
            comparisons["metric_comparisons"][metric] = evaluation
            scores.append(evaluation["performance_score"])
            
            # Categorize strengths and weaknesses
            if evaluation["is_elite"]:
                comparisons["strengths"].append(metric)
            else:
                comparisons["improvement_areas"].append(metric)
                
                # Identify critical violations
                if evaluation["percentile"] < 70:
                    comparisons["critical_violations"].append(f"{metric}: {evaluation['percentile']:.0f}th percentile")
    
    # Calculate overall scores
    comparisons["overall_elite_score"] = np.mean(scores) if scores else 0
    
    # Determine Olympic readiness level
    if comparisons["overall_elite_score"] >= 0.9:
        comparisons["olympic_readiness"] = "ELITE"
    elif comparisons["overall_elite_score"] >= 0.8:
        comparisons["olympic_readiness"] = "ADVANCED"
    elif comparisons["overall_elite_score"] >= 0.7:
        comparisons["olympic_readiness"] = "INTERMEDIATE"
    else:
        comparisons["olympic_readiness"] = "DEVELOPING"
    
    return comparisons

def generate_elite_coaching_insights(analysis_results: dict, technique: str, position: str = None) -> List[str]:
    """Generate Olympic-level coaching insights"""
    
    insights = []
    
    # Add technique-specific insights
    if technique in ELITE_COACHING_KNOWLEDGE:
        tech_knowledge = ELITE_COACHING_KNOWLEDGE[technique + "_optimization"]
        
        # Add universal principles
        insights.extend([
            ELITE_COACHING_KNOWLEDGE["universal_principles"]["body_alignment"],
            ELITE_COACHING_KNOWLEDGE["universal_principles"]["core_stability"]
        ])
        
        # Add technique-specific insights
        if "error_patterns" in tech_knowledge:
            # Check for common errors
            for error_type, error_description in tech_knowledge["error_patterns"].items():
                if error_type in [area.lower() for area in analysis_results.get("elite_comparisons", {}).get("improvement_areas", [])]:
                    insights.append(f"CRITICAL: {error_description}")
        
        # Add velocity targets for serves
        if technique == "serve" and "velocity_targets" in tech_knowledge:
            insights.append(f"Target velocities: {', '.join([f'{k}: {v}' for k, v in tech_knowledge['velocity_targets'].items()])}")
        
        # Add reception windows for digs
        if technique == "dig" and "reception_windows" in tech_knowledge:
            insights.append(f"Reception timing: {', '.join([f'{k}: {v}' for k, v in tech_knowledge['reception_windows'].items()])}")
    
    # Add position-specific insights
    if position and position in POSITION_ELITE_STANDARDS:
        position_data = POSITION_ELITE_STANDARDS[position]
        insights.append(f"Position focus: {', '.join(position_data['key_characteristics'])}")
        insights.append(f"Movement pattern: {position_data['movement_pattern']}")
    
    # Add temporal accuracy insights
    temporal_accuracy = analysis_results.get("temporal_accuracy", {})
    if "overall_timing_score" in temporal_accuracy:
        timing_score = temporal_accuracy["overall_timing_score"]
        if timing_score < 0.7:
            insights.append("Timing needs significant work - practice movement rhythm and coordination")
        elif timing_score < 0.9:
            insights.append("Good timing foundation - refine specific phase transitions")
        else:
            insights.append("Excellent timing - focus on consistency and power generation")
    
    # Add metric-specific coaching cues
    elite_comparisons = analysis_results.get("elite_comparisons", {})
    for metric in elite_comparisons.get("improvement_areas", []):
        cue = get_elite_coaching_cue(technique, metric)
        if cue and "Feel" in cue:
            insights.append(f"{metric.replace('_', ' ').title()}: {cue}")
    
    return insights

def calculate_performance_percentile(elite_comparisons: dict) -> float:
    """Calculate overall performance percentile"""
    
    if not elite_comparisons or "metric_comparisons" not in elite_comparisons:
        return 0
    
    percentiles = []
    for metric, evaluation in elite_comparisons["metric_comparisons"].items():
        percentiles.append(evaluation.get("percentile", 0))
    
    return np.mean(percentiles) if percentiles else 0

def calculate_olympic_readiness(elite_comparisons: dict, temporal_results: dict) -> float:
    """Calculate Olympic readiness score (0-100)"""
    
    if not elite_comparisons:
        return 0
    
    # Base score from biomechanical accuracy (70% weight)
    biomechanical_score = elite_comparisons.get("overall_elite_score", 0) * 70
    
    # Temporal accuracy score (20% weight)
    temporal_score = 0
    if temporal_results and "timing_analysis" in temporal_results:
        temporal_score = temporal_results["timing_analysis"].get("overall_timing_score", 0) * 20
    
    # Phase consistency score (10% weight)
    phase_score = 0
    if "phases" in temporal_results:
        phases = temporal_results["phases"]
        if phases:
            phase_scores = [phase.get("timing_score", 0) for phase in phases]
            phase_score = np.mean(phase_scores) * 10 if phase_scores else 0
    
    return min(100, biomechanical_score + temporal_score + phase_score)

def create_elite_training_program(analysis_results: dict, technique: str, position: str = None) -> dict:
    """Create Olympic-level training program based on analysis"""
    
    program = {
        "technique": technique,
        "position": position,
        "program_duration_weeks": 8,
        "weekly_structure": {},
        "specific_drills": [],
        "progression_milestones": [],
        "success_metrics": []
    }
    
    # Identify priority areas for improvement
    improvement_areas = analysis_results.get("elite_comparisons", {}).get("improvement_areas", [])
    critical_violations = analysis_results.get("elite_comparisons", {}).get("critical_violations", [])
    
    # Create 8-week progressive program
    for week in range(1, 9):
        if week <= 2:
            # Foundation phase
            program["weekly_structure"][f"week_{week}"] = {
                "focus": "Foundation and technique correction",
                "sessions_per_week": 3,
                "intensity": "moderate",
                "key_metrics": improvement_areas[:2] if improvement_areas else ["basic_technique"]
            }
        elif week <= 4:
            # Development phase
            program["weekly_structure"][f"week_{week}"] = {
                "focus": "Skill development and consistency",
                "sessions_per_week": 4,
                "intensity": "high",
                "key_metrics": improvement_areas[:3] if len(improvement_areas) > 2 else improvement_areas
            }
        elif week <= 6:
            # Performance phase
            program["weekly_structure"][f"week_{week}"] = {
                "focus": "Performance optimization and power development",
                "sessions_per_week": 4,
                "intensity": "very_high",
                "key_metrics": improvement_areas
            }
        else:
            # Elite phase
            program["weekly_structure"][f"week_{week}"] = {
                "focus": "Elite performance and competition readiness",
                "sessions_per_week": 5,
                "intensity": "maximum",
                "key_metrics": ["overall_technique", "temporal_accuracy", "power_generation"]
            }
    
    # Add specific drills based on technique and position
    if technique == "spike":
        program["specific_drills"] = [
            "4-step approach rhythm training",
            "Penultimate step power development",
            "Arm swing coordination drills",
            "Contact point accuracy training",
            "Follow-through completion exercises"
        ]
    elif technique == "block":
        program["specific_drills"] = [
            "Reaction time improvement drills",
            "Penetration technique training",
            "Timing coordination exercises",
            "Landing stability training",
            "Read and react simulations"
        ]
    
    # Set progression milestones
    program["progression_milestones"] = [
        {"week": 2, "target": "Correct basic technique errors"},
        {"week": 4, "target": "Achieve 80% consistency in technique execution"},
        {"week": 6, "target": "Reach intermediate performance level"},
        {"week": 8, "target": "Achieve elite-level performance metrics"}
    ]
    
    # Define success metrics
    program["success_metrics"] = [
        "Overall elite score > 0.85",
        "Temporal accuracy score > 0.8",
        "Critical violations eliminated",
        "Performance percentile > 85th"
    ]
    
    return program