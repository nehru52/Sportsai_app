"""
Pose extraction from video using YOLO11x-pose (2D) +
AthletePose3D MotionAGFormer (2D → real 3D lifting).
Biomechanics computed via kinematics.py (Butterworth-filtered joint angles + velocities).
Both models are loaded once and cached for the process lifetime.
"""
import numpy as np
import os

YOLO_MODEL_PATH = os.path.join(os.path.dirname(__file__), "yolo11x-pose.pt")
CONFIDENCE_THRESHOLD = 0.7

_yolo_model = None


import torch as _torch
_DEVICE = "cuda" if _torch.cuda.is_available() else "cpu"

def _get_yolo():
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO
        _yolo_model = YOLO(YOLO_MODEL_PATH)
        print(f"[pose_extractor] YOLO loaded — using {_DEVICE.upper()}")
    return _yolo_model


def _calc_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ba, bc = a - b, c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def _angles_over_time(pose_seq: np.ndarray, i: int, j: int, k: int) -> np.ndarray:
    """Vectorised joint angles for all frames."""
    ba = pose_seq[:, i] - pose_seq[:, j]
    bc = pose_seq[:, k] - pose_seq[:, j]
    cosine = np.einsum("fd,fd->f", ba, bc) / (
        np.linalg.norm(ba, axis=1) * np.linalg.norm(bc, axis=1) + 1e-8
    )
    return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))


def _person_height_px(pose_seq: np.ndarray) -> float:
    """
    Estimate person height in pixels from pose sequence.
    Uses median distance from nose (0) to midpoint of ankles (15, 16).
    This is the normalisation factor for all pixel-based metrics.
    """
    nose   = pose_seq[:, 0, :2]
    ankles = (pose_seq[:, 15, :2] + pose_seq[:, 16, :2]) / 2
    heights = np.linalg.norm(nose - ankles, axis=1)
    # Use 90th percentile — avoids crouched frames pulling it down
    h = float(np.percentile(heights[heights > 10], 90))
    return max(h, 50.0)   # safety floor — never divide by tiny number


def _select_person(results, technique: str, img_h: int,
                   locked_centre: tuple | None = None) -> int:
    """
    Select the correct person for this technique.

    If locked_centre is provided (x, y pixel position), pick whoever is
    closest to it — this locks tracking to the same person across frames.

    Otherwise score by technique:
    spike/block → most airborne (ankles high) + wrist height fallback
    dig         → lowest hip
    serve       → wrist above head
    """
    kps   = results[0].keypoints
    boxes = results[0].boxes
    n     = len(kps.conf)

    if n == 1:
        return 0

    # If we have a locked centre, always pick the closest person to it
    if locked_centre is not None and boxes is not None and boxes.xywh is not None:
        lx, ly = locked_centre
        best, best_dist = 0, float('inf')
        for i in range(n):
            cx = float(boxes.xywh[i, 0])
            cy = float(boxes.xywh[i, 1])
            dist = (cx - lx) ** 2 + (cy - ly) ** 2
            if dist < best_dist:
                best_dist = dist
                best = i
        return best

    scores = []
    for i in range(n):
        kp   = kps.xy[i].cpu().numpy()
        conf_kp = kps.conf[i].cpu().numpy()   # (17,) per-joint confidence
        conf = float(kps.conf[i].mean())
        if conf < 0.25:
            scores.append(-1)
            continue

        if technique in ("spike", "block"):
            # Ankle confidence — if low, fall back to wrist only
            ankle_conf = float((conf_kp[15] + conf_kp[16]) / 2)
            wrist_conf = float((conf_kp[9]  + conf_kp[10]) / 2)

            if ankle_conf > 0.3:
                ankle_y  = (kp[15, 1] + kp[16, 1]) / 2
                airborne = (img_h - ankle_y) / img_h
            else:
                # Ankles not visible — estimate from hip position
                hip_y    = (kp[11, 1] + kp[12, 1]) / 2
                airborne = (img_h - hip_y) / img_h * 0.6   # reduced weight

            if wrist_conf > 0.3:
                wrist_y = min(kp[9, 1], kp[10, 1])
                reach   = (img_h - wrist_y) / img_h
            else:
                reach = 0.0

            score = (airborne * 0.65 + reach * 0.35) * conf

        elif technique == "dig":
            hip_y = (kp[11, 1] + kp[12, 1]) / 2
            score = (hip_y / img_h) * conf

        elif technique == "serve":
            wrist_y = min(kp[9, 1], kp[10, 1])
            nose_y  = kp[0, 1]
            above   = 1.0 if wrist_y < nose_y else 0.0
            score   = above * conf

        else:
            w = boxes.xywh[i, 2].item() if boxes is not None else 1
            h = boxes.xywh[i, 3].item() if boxes is not None else 1
            score = w * h * conf

        scores.append(score)

    return int(np.argmax(scores)) if scores else 0


