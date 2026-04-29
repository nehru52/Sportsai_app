"""
Smart Analyser — full automatic analysis of any volleyball video.

User uploads ANY video (30 sec match footage, training clip, phone recording).
This module figures out everything:

1. Video quality check — is it even usable?
2. Scan the whole video — what techniques are happening and when?
3. For each detected technique segment — run full biomechanics
4. Generate coaching feedback per segment
5. Return a timeline of everything that happened + improvement advice
"""
import os
import numpy as np
import tempfile
import cv2

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Minimum frames a detected action must last to be worth analysing
MIN_SEGMENT_FRAMES = 15
# How many frames to pad around each detected segment
SEGMENT_PADDING    = 20     # extra frames around each detected segment
# Techniques we can do full biomechanics on
ANALYSABLE = {"spike", "serve", "block", "dig"}


def analyse_video_auto(
    video_path: str,
    athlete_id: str | None = None,
) -> dict:
    """
    Full automatic analysis. No technique hint needed.
    """
    from video_quality import check_video_quality
    from action_detector import detect_actions
    from action_localiser import extract_clip
    from pose_extractor import extract_pose
    from elite_analyser import analyze_elite_biomechanics, POSITION_ELITE_STANDARDS
    from progress_tracker import save_session

    result = {
        "quality":         None,
        "timeline":        [],
        "segments":        [],
        "summary":         {},
        "bad_video_advice": None,
    }

    # ── Step 1: Quality gate ──────────────────────────────────────────────────
    quality = check_video_quality(video_path, run_person_check=False)
    result["quality"] = quality.to_dict()

    if not quality.ok:
        result["bad_video_advice"] = _build_bad_video_advice(quality)
        return result

    # ── Step 2: Scan full video for action events ─────────────────────────────
    cap = cv2.VideoCapture(video_path)
    fps          = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps
    cap.release()

    # Try VolleyVision action detector first
    try:
        action_scan = detect_actions(video_path)
        events      = action_scan.get("events", [])
    except Exception:
        events = []
        action_scan = {"events": [], "action_counts": {}, "total_frames": total_frames}

    # If action detector found nothing, use kinematic scan + physics fallback
    if not events:
        action_scan, events = _kinematic_scan(video_path, fps, total_frames)

    # If EVERYTHING fails, return the error
    if not events:
        result["bad_video_advice"] = (
            "No techniques detected or insufficient data.\n"
            "Make sure the athlete is clearly visible performing a volleyball technique."
        )
        return result

    # ── Step 3: Build timeline ────────────────────────────────────────────────
    timeline = _build_timeline(events, fps, total_frames)
    result["timeline"] = timeline

    # ── Step 4: Extract and analyse each technique segment ───────────────────
    segments = []

    for seg in timeline:
        technique = seg["technique"]
        if technique not in ANALYSABLE:
            segments.append({**seg, "analysis": None,
                             "skip_reason": f"'{technique}' not yet supported for biomechanics"})
            continue

        tmp_clip = tempfile.mktemp(suffix=".mp4")
        try:
            extract_clip(video_path, seg["start_frame"], seg["end_frame"], tmp_clip)

            # Run pose extraction
            pose_result = extract_pose(tmp_clip, technique, skip_quality_check=True)
            
            # ELITE ANALYSIS INTEGRATION
            position = POSITION_ELITE_STANDARDS.get("receiver") # Default
            
            elite_report = analyze_elite_biomechanics(
                pose_result["pose_sequence_3d"], 
                technique,
                session_context={"athlete_id": athlete_id}
            )

            seg_result = {
                **seg,
                "analysis": {
                    "verdict":    elite_report["elite_comparisons"]["olympic_readiness"],
                    "score":      f"{int(elite_report['performance_percentile'])}%",
                    "metrics":    elite_report["elite_comparisons"]["metric_comparisons"],
                    "confidence": pose_result["average_confidence"],
                    "coaching":   {
                        "headline": elite_report["coaching_insights"][0] if elite_report["coaching_insights"] else "Focus on form",
                        "next_session_focus": elite_report["coaching_insights"][1] if len(elite_report["coaching_insights"]) > 1 else "Consistency",
                        "detailed_advice": elite_report["coaching_insights"]
                    },
                    "elite_data": elite_report
                },
            }

            if athlete_id:
                save_session(athlete_id, technique, seg_result["analysis"])

        except Exception as e:
            print(f"Analysis failed for segment: {e}")
            seg_result = {**seg, "analysis": None, "skip_reason": str(e)}
        finally:
            if os.path.exists(tmp_clip):
                os.remove(tmp_clip)

        segments.append(seg_result)

    result["segments"] = segments

    # ── Step 5: Session summary ───────────────────────────────────────────────
    result["summary"] = _build_summary(segments, duration_sec, action_scan)

    return result


