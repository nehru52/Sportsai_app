"""
Smart Analyser — full automatic analysis of any volleyball video.

User uploads ANY video (30 sec match footage, training clip, phone recording).
This module figures out everything:

1. Video quality check — is it even usable?
2. Scan the whole video — what techniques are happening and when?
3. For each detected technique segment — run full biomechanics
4. Generate coaching feedback per segment
5. Return a timeline of everything that happened + improvement advice

No need to tell the system "this is a spike video."
It watches the video and tells YOU what's in it.
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

    Returns:
        {
            "quality": {...},           # video quality report
            "timeline": [...],          # what happened and when
            "segments": [...],          # per-technique analysis
            "summary": {...},           # overall session summary
            "bad_video_advice": str,    # if video is bad, specific fix
        }
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

    # Try VolleyVision action detector first, fall back to kinematic scan
    try:
        action_scan = detect_actions(video_path)
        events      = action_scan.get("events", [])
    except Exception:
        events = []
        action_scan = {"events": [], "action_counts": {}, "total_frames": total_frames}

    # If action detector found nothing, use kinematic scan as fallback
    if not events:
        action_scan, events = _kinematic_scan(video_path, fps, total_frames)

    if not events:
        result["bad_video_advice"] = (
            "No volleyball actions were detected in this video. "
            "Make sure the athlete is clearly visible and performing a technique. "
            "The camera should be side-on at net height, 10-15m back."
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

        # Extract the clip for this segment
        tmp_clip = tempfile.mktemp(suffix=".mp4")
        try:
            extract_clip(video_path, seg["start_frame"], seg["end_frame"], tmp_clip)

            # Run pose extraction
            pose_result = extract_pose(tmp_clip, technique, skip_quality_check=True)
            
            # ELITE ANALYSIS INTEGRATION
            # Automatically detect position or use receiver as default
            position = POSITION_ELITE_STANDARDS.get("receiver") # Default
            
            # Perform Olympic-grade analysis
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

            # Save to progress history
            if athlete_id:
                save_session(athlete_id, technique, seg_result["analysis"])

        except Exception as e:
            import traceback
            print(f"Analysis failed for segment: {e}")
            traceback.print_exc()
            seg_result = {**seg, "analysis": None, "skip_reason": str(e)}
        finally:
            if os.path.exists(tmp_clip):
                os.remove(tmp_clip)

        segments.append(seg_result)

    result["segments"] = segments

    # ── Step 5: Session summary ───────────────────────────────────────────────
    result["summary"] = _build_summary(segments, duration_sec, action_scan)

    return result


# ── Timeline builder ──────────────────────────────────────────────────────────

def _build_timeline(events: list, fps: float, total_frames: int) -> list:
    """
    Convert raw action events into a clean timeline of segments.
    Merges consecutive same-action events into one segment.
    Adds human-readable timestamps.
    """
    if not events:
        return []

    timeline = []
    i = 0
    while i < len(events):
        ev = events[i]
        action = ev["action"]
        start_frame = max(0, ev["frame"] - SEGMENT_PADDING * 3)  # grab more before

        # Find end: next different action or end of video
        end_frame = total_frames - 1
        if i + 1 < len(events):
            end_frame = min(events[i + 1]["frame"] + SEGMENT_PADDING, total_frames - 1)

        # Skip tiny segments
        if end_frame - start_frame < MIN_SEGMENT_FRAMES:
            i += 1
            continue

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


# ── Summary builder ───────────────────────────────────────────────────────────

def _build_summary(segments: list, duration_sec: float, action_scan: dict) -> dict:
    """Build an overall session summary across all detected techniques."""
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

    # Collect all metrics across all segments
    all_good, all_bad = [], []
    for seg in analysed:
        report = seg["analysis"]["metrics"]
        for metric, val in report.items():
            if val.get("status", "") == "GOOD":
                all_good.append((metric, val["value"], val["elite_mean"]))
            else:
                all_bad.append((metric, val["value"], val["elite_mean"]))

    # Top strength = metric furthest above elite mean (proportionally)
    top_strength = None
    if all_good:
        top_strength = max(all_good, key=lambda x: abs(x[1] - x[2]))[0]

    # Top priority = metric furthest below elite mean
    top_priority = None
    if all_bad:
        top_priority = max(all_bad, key=lambda x: abs(x[1] - x[2]))[0]

    # Overall verdict
    good_count  = len(all_good)
    total_count = len(all_good) + len(all_bad)
    ratio = good_count / max(total_count, 1)
    overall = "ELITE" if ratio == 1.0 else "GOOD" if ratio >= 0.6 else "NEEDS WORK"

    # Per-technique verdicts
    per_technique = {}
    for seg in analysed:
        t = seg["technique"]
        per_technique[t] = seg["analysis"]["verdict"]

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


# ── Bad video advice ──────────────────────────────────────────────────────────

def _build_bad_video_advice(quality) -> str:
    """
    Turn quality issues into a single clear message the user can act on.
    Prioritises the most impactful fix.
    """
    issues = quality.issues
    recs   = quality.recommendations

    if not issues:
        return None

    # Map issue keywords to plain advice
    advice_map = [
        ("blurry",      "Your video is too blurry. Hold your phone steady or prop it against something. A tripod costs £10 and makes a huge difference."),
        ("dark",        "Your video is too dark. Record in daylight or turn on the gym lights. The athlete's full body must be clearly lit."),
        ("overexposed", "Your video is too bright/washed out. Don't record with bright light or sun directly behind the athlete."),
        ("resolution",  "Your video resolution is too low. Record at 720p or higher — most phones do this by default in camera settings."),
        ("short",       "Your video is too short. Record the full movement including the run-up and follow-through, not just the contact moment."),
        ("visible",     "The athlete isn't clearly visible. Frame the full body from head to feet. Don't zoom in on just the upper body."),
        ("moving",      "The camera is moving too much. Fix the camera in one position before recording. Don't follow the athlete with the camera."),
    ]

    for keyword, advice in advice_map:
        for issue in issues:
            if keyword in issue.lower():
                return advice

    # Generic fallback
    return f"Video issue: {issues[0]}. {recs[0] if recs else ''}"


def _verdict(report: dict) -> str:
    good  = sum(1 for r in report.values() if r["status"] == "GOOD")
    total = len(report)
    if good == total:        return "ELITE"
    if good >= total * 0.6:  return "GOOD"
    return "NEEDS WORK"


def _kinematic_scan(video_path: str, fps: float, total_frames: int) -> tuple:
    """
    Fallback scanner when VolleyVision action detector fails or finds nothing.
    Uses YOLO pose + kinematic signatures to detect technique windows.
    
    ADAPTIVE SAMPLING: Scans every frame during high-velocity movements,
    skips frames only during "dead time" to avoid aliasing the impact moment.
    """
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from action_localiser import (
        _get_yolo, _joint_velocity_signal,
        _detect_spike_window, _detect_serve_window,
        _detect_block_window, _detect_dig_window,
        SAMPLE_RATE, PADDING_FRAMES
    )

    yolo = _get_yolo()
    cap  = cv2.VideoCapture(video_path)
    keypoints_by_frame = {}
    frame_idx = 0
    locked_centre = None
    LOCK_AFTER = 5
    
    # ═══════════════════════════════════════════════════════════════════════
    # ADAPTIVE SAMPLING: Two-pass approach
    # Pass 1: Coarse scan to find activity regions
    # Pass 2: Dense scan (every frame) in high-activity regions
    # ═══════════════════════════════════════════════════════════════════════
    
    # Pass 1: Coarse scan (sample every Nth frame)
    COARSE_SAMPLE_RATE = 5
    coarse_velocities = []
    coarse_frames = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % COARSE_SAMPLE_RATE == 0:
            results = yolo(frame, verbose=False)
            if results and results[0].keypoints is not None:
                kps   = results[0].keypoints
                conf_kps = kps.conf
                boxes = results[0].boxes
                
                if conf_kps is not None and len(conf_kps) > 0:
                    img_h = frame.shape[0]
                    
                    # Use existing locked person if available
                    if locked_centre is not None and boxes is not None:
                        lx, ly = locked_centre
                        best_idx, min_dist = 0, float('inf')
                        for i in range(min(len(conf_kps), len(boxes.xywh))):
                            cx, cy = float(boxes.xywh[i, 0]), float(boxes.xywh[i, 1])
                            dist = (cx - lx)**2 + (cy - ly)**2
                            if dist < min_dist:
                                min_dist = dist
                                best_idx = i
                    else:
                        # Score everyone to find the ATHLETE
                        scores = []
                        for i in range(len(conf_kps)):
                            kp = kps.xy[i].cpu().numpy()
                            conf = float(conf_kps[i].mean())
                            wrist_y = min(kp[9, 1], kp[10, 1])
                            reach = (img_h - wrist_y) / img_h
                            ankle_y = (kp[15, 1] + kp[16, 1]) / 2
                            airborne = (img_h - ankle_y) / img_h
                            score = (reach * 0.4 + airborne * 0.4 + conf * 0.2)
                            scores.append(score)
                        best_idx = int(np.argmax(scores))

                    xy = kps.xy[best_idx].cpu().numpy()
                    
                    # Calculate velocity for this frame
                    if len(coarse_frames) > 0:
                        prev_xy = keypoints_by_frame[coarse_frames[-1]]
                        velocity = np.linalg.norm(xy - prev_xy, axis=1).sum()
                        coarse_velocities.append(velocity)
                    
                    keypoints_by_frame[frame_idx] = xy
                    coarse_frames.append(frame_idx)
                    
                    # Establish lock
                    if locked_centre is None and len(coarse_frames) >= LOCK_AFTER:
                        if boxes is not None and best_idx < len(boxes.xywh):
                            locked_centre = (float(boxes.xywh[best_idx, 0]), float(boxes.xywh[best_idx, 1]))
        frame_idx += 1
    cap.release()
    
    if len(coarse_frames) < 5:
        return {"events": [], "action_counts": {}, "total_frames": total_frames}, []
    
    # Identify high-activity regions (where velocity > 70th percentile)
    velocity_threshold = np.percentile(coarse_velocities, 70) if coarse_velocities else 0
    high_activity_regions = []
    in_region = False
    region_start = 0
    
    for i, vel in enumerate(coarse_velocities):
        if vel > velocity_threshold and not in_region:
            in_region = True
            region_start = coarse_frames[i]
        elif vel <= velocity_threshold * 0.5 and in_region:
            in_region = False
            region_end = coarse_frames[i]
            # Expand region by 0.5 seconds on each side
            high_activity_regions.append((
                max(0, region_start - int(fps * 0.5)),
                min(total_frames, region_end + int(fps * 0.5))
            ))
    
    if in_region:
        high_activity_regions.append((region_start, total_frames))
    
    # Pass 2: Dense scan (every frame) in high-activity regions
    cap = cv2.VideoCapture(video_path)
    frame_idx = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Check if this frame is in a high-activity region
        in_active_region = any(start <= frame_idx <= end for start, end in high_activity_regions)
        
        # Process every frame in active regions, skip otherwise
        if in_active_region and frame_idx not in keypoints_by_frame:
            results = yolo(frame, verbose=False)
            if results and results[0].keypoints is not None:
                kps   = results[0].keypoints
                conf_kps = kps.conf
                boxes = results[0].boxes
                
                if conf_kps is not None and len(conf_kps) > 0:
                    img_h = frame.shape[0]
                    
                    if locked_centre is not None and boxes is not None:
                        lx, ly = locked_centre
                        best_idx, min_dist = 0, float('inf')
                        for i in range(min(len(conf_kps), len(boxes.xywh))):
                            cx, cy = float(boxes.xywh[i, 0]), float(boxes.xywh[i, 1])
                            dist = (cx - lx)**2 + (cy - ly)**2
                            if dist < min_dist:
                                min_dist = dist
                                best_idx = i
                    else:
                        scores = []
                        for i in range(len(conf_kps)):
                            kp = kps.xy[i].cpu().numpy()
                            conf = float(conf_kps[i].mean())
                            wrist_y = min(kp[9, 1], kp[10, 1])
                            reach = (img_h - wrist_y) / img_h
                            ankle_y = (kp[15, 1] + kp[16, 1]) / 2
                            airborne = (img_h - ankle_y) / img_h
                            score = (reach * 0.4 + airborne * 0.4 + conf * 0.2)
                            scores.append(score)
                        best_idx = int(np.argmax(scores))

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

    # Try each technique detector
    for technique, detector in detectors.items():
        result = detector(kp_array, velocity, frames_with_kp, fps)
        if result:
            start_f, end_f, conf, method = result
            if conf >= 0.35:  # Even more permissive for fast Olympic movements
                events.append({
                    "frame":      int(start_f + (end_f - start_f)//2),
                    "action":     technique,
                    "confidence": round(conf, 3),
                })
                action_counts[technique] = action_counts.get(technique, 0) + 1

    # Sort events by frame
    events.sort(key=lambda x: x["frame"])

    # If we found multiple events of different types at the same time, pick best
    # (Simple deduplication)
    filtered_events = []
    if events:
        filtered_events.append(events[0])
        for i in range(1, len(events)):
            if events[i]["frame"] - filtered_events[-1]["frame"] > fps * 2:
                filtered_events.append(events[i])
            elif events[i]["confidence"] > filtered_events[-1]["confidence"]:
                filtered_events[-1] = events[i]
        
    dominant = max(action_counts, key=action_counts.get) if action_counts else None

    action_scan = {
        "events":         filtered_events,
        "action_counts":  action_counts,
        "total_frames":   total_frames,
        "dominant_action": dominant,
        "source":         "kinematic_fallback_adaptive",
    }
    return action_scan, filtered_events
