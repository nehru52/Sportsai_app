"""
Action Localiser — finds the exact frame range of a technique in a raw video.

Problem: users upload full clips with warmup, running, waiting, then the actual
technique. Biomechanics analysis on the full clip gives garbage results because
the approach speed, jump height baseline, and phase detection all get polluted
by the irrelevant footage.

Solution: detect the frame range [start, end] where the technique actually occurs,
then extract only that segment for analysis.

How it works (no extra model needed — uses what we already have):
1. Run YOLO pose on sampled frames to get joint positions
2. Compute joint velocity signal — high velocity = movement happening
3. Find the peak activity window (where the technique is)
4. Use technique-specific signatures to refine:
   - spike: look for rapid wrist elevation followed by downward snap
   - serve: look for wrist rising above head then contact
   - block: look for rapid upward arm extension
   - dig: look for rapid hip drop

This is purely kinematic — fast, no extra model, works offline.
"""
import numpy as np
import os
from typing import Optional

import torch as _torch
_DEVICE = "cuda" if _torch.cuda.is_available() else "cpu"
YOLO_MODEL_PATH = os.path.join(os.path.dirname(__file__), "yolo11x-pose.pt")
SAMPLE_RATE     = 1      # analyse every Nth frame for speed
MIN_CLIP_FRAMES = 20     # minimum frames for a valid technique clip
MAX_CLIP_FRAMES = 300    # maximum — anything longer is probably not a single technique
PADDING_FRAMES  = 25     # extra frames before/after detected window — more context

_yolo = None


def _get_yolo():
    global _yolo
    if _yolo is None:
        from ultralytics import YOLO
        _yolo = YOLO(YOLO_MODEL_PATH)
    return _yolo


def localise_technique(
    video_path: str,
    technique: str,
) -> dict:
    """
    Find the frame range where the technique occurs in the video.

    Returns:
        {
            "start_frame": int,
            "end_frame": int,
            "confidence": float,   # 0-1, how confident we are this is the right window
            "total_frames": int,
            "method": str,         # which detection method fired
        }

    If no clear technique window found, returns the full video range with low confidence.
    """
    import cv2

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Sample frames and extract keypoints
    keypoints_by_frame = {}
    frame_idx = 0

    yolo = _get_yolo()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % SAMPLE_RATE == 0:
            results = yolo(frame, verbose=False, device=_DEVICE)
            if results and results[0].keypoints is not None:
                kps = results[0].keypoints
                if kps.conf is not None and len(kps.conf) > 0:
                    best = int(kps.conf.mean(dim=1).argmax())
                    xy = kps.xy[best].cpu().numpy()   # (17, 2)
                    keypoints_by_frame[frame_idx] = xy
        frame_idx += 1

    cap.release()

    if len(keypoints_by_frame) < 5:
        return _full_video_fallback(total_frames, "insufficient_pose_data")

    # Build dense keypoint array (interpolate missing frames)
    frames_with_kp = sorted(keypoints_by_frame.keys())
    kp_array = np.array([keypoints_by_frame[f] for f in frames_with_kp])  # (N, 17, 2)

    # Compute joint velocity signal
    velocity = _joint_velocity_signal(kp_array)   # (N-1,)

    # Find technique window using technique-specific detector
    detectors = {
        "spike": _detect_spike_window,
        "serve": _detect_serve_window,
        "block": _detect_block_window,
        "dig":   _detect_dig_window,
    }
    detector = detectors.get(technique, _detect_generic_window)
    result = detector(kp_array, velocity, frames_with_kp, fps)

    if result is None:
        # Fall back to peak activity window
        result = _detect_generic_window(kp_array, velocity, frames_with_kp, fps)

    if result is None:
        return _full_video_fallback(total_frames, "no_technique_detected")

    start_frame, end_frame, confidence, method = result

    # Add padding
    start_frame = max(0, start_frame - PADDING_FRAMES)
    end_frame   = min(total_frames - 1, end_frame + PADDING_FRAMES)

    # Sanity check clip length
    clip_len = end_frame - start_frame
    if clip_len < MIN_CLIP_FRAMES:
        return _full_video_fallback(total_frames, "clip_too_short")

    return {
        "start_frame": int(start_frame),
        "end_frame":   int(end_frame),
        "confidence":  round(confidence, 3),
        "total_frames": total_frames,
        "clip_frames":  int(end_frame - start_frame),
        "clip_duration_sec": round((end_frame - start_frame) / fps, 2),
        "method": method,
    }


def extract_clip(
    video_path: str,
    start_frame: int,
    end_frame: int,
    output_path: str,
) -> str:
    """
    Extract frames [start_frame, end_frame] from video and save as new MP4.
    Returns output_path.
    """
    import cv2

    cap = cv2.VideoCapture(video_path)
    fps   = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    frame_idx = start_frame

    while frame_idx <= end_frame:
        ret, frame = cap.read()
        if not ret:
            break
        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()
    return output_path


# ── Technique-specific detectors ─────────────────────────────────────────────

