"""
Enhanced Pose Extractor with Olympic-level temporal analysis and position detection
Integrates elite biomechanical benchmarks with real-time analysis
"""
import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional
from elite_biomechanics import (
    get_elite_benchmark, evaluate_against_elite, get_temporal_constraints, 
    detect_position_from_movement, get_seasonal_context
)

def analyze_temporal_phases(pose_sequence: np.ndarray, fps: float, technique: str) -> Dict:
    """Analyze movement phases with Olympic-level timing constraints"""
    
    if len(pose_sequence) < 10:
        return {"phases": [], "timing_analysis": {}}
    
    phases = []
    timing_analysis = {}
    
    # Get temporal constraints for the technique
    temporal_constraints = get_temporal_constraints(technique, "all")
    
    # Calculate joint velocities for phase detection
    joint_velocities = calculate_joint_velocities(pose_sequence, fps)
    
    # Detect key movement phases based on velocity peaks
    if technique == "spike":
        phases = detect_spike_phases(pose_sequence, joint_velocities, fps, temporal_constraints)
    elif technique == "block":
        phases = detect_block_phases(pose_sequence, joint_velocities, fps, temporal_constraints)
    elif technique == "serve":
        phases = detect_serve_phases(pose_sequence, joint_velocities, fps, temporal_constraints)
    elif technique == "dig":
        phases = detect_dig_phases(pose_sequence, joint_velocities, fps, temporal_constraints)
    
    # Analyze timing against Olympic standards
    timing_analysis = evaluate_temporal_accuracy(phases, temporal_constraints, technique)
    
    return {
        "phases": phases,
        "timing_analysis": timing_analysis,
        "temporal_constraints": temporal_constraints,
        "joint_velocities": joint_velocities
    }

def calculate_joint_velocities(pose_sequence: np.ndarray, fps: float) -> Dict:
    """Calculate joint angular velocities for phase detection"""
    
    dt = 1.0 / fps
    velocities = {}
    
    # Key joints for each technique
    key_joints = {
        "wrist": [9, 10],  # Left and right wrist
        "elbow": [7, 8],   # Left and right elbow
        "shoulder": [5, 6], # Left and right shoulder
        "hip": [11, 12],    # Left and right hip
        "knee": [13, 14],   # Left and right knee
        "ankle": [15, 16],  # Left and right ankle
    }
    
    for joint_name, joint_indices in key_joints.items():
        velocities[joint_name] = {
            "linear_velocity": [],
            "angular_velocity": []
        }
        
        # Calculate linear velocity
        for i in range(1, len(pose_sequence)):
            prev_pos = pose_sequence[i-1, joint_indices, :2]
            curr_pos = pose_sequence[i, joint_indices, :2]
            
            # Average velocity across left/right joints
            velocity = np.mean(np.linalg.norm(curr_pos - prev_pos, axis=1)) / dt
            velocities[joint_name]["linear_velocity"].append(velocity)
        
        # Calculate angular velocity for relevant joints
        if joint_name in ["elbow", "shoulder", "knee", "hip"]:
            for i in range(1, len(pose_sequence)):
                prev_angle = calculate_joint_angle(pose_sequence[i-1], joint_indices)
                curr_angle = calculate_joint_angle(pose_sequence[i], joint_indices)
                angular_vel = abs(curr_angle - prev_angle) / dt
                velocities[joint_name]["angular_velocity"].append(angular_vel)
    
    return velocities

def calculate_joint_angle(pose_frame: np.ndarray, joint_indices: List[int]) -> float:
    """Calculate angle between three joints"""
    
    if len(joint_indices) == 2:  # For bilateral joints, use average
        left_angle = calculate_angle_between_joints(pose_frame, joint_indices[0], joint_indices[0]-1, joint_indices[0]+1)
        right_angle = calculate_angle_between_joints(pose_frame, joint_indices[1], joint_indices[1]-1, joint_indices[1]+1)
        return (left_angle + right_angle) / 2
    else:
        return 0.0

