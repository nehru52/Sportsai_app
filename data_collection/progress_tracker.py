"""
Layer 5 — Athlete Progress Tracking.
Stores session history per athlete, computes trends, detects plateaus,
flags injury risk patterns from kinematics over time.
"""
import json
import os
import numpy as np
from datetime import datetime

# Custom JSON encoder for numpy types
class NumpyEncoder(json.JSONEncoder):
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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRESS_DIR  = os.path.join(BASE_DIR, "data/progress")

# Metrics where a declining trend = injury risk
INJURY_RISK_METRICS = {
    "landing_balance":  ("lower", 0.6),   # below 0.6 = unstable landing
    "knee_bend":        ("higher", 150),  # above 150° = insufficient flexion
    "arm_cock_angle":   ("lower", 60),    # below 60° = shoulder impingement risk
}


def _athlete_path(athlete_id: str, technique: str) -> str:
    path = os.path.join(PROGRESS_DIR, athlete_id)
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, f"{technique}.json")


def save_session(athlete_id: str, technique: str, session: dict):
    """Append a session result to the athlete's history file."""
    path = _athlete_path(athlete_id, technique)
    history = load_history(athlete_id, technique)
    history.append({
        **session,
        "timestamp": datetime.now().isoformat(),
    })
    with open(path, "w") as f:
        json.dump(history, f, indent=2, cls=NumpyEncoder)


def load_history(athlete_id: str, technique: str) -> list:
    path = _athlete_path(athlete_id, technique)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def compute_trends(history: list) -> dict:
    """
    For each metric, compute direction of change over last 5 sessions.
    Returns {"metric": {"trend": "improving"|"declining"|"plateau", "delta": float}}
    """
    if len(history) < 2:
        return {}

    recent = history[-5:]
    trends = {}

    # Collect all metric names from most recent session
    if "metrics" not in recent[-1]:
        return {}

    for metric in recent[-1]["metrics"]:
        vals = [
            s["metrics"][metric]["value"]
            for s in recent
            if "metrics" in s and metric in s["metrics"]
        ]
        if len(vals) < 2:
            continue

        delta = vals[-1] - vals[0]
        if abs(delta) < 0.5:
            trend = "plateau"
        elif delta > 0:
            trend = "improving"
        else:
            trend = "declining"

        trends[metric] = {"trend": trend, "delta": round(delta, 3)}

    return trends


def check_injury_risk(history: list) -> list:
    """
    Scan last 3 sessions for injury risk patterns.
    Returns list of warning strings.
    """
    if not history:
        return []

    recent = history[-3:]
    warnings = []

    for metric, (direction, threshold) in INJURY_RISK_METRICS.items():
        vals = [
            s["metrics"][metric]["value"]
            for s in recent
            if "metrics" in s and metric in s["metrics"]
        ]
        if not vals:
            continue

        avg = sum(vals) / len(vals)
        if direction == "lower" and avg < threshold:
            warnings.append(f"{metric} averaging {avg:.1f} — below safe threshold of {threshold}")
        elif direction == "higher" and avg > threshold:
            warnings.append(f"{metric} averaging {avg:.1f} — above safe threshold of {threshold}")

    return warnings


def get_progress_report(athlete_id: str, technique: str) -> dict:
    """
    Full progress report for an athlete on a technique.

    Returns:
        {
          "sessions_total": int,
          "last_verdict": str,
          "trends": {...},
          "injury_risk": [...],
          "best_session": {...},
          "history": [...]
        }
    """
    history = load_history(athlete_id, technique)
    if not history:
        return {"sessions_total": 0, "message": "No sessions recorded yet"}

    verdicts = [s.get("verdict") for s in history if s.get("verdict")]
    best = max(
        (s for s in history if "metrics" in s),
        key=lambda s: sum(1 for m in s["metrics"].values() if m["status"] == "GOOD"),
        default=None,
    )

    return {
        "sessions_total": len(history),
        "last_verdict": verdicts[-1] if verdicts else None,
        "trends": compute_trends(history),
        "injury_risk": check_injury_risk(history),
        "best_session": best,
        "history": history,
    }