def _build_timeline(events: list, fps: float, total_frames: int) -> list:
    if not events:
        return []

    timeline = []
    i = 0
    while i < len(events):
        ev = events[i]
        action = ev["action"]
        
        # For short clips, ensure we grab the whole context
        if total_frames / fps < 15.0:
            start_frame = 0
            end_frame = total_frames - 1
        else:
            start_frame = max(0, ev["frame"] - SEGMENT_PADDING * 3)  
            end_frame = total_frames - 1
            if i + 1 < len(events):
                end_frame = min(events[i + 1]["frame"] + SEGMENT_PADDING, total_frames - 1)

        start_sec = start_frame / fps
        end_sec   = end_frame / fps

        timeline.append({
            "technique":   action,
            "start_frame": int(start_frame),
            "end_frame":   int(end_frame),
            "start_time":  _fmt_time(start_sec),
            "end_time":    _fmt_time(end_sec),
            "duration_sec": round(end_sec - start_sec, 1),
            "detection_confidence": ev.get("confidence", 0),
        })
        i += 1

    return timeline


def _fmt_time(sec: float) -> str:
    m = int(sec // 60)
    s = sec % 60
    return f"{m}:{s:05.2f}"


def _build_summary(segments: list, duration_sec: float, action_scan: dict) -> dict:
    analysed = [s for s in segments if s.get("analysis")]
    if not analysed:
        return {
            "techniques_detected": list(action_scan.get("action_counts", {}).keys()),
            "techniques_analysed": [],
            "overall_verdict": "INSUFFICIENT_DATA",
            "top_strength": None,
            "top_priority": None,
            "session_duration_sec": round(duration_sec, 1),
        }

    all_good, all_bad = [], []
    for seg in analysed:
        report = seg["analysis"]["metrics"]
        for metric, val in report.items():
            # NEW: Using the updated Olympic biomechanics dictionary keys
            measured_val = val.get("measured", 0)
            target_val = val.get("target", 0)
            
            if val.get("is_elite", False):
                all_good.append((metric, measured_val, target_val))
            else:
                all_bad.append((metric, measured_val, target_val))

    top_strength = max(all_good, key=lambda x: abs(x[1] - x[2]))[0] if all_good else None
    top_priority = max(all_bad, key=lambda x: abs(x[1] - x[2]))[0] if all_bad else None

    good_count  = len(all_good)
    total_count = len(all_good) + len(all_bad)
    ratio = good_count / max(total_count, 1)
    overall = "ELITE" if ratio == 1.0 else "GOOD" if ratio >= 0.6 else "NEEDS WORK"

    per_technique = {seg["technique"]: seg["analysis"]["verdict"] for seg in analysed}

    return {
        "techniques_detected":  list(action_scan.get("action_counts", {}).keys()),
        "techniques_analysed":  [s["technique"] for s in analysed],
        "overall_verdict":      overall,
        "per_technique":        per_technique,
        "top_strength":         top_strength,
        "top_priority":         top_priority,
        "metrics_good":         good_count,
        "metrics_total":        total_count,
        "session_duration_sec": round(duration_sec, 1),
        "segments_analysed":    len(analysed),
    }

def _build_bad_video_advice(quality) -> str:
    issues = quality.issues
    recs   = quality.recommendations
    if not issues: return None

    advice_map = [
        ("blurry",      "Your video is too blurry. Hold your phone steady or use a tripod."),
        ("dark",        "Your video is too dark. Record in better lighting."),
        ("overexposed", "Your video is washed out. Don't record with bright light behind the athlete."),
        ("resolution",  "Resolution is too low. Record at 720p or higher."),
        ("short",       "Video is too short. Include full run-up and follow-through."),
        ("visible",     "Athlete isn't fully visible. Frame the full body from head to feet."),
        ("moving",      "Camera is moving too much. Keep the camera stationary."),
    ]

    for keyword, advice in advice_map:
        for issue in issues:
            if keyword in issue.lower():
                return advice

    return f"Video issue: {issues[0]}. {recs[0] if recs else ''}"


def _kinematic_scan(video_path: str, fps: float, total_frames: int) -> tuple:
    """
    Fallback scanner. Uses YOLO pose + kinematic signatures to detect technique windows.
    INCLUDES ULTIMATE PHYSICS FALLBACK for short videos if standard detectors fail.
    """
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from action_localiser import (
        _get_yolo, _joint_velocity_signal,
        _detect_spike_window, _detect_serve_window,
        _detect_block_window, _detect_dig_window
    )

    yolo = _get_yolo()
    cap  = cv2.VideoCapture(video_path)
    keypoints_by_frame = {}
    frame_idx = 0
    
    # Dense scan (every frame) for maximum accuracy on short clips
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # We only need every 2nd frame to save processing time
        if frame_idx % 2 == 0:
            results = yolo(frame, verbose=False)
            if results and results[0].keypoints is not None:
                kps   = results[0].keypoints
                if kps.conf is not None and len(kps.conf) > 0:
                    best_idx = int(kps.conf.mean(dim=1).argmax())
                    xy = kps.xy[best_idx].cpu().numpy()
                    keypoints_by_frame[frame_idx] = xy
        frame_idx += 1
    cap.release()

    if len(keypoints_by_frame) < 5:
        return {"events": [], "action_counts": {}, "total_frames": total_frames}, []

    frames_with_kp = sorted(keypoints_by_frame.keys())
    kp_array = np.array([keypoints_by_frame[f] for f in frames_with_kp])
    velocity = _joint_velocity_signal(kp_array)

    events = []
    action_counts = {}

    detectors = {
        "spike": _detect_spike_window,
        "serve": _detect_serve_window,
        "block": _detect_block_window,
        "dig":   _detect_dig_window,
    }

    # Standard Detection Loop
    for technique, detector in detectors.items():
        result = detector(kp_array, velocity, frames_with_kp, fps)
        if result:
            start_f, end_f, conf, method = result
            if conf >= 0.35:  
                events.append({
                    "frame": int(start_f + (end_f - start_f)//2),
                    "action": technique,
                    "confidence": round(conf, 3),
                })
                action_counts[technique] = action_counts.get(technique, 0) + 1

    # ═══════════════════════════════════════════════════════════════════════
    # ULTIMATE PHYSICS-BASED FALLBACK
    # If the video is a short clip and standard detectors failed, FORCE a guess
    # ═══════════════════════════════════════════════════════════════════════
    if not events and (total_frames / fps) < 15.0:
        print("[smart_analyser] Standard detectors failed. Forcing Physics-Based Fallback.")
        
        # Calculate posture metrics across the whole video
        head_y = kp_array[:, 0, 1]
        wrist_y = np.minimum(kp_array[:, 9, 1], kp_array[:, 10, 1])
        hip_y = (kp_array[:, 11, 1] + kp_array[:, 12, 1]) / 2
        
        max_hip_drop = hip_y.max() - hip_y.min()
        hands_above_head = np.any(wrist_y < head_y)
        
        wrist_dist = np.linalg.norm(kp_array[:, 9, :2] - kp_array[:, 10, :2], axis=1)
        max_wrist_dist = wrist_dist.max()
        
        # Estimate player height in pixels for dynamic thresholds
        person_h = (kp_array[:, 15, 1] - kp_array[:, 0, 1]).max()
        
        guessed_action = "spike" # Default fallback
        
        if hands_above_head:
            if max_wrist_dist < (person_h * 0.3):
                guessed_action = "block"  # Hands held tight together high up
            else:
                guessed_action = "spike"  # Hands apart / swinging
        else:
            if max_hip_drop > (person_h * 0.15):
                guessed_action = "dig"    # Crouching down significantly
            else:
                guessed_action = "serve"  # Standing upright
                
        events.append({
            "frame": total_frames // 2,
            "action": guessed_action,
            "confidence": 0.45
        })
        action_counts[guessed_action] = 1

    events.sort(key=lambda x: x["frame"])
    dominant = max(action_counts, key=action_counts.get) if action_counts else None

    action_scan = {
        "events":         events,
        "action_counts":  action_counts,
        "total_frames":   total_frames,
        "dominant_action": dominant,
    }
    return action_scan, events