def calculate_angle_between_joints(pose_frame: np.ndarray, joint1: int, joint2: int, joint3: int) -> float:
    """Calculate angle between three joints using law of cosines"""
    
    try:
        # Get 2D coordinates
        p1 = pose_frame[joint1, :2]
        p2 = pose_frame[joint2, :2]
        p3 = pose_frame[joint3, :2]
        
        # Calculate vectors
        v1 = p1 - p2
        v2 = p3 - p2
        
        # Calculate angle
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
        angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
        
        return np.degrees(angle)
    except:
        return 0.0

def detect_spike_phases(pose_sequence: np.ndarray, velocities: Dict, fps: float, constraints: Dict) -> List[Dict]:
    """Detect spike phases with Olympic timing"""
    
    phases = []
    
    # Find key velocity peaks
    wrist_vel = np.array(velocities["wrist"]["linear_velocity"])
    elbow_ang_vel = np.array(velocities["elbow"]["angular_velocity"])
    
    # Approach phase (increasing velocity)
    approach_start = find_phase_start(wrist_vel, threshold=0.5, direction="increasing")
    
    # Repulsion phase (maximum acceleration)
    repulsion_peak = find_velocity_peak(wrist_vel, window_size=int(0.3 * fps))  # 0.3s window
    
    # Impact phase (maximum velocity)
    impact_peak = find_velocity_peak(wrist_vel[repulsion_peak:], direction="max")
    if impact_peak > 0:
        impact_peak += repulsion_peak
    
    # Landing phase (deceleration)
    landing_start = find_phase_start(wrist_vel[impact_peak:], threshold=0.3, direction="decreasing")
    if landing_start > 0:
        landing_start += impact_peak
    
    # Create phases with Olympic timing validation
    if approach_start >= 0 and repulsion_peak >= 0 and impact_peak >= 0:
        phases = [
            {
                "name": "APPROACH",
                "start_frame": approach_start,
                "end_frame": repulsion_peak,
                "duration": (repulsion_peak - approach_start) / fps,
                "target_duration": constraints.get("repulsion", {}).get("duration", 1.01),
                "timing_score": calculate_timing_score((repulsion_peak - approach_start) / fps, 1.01, 0.1)
            },
            {
                "name": "REPULSION",
                "start_frame": repulsion_peak,
                "end_frame": impact_peak,
                "duration": (impact_peak - repulsion_peak) / fps,
                "target_duration": constraints.get("impact", {}).get("duration", 0.57),
                "timing_score": calculate_timing_score((impact_peak - repulsion_peak) / fps, 0.57, 0.05)
            },
            {
                "name": "IMPACT",
                "start_frame": impact_peak,
                "end_frame": landing_start if landing_start > 0 else len(pose_sequence) - 1,
                "duration": (landing_start - impact_peak) / fps if landing_start > 0 else (len(pose_sequence) - impact_peak) / fps,
                "target_duration": constraints.get("landing", {}).get("duration", 0.39),
                "timing_score": calculate_timing_score((landing_start - impact_peak) / fps if landing_start > 0 else 0.39, 0.39, 0.05)
            }
        ]
    
    return phases