def _detect_spike_window(kp_array, velocity, frame_indices, fps):
    """
    Spike signature:
    1. High hip velocity (approach run) — but we want AFTER this
    2. Rapid wrist elevation (arm swing up)
    3. Peak wrist height (contact point)
    4. Rapid wrist descent (follow-through)

    We find the wrist peak and work backwards/forwards from there.
    """
    wrist_y = kp_array[:, 10, 1]   # right wrist Y (lower = higher in frame)
    hip_y   = kp_array[:, 11, 1]

    # Find the frame where wrist is highest (lowest Y value = highest in image)
    contact_idx = int(np.argmin(wrist_y))

    # Approach starts where hip velocity first spikes significantly
    hip_vel = np.abs(np.diff(hip_y))
    threshold = np.percentile(hip_vel, 70)

    # Find approach start — last time hip velocity was LOW before contact
    approach_start = 0
    for i in range(contact_idx - 1, -1, -1):
        if i < len(hip_vel) and hip_vel[i] < threshold * 0.4:
            approach_start = i
            break

    # Follow-through ends where wrist velocity drops back to low
    wrist_vel = np.abs(np.diff(wrist_y))
    follow_end = min(contact_idx + int(fps * 0.8), len(kp_array) - 1)
    for i in range(contact_idx, min(contact_idx + int(fps * 1.2), len(wrist_vel))):
        if wrist_vel[i] < np.percentile(wrist_vel, 30):
            follow_end = i + 1
            break

    if follow_end <= approach_start:
        return None

    start_f = frame_indices[approach_start]
    end_f   = frame_indices[min(follow_end, len(frame_indices) - 1)]
    confidence = 0.85 if (follow_end - approach_start) > 10 else 0.6

    return start_f, end_f, confidence, "spike_wrist_peak"


def _detect_serve_window(kp_array, velocity, frame_indices, fps):
    """
    Serve signature: wrist rises above head (toss), then contact, then follow-through.
    """
    wrist_y  = kp_array[:, 10, 1]
    nose_y   = kp_array[:, 0, 1]

    # Find where wrist goes above nose level (arm raised for serve)
    above_head = wrist_y < nose_y   # True when wrist is above nose in image coords
    if not above_head.any():
        return None

    first_above = int(np.argmax(above_head))
    contact_idx = int(np.argmin(wrist_y[first_above:])) + first_above

    start_idx = max(0, first_above - int(fps * 0.5))
    end_idx   = min(len(kp_array) - 1, contact_idx + int(fps * 0.8))

    start_f = frame_indices[start_idx]
    end_f   = frame_indices[end_idx]
    return start_f, end_f, 0.80, "serve_wrist_above_head"


def _detect_block_window(kp_array, velocity, frame_indices, fps):
    """
    Block signature: rapid upward arm extension, hands above head.
    """
    wrist_y = kp_array[:, 10, 1]
    nose_y  = kp_array[:, 0, 1]

    wrist_vel = np.abs(np.diff(wrist_y))
    peak_vel_idx = int(np.argmax(wrist_vel))

    start_idx = max(0, peak_vel_idx - int(fps * 0.3))
    end_idx   = min(len(kp_array) - 1, peak_vel_idx + int(fps * 0.8))

    start_f = frame_indices[start_idx]
    end_f   = frame_indices[end_idx]
    return start_f, end_f, 0.75, "block_arm_velocity_peak"


def _detect_dig_window(kp_array, velocity, frame_indices, fps):
    """
    Dig signature: rapid hip drop (hip Y increases = going down).
    """
    hip_y = kp_array[:, 11, 1]
    hip_vel = np.diff(hip_y)   # positive = moving down

    # Find biggest downward hip movement
    drop_idx = int(np.argmax(hip_vel))

    start_idx = max(0, drop_idx - int(fps * 0.3))
    end_idx   = min(len(kp_array) - 1, drop_idx + int(fps * 1.0))

    start_f = frame_indices[start_idx]
    end_f   = frame_indices[end_idx]
    return start_f, end_f, 0.75, "dig_hip_drop"


def _detect_generic_window(kp_array, velocity, frame_indices, fps):
    """
    Fallback: find the window of highest overall joint activity.
    """
    if len(velocity) < 3:
        return None

    # Smooth velocity
    kernel = np.ones(5) / 5
    smooth_vel = np.convolve(velocity, kernel, mode="same")

    # Find peak
    peak = int(np.argmax(smooth_vel))
    threshold = np.percentile(smooth_vel, 60)

    # Expand from peak while velocity stays above threshold
    start_idx = peak
    for i in range(peak, -1, -1):
        if smooth_vel[i] < threshold:
            start_idx = i
            break

    end_idx = peak
    for i in range(peak, len(smooth_vel)):
        if smooth_vel[i] < threshold:
            end_idx = i
            break

    if end_idx <= start_idx:
        return None

    start_f = frame_indices[min(start_idx, len(frame_indices) - 1)]
    end_f   = frame_indices[min(end_idx,   len(frame_indices) - 1)]
    return start_f, end_f, 0.55, "generic_activity_peak"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _joint_velocity_signal(kp_array: np.ndarray) -> np.ndarray:
    """Overall joint velocity per frame — sum of all joint movements."""
    diff = np.diff(kp_array, axis=0)                    # (N-1, 17, 2)
    return np.linalg.norm(diff, axis=2).sum(axis=1)     # (N-1,)


def _full_video_fallback(total_frames: int, reason: str) -> dict:
    return {
        "start_frame": 0,
        "end_frame":   total_frames - 1,
        "confidence":  0.3,
        "total_frames": total_frames,
        "clip_frames":  total_frames,
        "clip_duration_sec": None,
        "method": f"full_video_fallback:{reason}",
    }