def _extract_biomechanics(pose_seq: np.ndarray, technique: str, fps: float) -> dict:
    """
    Technique-specific biomechanics normalised by person height.
    All distance-based metrics are expressed as a ratio of body height (0.0–2.0 range).
    Angle-based metrics stay in degrees.
    Time-based metrics stay in seconds.
    This makes every metric camera-distance independent.
    """
    from kinematics import extract_kinematics

    bio = {}
    H = _person_height_px(pose_seq)   # normalisation factor

    if technique == "spike":
        # Angles — degrees, no normalisation needed
        angles = _angles_over_time(pose_seq, 6, 8, 10)
        bio["arm_cock_angle"] = float(np.max(angles))
        bio["follow_through"] = float(np.std(angles) * 2)

        # jump_height: ankle vertical travel / body height → ratio
        # Elite ~0.35–0.55 (35–55% of body height)
        ankle_y = pose_seq[:, 15, 1]
        bio["jump_height"] = float((ankle_y.max() - ankle_y.min()) / H)

        # approach_speed: hip displacement per frame / body height → body-heights per frame
        hip_pos = pose_seq[:, 11, :2]
        bio["approach_speed"] = float(
            np.mean(np.linalg.norm(np.diff(hip_pos, axis=0), axis=1)) / H
        )

        # contact_point: wrist-to-hip distance / body height → ratio
        # Lower = better (hand closer to ideal contact zone)
        hip_center = (pose_seq[:, 11] + pose_seq[:, 12]) / 2
        bio["contact_point"] = float(
            np.linalg.norm(pose_seq[:, 10, :2] - hip_center[:, :2], axis=1).min() / H
        )

    elif technique == "serve":
        mid = len(pose_seq) // 2
        bio["shoulder_rotation"] = _calc_angle(pose_seq[mid, 5], pose_seq[mid, 11], pose_seq[mid, 6])

        # toss_height: wrist vertical travel / body height
        wrist_y = pose_seq[:, 10, 1]
        bio["toss_height"] = float((wrist_y.max() - wrist_y.min()) / H)

        bio["body_lean"]   = float(np.mean(_angles_over_time(pose_seq, 0, 11, 15)))
        bio["step_timing"] = float(len(pose_seq) / fps)
        bio["wrist_snap"]  = float(np.std(pose_seq[:, 10, 0]) / H)

    elif technique == "block":
        # hand_position: how high wrist gets above hip / body height
        hip_y   = pose_seq[:, 11, 1]
        wrist_y = pose_seq[:, 10, 1]
        bio["hand_position"] = float((hip_y.mean() - wrist_y.min()) / H)

        # shoulder_width: shoulder span / body height
        bio["shoulder_width"] = float(
            np.mean(np.linalg.norm(pose_seq[:, 5, :2] - pose_seq[:, 6, :2], axis=1)) / H
        )

        bio["reaction_time"]    = float(len(pose_seq) / fps * 0.3)
        bio["penultimate_step"] = float(
            np.linalg.norm(pose_seq[-2, 15, :2] - pose_seq[-3, 15, :2]) / H
        )
        bio["landing_balance"]  = float(1.0 - np.std(pose_seq[-5:, 15, 1]) / H)

    elif technique == "dig":
        bio["knee_bend"]     = float(np.min(_angles_over_time(pose_seq, 11, 13, 15)))
        bio["arm_extension"] = float(np.mean(_angles_over_time(pose_seq, 5, 7, 9)))

        # hip_drop: hip vertical travel / body height
        hip_y = pose_seq[:, 11, 1]
        bio["hip_drop"] = float((hip_y.max() - hip_y.min()) / H)

        # platform_angle: forearm span / body height
        bio["platform_angle"] = float(
            np.mean(np.linalg.norm(pose_seq[:, 9, :2] - pose_seq[:, 10, :2], axis=1)) / H
        )
        bio["recovery_position"] = float(len(pose_seq) / fps)

    else:
        raise ValueError(f"Unknown technique: {technique}")

    bio.update(extract_kinematics(pose_seq, fps))
    return bio


