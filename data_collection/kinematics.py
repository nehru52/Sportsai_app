"""
Biomechanical kinematics: joint angles + joint velocities.
Adapted from models/AthletePose3D/stats_test/get_kinematics.py.

Uses Butterworth low-pass filter (8Hz cutoff) to smooth noisy pose data —
same methodology as the AthletePose3D paper.

Keypoint index convention (COCO 17-point):
  0:nose  1:l_eye  2:r_eye  3:l_ear  4:r_ear
  5:l_shoulder  6:r_shoulder  7:l_elbow  8:r_elbow
  9:l_wrist  10:r_wrist  11:l_hip  12:r_hip
  13:l_knee  14:r_knee  15:l_ankle  16:r_ankle
"""
import numpy as np
from scipy.signal import butter, filtfilt

# Joints to compute angles for: (proximal, joint, distal)
ANGLE_TRIPLETS = {
    "right_knee":    (12, 14, 16),
    "left_knee":     (11, 13, 15),
    "right_elbow":   (6,  8,  10),
    "left_elbow":    (5,  7,  9),
    "right_hip":     (6,  12, 14),
    "left_hip":      (5,  11, 13),
    "right_shoulder": (8,  6,  12),
    "left_shoulder":  (7,  5,  11),
}

_BUTTER_ORDER = 4
_CUTOFF_HZ = 6.0  # Lowered from 8.0 Hz for stronger smoothing (removes more jitter)


def _butter_filter(data: np.ndarray, fps: float) -> np.ndarray:
    """Apply zero-phase Butterworth low-pass filter along axis=0 (time)."""
    nyquist = 0.5 * fps
    normal_cutoff = _CUTOFF_HZ / nyquist
    # If signal too short for filter, return as-is
    if data.shape[0] < (_BUTTER_ORDER * 3 + 1):
        return data
    b, a = butter(_BUTTER_ORDER, normal_cutoff, btype="low", analog=False)
    return filtfilt(b, a, data, axis=0)


def compute_joint_angles(pose_seq: np.ndarray, fps: float = 30.0) -> dict:
    """
    Compute filtered joint angles for each frame.

    Args:
        pose_seq: (T, 17, 3) array of keypoints
        fps: video frame rate

    Returns:
        dict of joint_name -> np.ndarray shape (T,) in degrees
    """
    angles = {}
    for name, (p1, p2, p3) in ANGLE_TRIPLETS.items():
        vec1 = pose_seq[:, p1] - pose_seq[:, p2]
        vec2 = pose_seq[:, p3] - pose_seq[:, p2]
        norm1 = np.linalg.norm(vec1, axis=1, keepdims=True)
        norm2 = np.linalg.norm(vec2, axis=1, keepdims=True)
        cos_theta = np.sum(vec1 * vec2, axis=1) / (
            (norm1 * norm2).squeeze() + 1e-8
        )
        raw = np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0)))
        angles[name] = _butter_filter(raw, fps)
    return angles


def compute_joint_velocities(pose_seq: np.ndarray, fps: float = 30.0) -> np.ndarray:
    """
    Compute filtered joint velocities (mm/s equivalent in pose units).

    Args:
        pose_seq: (T, 17, 3)
        fps: video frame rate

    Returns:
        (T-1, 17) velocity magnitudes per joint per frame
    """
    dt = 1.0 / fps
    diff = np.diff(pose_seq, axis=0)                          # (T-1, 17, 3)
    speed = np.linalg.norm(diff, axis=2) / dt                 # (T-1, 17)
    # filter each joint's velocity trace
    filtered = np.zeros_like(speed)
    for j in range(speed.shape[1]):
        filtered[:, j] = _butter_filter(speed[:, j], fps)
    return filtered


def extract_kinematics(pose_seq: np.ndarray, fps: float = 30.0) -> dict:
    """
    Full kinematics extraction: angles + velocities + summary stats.

    Returns dict ready to merge into biomechanics output.
    """
    angles = compute_joint_angles(pose_seq, fps)
    velocities = compute_joint_velocities(pose_seq, fps)

    summary = {}
    for name, angle_seq in angles.items():
        summary[f"{name}_angle_mean"] = round(float(np.mean(angle_seq)), 3)
        summary[f"{name}_angle_min"]  = round(float(np.min(angle_seq)), 3)
        summary[f"{name}_angle_max"]  = round(float(np.max(angle_seq)), 3)

    # Peak velocity per joint (averaged across all joints = overall athleticism proxy)
    summary["peak_joint_velocity"] = round(float(np.max(velocities)), 3)
    summary["mean_joint_velocity"]  = round(float(np.mean(velocities)), 3)

    return summary
