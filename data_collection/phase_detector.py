"""
Phase Detector — splits a pose sequence into movement phases.

For each technique we detect the key biomechanical phases from kinematics,
then return a per-frame phase label and a mapping of phase → frame range.

Spike phases:   APPROACH → TAKEOFF → ARM_COCK → CONTACT → FOLLOW_THROUGH
Serve phases:   STANCE → TOSS → ARM_COCK → CONTACT → FOLLOW_THROUGH
Block phases:   READY → STEP → JUMP → REACH → LAND
Dig phases:     READY → MOVE → LOW_POSITION → CONTACT → RECOVERY

Phase detection is purely kinematic — no ML needed.
We use joint velocity and position thresholds derived from the movement.
"""
import numpy as np
from typing import NamedTuple


class Phase(NamedTuple):
    name: str
    start: int   # inclusive
    end: int     # exclusive


def detect_phases(pose_seq: np.ndarray, technique: str) -> list[Phase]:
    """
    Detect movement phases from a (T, 17, 3) pose sequence.
    Returns list of Phase(name, start, end) in temporal order.
    """
    T = len(pose_seq)
    if T < 5:
        return [Phase("FULL_MOVEMENT", 0, T)]

    detectors = {
        "spike": _spike_phases,
        "serve": _serve_phases,
        "block": _block_phases,
        "dig":   _dig_phases,
    }
    fn = detectors.get(technique)
    if fn is None:
        return [Phase("FULL_MOVEMENT", 0, T)]
    return fn(pose_seq)


def phase_progress(phases: list[Phase], frame_idx: int) -> tuple[str, float]:
    """
    Given a frame index, return (phase_name, progress_within_phase [0..1]).
    """
    for ph in phases:
        if ph.start <= frame_idx < ph.end:
            span = max(ph.end - ph.start, 1)
            return ph.name, (frame_idx - ph.start) / span
    # past last phase
    last = phases[-1]
    return last.name, 1.0


def map_athlete_to_elite(
    athlete_phases: list[Phase],
    elite_len: int,
    frame_idx: int,
) -> int:
    """
    Map an athlete frame index to the corresponding elite sequence frame index.
    Uses phase-proportional mapping so CONTACT maps to CONTACT, not just frame N.
    """
    ph_name, progress = phase_progress(athlete_phases, frame_idx)

    # Find the same phase in the elite sequence (uniform distribution)
    n_phases = len(athlete_phases)
    phase_names = [p.name for p in athlete_phases]
    try:
        ph_idx = phase_names.index(ph_name)
    except ValueError:
        ph_idx = 0

    # Elite phase boundaries (uniform split)
    elite_phase_start = int(ph_idx / n_phases * elite_len)
    elite_phase_end   = int((ph_idx + 1) / n_phases * elite_len)
    elite_frame = int(elite_phase_start + progress * (elite_phase_end - elite_phase_start))
    return int(np.clip(elite_frame, 0, elite_len - 1))


# ── Technique-specific phase detectors ───────────────────────────────────────