def detect_block_phases(pose_sequence: np.ndarray, velocities: Dict, fps: float, constraints: Dict) -> List[Dict]:
    """Detect block phases with Olympic timing"""
    
    phases = []
    
    # Find reaction and jump phases
    wrist_vel = np.array(velocities["wrist"]["linear_velocity"])
    
    # Reaction phase (initial movement)
    reaction_start = find_phase_start(wrist_vel, threshold=0.2, direction="increasing")
    
    # Penultimate step (loading phase)
    penultimate_peak = find_velocity_peak(wrist_vel, window_size=int(0.4 * fps))
    
    # Jump phase (maximum upward velocity)
    jump_peak = find_velocity_peak(wrist_vel[penultimate_peak:], direction="max")
    if jump_peak > 0:
        jump_peak += penultimate_peak
    
    if reaction_start >= 0 and penultimate_peak >= 0 and jump_peak >= 0:
        phases = [
            {
                "name": "REACTION",
                "start_frame": reaction_start,
                "end_frame": penultimate_peak,
                "duration": (penultimate_peak - reaction_start) / fps,
                "target_duration": 0.3,
                "timing_score": calculate_timing_score((penultimate_peak - reaction_start) / fps, 0.3, 0.05)
            },
            {
                "name": "PENULTIMATE",
                "start_frame": penultimate_peak,
                "end_frame": jump_peak,
                "duration": (jump_peak - penultimate_peak) / fps,
                "target_duration": 0.4,
                "timing_score": calculate_timing_score((jump_peak - penultimate_peak) / fps, 0.4, 0.1)
            }
        ]
    
    return phases

def detect_serve_phases(pose_sequence: np.ndarray, velocities: Dict, fps: float, constraints: Dict) -> List[Dict]:
    """Detect serve phases with Olympic timing"""
    
    phases = []
    
    # Find toss and contact phases
    wrist_vel = np.array(velocities["wrist"]["linear_velocity"])
    
    # Toss phase (upward wrist movement)
    toss_start = find_phase_start(wrist_vel, threshold=0.3, direction="increasing")
    
    # Loading phase (shoulder rotation)
    shoulder_ang_vel = np.array(velocities["shoulder"]["angular_velocity"])
    loading_peak = find_velocity_peak(shoulder_ang_vel, window_size=int(0.3 * fps))
    
    # Contact phase (maximum velocity)
    contact_peak = find_velocity_peak(wrist_vel[loading_peak:], direction="max")
    if contact_peak > 0:
        contact_peak += loading_peak
    
    if toss_start >= 0 and loading_peak >= 0 and contact_peak >= 0:
        phases = [
            {
                "name": "TOSS",
                "start_frame": toss_start,
                "end_frame": loading_peak,
                "duration": (loading_peak - toss_start) / fps,
                "target_duration": 0.3,
                "timing_score": calculate_timing_score((loading_peak - toss_start) / fps, 0.3, 0.1)
            },
            {
                "name": "LOADING",
                "start_frame": loading_peak,
                "end_frame": contact_peak,
                "duration": (contact_peak - loading_peak) / fps,
                "target_duration": 0.8,
                "timing_score": calculate_timing_score((contact_peak - loading_peak) / fps, 0.8, 0.1)
            }
        ]
    
    return phases

def detect_dig_phases(pose_sequence: np.ndarray, velocities: Dict, fps: float, constraints: Dict) -> List[Dict]:
    """Detect dig phases with Olympic timing"""
    
    phases = []
    
    # Find platform and recovery phases
    wrist_vel = np.array(velocities["wrist"]["linear_velocity"])
    
    # Platform formation (arms extending)
    platform_start = find_phase_start(wrist_vel, threshold=0.4, direction="increasing")
    
    # Contact phase (maximum velocity)
    contact_peak = find_velocity_peak(wrist_vel, window_size=int(0.2 * fps))
    
    # Recovery phase (return to ready position)
    recovery_start = find_phase_start(wrist_vel[contact_peak:], threshold=0.2, direction="decreasing")
    if recovery_start > 0:
        recovery_start += contact_peak
    
    if platform_start >= 0 and contact_peak >= 0:
        phases = [
            {
                "name": "PLATFORM",
                "start_frame": platform_start,
                "end_frame": contact_peak,
                "duration": (contact_peak - platform_start) / fps,
                "target_duration": 0.2,
                "timing_score": calculate_timing_score((contact_peak - platform_start) / fps, 0.2, 0.05)
            },
            {
                "name": "RECOVERY",
                "start_frame": contact_peak,
                "end_frame": recovery_start if recovery_start > 0 else len(pose_sequence) - 1,
                "duration": (recovery_start - contact_peak) / fps if recovery_start > 0 else 0.8,
                "target_duration": 0.8,
                "timing_score": calculate_timing_score((recovery_start - contact_peak) / fps if recovery_start > 0 else 0.8, 0.8, 0.1)
            }
        ]
    
    return phases

