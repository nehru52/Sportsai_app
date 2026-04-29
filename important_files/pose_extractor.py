"""
Pose extraction from video using YOLO11x-pose (2D) +
AthletePose3D MotionAGFormer (2D → real 3D lifting).
Biomechanics computed via kinematics.py (Butterworth-filtered joint angles + velocities).
Both models are loaded once and cached for the process lifetime.
"""
import numpy as np
import os
import time
from typing import Optional, Tuple

YOLO_MODEL_PATH = os.path.join(os.path.dirname(__file__), "yolo11x-pose.pt")
CONFIDENCE_THRESHOLD = 0.3  # Lower threshold for short clips and fast movements

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


def get_court_zone(bbox_cx: float, frame_w: int) -> str:
    """Fix 2: Categorise court zone based on horizontal position."""
    ratio = bbox_cx / frame_w
    if ratio < 0.35: return 'back'
    elif ratio > 0.65: return 'front'
    else: return 'mid'


def save_ema_state(ema_dict: dict, path: str = "data/pose_data/ema_state.pkl"):
    """Fix 4 & Fix 2 (Pass 2): Persist EMA state with timestamps."""
    import pickle
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(ema_dict, f)


def load_ema_state(path: str = "data/pose_data/ema_state.pkl", max_age_days: int = 7) -> dict:
    """Fix 4 & Fix 2 (Pass 2): Load EMA state with TTL and capping."""
    import pickle
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                state = pickle.load(f)
            
            # Prune stale entries
            cutoff = time.time() - max_age_days * 86400
            initial_count = len(state)
            state = {k: v for k, v in state.items() if v.get('last_seen', 0) > cutoff}
            pruned = initial_count - len(state)
            
            # Hard cap at 500 entries
            if len(state) > 500:
                print("[WARNING] EMA state capped at 500 tracks — consider reducing max_age_days")
                sorted_items = sorted(state.items(), key=lambda x: x[1].get('last_seen', 0), reverse=True)
                state = dict(sorted_items[:500])
            
            print(f"EMA state loaded: {len(state)} active tracks, {pruned} stale tracks removed")
            return state
        except Exception as e:
            print(f"Error loading EMA state: {e}")
    return {}


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
    Estimate person scale using Trunk Length (Shoulders to Hips) instead of Nose-to-Ankle.
    Trunk length is highly stable during crouching, jumping, and diving.
    We multiply by ~2.5 to roughly approximate full body height for backward compatibility.
    """
    # Shoulders (5, 6) center
    shoulders = (pose_seq[:, 5, :2] + pose_seq[:, 6, :2]) / 2
    # Hips (11, 12) center
    hips = (pose_seq[:, 11, :2] + pose_seq[:, 12, :2]) / 2
    
    # Calculate trunk length for all frames
    trunk_lengths = np.linalg.norm(shoulders - hips, axis=1)
    
    # Use the median trunk length to ignore anomaly frames
    median_trunk = float(np.median(trunk_lengths[trunk_lengths > 10]))
    
    # Multiply by 2.5 to simulate full body height equivalent
    h = median_trunk * 2.5
    
    return max(h, 50.0) # Safety floor


def _select_person(results, technique: str, img_h: int, locked_centre: Optional[Tuple[float, float]] = None, prev_positions: Optional[dict] = None) -> int:
    """
    Intelligent person selection using Centroid Locking and spatial stability.
    """
    kps   = results[0].keypoints
    boxes = results[0].boxes
    
    if kps is None or kps.conf is None or len(kps.conf) == 0:
        return 0
        
    n = len(kps.conf)
    if n == 1:
        return 0

    # 1. STRICT CENTROID LOCKING
    if locked_centre is not None and boxes is not None and boxes.xywh is not None:
        lx, ly = locked_centre
        best_idx, min_dist = 0, float('inf')
        for i in range(min(n, len(boxes.xywh))):
            cx, cy = float(boxes.xywh[i, 0]), float(boxes.xywh[i, 1])
            dist = (cx - lx)**2 + (cy - ly)**2
            if dist < min_dist:
                min_dist = dist
                best_idx = i
        return best_idx

    # 2. FALLBACK HEURISTICS (If no lock provided)
    scores = []
    for i in range(n):
        kp   = kps.xy[i].cpu().numpy()
        conf = float(kps.conf[i].mean())
        
        if conf < 0.25:
            scores.append(-1.0)
            continue
            
        score = conf * 10.0 
        
        if prev_positions is not None and i in prev_positions:
            prev_hip_y = prev_positions[i]
            curr_hip_y = (kp[11, 1] + kp[12, 1]) / 2 
            vy = prev_hip_y - curr_hip_y
            if vy > 2:  
                score += (vy * 5.0) 
                
        if boxes is not None and boxes.xywh is not None and i < len(boxes.xywh):
            w, h = boxes.xywh[i, 2], boxes.xywh[i, 3]
            area = (w * h) / (img_h * img_h)
            score += (area * 20.0)

        scores.append(score)

    return int(np.argmax(scores)) if scores else 0


def _extract_biomechanics(pose_seq: np.ndarray, technique: str, fps: float) -> dict:
    from kinematics import extract_kinematics

    bio = {}
    H = _person_height_px(pose_seq)   # normalisation factor

    if technique == "spike":
        angles = _angles_over_time(pose_seq, 6, 8, 10)
        bio["arm_cock_angle"] = float(np.max(angles))
        bio["follow_through"] = float(np.std(angles) * 2)

        ankle_y = pose_seq[:, 15, 1]
        bio["jump_height"] = float((ankle_y.max() - ankle_y.min()) / H)

        hip_pos = pose_seq[:, 11, :2]
        bio["approach_speed"] = float(
            np.mean(np.linalg.norm(np.diff(hip_pos, axis=0), axis=1)) / H
        )

        hip_center = (pose_seq[:, 11] + pose_seq[:, 12]) / 2
        bio["contact_point"] = float(
            np.linalg.norm(pose_seq[:, 10, :2] - hip_center[:, :2], axis=1).min() / H
        )

    elif technique == "serve":
        mid = len(pose_seq) // 2
        bio["shoulder_rotation"] = _calc_angle(pose_seq[mid, 5], pose_seq[mid, 11], pose_seq[mid, 6])

        wrist_y = pose_seq[:, 10, 1]
        bio["toss_height"] = float((wrist_y.max() - wrist_y.min()) / H)

        bio["body_lean"]   = float(np.mean(_angles_over_time(pose_seq, 0, 11, 15)))
        bio["step_timing"] = float(len(pose_seq) / fps)
        bio["wrist_snap"]  = float(np.std(pose_seq[:, 10, 0]) / H)

    elif technique == "block":
        hip_y   = pose_seq[:, 11, 1]
        wrist_y = pose_seq[:, 10, 1]
        bio["hand_position"] = float((hip_y.mean() - wrist_y.min()) / H)

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

        hip_y = pose_seq[:, 11, 1]
        bio["hip_drop"] = float((hip_y.max() - hip_y.min()) / H)

        bio["platform_angle"] = float(
            np.mean(np.linalg.norm(pose_seq[:, 9, :2] - pose_seq[:, 10, :2], axis=1)) / H
        )
        bio["recovery_position"] = float(len(pose_seq) / fps)

    else:
        raise ValueError(f"Unknown technique: {technique}")

    bio.update(extract_kinematics(pose_seq, fps))
    return bio


def extract_pose(video_path: str, technique: str, skip_quality_check: bool = False, locked_centre: Optional[Tuple[float, float]] = None) -> dict:
    import cv2
    from pose_3d_lifter import lift_to_3d
    from video_quality import check_video_quality
    from action_localiser import localise_technique, extract_clip
    from court_detector import detect_court_in_frame, order_corners
    from utils.homography_corrector import HomographyCorrector
    from utils.kalman_crop_expander import KalmanCropExpander
    from utils.role_classifier import RoleClassifier
    from utils.recruiter_output import RecruiterOutputBuilder
    from utils.rally_detector import RallyDetector
    from utils.heatmap_generator import HeatmapGenerator
    from utils.performance_drift import PerformanceDriftTracker
    from utils.match_timeline import MatchTimelineBuilder

    if not skip_quality_check:
        quality = check_video_quality(video_path)
        if not quality.ok:
            raise ValueError(f"VIDEO_QUALITY_FAIL:{quality.to_dict()}")

    localisation = localise_technique(video_path, technique)
    clip_confidence = localisation["confidence"]

    analysis_path = video_path
    tmp_clip_path = None
    if clip_confidence >= 0.55 and localisation["method"] != "full_video_fallback:insufficient_pose_data":
        tmp_clip_path = video_path + "_clip.mp4"
        extract_clip(video_path, localisation["start_frame"], localisation["end_frame"], tmp_clip_path)
        analysis_path = tmp_clip_path

    try:
        yolo = _get_yolo()
        cap = cv2.VideoCapture(analysis_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        img_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        img_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        corrector = HomographyCorrector()
        expander = KalmanCropExpander(frame_w=img_w, frame_h=img_h)
        role_clf = RoleClassifier()
        
        video_id = os.path.basename(analysis_path).split('.')[0]
        builder = RecruiterOutputBuilder(video_id)
        
        rally_detector = RallyDetector(fps=fps)
        heatmap_gen = HeatmapGenerator(frame_w=img_w, frame_h=img_h)
        drift_tracker = PerformanceDriftTracker()
        timeline_builder = MatchTimelineBuilder(video_id=video_id, fps=fps)

        ema_keypoints = load_ema_state()
        
        standing_stats = {}   
        max_jump_heights = {} 
        initial_y = {}        
        
        alpha = 0.7
        low_conf_counter = 0
        frame_counter = 0
        
        track_histories = {}
        
        pose2d_frames, conf_frames, confidences = [], [], []
        track_roles = {}

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_counter += 1
            
            court_data = detect_court_in_frame(frame)
            if court_data["success"] and court_data["polygon"] and len(court_data["polygon"]) >= 4:
                ordered_pts = order_corners(court_data["polygon"])
                if corrector.fit(ordered_pts):
                    frame = corrector.transform(frame)
            
            curr_h, curr_w = frame.shape[:2]

            results = yolo.track(frame, tracker="bytetrack.yaml", persist=True, conf=0.4, verbose=False)
            
            if not results or results[0].boxes is None or results[0].boxes.id is None:
                continue
                
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            bboxes = results[0].boxes.xyxy.cpu().numpy()
            kps_full = results[0].keypoints
            
            detections = {tid: bboxes[i] for i, tid in enumerate(track_ids)}
            expanded_crops = expander.process_frame(detections)
            
            best_idx = _select_person(results, technique, curr_h, locked_centre=locked_centre)
            target_tid = track_ids[best_idx]
            
            for i, tid in enumerate(track_ids):
                if tid not in track_histories: track_histories[tid] = []
                
                bx_cx = (bboxes[i][0] + bboxes[i][2]) / 2
                zone = get_court_zone(bx_cx, curr_w)
                
                track_histories[tid].append({
                    'bbox': bboxes[i],
                    'frame_idx': frame_counter,
                    'court_zone': zone
                })
                track_roles[tid] = role_clf.classify(track_histories[tid])

            if target_tid in expanded_crops:
                cx1, cy1, cx2, cy2 = expanded_crops[target_tid]
                cropped_frame = frame[cy1:cy2, cx1:cx2]
                
                if cropped_frame.size > 0 and cropped_frame.shape[0] > 50:
                    crop_results = yolo(cropped_frame, verbose=False, device=_DEVICE)
                    if crop_results and crop_results[0].keypoints is not None:
                        c_kps = crop_results[0].keypoints
                        if c_kps.conf is not None and len(c_kps.conf) > 0:
                            c_best = int(c_kps.conf.mean(dim=1).argmax())
                            conf = float(c_kps.conf[c_best].mean())
                            
                            if conf >= CONFIDENCE_THRESHOLD:
                                xy_crop = c_kps.xy[c_best].cpu().numpy()
                                kp_conf = c_kps.conf[c_best].cpu().numpy()
                                
                                if target_tid not in ema_keypoints:
                                    ema_keypoints[target_tid] = xy_crop.copy()
                                
                                smoothed_xy = xy_crop.copy()
                                for k in range(17):
                                    if kp_conf[k] < 0.5:
                                        low_conf_counter += 1
                                        smoothed_xy[k] = ema_keypoints[target_tid][k]
                                    else:
                                        ema_keypoints[target_tid][k] = alpha * smoothed_xy[k] + (1 - alpha) * ema_keypoints[target_tid][k]
                                
                                smoothed_xy[:, 0] += cx1
                                smoothed_xy[:, 1] += cy1
                                smoothed_xy = corrector.remap_keypoints(smoothed_xy)
                                
                                pose2d_frames.append(smoothed_xy)
                                conf_frames.append(kp_conf)
                                confidences.append(conf)
                                
                                track = expander.tracks[target_tid]
                                vy = track.kf.statePost[5, 0]
                                is_grounded = abs(vy) < 2.0
                                is_jumping_event = vy > 5.0
                                
                                full_bbox = detections[target_tid]
                                current_h = full_bbox[3] - full_bbox[1]
                                if is_grounded:
                                    stats = standing_stats.get(target_tid, {'sum': 0.0, 'count': 0})
                                    stats['sum'] += current_h
                                    stats['count'] += 1
                                    standing_stats[target_tid] = stats
                                
                                hip_y = (smoothed_xy[11, 1] + smoothed_xy[12, 1]) / 2
                                if target_tid not in initial_y:
                                    initial_y[target_tid] = hip_y
                                
                                current_jump_px = max(0, initial_y[target_tid] - hip_y)
                                max_jump_heights[target_tid] = max(max_jump_heights.get(target_tid, 0), current_jump_px)
                                
                                jump_height_normalised = None
                                avg_standing_h = 0
                                if target_tid in standing_stats and standing_stats[target_tid]['count'] >= 5:
                                    avg_standing_h = standing_stats[target_tid]['sum'] / standing_stats[target_tid]['count']
                                    jump_height_normalised = max_jump_heights[target_tid] / avg_standing_h
                                
                                wrist_y = min(smoothed_xy[9, 1], smoothed_xy[10, 1])
                                head_y = smoothed_xy[0, 1]
                                is_spiking = (track_roles[target_tid] == 'hitter' and track.is_jumping and wrist_y < head_y)
                                
                                bio_frame = {
                                    'avg_jump_height_px': max_jump_heights[target_tid],
                                    'jump_height_normalised': jump_height_normalised,
                                    'avg_standing_height_px': avg_standing_h if avg_standing_h > 0 else None,
                                    'vy': vy, 
                                    'arm_cock_angle': smoothed_xy[0,0] 
                                }
                                event_flags = {
                                    'is_jumping': is_jumping_event,
                                    'is_spiking': is_spiking
                                }
                                builder.update_player(target_tid, track_roles[target_tid], bio_frame, event_flags)
                                
                                bx, by = (cx1 + cx2)/2, (cy1 + cy2)/2
                                heatmap_gen.update(target_tid, bx, by)
                                drift_tracker.update(target_tid, frame_counter, bio_frame)
                                
                                track_states = {}
                                for i, tid in enumerate(track_ids):
                                    t_vy = expander.tracks[tid].kf.statePost[5, 0] if tid in expander.tracks else 0
                                    track_states[tid] = {
                                        'vy': t_vy,
                                        'court_zone': get_court_zone((bboxes[i][0]+bboxes[i][2])/2, curr_w),
                                        'bbox': bboxes[i]
                                    }
                                
                                rally_result = rally_detector.process_frame(frame_counter, track_roles, track_states)
                                timeline_builder.update(frame_counter, rally_result, track_roles, bio_frame)

                                if frame_counter % 100 == 0:
                                    print(f"[Improvement 4] Frame {frame_counter}: {low_conf_counter} keypoints smoothed.")
                                    low_conf_counter = 0
                                continue
            
            xy = kps_full.xy[best_idx].cpu().numpy()
            xy = corrector.remap_keypoints(xy) 
            kp_conf = kps_full.conf[best_idx].cpu().numpy()
            pose2d_frames.append(xy)
            conf_frames.append(kp_conf)
            confidences.append(results[0].boxes.conf[best_idx].item())
            
            builder.update_player(target_tid, track_roles.get(target_tid, 'unknown'), {}, {})

        cap.release()
        
        for tid in track_roles.keys():
            drift_report = drift_tracker.get_drift_report(tid)
            heatmap_dict = heatmap_gen.to_dict(tid)
            
            if str(tid) in builder.players:
                player = builder.players[str(tid)]
                player["performance_drift"] = drift_report
                player["heatmap"] = heatmap_dict
                
            timeline_builder.player_drift_reports[str(tid)] = drift_report

        timeline_builder.save()
        builder.save(output_dir='data/recruiter_outputs/')
        save_ema_state(ema_keypoints)

        if len(pose2d_frames) < 5:
            error_msg = f"Too few valid frames ({len(pose2d_frames)}) detected. "
            if len(pose2d_frames) == 0:
                error_msg += "No athlete detected in video. "
            error_msg += "Tips: 1) Ensure athlete is clearly visible and well-lit, "
            error_msg += "2) Record from side-on angle 5-10m away, "
            error_msg += "3) Include full technique (approach + contact + follow-through), "
            error_msg += f"4) Video should be at least 3 seconds long. "
            error_msg += f"Current confidence threshold: {CONFIDENCE_THRESHOLD}. "
            error_msg += f"Try recording a longer, clearer video."
            raise ValueError(error_msg)

        pose2d   = np.array(pose2d_frames)   
        kp_confs = np.array(conf_frames)
        pose_seq = lift_to_3d(pose2d, img_w, img_h, kp_confs)

        # Apply Savitzky-Golay filter across the time axis (axis=0)
        from scipy.signal import savgol_filter
        if len(pose_seq) > 7:
            pose_seq = savgol_filter(pose_seq, window_length=7, polyorder=2, axis=0)

        return {
            "pose_sequence_3d":   pose_seq,
            "pose_sequence_2d":   pose2d,     
            "biomechanics":       _extract_biomechanics(pose_seq, technique, fps),
            "average_confidence": round(float(np.mean(confidences)), 4),
            "localisation":       localisation,
        }

    finally:
        if tmp_clip_path and os.path.exists(tmp_clip_path):
            os.remove(tmp_clip_path)