def _spike_phases(pose_seq: np.ndarray) -> list[Phase]:
    T = len(pose_seq)
    # Hip velocity (approach speed proxy)
    hip = (pose_seq[:, 11, :2] + pose_seq[:, 12, :2]) / 2
    hip_vel = np.linalg.norm(np.diff(hip, axis=0), axis=1)  # (T-1,)

    # Ankle Y (jump height proxy) — higher Y = higher in frame (depends on coord)
    ankle_y = pose_seq[:, 15, 1]

    # Wrist Y (arm position)
    wrist_y = pose_seq[:, 10, 1]

    # Approach: high hip velocity in first ~40% of sequence
    approach_end = _first_local_min(hip_vel, start=int(T * 0.1), end=int(T * 0.5)) or int(T * 0.35)

    # Takeoff: ankle Y starts rising (or falling depending on coord system)
    ankle_vel = np.abs(np.diff(ankle_y))
    takeoff_start = approach_end
    takeoff_end   = _first_peak(ankle_vel, start=approach_end, end=int(T * 0.65)) or int(T * 0.55)

    # Contact: wrist at highest/lowest point (peak arm extension)
    contact_frame = _global_extremum(wrist_y, start=takeoff_end, end=int(T * 0.85))
    contact_start = takeoff_end
    contact_end   = min(contact_frame + max((contact_frame - contact_start) // 3, 2), T - 1)

    return [
        Phase("APPROACH",        0,              approach_end),
        Phase("TAKEOFF",         approach_end,   takeoff_end),
        Phase("ARM_COCK",        takeoff_end,    contact_start),
        Phase("CONTACT",         contact_start,  contact_end),
        Phase("FOLLOW_THROUGH",  contact_end,    T),
    ]


def _serve_phases(pose_seq: np.ndarray) -> list[Phase]:
    T = len(pose_seq)
    wrist_y = pose_seq[:, 10, 1]
    wrist_vel = np.abs(np.diff(wrist_y))

    toss_end    = _first_peak(wrist_vel, start=int(T * 0.1), end=int(T * 0.4)) or int(T * 0.3)
    arm_cock    = int(T * 0.5)
    contact     = _global_extremum(wrist_y, start=arm_cock, end=int(T * 0.8))
    contact_end = min(contact + max((contact - arm_cock) // 3, 2), T - 1)

    return [
        Phase("STANCE",         0,           int(T * 0.15)),
        Phase("TOSS",           int(T*0.15), toss_end),
        Phase("ARM_COCK",       toss_end,    arm_cock),
        Phase("CONTACT",        arm_cock,    contact_end),
        Phase("FOLLOW_THROUGH", contact_end, T),
    ]


def _block_phases(pose_seq: np.ndarray) -> list[Phase]:
    T = len(pose_seq)
    ankle_y = pose_seq[:, 15, 1]
    ankle_vel = np.abs(np.diff(ankle_y))

    step_end  = _first_peak(ankle_vel, start=int(T * 0.1), end=int(T * 0.4)) or int(T * 0.3)
    jump_end  = _first_local_min(ankle_vel, start=step_end, end=int(T * 0.65)) or int(T * 0.55)
    reach_end = int(T * 0.75)

    return [
        Phase("READY",  0,         int(T * 0.15)),
        Phase("STEP",   int(T*0.15), step_end),
        Phase("JUMP",   step_end,  jump_end),
        Phase("REACH",  jump_end,  reach_end),
        Phase("LAND",   reach_end, T),
    ]


def _dig_phases(pose_seq: np.ndarray) -> list[Phase]:
    T = len(pose_seq)
    hip_y = pose_seq[:, 11, 1]
    hip_vel = np.abs(np.diff(hip_y))

    move_end    = _first_peak(hip_vel, start=int(T * 0.1), end=int(T * 0.4)) or int(T * 0.3)
    low_end     = _global_extremum(hip_y, start=move_end, end=int(T * 0.7))
    contact_end = min(low_end + max((low_end - move_end) // 3, 2), T - 1)

    return [
        Phase("READY",        0,          int(T * 0.15)),
        Phase("MOVE",         int(T*0.15), move_end),
        Phase("LOW_POSITION", move_end,   low_end),
        Phase("CONTACT",      low_end,    contact_end),
        Phase("RECOVERY",     contact_end, T),
    ]


# ── Signal processing helpers ─────────────────────────────────────────────────

def _first_peak(signal: np.ndarray, start: int, end: int) -> int | None:
    end = min(end, len(signal))
    if start >= end:
        return None
    seg = signal[start:end]
    if len(seg) < 3:
        return start
    # find first local max
    for i in range(1, len(seg) - 1):
        if seg[i] > seg[i - 1] and seg[i] >= seg[i + 1]:
            return start + i
    return int(np.argmax(seg)) + start


def _first_local_min(signal: np.ndarray, start: int, end: int) -> int | None:
    end = min(end, len(signal))
    if start >= end:
        return None
    seg = signal[start:end]
    if len(seg) < 3:
        return start
    for i in range(1, len(seg) - 1):
        if seg[i] < seg[i - 1] and seg[i] <= seg[i + 1]:
            return start + i
    return int(np.argmin(seg)) + start


def _global_extremum(signal: np.ndarray, start: int, end: int) -> int:
    end = min(end, len(signal))
    if start >= end:
        return start
    seg = signal[start:end]
    return int(np.argmin(seg)) + start   # lower Y = higher in image