def extract_pose(video_path: str, technique: str, skip_quality_check: bool = False) -> dict:
    import cv2
    from pose_3d_lifter import lift_to_3d
    from video_quality import check_video_quality
    from action_localiser import localise_technique, extract_clip

    # ── Quality gate ──────────────────────────────────────────────────────────
    if not skip_quality_check:
        quality = check_video_quality(video_path)
        if not quality.ok:
            raise ValueError(f"VIDEO_QUALITY_FAIL:{quality.to_dict()}")

    # ── Auto-clip: find the actual technique window ───────────────────────────
    # This solves the "running before the spike" problem.
    # We detect where the technique actually starts/ends and extract only that.
    localisation = localise_technique(video_path, technique)
    clip_confidence = localisation["confidence"]

    # If we found a clear window (not full-video fallback), extract the clip
    analysis_path = video_path
    tmp_clip_path = None
    if clip_confidence >= 0.55 and localisation["method"] != "full_video_fallback:insufficient_pose_data":
        tmp_clip_path = video_path + "_clip.mp4"
        extract_clip(
            video_path,
            localisation["start_frame"],
            localisation["end_frame"],
            tmp_clip_path,
        )
        analysis_path = tmp_clip_path

    try:
        yolo = _get_yolo()
        cap = cv2.VideoCapture(analysis_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        img_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        img_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        pose2d_frames, conf_frames, confidences = [], [], []

        locked_centre = None   # set after first confident detection
        LOCK_AFTER    = 3      # lock person after this many frames

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            results = yolo(frame, verbose=False, device=_DEVICE)
            if not results or results[0].keypoints is None:
                continue
            kps   = results[0].keypoints
            boxes = results[0].boxes
            if kps.conf is None or len(kps.conf) == 0:
                continue

            best_idx = _select_person(results, technique, img_h, locked_centre)
            conf = float(kps.conf[best_idx].mean())
            if conf < CONFIDENCE_THRESHOLD:
                continue

            xy      = kps.xy[best_idx].cpu().numpy()
            kp_conf = kps.conf[best_idx].cpu().numpy()
            pose2d_frames.append(xy)
            conf_frames.append(kp_conf)
            confidences.append(conf)

            # Lock to this person's centre after enough frames
            if locked_centre is None and len(pose2d_frames) >= LOCK_AFTER:
                if boxes is not None and boxes.xywh is not None and best_idx < len(boxes.xywh):
                    locked_centre = (
                        float(boxes.xywh[best_idx, 0]),
                        float(boxes.xywh[best_idx, 1]),
                    )

        cap.release()

        if len(pose2d_frames) < 5:
            raise ValueError(f"Too few valid frames ({len(pose2d_frames)}) — try a clearer video with the full technique visible")

        pose2d   = np.array(pose2d_frames)   # (T, 17, 2) — raw pixel coords
        kp_confs = np.array(conf_frames)
        pose_seq = lift_to_3d(pose2d, img_w, img_h, kp_confs)

        return {
            "pose_sequence_3d":   pose_seq,
            "pose_sequence_2d":   pose2d,     # raw YOLO pixel coords for overlay
            "biomechanics":       _extract_biomechanics(pose_seq, technique, fps),
            "average_confidence": round(float(np.mean(confidences)), 4),
            "localisation":       localisation,
        }

    finally:
        # Clean up temp clip file
        if tmp_clip_path and os.path.exists(tmp_clip_path):
            os.remove(tmp_clip_path)
