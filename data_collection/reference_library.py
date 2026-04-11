"""
Reference Library — Elite pose sequence database.

Loads all elite .npy sequences for a technique, builds a canonical
"mean elite sequence" normalised to a fixed length (100 frames).
Used for side-by-side comparison in skeleton_overlay.render_side_by_side().

Key design: we normalise by PHASE, not by frame number.
A 400-frame elite sequence and a 100-frame athlete sequence both get
mapped to 100 canonical frames so the comparison is meaningful.
"""
import os
import json
import numpy as np
from scipy.interpolate import interp1d

BASE_DIR      = "C:/sportsai-backend"
METADATA_PATH = os.path.join(BASE_DIR, "data/pose_data/volleyball/metadata.json")
POSE_DIR      = os.path.join(BASE_DIR, "data/pose_data/volleyball")
CANONICAL_LEN = 100   # all sequences normalised to this length

_cache: dict[str, np.ndarray] = {}


def _time_normalise(seq: np.ndarray, target: int = CANONICAL_LEN) -> np.ndarray:
    """Resample (T, 17, 3) to (target, 17, 3) via linear interpolation."""
    T = len(seq)
    if T == target:
        return seq
    t_old = np.linspace(0, 1, T)
    t_new = np.linspace(0, 1, target)
    out = np.zeros((target, seq.shape[1], seq.shape[2]), dtype=np.float32)
    for j in range(seq.shape[1]):
        for d in range(seq.shape[2]):
            f = interp1d(t_old, seq[:, j, d], kind="linear")
            out[:, j, d] = f(t_new)
    return out


def _normalise_skeleton(seq: np.ndarray) -> np.ndarray:
    """
    Root-centre the skeleton so athlete height/distance doesn't affect comparison.
    Root = midpoint of hips (joints 11 + 12).
    Also scale by torso length so body size is normalised.
    """
    seq = seq.copy().astype(np.float32)
    root = (seq[:, 11] + seq[:, 12]) / 2   # (T, 3)

    # torso length = distance from root to nose (joint 0)
    torso = np.linalg.norm(seq[:, 0] - root, axis=1, keepdims=True)  # (T, 1)
    torso = np.maximum(torso, 1e-6)

    seq = seq - root[:, None, :]            # centre on hips
    seq = seq / torso[:, None, :]           # normalise scale
    return seq


def build_elite_reference(technique: str) -> np.ndarray:
    """
    Load all elite sequences for a technique, normalise each to CANONICAL_LEN,
    root-centre + scale-normalise, then average across all athletes.

    Returns: (CANONICAL_LEN, 17, 3) — the canonical elite pose sequence.
    Cached after first call.
    """
    if technique in _cache:
        return _cache[technique]

    with open(METADATA_PATH) as f:
        metadata = json.load(f)

    sequences = []
    for record in metadata["processed"]:
        if record.get("technique") != technique:
            continue
        if record.get("skill_level") != "elite":
            continue
        pose_file = os.path.join(POSE_DIR, technique, record["pose_file"])
        if not os.path.exists(pose_file):
            continue
        seq = np.load(pose_file).astype(np.float32)   # (T, 17, 3)
        if len(seq) < 10:
            continue
        seq = _normalise_skeleton(seq)
        seq = _time_normalise(seq, CANONICAL_LEN)
        sequences.append(seq)

    if not sequences:
        raise ValueError(f"No elite sequences found for technique '{technique}'")

    elite_mean = np.mean(sequences, axis=0)   # (CANONICAL_LEN, 17, 3)
    _cache[technique] = elite_mean
    return elite_mean


def get_elite_frame(technique: str, phase_progress: float) -> np.ndarray:
    """
    Get the elite reference frame at a given phase progress [0.0, 1.0].
    Returns (17, 3) normalised skeleton.
    """
    ref = build_elite_reference(technique)
    idx = int(np.clip(phase_progress * CANONICAL_LEN, 0, CANONICAL_LEN - 1))
    return ref[idx]


def get_elite_sequence(technique: str) -> np.ndarray:
    """Return the full (CANONICAL_LEN, 17, 3) elite reference sequence."""
    return build_elite_reference(technique)