def find_phase_start(velocity_array: np.ndarray, threshold: float, direction: str = "increasing") -> int:
    """Find the start of a movement phase"""
    
    if len(velocity_array) < 3:
        return -1
    
    for i in range(1, len(velocity_array) - 1):
        if direction == "increasing":
            if velocity_array[i] > threshold and velocity_array[i] > velocity_array[i-1]:
                return i
        elif direction == "decreasing":
            if velocity_array[i] < threshold and velocity_array[i] < velocity_array[i-1]:
                return i
    
    return -1

def find_velocity_peak(velocity_array: np.ndarray, window_size: int = 10, direction: str = "max") -> int:
    """Find peak velocity within a window"""
    
    if len(velocity_array) < window_size:
        return -1
    
    if direction == "max":
        # Find global maximum
        return int(np.argmax(velocity_array))
    else:
        # Find first significant peak
        for i in range(window_size, len(velocity_array) - window_size):
            if velocity_array[i] > np.mean(velocity_array[i-window_size:i+window_size]) + 1.5 * np.std(velocity_array[i-window_size:i+window_size]):
                return i
    
    return -1

def calculate_timing_score(actual_duration: float, target_duration: float, tolerance: float) -> float:
    """Calculate timing accuracy score (0-1)"""
    
    deviation = abs(actual_duration - target_duration)
    
    if deviation <= tolerance:
        return 1.0 - (deviation / tolerance) * 0.3  # 0.7-1.0 for within tolerance
    else:
        return max(0.0, 1.0 - (deviation - tolerance) / target_duration)

def evaluate_temporal_accuracy(phases: List[Dict], constraints: Dict, technique: str) -> Dict:
    """Evaluate temporal accuracy against Olympic standards"""
    
    analysis = {
        "overall_timing_score": 0.0,
        "phase_scores": {},
        "critical_violations": [],
        "recommendations": []
    }
    
    if not phases:
        analysis["critical_violations"].append("No phases detected - technique too slow or incomplete")
        return analysis
    
    # Calculate overall timing score
    timing_scores = [phase.get("timing_score", 0.0) for phase in phases]
    analysis["overall_timing_score"] = np.mean(timing_scores) if timing_scores else 0.0
    
    # Evaluate each phase
    for phase in phases:
        phase_name = phase.get("name", "unknown")
        score = phase.get("timing_score", 0.0)
        duration = phase.get("duration", 0.0)
        target = phase.get("target_duration", 0.5)
        
        analysis["phase_scores"][phase_name] = {
            "score": score,
            "duration": duration,
            "target": target,
            "deviation": abs(duration - target)
        }
        
        # Check for critical violations
        if score < 0.5:
            analysis["critical_violations"].append(f"{phase_name} phase timing significantly off")
        
        # Add specific recommendations
        if phase_name == "REPULSION" and score < 0.7:
            analysis["recommendations"].append("Focus on penultimate step timing - practice approach rhythm")
        elif phase_name == "IMPACT" and score < 0.7:
            analysis["recommendations"].append("Work on arm swing timing - delay contact for maximum power")
    
    # Technique-specific recommendations
    if technique == "spike":
        if analysis["overall_timing_score"] < 0.7:
            analysis["recommendations"].append("Overall spike timing needs work - practice 3-step approach rhythm")
    elif technique == "dig":
        if len(analysis["critical_violations"]) > 0:
            analysis["recommendations"].append("Critical: Reception window exceeded - work on reaction time")
    
    return analysis