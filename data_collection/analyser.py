"""
Shared biomechanics analyser for all volleyball techniques.
Replaces spike_analyser.py, serve_analyser.py, block_analyser.py, dig_analyser.py.
"""
import os
import json
import numpy as np

BASE_DIR = "C:/sportsai-backend"
METADATA_PATH = os.path.join(BASE_DIR, "data/pose_data/volleyball/metadata.json")

# Per-technique metric config: metric -> "higher" | "lower"
TECHNIQUE_CONFIG: dict[str, dict[str, str]] = {
    "spike": {
        "arm_cock_angle":  "higher",
        "jump_height":     "higher",
        "approach_speed":  "higher",
        "contact_point":   "lower",
        "follow_through":  "higher",
    },
    "serve": {
        "toss_height":        "higher",
        "step_timing":        "lower",
        "shoulder_rotation":  "higher",
        "wrist_snap":         "higher",
        "body_lean":          "lower",
    },
    "block": {
        "reaction_time":     "lower",
        "penultimate_step":  "higher",
        "hand_position":     "higher",
        "shoulder_width":    "higher",
        "landing_balance":   "higher",
    },
    "dig": {
        "platform_angle":      "higher",
        "knee_bend":           "lower",
        "hip_drop":            "higher",
        "arm_extension":       "lower",
        "recovery_position":   "lower",
    },
}


def load_biomechanics_by_level(technique: str) -> dict:
    """Load all biomechanics records for a technique, grouped by skill level."""
    if technique not in TECHNIQUE_CONFIG:
        raise ValueError(f"Unknown technique: {technique}")

    with open(METADATA_PATH) as f:
        metadata = json.load(f)

    data: dict[str, list] = {"elite": [], "advanced": [], "intermediate": []}
    bio_dir = os.path.join(BASE_DIR, "data/pose_data/volleyball", technique)

    for record in metadata["processed"]:
        if record.get("technique") != technique:
            continue
        level = record.get("skill_level")
        if level not in data:
            continue
        bio_file = os.path.join(bio_dir, record["biomechanics_file"])
        if not os.path.exists(bio_file):
            continue
        with open(bio_file) as f:
            data[level].append(json.load(f))

    return data


def compute_thresholds(data: dict, technique: str) -> dict:
    """Compute elite mean/std and intermediate mean per metric."""
    metrics = list(TECHNIQUE_CONFIG[technique].keys())
    thresholds = {}
    for metric in metrics:
        elite_vals = [d[metric] for d in data["elite"] if metric in d]
        inter_vals = [d[metric] for d in data["intermediate"] if metric in d]
        if elite_vals and inter_vals:
            thresholds[metric] = {
                "elite_mean": round(float(np.mean(elite_vals)), 3),
                "elite_std":  round(float(np.std(elite_vals)), 3),
                "intermediate_mean": round(float(np.mean(inter_vals)), 3),
            }
    return thresholds


def analyse_biomechanics(bio: dict, thresholds: dict, technique: str) -> dict:
    """Compare a single biomechanics dict against elite thresholds."""
    config = TECHNIQUE_CONFIG[technique]
    report = {}
    for metric, direction in config.items():
        if metric not in bio or metric not in thresholds:
            continue
        val = bio[metric]
        t = thresholds[metric]
        elite_mean, elite_std = t["elite_mean"], t["elite_std"]

        if direction == "higher":
            good = val >= (elite_mean - elite_std * 0.25)
        else:
            good = val <= (elite_mean + elite_std * 0.25)

        report[metric] = {
            "value": round(val, 3),
            "elite_mean": elite_mean,
            "status": "GOOD" if good else "NEEDS IMPROVEMENT",
        }
    return report


def load_thresholds(technique: str) -> dict:
    """Convenience: load data and compute thresholds in one call."""
    return compute_thresholds(load_biomechanics_by_level(technique), technique)
